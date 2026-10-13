import numpy as np

from app.automation.coordinate_mapper import Rect
from app.automation.windows_mcp_backend import parse_snapshot
from app.capture.screen_capture import Capture
from app.recognition.ocr_engine import OCREngine
from app.recognition.question_context import current_question
from app.recognition import uia_reader
from types import SimpleNamespace


TREE = '''UI Tree:
desktop
    ├── window "AI AutoAnswer · 本地网页模拟题库"
    │   ├── (300,100) text "20 道单选 + 10 道多选，测试识别"
    │   ├── (300,200) text "单选题"
    │   ├── (300,250) text "1. 哪一种数据结构遵循先进先出原则？"
    │   ├── (300,310) 单选按钮 "A. 栈" [action: click] [toggle:off]
    │   ├── (300,360) 单选按钮 "B. 队列" [action: click] [toggle:off]
    │   ├── (300,420) 按钮 "下一题 →" [action: click]
'''


def test_snapshot_ignores_global_single_multiple_summary():
    observed = parse_snapshot(TREE, "AI AutoAnswer · 本地网页模拟题库")
    assert observed.question_type == "single"
    assert observed.question == "1. 哪一种数据结构遵循先进先出原则？"


def test_ocr_ignores_global_single_multiple_summary(monkeypatch):
    texts = [(100, "20 道单选 + 10 道多选，测试识别"), (200, "单选题"),
             (250, "1. 哪一种数据结构遵循先进先出原则？"),
             (310, "A. 栈"), (360, "B. 队列"), (420, "下一题 →")]
    lines = []
    for y, value in texts:
        lines.append(([[100, y], [400, y], [400, y + 24], [100, y + 24]], (value, 0.99)))

    class FakePaddle:
        def ocr(self, image, cls=True):
            return [lines]

    monkeypatch.setattr("app.recognition.ocr_engine.preprocess", lambda image: image)
    engine = OCREngine()
    engine._engine = FakePaddle()
    observed = engine.read(Capture(np.ones((500, 500, 3), dtype=np.uint8), Rect(0, 0, 500, 500)))
    assert observed.question_type == "single"
    assert observed.question == "1. 哪一种数据结构遵循先进先出原则？"


def test_wrapped_simulator_heading_keeps_type_and_stem():
    question, kind = current_question([
        (60, "模拟练习 第 21 题 / 30：多选题。以下哪些属于 Python 内置容器？"),
        (95, "请结合图示及定义判断，并注意选项可能改变顺序。"),
    ])
    assert kind == "multiple"
    assert "多选题" in question
    assert "请结合图示" in question


def test_uia_radio_controls_override_page_summary(monkeypatch):
    class Control:
        def __init__(self, name, kind, y):
            self.name, self.element_info, self.y = name, SimpleNamespace(control_type=kind), y

        def window_text(self):
            return self.name

        def rectangle(self):
            return SimpleNamespace(left=100, top=self.y, width=lambda: 200, height=lambda: 25)

    controls = [Control("20 道单选 + 10 道多选", "Text", 100),
                Control("单选题", "Text", 200),
                Control("1. 哪一种结构先进先出？", "Text", 250),
                Control("A. 栈", "RadioButton", 310),
                Control("B. 队列", "RadioButton", 360)]
    monkeypatch.setattr(uia_reader, "Desktop", lambda backend: SimpleNamespace(
        window=lambda handle: SimpleNamespace(descendants=lambda: controls)))
    observed = uia_reader.UIAReader().read(SimpleNamespace(hwnd=99))
    assert observed.question_type == "single"
    assert observed.question == "1. 哪一种结构先进先出？"
