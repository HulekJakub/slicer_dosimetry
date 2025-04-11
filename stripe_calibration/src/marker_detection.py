import cv2
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy

font = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 0.7
fontColor = (255, 0, 0)
thickness = 2
lineType = 2


def binarize_stripes(stripes_raw, verbose=False):
    stripes_gray = cv2.cvtColor(stripes_raw, cv2.COLOR_BGR2GRAY)
    stripes_blured = cv2.GaussianBlur(stripes_gray, (5, 5), 0)
    _, stripes_binarized = cv2.threshold(
        stripes_blured, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV
    )
    if verbose:
        plt.imshow(stripes_binarized, "grey")
        plt.show()
    return stripes_binarized


def find_n_contours(stripes_binarized, stripes_raw, n, verbose=False):
    contours, _ = cv2.findContours(
        stripes_binarized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours_sorted = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)

    if verbose:
        stripes_raw_copy = deepcopy(stripes_raw)
        stripes_raw_copy = cv2.cvtColor(stripes_raw_copy, cv2.COLOR_BGR2RGB)
        rectangle_size = 20
        for contour in contours_sorted[:n]:
            M = cv2.moments(contour)
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            cv2.drawContours(stripes_raw_copy, [contour], -1, (200, 0, 0), 2)
            cv2.circle(stripes_raw_copy, (cx, cy), 5, (0, 160, 0), -1)
            cv2.rectangle(
                stripes_raw_copy,
                (cx - rectangle_size, cy - rectangle_size),
                (cx + rectangle_size, cy + rectangle_size),
                (0, 0, 160),
            )

        plt.imshow(stripes_raw_copy)
        plt.show()
    return contours_sorted[:n]


def match_contours_to_calibration(calibration_dict, stripes_raw, contours):
    valued_contours = []
    for contour in contours:
        M = cv2.moments(contour)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        value = np.mean(stripes_raw[cy - 10 : cy + 10, cx - 10 : cx + 10])
        valued_contours.append((contour, value))
    valued_contours = sorted(valued_contours, key=lambda x: x[1], reverse=True)

    contours_matched = {
        id: {"value": calibration_dict[id], "contour": valued_contour[0]}
        for id, valued_contour in zip(calibration_dict.keys(), valued_contours)
    }
    return contours_matched


def find_centers_of_dark_areas(contours_matched, stripes_raw):
    control_stripe_contour = contours_matched[0]["contour"]
    control_stripe_M = cv2.moments(control_stripe_contour)
    control_stripe_cx = int(control_stripe_M["m10"] / control_stripe_M["m00"])
    control_stripe_cy = int(control_stripe_M["m01"] / control_stripe_M["m00"])
    contours_matched[0]["cx"] = control_stripe_cx
    contours_matched[0]["cy"] = control_stripe_cy

    fill_value = int(
        np.mean(
            stripes_raw[
                control_stripe_cy - 10 : control_stripe_cy + 10,
                control_stripe_cx - 10 : control_stripe_cx + 10,
            ]
        )
    )

    for contour_id in contours_matched.keys():
        if contour_id == 0:
            continue
        contour = contours_matched[contour_id]["contour"]

        stripe_gray = cv2.cvtColor(stripes_raw, cv2.COLOR_BGR2GRAY)
        mask = np.zeros_like(stripe_gray)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        stripe_masked = cv2.bitwise_and(stripe_gray, stripe_gray, mask=mask)
        stripe_masked[stripe_masked == 0] = fill_value

        _, stripe_darker = cv2.threshold(
            stripe_masked, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV
        )
        darker_contours, _ = cv2.findContours(
            stripe_darker, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        darker_contours = sorted(
            darker_contours, reverse=True, key=lambda x: cv2.contourArea(x)
        )
        dark_contour = darker_contours[0]

        M = cv2.moments(dark_contour)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        contours_matched[contour_id]["cx"] = cx
        contours_matched[contour_id]["cy"] = cy
    return contours_matched


def prepare_output(contours_matched):
    return {
        id: {
            "x": contour_info["cx"],
            "y": contour_info["cy"],
            "value": contour_info["value"],
        }
        for id, contour_info in contours_matched.items()
    }


def plot_matched_dict(stripes_raw, contours_matched, centers_from_dict=False):
    stripes_raw_copy = deepcopy(stripes_raw)
    stripes_raw_copy = cv2.cvtColor(stripes_raw_copy, cv2.COLOR_BGR2RGB)

    for contour_id in contours_matched.keys():
        contour = contours_matched[contour_id]["contour"]
        if centers_from_dict:
            cx = contours_matched[contour_id]["cx"]
            cy = contours_matched[contour_id]["cy"]
        else:
            M = cv2.moments(contour)
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

        cv2.drawContours(stripes_raw_copy, [contour], -1, (200, 0, 0), 2)
        cv2.circle(stripes_raw_copy, (cx, cy), 5, (0, 160, 0), -1)
        rectangle_size = 20
        cv2.rectangle(
            stripes_raw_copy,
            (cx - rectangle_size, cy - rectangle_size),
            (cx + rectangle_size, cy + rectangle_size),
            (0, 0, 160),
        )
        cv2.putText(
            stripes_raw_copy,
            f"{contours_matched[contour_id]['value']}",
            (cx - 20, cy - 30),
            font,
            fontScale,
            fontColor,
            thickness,
            lineType,
        )
    plt.imshow(stripes_raw_copy)
    plt.show()


def markers_detection(stripes_tiff, calibration_lines):
    stripes_bgr = (stripes_tiff // 256).astype("uint8")
    calibration_dict = {
        int(el[0].strip()): float(el[1].strip())
        for el in [line.split("-") for line in calibration_lines]
    }

    stripes_binarized = binarize_stripes(stripes_bgr, False)

    contours = find_n_contours(
        stripes_binarized, stripes_bgr, len(calibration_dict), False
    )

    contours_matched = match_contours_to_calibration(
        calibration_dict, stripes_bgr, contours
    )

    contours_matched = find_centers_of_dark_areas(contours_matched, stripes_bgr)
    output = prepare_output(contours_matched)
    return output
