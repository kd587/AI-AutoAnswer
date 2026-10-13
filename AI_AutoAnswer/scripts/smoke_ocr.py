"""Render the Qt fixture to memory and exercise PaddleOCR without desktop focus."""
import cv2
import numpy as np
import sys
from PySide6.QtWidgets import QApplication

from app.automation.coordinate_mapper import Rect
from app.capture.screen_capture import Capture, preprocess
from app.recognition.ocr_engine import OCREngine
from test_client.client import PracticeClient


def main():
    app = QApplication([])
    client = PracticeClient(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    client.show()
    app.processEvents()
    image = client.grab().toImage()
    ptr = image.constBits()
    buffer = np.frombuffer(ptr, np.uint8).reshape(image.height(), image.bytesPerLine())
    pixels = buffer[:, :image.width() * 4].reshape(image.height(), image.width(), 4)
    bgr = cv2.cvtColor(pixels, cv2.COLOR_BGRA2BGR)
    engine = OCREngine()
    result = engine.read(Capture(bgr, Rect(0, 0, image.width(), image.height())))
    if client.index >= client.total:
        assert result is not None and result.finished
        print("OCR completion page OK")
        client.close()
        return
    if result is None or len(result.options) < 4:
        print("OCR raw:", [(line[1][0], round(line[1][1], 2))
                           for line in (engine._get_engine().ocr(preprocess(bgr), cls=True)[0] or [])])
        print("OCR original:", [(line[1][0], round(line[1][1], 2))
                                for line in (engine._get_engine().ocr(bgr, cls=True)[0] or [])])
    assert result is not None
    assert len(result.options) >= 4, result
    assert result.next_rect is not None
    expected_type = "multiple" if client.index >= 20 else "single"
    assert result.question_type == expected_type, (result.question_type, result.question)
    print("OCR smoke OK:", result.question_type, result.question, result.option_text)
    client.close()


if __name__ == "__main__":
    main()
