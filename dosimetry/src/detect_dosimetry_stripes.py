import cv2
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy


def binarize_stripes(stripes_raw):
    stripes_gray = cv2.cvtColor(stripes_raw, cv2.COLOR_BGR2GRAY)
    stripes_blured = cv2.GaussianBlur(stripes_gray, (5, 5), 0)
    _, stripes_binarized = cv2.threshold(
        stripes_blured, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV
    )

    return stripes_binarized


def find_n_contours(stripes_binarized, n=3):
    contours, _ = cv2.findContours(
        stripes_binarized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours_sorted = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)
    return contours_sorted[:n]


def label_contours(stripes_raw, contours):
    valued_contours = []
    for contour in contours:
        M = cv2.moments(contour)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        mean = np.mean(stripes_raw[cy - 10 : cy + 10, cx - 10 : cx + 10])

        black_canvas = np.zeros_like(stripes_raw).astype(np.uint8)
        cv2.drawContours(black_canvas, [contour], -1, (255, 255, 255), cv2.FILLED)
        var = np.var(stripes_raw[black_canvas == 255])

        valued_contours.append((contour, mean, var))

    valued_contours = sorted(valued_contours, key=lambda x: cv2.contourArea(x[0]), reverse=True)
    result = {"sample": valued_contours[0][0]}
    if len(valued_contours) > 1:
        valued_contours = sorted(valued_contours[1:], key=lambda x: x[1], reverse=True)
        result["control"] = valued_contours[0][0]
        result["recalibration"] = valued_contours[1][0]

    return result


def find_maximal_inscribed_square(bin, contour):
    mask = np.zeros_like(bin).astype(np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)  # Fill the contour

    dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

    # Find the maximum inscribed square
    max_area = 0
    best_rect = None
    h, w = dist_transform.shape
    a = 0

    # Iterate through possible squares
    for y in range(h):
        for x in range(w):
            if dist_transform[y, x] > 0:
                for rect_w in range(int(dist_transform[y, x]) * 2, 0, -1):
                    rect_h = rect_w
                    x0 = x - rect_w // 2
                    y0 = y - rect_h // 2
                    x1 = x0 + rect_w
                    y1 = y0 + rect_h

                    if x0 >= 0 and y0 >= 0 and x1 < w and y1 < h:
                        if np.all(mask[y0:y1, x0:x1] == 255):
                            area = rect_w * rect_h
                            if area > max_area:
                                max_area = area
                                best_rect = (x0, y0, rect_w, rect_h)
                            break
    return best_rect


def detect_dosimetry_stripes(stripes_tiff, recalibration_stripes_present):
    dosimetry_uint8 = (stripes_tiff / 2**8).astype(np.uint8)
    stripes_binarized = binarize_stripes(stripes_tiff)
    contours = find_n_contours(
        stripes_binarized.astype(np.uint8), 3 if recalibration_stripes_present else 1
    )

    labelled_contours = label_contours(dosimetry_uint8, contours)
    best_rect = find_maximal_inscribed_square(
        stripes_binarized, labelled_contours["sample"]
    )

    x, y, rw, rh = best_rect
    roi_coordinates = {"sample": {"x": x + rw // 2, "y": y + rh // 2, "w": rw, "h": rh}}
    if recalibration_stripes_present:
        for name in ["control", "recalibration"]:
            M = cv2.moments(labelled_contours[name])
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            roi_coordinates[name] = {"x": cx, "y": cy}
    return roi_coordinates
