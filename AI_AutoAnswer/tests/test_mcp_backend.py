import pytest
import numpy as np

from app.ai.schema import AnswerPayload, validate_answer
from app.automation.chaoxing_adapter import ChaoxingAdapter
from app.automation.windows_mcp_backend import NEXT as MCP_NEXT, parse_snapshot
from app.automation import windows_mcp_backend as backend_module
from types import SimpleNamespace
from app.recognition.ocr_engine import NEXT as OCR_NEXT
from app.recognition.uia_reader import NEXT as UIA_NEXT
from app.automation.answer_executor import AnswerExecutor
from app.automation.coordinate_mapper import Rect
from app.capture.screen_capture import Capture
from app.recognition.models import LocatedOption, ObservedQuestion


SNAPSHOT = '''Focused Window:
Name Handle
AI AutoAnswer 模拟练习客户端 123
UI Tree:
desktop
    ├── window "AI AutoAnswer 模拟练习客户端"
    │   ├── (500,200) text "模拟练习 第 1 题：选择队列"
    │   ├── (500,260) 单选按钮 "A. 栈" [action: click] [toggle:off]
    │   ├── (500,310) 单选按钮 "B. 队列" [action: click] [toggle:on]
    │   ├── (500,360) 按钮 "下一题" [action: click]
    ├── window "unrelated"
    │   ├── (40,40) 按钮 "C. unrelated" [action: click]
'''


def test_snapshot_scopes_options_and_state_to_selected_window():
    question = parse_snapshot(SNAPSHOT, "AI AutoAnswer 模拟练习客户端")
    assert question.question_type == "single"
    assert set(question.options) == {"A", "B"}
    assert question.options["B"].selected is True
    assert question.next_rect.center == (500, 360)
    assert question.source == "mcp"


def test_snapshot_rejects_other_window():
    assert parse_snapshot(SNAPSHOT, "other target") is None


def test_unusable_snapshot_is_not_repeated_for_same_target(monkeypatch):
    calls = []

    class Client:
        def call(self, name, arguments=None, timeout=20):
            calls.append(name)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="UI Tree:\ndesktop")])

    monkeypatch.setattr(backend_module, "ensure_target", lambda target: Rect(0, 0, 100, 100))
    backend = backend_module.WindowsMCPBackend(Client())
    target = SimpleNamespace(hwnd=10, pid=20, process_started_at=30, title="模拟练习")
    assert backend.read(target) is None
    assert backend.read(target) is None
    assert calls == ["Snapshot"]


def test_next_control_accepts_visual_arrow_but_not_final_submit():
    for matcher in (MCP_NEXT, OCR_NEXT, UIA_NEXT):
        assert matcher.fullmatch("下一题 →")
        assert matcher.fullmatch("下一题→")
        assert not matcher.fullmatch("交卷")
        assert not matcher.fullmatch("最终提交")


def test_minimal_answer_only_accepts_observed_labels():
    payload = AnswerPayload.model_validate({"is_question": True, "question_type": "single",
                                            "answers": ["F"], "can_answer": True})
    with pytest.raises(ValueError):
        validate_answer(payload, {"A": "栈", "B": "队列"})


def test_answer_schema_rejects_extra_explanation():
    with pytest.raises(ValueError):
        AnswerPayload.model_validate({"is_question": True, "question_type": "single",
                                      "answers": ["B"], "can_answer": True,
                                      "reason": "not requested"})


def test_chaoxing_pauses_on_restricted_or_unknown_page():
    adapter = ChaoxingAdapter()
    with pytest.raises(RuntimeError):
        adapter.assert_allowed(ObservedQuestion("选择正确答案", "single"))
    with pytest.raises(RuntimeError):
        adapter.assert_allowed(ObservedQuestion("模拟练习：选择答案", "single"), "正式考试")
    adapter.assert_allowed(ObservedQuestion("模拟练习：选择答案", "single"))


def test_executor_requires_selected_state_before_advancing(monkeypatch):
    class Backend:
        clicked = []
        def capture(self, target):
            return Capture(np.zeros((100, 100, 3), np.uint8), Rect(0, 0, 100, 100))
        def click(self, target, point):
            self.clicked.append(point)
        def read(self, target):
            return ObservedQuestion("模拟练习", "single", {
                "B": LocatedOption("B", "队列", Rect(10, 10, 10, 10), selected=False)})

    backend = Backend()
    executor = AnswerExecutor(backend)
    with pytest.raises(RuntimeError, match="not selected"):
        executor.click_option(object(), LocatedOption("B", "队列", Rect(10, 10, 10, 10)))
    assert backend.clicked == [(15, 15)]


def test_visual_verification_uses_target_capture_without_desktop_snapshot():
    class Backend:
        captures = 0
        def capture(self, target):
            self.captures += 1
            image = np.zeros((100, 100, 3), np.uint8)
            if self.captures > 1:
                image[10:20, 10:20] = 255
            return Capture(image, Rect(0, 0, 100, 100))
        def click(self, target, point):
            assert point == (15, 15)
        def read(self, target):
            raise AssertionError("Browser option verification should not scan the desktop")

    backend = Backend()
    executor = AnswerExecutor(backend, reader=lambda shot: None)
    executor.click_option(object(), LocatedOption("B", "队列", Rect(10, 10, 10, 10)))
    assert backend.captures == 2
