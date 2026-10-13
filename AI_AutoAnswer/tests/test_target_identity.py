from types import SimpleNamespace

import pytest

from app.automation import window_manager as wm


def test_browser_tab_change_pauses_before_capture_or_click(monkeypatch):
    target = wm.TargetWindow(42, 99, "AI AutoAnswer · 本地网页模拟题库 - Microsoft Edge", "msedge.exe")
    monkeypatch.setattr(wm.win32gui, "IsWindow", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "IsWindowVisible", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "IsIconic", lambda hwnd: False)
    monkeypatch.setattr(wm.win32gui, "GetWindowText", lambda hwnd: "ChatGPT - Microsoft Edge")
    monkeypatch.setattr(wm, "_pid", lambda hwnd: 99)
    with pytest.raises(RuntimeError, match="tab|标签页"):
        wm.ensure_target(target, require_foreground=False)


def test_activation_restores_minimized_selected_window(monkeypatch):
    target = wm.TargetWindow(42, 99, "模拟练习客户端", "client.exe", state="minimized")
    calls = []
    monkeypatch.setattr(wm.win32gui, "IsWindow", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "IsWindowVisible", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "IsIconic", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "GetWindowText", lambda hwnd: target.title)
    monkeypatch.setattr(wm.win32gui, "ShowWindow", lambda hwnd, mode: calls.append(("restore", hwnd, mode)))
    monkeypatch.setattr(wm.win32gui, "SetForegroundWindow", lambda hwnd: calls.append(("focus", hwnd)))
    monkeypatch.setattr(wm, "_pid", lambda hwnd: 99)
    wm.request_target_foreground(target)
    assert calls == [("restore", 42, wm.win32con.SW_RESTORE), ("focus", 42)]


def test_activation_rejects_stale_browser_tab_before_restoring(monkeypatch):
    target = wm.TargetWindow(42, 99, "题库 - Microsoft Edge", "msedge.exe", state="minimized")
    monkeypatch.setattr(wm.win32gui, "IsWindow", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "GetWindowText", lambda hwnd: "ChatGPT - Microsoft Edge")
    monkeypatch.setattr(wm, "_pid", lambda hwnd: 99)
    restored = []
    monkeypatch.setattr(wm.win32gui, "ShowWindow", lambda *args: restored.append(args))
    with pytest.raises(RuntimeError, match="标签页"):
        wm.request_target_foreground(target)
    assert restored == []


def test_foreground_failure_names_the_window_that_took_focus(monkeypatch):
    target = wm.TargetWindow(42, 99, "模拟练习客户端", "client.exe")
    monkeypatch.setattr(wm.win32gui, "IsWindow", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "IsWindowVisible", lambda hwnd: True)
    monkeypatch.setattr(wm.win32gui, "IsIconic", lambda hwnd: False)
    monkeypatch.setattr(wm.win32gui, "GetForegroundWindow", lambda: 77)
    monkeypatch.setattr(wm.win32gui, "GetAncestor", lambda hwnd, mode: hwnd)
    monkeypatch.setattr(wm.win32gui, "GetWindowText", lambda hwnd: "AI AutoAnswer" if hwnd == 77 else target.title)
    monkeypatch.setattr(wm, "_pid", lambda hwnd: 99 if hwnd == 42 else 88)
    with pytest.raises(RuntimeError, match="AI AutoAnswer"):
        wm.ensure_target(target)
