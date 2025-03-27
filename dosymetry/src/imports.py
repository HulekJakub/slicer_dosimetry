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
    import cv2

try:
    import cv2
except ModuleNotFoundError:
    slicer.util.pip_install("imageio")
    import cv2
