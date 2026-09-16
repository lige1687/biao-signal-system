"""飞书卡用户视角：正文无工程标注，note 保留一行小字（红线不破）。"""
from __future__ import annotations

from lei_signal.notify.render import (
    _alert_line,
    _provenance_footer,
    _safe_body,
    merge_daily_summaries,
    render_cycle,
)
from lei_signal.plans.actions import CycleResult
from lei_signal.plans.grounding import RESEARCH_PROXY_MARKER
from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan

_NOTE_TEXT = "研究代理判定 · 溯源见系统"


def _alert(**kw):
    base = dict(
        code="ENTRY_CONDITIONS_MET", severity="remind", rule_id="dual_ma_bull",
        evidence={"close": 4029.86}, principle_source="规格 §14 原文",
        logic_provenance="research_proxy", caveat_cn="", actionable_from="2026-08-24",
        data_as_of="2026-08-21", next_step_cn="入场条件成立", action_kind="ENTER",
    )
    base.update(kw)
    return PlanAlert(**base)


def _plan(plan_id: str = "plan_1") -> TradePlan:
    return TradePlan(
        plan_id=plan_id,
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


def _item(code: str, *, kind: str = "ENTER") -> ActionItem:
    return ActionItem(
        action_id=f"action_{code.lower()}",
        plan_id="plan_1",
        kind=kind,
        source_alert_code=code,
        state="open",
        due_from="2026-08-24",
        nag_count=1,
    )


def test_alert_line_has_no_engineering_marks():
    line = _alert_line(_alert())
    assert "rule_id:" not in line
    assert "研究代理" not in line
    assert "入场条件成立" in line  # 人话保留


def test_provenance_footer_keeps_redline_in_note():
    assert _NOTE_TEXT in _provenance_footer([_alert()])
    assert _provenance_footer([]) == ""


def test_action_payload_body_is_human_with_note_and_rule_ids_kept():
    """Tier1 待办卡：正文人话 + 末尾 note；rule_ids 结构字段保留供回调审计。"""
    alert = _alert(code="EXIT_TRIGGERED", rule_id="key_wave_black",
                   next_step_cn="退出条件触发", action_kind="EXIT")
    payloads = render_cycle(
        _plan(),
        CycleResult(
            plan_id="plan_1", alerts=[alert],
            nagged=[_item("EXIT_TRIGGERED", kind="EXIT")],
        ),
        action_base_url="",
        action_secret="",
    )
    assert len(payloads) == 1
    body = payloads[0].body_md
    assert "rule_id:" not in body
    assert RESEARCH_PROXY_MARKER not in body
    assert "规格 §14 原文" not in body
    assert "退出条件触发" in body
    assert body.rstrip().endswith(_NOTE_TEXT)
    assert payloads[0].rule_ids == frozenset({"key_wave_black"})


def test_summary_and_standalone_tier1_carry_note():
    """汇总卡与无待办的 Tier1 独立卡都带 note（红线在每张卡可展开获得）。"""
    summary_alert = _alert(code="PLAN_EXPIRING", rule_id="plan_valid_until",
                           next_step_cn="计划临近到期，请复核")
    standalone = _alert(code="STOP_PRICE_BREACHED", rule_id="stop_price",
                        next_step_cn="止损价击穿")
    payloads = render_cycle(
        _plan(),
        CycleResult(plan_id="plan_1", alerts=[summary_alert, standalone]),
        action_base_url="",
        action_secret="",
    )
    assert [p.tier for p in payloads] == [1, 2]
    for payload in payloads:
        assert "rule_id:" not in payload.body_md
        assert RESEARCH_PROXY_MARKER not in payload.body_md
        assert payload.body_md.rstrip().endswith(_NOTE_TEXT)
    assert payloads[0].rule_ids == frozenset({"stop_price"})
    assert payloads[1].rule_ids == frozenset({"plan_valid_until"})


def test_safe_body_fallback_has_no_engineering_marks():
    """降级分支同样去工程标注：禁用词触发 fallback 时只留人话，rule_ids 照常返回。"""
    alert = _alert(next_step_cn="复核买入条件前不动作")  # 命中禁用词 -> 降级
    body, rule_ids = _safe_body(_alert_line(alert), [alert])
    assert "rule_id:" not in body
    assert RESEARCH_PROXY_MARKER not in body
    assert rule_ids == frozenset({"dual_ma_bull"})


def test_nag_card_without_source_alert_still_carries_note():
    """I-1：催办卡源 alert 本轮未复现（related=[]）但待办仍在催 -> 保底挂 note。

    红线要求每张发出的卡都能找到研究代理标注，不能因源 alert 缺席而裸发。
    """
    payloads = render_cycle(
        _plan(),
        CycleResult(
            plan_id="plan_1", alerts=[],
            nagged=[_item("STOP_PRICE_BREACHED", kind="EXIT")],
        ),
        action_base_url="",
        action_secret="",
    )
    assert len(payloads) == 1
    body = payloads[0].body_md
    assert "EXIT 待办" in body  # 催办头仍在
    assert "rule_id:" not in body
    assert RESEARCH_PROXY_MARKER not in body
    assert body.rstrip().endswith(_NOTE_TEXT)  # note 保底


def test_merge_daily_summaries_keeps_single_note():
    """M-1：合并多计划 Tier2 时去重 note——各段剥尾，整卡末尾只挂一次。"""
    first = render_cycle(
        _plan("plan_1"),
        CycleResult(plan_id="plan_1", alerts=[
            _alert(code="PLAN_EXPIRING", rule_id="plan_valid_until",
                   next_step_cn="计划临近到期，请复核"),
        ]),
        action_base_url="",
        action_secret="",
    )
    second = render_cycle(
        _plan("plan_2"),
        CycleResult(plan_id="plan_2", alerts=[
            _alert(code="TAKE_PROFIT_APPROACHING", rule_id="target_b_near",
                   next_step_cn="接近目标价，请关注"),
        ]),
        action_base_url="",
        action_secret="",
    )
    merged = merge_daily_summaries(first + second)
    assert merged is not None
    body = merged.body_md
    assert "计划临近到期，请复核" in body and "接近目标价，请关注" in body
    assert "\n\n---\n\n" in body  # 分段结构保留
    assert body.count(f"> {_NOTE_TEXT}") == 1  # 单卡单 note
    assert body.rstrip().endswith(_NOTE_TEXT)  # 且挂在整卡末尾
