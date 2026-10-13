import time

import cv2
import numpy as np
import pyautogui
import win32api
import win32con
import win32gui

from app.automation.coordinate_mapper import Rect
from app.automation.window_manager import TargetWindow, ensure_target
from app.capture.screen_capture import ScreenCaptureEngine
from app.recognition.models import LocatedOption, ObservedQuestion


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def _assert_point(target: TargetWindow, point: tuple[int, int]) -> None:
    client = ensure_target(target)
    if not client.contains(point):
        raise RuntimeError("Click point outside target client area")
    hit = win32gui.GetAncestor(win32gui.WindowFromPoint(point), win32con.GA_ROOT)
    if hit != target.hwnd:
        raise RuntimeError("Click point is obscured by another window")


def _crop(image: np.ndarray, capture_rect: Rect, screen_rect: Rect) -> np.ndarray:
    x = screen_rect.left - capture_rect.left
    y = screen_rect.top - capture_rect.top
    return image[max(0, y - 12):min(image.shape[0], y + screen_rect.height + 12),
                 max(0, x - 40):min(image.shape[1], x + screen_rect.width + 24)]


def _visual_changed(before: np.ndarray, after: np.ndarray) -> bool:
    if before.shape != after.shape or before.size == 0:
        return False
    difference = cv2.absdiff(before, after)
    return bool(np.count_nonzero(np.max(difference, axis=2) > 20) >= 20)


class MouseController:
    def __init__(self):
        self.camera = ScreenCaptureEngine()

    def click_option(self, target: TargetWindow, option: LocatedOption,
                     expected_cursor: tuple[int, int] | None = None) -> None:
        point = option.rect.center
        _assert_point(target, point)
        if expected_cursor is not None and win32api.GetCursorPos() != expected_cursor:
            raise RuntimeError("User moved mouse; automation paused")
        before = self.camera.capture(target)
        if option.control is not None:
            kind = option.control.element_info.control_type
            if kind not in ("RadioButton", "CheckBox", "Button"):
                raise RuntimeError("Unsupported option control")
            try:
                state = (option.control.get_toggle_state() if kind == "CheckBox"
                         else option.control.get_selection_item_state()) if kind != "Button" else False
                if state:
                    return
                if kind == "RadioButton":
                    option.control.iface_selection_item.Select()
                elif kind == "CheckBox":
                    option.control.iface_toggle.Toggle()
                else:
                    option.control.iface_invoke.Invoke()
            except Exception:
                pass
            time.sleep(0.15)
            try:
                state = (option.control.get_toggle_state() if kind == "CheckBox"
                         else option.control.get_selection_item_state()) if kind != "Button" else False
                if state:
                    return
            except Exception:
                pass
            if kind != "Button":
                _assert_point(target, point)
            else:
                after_invoke = self.camera.capture(target)
                before_crop = _crop(before.image, before.screen_rect, option.rect)
                after_crop = _crop(after_invoke.image, after_invoke.screen_rect, option.rect)
                if _visual_changed(before_crop, after_crop):
                    return
                _assert_point(target, point)
        pyautogui.click(*point)
        time.sleep(0.15)
        after = self.camera.capture(target)
        if option.control is not None:
            try:
                selected = (option.control.get_toggle_state() if option.control.element_info.control_type == "CheckBox"
                            else option.control.get_selection_item_state())
                if selected:
                    return
            except Exception:
                pass
        before_crop = _crop(before.image, before.screen_rect, option.rect)
        after_crop = _crop(after.image, after.screen_rect, option.rect)
        if not _visual_changed(before_crop, after_crop):
            raise RuntimeError("No visible selection change")

    def click_next(self, target: TargetWindow, observed: ObservedQuestion) -> None:
        if observed.next_rect is None:
            raise RuntimeError("Next button not found; final submit is never clicked")
        _assert_point(target, observed.next_rect.center)
        pyautogui.click(*observed.next_rect.center)
