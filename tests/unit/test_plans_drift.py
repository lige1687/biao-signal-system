"""P3 漂移复议门禁：方向分类器 + 硬规则 truth table。"""
from __future__ import annotations

from lei_signal.plans.drift import (
    DIRECTION_RELAX,
    DIRECTION_TIGHTEN,
    check_revision,
)
from lei_signal.plans.models import PLAN_ARMED, PLAN_ENTERED, TradePlan

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


# ---------------------------------------------------------------- 方向分类器


def test_long_tighten_within_playbook() -> None:
    # 多头上移失效价 = 收紧 = 移动止盈 -> 放行
    v = check_revision(_plan(invalidation_price=3650.0), {"invalidation_price": 3700.0})
    assert v.verdict == "within_playbook"
    assert v.direction == DIRECTION_TIGHTEN


def test_long_relax_needs_review() -> None:
    # 多头下移失效价 = 放宽 -> 复议
    v = check_revision(_plan(invalidation_price=3650.0), {"invalidation_price": 3600.0})
    assert v.verdict == "needs_review"
    assert v.direction == DIRECTION_RELAX


def test_short_relax_needs_review() -> None:
    # 空头上移失效价 = 放宽 -> 复议
    v = check_revision(_plan(direction="short", invalidation_price=4200.0),
                       {"invalidation_price": 4250.0})
    assert v.verdict == "needs_review"
    assert v.direction == DIRECTION_RELAX


def test_short_tighten_within_playbook() -> None:
    # 空头下移失效价 = 收紧 -> 放行
    v = check_revision(_plan(direction="short", invalidation_price=4200.0),
                       {"invalidation_price": 4150.0})
    assert v.verdict == "within_playbook"
    assert v.direction == DIRECTION_TIGHTEN


def test_invalidation_unchanged_within_playbook() -> None:
    v = check_revision(_plan(invalidation_price=3650.0), {"invalidation_price": 3650.0})
    assert v.verdict == "within_playbook"
    assert v.direction is None


# ---------------------------------------------------------------- 硬规则


def test_entered_change_entry_rule_needs_review() -> None:
    v = check_revision(_plan(state=PLAN_ENTERED), {"entry_rule_id": "false_breakout_reclaim"})
    assert v.verdict == "needs_review"
    assert "§14" in v.reason_cn


def test_armed_change_entry_rule_within_playbook() -> None:
    # armed 阶段换入场理由不在硬规则内（尚未进场）-> 预案内
    v = check_revision(_plan(state=PLAN_ARMED), {"entry_rule_id": "false_breakout_reclaim"})
    assert v.verdict == "within_playbook"


def test_change_module_needs_review() -> None:
    v = check_revision(_plan(module="A"), {"module": "D"})
    assert v.verdict == "needs_review"
    assert "§12" in v.reason_cn


def test_change_thesis_cn_needs_review() -> None:
    v = check_revision(_plan(), {"thesis_cn": "改主意了"})
    assert v.verdict == "needs_review"


def test_change_invalidation_criteria_needs_review() -> None:
    v = check_revision(_plan(), {"invalidation_criteria_cn": "改失效条件"})
    assert v.verdict == "needs_review"


def test_change_drawdown_playbook_needs_review() -> None:
    v = check_revision(_plan(), {"drawdown_playbook_cn": "改下跌预案"})
    assert v.verdict == "needs_review"


# ---------------------------------------------------------------- 非冻结字段


def test_non_frozen_field_within_playbook() -> None:
    v = check_revision(_plan(), {"entry_trigger_cn": "细化触发条件"})
    assert v.verdict == "within_playbook"
