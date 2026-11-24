"""Offline IO tests plus actual immutable ledger behavior on synthetic prices."""

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from lei_signal.strategy_portfolios import paper_live as paper
from lei_signal.strategy_portfolios import service

START = "2026-11-02T08:00:00-05:00"
CLOSE = "2026-11-02T17:00:00-05:00"


@pytest.fixture
def env(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_bytes(paper.CONFIG.read_bytes())
    monkeypatch.setattr(paper, "CONFIG", config)
    monkeypatch.setattr(paper, "binding", lambda: {"config": service.digest(config)})
    monkeypatch.setattr(service, "utcnow", lambda: CLOSE)
    return tmp_path / "active", config


def source(tmp_path, until="2026-10-30", received=START):
    bars = []
    day, count = date(2024, 9, 1), 0
    while day.isoformat() <= until:
        if day.weekday() < 5:
            count += 1
            bars.append(
                {
                    "symbol": "ABC",
                    "date": day.isoformat(),
                    "open": 100 + count,
                    "close": 101 + count,
                    "volume": 10000,
                    "valid": True,
                }
            )
        day += timedelta(days=1)
    snapshot = tmp_path / f"snapshot-{until}.json"
    snapshot.write_text(
        json.dumps(
            {
                "received_at": received,
                "markets": {
                    "US": {"bars": bars, "universe": [{"symbol": "ABC", "name": "test"}]},
                    "CN": {"bars": bars},
                },
            }
        )
    )
    path = tmp_path / f"source-{until}.json"
    path.write_text(
        json.dumps({"snapshot": str(snapshot), "snapshot_sha256": service.digest(snapshot)})
    )
    return path, snapshot


def test_get_is_readonly_even_before_freeze(env, monkeypatch):
    active, _ = env
    # Endpoint resolves dashboard's default argument; replace only this read function.
    original = paper.dashboard
    monkeypatch.setattr(paper, "dashboard", lambda: original(active))
    with TestClient(paper.app) as client:
        response = client.get("/api/strategy-paper-live")
        assert response.status_code == 200
        data = response.json()
    assert not active.exists()
    assert data["started_at"] is None
    assert len(data["accounts"]) == 4
    assert all(a["summary"] is None for a in data["accounts"])
    assert all(a["relative_to_equal"]["relative_wealth_return"] is None for a in data["accounts"])
    assert data["parent_index"]["status"] == "not_evaluated"
    assert len(data["pending"]) == 3


def test_freeze_is_immutable_and_drift_fails(env):
    active, config = env
    frozen = paper.freeze(active, START)
    assert paper.freeze(active, CLOSE) == frozen
    cfg = json.loads(config.read_text())
    cfg["initial_cash"] = 2
    config.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="冻结"):
        paper.freeze(active)
    with pytest.raises(ValueError, match="冻结"):
        paper.ingest("not-read.json", active)


def test_hash_and_future_rejected_before_event(env, tmp_path):
    active, _ = env
    paper.freeze(active, START)
    path, snapshot = source(tmp_path)
    snapshot.write_text(snapshot.read_text() + " ")
    with pytest.raises(ValueError, match="指纹"):
        paper.ingest(path, active, START)
    path, _ = source(tmp_path, received=CLOSE)
    with pytest.raises(ValueError, match="未来"):
        paper.ingest(path, active, START)
    with paper._readonly(active) as conn:
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 0


def test_only_us_four_schemes_no_retrofills_and_dedup(env, tmp_path):
    active, _ = env
    paper.freeze(active, START)
    path, _ = source(tmp_path)
    seeded = paper.ingest(path, active, START)
    assert set(seeded["markets"]) == {"US"}
    assert set(seeded["markets"]["US"]["accounts"]) == set(paper.SCHEMES)
    for a in seeded["markets"]["US"]["accounts"].values():
        assert a["series"] == []
        assert a["orders"][0]["execute_date"] == "2026-11-02"
        assert a["orders"][0]["status"] == "等待"
    assert paper.ingest(path, active, START) == json.loads(json.dumps(seeded))
    path, _ = source(tmp_path, "2026-11-02", CLOSE)
    state = paper.ingest(path, active, CLOSE)
    for a in state["markets"]["US"]["accounts"].values():
        assert a["orders"][0]["status"] == "报价模拟成交"
        assert a["orders"][0]["created_at"] == START
        assert a["orders"][0]["observed_at"] == CLOSE
        assert len(a["series"]) == 1
    assert paper.ingest(path, active, CLOSE) == json.loads(json.dumps(state))
    dash = paper.dashboard(active)
    assert dash["market"]["missing_sessions"] == []
    assert dash["accounts"][0]["summary"]["annual_return"] is None
    with paper._readonly(active) as conn:
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 2


def test_same_date_new_source_does_not_duplicate_valuation(env, tmp_path):
    active, _ = env
    paper.freeze(active, START)
    path, snapshot = source(tmp_path, "2026-11-02", CLOSE)
    paper.ingest(path, active, CLOSE)
    snapshot.write_text(snapshot.read_text() + " ")
    loc = json.loads(path.read_text())
    loc["snapshot_sha256"] = service.digest(snapshot)
    path.write_text(json.dumps(loc))
    state = paper.ingest(path, active, CLOSE)
    assert len(state["markets"]["US"]["accounts"]["m"]["series"]) == 1


def test_gap_visible_and_no_backfill(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    path, _ = source(tmp_path)
    paper.ingest(path, active, START)
    later = "2026-11-03T17:00:00-05:00"
    path, _ = source(tmp_path, "2026-11-03", later)
    state = paper.ingest(path, active, later)
    account = state["markets"]["US"]["accounts"]["m"]
    assert account["orders"][0]["status"] == "未成交"
    assert "错过指定" in account["orders"][0]["failure_reason"]
    monkeypatch.setattr(service, "utcnow", lambda: later)
    assert paper.dashboard(active)["market"]["missing_sessions"] == ["2026-11-02"]


def test_relative_uses_only_matched_date_navs():
    result = paper._relative(
        [{"date": "a", "nav": 3}, {"date": "b", "nav": 1.2}],
        [{"date": "b", "nav": 1.1}, {"date": "c", "nav": 5}],
    )
    assert result["matched_dates"] == 1
    assert result["relative_wealth_return"] == pytest.approx(1.2 / 1.1 - 1)
    assert result["cumulative_difference_pp"] == pytest.approx(10)


def legacy(tmp_path):
    active = tmp_path / "legacy"
    with service.connect(active) as conn:
        frozen = {"bindings": service.binding(), "state": {}}
        conn.execute("INSERT INTO frozen VALUES (1,?)", (json.dumps(frozen),))
    return active


def test_binding_failure_precedes_any_collector(env, tmp_path, monkeypatch):
    active, config = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    calls = []
    monkeypatch.setattr(paper.runner, "tick", lambda *a: calls.append(a))
    config.write_text(config.read_text() + " ")
    with pytest.raises(ValueError, match="冻结"):
        paper.tick(active, old)
    assert not calls


def test_legacy_and_own_lock_prevent_duplicate_collectors(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    calls = []
    monkeypatch.setattr(paper.runner, "tick", lambda *a: calls.append(a))
    with paper._lock(old / "worker.lock"), pytest.raises(RuntimeError, match="锁"):
        paper.tick(active, old)
    assert not calls
    with (
        paper._lock(active / "paper-live.lock"),
        pytest.raises(RuntimeError, match="锁"),
        paper._lock(active / "paper-live.lock"),
    ):
        pass


def test_old_source_not_replayed_by_new_worker(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    with service.connect(old) as conn:
        conn.execute(
            "INSERT INTO runs VALUES (?,?,?,?)",
            ("2026-11-02", "2026-11-02T06:00:00-05:00", "completed", '{"attempt":1}'),
        )
    monkeypatch.setattr(paper.runner, "tick", lambda *a: None)
    assert "冻结后" in paper.tick(active, old)["status"]
    with paper._readonly(active) as conn:
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 0


def test_calendar_exhaustion_visible_and_blocks_collection(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    calls = []
    monkeypatch.setattr(paper.runner, "tick", lambda *a: calls.append(a))
    monkeypatch.setattr(service, "utcnow", lambda: "2027-01-04T20:00:00+00:00")
    assert paper.dashboard(active)["run"]["error"]
    with pytest.raises(ValueError, match="日历"):
        paper.tick(active, old)
    assert not calls


def test_legacy_binding_failure_precedes_collector(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    with service.connect(old) as conn:
        conn.execute("UPDATE frozen SET payload=?", ('{"bindings":{},"state":{}}',))
    calls = []
    monkeypatch.setattr(paper.runner, "tick", lambda *a: calls.append(a))
    with pytest.raises(ValueError, match="冻结"):
        paper.tick(active, old)
    assert not calls


def test_daily_shared_source_ingested_once_and_failure_retained(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    path, _ = source(tmp_path, "2026-11-02", CLOSE)
    (old / "source-2026-11-02-2.json").write_bytes(path.read_bytes())
    with service.connect(old) as conn:
        conn.execute(
            "INSERT INTO runs VALUES (?,?,?,?)", ("2026-11-02", CLOSE, "completed", '{"attempt":2}')
        )
    calls = []
    monkeypatch.setattr(paper.runner, "tick", lambda *a: calls.append(a))
    assert paper.tick(active, old)["successful_collection"] is True
    paper.tick(active, old)
    assert len(calls) == 2  # scheduler called; its frozen daily guard owns collection dedup
    with paper._readonly(active) as conn:
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == 1
    paper._heartbeat(active, {"pid": 123, "status": "采集异常", "error": "vendor failed"})
    assert paper.dashboard(active)["run"]["error"] == "vendor failed"
    assert paper.dashboard(active)["run"]["pid"] == 123


def test_relative_preserves_first_day_cost_and_rejects_unknown():
    a = [
        {"date": "a", "nav": 0.99, "unknown_weight": 0},
        {"date": "b", "nav": 2, "unknown_weight": 0.1},
        {"date": "c", "nav": float("nan")},
        {"date": "d", "nav": 0},
    ]
    b = [{"date": day, "nav": 1} for day in ("a", "b", "c", "d")]
    comparison = paper._relative(a, b)
    assert comparison["matched_dates"] == 1
    assert comparison["cumulative_difference_pp"] == pytest.approx(-1)
    assert comparison["relative_wealth_return"] == pytest.approx(-0.01)


def test_watch_owns_both_locks_and_updates_both_heartbeats(env, tmp_path, monkeypatch):
    active, _ = env
    paper.freeze(active, START)
    old = legacy(tmp_path)
    signals = {}
    monkeypatch.setattr(paper.signal, "signal", lambda number, fn: signals.update({number: fn}))

    def fake_tick(new, legacy_active, *, _legacy_lock_held):
        assert _legacy_lock_held
        for path in (new / "paper-live.lock", legacy_active / "worker.lock"):
            with pytest.raises(RuntimeError, match="锁"), paper._lock(path):
                pass
        signals[paper.signal.SIGTERM](15, None)
        return {"status": "等待新采集"}

    monkeypatch.setattr(paper, "tick", fake_tick)
    paper.watch(active, old)
    for location in (active, old):
        hb = json.loads((location / "worker-status.json").read_text())
        assert hb["managed_by"] == "strategy-paper-live"
        assert hb["pid"] == paper.os.getpid()
        assert hb["status"] == "已停止"
        assert hb["error"]
