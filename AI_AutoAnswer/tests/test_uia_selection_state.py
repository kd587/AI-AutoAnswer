from types import SimpleNamespace

from app.recognition import uia_reader


class Control:
    def __init__(self, kind, text, top, selected=None):
        self.element_info = SimpleNamespace(control_type=kind)
        self._text = text
        self._top = top
        self._selected = selected

    def window_text(self):
        return self._text

    def rectangle(self):
        top = self._top
        return SimpleNamespace(left=100, top=top, width=lambda: 200, height=lambda: 30)

    def get_toggle_state(self):
        return 1 if self._selected else 0

    def is_selected(self):
        return bool(self._selected)


def test_uia_reader_reports_checkbox_toggle_state(monkeypatch):
    controls = [Control("Text", "模拟练习 第 21 题：多选题", 100),
                Control("CheckBox", "A. 列表", 200, True),
                Control("CheckBox", "B. 元组", 250, False),
                Control("Button", "下一题", 300)]
    monkeypatch.setattr(uia_reader, "Desktop", lambda backend: SimpleNamespace(
        window=lambda handle: SimpleNamespace(descendants=lambda: controls)))
    target = SimpleNamespace(hwnd=42)
    observed = uia_reader.UIAReader().read(target)
    assert observed.question_type == "multiple"
    assert observed.options["A"].selected is True
    assert observed.options["B"].selected is False


def test_uia_reader_reports_completion_without_options(monkeypatch):
    controls = [Control("Text", "全部完成：30 道模拟题已处理", 100),
                Control("Text", "练习结束，无需最终提交", 140)]
    monkeypatch.setattr(uia_reader, "Desktop", lambda backend: SimpleNamespace(
        window=lambda handle: SimpleNamespace(descendants=lambda: controls)))
    observed = uia_reader.UIAReader().read(SimpleNamespace(hwnd=42))
    assert observed is not None and observed.finished


def test_uia_reader_ignores_stale_options_on_completion_page(monkeypatch):
    controls = [Control("Text", "全部完成：30 道模拟题已处理", 100),
                Control("Text", "练习结束，无需最终提交", 140),
                Control("RadioButton", "A. 栈", 200, False),
                Control("RadioButton", "B. 队列", 250, True)]
    monkeypatch.setattr(uia_reader, "Desktop", lambda backend: SimpleNamespace(
        window=lambda handle: SimpleNamespace(descendants=lambda: controls)))
    observed = uia_reader.UIAReader().read(SimpleNamespace(hwnd=42))
    assert observed is not None and observed.finished
