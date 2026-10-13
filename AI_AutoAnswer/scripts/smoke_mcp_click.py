"""Real Windows-MCP click probe against the Qt simulator with a live event loop."""
import os
import threading
import time

import psutil
import win32gui
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.automation.answer_executor import AnswerExecutor
from app.automation.window_manager import TargetWindow
from app.automation.windows_mcp_backend import WindowsMCPBackend
from test_client.client import PracticeClient


def main():
    app = QApplication([])
    client = PracticeClient()
    client.show()
    client.raise_()
    client.activateWindow()
    target = TargetWindow(int(client.winId()), os.getpid(), client.windowTitle(),
                          psutil.Process().name(), psutil.Process().create_time())
    try:
        win32gui.SetForegroundWindow(target.hwnd)
    except Exception:
        pass
    backend = WindowsMCPBackend()
    outcome = []

    def probe():
        try:
            backend.start()
            observed = backend.read(target)
            assert observed is not None, "MCP Snapshot did not find simulator question"
            assert observed.question_type == "single", observed.question_type
            assert "B" in observed.options, observed.option_text
            assert observed.next_rect is not None, "MCP Snapshot did not find next button"
            executor = AnswerExecutor(backend)
            executor.click_option(target, observed.options["B"])
            fresh = backend.read(target)
            assert fresh is not None and fresh.options["B"].selected is True, "MCP did not confirm B selected"
            executor.click_next(target, fresh)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                loaded = backend.read(target)
                if loaded and loaded.fingerprint != observed.fingerprint:
                    outcome.append("MCP click and next verified on live Qt simulator")
                    return
                time.sleep(0.2)
            raise AssertionError("Next question did not load")
        except BaseException as exc:
            outcome.append(exc)
        finally:
            backend.stop()

    thread = threading.Thread(target=probe, daemon=True)
    QTimer.singleShot(200, thread.start)
    timer = QTimer()
    timer.timeout.connect(lambda: app.quit() if outcome else None)
    timer.start(100)
    QTimer.singleShot(60000, app.quit)
    app.exec()
    thread.join(timeout=5)
    client.close()
    if not outcome:
        raise TimeoutError("MCP click probe did not finish in 60 seconds")
    if isinstance(outcome[0], BaseException):
        raise outcome[0]
    print(outcome[0])


if __name__ == "__main__":
    main()
