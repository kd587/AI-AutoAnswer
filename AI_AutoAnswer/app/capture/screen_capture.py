from dataclasses import dataclass

import cv2
import mss
import numpy as np

from app.automation.coordinate_mapper import Rect
from app.automation.window_manager import TargetWindow, ensure_target


@dataclass
class Capture:
    image: np.ndarray
    screen_rect: Rect


class ScreenCaptureEngine:
    def capture(self, target: TargetWindow) -> Capture:
        rect = ensure_target(target)
        with mss.mss() as camera:
            raw = np.asarray(camera.grab({"left": rect.left, "top": rect.top,
                                          "width": rect.width, "height": rect.height}))
        image = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if gray.std() < 2 or gray.mean() < 2:
            raise RuntimeError("Screenshot is blank or protected")
        return Capture(image, rect)


def preprocess(image: np.ndarray, crop: Rect | None = None,
               denoise: bool = False, sharpen: bool = False) -> np.ndarray:
    if crop is not None:
        if crop.left < 0 or crop.top < 0 or crop.width <= 0 or crop.height <= 0:
            raise ValueError("Invalid crop rectangle")
        image = image[crop.top:crop.top + crop.height,
                      crop.left:crop.left + crop.width]
        if image.size == 0:
            raise ValueError("Crop outside image")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(gray)
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, h=8)
    if sharpen:
        gray = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
    return gray


def detect_text_regions(image: np.ndarray) -> list[Rect]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 21, 10)
    joined = cv2.morphologyEx(binary, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3)))
    contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = [Rect(x, y, width, height) for contour in contours
               for x, y, width, height in [cv2.boundingRect(contour)]
               if width >= 20 and height >= 8]
    return sorted(regions, key=lambda rect: (rect.top, rect.left))
