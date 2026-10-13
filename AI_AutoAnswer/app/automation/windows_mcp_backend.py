"""Target-scoped operations backed by the Windows-MCP stdio server."""
import base64
import json
import re

import cv2
import numpy as np
import win32gui

from app.automation.coordinate_mapper import Rect
from app.automation.window_manager import TargetWindow, ensure_target
from app.capture.screen_capture import Capture
from app.recognition.models import LocatedOption, ObservedQuestion
from app.recognition.question_context import current_question
from .mcp_client import MCPClientManager


OPTION = re.compile(r"^\s*([A-H])\s*[.、．:：)）]\s*(.+)$", re.I)
ELEMENT = re.compile(r'\((-?\d+),(-?\d+)\)\s+([^\"]+?)\s+"([^\"]+)"')
NEXT = re.compile(r"^(下一题|下一页|继续|Next)\s*[→›>]*$", re.I)
FINISH = re.compile(r"(全部完成|答题完成|练习结束)")


def _text(result) -> str:
    parts = []
    for block in result.content:
        if block.type != "text":
            continue
        value = block.text
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                if all(isinstance(part, str) for part in parsed):
                    parts.extend(parsed)
                else:
                    parts.append(value)
                continue
        except (ValueError, TypeError):
            pass
        parts.append(value)
    return "\n".join(parts)


def parse_snapshot(text: str, title: str) -> ObservedQuestion | None:
    tree = text.split("UI Tree:", 1)[-1]
    lines = tree.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if 'window "' in line and title in line), None)
    if start is None:
        return None
    scoped = []
    for line in lines[start + 1:]:
        if 'window "' in line and re.match(r"\s*[├└]── window", line):
            break
        scoped.append(line)
    options = {}
    option_kinds = set()
    question_lines = []
    next_rect = None
    for line in scoped:
        match = ELEMENT.search(line)
        if not match:
            continue
        x, y, kind, name = match.groups()
        x, y = int(x), int(y)
        if x <= 0 and y <= 0:
            continue
        option = OPTION.match(name)
        if option and "[action: click]" in line:
            label, value = option.groups()
            option_kinds.add(kind.strip().lower())
            selected = True if "[toggle:on]" in line or "[selected]" in line else (
                False if "[toggle:off]" in line else None)
            options[label.upper()] = LocatedOption(label.upper(), value.strip(),
                                                     Rect(x - 5, y - 5, 10, 10), selected=selected)
        elif NEXT.match(name) and "[action: click]" in line:
            next_rect = Rect(x - 5, y - 5, 10, 10)
        elif "text " in line or "文本 " in line or "[action: click]" not in line:
            question_lines.append((y, name))
    all_text = "\n".join(name for _, name in question_lines)
    if FINISH.search(all_text) and not options:
        return ObservedQuestion("", "unknown", source="mcp", finished=True)
    if len(options) < 2:
        return None
    first_y = min(opt.rect.top for opt in options.values())
    question, local_kind = current_question([(y, name) for y, name in question_lines
                                             if y < first_y and not FINISH.search(name)])
    if not question:
        return None
    if any("复选框" in kind or "checkbox" in kind for kind in option_kinds):
        detected_kind = "multiple"
    elif any("单选按钮" in kind or "radiobutton" in kind for kind in option_kinds):
        detected_kind = "single"
    else:
        detected_kind = local_kind
    return ObservedQuestion(question, detected_kind,
                            options, next_rect, source="mcp")


class WindowsMCPBackend:
    def __init__(self, client: MCPClientManager | None = None):
        self.client = client or MCPClientManager()
        self.displays = []
        self.last_snapshot_text = ""
        self._snapshot_misses = set()

    def start(self):
        self.client.start()
        self._snapshot_misses.clear()
        response = self.client.call("DisplayInventory", timeout=10)
        self.displays = json.loads(_text(response))
        if not self.displays:
            raise RuntimeError("Windows-MCP reported no displays")

    def stop(self):
        self.client.stop()

    def cancel_pending(self):
        self.client.cancel_pending()

    def read(self, target: TargetWindow) -> ObservedQuestion | None:
        ensure_target(target)
        identity = (target.hwnd, target.pid, target.process_started_at, target.title)
        if identity in self._snapshot_misses:
            return None
        result = self.client.call("Snapshot", {"use_vision": False,
                           "use_dom": False, "use_annotation": False}, timeout=20)
        ensure_target(target)
        self.last_snapshot_text = _text(result)
        observed = parse_snapshot(self.last_snapshot_text, target.title)
        if observed is None:
            self._snapshot_misses.add(identity)
        return observed

    def reset_recognition_strategy(self):
        self._snapshot_misses.clear()

    def capture(self, target: TargetWindow) -> Capture:
        rect = ensure_target(target)
        result = self.client.call("Screenshot", {"use_annotation": False}, timeout=20)
        ensure_target(target)
        text = _text(result)
        image_block = next((item for item in result.content if item.type == "image"), None)
        if image_block is None:
            raise RuntimeError("Windows-MCP screenshot has no image")
        encoded = base64.b64decode(image_block.data)
        image = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError("Windows-MCP screenshot decoding failed")
        region_match = re.search(r"Screenshot Region: \((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", text)
        if region_match:
            left, top, right, bottom = map(int, region_match.groups())
        else:
            bounds = [display["bounds"] for display in self.displays]
            left, top = min(b["left"] for b in bounds), min(b["top"] for b in bounds)
            right, bottom = max(b["right"] for b in bounds), max(b["bottom"] for b in bounds)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            raise RuntimeError("Invalid MCP display bounds")
        if image.shape[1] != width or image.shape[0] != height:
            image = cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
        x, y = rect.left - left, rect.top - top
        if x < 0 or y < 0 or x + rect.width > width or y + rect.height > height:
            raise RuntimeError("Target outside MCP screenshot region")
        crop = image[y:y + rect.height, x:x + rect.width].copy()
        if cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).std() < 2:
            raise RuntimeError("MCP screenshot is blank or protected")
        return Capture(crop, rect)

    def click(self, target: TargetWindow, point: tuple[int, int]):
        client_rect = ensure_target(target)
        if not client_rect.contains(point):
            raise RuntimeError("Click point outside selected client")
        hit = win32gui.GetAncestor(win32gui.WindowFromPoint(point), 2)
        if hit != target.hwnd:
            raise RuntimeError("Click point obscured by another window")
        self.client.call("Click", {"loc": list(point), "button": "left", "clicks": 1}, timeout=10)
        ensure_target(target)

    def wait_for_text(self, target: TargetWindow, text: str, timeout: float = 5):
        ensure_target(target)
        return self.client.call("WaitFor", {"condition": "text_exists", "text": text,
                                 "timeout": timeout, "interval": 0.25}, timeout=timeout + 2)

    def scroll(self, target: TargetWindow, direction: str = "down", amount: int = 1):
        if direction not in {"up", "down"} or amount not in {1, 2}:
            raise ValueError("Only bounded vertical scroll is allowed")
        point = ensure_target(target).center
        if win32gui.GetAncestor(win32gui.WindowFromPoint(point), 2) != target.hwnd:
            raise RuntimeError("Target center is obscured")
        self.client.call("Scroll", {"loc": list(point), "type": "vertical",
                                    "direction": direction, "wheel_times": amount}, timeout=10)
        ensure_target(target)
