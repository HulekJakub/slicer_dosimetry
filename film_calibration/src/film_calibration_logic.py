import logging
from typing import Any, Dict
import os
import json
import slicer
from slicer.i18n import tr as _
from slicer.ScriptedLoadableModule import *

from slicer import vtkMRMLVectorVolumeNode
from src.marker_detection import markers_detection

import slicer.util
from src.film_calibration_parameter_node import film_calibrationParameterNode

#
# film_calibrationLogic
#

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


class film_calibrationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return film_calibrationParameterNode(super().getParameterNode())

    def detectStripes(
        self, inputImage: vtkMRMLVectorVolumeNode, calibrationFilePath: str
    ) -> Dict[int, Dict[str, Any]]:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        """

        if not inputImage or not calibrationFilePath:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.time()
        logging.info(f"Processing started")
        img = slicer.util.arrayFromVolume(inputImage)
        img = img.reshape((img.shape[-3], img.shape[-2], img.shape[-1]))
        with open(calibrationFilePath, "r") as f:
            calibration_lines = [
                line.strip() for line in f.readlines() if line.strip() != ""
            ]
        output = markers_detection(img, calibration_lines)

        stopTime = time.time()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")

        return output

    def create_calibration(
        self, volume_node, roi_nodes, calibration_file_path, output_dir_path
    ):
        with open(calibration_file_path, "r") as f:
            calibration_lines = [
                line.strip() for line in f.readlines() if line.strip() != ""
            ]
        calibration_dict = {
            int(el[0].strip()): int(el[1].strip())
            for el in [line.split("-") for line in calibration_lines]
        }

        roi_pixel_data = self.__extract_roi_regions(volume_node, roi_nodes)

        roi_nodes_data_normalized = {k: v / 2**16 for k, v in roi_pixel_data.items()}
        roi_rgb_mean_normalized = {
            k: {c: v[:, :, i].mean() for i, c in enumerate(["r", "g", "b"])}
            for k, v in roi_nodes_data_normalized.items()
        }
        roi_rgb_std_normalized = {
            k: {c: v[:, :, i].std() for i, c in enumerate(["r", "g", "b"])}
            for k, v in roi_nodes_data_normalized.items()
        }

        interpolation_parameters = self.__calculate_interpolatation_parameters(
            calibration_dict, roi_rgb_mean_normalized, roi_rgb_std_normalized
        )
        self.__create_interpolation_plot(
            calibration_dict,
            roi_nodes_data_normalized,
            interpolation_parameters,
            output_dir_path,
        )

        with open(
            os.path.join(output_dir_path, "calibration_parameters.json"), "w"
        ) as f:
            json.dump(interpolation_parameters, f)

        return interpolation_parameters

    def __extract_roi_regions(self, volume_node, roi_nodes):
        """Extract regions in IJK format and convert to arrays."""
        # Get image properties
        image_data = slicer.util.arrayFromVolume(volume_node)  # Get numpy array
        image_data = image_data.reshape(
            (image_data.shape[-3], image_data.shape[-2], image_data.shape[-1])
        )

        spacing = volume_node.GetSpacing()
        origin = volume_node.GetOrigin()

        roi_regions = {}

        for key, roi_node in roi_nodes.items():
            bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            roi_node.GetBounds(bounds)

            # Convert RAS bounds to IJK
            col_max = int(round((origin[0] - bounds[0]) / spacing[0]))
            col_min = int(round((origin[0] - bounds[1]) / spacing[0]))
            row_max = int(round((origin[1] - bounds[2]) / spacing[1]))
            row_min = int(round((origin[1] - bounds[3]) / spacing[1]))

            col_min = max(0, col_min)
            row_min = max(0, row_min)
            col_max = min(image_data.shape[1] - 1, col_max)
            row_max = min(image_data.shape[0] - 1, row_max)

            roi_pixels = image_data[row_min : row_max + 1, col_min : col_max + 1]

            roi_regions[key] = roi_pixels

        return roi_regions

    def __calculate_interpolatation_parameters(
        self, calibration_dict, roi_rgb_mean_normalized, roi_rgb_std_normalized
    ):
        def model_func(x, a, b, c):
            return (a + b * x) / (c + x)

        interpolation_parameters = {}
        x_data = np.array(list(calibration_dict.values()))
        for color in ["r", "g", "b"]:
            sigma = np.array(
                [
                    color_values[color]
                    for color_values in roi_rgb_std_normalized.values()
                ]
            )
            y_median = np.array(
                [
                    color_values[color]
                    for color_values in roi_rgb_mean_normalized.values()
                ]
            )

            initial_guess = [0.5, -0.001, 1]

            popt, _ = curve_fit(
                model_func, x_data, y_median, p0=initial_guess, sigma=sigma
            )
            fitted_a, fitted_b, fitted_c = popt

            interpolation_parameters[color] = {
                "a": fitted_a,
                "b": fitted_b,
                "c": fitted_c,
            }
        return interpolation_parameters

    def __create_interpolation_plot(
        self,
        calibration_dict,
        roi_nodes_data_normalized,
        interpolation_parameters,
        output_dir_path,
    ):
        def model_func(x, a, b, c):
            return (a + b * x) / (c + x)

        x_data = np.array(list(calibration_dict.values()))
        plt.figure(figsize=(10, 8))
        for i, color in enumerate(["r", "g", "b"]):
            y_data_list = [
                color_values[:, :, i].flatten()
                for color_values in roi_nodes_data_normalized.values()
            ]
            x_fit = np.linspace(min(x_data), max(x_data), 200)
            y_fit = model_func(
                x_fit,
                interpolation_parameters[color]["a"],
                interpolation_parameters[color]["b"],
                interpolation_parameters[color]["c"],
            )

            # Create boxplot at each x_data point
            for x, y_list in zip(x_data, y_data_list):
                plt.boxplot(
                    y_list,
                    positions=[x],
                    widths=max(x_data) / len(x_data) / 4,
                    vert=True,
                    patch_artist=True,
                    boxprops=dict(facecolor=color, alpha=0.5),
                    capprops=dict(color=color),
                    whiskerprops=dict(color=color),
                    flierprops=dict(marker=".", color=color, alpha=0.07),
                    medianprops=dict(color="black"),
                )

            plt.plot(x_fit, y_fit, f"{color}-", label=f"Fitted curve ({color})")

        plt.xlabel("x")
        plt.ylabel("y")
        plt.legend()
        plt.title("Interpolation with y = (a + b*x) / (c + x)")
        plt.savefig(os.path.join(output_dir_path, "calibration_plot.png"))
        return
