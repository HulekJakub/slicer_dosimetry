import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *


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
    import imageio
except ModuleNotFoundError:
    slicer.util.pip_install("imageio")

# from Testing.Python.example_test import *
from src.stripe_calibration_logic import *
from src.stripe_calibration_parameter_node import *
from src.stripe_calibration_widget import *

#
# stripe_calibration
#


class stripe_calibration(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _(
            "Stripe Calibration"
        )  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Dosimetry")]
        self.parent.dependencies = (
            []
        )  # TODO: add here list of module names that this module requires
        self.parent.contributors = [
            "Jakub Hulek (AGH University of Krakow)"
        ]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _(
            """I express my gratitude to Professor Zbisław Tabor from AGH University Of Krakow for help and materials provided"""
        )

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    pass


class stripe_calibrationTest(ScriptedLoadableModuleTest):

    def setUp(self):
        pass

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_stripe_calibration()

    def test_stripe_calibration(self):
        self.delayDisplay("Starting the mock test")
        self.delayDisplay("Mock test passed")
