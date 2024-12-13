import logging

import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *

from slicer import vtkMRMLVectorVolumeNode, vtkMRMLScalarVolumeNode

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

    def process(self,
                inputVolume: vtkMRMLVectorVolumeNode,
                outputVolume: vtkMRMLScalarVolumeNode,
                imageThreshold: float,
                invert: bool = False,
                showResult: bool = True) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not outputVolume:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.time()
        logging.info(f"Processing started {imageThreshold} {invert}")
        img = slicer.util.arrayFromVolume(inputVolume)
        cv2.imwrite(r'C:\Studia\Magisterka\dosymetry_slicer\opened_image.png', img)
        thresholded_image = np.zeros((1, img.shape[1], img.shape[2], 1))
        img_gray = cv2.cvtColor(img[0], cv2.COLOR_RGBA2GRAY)
        logging.info(str(np.mean(img_gray)))
        img_gray[img_gray >= imageThreshold] = 255
        img_gray[img_gray < imageThreshold] = 0
        if invert:
            img_gray[img_gray >= imageThreshold] = 0
            img_gray[img_gray < imageThreshold] = 255
        else:
            img_gray[img_gray >= imageThreshold] = 255
            img_gray[img_gray < imageThreshold] = 0
        print(img_gray[:,:,np.newaxis].shape)
        print(thresholded_image[0].shape)
        thresholded_image[0] = img_gray[:,:,np.newaxis]
        slicer.util.updateVolumeFromArray(outputVolume, img_gray[np.newaxis,:,:])
        
        
        
        print(img.shape)
        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        cliParams = {
            "InputVolume": inputVolume.GetID(),
            "OutputVolume": outputVolume.GetID(),
            "ThresholdValue": imageThreshold,
            "ThresholdType": "Above" if invert else "Below",
        }
        # cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
        # # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        # slicer.mrmlScene.RemoveNode(cliNode)

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")


