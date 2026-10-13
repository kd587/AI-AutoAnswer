"""Interactive 30-question MCP run on the local Qt fixture, without an API key.

Run this script, then bring its Qt window to the foreground within 60 seconds.
The deterministic provider isolates desktop execution from model accuracy.
"""
import os
import sys
import threading
import time

import psutil
import win32gui
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.ai.schema import AnswerPayload
from app.automation.window_manager import TargetWindow
from app.automation.windows_mcp_backend import WindowsMCPBackend
from app.core.controller import AutoTaskController, RunLimits
from test_client.client import PracticeClient


class VerifiedClient(PracticeClient):
    def __init__(self):
        self.incorrect_advances = 0
        super().__init__()

    def next_question(self):
        if "（正确）" not in self.feedback.text():
            self.incorrect_advances += 1
            return
        super().next_question()


class DeterministicProvider:
    price_per_million = (0.3, 1.2)

    def __init__(self):
        self.usage = type("Usage", (), {"calls": 0, "input_tokens": 0,
                                        "output_tokens": 0, "upper_cost_usd": 0.0})()

    def analyze(self, observed, image, use_vision):
        self.usage.calls += 1
        answers = (["A", "C"] + (["E"] if "E" in observed.options else [])
                   if observed.question_type == "multiple" else ["B"])
        return AnswerPayload(is_question=True, question_type=observed.question_type,
                             answers=answers, can_answer=True)


class EventLog:
    def __init__(self):
        self.states = []

    def log(self, pid, state, question="", answers="", detail=""):
        self.states.append((state, detail))
        if state in {"PAUSED", "ERROR", "FINISHED", "STOPPED"}:
            print(f"{state}: {detail}", flush=True)


def main():
    app = QApplication([])
    client = VerifiedClient()
    client.show()
    target = TargetWindow(int(client.winId()), os.getpid(), client.windowTitle(),
                          psutil.Process().name(), psutil.Process().create_time())
    events = EventLog()
    provider = DeterministicProvider()
    backend = WindowsMCPBackend()
    controller = AutoTaskController(target, provider, events,
                                    RunLimits(max_questions=30, max_seconds=600,
                                              max_cost_usd=1, mode="auto"), backend)
    controller.status.connect(lambda status: controller.stop()
                              if status.startswith(("已暂停：", "运行异常：")) else None)
    thread = threading.Thread(target=controller.run, daemon=True)
    started = time.monotonic()
    started_run = False

    def poll():
        nonlocal started_run
        if not started_run and win32gui.GetForegroundWindow() == target.hwnd:
            started_run = True
            print("Foreground ready; starting 30-question MCP run", flush=True)
            thread.start()
        if started_run and not thread.is_alive():
            app.quit()
        elif not started_run and time.monotonic() - started > 60:
            app.quit()

    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(100)
    QTimer.singleShot(660000, app.quit)
    print(f"READY: activate Qt window HWND={target.hwnd}", flush=True)
    app.exec()
    if thread.is_alive():
        controller.stop()
        thread.join(timeout=5)
    client.close()
    assert started_run, "Simulator never gained foreground"
    assert client.incorrect_advances == 0, f"Incorrect advance attempts: {client.incorrect_advances}"
    assert client.index == 30, f"Stopped at question {client.index + 1}; last events={events.states[-5:]}"
    assert events.states[-1][0] == "FINISHED", events.states[-5:]
    print(f"PASS: 30 questions, {provider.usage.calls} provider calls, final completion page", flush=True)


if __name__ == "__main__":
    main()
