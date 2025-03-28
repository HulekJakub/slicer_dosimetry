import concurrent.futures
import concurrent


def parrarelize_processes(function, args_list, n_executors=5):
    assert n_executors < 30
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(n_executors, len(args_list))
    ) as executor:
        future_to_id = {
            executor.submit(function, *args): id for id, args in enumerate(args_list)
        }
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
    col, row = point
    value = 0
    x_ras = image_origin[0] - col * image_spacing[0]
    y_ras = image_origin[1] - row * image_spacing[1]
    z_ras = image_origin[2] - value * image_spacing[2]

    return x_ras, y_ras, z_ras
