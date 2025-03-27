from typing import Annotated

from slicer.ScriptedLoadableModule import *
from slicer.parameterNodeWrapper import parameterNodeWrapper

from slicer import vtkMRMLScalarVolumeNode


@parameterNodeWrapper
class gamma_analysisParameterNode:
    """
    The parameters needed by the module.

    inputImage - The 3-channel input image where markers will be detected and placed.
    """

    dosymetryResultVolume: vtkMRMLScalarVolumeNode
    rtDoseVolume: vtkMRMLScalarVolumeNode
