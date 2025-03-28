import os
import json
import qt
import slicer

DEFAULT_SETTINGS = {
    "median_kernel_size": "0",
    "tolerance": "0.01",
    "max_iterations": "1000",
    "normalization_factor": "65536",
    "max_dose": "3000",
    "number_of_processes": "6",
}

SETTINGS_LABELS = {
    "median_kernel_size": "Median kernel size (0 for no filter)",
    "tolerance": "Tolerance",
    "max_iterations": "Max number of iterations",
    "normalization_factor": "Image normalization factor",
    "max_dose": "Maximal possible dose",
    "number_of_processes": "Number of workers",
}

SETTINGS_PREPROCESSING = {
    "median_kernel_size": lambda x: int(x),
    "tolerance": lambda x: float(x),
    "max_iterations": lambda x: int(x),
    "normalization_factor": lambda x: int(x),
    "max_dose": lambda x: float(x),
    "number_of_processes": lambda x: int(x),
}


class DosimetrySettingsWidget(object):
    def __init__(self, parentWidget=None):
        self.presetsDir = os.path.join(os.path.dirname(__file__), "..", "presets")
        if not os.path.exists(self.presetsDir):
            os.makedirs(self.presetsDir)

        self.textInputs = {}
        self.default_settings = DEFAULT_SETTINGS
        self.settings_labels = SETTINGS_LABELS
        self.settings_preprocessing = SETTINGS_PREPROCESSING
        self.setupUI(parentWidget)

    def setupUI(self, parentWidget):
        self.widget = qt.QWidget(parentWidget)
        self.layout = qt.QFormLayout(self.widget)

        for key in self.default_settings.keys():
            lineEdit = qt.QLineEdit()
            self.layout.addRow(qt.QLabel(self.settings_labels[key] + ":"), lineEdit)
            self.textInputs[key] = lineEdit

        self.presetComboBox = qt.QComboBox()
        self.layout.addRow(qt.QLabel("Load Preset:"), self.presetComboBox)
        self.presetComboBox.connect(
            "currentIndexChanged(QString)", self.onPresetSelected
        )

        self.presetNameLineEdit = qt.QLineEdit()
        self.layout.addRow(qt.QLabel("Preset Name:"), self.presetNameLineEdit)

        self.saveButton = qt.QPushButton("Save Preset")
        self.layout.addWidget(self.saveButton)
        self.saveButton.connect("clicked()", self.onSavePreset)

        self.loadPresetList()

    def onSavePreset(self):
        presetName = self.presetNameLineEdit.text.strip()
        if not presetName:
            qt.QMessageBox.warning(
                slicer.util.mainWindow(), "Warning", "Please enter a preset name"
            )
            return

        if presetName == "default":
            qt.QMessageBox.warning(
                slicer.util.mainWindow(), "Warning", "default is forbidden"
            )
            return

        presetData = {}
        for label, lineEdit in self.textInputs.items():
            presetData[label] = lineEdit.text

        presetFile = os.path.join(self.presetsDir, presetName + ".json")
        try:
            with open(presetFile, "w") as f:
                json.dump(presetData, f, indent=4)
            qt.QMessageBox.information(
                slicer.util.mainWindow(), "Info", "Preset saved successfully."
            )
        except Exception as e:
            qt.QMessageBox.critical(
                slicer.util.mainWindow(), "Error", "Failed to save preset: " + str(e)
            )

        self.loadPresetList()

    def loadPresetList(self):
        self.presetComboBox.clear()
        self.presetComboBox.addItems(["default"])
        if not os.path.exists(self.presetsDir):
            return

        presetFiles = [f for f in os.listdir(self.presetsDir) if f.endswith(".json")]
        presetNames = [os.path.splitext(f)[0] for f in presetFiles]
        self.presetComboBox.addItems(presetNames)

    def onPresetSelected(self, presetName):
        if not presetName:
            return
        if presetName == "default":
            for key, lineEdit in self.textInputs.items():
                lineEdit.text = self.default_settings[key]

        presetFile = os.path.join(self.presetsDir, presetName + ".json")
        if os.path.exists(presetFile):
            try:
                with open(presetFile, "r") as f:
                    presetData = json.load(f)
                for label, lineEdit in self.textInputs.items():
                    if label in presetData:
                        lineEdit.text = presetData[label]
            except Exception as e:
                qt.QMessageBox.critical(
                    slicer.util.mainWindow(),
                    "Error",
                    "Failed to load preset: " + str(e),
                )

    def getData(self):
        settings = {}
        errors = []
        for label, lineEdit in self.textInputs.items():
            try:
                settings[label] = self.settings_preprocessing[label](lineEdit.text)
            except:
                errors.append(f"{self.settings_labels[label]} is invalid.")
        if len(errors) > 0:
            raise ValueError("\n".join(errors))
        return settings
