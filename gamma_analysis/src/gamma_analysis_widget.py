from typing import Annotated, Optional
import qt

import ctk
import slicer.util
import vtk

import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin


import matplotlib


matplotlib.use("Agg")

import vtk


from slicer import vtkMRMLScalarVolumeNode

from src.gamma_analysis_logic import gamma_analysisLogic
from src.gamma_analysis_settings_widget import GammaAnalysisSettingsWidget
from src.gamma_analysis_parameter_node import gamma_analysisParameterNode

#
# gamma_analysisWidget
#


class gamma_analysisWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic: Optional[gamma_analysisLogic] = None
        self._parameterNode: Optional[gamma_analysisParameterNode] = None
        self._parameterNodeGuiTag = None
        self.stripesDetected = False
        self.roi_nodes = {}
        self.settingsWidget = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/gamma_analysis.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        self.logic = gamma_analysisLogic()

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose
        )
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose
        )

        # Buttons
        self.ui.runButton.connect("clicked(bool)", self.onRunButton)

        self.settingsCollapsibleButton = ctk.ctkCollapsibleButton()
        self.settingsCollapsibleButton.text = "Advanced Settings"
        self.settingsCollapsibleButton.checked = True
        self.layout.addWidget(self.settingsCollapsibleButton)

        # Create a layout for the collapsible button
        self.settingsFormLayout = qt.QFormLayout(self.settingsCollapsibleButton)

        # Initialize the settings widget and add it to the collapsible button layout
        self.settingsWidget = GammaAnalysisSettingsWidget(
            parentWidget=self.settingsCollapsibleButton
        )
        self.settingsFormLayout.addWidget(self.settingsWidget.widget)
        # Make sure parameter node is initialized (needed for module reload)

        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanRun
            )

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(
        self, inputParameterNode: Optional[gamma_analysisParameterNode]
    ) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanRun
            )
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanRun
            )
            self._checkCanRun()

    def _checkCanRun(self, caller=None, event=None) -> None:
        if (
            self._parameterNode
            and self._parameterNode.dosimetryResultVolume is not None
            and self._parameterNode.rtDoseVolume is not None
        ):
            self.ui.runButton.toolTip = _("Compute gamma index")
            self.ui.runButton.enabled = True
        else:
            self.ui.runButton.toolTip = _("Select reference and evaluated volume nodes")
            self.ui.runButton.enabled = False

    def __onRunButtonCheck(self):
        errors = []
        if self.ui.rtPlanFileSelector.currentPath == "":
            errors.append("Did not set RT Plan File!")
        return errors

    def onRunButton(self) -> None:
        errors = self.__onRunButtonCheck()

        try:
            advancedSettings = self.settingsWidget.getData()
        except ValueError as e:
            errors.append(e.args[0])

        if (
            self._parameterNode is None
            or self._parameterNode.dosimetryResultVolume is None
            or self._parameterNode.rtDoseVolume is None
        ):
            errors.append("Select reference and evaluated volume nodes")

        if len(errors) > 0:
            slicer.util.errorDisplay("\n".join(errors))
            return

        with slicer.util.tryWithErrorDisplay(
            _("Failed to compute results."), waitCursor=True
        ):
            dose = advancedSettings["dose"]
            dose_threshold = advancedSettings["dose_threshold"]
            dta = advancedSettings["dta"]
            GPR, gammaImage, alignedRtDose = self.logic.runGammaAnalysis(
                self._parameterNode.dosimetryResultVolume,
                self._parameterNode.rtDoseVolume,
                self.ui.rtPlanFileSelector.currentPath,
                dose,
                dose_threshold,
                dta,
            )

            nodeName = "RegisteredTPSDose"
            registeredDose = self.__get_or_create_node(
                nodeName, "vtkMRMLScalarVolumeNode"
            )
            slicer.util.updateVolumeFromArray(registeredDose, alignedRtDose)
            registeredDose.SetOrigin(
                self._parameterNode.dosimetryResultVolume.GetOrigin()
            )
            registeredDose.SetSpacing(
                self._parameterNode.dosimetryResultVolume.GetSpacing()
            )

            nodeName = "GammaImage"
            gammaVolume = self.__get_or_create_node(nodeName, "vtkMRMLScalarVolumeNode")
            slicer.util.updateVolumeFromArray(gammaVolume, gammaImage)
            gammaVolume.SetOrigin(self._parameterNode.dosimetryResultVolume.GetOrigin())
            gammaVolume.SetSpacing(
                self._parameterNode.dosimetryResultVolume.GetSpacing()
            )
            slicer.app.layoutManager().sliceWidget(
                "Red"
            ).sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(
                gammaVolume.GetID()
            )
            sliceLogics = slicer.app.layoutManager().mrmlSliceLogics()
            for i in range(sliceLogics.GetNumberOfItems()):
                sliceLogic = sliceLogics.GetItemAsObject(i)
                if sliceLogic:
                    sliceLogic.FitSliceToAll()
            # CImg(alignedRtDose).display('registered TPS dose')
            # CImg(gammaImage).display('gamma image')
            self.ui.gammaLineEdit.text = f"{GPR:.2f}"

    def __get_or_create_node(self, nodeName, nodeClass):
        existingNode = slicer.mrmlScene.GetFirstNodeByName(nodeName)
        if existingNode:
            return existingNode
        else:
            return slicer.mrmlScene.AddNewNodeByClass(nodeClass, nodeName)
