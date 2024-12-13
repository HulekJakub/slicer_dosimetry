
import slicer
try:
    import cv2
except ModuleNotFoundError:
  slicer.util.pip_install("opencv-contrib-python")
  import cv2

try:
    from scipy.optimize import curve_fit
except ModuleNotFoundError:
    slicer.util.pip_install("scipy")
    from scipy.optimize import curve_fit
    
try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:  
    slicer.util.pip_install("matplotlib")
    import matplotlib.pyplot as plt
