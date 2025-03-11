import concurrent.futures
import concurrent


def parrarelize_processes(function, args_list, n_executors=5):
    assert n_executors < 30
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(n_executors, len(args_list))) as executor:
        future_to_id = {executor.submit(function, *args): id for id, args in enumerate(args_list)}
        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            yield (id, future.result())
            del future_to_id[future]

def isFloat(x):
    try:
        float(x)
    except ValueError:
        return False
    return True

def point2dToRas(point, image_origin, image_spacing):
        col, row = point  # row and col represent image indices
        value = 0
        # Convert from image coordinates (row, col, value) to RAS coordinates
        x_ras = image_origin[0] - col * image_spacing[0]  # Convert column index to real world x
        y_ras = image_origin[1] - row * image_spacing[1]  # Convert row index to real world y
        z_ras = image_origin[2] - value * image_spacing[2]  # Convert value index to real world z
        
        return x_ras, y_ras, z_ras