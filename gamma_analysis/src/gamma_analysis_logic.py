import sys
import logging
import os
import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *

from slicer import vtkMRMLVectorVolumeNode, vtkMRMLScalarVolumeNode

import slicer.util
from src.gamma_analysis_parameter_node import gamma_analysisParameterNode

# gamma_analysisLogic
#
import numpy as np
import subprocess
import SimpleITK as sitk
import pydicom
import vtk
import pymedphys


class gamma_analysisLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return gamma_analysisParameterNode(super().getParameterNode())

    def runGammaAnalysis(
        self,
        dosimetryResultVolume: vtkMRMLScalarVolumeNode,
        rtDoseVolume: vtkMRMLScalarVolumeNode,
        rtPlanFilepath: str,
        dose,
        dose_threshold,
        dta,
    ):
        import time

        startTime = time.time()
        logging.info(f"Processing started")

        rtDoseFileName = rtDoseVolume.GetStorageNode().GetFileName()
        rtDoseDicom = pydicom.dcmread(rtDoseFileName, force=True)
        scaling = float(rtDoseDicom.DoseGridScaling)

        rtDose = (
            slicer.util.arrayFromVolume(rtDoseVolume) * scaling * 100
        )  # change Gy to cGy
        dosimetryResult = slicer.util.arrayFromVolume(dosimetryResultVolume)[0]
        dosimetryResult = dosimetryResult.astype("float64")
        spacing = dosimetryResultVolume.GetSpacing()

        rtPlanDicom = pydicom.dcmread(rtPlanFilepath, force=True)
        X, Y, Z = rtPlanDicom.BeamSequence[0].ControlPointSequence[0].IsocenterPosition

        _, J, _ = self.__getIJKCoordinates1(X, -Y, Z, rtDoseVolume)

        section = np.copy(rtDose[:, J, :])
        section = section[::-1, :]

        moving = sitk.GetImageFromArray(section)
        fixed = sitk.GetImageFromArray(dosimetryResult)

        alignedRtDoseImage = self.__affine_registration(fixed, moving)
        alignedRtDose = sitk.GetArrayFromImage(alignedRtDoseImage)

        gammaImage = self.__calculate_gamma_index(
            alignedRtDose, dosimetryResult, spacing, dose, dta, dose_threshold
        )

        GPR = (
            1.0 - len(np.where(gammaImage >= 1.0)[0]) / np.prod(gammaImage.shape)
        ) * 100

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")

        return GPR, gammaImage, alignedRtDose

    def __getIJKCoordinates1(self, X, Y, Z, volumeNode):
        # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository/volumes.html "Get volume voxel coordinates from markup control point RAS coordinates"
        point_Ras = [X, Y, Z]

        transformRasToVolumeRas = vtk.vtkGeneralTransform()
        slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(
            None, volumeNode.GetParentTransformNode(), transformRasToVolumeRas
        )
        point_VolumeRas = transformRasToVolumeRas.TransformPoint(point_Ras)

        # Get voxel coordinates from physical coordinates
        volumeRasToIjk = vtk.vtkMatrix4x4()
        volumeNode.GetRASToIJKMatrix(volumeRasToIjk)
        point_Ijk = [0, 0, 0, 1]
        volumeRasToIjk.MultiplyPoint(np.append(point_VolumeRas, 1.0), point_Ijk)
        point_Ijk = [int(round(c)) for c in point_Ijk[0:3]]

        return point_Ijk

    def __affine_registration(self, fixed, moving):
        R = sitk.ImageRegistrationMethod()
        R.SetMetricAsCorrelation()
        R.SetOptimizerAsRegularStepGradientDescent(
            learningRate=2.0,
            minStep=1e-12,
            numberOfIterations=1000,
            gradientMagnitudeTolerance=1e-8,
        )
        R.SetOptimizerScalesFromIndexShift()
        tx = sitk.CenteredTransformInitializer(
            fixed, moving, sitk.Similarity2DTransform()
        )
        R.SetInitialTransform(tx)
        R.SetInterpolator(sitk.sitkLinear)

        outTx = R.Execute(fixed, moving)

        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(fixed)
        resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetDefaultPixelValue(0)
        resampler.SetTransform(outTx)

        out = resampler.Execute(moving)

        return out

    def __calculate_gamma_index(
        self,
        alignedRtDose,
        dosimetryResult,
        spacing,
        dose,
        dta,
        dose_threshold,
        max_gamma=2.0,
        interp_fraction=5,
    ) -> np.ndarray:

        gridx = np.arange(alignedRtDose.shape[0]) * abs(spacing[0])
        gridy = np.arange(alignedRtDose.shape[1]) * abs(spacing[1])
        grid = (gridx, gridy)

        gamma = pymedphys.gamma(
            grid,
            alignedRtDose,
            grid,
            dosimetryResult,
            dose,
            dta,
            max_gamma=max_gamma,
            interp_fraction=interp_fraction,
            lower_percent_dose_cutoff=dose_threshold,
        )
        gamma = np.nan_to_num(gamma, nan=0)

        return gamma
