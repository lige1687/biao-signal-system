"""P4 表达层门禁：verify_grounding / 禁用词 / 两层标注 / 降级 / 端到端溯源。"""
from __future__ import annotations

from lei_signal.plans.actions import sync_action_items
from lei_signal.plans.grounding import (
    FORBIDDEN_TERMS,
    RESEARCH_PROXY_MARKER,
    render_alerts,
    template_render,
    verify_grounding,
)
from lei_signal.plans.models import PLAN_ARMED, TradePlan
from lei_signal.plans.monitor import (
    INVALIDATION_BREACHED,
    MonitorContext,
    OpportunityRef,
    evaluate_plan,
)
from lei_signal.plans.store import (
    confirm_plan,
    create_plan,
    list_action_items,
)
from lei_signal.storage.sqlite_store import connect

RULESET = "1.3.0"


# ---------------------------------------------------------------- verify_grounding


def test_verify_grounding_rejects_superset_rule_id() -> None:
    text = "说明 [rule_id:fake_rule | 证据:close=10]"
    ok, reason = verify_grounding(text, {"first_ma_pullback"})
    assert not ok
    assert "fake_rule" in reason


def test_verify_grounding_rejects_forbidden_terms() -> None:
    for term in FORBIDDEN_TERMS:
        text = f"建议{term}该标的 [rule_id:first_ma_pullback]"
        ok, _ = verify_grounding(text, {"first_ma_pullback"})
        assert not ok, f"禁用词 {term} 应被拒绝"


def test_verify_grounding_accepts_valid_output() -> None:
    text = "入场条件成立 [rule_id:first_ma_pullback | 证据:confirmed=True]"
    ok, _ = verify_grounding(text, {"first_ma_pullback", "tradability_gate"})
    assert ok


# ---------------------------------------------------------------- 两层标注渲染


def test_template_render_two_layer_provenance() -> None:
    """§14 research_proxy alert 的模板渲染同时含原文出处 + 判定方式为研究代理。"""
    plan = TradePlan(
        plan_id="p1", symbol="000001.SS", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="t", entry_price_ref=3800.0, invalidation_price=3900.0,
        target_b_price=4200.0, target_b_source="swing_high", reward_risk_at_plan=3.5,
        valid_until="2026-12-31", state=PLAN_ARMED, ruleset_version=RULESET, reason="x",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    ctx = MonitorContext(
        last_bar_date="2026-08-04", cache_fallback_used=False, current_close=3820.0,
        ema20=3800.0, tradability_tradable=True, ruleset_version=RULESET,
        opportunities=(OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 3.5, True),),
    )
    alerts = evaluate_plan(plan, ctx)
    assert any(a.code == INVALIDATION_BREACHED for a in alerts)
    text = template_render(alerts, plan=plan, context_min={"last_bar_date": "2026-08-04"})
    assert "规格 §14 原文" in text
    assert RESEARCH_PROXY_MARKER in text
    # 渲染结果自身接地通过（rule_id 都在 alerts 集合内）
    allowed = {a.rule_id for a in alerts if a.rule_id}
    ok, _ = verify_grounding(text, allowed)
    assert ok


# ---------------------------------------------------------------- 降级路径


def test_render_alerts_fallback_on_failed_llm() -> None:
    """LLM 两次都过不了校验 -> 降级模板直出，不抛异常。"""
    plan = TradePlan(
        plan_id="p1", symbol="X", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="t", entry_price_ref=3800.0, invalidation_price=3900.0,
        target_b_price=4200.0, target_b_source="swing_high", reward_risk_at_plan=3.5,
        valid_until="2026-12-31", state=PLAN_ARMED, ruleset_version=RULESET, reason="x",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    ctx = MonitorContext(
        last_bar_date="2026-08-04", cache_fallback_used=False, current_close=3820.0,
        ema20=3800.0, tradability_tradable=True, ruleset_version=RULESET,
        opportunities=(OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 3.5, True),),
    )
    alerts = evaluate_plan(plan, ctx)

    def bad_llm(_alerts, _ctx):  # noqa: ANN001
        return "建议买入 [rule_id:fake_rule]"  # 禁用词 + 超集

    rendered = render_alerts(alerts, plan=plan, llm_render=bad_llm, max_attempts=2)
    expected = template_render(alerts, plan=plan)
    assert rendered == expected  # 降级为模板
    # 模板无禁用词
    assert all(term not in rendered for term in FORBIDDEN_TERMS)


def test_render_alerts_fallback_on_llm_exception() -> None:
    plan = TradePlan(
        plan_id="p1", symbol="X", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="t", entry_price_ref=3800.0, invalidation_price=3900.0,
        target_b_price=4200.0, target_b_source="swing_high", reward_risk_at_plan=3.5,
        valid_until="2026-12-31", state=PLAN_ARMED, ruleset_version=RULESET, reason="x",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    ctx = MonitorContext(
        last_bar_date="2026-08-04", cache_fallback_used=False, current_close=3820.0,
        ema20=3800.0, tradability_tradable=True, ruleset_version=RULESET,
        opportunities=(OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 3.5, True),),
    )
    alerts = evaluate_plan(plan, ctx)

    def exploding_llm(_alerts, _ctx):  # noqa: ANN001
        raise RuntimeError("ark 宕机")

    rendered = render_alerts(alerts, plan=plan, llm_render=exploding_llm)
    assert rendered == template_render(alerts, plan=plan)  # 不抛异常，降级模板


# ---------------------------------------------------------------- 端到端


def test_e2e_draft_armed_alert_action_render_traceable(tmp_path) -> None:  # noqa: ANN001
    """建 draft -> armed -> alert -> 待办 -> 讲解，全程溯源标签可校验。"""
    conn = connect(tmp_path / "e2e.db")
    plan = create_plan(
        conn, symbol="000001.SS", module="A", direction="long", ruleset_version=RULESET,
        reason="x", valid_until="2026-12-31", entry_rule_id="first_ma_pullback",
        entry_lifecycle_id="lc1", entry_trigger_cn="t", entry_price_ref=3800.0,
        invalidation_price=3650.0, target_b_price=4200.0, target_b_source="swing_high",
        reward_risk_at_plan=3.5, thesis_cn="t", invalidation_criteria_cn="i",
        drawdown_playbook_cn="d", take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    assert plan.state == "draft"
    armed = confirm_plan(conn, plan.plan_id)
    assert armed.state == "armed"

    ctx = MonitorContext(
        last_bar_date="2026-08-04", cache_fallback_used=False, current_close=3820.0,
        ema20=3800.0, tradability_tradable=True, ruleset_version=RULESET,
        opportunities=(OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 3.5, True),),
    )
    alerts = evaluate_plan(armed, ctx)
    sync_action_items(conn, armed, alerts)
    items = list_action_items(conn, plan.plan_id, state="open")
    assert any(i.kind == "ENTER" for i in items)

    rendered = render_alerts(alerts, plan=armed, action_items=items,
                             context_min={"last_bar_date": "2026-08-04"})
    allowed = {a.rule_id for a in alerts if a.rule_id}
    ok, reason = verify_grounding(rendered, allowed)
    assert ok, f"渲染输出未过接地校验: {reason}"
    conn.close()


if __name__ == "__main__":
    pass
