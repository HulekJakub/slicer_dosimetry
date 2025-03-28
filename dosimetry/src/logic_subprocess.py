import sys
import os
import concurrent.futures
import concurrent
from src.optimize import optimize
from src.utils import parrarelize_processes
import json
import SimpleITK as sitk
import numpy as np


def run_dosimetry(parameters):
    sampleImgSITK = sitk.ReadImage(parameters["sampleRegionFilePath"])
    sampleImg = sitk.GetArrayFromImage(sampleImgSITK)
    args_list = [(sampleImg[y], parameters) for y in range(sampleImg.shape[0])]
    results_sample = {}

    to_do = len(args_list)
    done = 0
    for id, result in parrarelize_processes(
        optimize, args_list, n_executors=parameters["number_of_processes"]
    ):
        done += 1
        results_sample[id] = result

        print(f"progress;{done/to_do}", flush=True)

    sample_result_image = np.stack(
        [results_sample[i] for i in sorted(results_sample.keys())], axis=0
    )
    sample_result_SITK = sitk.GetImageFromArray(sample_result_image)
    sample_filename = os.path.join(parameters["tempPath"], "dosimetry_result.nii")
    sitk.WriteImage(sample_result_SITK, sample_filename)

    print(f"sample;{sample_filename}", flush=True)


def run_dosimetry_with_recalibration(parameters):
    sampleImgSITK = sitk.ReadImage(parameters["sampleRegionFilePath"])
    sampleImg = sitk.GetArrayFromImage(sampleImgSITK)
    args_list = [(sampleImg[y], parameters) for y in range(sampleImg.shape[0])]

    control_start_id = len(args_list)
    controlImgSITK = sitk.ReadImage(parameters["controlRegionFilePath"])
    controlImg = sitk.GetArrayFromImage(controlImgSITK)
    args_list.extend([(controlImg[y], parameters) for y in range(controlImg.shape[0])])

    recalibration_start_id = len(args_list)
    recalibrationImgSITK = sitk.ReadImage(parameters["recalibrationRegionFilePath"])
    recalibrationImg = sitk.GetArrayFromImage(recalibrationImgSITK)
    args_list.extend(
        [(recalibrationImg[y], parameters) for y in range(recalibrationImg.shape[0])]
    )

    results_sample = {}
    results_control = {}
    results_recalibration = {}

    to_do = len(args_list)
    done = 0
    for id, result in parrarelize_processes(
        optimize, args_list, n_executors=parameters["number_of_processes"]
    ):
        done += 1
        if id < control_start_id:
            results_sample[id] = result
        elif id >= control_start_id and id < recalibration_start_id:
            results_control[id] = result
        else:
            results_recalibration[id] = result

        print(f"progress;{done/to_do}", flush=True)

    sample_result_image = np.stack(
        [results_sample[i] for i in sorted(results_sample.keys())], axis=0
    )
    sample_result_SITK = sitk.GetImageFromArray(sample_result_image)
    sample_filename = os.path.join(parameters["tempPath"], "dosimetry_result.nii")
    sitk.WriteImage(sample_result_SITK, sample_filename)

    print(f"sample;{sample_filename}", flush=True)

    control_result_image = np.stack(
        [results_control[i] for i in sorted(results_control.keys())], axis=0
    )
    recalibration_result_image = np.stack(
        [results_recalibration[i] for i in sorted(results_recalibration.keys())], axis=0
    )

    print(f"control_mean;{control_result_image.mean()}", flush=True)
    print(f"control_std;{control_result_image.std()}", flush=True)
    print(f"recalibration_mean;{recalibration_result_image.mean()}", flush=True)
    print(f"recalibration_std;{recalibration_result_image.std()}", flush=True)


if __name__ == "__main__":
    parameters_path = sys.argv[1]
    with open(parameters_path, "r") as f:
        parameters = json.load(f)
    with_recalibration = (
        "controlRegionFilePath" in parameters
        and "recalibrationRegionFilePath" in parameters
    )

    if with_recalibration:
        run_dosimetry_with_recalibration(parameters)
    else:
        run_dosimetry(parameters)
