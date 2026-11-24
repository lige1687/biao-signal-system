"""回归测试：5项宏观底子修复、海外场内ETF溢价率与行业拥挤度证伪归档白话检查。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import fundamentals as fundamentals_route
from lei_signal.fundamentals import etf_premium, observations, sources
from lei_signal.fundamentals.service import FundamentalsService
from lei_signal.market_context import cn_breadth_refresh, observation_refresh
from lei_signal.strategy_lab.plain_language_guard import audit_markdown_report, check_plain_chinese


def test_cn_breadth_resolve_node_bin_finds_env_or_standard_path(monkeypatch, tmp_path):
    fake_node = tmp_path / "node"
    fake_node.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_node.chmod(0o755)
    monkeypatch.setenv("LEI_NODE_BIN", str(fake_node))
    assert cn_breadth_refresh._resolve_node_bin() == str(fake_node)


def test_observation_refresh_clamps_cn_breadth_cutoff_between_16_and_18_shanghai():
    # 2026-11-24 09:00 UTC = 17:00 Shanghai (between 16:00 and 18:00)
    now = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
    cutoffs = observation_refresh.completed_cutoffs(now)
    assert cutoffs["cn"] == "2026-11-24"
    # breadth-cn must wait until 18:00 Shanghai so it does not collide with closed_cutoff()
    assert observation_refresh._scope_cutoff("breadth-cn", cutoffs, now) == "2026-11-23"
    assert observation_refresh._scope_cutoff("erp-cn", cutoffs, now) == "2026-11-24"


def test_install_cn_surfaces_receipt_error_before_missing_candidate(tmp_path):
    out = tmp_path / "breadth-cn"
    out.mkdir()
    (out / "receipt.json").write_text(
        json.dumps({"status": "failed", "errors": ["boom: node missing"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="boom: node missing"):
        observation_refresh._install_cn(out, tmp_path)


def test_us_erp_history_falls_back_to_fresh_cached_monthly_ey(monkeypatch, tmp_path):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    ey_pts = {f"{y}-{m:02d}-01": 4.2 for y in range(2015, 2027) for m in range(1, 13)}
    # Keep up to 2026-10-01
    ey_pts = {k: v for k, v in ey_pts.items() if k <= "2026-10-01"}
    sources._write_cached_us_ey(ey_pts)

    monkeypatch.setattr(
        sources,
        "fetch_us_ey_history",
        lambda: (_ for _ in ()).throw(sources.FundamentalsSourceError("SSL EOF")),
    )
    treasury = {"2026-11-20": {"us_10y": 4.0}, "2026-11-23": {"us_10y": 4.1}}
    res = sources.fetch_us_erp_history(lookback_days=30, treasury_hist=treasury)
    assert res["2026-11-20"] == 0.2
    assert res["2026-11-23"] == 0.1


def test_us_observations_include_10y_history_percentile(monkeypatch, tmp_path):
    start = datetime(2025, 1, 1, tzinfo=UTC).date()
    long_series = {(start + timedelta(days=i)).isoformat(): 10.0 + i * 0.05 for i in range(300)}
    monkeypatch.setattr(sources, "fetch_vix_history", lambda _: long_series)
    monkeypatch.setattr(sources, "_fetch_fred_series", lambda sid, *, cosd: long_series)
    monkeypatch.setenv("LEI_SENTIMENT_ROOT", str(tmp_path))
    out = observations.build_observations("us", lambda _k, fn: fn())
    by_id = {x["metric_id"]: x for x in out["items"]}
    assert by_id["hy_oas"]["history_percentile"] == 100.0
    assert by_id["vxn"]["history_percentile"] == 100.0
    assert by_id["real_yield_10y"]["history_percentile"] == 100.0


def test_cn_observations_add_margin_ratio_and_live_turnover_without_breaking_frozen(monkeypatch, tmp_path):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    (tmp_path / "cn_funding_live.json").write_text(
        json.dumps(
            {
                "generatedAt": "2026-11-24T10:00:00+00:00",
                "turnoverPoints": [
                    {"date": f"2026-10-{i:02d}", "value_yi": 15000.0} for i in range(1, 22)
                ]
                + [{"date": "2026-11-23", "value_yi": 18000.0}],
            }
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 8, 31, tzinfo=UTC).date()
    hist = {
        (start + timedelta(days=i)).isoformat(): {
            "rzye_yi": 100.0 + i / 10,
            "buy_yi": 4.0 + i / 20,
            "rzyezb_pct": 2.1 + i * 0.01,
        }
        for i in range(25)
    }
    monkeypatch.setattr(sources, "fetch_margin_history", lambda _: hist)
    out = observations.build_observations("cn", lambda _k, fn: fn())
    by_id = {x["metric_id"]: x for x in out["items"]}
    # Frozen snapshot untouched
    assert by_id["stock_turnover"]["observation_date"] == "2026-09-29"
    # New live turnover & market-cap-normalized margin ratio present
    assert by_id["cn_turnover_live"]["observation_date"] == "2026-11-23"
    assert by_id["cn_turnover_live"]["value"] == 18000.0
    assert by_id["cn_turnover_live"]["change"] == 20.0
    assert by_id["margin_balance_ratio"]["value"] == 2.34


def test_cross_border_premium_thresholds_group_best_and_route(tmp_path):
    quotes = {
        "513100": {"name": "纳指ETF国泰", "price": 2.131, "quote_date": "2026-11-24"},
        "159941": {"name": "纳指ETF广发", "price": 1.210, "quote_date": "2026-11-24"},
        "513300": {"name": "纳斯达克ETF华夏", "price": 1.520, "quote_date": "2026-11-24"},
        "513500": {"name": "标普500ETF博时", "price": 2.528, "quote_date": "2026-11-24"},
        "159655": {"name": "标普ETF华夏", "price": 1.610, "quote_date": "2026-11-24"},
        "513180": {"name": "恒生科技ETF华夏", "price": 0.432, "quote_date": "2026-11-24"},
    }
    navs = {
        "513100": {"nav": 1.788, "nav_date": "2026-11-23", "subscribe_status": "暂停申购"},
        "159941": {"nav": 1.180, "nav_date": "2026-11-23", "subscribe_status": "限大额"},
        "513300": {"nav": 1.400, "nav_date": "2026-11-23", "subscribe_status": "暂停申购"},
        "513500": {"nav": 2.2973, "nav_date": "2026-11-23", "subscribe_status": "暂停申购"},
        "159655": {"nav": 1.595, "nav_date": "2026-11-23", "subscribe_status": "开放申购"},
        "513180": {"nav": 0.4356, "nav_date": "2026-11-24", "subscribe_status": "场内买入"},
    }
    data = etf_premium.build_cross_border_premium(
        quote_loader=lambda _s: quotes,
        nav_loader=lambda c: navs[c],
        cache=tmp_path,
        persist=True,
    )
    by_code = {x["code"]: x for x in data["items"]}
    assert by_code["513100"]["risk_level"] == "high_risk"
    assert by_code["513100"]["premium_pct"] == 19.18
    assert by_code["159941"]["is_lowest_in_group"] is True
    assert by_code["159941"]["risk_level"] == "caution"
    assert by_code["159655"]["risk_level"] == "fair"
    assert by_code["159655"]["is_lowest_in_group"] is True
    assert by_code["513180"]["risk_level"] == "fair"
    assert by_code["513180"]["nav_lag"] is False
    # Plain language guard check on all user-facing strings
    all_cn = "\n".join(
        [data["thresholds"]["rule_cn"]]
        + [f"{x['verdict_cn']} {x['note_cn']}" for x in data["items"]]
    )
    assert check_plain_chinese(all_cn) == []
    assert (tmp_path / "cross_border_etf_premium.json").is_file()

    # Route check
    app = FastAPI()
    svc = FundamentalsService()
    svc._cache.get_or_load("cross_border_premium", 1800, lambda: data)
    app.state.fundamentals_service = svc
    app.include_router(fundamentals_route.router)
    resp = TestClient(app).get("/api/fundamentals/cross-border-premium")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 6


def test_sector_crowding_audit_report_passes_plain_language_guard():
    report = Path(__file__).resolve().parents[2] / "docs/experiments/sector-crowding-threshold-audit-2026-11-24.md"
    audit = audit_markdown_report(report)
    assert audit["has_plain_oneliner_heading"] is True
    assert audit["passed"] is True, audit["violations"]
