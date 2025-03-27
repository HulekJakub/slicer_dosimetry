import logging
import os
from typing import Annotated, Optional

import ctk
import slicer.util
import vtk
from vtk import vtkVector3d

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLVectorVolumeNode

try:
    import matplotlib
except ModuleNotFoundError:
    slicer.util.pip_install("matplotlib")
    import matplotlib

matplotlib.use("Agg")
import qt
from qt import QObject, Signal, Slot

from src.dosymetry_logic import dosymetryLogic
from src.dosymetry_parameter_node import dosymetryParameterNode
from src.dosymetry_settings_widget import DosymetrySettingsWidget
from src.utils import isFloat, point2dToRas
import SimpleITK as sitk


#
# DosymetryWidget
#
class Communicate(QObject):
    setProgressValue = Signal(int)


class dosymetryWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic: Optional[dosymetryLogic] = None
        self._parameterNode: Optional[dosymetryParameterNode] = None
        self._parameterNodeGuiTag = None
        self.stripesDetected = False
        self.roi_nodes = {}
        self.settingsWidget = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/dosymetry.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        self.logic = dosymetryLogic()

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose
        )
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose
        )

        # Buttons
        self.ui.runButton.connect("clicked(bool)", self.onRunButton)
        self.ui.detectStripesButton.connect("clicked(bool)", self.onDetectStripes)

        self.settingsCollapsibleButton = ctk.ctkCollapsibleButton()
        self.settingsCollapsibleButton.text = "Advanced Settings"
        self.settingsCollapsibleButton.checked = False
        self.layout.addWidget(self.settingsCollapsibleButton)

        # Create a layout for the collapsible button
        self.settingsFormLayout = qt.QFormLayout(self.settingsCollapsibleButton)

        # Initialize the settings widget and add it to the collapsible button layout
        self.settingsWidget = DosymetrySettingsWidget(
            parentWidget=self.settingsCollapsibleButton
        )
        self.settingsFormLayout.addWidget(self.settingsWidget.widget)
        # Make sure parameter node is initialized (needed for module reload)

        self.monitor = Communicate()
        self.monitor.setProgressValue.connect(self.setProgressBar)

        self.ui.progressBar.visible = False
        self.ui.controlResult.visible = False
        self.ui.recalibrationResult.visible = False
        self.initializeParameterNode()

    @Slot(int)
    def setProgressBar(self, value) -> None:
        self.ui.progressBar.setValue(value)
        slicer.util.resetSliceViews()

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

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputImage:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass(
                "vtkMRMLVectorVolumeNode"
            )
            if firstVolumeNode:
                self._parameterNode.inputImage = firstVolumeNode

    def setParameterNode(
        self, inputParameterNode: Optional[dosymetryParameterNode]
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
            and self._parameterNode.inputImage is not None
            and self.stripesDetected
        ):
            self.ui.runButton.toolTip = _("Run measurement")
            self.ui.runButton.enabled = True
        else:
            self.ui.runButton.toolTip = _(
                "Select input volume, detect stripes and calibration file path"
            )
            self.ui.runButton.enabled = False

        if self._parameterNode and self._parameterNode.inputImage is not None:
            self.ui.detectStripesButton.toolTip = _("Detect stripes")
            self.ui.detectStripesButton.enabled = True
        else:
            self.ui.detectStripesButton.toolTip = _("Select input volume")
            self.ui.detectStripesButton.enabled = False

    def __onRunButtonCheck(self):
        errors = []
        if self.ui.calibrationFileSelector.currentPath == "":
            errors.append("Did not set calibration file!")
        if self.ui.outputSelector.currentPath == "":
            errors.append("Did not set output directory!")
        if "sample" not in self.roi_nodes:
            errors.append("Sample was not detected!")
        if "control" in self.roi_nodes and self.ui.controlStripeDose.text == "":
            errors.append("Did not set control stripe dose!")
        if "control" in self.roi_nodes and not isFloat(self.ui.controlStripeDose.text):
            errors.append("Control stripe dose in not a number!")
        if (
            "recalibration" in self.roi_nodes
            and self.ui.recalibrationStripeDose.text == ""
        ):
            errors.append("Did not set recalibration stripe dose!")
        if "recalibration" in self.roi_nodes and not isFloat(
            self.ui.recalibrationStripeDose.text
        ):
            errors.append("Recalibration stripe dose in not a number!")
        return errors

    def onRunButton(self) -> None:
        errors = self.__onRunButtonCheck()

        try:
            advancedSettings = self.settingsWidget.getData()
        except ValueError as e:
            errors.append(e.args[0])
        if len(errors) > 0:
            slicer.util.errorDisplay("\n".join(errors))
            return

        with slicer.util.tryWithErrorDisplay(
            _("Failed to compute results."), waitCursor=True
        ):
            self.ui.progressBar.setValue(0)
            self.ui.progressBar.visible = True
            progressUpdateCallback = lambda x: self.monitor.setProgressValue.emit(
                int(x * 100)
            )

            input_volume_node = self.ui.inputImageSelector.currentNode()
            if "recalibration" in self.roi_nodes and "control" in self.roi_nodes:
                (
                    calibrated_image,
                    control_mean,
                    control_std,
                    recalibration_mean,
                    recalibration_std,
                ) = self.logic.runDosymetry(
                    input_volume_node,
                    self.ui.calibrationFileSelector.currentPath,
                    self.ui.outputSelector.currentPath,
                    self.roi_nodes,
                    advancedSettings,
                    float(self.ui.controlStripeDose.text),
                    float(self.ui.recalibrationStripeDose.text),
                    progressUpdate=progressUpdateCallback,
                )
            else:
                (
                    calibrated_image,
                    control_mean,
                    control_std,
                    recalibration_mean,
                    recalibration_std,
                ) = self.logic.runDosymetry(
                    input_volume_node,
                    self.ui.calibrationFileSelector.currentPath,
                    self.ui.outputSelector.currentPath,
                    self.roi_nodes,
                    advancedSettings,
                    progressUpdate=progressUpdateCallback,
                )

            for node in self.roi_nodes.values():
                slicer.mrmlScene.RemoveNode(node)
            self.roi_nodes = {}

            saveFileName = os.path.join(
                self.ui.outputSelector.currentPath, "dosymetry_result.nrrd"
            )
            saveImg = sitk.GetImageFromArray(calibrated_image)
            saveImg.SetOrigin(input_volume_node.GetOrigin())
            saveImg.SetSpacing(input_volume_node.GetSpacing())
            sitk.WriteImage(saveImg, saveFileName)
            if (
                control_mean is not None
                and control_std is not None
                and recalibration_mean is not None
                and recalibration_std is not None
            ):
                self.ui.controlResult.text = (
                    f"Control stripe mean: {control_mean:.2f}, std:{control_std:.2f}"
                )
                self.ui.recalibrationResult.text = f"Recalibration stripe mean: {recalibration_mean:.2f}, std:{recalibration_std:.2f}"
                self.ui.controlResult.visible = True
                self.ui.recalibrationResult.visible = True

            slicer.util.loadVolume(saveFileName, properties={"show": True})

    def onDetectStripes(self) -> None:
        with slicer.util.tryWithErrorDisplay(
            _("Failed to compute results."), waitCursor=True
        ):
            input_volume_node = self.ui.inputImageSelector.currentNode()
            roi_coordinates = self.logic.detectStripes(
                input_volume_node, self.ui.calibrationStripesIncludedCheckbox.checked
            )
            self.createMarkups(roi_coordinates)
            self.stripesDetected = True
            self._checkCanRun()

    def createMarkups(self, roi_coordinates):
        input_volume_node = self.ui.inputImageSelector.currentNode()
        image_spacing = input_volume_node.GetSpacing()
        image_origin = input_volume_node.GetOrigin()

        for node in self.roi_nodes.values():
            slicer.mrmlScene.RemoveNode(node)
        self.roi_nodes = {}

        x_ras, y_ras, z_ras = point2dToRas(
            [roi_coordinates["sample"]["x"], roi_coordinates["sample"]["y"]],
            image_origin,
            image_spacing,
        )
        sample_roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode")
        sample_roi_node.SetXYZ(x_ras, y_ras, z_ras)
        sample_roi_node.SetSize(
            roi_coordinates["sample"]["w"] * image_spacing[0],
            roi_coordinates["sample"]["h"] * image_spacing[1],
            1,
        )
        sample_roi_node.SetName(f"sample")
        self.roi_nodes["sample"] = sample_roi_node

        size = self.ui.roiSizeSelector.value
        for name in ["control", "recalibration"]:
            if name in roi_coordinates:
                x_ras, y_ras, z_ras = point2dToRas(
                    [roi_coordinates[name]["x"], roi_coordinates[name]["y"]],
                    image_origin,
                    image_spacing,
                )
                roi_node = self.__createRoiNode(x_ras, y_ras, z_ras, size, name)
                self.roi_nodes[name] = roi_node

    def __createRoiNode(self, x_ras, y_ras, z_ras, size, name):
        roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode")

        roi_node.SetXYZ(x_ras, y_ras, z_ras)
        roi_node.SetSize(size, size, size)

        roi_node.SetName(f"{name}")
        return roi_node
