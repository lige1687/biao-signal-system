"""草稿符合性判定门禁：硬阻断 / 软建议 / can_confirm / holding_watch 退出核对。"""
from __future__ import annotations

from lei_signal.plans.conformance import (
    DIRECTION_MISMATCH,
    ENTRY_BLOCKED_BY_TRADABILITY,
    ENTRY_RULE_NOT_ENTRY_MODULE,
    INVALIDATION_ALREADY_BREACHED,
    MISSING_EXIT_TRIGGER,
    MISSING_INVALIDATION,
    MODULE_NOT_IMPLEMENTED,
    MODULE_RULE_MISMATCH,
    MODULE_SCENARIO_MISMATCH,
    PLAN_ORPHANED,
    RR_BELOW_IDEAL,
    RR_NOT_COMPUTABLE,
    TP_SL_DIRECTION_INSANE,
    evaluate_draft_conformance,
)
from lei_signal.plans.models import (
    PLAN_DRAFT,
    PLAN_KIND_HOLDING_WATCH,
    TradePlan,
)
from lei_signal.plans.monitor import MonitorContext, OpportunityRef

RULESET = "1.3.0"


def _plan(**overrides) -> TradePlan:
    defaults = dict(
        plan_id="p1", symbol="000001.SS", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="站回 SMA20", entry_price_ref=3800.0,
        invalidation_price=3650.0, target_b_price=4200.0, target_b_source="swing_high",
        reward_risk_at_plan=3.5, valid_until="2026-12-31", state=PLAN_DRAFT,
        ruleset_version=RULESET, reason="x",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    defaults.update(overrides)
    return TradePlan(**defaults)


def _holding(**overrides) -> TradePlan:
    base = _plan(
        plan_kind=PLAN_KIND_HOLDING_WATCH, module="",
        entry_rule_id=None, entry_lifecycle_id=None, entry_price_ref=None,
        invalidation_price=None, target_b_price=None, target_b_source=None,
        reward_risk_at_plan=None, take_profit_price=4000.0, stop_price=3600.0,
        watch_signal_rule_ids=(),
    )
    base_kwargs = {
        **{f: getattr(base, f) for f in (
            "plan_id", "symbol", "module", "direction", "entry_rule_id",
            "entry_lifecycle_id", "entry_trigger_cn", "entry_price_ref",
            "invalidation_price", "target_b_price", "target_b_source",
            "reward_risk_at_plan", "valid_until", "state", "ruleset_version",
            "reason", "thesis_cn", "invalidation_criteria_cn",
            "drawdown_playbook_cn", "take_profit_plan_cn", "stop_plan_cn",
            "plan_kind", "take_profit_price", "stop_price",
            "watch_signal_rule_ids",
        )},
    }
    base_kwargs.update(overrides)
    return TradePlan(**base_kwargs)


def _ctx(**overrides) -> MonitorContext:
    defaults = dict(
        last_bar_date="2026-08-04", cache_fallback_used=False,
        current_close=3820.0, ema20=3800.0, tradability_tradable=True,
        tradability_blocking_reasons=(), ruleset_version=RULESET,
        opportunities=(
            OpportunityRef(lifecycle_id="lc1", current_conditions_confirmed=True,
                           state="confirmed", rule_id="first_ma_pullback",
                           reward_risk_ratio=3.5, reward_risk_computable=True),
        ),
        exit_signals=(), new_event_rule_ids=(),
    )
    defaults.update(overrides)
    return MonitorContext(**defaults)


def _hard(plan: TradePlan, ctx: MonitorContext) -> set[str]:
    return {i.code for i in evaluate_draft_conformance(plan, ctx).hard_issues}


def _soft(plan: TradePlan, ctx: MonitorContext) -> set[str]:
    return {i.code for i in evaluate_draft_conformance(plan, ctx).soft_issues}


# ---------------------------------------------------------------- entry: clean


def test_entry_clean_can_confirm() -> None:
    r = evaluate_draft_conformance(_plan(), _ctx())
    assert r.can_confirm
    assert r.hard_issues == []
    assert r.soft_issues == []


# ---------------------------------------------------------------- entry: hard


def test_module_not_implemented() -> None:
    assert MODULE_NOT_IMPLEMENTED in _hard(_plan(module="X"), _ctx())


def test_entry_blocked_by_tradability() -> None:
    ctx = _ctx(tradability_tradable=False,
               tradability_blocking_reasons=("横盘反复",))
    assert ENTRY_BLOCKED_BY_TRADABILITY in _hard(_plan(), ctx)


def test_missing_invalidation() -> None:
    assert MISSING_INVALIDATION in _hard(_plan(invalidation_price=None), _ctx())


def test_invalidation_already_breached_long() -> None:
    # close 3650 <= invalidation 3650 -> 已到失效价，不该开仓
    ctx = _ctx(current_close=3650.0)
    assert INVALIDATION_ALREADY_BREACHED in _hard(_plan(invalidation_price=3650.0), ctx)


def test_invalidation_already_breached_short() -> None:
    plan = _plan(direction="short", invalidation_price=3900.0)
    ctx = _ctx(current_close=3900.0)  # close >= invalidation for short
    assert INVALIDATION_ALREADY_BREACHED in _hard(plan, ctx)


def test_module_rule_mismatch() -> None:
    # module=A 但 entry_rule_id=false_breakout_reclaim 属于 D
    assert MODULE_RULE_MISMATCH in _hard(
        _plan(module="A", entry_rule_id="false_breakout_reclaim"), _ctx()
    )


def test_entry_rule_not_entry_module() -> None:
    # low_level_confirmation 不映射到 A/B/C/D（确认信号当入场触发）
    assert ENTRY_RULE_NOT_ENTRY_MODULE in _hard(
        _plan(entry_rule_id="low_level_confirmation", entry_lifecycle_id="ll1"),
        _ctx(),
    )


def test_direction_mismatch() -> None:
    opp = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback",
                         3.5, True, direction="short")
    assert DIRECTION_MISMATCH in _hard(_plan(direction="long"), _ctx(opportunities=(opp,)))


def test_hard_blocks_confirm() -> None:
    assert not evaluate_draft_conformance(
        _plan(module="X"), _ctx()
    ).can_confirm


# ---------------------------------------------------------------- entry: soft


def test_rr_below_ideal_is_soft() -> None:
    r = evaluate_draft_conformance(_plan(reward_risk_at_plan=2.0), _ctx())
    assert RR_BELOW_IDEAL in {i.code for i in r.soft_issues}
    assert r.can_confirm  # 软项不阻断


def test_rr_not_computable_is_soft() -> None:
    r = evaluate_draft_conformance(_plan(reward_risk_at_plan=None), _ctx())
    assert RR_NOT_COMPUTABLE in {i.code for i in r.soft_issues}
    assert r.can_confirm


def test_module_scenario_mismatch_is_soft() -> None:
    # 系统主力场景属 D，用户选 A -> 软提醒
    opp = OpportunityRef("lc9", True, "confirmed", "false_breakout_reclaim",
                         4.0, True)
    r = evaluate_draft_conformance(_plan(), _ctx(opportunities=(opp,)))
    assert MODULE_SCENARIO_MISMATCH in {i.code for i in r.soft_issues}
    assert r.can_confirm


def test_plan_orphaned_is_soft() -> None:
    # lifecycle 与 rule_id 都不匹配才算孤儿（rule_id 仍匹配说明信号还在）
    r = evaluate_draft_conformance(
        _plan(entry_rule_id=None, entry_lifecycle_id="gone"), _ctx()
    )
    assert PLAN_ORPHANED in {i.code for i in r.soft_issues}
    assert r.can_confirm


# ---------------------------------------------------------------- holding_watch


def test_holding_clean_can_confirm() -> None:
    r = evaluate_draft_conformance(_holding(), _ctx())
    assert r.can_confirm
    assert r.hard_issues == []


def test_holding_tp_direction_insane() -> None:
    # long：止盈价 <= close（止盈在下方）-> 硬阻断
    assert TP_SL_DIRECTION_INSANE in _hard(
        _holding(take_profit_price=3800.0), _ctx(current_close=3820.0)
    )


def test_holding_stop_direction_insane() -> None:
    # long：止损价 >= close（止损在上方）-> 硬阻断
    assert TP_SL_DIRECTION_INSANE in _hard(
        _holding(stop_price=3900.0), _ctx(current_close=3820.0)
    )


def test_holding_missing_exit_trigger() -> None:
    plan = _holding(take_profit_price=None, stop_price=None,
                    watch_signal_rule_ids=())
    assert MISSING_EXIT_TRIGGER in _hard(plan, _ctx())


def test_holding_short_tp_insane() -> None:
    # short：止盈价 >= close（止盈在上方）-> 硬阻断
    plan = _holding(direction="short", take_profit_price=3900.0, stop_price=4100.0)
    assert TP_SL_DIRECTION_INSANE in _hard(plan, _ctx(current_close=3820.0))


# ---------------------------------------------------------------- system_detected


def test_system_detected_reflects_match() -> None:
    r = evaluate_draft_conformance(_plan(), _ctx())
    assert r.system_detected["module"] == "A"
    assert r.system_detected["direction"] == "long"
    assert any(s["module"] == "A" for s in r.system_detected["scenarios"])
