import logging
import os
from typing import Annotated, Optional

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


from src.film_calibration_logic import film_calibrationLogic
from src.film_calibration_parameter_node import film_calibrationParameterNode

#
# film_calibrationWidget
#


class film_calibrationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic: Optional[film_calibrationLogic] = None
        self._parameterNode: Optional[film_calibrationParameterNode] = None
        self._parameterNodeGuiTag = None
        self.stripesDetected = False
        self.roi_nodes = {}

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/film_calibration.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = film_calibrationLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.detectStripesButton.connect("clicked(bool)", self.onDetectStripesButton)
        self.ui.generateCalibrationButton.connect("clicked(bool)", self.onGenerateCalibration)

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
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanDetectStripes)

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

    def setParameterNode(self, inputParameterNode: Optional[film_calibrationParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanDetectStripes)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanGenerateCalibration)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanDetectStripes)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanGenerateCalibration)
            self._checkCanDetectStripes()
            self._checkCanGenerateCalibration()

    def _checkCanDetectStripes(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.inputImage is not None and self._parameterNode.calibrationFilePath is not None:
            self.ui.detectStripesButton.toolTip = _("Detect stripes")
            self.ui.detectStripesButton.enabled = True
        else:
            self.ui.detectStripesButton.toolTip = _("Select input volume and calibration file path")
            self.ui.detectStripesButton.enabled = False
    
    def _checkCanGenerateCalibration(self, caller=None, event=None) -> None:
        if self.stripesDetected:
            self.ui.generateCalibrationButton.toolTip = _("Generate calibration")
            self.ui.generateCalibrationButton.enabled = True
        else:
            self.ui.generateCalibrationButton.toolTip = _("First detect stripes")
            self.ui.generateCalibrationButton.enabled = False

    def onDetectStripesButton(self) -> None:
        """Run processing when user clicks "DetectStripes" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            centers = self.logic.detectStripes(self.ui.inputImageSelector.currentNode(), self.ui.calibrationFileSelector.currentPath)
            self.centers = centers
            self.create_markups(centers)
            self.stripesDetected = True
            self._checkCanGenerateCalibration()
            
    def create_markups(self, centers):
        volume_node = self.ui.inputImageSelector.currentNode()  
        image_spacing = volume_node.GetSpacing()  # Get the spacing (x, y, z)
        image_origin = volume_node.GetOrigin()  # Get the origin (x, y, z)
        image_origin = (0.0, 0.0, 0.0)

        for node in self.roi_nodes.values():
            slicer.mrmlScene.RemoveNode(node)
        self.roi_nodes = {}
        
        for key, point in centers.items():
            row, col, value = point['y'], point['x'], 0  # row and col represent image indices
            
            # Convert from image coordinates (row, col, value) to RAS coordinates
            # Assuming the z-value is a direct translation for now
            x_ras = image_origin[0] - col * image_spacing[0]  # Convert column index to real world x
            y_ras = image_origin[1] - row * image_spacing[1]  # Convert row index to real world y
            z_ras = image_origin[2] + value * image_spacing[2]  # Convert value index to real world z

            # control_point = vtkVector3d(x_ras, y_ras, z_ras)
            # index = markup_node.AddControlPoint(control_point)
            # label = f"Point-{key}"  # Custom label
            # markup_node.SetNthControlPointLabel(index, label)
            # description = f"Value: {point['value']}"  # Custom description
            # markup_node.SetAttribute(f"Point-{key}-description", description)
            
            roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode")
            

            roi_node.SetXYZ(x_ras, y_ras, z_ras)  # Set center in RAS
            size = self.ui.roiSize.value # Size in mm
            roi_node.SetSize(size, size, size)

            roi_node.SetName(f"{key}")

            roi_node.SetAttribute(f"value", f"{point['value']}")
            roi_node.SetAttribute(f"x", f"{point['x']}")
            roi_node.SetAttribute(f"y", f"{point['y']}")
            self.roi_nodes[key] = roi_node

    def onGenerateCalibration(self):
        print("calibration")
        
