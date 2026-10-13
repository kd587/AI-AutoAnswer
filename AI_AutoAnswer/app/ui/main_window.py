import ctypes
import ctypes.wintypes
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import win32con
import win32api
import win32gui
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QSpinBox,
    QSplitter, QTextEdit, QVBoxLayout, QWidget)

from app.ai.deepseek_client import AIProvider
from app.automation.window_manager import (TargetWindow, ensure_target, list_windows,
                                            request_target_foreground, target_from_point)
from app.automation.windows_mcp_backend import WindowsMCPBackend
from app.core.controller import AutoTaskController, RunLimits
from app.storage.config import load_api_key, save_api_key
from app.storage.database import RunDatabase
from app.storage.database import redact


class WindowPicker(QPushButton):
    picked = Signal(object)
    failed = Signal(str)
    hovered = Signal(str)

    def __init__(self):
        super().__init__("拖动准星选窗口")
        self._dragging = False
        self._last_probe = 0.0

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self._dragging = True
        self.setDown(True)
        self.setText("拖到目标窗口后松开")
        self.grabMouse(QCursor(Qt.CrossCursor))
        event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and time.monotonic() - self._last_probe >= 0.2:
            self._last_probe = time.monotonic()
            try:
                target = target_from_point(*win32api.GetCursorPos())
                self.hovered.emit(f"准星指向：{target.title} | PID {target.pid}")
            except Exception:
                self.hovered.emit("准星指向：无可选窗口")
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._dragging:
            super().mouseReleaseEvent(event)
            return
        self._dragging = False
        self.releaseMouse()
        self.setDown(False)
        self.setText("拖动准星选窗口")
        try:
            self.picked.emit(target_from_point(*win32api.GetCursorPos()))
        except Exception as exc:
            self.failed.emit(str(exc))
        event.accept()


class MainWindow(QMainWindow):
    connection_result = Signal(str)
    mcp_result = Signal(str)

    def __init__(self, start_mcp: bool = True):
        super().__init__()
        self.setWindowTitle("AI AutoAnswer 2026.10.12 日志版")
        self.resize(850, 590)
        self.target = None
        self.worker = None
        self.thread = None
        self._handoff_pending = False
        self._handoff_generation = 0
        self.failed_count = 0
        self._last_metrics = (0, 0, 0, 0.0, 0)
        self.db = RunDatabase(Path.home() / "AppData" / "Local" / "AI_AutoAnswer" / "runs.db")
        self.backend = WindowsMCPBackend()
        self.connection_result.connect(self._connection_result)
        self.mcp_result.connect(self.mcp_status_update)
        self._build()
        self.refresh_windows()
        self._register_hotkey()
        self.mcp_boot = None
        if start_mcp:
            self.mcp_boot = threading.Thread(target=self._start_mcp, daemon=True)
            self.mcp_boot.start()

    def _start_mcp(self):
        try:
            self.backend.start()
            self.mcp_result.emit("MCP：已连接")
        except Exception as exc:
            self.mcp_result.emit(f"MCP：启动失败：{exc}")

    def mcp_status_update(self, status):
        self.mcp_status.setText(redact(status))
        self._append_event(status)

    def _build(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        left = QFrame()
        left.setObjectName("panel")
        form = QFormLayout(left)
        self.key = QLineEdit(load_api_key())
        self.key.setEchoMode(QLineEdit.Password)
        self.model = QLineEdit("deepseek-flash")
        self.url = QLineEdit("https://api.deepseek.com")
        self.timeout = QSpinBox(); self.timeout.setRange(5, 120); self.timeout.setValue(30)
        self.retries = QSpinBox(); self.retries.setRange(0, 5); self.retries.setValue(2)
        self.windows = QComboBox()
        self.max_questions = QSpinBox(); self.max_questions.setRange(1, 10000); self.max_questions.setValue(30)
        self.max_minutes = QSpinBox(); self.max_minutes.setRange(1, 600); self.max_minutes.setValue(30)
        self.budget = QDoubleSpinBox(); self.budget.setRange(0.01, 1000); self.budget.setValue(1.0)
        self.budget.setPrefix("$ ")
        test = QPushButton("测试连接"); test.clicked.connect(self.test_connection)
        refresh = QPushButton("刷新窗口"); refresh.clicked.connect(self.refresh_windows)
        picker = WindowPicker(); picker.picked.connect(self._picked_window)
        picker.failed.connect(self._picker_failed)
        picker.hovered.connect(self._picker_hovered)
        for label, widget in [("API Key", self.key), ("模型", self.model), ("API 地址", self.url),
                              ("超时/秒", self.timeout), ("重试次数", self.retries),
                              ("目标客户端", self.windows),
                              ("最大题量", self.max_questions), ("最长运行/分钟", self.max_minutes),
                              ("费用预算上限", self.budget)]:
            form.addRow(label, widget)
        form.addRow(test); form.addRow(refresh); form.addRow(picker)
        form.addRow(QLabel("浏览器请选择题库标签页；切换标签页会暂停。"))
        splitter.addWidget(left)

        right = QFrame(); right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        self.status = QLabel("待机")
        self.mcp_status = QLabel("MCP：连接中")
        self.metrics = QLabel("识别 0 | 处理 0 | 操作 0 | 失败 0\nAPI 0 次 | 费用上界 $0.0000")
        self.events = QTextEdit(); self.events.setReadOnly(True)
        self.events.document().setMaximumBlockCount(3000)
        self.events.setPlaceholderText("运行步骤、阶段耗时、点击验证和异常调用栈显示在这里")
        copy_log = QPushButton("复制当前日志"); copy_log.clicked.connect(self.copy_log)
        export = QPushButton("导出完整日志 CSV"); export.clicked.connect(self.export_log)
        right_layout.addWidget(QLabel("运行状态")); right_layout.addWidget(self.status)
        right_layout.addWidget(self.mcp_status)
        right_layout.addWidget(self.metrics); right_layout.addWidget(self.events, 1)
        log_actions = QHBoxLayout(); log_actions.addWidget(copy_log); log_actions.addWidget(export)
        right_layout.addLayout(log_actions)
        splitter.addWidget(right)
        splitter.setSizes([410, 410])

        controls = QHBoxLayout()
        for text, handler in [("开始", self.start), ("暂停", self.pause), ("继续", self.resume),
                              ("停止", self.stop)]:
            button = QPushButton(text); button.clicked.connect(handler); controls.addWidget(button)
        outer.addLayout(controls)
        outer.addWidget(QLabel("紧急停止：Ctrl+Shift+F12。自动运行期间请保持目标页在前台；点击其他窗口会暂停。"))
        self.setCentralWidget(root)
        self.setStyleSheet("""QMainWindow,QWidget {background:#0f172a;color:#e2e8f0;font-size:13px}
            QFrame#panel {background:#1e293b;border:1px solid #334155;border-radius:8px;margin:4px}
            QPushButton {background:#2563eb;border:0;border-radius:5px;padding:9px;color:white}
            QPushButton:hover {background:#3b82f6} QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTextEdit
            {background:#0f172a;border:1px solid #475569;border-radius:4px;padding:5px;color:#e2e8f0}""")

    def _register_hotkey(self):
        try:
            win32gui.RegisterHotKey(int(self.winId()), 1,
                win32con.MOD_CONTROL | win32con.MOD_SHIFT, win32con.VK_F12)
            self.hotkey_registered = True
        except Exception:
            self.hotkey_registered = False
        if not self.hotkey_registered:
            self._append_event("警告：全局紧急停止快捷键注册失败")

    def nativeEvent(self, event_type, message):
        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == win32con.WM_HOTKEY and msg.wParam == 1:
            self.stop()
            return True, 0
        return super().nativeEvent(event_type, message)

    def refresh_windows(self):
        self.windows.clear()
        self.windows.addItem("请选择目标客户端", None)
        for item in list_windows(os.getpid()):
            self.windows.addItem(f"{item.title} | {item.process_name} | PID {item.pid} | HWND {item.hwnd} | {item.state}", item)

    def _picker_hovered(self, detail):
        self.status.setText(detail)

    def _append_event(self, detail):
        safe = redact(str(detail))
        self.events.append(f"{datetime.now().strftime('%H:%M:%S')} [UI] {safe}")
        database = getattr(self, "db", None)
        if database is not None:
            target = getattr(self, "target", None)
            try:
                database.log(target.pid if target else None, "UI", detail=safe)
            except Exception as exc:
                self.events.append(f"{datetime.now().strftime('%H:%M:%S')} [ERROR] "
                                   f"日志写入失败：{redact(str(exc))}")

    def copy_log(self):
        QApplication.clipboard().setText(self.events.toPlainText())
        self._append_event("界面日志已复制到剪贴板")

    def export_log(self):
        default = str(Path.home() / "Desktop" / "AI_AutoAnswer_运行日志.csv")
        path, _ = QFileDialog.getSaveFileName(self, "导出运行日志", default, "CSV 文件 (*.csv)")
        if path:
            try:
                self.db.export_csv(Path(path))
                self._append_event(f"日志已导出：{path}")
            except Exception as exc:
                self._append_event(f"日志导出失败：{type(exc).__name__}: {exc}")

    def _picked_window(self, target):
        if target.pid == os.getpid():
            self._picker_failed("请选择目标窗口，不能选择 AI AutoAnswer 自身")
            return
        self.target = target
        for index in range(self.windows.count()):
            current = self.windows.itemData(index)
            if current is not None and current.hwnd == target.hwnd:
                self.windows.setItemData(index, target)
                self.windows.setItemText(index, f"{target.title} | {target.process_name} | PID {target.pid} | HWND {target.hwnd} | {target.state}")
                self.windows.setCurrentIndex(index)
                self.status.setText(f"已选目标窗口：{target.title}")
                self._append_event(f"准星锁定窗口：{target.title}；PID={target.pid}；HWND={target.hwnd}")
                return
        self.windows.addItem(f"{target.title} | {target.process_name} | PID {target.pid} | HWND {target.hwnd}", target)
        self.windows.setCurrentIndex(self.windows.count() - 1)
        self.status.setText(f"已选目标窗口：{target.title}")
        self._append_event(f"准星锁定窗口：{target.title}；PID={target.pid}；HWND={target.hwnd}")

    def _picker_failed(self, detail):
        message = f"目标窗口选择失败：{detail}"
        self.status.setText(message)
        self._append_event(message)

    def _provider(self):
        key = self.key.text().strip()
        if not key:
            raise ValueError("请先输入 API Key")
        save_api_key(key)
        return AIProvider(key, self.model.text().strip(), self.url.text().strip(),
                          self.timeout.value(), self.retries.value())

    def test_connection(self):
        try:
            provider = self._provider()
        except Exception as exc:
            self.status.setText(str(exc)); return
        threading.Thread(target=lambda: self._test_in_thread(provider), daemon=True).start()

    def _test_in_thread(self, provider):
        try:
            self.connection_result.emit("连接成功：" + provider.test_connection())
        except Exception as exc:
            self.connection_result.emit("连接失败：" + str(exc))

    def _connection_result(self, result):
        if self.worker is None:
            self.status.setText(redact(result))
        self._append_event(result)

    def _selected_target(self):
        target = self.windows.currentData()
        if target is None:
            raise ValueError("请先选择客户端")
        self.target = target
        return target

    def _handoff(self, target, on_ready, action, generation):
        if generation != self._handoff_generation:
            return
        try:
            self._append_event(f"{action}：校验目标 HWND={target.hwnd} PID={target.pid}；"
                               f"当前状态={'最小化' if win32gui.IsIconic(target.hwnd) else '可见'}")
            request_target_foreground(target)
        except Exception as exc:
            self._handoff_failed(action, exc)
            return
        QTimer.singleShot(300, lambda: self._verify_handoff(target, on_ready, action, 0, generation))

    def _verify_handoff(self, target, on_ready, action, attempt, generation):
        if generation != self._handoff_generation:
            return
        try:
            ensure_target(target)
        except Exception as exc:
            if attempt < 2 and "not foreground" in str(exc):
                QTimer.singleShot(200, lambda: self._verify_handoff(target, on_ready, action,
                                                                     attempt + 1, generation))
                return
            self._handoff_failed(action, exc)
            return
        self._handoff_pending = False
        if self.windows.currentData() == target and "minimized" in self.windows.currentText():
            self.windows.setItemText(self.windows.currentIndex(),
                                     self.windows.currentText().replace("minimized", "visible"))
        self._append_event(f"{action}：目标已恢复并处于前台，身份校验通过")
        on_ready()

    def _handoff_failed(self, action, exc):
        self._handoff_pending = False
        message = (f"{action}失败：{type(exc).__name__}: {exc}。"
                   f"请先打开目标窗口并使其位于前台，然后重新点击{'开始' if action == '启动' else '继续'}")
        self.status.setText(redact(message))
        self._append_event(message)

    def start(self):
        if self._handoff_pending or (self.thread and self.thread.isRunning()):
            return
        try:
            provider = self._provider()
            target = self._selected_target()
            limits = RunLimits(self.max_questions.value(), self.max_minutes.value() * 60,
                               self.budget.value(), "auto", False)
            self._handoff_pending = True
            self._handoff_generation += 1
            generation = self._handoff_generation
            self.status.setText("正在恢复并切换到目标窗口")
            QTimer.singleShot(100, lambda: self._handoff(
                target, lambda: self._launch_worker(target, provider, limits), "启动", generation))
        except Exception as exc:
            self.status.setText(f"启动失败：{exc}")
            self._append_event(f"启动失败：{type(exc).__name__}: {exc}")

    def _launch_worker(self, target, provider, limits):
        try:
            self.worker = AutoTaskController(target, provider, self.db, limits,
                                             backend=self.backend)
            self.thread = QThread(self)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.status.connect(self._show_status)
            self.worker.metrics.connect(self._show_metrics)
            self.worker.trace.connect(self.events.append)
            self.worker.finished.connect(self._finished)
            self.worker.finished.connect(self.thread.quit)
            self.thread.finished.connect(self.worker.deleteLater)
            self.thread.start()
            self._append_event(f"开始任务：目标={target.title}；PID={target.pid}；HWND={target.hwnd}；"
                               f"最多={limits.max_questions}题；最长={limits.max_seconds}秒；预算=${limits.max_cost_usd:.2f}")
        except Exception as exc:
            self.status.setText(f"启动失败：{exc}")
            self._append_event(f"启动失败：{type(exc).__name__}: {exc}")

    def _show_status(self, status):
        status = redact(status)
        self.status.setText(status)
        if status.startswith(("已暂停", "运行异常")):
            self.failed_count += 1
            self._show_metrics(*self._last_metrics)
            self._append_event(status)
        elif status.startswith("已停止："):
            self._append_event(status)
        self.mcp_status.setText("MCP：连接中" if status == "MCP 连接中" else
                                "MCP：已连接" if status in {"CAPTURE", "RECOGNIZE", "REQUEST_AI", "LOCATE", "CLICK", "VERIFY", "NEXT", "WAIT"} else
                                "MCP：已断开" if status.startswith("运行异常") else self.mcp_status.text())

    def _show_metrics(self, recognized, selected, clicked, cost, calls):
        self._last_metrics = (recognized, selected, clicked, cost, calls)
        self.metrics.setText(f"识别 {recognized} | 处理 {selected} | 操作 {clicked} | 失败 {self.failed_count}\n"
                             f"API {calls} 次 | 费用上界 ${cost:.4f}")

    def _finished(self, text):
        if not self.status.text().startswith(("已暂停：", "运行异常：", "已停止：")):
            self.status.setText(text)
        self.mcp_status.setText("MCP：已断开")
        self._append_event(text)

    def pause(self):
        if self.worker: self.worker.pause()

    def resume(self):
        if self.worker and not self._handoff_pending:
            try:
                target = self._selected_target()
                if target.hwnd != self.worker.target.hwnd:
                    raise RuntimeError("恢复时不能更换目标窗口，请先停止当前任务")
                self._handoff_pending = True
                self._handoff_generation += 1
                generation = self._handoff_generation
                self.status.setText("正在切换到目标窗口")
                QTimer.singleShot(100, lambda: self._handoff(target, self.worker.resume,
                                                               "恢复", generation))
            except Exception as exc:
                self.status.setText(str(exc))
                self._append_event(f"恢复失败：{type(exc).__name__}: {exc}")

    def stop(self):
        self._handoff_generation += 1
        self._handoff_pending = False
        if self.worker: self.worker.stop()
        self.status.setText("停止中")

    def closeEvent(self, event):
        self.stop()
        if self.thread and self.thread.isRunning():
            event.ignore()
            QTimer.singleShot(500, self.close)
            return
        if getattr(self, "hotkey_registered", False):
            win32gui.UnregisterHotKey(int(self.winId()), 1)
        if self.mcp_boot and self.mcp_boot.is_alive():
            self.mcp_boot.join(timeout=5)
        self.backend.stop()
        super().closeEvent(event)
