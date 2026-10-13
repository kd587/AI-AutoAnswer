import cv2
import numpy as np

from app.automation.coordinate_mapper import Rect
from app.capture.screen_capture import detect_text_regions, preprocess


def test_preprocess_can_crop_and_sharpen_without_changing_input():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.putText(image, "A", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    original = image.copy()
    processed = preprocess(image, crop=Rect(20, 20, 60, 60), denoise=True, sharpen=True)
    assert processed.shape == (60, 60)
    assert np.array_equal(image, original)


def test_detect_text_regions_finds_printed_line():
    image = np.full((80, 240, 3), 255, dtype=np.uint8)
    cv2.putText(image, "QUESTION", (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    regions = detect_text_regions(image)
    assert any(region.width > 80 and region.height > 10 for region in regions)
