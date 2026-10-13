import threading
import time
import traceback
from datetime import datetime
from dataclasses import dataclass

import cv2
import win32api
import win32gui
from PySide6.QtCore import QObject, Signal, Slot

from app.ai.deepseek_client import AIProvider
from app.automation.mouse_controller import MouseController
from app.automation.answer_executor import AnswerExecutor
from app.automation.chaoxing_adapter import ChaoxingAdapter
from app.automation.windows_mcp_backend import WindowsMCPBackend
from app.automation.user_activity import MouseActivityGuard
from app.automation.window_manager import TargetWindow, ensure_target
from app.capture.screen_capture import ScreenCaptureEngine
from app.recognition.ocr_engine import OCREngine
from app.recognition.uia_reader import UIAReader
from app.storage.database import RunDatabase
from app.storage.database import redact
from .state_machine import RunState, StateMachine


@dataclass
class RunLimits:
    max_questions: int = 30
    max_seconds: int = 1800
    max_cost_usd: float = 1.0
    mode: str = "semi"
    use_vision: bool = False


@dataclass
class RunProgress:
    started: float
    recognized: int = 0
    selected: int = 0
    clicked: int = 0
    seen: set[str] | None = None

    def __post_init__(self):
        if self.seen is None:
            self.seen = set()


class FatalAutomationError(RuntimeError):
    """A configured run limit or invariant that cannot be fixed by retrying."""


class AutomationController(QObject):
    status = Signal(str)
    question = Signal(str, str, str)
    preview = Signal(object)
    metrics = Signal(int, int, int, float, int)
    approval_needed = Signal()
    finished = Signal(str)
    trace = Signal(str)

    def __init__(self, target: TargetWindow, provider: AIProvider,
                 database: RunDatabase, limits: RunLimits,
                 backend: WindowsMCPBackend | None = None):
        super().__init__()
        self.target = target
        self.provider = provider
        self.database = database
        self.limits = limits
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.approve_event = threading.Event()
        self.backend = backend
        self.camera = backend if backend else ScreenCaptureEngine()
        self.uia = UIAReader()
        self.ocr = OCREngine()
        self.mouse = AnswerExecutor(backend, reader=self._recognize) if backend else MouseController()
        self.adapter = ChaoxingAdapter() if ChaoxingAdapter.applies(target.process_name, target.title) else None
        self.machine = StateMachine()
        self._stage_started_at = None

    def stop(self):
        self.stop_event.set()
        self.approve_event.set()
        if self.backend:
            self.backend.cancel_pending()

    def pause(self):
        self.pause_event.set()

    def resume(self):
        self.pause_event.clear()

    def approve(self):
        self.approve_event.set()

    def _wait_if_paused(self):
        if self.pause_event.is_set():
            self.status.emit("PAUSED")
            while self.pause_event.is_set() and not self.stop_event.wait(0.1):
                pass
            if self.stop_event.is_set():
                raise RuntimeError("Stopped")
            ensure_target(self.target)

    def _step(self, state: RunState):
        previous = self.machine.state
        self.machine.advance(state)
        now = time.monotonic()
        if self._stage_started_at is not None:
            self._log(previous.value, f"阶段完成；耗时={now - self._stage_started_at:.2f}s")
        self._stage_started_at = now
        self.status.emit(state.value)
        self._log(state.value, f"阶段={state.value}")

    def _log_exception(self, state: str, stage: str, exc: Exception):
        elapsed = (f"；阶段耗时={time.monotonic() - self._stage_started_at:.2f}s"
                   if self._stage_started_at is not None else "")
        self._log("TRACEBACK", traceback.format_exc(limit=8))
        self._log(state, f"出错阶段={stage}{elapsed}；{type(exc).__name__}: {exc}")

    def _log(self, state: str, detail: str):
        safe = redact(detail)
        self.database.log(self.target.pid, state, detail=safe)
        self.trace.emit(f"{datetime.now().strftime('%H:%M:%S')} [{state}] {safe}")

    def _metrics(self, progress: RunProgress):
        self.metrics.emit(progress.recognized, progress.selected, progress.clicked,
                          self.provider.usage.upper_cost_usd,
                          getattr(self.provider.usage, "calls", 0))

    def _recognize(self, shot):
        if self.backend:
            if self.target.process_name.lower() in {
                    "msedge.exe", "chrome.exe", "firefox.exe", "brave.exe", "opera.exe"}:
                # Browser accessibility trees cover many tabs and controls. The
                # target-scoped capture is already available, so do not scan
                # the entire desktop before reading the visible quiz.
                return self.ocr.read(shot)
            try:
                found = self.uia.read(self.target)
                if found:
                    return found
            except Exception as exc:
                self._log("RECOGNIZE", f"目标窗口 UIA 不可用：{type(exc).__name__}: {exc}")
            found = self.ocr.read(shot)
            if found or self.machine.state != RunState.RECOGNIZE:
                return found
            # Desktop Snapshot is only a bounded initial fallback. During
            # selection and page loading it can traverse unrelated windows
            # and delay the state checks beyond their deadlines.
            return self.backend.read(self.target)
        try:
            found = self.uia.read(self.target)
            if found:
                return found
        except Exception:
            pass
        return self.ocr.read(shot)

    def _emit_preview(self, shot, observed):
        image = shot.image.copy()
        if observed:
            for option in observed.options.values():
                rect = option.rect
                x = rect.left - shot.screen_rect.left
                y = rect.top - shot.screen_rect.top
                cv2.rectangle(image, (x, y), (x + rect.width, y + rect.height), (51, 214, 112), 2)
            if observed.next_rect:
                rect = observed.next_rect
                x = rect.left - shot.screen_rect.left
                y = rect.top - shot.screen_rect.top
                cv2.rectangle(image, (x, y), (x + rect.width, y + rect.height), (255, 173, 51), 2)
        self.preview.emit(image)

    def _wait_for_new(self, old_fingerprint: str, deadline: float):
        while time.monotonic() < deadline and not self.stop_event.is_set():
            self._wait_if_paused()
            ensure_target(self.target)
            shot = self.camera.capture(self.target)
            found = self._recognize(shot)
            if found and (found.finished or found.fingerprint != old_fingerprint):
                return found
            self.stop_event.wait(0.4)
        raise RuntimeError("New question did not appear within 15 seconds")

    def _cycle(self, progress: RunProgress) -> bool:
        self.current_counted = False
        if time.monotonic() - progress.started >= self.limits.max_seconds:
            raise FatalAutomationError("Maximum runtime reached")
        if self.provider.usage.upper_cost_usd >= self.limits.max_cost_usd:
            raise FatalAutomationError("Cost budget reached")
        ensure_target(self.target)
        cursor = win32api.GetCursorPos()
        shot = self.camera.capture(self.target)
        self._log("CAPTURE", f"目标 HWND={self.target.hwnd} PID={self.target.pid}；截图={shot.image.shape[1]}x{shot.image.shape[0]}")
        self._step(RunState.RECOGNIZE)
        observed = self._recognize(shot)
        self._emit_preview(shot, observed)
        if not observed:
            raise RuntimeError("Could not recognize a reliable question")
        if observed.finished:
            self._log("FINISHED", "页面显示练习完成")
            return True
        self._log("RECOGNIZE", f"来源={observed.source}；题型={observed.question_type}；"
                  f"选项={','.join(sorted(observed.options))}；下一题={'有' if observed.next_rect else '无'}；"
                  f"题目指纹={observed.fingerprint[:12]}")
        if self.adapter:
            self.adapter.assert_allowed(observed,
                self.backend.last_snapshot_text if self.backend else "")
        self.current_fingerprint = observed.fingerprint
        if observed.fingerprint in progress.seen:
            raise RuntimeError("Repeated question detected")
        progress.seen.add(observed.fingerprint)
        progress.recognized += 1
        self.current_counted = True
        # Reading an already captured image can continue after focus changes,
        # but do not spend API budget after another window takes control.
        ensure_target(self.target)
        self._step(RunState.ANALYZE)
        if self.limits.mode == "auto":
            with MouseActivityGuard(win32api.GetCursorPos) as guard:
                answer = self.provider.analyze(observed, shot.image, self.limits.use_vision)
            if guard.moved:
                raise RuntimeError("User moved mouse during AI analysis")
        else:
            answer = self.provider.analyze(observed, shot.image, self.limits.use_vision)
        self.question.emit("", ",".join(answer.answers), "")
        self._log("REQUEST_AI", f"AI 题型={answer.question_type}；答案={','.join(answer.answers)}；"
                  f"请求={self.provider.usage.calls}；输入/输出 token="
                  f"{self.provider.usage.input_tokens}/{self.provider.usage.output_tokens}；"
                  f"费用上界=${self.provider.usage.upper_cost_usd:.6f}")
        self._metrics(progress)
        if self.limits.mode == "assist":
            return True
        self._step(RunState.LOCATE)
        if self.limits.mode == "semi":
            self.approve_event.clear()
            self.approval_needed.emit()
            while not self.approve_event.wait(0.1):
                if self.stop_event.is_set():
                    return True
                self._wait_if_paused()
        if self.stop_event.is_set():
            return True
        self._wait_if_paused()
        ensure_target(self.target)
        fresh = self._recognize(self.camera.capture(self.target))
        if not fresh or fresh.fingerprint != observed.fingerprint:
            raise RuntimeError("Question changed before selection")
        if win32api.GetCursorPos() != cursor and self.limits.mode == "auto":
            raise RuntimeError("User moved mouse; automation paused")
        self._step(RunState.SELECT)
        for label in answer.answers:
            if self.stop_event.is_set():
                return True
            self._wait_if_paused()
            fresh = self._recognize(self.camera.capture(self.target))
            if not fresh or fresh.fingerprint != observed.fingerprint:
                raise RuntimeError("Question changed during selection")
            if label not in fresh.options:
                raise RuntimeError("Answer option moved or disappeared")
            self._log("CLICK", f"选项={label}；位置={fresh.options[label].rect.center}；开始验证")
            self.mouse.click_option(self.target, fresh.options[label],
                                    cursor if self.limits.mode == "auto" else None)
            self._log("VERIFY", f"选项={label}；选择状态已确认")
            cursor = win32api.GetCursorPos()
            progress.clicked += 1
        progress.selected += 1
        self.selected_current = True
        self._step(RunState.VERIFY)
        self._metrics(progress)
        if self.stop_event.is_set():
            return True
        self._wait_if_paused()
        fresh = self._recognize(self.camera.capture(self.target))
        if not fresh or fresh.fingerprint != observed.fingerprint:
            raise RuntimeError("Question changed before next click")
        self._step(RunState.NEXT)
        self._log("NEXT", f"下一题位置={fresh.next_rect.center if fresh.next_rect else '未找到'}")
        self.mouse.click_next(self.target, fresh)
        self._step(RunState.WAIT)
        if self.limits.mode == "auto":
            with MouseActivityGuard(win32api.GetCursorPos) as guard:
                next_observed = self._wait_for_new(observed.fingerprint, time.monotonic() + 15)
            if guard.moved:
                raise RuntimeError("User moved mouse while next question loaded")
        else:
            next_observed = self._wait_for_new(observed.fingerprint, time.monotonic() + 15)
        if next_observed.finished:
            self._log("FINISHED", "翻页后检测到完成页面")
            return True
        self._log("WAIT", f"新题已出现；题目指纹={next_observed.fingerprint[:12]}")
        if self.adapter and self.backend:
            self.backend.reset_recognition_strategy()
        self._step(RunState.CAPTURE)
        self.current_fingerprint = None
        self.selected_current = False
        self.current_counted = False
        return False

    @Slot()
    def run(self):
        try:
            if self.backend:
                self.status.emit("MCP 连接中")
                self.backend.start()
            self._stage_started_at = time.monotonic()
            self._run_loop()
        except Exception as exc:
            failed_stage = self.machine.state.value
            self.machine.advance(RunState.ERROR)
            self._log_exception("ERROR", failed_stage, exc)
            self.status.emit(f"运行异常：{exc}")
            self.finished.emit("运行异常")
        finally:
            if self.backend:
                self.backend.stop()

    def _run_loop(self):
        progress = RunProgress(time.monotonic())
        self.current_fingerprint = None
        self.selected_current = False
        self.current_counted = False
        failures = {}
        completed = False
        while not self.stop_event.is_set() and progress.recognized < self.limits.max_questions:
            try:
                if self.limits.mode != "assist" and self.provider.price_per_million is None:
                    raise FatalAutomationError("Unknown model pricing; automatic cost budget cannot be enforced")
                if self.pause_event.is_set():
                    self.machine.advance(RunState.PAUSED)
                    self._wait_if_paused()
                    self.machine.advance(RunState.CAPTURE)
                if self._cycle(progress):
                    completed = not self.stop_event.is_set()
                    break
            except FatalAutomationError as exc:
                self._log_exception("STOPPED", self.machine.state.value, exc)
                self._metrics(progress)
                self.status.emit(f"已停止：{exc}")
                break
            except Exception as exc:
                failed_stage = self.machine.state.value
                self.machine.advance(RunState.PAUSED)
                self._log_exception("PAUSED", failed_stage, exc)
                self._metrics(progress)
                self.status.emit(f"已暂停：{exc}")
                failed = self.current_fingerprint
                failures[failed] = failures.get(failed, 0) + 1
                self.pause_event.set()
                while self.pause_event.is_set() and not self.stop_event.wait(0.1):
                    pass
                if self.stop_event.is_set():
                    break
                try:
                    ensure_target(self.target)
                    current = self._recognize(self.camera.capture(self.target))
                    if self.selected_current and current and current.fingerprint == failed:
                        raise RuntimeError("Please manually advance past the selected question")
                    if failures[failed] >= 2 and current and current.fingerprint == failed:
                        self.stop_event.set()
                        raise RuntimeError("Repeated failure; stopped for manual handling")
                    if failed and self.current_counted and not self.selected_current:
                        progress.seen.discard(failed)
                        progress.recognized = max(0, progress.recognized - 1)
                    self.machine.advance(RunState.CAPTURE)
                    self.current_fingerprint = None
                    self.selected_current = False
                    self.current_counted = False
                except Exception as resume_error:
                    self.status.emit(f"已暂停：{resume_error}")
                    self.pause_event.set()
        final_state = RunState.FINISHED if completed else RunState.STOPPED
        self.machine.advance(final_state)
        self._log(final_state.value, "任务结束")
        self.finished.emit("任务完成" if completed else "已停止")


class AutoTaskController(AutomationController):
    """Windows client choice-task controller with bounded state transitions."""
