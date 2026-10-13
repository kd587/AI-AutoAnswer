from dataclasses import dataclass

import psutil
import win32con
import win32gui
import win32process

from .coordinate_mapper import Rect


@dataclass(frozen=True)
class TargetWindow:
    hwnd: int
    pid: int
    title: str
    process_name: str
    process_started_at: float | None = None
    state: str = "visible"


def _pid(hwnd: int) -> int:
    return win32process.GetWindowThreadProcessId(hwnd)[1]


def list_windows(exclude_pid: int | None = None) -> list[TargetWindow]:
    found = []

    def visit(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or win32gui.GetWindow(hwnd, win32con.GW_OWNER):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        try:
            pid = _pid(hwnd)
            if pid == exclude_pid:
                return
            name = psutil.Process(pid).name()
            state = "minimized" if win32gui.IsIconic(hwnd) else (
                "disabled" if not win32gui.IsWindowEnabled(hwnd) else "visible")
            found.append(TargetWindow(hwnd, pid, title, name,
                                      psutil.Process(pid).create_time(), state))
        except (psutil.Error, OSError):
            return

    win32gui.EnumWindows(visit, None)
    return sorted(found, key=lambda item: item.title.lower())


def target_from_point(x: int, y: int) -> TargetWindow:
    hwnd = win32gui.GetAncestor(win32gui.WindowFromPoint((x, y)), win32con.GA_ROOT)
    if not hwnd or not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("准星没有落在可见应用窗口内")
    title = win32gui.GetWindowText(hwnd).strip()
    if not title:
        raise RuntimeError("目标窗口没有标题；请将准星放在题目内容区域后松开")
    pid = _pid(hwnd)
    process = psutil.Process(pid)
    state = "minimized" if win32gui.IsIconic(hwnd) else "visible"
    if state != "visible":
        raise RuntimeError("目标窗口已最小化")
    return TargetWindow(hwnd, pid, title,
                        process.name(), process.create_time(), state)


def validate_target_identity(target: TargetWindow) -> None:
    if not win32gui.IsWindow(target.hwnd) or _pid(target.hwnd) != target.pid:
        raise RuntimeError("Target window closed or HWND reused")
    if target.process_started_at is not None:
        try:
            if psutil.Process(target.pid).create_time() != target.process_started_at:
                raise RuntimeError("Target process PID was reused")
        except psutil.Error as exc:
            raise RuntimeError("Target process ended") from exc
    if target.process_name.lower() in {"msedge.exe", "chrome.exe", "firefox.exe", "brave.exe", "opera.exe"}:
        current_title = win32gui.GetWindowText(target.hwnd).strip()
        if current_title != target.title:
            raise RuntimeError(f"浏览器标签页或页面已切换；已选：{target.title}；当前：{current_title}。请重新选择目标页")


def request_target_foreground(target: TargetWindow) -> None:
    """Request focus only for the exact user-selected window; caller verifies it later."""
    validate_target_identity(target)
    if win32gui.IsIconic(target.hwnd):
        win32gui.ShowWindow(target.hwnd, win32con.SW_RESTORE)
    if not win32gui.IsWindowVisible(target.hwnd):
        raise RuntimeError("目标窗口不可见，无法启动")
    win32gui.SetForegroundWindow(target.hwnd)


def ensure_target(target: TargetWindow, require_foreground: bool = True) -> Rect:
    validate_target_identity(target)
    if not win32gui.IsWindowVisible(target.hwnd) or win32gui.IsIconic(target.hwnd):
        raise RuntimeError("Target window is hidden or minimized")
    if require_foreground:
        foreground = win32gui.GetAncestor(win32gui.GetForegroundWindow(), win32con.GA_ROOT)
        if foreground != target.hwnd:
            try:
                current_title = win32gui.GetWindowText(foreground).strip() or "无标题窗口"
            except Exception:
                current_title = "未知窗口或安全桌面"
            raise RuntimeError(
                f"Target window is not foreground; current={current_title} "
                f"(HWND {foreground}); selected={target.title} (HWND {target.hwnd}); automation paused")
    left, top, right, bottom = win32gui.GetClientRect(target.hwnd)
    x0, y0 = win32gui.ClientToScreen(target.hwnd, (left, top))
    x1, y1 = win32gui.ClientToScreen(target.hwnd, (right, bottom))
    if x1 <= x0 or y1 <= y0:
        raise RuntimeError("Target has no visible client area")
    return Rect(x0, y0, x1 - x0, y1 - y0)
