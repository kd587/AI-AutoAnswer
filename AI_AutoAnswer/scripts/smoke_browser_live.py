"""Run one real Windows-MCP selection against a fresh local Edge quiz window.

Uses a deterministic answer to isolate screenshot/OCR/click behavior from the
DeepSeek service. The script closes only the Edge window it created.
"""
import subprocess
import sys
import time
from pathlib import Path

import cv2
import win32con
import win32gui
from PySide6.QtCore import QCoreApplication, Qt

from app.ai.schema import AnswerPayload
from app.automation.window_manager import ensure_target, list_windows, request_target_foreground
from app.automation.windows_mcp_backend import WindowsMCPBackend
from app.capture.screen_capture import preprocess
from app.core.controller import AutoTaskController, RunLimits
from app.recognition.ocr_engine import OCREngine


class DeterministicProvider:
    price_per_million = (0.3, 1.2)

    def __init__(self):
        self.usage = type("Usage", (), {"calls": 0, "input_tokens": 0,
                                        "output_tokens": 0, "upper_cost_usd": 0.0})()

    def analyze(self, observed, image, use_vision):
        self.usage.calls += 1
        matches = [label for label, option in observed.options.items() if "队列" in option.text]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one queue option; observed {observed.option_text}")
        return AnswerPayload(is_question=True, question_type="single",
                             answers=matches, can_answer=True)


class EventLog:
    def __init__(self):
        self.states = []

    def log(self, pid, state, question="", answers="", detail=""):
        self.states.append((state, detail))
        if state in {"RECOGNIZE", "CLICK", "VERIFY", "WAIT", "PAUSED", "ERROR", "FINISHED", "STOPPED"}:
            print(f"{state}: {detail}", flush=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    QCoreApplication([])
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge.is_file():
        raise RuntimeError(f"Edge executable missing: {edge}")
    quiz = Path(__file__).resolve().parents[1] / "test_web" / "index.html"
    before = {window.hwnd for window in list_windows()}
    subprocess.Popen([str(edge), "--inprivate", "--new-window", quiz.as_uri() + "?start=1"])
    target = None
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        candidates = [window for window in list_windows()
                      if window.hwnd not in before and window.process_name.lower() == "msedge.exe"
                      and "AI AutoAnswer · 本地网页模拟题库" in window.title]
        if len(candidates) == 1:
            target = candidates[0]
            break
        time.sleep(0.2)
    if target is None:
        raise RuntimeError("New local Edge quiz window did not appear uniquely")
    try:
        backend = WindowsMCPBackend()
        backend.start()
        try:
            request_target_foreground(target)
        except Exception as exc:
            print(f"Foreground request needs user desktop activation: {exc}", flush=True)
        deadline = time.monotonic() + 60
        print(f"READY: activate Edge fixture HWND={target.hwnd}", flush=True)
        while win32gui.GetForegroundWindow() != target.hwnd and time.monotonic() < deadline:
            time.sleep(0.1)
        ensure_target(target)
        if "--scroll-before" in sys.argv:
            backend.scroll(target, amount=1)
            time.sleep(0.4)
        if "--diagnose" in sys.argv:
            shot = backend.capture(target)
            output = Path(__file__).resolve().parents[1] / "research" / "browser-first.png"
            output.parent.mkdir(parents=True, exist_ok=True)
            ok, png = cv2.imencode(".png", shot.image)
            if not ok:
                raise RuntimeError("Could not encode browser diagnostic image")
            png.tofile(str(output))
            lines = OCREngine()._get_engine().ocr(preprocess(shot.image), cls=True)
            print("OCR diagnostic image:", output, flush=True)
            print("OCR lines:", [(item[1][0], round(item[1][1], 2))
                                 for item in (lines[0] if lines else [])], flush=True)
        events = EventLog()
        provider = DeterministicProvider()
        controller = AutoTaskController(target, provider, events,
                                        RunLimits(max_questions=1, max_seconds=180,
                                                  max_cost_usd=1, mode="auto"),
                                        backend)
        controller.status.connect(lambda status: controller.stop()
                                  if status.startswith(("已暂停：", "运行异常：")) else None,
                                  Qt.DirectConnection)
        controller.run()
        assert any(state == "VERIFY" and "选择状态已确认" in detail
                   for state, detail in events.states), events.states[-8:]
        assert any(state == "WAIT" and "新题已出现" in detail
                   for state, detail in events.states), events.states[-8:]
        assert provider.usage.calls == 1
        print("PASS: browser question selected, verified, and advanced", flush=True)
    finally:
        if "backend" in locals():
            backend.stop()
        if win32gui.IsWindow(target.hwnd):
            win32gui.PostMessage(target.hwnd, win32con.WM_CLOSE, 0, 0)


if __name__ == "__main__":
    main()
