import logging
from typing import Any, Dict

import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *

from slicer import vtkMRMLVectorVolumeNode, vtkMRMLScalarVolumeNode
from src.marker_detection import markers_detection

import slicer.util
from src.film_calibration_parameter_node import film_calibrationParameterNode
#
# film_calibrationLogic
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

# python path
# C:\Users\jakub\AppData\Local\slicer.org\Slicer 5.6.2\bin
class film_calibrationLogic(ScriptedLoadableModuleLogic):
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
        return film_calibrationParameterNode(super().getParameterNode())

    def detectStripes(self, inputImage: vtkMRMLVectorVolumeNode, calibrationFilePath: str) -> Dict[int, Dict[str, Any]]:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        """

        if not inputImage or not calibrationFilePath:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.time()
        logging.info(f"Processing started")
        img = slicer.util.arrayFromVolume(inputImage)
        print(img.shape)
        img = img.reshape((img.shape[-3], img.shape[-2], img.shape[-1]))
        print(img.shape)
        with open(calibrationFilePath, 'r') as f:
            calibration_lines = [line.strip() for line in f.readlines() if line.strip() != '']
        output = markers_detection(img, calibration_lines)

        print(output)
        # slicer.util.updateVolumeFromArray(outputVolume, img_gray[np.newaxis,:,:])
        
        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")
        
        return output
