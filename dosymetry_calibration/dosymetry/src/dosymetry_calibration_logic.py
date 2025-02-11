import logging
from typing import Any, Dict
import os
import json
import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *

from slicer import vtkMRMLVectorVolumeNode, vtkMRMLScalarVolumeNode

import slicer.util
from src.dosymetry_calibration_parameter_node import dosymetryParameterNode
#
# dosymetryLogic
#
try:
    import cv2
except ModuleNotFoundError:
    slicer.util.pip_install("opencv-contrib-python")
    import cv2
  
try:
    import numpy as np
except ModuleNotFoundError:
    slicer.util.pip_install("numpy")
    import numpy as np

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    slicer.util.pip_install("matplotlib")
    import matplotlib.pyplot as plt

try:
    from scipy.optimize import curve_fit
except ModuleNotFoundError:
    slicer.util.pip_install("scipy")
    from scipy.optimize import curve_fit

# python path
# C:\Users\jakub\AppData\Local\slicer.org\Slicer 5.6.2\bin
class dosymetryLogic(ScriptedLoadableModuleLogic):
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
        return dosymetryParameterNode(super().getParameterNode())

    def run(self, inputImage: vtkMRMLVectorVolumeNode, calibrationFilePath: str, outputDirectoryPath: str) -> Dict[int, Dict[str, Any]]:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        """

        if not inputImage or not calibrationFilePath:
            raise ValueError("Input or output volume is invalid")

        print(calibrationFilePath)
        print(outputDirectoryPath)
        
    
    
        