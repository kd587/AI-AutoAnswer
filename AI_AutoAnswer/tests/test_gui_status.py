from types import SimpleNamespace
import csv

from app.ui.main_window import MainWindow
from app.storage.database import RunDatabase


class Label:
    def __init__(self, value=""):
        self.value = value

    def setText(self, value):
        self.value = value

    def text(self):
        return self.value


class Events:
    def __init__(self):
        self.items = []

    def append(self, value):
        self.items.append(value)


def test_connection_result_does_not_hide_automation_failure():
    view = SimpleNamespace(status=Label("已暂停：无法识别题目"), events=Events(), worker=object())
    view._append_event = lambda detail: MainWindow._append_event(view, detail)
    MainWindow._connection_result(view, "连接成功：OK")
    assert view.status.text() == "已暂停：无法识别题目"
    assert "连接成功：OK" in view.events.items[0]


def test_pause_reason_is_kept_in_visible_event_log():
    view = SimpleNamespace(status=Label("待机"), mcp_status=Label("MCP：已连接"),
                           metrics=Label(), failed_count=0, _last_metrics=(0, 0, 0, 0.0, 0),
                           events=Events())
    view._show_metrics = lambda *args: None
    view._append_event = lambda detail: MainWindow._append_event(view, detail)
    MainWindow._show_status(view, "已暂停：目标窗口不在前台")
    assert view.failed_count == 1
    assert "已暂停：目标窗口不在前台" in view.events.items[0]


def test_finished_signal_does_not_erase_error_reason():
    view = SimpleNamespace(status=Label("运行异常：截图不可用"),
                           mcp_status=Label("MCP：已连接"), events=Events())
    view._append_event = lambda detail: MainWindow._append_event(view, detail)
    MainWindow._finished(view, "运行异常")
    assert view.status.text() == "运行异常：截图不可用"
    assert view.mcp_status.text() == "MCP：已断开"


def test_ui_event_is_visible_and_in_export_database():
    class Database:
        def __init__(self): self.rows = []
        def log(self, pid, state, detail="", **kwargs): self.rows.append((pid, state, detail))

    database = Database()
    view = SimpleNamespace(events=Events(), db=database, target=None)
    MainWindow._append_event(view, "准星锁定窗口：练习页")
    assert "准星锁定窗口：练习页" in view.events.items[0]
    assert database.rows == [(None, "UI", "准星锁定窗口：练习页")]


def test_ui_event_is_in_exported_csv(tmp_path):
    database = RunDatabase(tmp_path / "runs.db")
    view = SimpleNamespace(events=Events(), db=database, target=None)
    MainWindow._append_event(view, "连接测试成功")
    output = tmp_path / "events.csv"
    database.export_csv(output)
    with output.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert rows[0]["state"] == "UI"
    assert rows[0]["detail"] == "连接测试成功"
