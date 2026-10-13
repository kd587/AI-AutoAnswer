import os
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox

from app.ui import main_window as ui


def _app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_drag_release_uses_native_screen_point(monkeypatch):
    _app(monkeypatch)
    point = (2380, 980)
    expected = object()
    calls = []
    monkeypatch.setattr(ui.win32api, "GetCursorPos", lambda: point)
    monkeypatch.setattr(ui, "target_from_point", lambda x, y: calls.append((x, y)) or expected)
    picker = ui.WindowPicker()
    chosen = []
    picker.picked.connect(chosen.append)
    QTest.mousePress(picker, Qt.LeftButton)
    QTest.mouseRelease(picker, Qt.LeftButton)
    assert calls == [point]
    assert chosen == [expected]
    assert picker.text() == "拖动准星选窗口"


def test_lookup_error_is_reported_instead_of_silently_ignored(monkeypatch):
    _app(monkeypatch)
    monkeypatch.setattr(ui.win32api, "GetCursorPos", lambda: (400, 300))
    monkeypatch.setattr(ui, "target_from_point", lambda x, y: (_ for _ in ()).throw(RuntimeError("窗口不可访问")))
    picker = ui.WindowPicker()
    errors = []
    picker.failed.connect(errors.append)
    QTest.mousePress(picker, Qt.LeftButton)
    QTest.mouseRelease(picker, Qt.LeftButton)
    assert errors == ["窗口不可访问"]


def test_picking_own_program_shows_actionable_message():
    messages = []
    fake = SimpleNamespace(status=SimpleNamespace(setText=messages.append),
                           events=SimpleNamespace(append=messages.append))
    fake._append_event = lambda detail: ui.MainWindow._append_event(fake, detail)
    fake._picker_failed = lambda detail: ui.MainWindow._picker_failed(fake, detail)
    ui.MainWindow._picked_window(fake, SimpleNamespace(pid=os.getpid()))
    assert any("目标窗口" in item for item in messages)


def test_repick_same_browser_window_refreshes_tab_title(monkeypatch):
    _app(monkeypatch)
    old = ui.TargetWindow(99, 123, "旧标签页", "msedge.exe")
    new = ui.TargetWindow(99, 123, "AI AutoAnswer · 本地网页模拟题库", "msedge.exe")
    combo = QComboBox()
    combo.addItem("旧标签页", old)
    messages = []
    fake = SimpleNamespace(windows=combo, status=SimpleNamespace(setText=messages.append))
    fake._append_event = messages.append
    ui.MainWindow._picked_window(fake, new)
    assert combo.currentData() == new
    assert "本地网页模拟题库" in combo.currentText()
