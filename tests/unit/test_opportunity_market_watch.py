"""The market watch uses saved observations without refreshing market data."""

import json
import sqlite3
from datetime import date

from lei_signal.api.opportunity_market_watch import build_market_watch


def _inputs(tmp_path, *, breadth_day="2026-10-16", b50=18.14, b200=14.81, rows=None):
    (tmp_path / "a_share_ma_breadth_history.json").write_text(
        json.dumps(
            [
                {"date": "2026-10-09", "ma50_pct": 41.49, "ma200_pct": 21.69},
                {"date": "2026-10-12", "ma50_pct": 35, "ma200_pct": 20},
                {"date": "2026-10-13", "ma50_pct": 30, "ma200_pct": 19},
                {"date": "2026-10-14", "ma50_pct": 25, "ma200_pct": 18},
                {"date": "2026-10-15", "ma50_pct": b50, "ma200_pct": b200},
                {"date": breadth_day, "ma50_pct": b50, "ma200_pct": b200},
            ]
        )
    )
    (tmp_path / "a_share_ma_breadth.json").write_text(
        json.dumps(
            {"date": breadth_day, "ma50_pct": b50, "ma200_pct": b200, "source": "local close cache"}
        )
    )
    db = tmp_path / "macro.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE opportunity_macro_observations "
            "(market TEXT, checked_on TEXT, status TEXT, rows_json TEXT)"
        )
        for market, values in (rows or {}).items():
            conn.execute(
                "INSERT INTO opportunity_macro_observations VALUES (?, ?, 'ready', ?)",
                (market, "2026-10-18", json.dumps(values)),
            )
    return str(db)


def _row(market, metric, day, fact, *, published_at=None):
    return {
        "market": market,
        "metric_id": metric,
        "observation_date": day,
        "published_at": published_at,
        "text": fact,
        "source": "public source",
        "source_ref": "https://example.org/source",
        "public": True,
        "provenance": "local_macro_observation",
        "limitations": [],
    }


def test_weekend_window_breadth_threshold_is_observation_needing_check(tmp_path):
    db = _inputs(tmp_path)
    result = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert result["news_window"] == {"start": "2026-10-15", "end": "2026-10-19", "days": 5}
    assert "2026-10-12—2026-10-16" in result["market_window_label"]
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["kind"] == "breadth" and item["status"] == "needs_check"
    assert item["threshold"]["value"] == 20.0
    assert "非策略规则" in item["threshold"]["basis"]
    assert "18.14%" in item["fact"] and "14.81%" in item["fact"]
    assert "2026-10-09" in item["fact"] and "-23.35个百分点" in item["fact"]
    assert any("逐股行情日期" in x for x in item["limitations"])
    assert any("完全相同" in x for x in item["limitations"])
    assert "反转位置" not in str(result) and "买点" not in item["meaning"]
    assert all(x["id"] != item["id"] for x in result["readings"])


def test_stale_or_mismatched_breadth_cannot_be_recent_focus(tmp_path):
    db = _inputs(tmp_path)
    old = build_market_watch(as_of=date(2026, 10, 26), db_path=db, cache_dir=tmp_path)
    assert old["items"] == []
    assert any("超过7个自然日" in x for x in old["limitations"])
    snapshot = tmp_path / "a_share_ma_breadth.json"
    value = json.loads(snapshot.read_text())
    value["ma50_pct"] = 50
    snapshot.write_text(json.dumps(value))
    bad = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert bad["items"] == [] and bad["readings"] == []
    assert any("不一致" in x for x in bad["limitations"])


def test_macro_readings_deduplicate_and_cpi_is_not_new_event(tmp_path):
    cn_cpi = _row("cn", "cpi", "2026-09-01", "截至2026-09-01，CPI同比为0.9%。")
    us_vix = _row("us", "vix", "2026-10-16", "截至2026-10-16，VIX为19.99。")
    db = _inputs(tmp_path, rows={"cn": [cn_cpi, cn_cpi], "us": [us_vix]})
    result = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert [x["id"] for x in result["items"]] == ["cn_all_a:breadth_b50_b200"]
    assert [x["id"] for x in result["readings"]] == ["cn:cpi", "us:vix"]
    cpi = result["readings"][0]
    assert cpi["observation_date"] == "2026-09-01"
    assert cpi["published_at"] is None
    assert any("发布时间未核" in x for x in cpi["limitations"])
    assert len(result["readings"]) <= 6


def test_future_rows_and_missing_db_do_not_create_events_or_file(tmp_path):
    db = _inputs(
        tmp_path,
        rows={"us": [_row("us", "vix", "2026-10-20", "future value")]},
    )
    result = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert all(x["id"] != "us:vix" for x in result["readings"])
    nonexistent = tmp_path / "missing.db"
    missing = build_market_watch(
        as_of=date(2026, 10, 19), db_path=str(nonexistent), cache_dir=tmp_path
    )
    assert not nonexistent.exists()
    assert any("观察库缺失" in x for x in missing["limitations"])


def test_hot_and_single_b50_extremes_use_neutral_observation_language(tmp_path):
    db = _inputs(tmp_path, b50=85, b200=88)
    hot = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert len(hot["items"]) == 1
    assert "双线高于" in hot["items"][0]["title"]
    assert "比例较高" in hot["items"][0]["meaning"]
    assert hot["items"][0]["status"] == "needs_check"
    assert hot["readings"] == []

    history = tmp_path / "a_share_ma_breadth_history.json"
    values = json.loads(history.read_text())
    for row in values[-2:]:
        row["ma50_pct"] = 15
        row["ma200_pct"] = None
    history.write_text(json.dumps(values))
    snapshot = tmp_path / "a_share_ma_breadth.json"
    value = json.loads(snapshot.read_text())
    value.update({"ma50_pct": 15, "ma200_pct": None})
    snapshot.write_text(json.dumps(value))
    single = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert len(single["items"]) == 1
    assert "50日线宽度低于" in single["items"][0]["title"]
    assert "200日线" not in single["items"][0]["fact"]


def test_incomplete_same_day_and_untrusted_macro_rows_are_excluded(tmp_path):
    bad_rows = [
        _row("us", "vix", "2026-10-16", "截至2026-10-16，VIX为19.99。"),
        _row("us", "us_10y", "2026-10-16", "截至2026-10-16，利率为NaN。"),
        _row("us", "hy_oas", "2026-10-16", "截至2026-10-16，利差为3.2%。"),
    ]
    bad_rows[0]["public"] = False
    bad_rows[2]["source_ref"] = "http://example.org/source"
    db = _inputs(tmp_path, breadth_day="2026-10-19", rows={"us": bad_rows})
    current = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert current["items"] == [] and current["readings"] == []
    assert any("快照与历史末日不一致" in x for x in current["limitations"])

    closed = build_market_watch(
        as_of=date(2026, 10, 19),
        db_path=db,
        cache_dir=tmp_path,
        completed_through=date(2026, 10, 19),
    )
    assert len(closed["items"]) == 1
    assert closed["items"][0]["observation_date"] == "2026-10-19"
    assert "2026-10-19" in closed["market_window_label"]

    future_claim = build_market_watch(
        as_of=date(2026, 10, 19),
        db_path=db,
        cache_dir=tmp_path,
        completed_through=date(2026, 10, 20),
    )
    assert future_claim["items"] == closed["items"]


def test_same_day_receipt_replaces_mixed_day_cache_and_shows_its_denominators(tmp_path):
    db = _inputs(tmp_path, b50=18.14, b200=14.81)
    quality = {
        "target_day": "2026-10-16",
        "universe_total": 110,
        "same_day_available": 100,
        "calculation_status": "verified_same_day_sample",
        "price_adjustment": "qfqday",
        "price_provenance": "qfq_source_receipt_v1",
        "price_source_ref": "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get",
        "price_cache_sha256": "a" * 64,
        "eligible50": 100,
        "above50": 25,
        "ma50_pct": 25.0,
        "eligible200": 90,
        "above200": 9,
        "ma200_pct": 10.0,
        "status": "needs_check",
        "limitations": ["仅有限样本；尚缺10只。"],
    }
    path = tmp_path / "a_share_ma_breadth_qualification.json"
    path.write_text(json.dumps(quality))
    result = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert result["items"] == []  # The old mixed-day both-below-20 observation is removed.
    item = result["readings"][0]
    assert item["status"] == "observed" and item["quality_label"] == "同日样本已核"
    assert "25.00%" in item["fact"] and "100/110" in item["fact"]
    assert "18.14" not in str(result) and "较2026" not in item["fact"]
    assert any("200日线按90只" in x for x in item["limitations"])
    assert item["source_ref"] is None  # Never link the corrected sample to the old mixed history.
    quality["ma50_pct"] = 18.14
    path.write_text(json.dumps(quality))
    rejected = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert not rejected["items"] and not rejected["readings"]
    assert any("分子、分母" in x for x in rejected["limitations"])

    quality["ma50_pct"] = 25.0
    quality.pop("price_provenance")
    path.write_text(json.dumps(quality))
    unproven = build_market_watch(as_of=date(2026, 10, 19), db_path=db, cache_dir=tmp_path)
    assert not unproven["items"] and not unproven["readings"]
    assert any("前复权来源" in x for x in unproven["limitations"])
