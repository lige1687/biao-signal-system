"""Latest saved signals preserve original dates and never migrate or scan."""
import hashlib
from contextlib import closing
from types import SimpleNamespace

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import upsert_scan_results
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.api.signal_alerts_store import upsert_signal_alerts
from lei_signal.storage.sqlite_store import connect


def _app(path):
    app = create_app(analysis_service=SimpleNamespace())
    app.state.plans_db_path = str(path)
    return app


def _save(path, day):
    with closing(connect(str(path))) as conn:
        upsert_scan_results(conn, day, [ScanItemDTO(
            symbol="510300.SS", display_name="沪深300ETF", verdict="waiting", verdict_cn="等待条件"
        )])
        upsert_signal_alerts(conn, day, "close", [])
        conn.execute(
            "UPDATE daily_opportunity_scan SET generated_at=? WHERE scan_date=?",
            (day + "T07:05:00+00:00", day),
        )
        conn.commit()


def test_latest_preserves_saved_date_and_does_not_write(tmp_path, monkeypatch):
    from lei_signal.api.routes import signals
    monkeypatch.setattr(signals, "today_date", lambda: "2026-10-18")
    path = tmp_path / "signals.db"
    _save(path, "2026-10-15")
    _save(path, "2026-10-16")
    _save(path, "2026-10-19")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with TestClient(_app(path)) as client:
        body = client.get('/api/signals/latest').json()
    assert body['scan_date'] == '2026-10-16'
    assert body['generated_at'] == '2026-10-16T07:05:00+00:00'
    assert body['waiting'][0]['symbol'] == '510300.SS'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_latest_missing_database_is_not_created(tmp_path):
    path = tmp_path / 'missing.db'
    with TestClient(_app(path)) as client:
        response = client.get('/api/signals/latest')
    assert response.status_code == 200
    assert response.json()['available'] is False
    assert not path.exists()


def test_latest_ignores_malformed_scan_dates(tmp_path, monkeypatch):
    from lei_signal.api.routes import signals
    monkeypatch.setattr(signals, "today_date", lambda: "2026-10-18")
    path = tmp_path / 'signals.db'
    _save(path, '2026-10-16')
    _save(path, '2026-10-17x')
    with TestClient(_app(path)) as client:
        body = client.get('/api/signals/latest').json()
    assert body['scan_date'] == '2026-10-16'


def test_latest_legacy_database_has_no_schema_changes(tmp_path):
    import sqlite3
    path = tmp_path / 'legacy.db'
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('CREATE TABLE retained (value TEXT)')
        conn.commit()
    before = path.read_bytes()
    with TestClient(_app(path)) as client:
        body = client.get('/api/signals/latest').json()
    assert body['available'] is False
    assert path.read_bytes() == before
