"""监督周期通知分级与每日汇总门禁。"""
from __future__ import annotations

from lei_signal.notify.render import render_cycle
from lei_signal.plans.actions import CycleResult
from lei_signal.plans.grounding import FORBIDDEN_TERMS, RESEARCH_PROXY_MARKER, verify_grounding
from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan


def _plan() -> TradePlan:
    return TradePlan(
        plan_id="plan_1",
        symbol="000001.SS",
        module="A",
        direction="long",
        entry_rule_id="first_ma_pullback",
        entry_lifecycle_id="lc1",
        entry_trigger_cn="条件成立",
        entry_price_ref=3800.0,
        invalidation_price=3650.0,
        target_b_price=4200.0,
        target_b_source="swing_high",
        reward_risk_at_plan=3.5,
        valid_until="2026-12-31",
        state="armed",
        ruleset_version="1.3.0",
        reason="测试",
    )


def _alert(code: str, *, action_kind: str | None = None) -> PlanAlert:
    rule_by_code = {
        "ENTRY_CONDITIONS_MET": "first_ma_pullback",
        "EXIT_TRIGGERED": "key_wave_black",
        "INVALIDATION_BREACHED": "plan_invalidation_price",
        "PLAN_EXPIRING": "plan_valid_until",
        "ENTRY_RR_BELOW_IDEAL": "entry_reward_risk",
        "DATA_STALE": "data_freshness",
    }
    return PlanAlert(
        code=code,
        severity="remind",
        rule_id=rule_by_code[code],
        principle_source="规格测试原文",
        next_step_cn="按计划检查条件并记录状态",
        action_kind=action_kind,
    )


def _item(kind: str, code: str, *, nag_count: int = 2) -> ActionItem:
    return ActionItem(
        action_id=f"action_{kind.lower()}",
        plan_id="plan_1",
        kind=kind,
        source_alert_code=code,
        state="open",
        due_from="2026-08-05",
        nag_count=nag_count,
    )


def test_tier_one_is_separate_and_tier_two_is_one_summary() -> None:
    entry = _alert("ENTRY_CONDITIONS_MET", action_kind="ENTER")
    exit_alert = _alert("EXIT_TRIGGERED", action_kind="EXIT")
    result = CycleResult(
        plan_id="plan_1",
        alerts=[entry, exit_alert],
        nagged=[
            _item("ENTER", "ENTRY_CONDITIONS_MET"),
            _item("EXIT", "EXIT_TRIGGERED"),
        ],
    )
    payloads = render_cycle(
        _plan(),
        result,
        action_base_url="https://lei.example.test",
        action_secret="secret",
    )
    assert [payload.tier for payload in payloads] == [1, 2]
    assert payloads[0].action_id == "action_exit"
    assert payloads[1].title.endswith("每日汇总")
    assert payloads[1].body_md.count("ENTRY_CONDITIONS_MET") == 1
    assert len(payloads[1].buttons) == 1


def test_tier_three_and_data_stale_do_not_push() -> None:
    hint = _alert("ENTRY_RR_BELOW_IDEAL")
    assert render_cycle(
        _plan(),
        CycleResult(plan_id="plan_1", alerts=[hint]),
        action_base_url="",
        action_secret="",
    ) == []
    stale = _alert("DATA_STALE")
    entry = _alert("ENTRY_CONDITIONS_MET", action_kind="ENTER")
    assert render_cycle(
        _plan(),
        CycleResult(
            plan_id="plan_1",
            alerts=[stale, entry],
            nagged=[_item("ENTER", "ENTRY_CONDITIONS_MET")],
        ),
        action_base_url="https://lei.example.test",
        action_secret="secret",
    ) == []


def test_rendered_copy_is_grounded_and_contains_two_provenance_layers() -> None:
    alert = _alert("PLAN_EXPIRING", action_kind="REVIEW")
    payloads = render_cycle(
        _plan(),
        CycleResult(plan_id="plan_1", alerts=[alert]),
        action_base_url="",
        action_secret="",
    )
    assert len(payloads) == 1
    body = payloads[0].body_md
    assert "规格测试原文" in body
    assert RESEARCH_PROXY_MARKER in body
    assert not any(term in body for term in FORBIDDEN_TERMS)
    assert verify_grounding(body, set(payloads[0].rule_ids))[0]
