import numpy as np

from app.automation.coordinate_mapper import Rect
from app.capture.screen_capture import Capture
from app.recognition.ocr_engine import OCREngine


def _engine_with_lines(*texts):
    class FakePaddle:
        def ocr(self, image, cls=True):
            return [[([[0, i * 30], [200, i * 30], [200, i * 30 + 20], [0, i * 30 + 20]],
                      (text, 0.99)) for i, text in enumerate(texts)]]

    engine = OCREngine()
    engine._engine = FakePaddle()
    return engine


def test_browser_loading_note_about_final_submit_is_not_completion():
    shot = Capture(np.zeros((100, 200, 3), np.uint8), Rect(0, 0, 200, 100))
    observed = _engine_with_lines("正在加载下一题…", "无最终提交操作").read(shot)
    assert observed is None


def test_browser_completion_without_options_is_detected():
    shot = Capture(np.zeros((100, 200, 3), np.uint8), Rect(0, 0, 200, 100))
    observed = _engine_with_lines("练习完成", "任务完成").read(shot)
    assert observed is not None and observed.finished
