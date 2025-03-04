import os
import json
import qt
import slicer

DEFAULT_SETTINGS = {
    "a": '1',
    "b": '2',
    "c": '3'
}

class DosimetrySettingsWidget(object):
    def __init__(self, parentWidget=None):
        # Directory to save presets relative to this file.
        self.presetsDir = os.path.join(os.path.dirname(__file__), '..', "presets")
        if not os.path.exists(self.presetsDir):
            os.makedirs(self.presetsDir)
        
        # Code-defined list of labels
        self.labels = list(DEFAULT_SETTINGS.keys())
        self.textInputs = {}  # Dictionary to hold QLineEdit widgets keyed by label
        
        self.setupUI(parentWidget)

    def setupUI(self, parentWidget):
        # Create a widget to hold our controls
        self.widget = qt.QWidget(parentWidget)
        self.layout = qt.QFormLayout(self.widget)

        # Create a text input for each label
        for label in self.labels:
            lineEdit = qt.QLineEdit()
            self.layout.addRow(qt.QLabel(label + ':'), lineEdit)
            self.textInputs[label] = lineEdit

        # Add a text input for naming the preset
        self.presetNameLineEdit = qt.QLineEdit()
        self.layout.addRow(qt.QLabel("Preset Name:"), self.presetNameLineEdit)

        # Add a button to save the current settings as a preset
        self.saveButton = qt.QPushButton("Save Preset")
        self.layout.addWidget(self.saveButton)
        self.saveButton.connect('clicked()', self.onSavePreset)

        # Add a dropdown to list and load saved presets
        self.presetComboBox = qt.QComboBox()
        self.layout.addRow(qt.QLabel("Load Preset:"), self.presetComboBox)
        self.presetComboBox.connect('currentIndexChanged(QString)', self.onPresetSelected)

        # Load any previously saved presets into the dropdown
        self.loadPresetList()

    def onSavePreset(self):
        # Get the preset name from the text box
        presetName = self.presetNameLineEdit.text.strip()
        if not presetName:
            qt.QMessageBox.warning(slicer.util.mainWindow(), "Warning", "Please enter a preset name")
            return
        
        if presetName == 'default':
            qt.QMessageBox.warning(slicer.util.mainWindow(), "Warning", "default is forbidden")
            return

        # Gather all the settings from the text inputs into a dictionary
        presetData = {}
        for label, lineEdit in self.textInputs.items():
            presetData[label] = lineEdit.text

        # Save the dictionary as a JSON file in the presets directory
        presetFile = os.path.join(self.presetsDir, presetName + ".json")
        try:
            with open(presetFile, "w") as f:
                json.dump(presetData, f, indent=4)
            qt.QMessageBox.information(slicer.util.mainWindow(), "Info", "Preset saved successfully.")
        except Exception as e:
            qt.QMessageBox.critical(slicer.util.mainWindow(), "Error", "Failed to save preset: " + str(e))
        
        # Refresh the dropdown list to include the new preset
        self.loadPresetList()

    def loadPresetList(self):
        # Clear the combo box and load all JSON files from the presets directory
        self.presetComboBox.clear()
        self.presetComboBox.addItems(['default'])
        if not os.path.exists(self.presetsDir):
            return

        presetFiles = [f for f in os.listdir(self.presetsDir) if f.endswith(".json")]
        presetNames = [os.path.splitext(f)[0] for f in presetFiles]
        self.presetComboBox.addItems(presetNames)

    def onPresetSelected(self, presetName):
        if not presetName:
            return
        if presetName == 'default':
            for label, lineEdit in self.textInputs.items():
                lineEdit.text = DEFAULT_SETTINGS[label]

        # Construct the file path and load the preset if it exists
        presetFile = os.path.join(self.presetsDir, presetName + ".json")
        if os.path.exists(presetFile):
            try:
                with open(presetFile, "r") as f:
                    presetData = json.load(f)
                # Update each text input with the saved value
                for label, lineEdit in self.textInputs.items():
                    if label in presetData:
                        lineEdit.text = presetData[label]
            except Exception as e:
                qt.QMessageBox.critical(slicer.util.mainWindow(), "Error", "Failed to load preset: " + str(e))


    def getTextData(self):
        settings = {}
        for label, lineEdit in self.textInputs.items():
            settings[label] = lineEdit.text
        return settings
