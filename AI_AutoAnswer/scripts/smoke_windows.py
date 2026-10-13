"""Manual visible Windows integration probe for the simulated client."""
import os
import sys
import time

import win32gui

from PySide6.QtWidgets import QApplication

from app.automation.window_manager import TargetWindow
from app.capture.screen_capture import ScreenCaptureEngine
from app.recognition.uia_reader import UIAReader
from test_client.client import PracticeClient


def main():
    app = QApplication([])
    client = PracticeClient()
    client.show()
    client.raise_()
    client.activateWindow()
    app.processEvents()
    target = TargetWindow(int(client.winId()), os.getpid(), client.windowTitle(), "python.exe")
    try:
        win32gui.SetForegroundWindow(target.hwnd)
    except Exception:
        pass
    time.sleep(0.2)
    app.processEvents()
    question = UIAReader().read(target)
    assert question is not None, "UIA failed to read the simulated Qt client"
    assert len(question.options) >= 4
    assert question.next_rect is not None
    print(f"UIA smoke OK: {question.question}, {question.option_text}")
    if "--select" in sys.argv:
        question.options["B"].control.iface_selection_item.Select()
        app.processEvents()
        assert client.option_buttons["B"].isChecked(), "UIA SelectionItem did not select B"
        print("UIA selection state verified")
    if "--next" in sys.argv:
        question.next_control.iface_invoke.Invoke()
        app.processEvents()
        assert "加载中" in client.heading.text(), "UIA Invoke did not advance the simulator"
        print("UIA next loading verified")
    if "--capture" in sys.argv:
        shot = ScreenCaptureEngine().capture(target)
        assert shot.image.shape[0] > 0
        print("Foreground screenshot OK")
    client.close()


if __name__ == "__main__":
    main()
