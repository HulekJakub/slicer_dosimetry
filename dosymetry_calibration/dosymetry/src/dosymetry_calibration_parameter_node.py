from typing import Annotated

from slicer.ScriptedLoadableModule import *
from slicer.parameterNodeWrapper import parameterNodeWrapper

from slicer import vtkMRMLVectorVolumeNode

@parameterNodeWrapper
class dosymetryParameterNode:
    """
    The parameters needed by the module.

    inputImage - The 3-channel input image where markers will be detected and placed.
    calibrationFilePath - A .txt file containing additional marker-related data or configurations.
    """

    inputImage: vtkMRMLVectorVolumeNode  # 3-channel input image

