from typing import Annotated

from slicer.ScriptedLoadableModule import *
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import  vtkMRMLVectorVolumeNode, vtkMRMLScalarVolumeNode
#
# film_calibrationParameterNode
#


@parameterNodeWrapper
class film_calibrationParameterNode:
    """
    The parameters needed by module.

    inputVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    invertThreshold - If true, will invert the threshold.
    thresholdedVolume - The output volume that will contain the thresholded volume.
    invertedVolume - The output volume that will contain the inverted thresholded volume.
    """

    inputVolume: vtkMRMLVectorVolumeNode
    imageThreshold: Annotated[float, WithinRange(0, 255)] = 100
    invertThreshold: bool = False
    thresholdedVolume: vtkMRMLScalarVolumeNode
    invertedVolume: vtkMRMLScalarVolumeNode
