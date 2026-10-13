import numpy as np
import threading
import time
from PySide6.QtCore import Qt

from app.ai.schema import AnswerPayload
from app.automation.coordinate_mapper import Rect
from app.automation.window_manager import TargetWindow
from app.core import controller as module
from app.recognition.models import LocatedOption, ObservedQuestion


def test_thirty_question_loop_handles_twenty_single_and_ten_multiple(monkeypatch):
    progress = {"index": 0, "clicks": 0, "next": 0}

    class Camera:
        def capture(self, target):
            return type("Shot", (), {"image": np.ones((20, 20, 3), dtype=np.uint8),
                                      "screen_rect": Rect(0, 0, 20, 20)})()

    class Reader:
        def read(self, target):
            if progress["index"] == 30:
                return ObservedQuestion("", "unknown", finished=True)
            number = progress["index"] + 1
            multiple = progress["index"] >= 20
            return ObservedQuestion(
                f"Question {number}", "multiple" if multiple else "single",
                {"A": LocatedOption("A", "wrong", Rect(0, 0, 10, 10)),
                 "B": LocatedOption("B", "right", Rect(10, 0, 10, 10)),
                 "C": LocatedOption("C", "right too", Rect(0, 10, 10, 10))},
                Rect(0, 10, 10, 10), source="uia")

    class Mouse:
        def click_option(self, target, option, expected_cursor=None):
            assert option.label in ({"A", "C"} if progress["index"] >= 20 else {"B"})
            progress["clicks"] += 1

        def click_next(self, target, observed):
            progress["next"] += 1
            progress["index"] += 1

    class Provider:
        price_per_million = (0.3, 1.2)
        usage = type("Usage", (), {"upper_cost_usd": 0.0, "calls": 0,
                                    "input_tokens": 0, "output_tokens": 0})()

        def analyze(self, observed, image, use_vision):
            self.usage.calls += 1
            multiple = progress["index"] >= 20
            return AnswerPayload(is_question=True, question_type="multiple" if multiple else "single",
                                 answers=["A", "C"] if multiple else ["B"], can_answer=True)

    class Database:
        def __init__(self): self.states = []
        def log(self, pid, state, question="", answers="", detail=""):
            self.states.append(state)

    monkeypatch.setattr(module, "ScreenCaptureEngine", Camera)
    monkeypatch.setattr(module, "UIAReader", Reader)
    monkeypatch.setattr(module, "OCREngine", Reader)
    monkeypatch.setattr(module, "MouseController", Mouse)
    monkeypatch.setattr(module, "ensure_target", lambda target: Rect(0, 0, 20, 20))
    monkeypatch.setattr(module.win32api, "GetCursorPos", lambda: (100, 100))
    database = Database()
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                         Provider(), database,
                                         module.RunLimits(max_questions=30, mode="auto"))
    worker.run()
    assert progress == {"index": 30, "clicks": 40, "next": 30}
    assert database.states[-1] == "FINISHED"


def test_api_failure_pauses_and_can_resume(monkeypatch):
    progress = {"next": False}

    class Camera:
        def capture(self, target):
            return type("Shot", (), {"image": np.ones((20, 20, 3), dtype=np.uint8),
                                      "screen_rect": Rect(0, 0, 20, 20)})()

    class Reader:
        def read(self, target):
            if progress["next"]:
                return ObservedQuestion("", "unknown", finished=True)
            return ObservedQuestion("Question", "single",
                {"A": LocatedOption("A", "wrong", Rect(0, 0, 10, 10)),
                 "B": LocatedOption("B", "right", Rect(10, 0, 10, 10))},
                Rect(0, 10, 10, 10), source="uia")

    class Mouse:
        def click_option(self, target, option, expected_cursor=None): pass
        def click_next(self, target, observed): progress["next"] = True

    class Provider:
        price_per_million = (0.3, 1.2)
        usage = type("Usage", (), {"upper_cost_usd": 0.0, "calls": 0,
                                    "input_tokens": 0, "output_tokens": 0})()

        def analyze(self, observed, image, use_vision):
            self.usage.calls += 1
            if self.usage.calls == 1:
                raise RuntimeError("temporary API failure")
            return AnswerPayload(is_question=True, question_type="single",
                                 answers=["B"], can_answer=True)

    class Database:
        def __init__(self): self.states = []
        def log(self, pid, state, question="", answers="", detail=""):
            self.states.append(state)

    monkeypatch.setattr(module, "ScreenCaptureEngine", Camera)
    monkeypatch.setattr(module, "UIAReader", Reader)
    monkeypatch.setattr(module, "OCREngine", Reader)
    monkeypatch.setattr(module, "MouseController", Mouse)
    monkeypatch.setattr(module, "ensure_target", lambda target: Rect(0, 0, 20, 20))
    monkeypatch.setattr(module.win32api, "GetCursorPos", lambda: (100, 100))
    database = Database()
    provider = Provider()
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                         provider, database,
                                         module.RunLimits(max_questions=1, mode="auto"))
    metrics = []
    worker.metrics.connect(lambda *values: metrics.append(values), Qt.DirectConnection)
    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()
    for _ in range(100):
        if worker.pause_event.is_set():
            break
        time.sleep(0.01)
    assert worker.pause_event.is_set() and thread.is_alive()
    worker.resume()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert provider.usage.calls == 2
    assert any(values[-1] == 1 for values in metrics)
    assert database.states[-1] == "FINISHED"


def test_cost_budget_stops_without_retry():
    class Provider:
        price_per_million = (0.3, 1.2)
        usage = type("Usage", (), {"upper_cost_usd": 1.0})()

    class Database:
        def __init__(self): self.states = []
        def log(self, pid, state, question="", answers="", detail=""):
            self.states.append(state)

    database = Database()
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                         Provider(), database,
                                         module.RunLimits(max_cost_usd=0.5, mode="auto"))
    worker.run()
    assert not worker.pause_event.is_set()
    assert database.states[-1] == "STOPPED"


def test_mcp_startup_failure_is_logged_and_runtime_closed():
    class Backend:
        closed = False
        def start(self):
            raise RuntimeError("stdio disconnected")
        def stop(self):
            self.closed = True

    class Provider:
        pass

    class Database:
        def __init__(self): self.states = []
        def log(self, pid, state, question="", answers="", detail=""):
            self.states.append((state, detail))

    backend = Backend()
    database = Database()
    worker = module.AutoTaskController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                       Provider(), database, module.RunLimits(), backend)
    worker.run()
    assert database.states[-1][0] == "ERROR"
    assert "stdio disconnected" in database.states[-1][1]
    assert backend.closed
    assert any(state == "TRACEBACK" and "self.backend.start()" in detail
               for state, detail in database.states)


def test_state_transition_logs_previous_stage_duration(monkeypatch):
    class Database:
        def __init__(self): self.rows = []
        def log(self, pid, state, question="", answers="", detail=""):
            self.rows.append((state, detail))

    database = Database()
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                         object(), database, module.RunLimits())
    worker._stage_started_at = 20.0
    monkeypatch.setattr(module.time, "monotonic", lambda: 22.5)
    worker._step(module.RunState.RECOGNIZE)
    assert any(state == "CAPTURE" and "耗时=2.50s" in detail
               for state, detail in database.rows)


def test_target_scoped_uia_precedes_ocr_after_mcp_snapshot_miss(monkeypatch):
    found = ObservedQuestion("模拟练习 第 1 题：单选题", "single",
                             {"A": LocatedOption("A", "栈", Rect(0, 0, 10, 10)),
                              "B": LocatedOption("B", "队列", Rect(20, 0, 10, 10))},
                             source="uia")
    class Backend:
        last_snapshot_text = ""
        def read(self, target):
            return None

    class UIA:
        def read(self, target):
            return found

    class OCR:
        def read(self, shot):
            raise AssertionError("OCR should not run after target UIA succeeds")

    monkeypatch.setattr(module, "UIAReader", UIA)
    monkeypatch.setattr(module, "OCREngine", OCR)
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                         object(), object(), module.RunLimits(), Backend())
    assert worker._recognize(object()) is found


def test_browser_recognition_uses_captured_ocr_before_desktop_snapshot(monkeypatch):
    found = ObservedQuestion("模拟练习 第 1 题", "single",
                             {"A": LocatedOption("A", "栈", Rect(0, 0, 10, 10)),
                              "B": LocatedOption("B", "队列", Rect(20, 0, 10, 10))},
                             source="ocr")
    class Backend:
        last_snapshot_text = ""
        def read(self, target):
            raise AssertionError("A full-desktop Snapshot must not precede browser OCR")

    class OCR:
        def read(self, shot):
            return found

    monkeypatch.setattr(module, "OCREngine", OCR)
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "msedge.exe"),
                                         object(), object(), module.RunLimits(), Backend())
    assert worker._recognize(object()) is found


def test_waiting_for_new_question_does_not_scan_full_desktop(monkeypatch):
    class Backend:
        last_snapshot_text = ""
        def read(self, target):
            raise AssertionError("Do not use desktop Snapshot while the next page loads")

    class UIA:
        def read(self, target):
            return None

    class OCR:
        def read(self, shot):
            return None

    monkeypatch.setattr(module, "UIAReader", UIA)
    monkeypatch.setattr(module, "OCREngine", OCR)
    worker = module.AutomationController(TargetWindow(1, 2, "fixture", "fixture.exe"),
                                         object(), object(), module.RunLimits(), Backend())
    worker.machine.state = module.RunState.WAIT
    assert worker._recognize(object()) is None
