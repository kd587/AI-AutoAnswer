from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.automation.coordinate_mapper import Rect
from app.automation.window_manager import TargetWindow
from app.ui import main_window as ui


def _window(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(ui, "load_api_key", lambda: "")
    monkeypatch.setattr(ui, "list_windows", lambda exclude_pid=None: [])
    monkeypatch.setattr(ui.MainWindow, "_register_hotkey", lambda self: setattr(self, "hotkey_registered", False))

    class Backend:
        def stop(self):
            pass

    monkeypatch.setattr(ui, "WindowsMCPBackend", Backend)
    window = ui.MainWindow(start_mcp=False)
    target = TargetWindow(42, 99, "模拟练习客户端", "client.exe", state="minimized")
    window.windows.addItem("模拟练习客户端 | minimized", target)
    window.windows.setCurrentIndex(window.windows.count() - 1)
    window._provider = lambda: object()
    return window


def test_start_waits_for_restored_foreground_before_creating_worker(monkeypatch):
    window = _window(monkeypatch)
    events = []
    monkeypatch.setattr(ui.win32gui, "IsIconic", lambda hwnd: True)
    monkeypatch.setattr(ui, "request_target_foreground", lambda target: events.append("restore"))
    monkeypatch.setattr(ui, "ensure_target", lambda target: events.append("foreground") or Rect(0, 0, 100, 100))
    window._launch_worker = lambda *args: events.append("worker")
    window.start()
    assert events == []
    QTest.qWait(550)
    assert events == ["restore", "foreground", "worker"]
    assert "visible" in window.windows.currentText()
    window.close()


def test_stop_cancels_pending_foreground_handoff(monkeypatch):
    window = _window(monkeypatch)
    events = []
    monkeypatch.setattr(ui, "request_target_foreground", lambda target: events.append("restore"))
    window._launch_worker = lambda *args: events.append("worker")
    window.start()
    window.stop()
    QTest.qWait(550)
    assert events == []
    window.close()
