"""Resolve observed option positions to target-checked MCP clicks."""
import time

import cv2
import numpy as np
import win32api

from app.automation.coordinate_mapper import Rect
from app.capture.screen_capture import Capture
from app.recognition.models import LocatedOption, ObservedQuestion
from .windows_mcp_backend import WindowsMCPBackend


def _crop(shot: Capture, rect: Rect) -> np.ndarray:
    x, y = rect.left - shot.screen_rect.left, rect.top - shot.screen_rect.top
    return shot.image[max(0, y - 14):min(shot.image.shape[0], y + rect.height + 14),
                      max(0, x - 35):min(shot.image.shape[1], x + rect.width + 35)]


class AnswerExecutor:
    def __init__(self, backend: WindowsMCPBackend, reader=None):
        self.backend = backend
        self.reader = reader

    def click_option(self, target, option: LocatedOption, expected_cursor=None):
        if expected_cursor is not None and win32api.GetCursorPos() != expected_cursor:
            raise RuntimeError("User moved mouse; automation paused")
        before = self.backend.capture(target)
        self.backend.click(target, option.rect.center)
        time.sleep(0.15)
        after = self.backend.capture(target)
        current = self.reader(after) if self.reader else self.backend.read(target)
        if current and option.label in current.options:
            selected = current.options[option.label].selected
            if selected is True:
                return
            if selected is False:
                raise RuntimeError("MCP reports option not selected")
        first, second = _crop(before, option.rect), _crop(after, option.rect)
        if first.shape != second.shape or first.size == 0 or np.count_nonzero(
                np.max(cv2.absdiff(first, second), axis=2) > 20) < 20:
            raise RuntimeError("Selection could not be verified")

    def click_next(self, target, observed: ObservedQuestion):
        if observed.next_rect is None:
            raise RuntimeError("Next question control not found")
        self.backend.click(target, observed.next_rect.center)
