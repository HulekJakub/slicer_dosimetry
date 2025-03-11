
import sys
import os
import concurrent.futures
import concurrent
from src.optimize import optimize
from src.utils import parrarelize_processes
import json
import SimpleITK as sitk
import numpy as np

if __name__ == "__main__":
    print("start")
    parameters_path = sys.argv[1]
    with open(parameters_path, 'r') as f:
        parameters = json.load(f)
    imgSITK = sitk.ReadImage(parameters['sampleRegionFilePath'])
    img = sitk.GetArrayFromImage(imgSITK)    
    
    args_list = [(img[y], parameters) for y in range(img.shape[0])]
    results = {}
    done = 0
    for id, result in parrarelize_processes(optimize, args_list, n_executors=parameters['number_of_processes']):
        done += 1
        results[id] = result
        print(done/img.shape[0], flush=True)
    
    full_image = np.stack([results[i] for i in sorted(results.keys())], axis=0)
    imSITK = sitk.GetImageFromArray(full_image)
    # np.save(os.path.join(parameters['outputDirectoryPath'], 'result_numpy.npy'), full_image)
    fname = os.path.join(parameters['tempPath'], 'result.nii.gz')
    sitk.WriteImage(imSITK, fname)
    print(fname, flush=True)
