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

from src.dosymetry_logic import dosymetryLogic
from src.dosymetry_parameter_node import dosymetryParameterNode
from src.dosymetry_settings_widget import DosimetrySettingsWidget

#
# dosymetryWidget
#


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

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = dosymetryLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

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
        self.settingsWidget = DosimetrySettingsWidget(parentWidget=self.settingsCollapsibleButton)
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
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanRun)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputImage:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLVectorVolumeNode")
            if firstVolumeNode:
                self._parameterNode.inputImage = firstVolumeNode

    def setParameterNode(self, inputParameterNode: Optional[dosymetryParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanRun)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanRun)
            self._checkCanRun()

    def _checkCanRun(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.inputImage is not None and self.stripesDetected:
            self.ui.runButton.toolTip = _("Run measurement")
            self.ui.runButton.enabled = True
        else:
            self.ui.runButton.toolTip = _("Select input volume, detect stripes and calibration file path")
            self.ui.runButton.enabled = False
            
        if self._parameterNode and self._parameterNode.inputImage is not None:
            self.ui.detectStripesButton.toolTip = _("Detect stripes")
            self.ui.detectStripesButton.enabled = True
        else:
            self.ui.detectStripesButton.toolTip = _("Select input volume")
            self.ui.detectStripesButton.enabled = False

    def onRunButton(self) -> None:
        if self.ui.calibrationFileSelector.currentPath == '':
            slicer.util.errorDisplay('Did not set calibration file!')
            return
        if self.ui.outputSelector.currentPath == '':
            slicer.util.errorDisplay('Did not set output directory!')
            return
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            print("running")
            volume_node = self.ui.inputImageSelector.currentNode()
            self.logic.run(volume_node, self.ui.calibrationFileSelector.currentPath, self.ui.outputSelector.currentPath)
                
            plot_path = os.path.join(self.ui.calibrationOutputSelector.currentPath, 'image_dosage.tif')
            slicer.util.loadVolume(plot_path, properties={'show': True})

    def onDetectStripes(self) -> None:
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            print("running")
            volume_node = self.ui.inputImageSelector.currentNode()
            roi_coordinates = self.logic.detectStripes(volume_node, self.ui.calibrationStripesIncludedCheckbox.checked)
            self.create_markups(roi_coordinates)
            self.stripesDetected = True
            self._checkCanRun()
            
    def create_markups(self, roi_coordinates):
        volume_node = self.ui.inputImageSelector.currentNode()  
        image_spacing = volume_node.GetSpacing()  # Get the spacing (x, y, z)
        image_origin = volume_node.GetOrigin()  # Get the origin (x, y, z)

        for node in self.roi_nodes.values():
            slicer.mrmlScene.RemoveNode(node)
        self.roi_nodes = {}
        
        x_ras, y_ras, z_ras = self.__point2d_to_ras([roi_coordinates['sample']['x'], roi_coordinates['sample']['y']], image_origin, image_spacing)
        sample_roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode")
        sample_roi_node.SetXYZ(x_ras, y_ras, z_ras)  
        sample_roi_node.SetSize(roi_coordinates['sample']['w'] * image_spacing[0], roi_coordinates['sample']['h'] * image_spacing[1], 1)
        sample_roi_node.SetName(f"sample")
        self.roi_nodes['sample'] = sample_roi_node  
        
        size = self.ui.roiSizeSelector.value 
        for name in ['control', 'max_dose']:
            if name in roi_coordinates:
                x_ras, y_ras, z_ras = self.__point2d_to_ras([roi_coordinates[name]['x'], roi_coordinates[name]['y']], image_origin, image_spacing)
                roi_node = self.__create_roi_node(x_ras, y_ras, z_ras, size, name)
                self.roi_nodes[name] = roi_node
            
            
    def __point2d_to_ras(self, point, image_origin, image_spacing):
        row, col = point[1], point[0]  # row and col represent image indices
        value = 0
        # Convert from image coordinates (row, col, value) to RAS coordinates
        x_ras = image_origin[0] - col * image_spacing[0]  # Convert column index to real world x
        y_ras = image_origin[1] - row * image_spacing[1]  # Convert row index to real world y
        z_ras = image_origin[2] - value * image_spacing[2]  # Convert value index to real world z
        
        return x_ras, y_ras, z_ras

    def __create_roi_node(self, x_ras, y_ras, z_ras, size, name):
        roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode")

        roi_node.SetXYZ(x_ras, y_ras, z_ras)  # Set center in RAS
        roi_node.SetSize(size, size, size)

        roi_node.SetName(f"{name}")
        return roi_node