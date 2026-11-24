import json
from datetime import datetime, timezone

from lei_signal.market_context.a_share_breadth import get_ma_breadth_history
from lei_signal.market_context.observation_refresh import completed_cutoffs, is_due


def test_cutoffs_follow_each_market_close_and_weekend():
    assert completed_cutoffs(datetime(2026, 11, 5, 7, 59, tzinfo=timezone.utc))["cn"] == "2026-11-04"
    assert completed_cutoffs(datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc))["cn"] == "2026-11-05"
    assert completed_cutoffs(datetime(2026, 11, 5, 10, 30, tzinfo=timezone.utc)) == {"cn": "2026-11-05", "us": "2026-11-04"}
    assert completed_cutoffs(datetime(2026, 11, 8, 10, 30, tzinfo=timezone.utc)) == {"cn": "2026-11-06", "us": "2026-11-06"}


def test_finished_scopes_do_not_redownload_and_failures_retry_with_backoff():
    now = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    assert not is_due("erp-cn", {"as_of": "2026-11-05"}, "2026-11-05", now)
    failed = {"cutoff": "2026-11-05", "checked_at": "2026-11-05T09:00:00+00:00"}
    assert not is_due("erp-cn", failed, "2026-11-05", now)
    assert is_due("erp-cn", failed, "2026-11-06", now)
    assert is_due("erp-cn", failed, "2026-11-05", datetime(2026, 11, 5, 14, tzinfo=timezone.utc))


def test_get_ma_breadth_history_merges_full_base_and_live_tail(tmp_path, monkeypatch):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    (tmp_path / "a_share_ma_breadth_full_history.json").write_text(
        json.dumps([
            {"date": "1993-04-22", "ma20_pct": 51.2, "ma50_pct": 48.0, "ma200_pct": 44.1},
            {"date": "2021-06-17", "ma20_pct": 40.0, "ma50_pct": 41.0, "ma200_pct": 42.0},
        ]),
        encoding="utf-8",
    )
    (tmp_path / "a_share_ma_breadth_history.json").write_text(
        json.dumps([
            {"date": "2021-06-17", "ma20_pct": 40.5, "ma50_pct": 41.5, "ma200_pct": 42.5},
            {"date": "2026-11-18", "ma20_pct": 22.0, "ma50_pct": 16.0, "ma200_pct": 11.0},
        ]),
        encoding="utf-8",
    )
    merged = get_ma_breadth_history(lookback_days=12600)
    assert [r["date"] for r in merged] == ["1993-04-22", "2021-06-17", "2026-11-18"]
    assert merged[1]["ma20_pct"] == 40.5
