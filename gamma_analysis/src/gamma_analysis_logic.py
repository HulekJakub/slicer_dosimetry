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
        rtDoseFilepath: str,
        rtPlanFilepath: str,
        dose,
        dose_threshold,
        dta,
        localGamma,
    ):
        import time

        startTime = time.time()
        logging.info(f"Processing started")

        rtDoseDicom = pydicom.dcmread(rtDoseFilepath, force=True)
        dicomFileName = os.path.basename(rtDoseFilepath)
        rtDoseVolume = self.__loadVolumeFromDICOMFile(rtDoseDicom, dicomFileName)
        scaling = float(rtDoseDicom.DoseGridScaling)

        rtDose = (
            slicer.util.arrayFromVolume(rtDoseVolume) * scaling * 100
        )  # dose in 16-bit unsigned int * Gy per unit * 100 to convert to cGY
        dosimetryResult = slicer.util.arrayFromVolume(dosimetryResultVolume)[0]
        dosimetryResult = dosimetryResult.astype("float64")
        spacing = dosimetryResultVolume.GetSpacing()

        rtPlanDicom = pydicom.dcmread(rtPlanFilepath, force=True)
        X, Y, Z = rtPlanDicom.BeamSequence[0].ControlPointSequence[0].IsocenterPosition

        _, J, _ = self.__getIJKCoordinates1(X, Y, Z, rtDoseVolume)
        section = np.copy(rtDose[:, J, :])
        section = section[::-1, :]

        moving = sitk.GetImageFromArray(section)
        moving.SetSpacing((rtDoseVolume.GetSpacing()[0], rtDoseVolume.GetSpacing()[2]))         # fill in your real mm/pixel
        fixed = sitk.GetImageFromArray(dosimetryResult)
        fixed.SetSpacing(dosimetryResultVolume.GetSpacing()[:2])         # fill in your real mm/pixel
        
        alignedRtDoseImage = self.__affine_registration(fixed, moving)
        alignedRtDose = sitk.GetArrayFromImage(alignedRtDoseImage)

        gammaImage = self.__calculate_gamma_index(
            alignedRtDose,
            dosimetryResult,
            spacing,
            dose,
            dta,
            dose_threshold,
            localGamma=localGamma,
        )

        GPR = (
            1.0 - len(np.where(gammaImage >= 1.0)[0]) / np.prod(gammaImage.shape)
        ) * 100

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")

        return GPR, gammaImage, alignedRtDose, section

    def __loadVolumeFromDICOMFile(self, dicomFile, name):
        pixelImage = dicomFile.pixel_array.astype(np.uint16)

        # pixelImage = np.squeeze(pixelImage)
        volumeNode = slicer.util.addVolumeFromArray(pixelImage, name=name)

        pixel_spacing = [float(spc) for spc in dicomFile.PixelSpacing]
        slice_thickness = float(
            1 if dicomFile.SliceThickness is None else dicomFile.SliceThickness
        )
        spacing = [pixel_spacing[0], pixel_spacing[1], slice_thickness]
        volumeNode.SetSpacing(spacing)

        origin = [float(v) for v in dicomFile.ImagePositionPatient]
        volumeNode.SetOrigin(origin)

        orientation = [float(x) for x in dicomFile.ImageOrientationPatient]
        row_cosines = np.array(orientation[0:3])
        col_cosines = np.array(orientation[3:6])
        slice_cosines = np.cross(row_cosines, col_cosines)
        ijk_to_ras = vtk.vtkMatrix4x4()
        for i in range(3):
            ijk_to_ras.SetElement(i, 0, row_cosines[i] * spacing[0])
            ijk_to_ras.SetElement(i, 1, col_cosines[i] * spacing[1])
            ijk_to_ras.SetElement(i, 2, slice_cosines[i] * spacing[2])
            ijk_to_ras.SetElement(i, 3, origin[i])
        ijk_to_ras.SetElement(3, 3, 1.0)

        volumeNode.SetIJKToRASMatrix(ijk_to_ras)
        print(ijk_to_ras)

        return volumeNode

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
        localGamma=False,
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
            local_gamma=localGamma,
        )
        gamma = np.nan_to_num(gamma, nan=0)

        return gamma
