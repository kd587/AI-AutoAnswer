import csv
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class RunDatabase:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        self.connection.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, at TEXT NOT NULL, pid INTEGER, state TEXT NOT NULL,
            question TEXT, answers TEXT, detail TEXT)""")
        self.connection.commit()

    def log(self, pid: int | None, state: str, question: str = "",
            answers: str = "", detail: str = "") -> None:
        detail = redact(detail)
        with self._lock:
            self.connection.execute("INSERT INTO events(at,pid,state,question,answers,detail) VALUES(?,?,?,?,?,?)",
                                    (datetime.now(timezone.utc).isoformat(), pid, state, question, answers, detail))
            self.connection.commit()

    def export_csv(self, path: Path) -> None:
        with self._lock:
            rows = self.connection.execute(
                "SELECT at,pid,state,question,answers,detail FROM events ORDER BY id").fetchall()
        with path.open("w", newline="", encoding="utf-8-sig") as output:
            writer = csv.writer(output)
            writer.writerow(["time_utc", "pid", "state", "question", "answers", "detail"])
            writer.writerows(rows)


def redact(value: str) -> str:
    safe = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[REDACTED]", value)
    safe = re.sub(r"(?i)(\bBearer\s+)[^\s;,'\"]+", r"\1[REDACTED]", safe)
    return re.sub(r"(?i)(\bapi[_-]?key['\"]?\s*[=:]\s*['\"]?)[^\s;,'\"}]+",
                  r"\1[REDACTED]", safe)
