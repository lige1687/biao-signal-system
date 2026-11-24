import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from lei_signal.strategy_portfolios import runner, service


def test_frozen_event_survives_restart_and_duplicate_source(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "binding", lambda: {"synthetic": "fixed"})
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps({"received_at": "2026-10-20T09:00:00+00:00", "markets": {"CN": {}, "US": {}}})
    )
    locator = tmp_path / "locator.json"
    locator.write_text(
        json.dumps(
            {
                "snapshot": str(source),
                "snapshot_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    )
    active = tmp_path / "active"
    first = service.ingest(locator, active, "2026-10-20T10:00:00+00:00")
    second = service.ingest(locator, active, "2026-10-20T11:00:00+00:00")
    assert first == second == service.read_state(active)
    with service.connect(active) as conn:
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 1
    monkeypatch.setattr(service, "binding", lambda: {"synthetic": "changed"})
    import pytest

    with pytest.raises(ValueError, match="冻结代码"):
        service.ingest(locator, active, "2026-10-20T12:00:00+00:00")


def test_shared_capital_is_average_nav_not_average_daily_returns():
    def rows(values):
        previous = 100000
        result = []
        for i, value in enumerate(values):
            result.append(
                {
                    "date": f"2026-10-{20 + i}",
                    "equity": value,
                    "cash": 0,
                    "return": value / previous - 1,
                    "exposure": 1,
                    "unknown_weight": 0,
                }
            )
            previous = value
        return result

    result = service.combined_forward(
        {"mv": {"series": rows([200000, 100000])}, "rv": {"series": rows([100000, 200000])}}
    )
    assert result["series"][-1]["equity"] == 150000
    assert result["series"][-1]["return"] == 0


def test_calendar_union_and_interrupted_collection_reuses_source(tmp_path, monkeypatch):
    # US Thanksgiving is still a CN trading day.
    assert service.next_collection("2026-11-26T12:00:00-05:00").startswith("2026-11-26")

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 26, 17, 10, tzinfo=ZoneInfo("America/New_York")).astimezone(
                tz
            )

    monkeypatch.setattr(runner, "datetime", Clock)
    with service.connect(tmp_path) as conn:
        conn.execute(
            "INSERT INTO runs VALUES (?,?,?,?)",
            ("2026-11-26", "2026-11-26T22:01:00+00:00", "running", '{"attempt":1}'),
        )
    locator = tmp_path / "source-2026-11-26-1.json"
    locator.write_text("{}")
    received = []
    monkeypatch.setattr(runner, "ingest", lambda p, a: received.append(p) or {"markets": {}})
    monkeypatch.setattr(
        runner, "collect", lambda **k: (_ for _ in ()).throw(AssertionError("redownload"))
    )
    runner.tick(tmp_path)
    runner.tick(tmp_path)
    assert received == [locator]
    with service.connect(tmp_path) as conn:
        assert conn.execute("SELECT status FROM runs").fetchone()[0] == "completed"
