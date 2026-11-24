from copy import deepcopy
from datetime import datetime

from lei_signal.integrations.daily_decisions import (
    build_daily_decisions,
    plan_scenario,
    render_scenario_svg,
)

NOW = datetime.fromisoformat("2026-10-08T14:40:00+08:00")


def facts():
    plan = {
        "plan_id": "p1",
        "symbol": "515880.SS",
        "state": "entered",
        "direction": "long",
        "entry_price_ref": 1,
        "invalidation_price": 0.9,
        "target_b_price": 1.5,
        "target_b_source": "已保存计划的目标说明",
    }
    item = {
        "holding_id": "h1",
        "name": "示例通信ETF",
        "code": "515880",
        "symbol": "515880.SS",
        "plan": {"plan_id": "p1"},
        "gaps": [],
        "status": "no_trigger",
        "technical": {"meta": {"last_bar_date": "2026-09-30", "is_intraday_forming": False}},
        "alerts": [],
    }
    return {"items": [item]}, {"plans": [plan]}


def test_arithmetic_is_conditional_and_not_probability():
    p, plans = facts()
    result = build_daily_decisions(portfolio=p, plans=plans, now=NOW)
    scenario = result["holdings"][0]["scenario"]
    assert scenario["reward_risk"] == 5
    assert scenario["risk_pct"] == 10
    assert scenario["reward_pct"] == 50
    assert "示例通信ETF" in render_scenario_svg(scenario)
    assert result["research_evidence"]["current_trade_win_probability"] is None


def test_nav_fund_never_borrows_index_price():
    scenario = plan_scenario(
        {
            "symbol": "^HSTECH",
            "entry_price_ref": 5000,
            "invalidation_price": 4500,
            "target_b_price": 7000,
        },
        product={"name": "华夏恒生科技ETF联接C", "code": "013403"},
    )
    assert scenario["reward_risk"] is None and scenario["entry"] is None
    assert "暂不绘制" in render_scenario_svg(scenario)


def test_unqualified_source_cannot_claim_safe_or_triggered():
    p, plans = facts()
    for mutation in ("forming", "gap", "future", "wrong_product", "draft", "missing_date"):
        data = deepcopy(p)
        ps = deepcopy(plans)
        item = data["items"][0]
        item["alerts"] = [
            {
                "code": "STOP_PRICE_BREACHED",
                "data_as_of": "2026-10-08",
                "actionable_from": "2026-10-08",
            }
        ]
        if mutation == "forming":
            item["technical"]["meta"]["is_intraday_forming"] = True
        if mutation == "gap":
            item["gaps"] = ["假日交易日历未核实"]
        if mutation == "future":
            item["technical"]["meta"]["last_bar_date"] = "2026-10-09"
        if mutation == "wrong_product":
            ps["plans"][0]["symbol"] = "^HSTECH"
        if mutation == "draft":
            ps["plans"][0]["state"] = "draft"
        if mutation == "missing_date":
            item["alerts"][0].pop("actionable_from")
        review = build_daily_decisions(portfolio=data, plans=ps, now=NOW)["holdings"][0]
        assert review["alerts"] == [] and "无法判断" in review["status"], mutation


def test_afternoon_keeps_dated_confirmed_alert_noon_does_not():
    p, plans = facts()
    p["items"][0]["alerts"] = [
        {"code": "STOP_PRICE_BREACHED", "data_as_of": "2026-09-30", "actionable_from": "2026-10-08"}
    ]
    out = build_daily_decisions(portfolio=p, plans=plans, now=NOW)
    assert out["holdings"][0]["alerts"][0]["data_as_of"] == "2026-09-30"
    noon = build_daily_decisions(portfolio=p, plans=plans, slot="1135", now=NOW)
    assert noon["holdings"][0]["alerts"] == []


def test_scan_candidate_is_not_instruction_and_news_requires_same_code():
    p, _ = facts()
    out = build_daily_decisions(
        portfolio=p,
        now=NOW,
        opportunities={"actionable": [{"symbol": "QQQ", "display_name": "纳指100 QQQ"}]},
        news={
            "items": [
                {"title": "指数新闻", "symbols": ["^HSTECH"]},
                {"title": "明确关联", "symbols": ["515880"]},
            ]
        },
    )
    assert out["opportunities"][0]["is_trade_instruction"] is False
    assert [a["title"] for a in out["related_news"][0]["articles"]] == ["明确关联"]


def test_invalid_prices_missing_names_and_offline_visible():
    for bad in (0, -1, float("nan"), float("inf"), True):
        assert (
            plan_scenario(
                {
                    "symbol": "QQQ",
                    "entry_price_ref": bad,
                    "invalidation_price": 90,
                    "target_b_price": 150,
                }
            )["reward_risk"]
            is None
        )
    out = build_daily_decisions(
        portfolio={"available": False, "errors": {"workspace": "offline"}}, now=NOW
    )
    assert out["source_errors"]["portfolio"]["workspace"] == "offline"
    assert out["holdings"] == []
