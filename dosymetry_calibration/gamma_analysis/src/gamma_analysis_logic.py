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
import cv2
import numpy as np
import matplotlib.pyplot as plt


# python path
# C:\Users\jakub\AppData\Local\slicer.org\Slicer 5.6.2\bin
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
    
    def runGammaAnalysis(self, inputImage: vtkMRMLVectorVolumeNode, calibrationFilePath: str, outputDirectoryPath: str, roiNodes, advancedSettings, controlStripeDose=None, recalibrationStripeDose=None, progressUpdate=None) -> np.ndarray:
        import time

        startTime = time.time()
        logging.info(f"Processing started")
        
        workDir = os.path.join(os.path.dirname(__file__), '..')
        tempDir = os.path.join(workDir, 'temp')
        os.makedirs(tempDir, exist_ok=True)
        
        
       
        # shutil.rmtree(tempDir)
        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")
        return None
        
    def detectStripes(self, volume_node, recalibration_stripes_present):
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        """

        if not volume_node or recalibration_stripes_present is None:
            raise ValueError("Input or output volume is invalid")

        pass
        
    

        
    
    
        