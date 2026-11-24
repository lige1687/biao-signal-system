"""Industry reference identity, time and account-state boundaries."""
import copy
import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from lei_signal.portfolio.industry_context import (
    DEFAULT_PATH, build_industry_reference, cached_industry_reference,
)

TODAY = date(2026, 10, 14)


def disclosure():
    return {"fund_code": "001513", "status": "available", "report_date": "2026-06-30",
            "holdings": [{"stock_code": "300502", "stock_name": "新易盛", "weight_pct": 6.09,
                          "industry_label": "光通信设备与器件", "industry_source_url": "https://www.eoptolink.com/cn/"}]}


def build(d=None, **kwargs):
    return build_industry_reference("001513", "易方达信息产业混合A", d or disclosure(), today=TODAY, **kwargs)


def test_binds_company_and_fund_fact_without_fund_trade_advice():
    d = disclosure()
    before = copy.deepcopy(d)
    out = build(d)
    assert d == before
    assert out["references"][0]["symbol"] == "515880.SS"
    assert out["references"][0]["companies"][0]["weight_pct"] == 6.09
    assert out["references"][0]["technical"] is None
    assert out["fundamentals"][0]["kind"] == "基金经理观点"
    assert not any(key in out for key in ("sell", "exit_price", "action_required", "plan"))


@pytest.mark.parametrize("field,value", [
    ("stock_name", "另一个产品"), ("stock_code", "US_UNKNOWN"),
    ("industry_label", "软件"), ("industry_source_url", ""),
    ("weight_pct", float("nan")), ("weight_pct", -1), ("weight_pct", True),
])
def test_does_not_infer_market_or_business(field, value):
    d = disclosure()
    d["holdings"][0][field] = value
    assert build(d)["references"] == []


@pytest.mark.parametrize("field,value", [
    ("fund_code", "009999"), ("status", "invalid"),
    ("report_date", "2026-12-31"), ("report_date", "2026-02-30"),
    ("report_date", None),
])
def test_invalid_disclosure_stays_unavailable(field, value):
    d = disclosure()
    d[field] = value
    out = build(d)
    assert out["references"] == out["fundamentals"] == []


def test_no_cross_market_reference_or_future_catalog():
    catalog = json.loads(DEFAULT_PATH.read_text())
    catalog["references"]["communication_cn"]["market"] = "美股"
    assert build(catalog=catalog)["references"] == []
    catalog["checked_on"] = "2026-10-15"
    assert build(catalog=catalog)["fundamentals"] == []


def test_exact_share_class_and_report_for_manager_view():
    out = build_industry_reference("001513", "易方达信息产业混合C", disclosure(), today=TODAY)
    assert out["fundamentals"] == []
    d = disclosure()
    d["report_date"] = "2026-09-30"
    assert build(d)["fundamentals"] == []


def test_reference_snapshot_identity_and_dates():
    for snapshot in [{"symbol": "IGV", "as_of": "2026-10-13"},
                     {"symbol": "515880.SS", "as_of": "2026-10-15"}]:
        assert build(snapshots={"515880.SS": snapshot})["references"][0]["technical"] is None
    snapshot = {"symbol": "515880.SS", "as_of": "2026-10-13", "stage_cn": "风险关注"}
    assert build(snapshots={"515880.SS": snapshot})["references"][0]["technical"] == snapshot


def test_cache_only_does_not_call_remote_service():
    class Service:
        _entries = {}
        def get(self, *args, **kwargs):
            raise AssertionError("network fetch forbidden")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(analysis_service=Service())))
    out = cached_industry_reference(request, "001513", "易方达信息产业混合A", disclosure(),
                                    datetime(2026, 10, 14, 18, tzinfo=ZoneInfo("Asia/Shanghai")))
    assert len(out["references"]) == 1
    assert out["references"][0]["technical"] is None


@pytest.mark.parametrize("as_of,stale", [("2026-09-30", True), ("2026-10-14", False)])
def test_old_cached_phase_is_explicitly_stale(monkeypatch, as_of, stale):
    from lei_signal.api.routes import symbols
    from lei_signal.api import card_mapper
    now = datetime(2026, 10, 14, 18, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = SimpleNamespace(symbol="515880.SS", cache_fallback_used=False)
    entry = SimpleNamespace(result=result, fetched_at=now, error=None)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        analysis_service=SimpleNamespace(_entries={"515880.SS": entry}))))
    monkeypatch.setattr(symbols, "_assessment_dto", lambda result: SimpleNamespace(
        as_of=as_of, stage_cn="风险关注", color_cn="灰色", risk_state_cn="关注"))
    monkeypatch.setattr(card_mapper, "is_intraday_forming", lambda result, now, fetched_at=None: False)
    out = cached_industry_reference(request, "001513", "易方达信息产业混合A", disclosure(), now)
    assert out["references"][0]["technical"]["stale"] is stale


def test_portfolio_context_carries_reference_in_frozen_material(monkeypatch):
    from lei_signal.api import portfolio_workspace
    from lei_signal.copilot.portfolio_context import build_portfolio_context, frozen_portfolio_context
    reference = build()
    monkeypatch.setattr(portfolio_workspace, "build_workspace", lambda request: {
        "items": [{"holding_id": "one", "name": "易方达信息产业混合A", "industry_reference": reference},
                  {"holding_id": "other", "name": "其他基金"}]})
    context = build_portfolio_context(None, "one")
    assert len(context["portfolio"]["items"]) == 1
    assert context["portfolio"]["items"][0]["industry_reference"] == reference
    assert frozen_portfolio_context(context, "one") == context
