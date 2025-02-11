import logging
import os
from typing import Annotated, Optional

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

from src.dosymetry_calibration_logic import dosymetryLogic
from src.dosymetry_calibration_parameter_node import dosymetryParameterNode

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
        # self.ui.generateCalibrationButton.connect("clicked(bool)", self.onGenerateCalibration)

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
        if self._parameterNode and self._parameterNode.inputImage is not None:
            self.ui.runButton.toolTip = _("Detect stripes")
            self.ui.runButton.enabled = True
        else:
            self.ui.runButton.toolTip = _("Select input volume and calibration file path")
            self.ui.runButton.enabled = False
    
    def onRunButton(self) -> None:
        """Run processing when user clicks "DetectStripes" button."""
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

            
    
