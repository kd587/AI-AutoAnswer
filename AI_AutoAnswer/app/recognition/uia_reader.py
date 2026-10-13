import re

from pywinauto import Desktop

from app.automation.coordinate_mapper import Rect
from app.automation.window_manager import TargetWindow
from .models import LocatedOption, ObservedQuestion
from .question_context import HEADING, STEM, current_question


OPTION = re.compile(r"^\s*([A-H])\s*[.、．:：)）]\s*(.+)$", re.I)
NEXT = re.compile(r"^(下一题|下一页|继续|Next)\s*[→›>]*$", re.I)
FINISH = re.compile(r"(完成|交卷|提交|结束考试)")
DONE = re.compile(r"^\s*(全部完成|答题完成|练习结束|练习已完成|模拟练习已完成)")


def _rect(control) -> Rect:
    r = control.rectangle()
    return Rect(r.left, r.top, r.width(), r.height())


class UIAReader:
    def read(self, target: TargetWindow) -> ObservedQuestion | None:
        root = Desktop(backend="uia").window(handle=target.hwnd)
        controls = root.descendants()
        texts = []
        options = {}
        next_control = None
        for control in controls:
            try:
                name = control.window_text().strip()
                kind = control.element_info.control_type
                rect = _rect(control)
                if not name or rect.width <= 0 or rect.height <= 0:
                    continue
                if kind in ("RadioButton", "CheckBox", "Button"):
                    match = OPTION.match(name)
                    if match:
                        label, value = match.groups()
                        selected = None
                        try:
                            if kind == "CheckBox":
                                toggle_state = control.get_toggle_state()
                                selected = bool(toggle_state) if toggle_state in (0, 1) else None
                            elif kind == "RadioButton":
                                selected = bool(control.is_selected())
                        except Exception:
                            pass
                        options[label.upper()] = LocatedOption(label.upper(), value, rect,
                                                               control, selected)
                    elif kind == "Button" and NEXT.match(name):
                        next_control = control
                elif kind == "Text":
                    texts.append((rect.top, name))
            except Exception:
                continue
        if any(DONE.match(name) for _, name in texts) and not any(
                STEM.match(name) or HEADING.match(name) for _, name in texts):
            return ObservedQuestion("", "unknown", source="uia", finished=True)
        if len(options) < 2:
            return None
        first_top = min(option.rect.top for option in options.values())
        question, local_kind = current_question([(top, name) for top, name in texts
                                                 if top < first_top and not FINISH.search(name)])
        if not question:
            return None
        control_kinds = {getattr(opt.control.element_info, "control_type", "")
                         for opt in options.values()}
        if "CheckBox" in control_kinds:
            kind = "multiple"
        elif "RadioButton" in control_kinds:
            kind = "single"
        else:
            kind = local_kind
        return ObservedQuestion(question, kind, options,
                                _rect(next_control) if next_control else None,
                                next_control, "uia")
