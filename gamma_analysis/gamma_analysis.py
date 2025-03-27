import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *


"""
    Imports for compatibility with Slicer
"""
from src.imports import *

from src.gamma_analysis_logic import *
from src.gamma_analysis_parameter_node import *
from src.gamma_analysis_widget import *

#
# GammaAnalysis
#


class gamma_analysis(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _(
            "Gamma Analysis"
        )  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Dosymetry")]
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


def registerSampleData():
    """Add data sets to Sample Data module."""
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    pass


class GammaAnalysisTest(ScriptedLoadableModuleTest):

    def setUp(self):
        pass

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_gamma_analyis()

    def test_gamma_analyis(self):
        self.delayDisplay("Starting the mock test")
        self.delayDisplay("Mock test passed")
