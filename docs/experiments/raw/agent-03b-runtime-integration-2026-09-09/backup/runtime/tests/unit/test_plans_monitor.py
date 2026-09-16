"""P1 监督判定门禁：12 alert code truth table + 溯源/红线1/幂等/两层标注/无裸数值。"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from lei_signal.domain.rules_config import get_rule
from lei_signal.plans.models import (
    PLAN_ARMED,
    PLAN_ENTERED,
    TradePlan,
)
from lei_signal.plans.monitor import (
    DATA_STALE,
    ENTRY_BLOCKED_BY_TRADABILITY,
    ENTRY_CONDITIONS_LOST,
    ENTRY_CONDITIONS_MET,
    ENTRY_RR_BELOW_IDEAL,
    ENTRY_RR_NOT_COMPUTABLE,
    EXIT_TRIGGERED,
    INVALIDATION_BREACHED,
    MODULE_NOT_IMPLEMENTED,
    PLAN_EXPIRING,
    PLAN_ORPHANED,
    PLAN_STALE_RULESET,
    ExitSignalRef,
    MonitorContext,
    OpportunityRef,
    evaluate_plan,
    evaluate_resume,
)

RULESET = "1.3.0"


def _plan(**overrides) -> TradePlan:
    defaults = dict(
        plan_id="p1", symbol="000001.SS", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="站回 SMA20", entry_price_ref=3800.0,
        invalidation_price=3650.0, target_b_price=4200.0, target_b_source="swing_high",
        reward_risk_at_plan=3.5, valid_until="2026-12-31", state=PLAN_ARMED,
        ruleset_version=RULESET, reason="x",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    defaults.update(overrides)
    return TradePlan(**defaults)


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


def _codes(alerts) -> set[str]:  # noqa: ANN001
    return {a.code for a in alerts}


def _by_code(alerts, code):  # noqa: ANN001
    return next((a for a in alerts if a.code == code), None)


# ---------------------------------------------------------------- truth table


def test_entry_conditions_met_positive_negative() -> None:
    # 正：armed + confirmed=True
    assert ENTRY_CONDITIONS_MET in _codes(evaluate_plan(_plan(), _ctx()))
    # 反：confirmed=False -> 不触发 MET，转 LOST
    opp = OpportunityRef("lc1", False, "weakened", "first_ma_pullback", 3.5, True)
    alerts = evaluate_plan(_plan(), _ctx(opportunities=(opp,)))
    assert ENTRY_CONDITIONS_MET not in _codes(alerts)
    assert ENTRY_CONDITIONS_LOST in _codes(alerts)


def test_entry_blocked_by_tradability() -> None:
    # 正：tradable=False
    alerts = evaluate_plan(_plan(), _ctx(tradability_tradable=False,
                                         tradability_blocking_reasons=("横盘反复",)))
    a = _by_code(alerts, ENTRY_BLOCKED_BY_TRADABILITY)
    assert a is not None and a.severity == "block"
    assert a.evidence["blocking_reasons"] == ["横盘反复"]
    # 反：tradable=True
    assert ENTRY_BLOCKED_BY_TRADABILITY not in _codes(evaluate_plan(_plan(), _ctx()))


def test_entry_rr_below_ideal() -> None:
    rr_min = float(get_rule("reward_risk_filter").param("rr_min_ideal", 3))
    opp = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", rr_min - 0.5, True)
    alerts = evaluate_plan(_plan(), _ctx(opportunities=(opp,)))
    a = _by_code(alerts, ENTRY_RR_BELOW_IDEAL)
    assert a is not None and a.severity == "hint"
    # 反：R/R >= min
    opp2 = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", rr_min + 1, True)
    assert ENTRY_RR_BELOW_IDEAL not in _codes(evaluate_plan(_plan(), _ctx(opportunities=(opp2,))))


def test_entry_rr_not_computable() -> None:
    opp = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", None, False)
    alerts = evaluate_plan(_plan(), _ctx(opportunities=(opp,)))
    assert ENTRY_RR_NOT_COMPUTABLE in _codes(alerts)
    # 反：computable=True -> 不触发 NOT_COMPUTABLE
    opp2 = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 4.0, True)
    alerts2 = evaluate_plan(_plan(), _ctx(opportunities=(opp2,)))
    assert ENTRY_RR_NOT_COMPUTABLE not in _codes(alerts2)


def test_invalidation_breached() -> None:
    # 正：close < invalidation_price
    alerts = evaluate_plan(_plan(invalidation_price=3900.0), _ctx(current_close=3820.0))
    a = _by_code(alerts, INVALIDATION_BREACHED)
    assert a is not None and a.severity == "block"
    # entered 时产 EXIT 待办
    ent_alerts = evaluate_plan(
        _plan(state=PLAN_ENTERED, invalidation_price=3900.0), _ctx(current_close=3820.0)
    )
    a_ent = _by_code(ent_alerts, INVALIDATION_BREACHED)
    assert a_ent is not None and a_ent.action_kind == "EXIT"
    # 反：close >= invalidation_price
    assert INVALIDATION_BREACHED not in _codes(evaluate_plan(_plan(), _ctx(current_close=3820.0)))


def test_exit_triggered() -> None:
    esig = ExitSignalRef(rule_id="exit_ema20_costbasis", state="active")
    # 正：entered + active exit signal
    alerts = evaluate_plan(_plan(state=PLAN_ENTERED, invalidation_price=3600.0),
                           _ctx(current_close=3820.0, exit_signals=(esig,)))
    a = _by_code(alerts, EXIT_TRIGGERED)
    assert a is not None and a.action_kind == "EXIT"
    # 反：armed 不触发 exit alert
    assert EXIT_TRIGGERED not in _codes(
        evaluate_plan(_plan(), _ctx(exit_signals=(esig,)))
    )


def test_plan_expiring() -> None:
    # 正：last_bar_date >= valid_until
    alerts = evaluate_plan(_plan(valid_until="2026-08-04"), _ctx(last_bar_date="2026-08-04"))
    a = _by_code(alerts, PLAN_EXPIRING)
    assert a is not None and a.action_kind == "REVIEW"
    # 反：未到期
    assert PLAN_EXPIRING not in _codes(
        evaluate_plan(_plan(valid_until="2026-12-31"), _ctx(last_bar_date="2026-08-04"))
    )
    # 到期不自动改 plan 状态
    assert _plan(valid_until="2026-08-04").state == PLAN_ARMED


def test_plan_stale_ruleset() -> None:
    alerts = evaluate_plan(_plan(ruleset_version="1.0.0"), _ctx(ruleset_version="1.3.0"))
    a = _by_code(alerts, PLAN_STALE_RULESET)
    assert a is not None and a.action_kind == "REVIEW"
    # 反：版本一致
    assert PLAN_STALE_RULESET not in _codes(evaluate_plan(_plan(), _ctx()))


def test_plan_orphaned() -> None:
    # 正：entry_lifecycle_id 在 DTO 中找不到
    alerts = evaluate_plan(_plan(entry_lifecycle_id="ghost"),
                           _ctx(opportunities=()))
    assert PLAN_ORPHANED in _codes(alerts)
    # 反：存在
    assert PLAN_ORPHANED not in _codes(evaluate_plan(_plan(), _ctx()))


def test_opposite_direction_opportunity_does_not_match() -> None:
    """做多计划不得拿同名的空头场景当入场条件（红线4：方向不混算）。

    回归：ma_full_alignment 场景的 direction 随排列方向变，曾把
    ma_alignment_bearish_start 当作做多入场机会并产 ENTER 待办。
    """
    short_opp = OpportunityRef(
        lifecycle_id="lc1", current_conditions_confirmed=True, state="confirmed",
        rule_id="ma_full_alignment", reward_risk_ratio=None,
        reward_risk_computable=False, direction="short",
    )
    alerts = evaluate_plan(_plan(direction="long"), _ctx(opportunities=(short_opp,)))
    codes = _codes(alerts)
    assert ENTRY_CONDITIONS_MET not in codes, "空头机会不得触发做多入场"
    assert not any(a.action_kind == "ENTER" for a in alerts), "不得产 ENTER 待办"
    # 方向不匹配 = 找不到对应机会 -> 视为 orphaned，提醒复核
    assert PLAN_ORPHANED in codes


def test_same_direction_opportunity_matches() -> None:
    short_opp = OpportunityRef(
        lifecycle_id="lc1", current_conditions_confirmed=True, state="confirmed",
        rule_id="ma_full_alignment", reward_risk_ratio=None,
        reward_risk_computable=False, direction="short",
    )
    alerts = evaluate_plan(_plan(direction="short"), _ctx(opportunities=(short_opp,)))
    assert ENTRY_CONDITIONS_MET in _codes(alerts)


def test_module_not_implemented() -> None:
    # B/C 已实现，不再触发 MODULE_NOT_IMPLEMENTED；A/D 同样不触发。
    for module in ("A", "B", "C", "D"):
        assert MODULE_NOT_IMPLEMENTED not in _codes(
            evaluate_plan(_plan(module=module), _ctx())
        )
    # 反：未登记的模块仍触发（由 module_backtest.MODULE_MAP 派生）。
    a = _by_code(evaluate_plan(_plan(module="Z"), _ctx()), MODULE_NOT_IMPLEMENTED)
    assert a is not None and a.severity == "hint"


def test_data_stale() -> None:
    alerts = evaluate_plan(_plan(), _ctx(cache_fallback_used=True))
    a = _by_code(alerts, DATA_STALE)
    assert a is not None and a.severity == "hint"
    assert DATA_STALE not in _codes(evaluate_plan(_plan(), _ctx()))


# ---------------------------------------------------------------- 红线与质量


def test_every_alert_rule_id_resolves() -> None:
    """溯源闭环：每条 alert 的 rule_id 必须能被 get_rule() 命中。"""
    cases = [
        evaluate_plan(_plan(), _ctx(tradability_tradable=False)),
        evaluate_plan(_plan(state=PLAN_ENTERED, invalidation_price=3900.0),
                      _ctx(current_close=3820.0,
                           exit_signals=(ExitSignalRef("exit_ema20_costbasis", "active"),))),
        evaluate_plan(_plan(module="B", ruleset_version="1.0.0", entry_lifecycle_id="ghost"),
                      _ctx(opportunities=(), cache_fallback_used=True)),
    ]
    for alerts in cases:
        for a in alerts:
            assert a.rule_id is not None, f"{a.code} 缺 rule_id"
            get_rule(a.rule_id)  # 命中否则 KeyError -> 测试失败


def test_actionable_from_strictly_after_data_as_of() -> None:
    """红线 1：actionable_from 严格晚于 data_as_of。"""
    alerts = evaluate_plan(_plan(), _ctx(last_bar_date="2026-08-04"))
    for a in alerts:
        assert a.actionable_from > a.data_as_of, f"{a.code}: {a.actionable_from} <= {a.data_as_of}"


def test_evaluate_plan_is_idempotent() -> None:
    plan = _plan()
    ctx = _ctx(tradability_tradable=False, cache_fallback_used=True)
    a1 = evaluate_plan(plan, ctx)
    a2 = evaluate_plan(plan, ctx)
    assert [(a.code, a.rule_id, a.evidence, a.actionable_from) for a in a1] == \
           [(a.code, a.rule_id, a.evidence, a.actionable_from) for a in a2]


def test_two_layer_provenance_for_section14_alert() -> None:
    """两层标注：INVALIDATION_BREACHED 同时含原文出处 + research_proxy + caveat。"""
    alerts = evaluate_plan(_plan(invalidation_price=3900.0), _ctx(current_close=3820.0))
    a = _by_code(alerts, INVALIDATION_BREACHED)
    assert a is not None
    assert a.principle_source == "规格 §14 原文"
    assert a.logic_provenance == "research_proxy"
    assert a.caveat_cn  # 非空


def test_two_layer_provenance_for_rr_alert() -> None:
    opp = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 1.5, True)
    alerts = evaluate_plan(_plan(), _ctx(opportunities=(opp,)))
    a = _by_code(alerts, ENTRY_RR_BELOW_IDEAL)
    assert a is not None
    assert a.principle_source == "规格 §13 第 4 条 原文"
    assert a.logic_provenance == "research_proxy"
    assert a.caveat_cn


def test_monitor_source_has_no_bare_numeric_threshold() -> None:
    """红线 3：monitor.py 不得出现裸数值阈值（rr_min 须来自 get_rule）。"""
    source = Path("src/lei_signal/plans/monitor.py").read_text(encoding="utf-8")
    # 剥离 get_rule(...).param(...) 中的默认值，再扫比较运算符后跟裸数字
    stripped = re.sub(r'param\([^)]*\)', 'param(...)', source)
    # 允许：列表/字典索引、format 精度等；禁止：< 3 / >= 3 / > 2 这类裸阈值
    bare = re.findall(r'[<>]=?\s+\d+(?!\.\d)', stripped)
    # 过滤掉 RESOLVABLE_PATHS 元组下标、ops 字典键等无害命中
    real = [b for b in bare if b not in (">= 0",)]
    assert not real, f"monitor.py 出现裸数值阈值: {real}"


# ---------------------------------------------------------------- evaluate_resume


def test_resume_rule_id_form() -> None:
    ctx = _ctx(new_event_rule_ids=("exit_ema20_costbasis",))
    assert evaluate_resume({"rule_id": "exit_ema20_costbasis"}, ctx) is True
    assert evaluate_resume({"rule_id": "first_ma_pullback"}, ctx) is False


def test_resume_field_comparison() -> None:
    ctx = _ctx(current_close=3900.0, ema20=3800.0)
    assert evaluate_resume({"field": "close", "op": ">=", "ref": "ema20"}, ctx) is True
    assert evaluate_resume({"field": "close", "op": ">=", "ref": 4000.0}, ctx) is False
    assert evaluate_resume({"field": "tradability.tradable", "op": "==", "ref": True}, ctx) is True


def test_resume_rejects_unresolvable_path() -> None:
    with pytest.raises(ValueError, match="算不出的路径"):
        evaluate_resume({"field": "volume_anomaly", "op": ">=", "ref": 1.5}, _ctx())


if __name__ == "__main__":
    pass
