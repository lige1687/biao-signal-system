import sqlite3

from lei_signal.forward_observation import initialize, process_observation
from lei_signal.forward_observation.replay import replay_saved


def test_saved_receipts_reproduce_tables_without_touching_live(tmp_path):
    config = {
        "assets": [{"symbol": "510300.SS"}], "initial_cash": 100000,
        "accounts": [{"id": "buy", "kind": "buy_hold"}, {"id": "cash", "kind": "cash"}],
    }
    source = tmp_path / "live.db"
    initialize(source, config, "2026-10-20T09:00:00+08:00")
    for name, stamp, end in [
        ("fill", "2026-10-20T10:00:00+08:00", False),
        ("close", "2026-10-20T15:00:00+08:00", True),
    ]:
        observation = {
            "id": name, "symbol": "510300.SS", "source": "synthetic replay test",
            "source_time": stamp, "received_at": stamp, "last": 4.0, "bid": 3.999,
            "ask": 4.0, "ask_size": 100, "market_open": not end, "quality": "valid",
            "corporate_actions_checked_from": "2026-10-19",
            "corporate_actions_checked_through": "2026-10-20",
            "corporate_actions": [], "is_eod": end,
        }
        process_observation(source, observation, stamp)
    before = source.read_bytes()
    receipt = replay_saved(source, config, tmp_path / "replays")
    assert receipt["passed"], receipt
    assert receipt["source_counts"]["fills"] == 1
    assert receipt["source_counts"]["valuations"] == 2
    assert source.read_bytes() == before
    with sqlite3.connect(source) as db:
        db.execute("UPDATE orders SET filled_qty=200")
    tampered = replay_saved(source, config, tmp_path / "replays")
    assert not tampered["passed"]
    assert tampered["tables"]["orders"] is False
