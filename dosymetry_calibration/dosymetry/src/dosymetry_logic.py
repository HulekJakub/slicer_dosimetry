import logging
from typing import Any, Dict
import os
import json
import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *

from slicer import vtkMRMLVectorVolumeNode, vtkMRMLScalarVolumeNode

import slicer.util
from src.dosymetry_parameter_node import dosymetryParameterNode
from src.detect_dosymetry_stripes import detect_dosymetry_stripes

import subprocess
import SimpleITK as sitk
import shutil
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
    
    def runDosymetry(self, inputImage: vtkMRMLVectorVolumeNode, calibrationFilePath: str, outputDirectoryPath: str, roiNodes, advancedSettings, controlStripeDose=None, recalibrationStripeDose=None) -> np.ndarray:
        import time

        startTime = time.time()
        logging.info(f"Processing started")
        
        workDir = os.path.join(os.path.dirname(__file__), '..')
        tempDir = os.path.join(workDir, 'temp')
        os.makedirs(tempDir, exist_ok=True)
        
        
        roiRegions = self.__extractRoiRegions(inputImage, roiNodes)
        sampleRegionFilePath = self.__exportSampleRegion(roiRegions, tempDir, advancedSettings['median_kernel_size'])
        
        parameters = self.__createParametersDict(calibrationFilePath, outputDirectoryPath, advancedSettings, controlStripeDose, recalibrationStripeDose, roiRegions, sampleRegionFilePath, tempDir)
        parameters_path = os.path.join(tempDir, 'parameters.json')
        with open(parameters_path, 'w') as f:
            json.dump(parameters, f, indent=2)
        
        process = self.__createProcessingProcess(workDir, parameters_path)
        for message in self.__monitorProcessing(process):
            print(f"Received: {message.strip()}", flush=True)
            
        result_path = message.strip()
        
        imgSITK = sitk.ReadImage(result_path)
        img = sitk.GetArrayFromImage(imgSITK)    
        # shutil.rmtree(tempDir)
        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")
        return img
        
    def detectStripes(self, volume_node, recalibration_stripes_present):
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        """

        if not volume_node or recalibration_stripes_present is None:
            raise ValueError("Input or output volume is invalid")

        img = slicer.util.arrayFromVolume(volume_node)
        img = img.reshape((img.shape[-3], img.shape[-2], img.shape[-1]))
        output = detect_dosymetry_stripes(img, recalibration_stripes_present)
        
        return output
        
    def __exportSampleRegion(self, roiRegions, tempDir, kernel_size):
        img = roiRegions['sample']
            
        if kernel_size >= 1:
            img = cv2.medianBlur(img, ksize=kernel_size)
        
        imSITK = sitk.GetImageFromArray(img)
        fname = os.path.join(tempDir, 'temp.nii.gz')
        sitk.WriteImage(imSITK, fname)
        return fname
        
    def __createParametersDict(self, calibrationFilePath, outputDirectoryPath, advancedSettings, controlStripeDose, recalibrationStripeDose, roiRegions, sampleRegionFilePath, tempDir):
        parameters = {
            **advancedSettings,
            "outputDirectoryPath": outputDirectoryPath,
            "sampleRegionFilePath": sampleRegionFilePath,
            "tempPath": tempDir
        }
        
        if controlStripeDose is not None and recalibrationStripeDose is not None:
            control_rgb_mean = {c: roiRegions['control'][:,:,i].mean() for i, c in enumerate(['r', 'g', 'b'])}
            recalibration_rgb_mean = {c: roiRegions['recalibration'][:,:,i].mean() for i, c in enumerate(['r', 'g', 'b'])}
            parameters['control_stripe_dose'] = controlStripeDose
            parameters['recalibration_stripe_dose'] = recalibrationStripeDose
            parameters['control_rgb_mean'] = control_rgb_mean
            parameters['recalibration_rgb_mean'] = recalibration_rgb_mean
            
        with open(calibrationFilePath, 'r') as f:
            calibration_parameters = json.load(f)
        parameters['calibration_parameters'] = calibration_parameters
        return parameters
    
    def __createProcessingProcess(self, workDir, parameters_path):
        slicerDir = os.getcwd()
        env = os.environ.copy()
        env['PYTHONPATH'] = env['PYTHONPATH'] + os.pathsep + os.path.join(os.path.dirname(__file__), '..').replace('\\\\', '/')
        cmd = [os.path.join(slicerDir, 'bin','PythonSlicer'),  os.path.join(workDir, 'src', 'logic_subprocess.py'), parameters_path]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=(subprocess.CREATE_NO_WINDOW),
            env=env,
            text=True
        )
        return process
    
    def __monitorProcessing(self, process):
        while True:
            line = process.stdout.readline()
            if not line:
                break
            yield line
        stderr_output = process.stderr.read()
        if stderr_output:
            print("Error:", stderr_output.strip())
        print("Finished with code:",process.wait())
        
    def __extractRoiRegions(self, volume_node, roi_nodes):
        """Extract regions in IJK format and convert to arrays."""
        # Get image properties
        image_data = slicer.util.arrayFromVolume(volume_node)  # Get numpy array
        image_data = image_data.reshape((image_data.shape[-3], image_data.shape[-2], image_data.shape[-1]))
        
        spacing = volume_node.GetSpacing()
        origin = volume_node.GetOrigin()

        # Prepare result storage
        roi_regions = {}

        for key, roi_node in roi_nodes.items():
            # Get ROI parameters
            bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            roi_node.GetBounds(bounds)
            print(bounds)

            # Convert RAS bounds to IJK
            col_max = int(round((origin[0] - bounds[0]) / spacing[0]))  
            col_min = int(round((origin[0] - bounds[1]) / spacing[0]))  
            row_max = int(round((origin[1] - bounds[2]) / spacing[1]))  
            row_min = int(round((origin[1] - bounds[3]) / spacing[1]))  
            
            col_min = max(0, col_min)
            row_min = max(0, row_min)
            print(image_data.shape)
            col_max = min(image_data.shape[1] - 1, col_max)
            row_max = min(image_data.shape[0] - 1, row_max)
            
            print((col_min, row_min), (col_max, row_max))
            # Extract region as numpy array
            roi_pixels = image_data[row_min: row_max + 1, col_min: col_max + 1]

            # Store result
            roi_regions[key] = roi_pixels

        return roi_regions
        

        
    
    
        