
import slicer
try:
    import cv2
except ModuleNotFoundError:
    slicer.util.pip_install("opencv-contrib-python")
    
try:
    import numpy as np
except ModuleNotFoundError:
    slicer.util.pip_install("numpy")
    
try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    slicer.util.pip_install("matplotlib")
    
try:
    from scipy.optimize import curve_fit
except ModuleNotFoundError:
    slicer.util.pip_install("scipy")
    
try:
    import SimpleITK as sitk
except ModuleNotFoundError:
    slicer.util.pip_install("SimpleITK")
    
try:
    import cv2
except ModuleNotFoundError:
    slicer.util.pip_install("imageio")
    
try:
    from pycimg import CImg
except ModuleNotFoundError:
    slicer.util.pip_install("pycimg")

try:
    import pydicom
except ModuleNotFoundError:
    slicer.util.pip_install("pydicom")

try:
    import pymedphys
except:
    slicer.util.pip_install("pymedphys==0.37.1")
    