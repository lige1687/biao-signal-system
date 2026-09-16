"""P5 真实数据验证：000001.SS 建计划跑 alert 看催办，非退化。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.plans.actions import run_plan_cycle
from lei_signal.plans.context import context_from_result
from lei_signal.plans.store import (
    confirm_plan,
    create_plan,
    list_action_items,
    list_plans,
)
from lei_signal.storage.sqlite_store import connect

RULESET = "1.3.0"


def test_supervisor_on_real_fixture_000001(tmp_path) -> None:  # noqa: ANN001
    """000001.SS 趋势可交易标的：建计划 -> 跑监督 -> 产出 alert 与待办，非退化。"""
    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet"))
    result = analyze_bars("000001.SS", bars)
    ctx = context_from_result(result, cache_fallback_used=False)

    conn = connect(tmp_path / "real.db")
    # 用 fixture 里真实存在的入场 lifecycle 建计划；没有就建一个无 lifecycle 的（仍能产 meta alert）
    lifecycle = ctx.opportunities[0].lifecycle_id if ctx.opportunities else None
    entry_rule = ctx.opportunities[0].rule_id if ctx.opportunities else "first_ma_pullback"
    plan = create_plan(
        conn, symbol="000001.SS", module="A", direction="long", ruleset_version=RULESET,
        reason="真实数据验证", valid_until="2027-12-31", entry_rule_id=entry_rule,
        entry_lifecycle_id=lifecycle, entry_trigger_cn="t", entry_price_ref=ctx.current_close,
        invalidation_price=ctx.current_close * 0.95 if ctx.current_close else None,
        target_b_price=ctx.current_close * 1.10 if ctx.current_close else None,
        target_b_source="swing_high", reward_risk_at_plan=3.0,
        thesis_cn="冲周线多头回调", invalidation_criteria_cn="收盘跌破 -5%",
        drawdown_playbook_cn="回踩 SMA60 正常", take_profit_plan_cn="到 B1 分批",
        stop_plan_cn="收盘跌破失效价下一日开盘出",
    )
    armed = confirm_plan(conn, plan.plan_id)

    cycle = run_plan_cycle(conn, armed, ctx)
    # 非退化：至少产出 alert（数据/可交易性/入场/失效价等之一）
    assert len(cycle.alerts) > 0, "应产出 alert"
    # 至少一条 alert 的 rule_id 可溯源（注册规则）
    assert any(a.rule_id for a in cycle.alerts)
    # 可交易性有明确判定（非空）
    assert ctx.tradability_tradable in (True, False)
    # 若入场条件成立，应产出 ENTER 待办
    if any(a.code == "ENTRY_CONDITIONS_MET" for a in cycle.alerts):
        items = list_action_items(conn, plan.plan_id, state="open")
        assert any(i.kind == "ENTER" for i in items)
    # 计划状态未被运行时擅自改动
    assert list_plans(conn, symbol="000001.SS")[0].state == "armed"
    conn.close()


def test_supervisor_on_blocked_fixture_000300(tmp_path) -> None:  # noqa: ANN001
    """000300.SS 趋势不明阻断：建计划跑监督应产 ENTRY_BLOCKED_BY_TRADABILITY。"""
    bars = pd.read_parquet(Path("tests/000300.SS.bars.parquet"))
    result = analyze_bars("000300.SS", bars)
    ctx = context_from_result(result, cache_fallback_used=False)

    conn = connect(tmp_path / "blocked.db")
    plan = create_plan(
        conn, symbol="000300.SS", module="A", direction="long", ruleset_version=RULESET,
        reason="阻断验证", valid_until="2027-12-31", entry_rule_id="first_ma_pullback",
        entry_lifecycle_id=None, entry_trigger_cn="t",
        entry_price_ref=ctx.current_close,
        invalidation_price=ctx.current_close * 0.95 if ctx.current_close else None,
        target_b_price=None, target_b_source=None, reward_risk_at_plan=None,
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    armed = confirm_plan(conn, plan.plan_id)
    cycle = run_plan_cycle(conn, armed, ctx)
    # 000300 趋势不明 -> 应被可交易性阻断（或至少产出 alert）
    assert len(cycle.alerts) > 0
    if not ctx.tradability_tradable:
        assert any(a.code == "ENTRY_BLOCKED_BY_TRADABILITY" for a in cycle.alerts)
    conn.close()
