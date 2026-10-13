from app.storage.database import RunDatabase


def test_event_log_redacts_api_key(tmp_path):
    database = RunDatabase(tmp_path / "runs.db")
    test_key = "sk-" + "x" * 32
    database.log(1, "PAUSED", detail=f"request failed for {test_key}")
    saved = database.connection.execute("SELECT detail FROM events").fetchone()[0]
    assert test_key not in saved
    assert "[REDACTED]" in saved


def test_event_log_redacts_authorization_and_assignment(tmp_path):
    database = RunDatabase(tmp_path / "runs.db")
    database.log(1, "ERROR", detail='Authorization: Bearer opaque-value-123; api_key=opaque-value-456; "api_key": "opaque-value-789"')
    saved = database.connection.execute("SELECT detail FROM events").fetchone()[0]
    assert "opaque-value-123" not in saved
    assert "opaque-value-456" not in saved
    assert "opaque-value-789" not in saved
    assert saved.count("[REDACTED]") == 3
