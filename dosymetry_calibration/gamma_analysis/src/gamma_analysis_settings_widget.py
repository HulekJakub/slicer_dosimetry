import os
import json
import qt
import slicer

DEFAULT_SETTINGS = {
    "dose": '3',
    "dose_threshold": '20',
    "dta": '3',
}

SETTINGS_LABELS = {
    "dose": 'Dose [%]',
    "dose_threshold": 'Dose threhold [%]',
    "dta": 'DTA [mm]',
}

SETTINGS_PREPROCESSING = {
    "dose": lambda x: int(x),
    "dose_threshold": lambda x: int(x),
    "dta": lambda x: float(x),
}

class GammaAnalysisSettingsWidget(object):
    def __init__(self, parentWidget=None):
        # Directory to save presets relative to this file.
        self.presetsDir = os.path.join(os.path.dirname(__file__), '..', "presets")
        if not os.path.exists(self.presetsDir):
            os.makedirs(self.presetsDir)
        
        # Code-defined list of labels

        self.textInputs = {}  # Dictionary to hold QLineEdit widgets keyed by label
        self.default_settings = DEFAULT_SETTINGS
        self.settings_labels = SETTINGS_LABELS
        self.settings_preprocessing = SETTINGS_PREPROCESSING
        self.setupUI(parentWidget)

    def setupUI(self, parentWidget):
        # Create a widget to hold our controls
        self.widget = qt.QWidget(parentWidget)
        self.layout = qt.QFormLayout(self.widget)

        # Create a text input for each label
        for key in self.default_settings.keys():
            lineEdit = qt.QLineEdit()
            self.layout.addRow(qt.QLabel(self.settings_labels[key] + ':'), lineEdit)
            self.textInputs[key] = lineEdit

        # Add a dropdown to list and load saved presets
        self.presetComboBox = qt.QComboBox()
        self.layout.addRow(qt.QLabel("Load Preset:"), self.presetComboBox)
        self.presetComboBox.connect('currentIndexChanged(QString)', self.onPresetSelected)
        
        # Add a text input for naming the preset
        self.presetNameLineEdit = qt.QLineEdit()
        self.layout.addRow(qt.QLabel("Preset Name:"), self.presetNameLineEdit)

        # Add a button to save the current settings as a preset
        self.saveButton = qt.QPushButton("Save Preset")
        self.layout.addWidget(self.saveButton)
        self.saveButton.connect('clicked()', self.onSavePreset)

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
            for key, lineEdit in self.textInputs.items():
                lineEdit.text = self.default_settings[key]

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


    def getData(self):
        settings = {}
        errors = []
        for label, lineEdit in self.textInputs.items():
            try:
                settings[label] = self.settings_preprocessing[label](lineEdit.text)
            except:
                errors.append(f"{self.settings_labels[label]} is invalid.")
        if len(errors) > 0:
            raise ValueError('\n'.join(errors))
        return settings
