"""P2 待办与催办门禁：nag 幂等 / DATA_STALE / 复活 / validate / superseded / 到期 / dry-run。"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.domain.rules_config import ruleset_version
from lei_signal.plans.actions import (
    run_plan_cycle,
    validate_resume_on,
)
from lei_signal.plans.context import context_from_result
from lei_signal.plans.monitor import MonitorContext, OpportunityRef
from lei_signal.plans.store import (
    create_plan,
    list_action_items,
    list_annotations,
    list_plans,
    set_entered,
)
from lei_signal.storage.sqlite_store import connect

RULESET = "1.3.0"


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


def _make_armed_plan(conn, **overrides):
    kwargs = dict(
        symbol="000001.SS", module="A", direction="long", ruleset_version=RULESET,
        reason="x", valid_until="2026-12-31", entry_rule_id="first_ma_pullback",
        entry_lifecycle_id="lc1", entry_trigger_cn="t", entry_price_ref=3800.0,
        invalidation_price=3650.0, target_b_price=4200.0, target_b_source="swing_high",
        reward_risk_at_plan=3.5, thesis_cn="t", invalidation_criteria_cn="i",
        drawdown_playbook_cn="d", take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    kwargs.update(overrides)
    plan = create_plan(conn, **kwargs)
    from lei_signal.plans.store import confirm_plan
    return confirm_plan(conn, plan.plan_id)


# ---------------------------------------------------------------- nag 幂等 / DATA_STALE


def test_nag_idempotent_same_bar_date(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "nag.db")
    plan = _make_armed_plan(conn)
    ctx = _ctx(last_bar_date="2026-08-04")
    run_plan_cycle(conn, plan, ctx)
    items = list_action_items(conn, plan.plan_id, state="open")
    assert items, "应创建开放待办"
    n1 = items[0].nag_count
    assert n1 == 1
    # 同一 last_bar_date 再跑 -> nag_count 不变（幂等）
    plan2 = list_plans(conn, symbol="000001.SS")[0]
    run_plan_cycle(conn, plan2, ctx)
    assert list_action_items(conn, plan.plan_id, state="open")[0].nag_count == n1
    conn.close()


def test_nag_advances_on_new_bar_date(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "nag2.db")
    plan = _make_armed_plan(conn)
    run_plan_cycle(conn, plan, _ctx(last_bar_date="2026-08-04"))
    plan2 = list_plans(conn, symbol="000001.SS")[0]
    run_plan_cycle(conn, plan2, _ctx(last_bar_date="2026-08-05"))
    assert list_action_items(conn, plan.plan_id, state="open")[0].nag_count == 2
    conn.close()


def test_data_stale_does_not_increment_nag(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "stale.db")
    plan = _make_armed_plan(conn)
    run_plan_cycle(conn, plan, _ctx(last_bar_date="2026-08-04", cache_fallback_used=True))
    items = list_action_items(conn, plan.plan_id, state="open")
    assert all(i.nag_count == 0 for i in items)
    conn.close()


# ---------------------------------------------------------------- 复活


def test_revive_deferred_when_condition_met(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "rev.db")
    plan = _make_armed_plan(conn)
    from lei_signal.plans.store import update_action_item, upsert_action_item
    item = upsert_action_item(
        conn, plan_id=plan.plan_id, kind="ENTER", source_alert_code="ENTRY_CONDITIONS_MET",
        state="open", due_from="2026-08-05",
    )
    update_action_item(
        conn, item.action_id, state="deferred",
        resume_on=json.dumps({"field": "close", "op": ">=", "ref": "ema20"}),
    )
    # close >= ema20 -> 复活
    plan2 = list_plans(conn, symbol="000001.SS")[0]
    run_plan_cycle(conn, plan2, _ctx(current_close=3900.0, ema20=3800.0))
    revived = list_action_items(conn, plan.plan_id)
    assert any(i.state == "open" for i in revived)
    assert any("复活" in a.reason_cn for a in list_annotations(conn, plan.plan_id))
    conn.close()


def test_revive_stays_deferred_when_condition_unmet(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "rev2.db")
    plan = _make_armed_plan(conn)
    from lei_signal.plans.store import update_action_item, upsert_action_item
    item = upsert_action_item(
        conn, plan_id=plan.plan_id, kind="ENTER", source_alert_code="ENTRY_CONDITIONS_MET",
        state="open", due_from="2026-08-05",
    )
    update_action_item(
        conn, item.action_id, state="deferred",
        resume_on=json.dumps({"field": "close", "op": ">=", "ref": "ema20"}),
    )
    plan2 = list_plans(conn, symbol="000001.SS")[0]
    run_plan_cycle(conn, plan2, _ctx(current_close=3700.0, ema20=3800.0))
    items = list_action_items(conn, plan.plan_id, state="deferred")
    assert len(items) == 1  # 仍 deferred
    conn.close()


# ---------------------------------------------------------------- validate_resume_on


def test_validate_resume_on_rejects_unknown_rule_id() -> None:
    with pytest.raises(ValueError, match="未注册的 rule_id"):
        validate_resume_on({"rule_id": "not_a_rule"}, _ctx())


def test_validate_resume_on_rejects_unknown_path() -> None:
    with pytest.raises(ValueError, match="算不出的路径"):
        validate_resume_on({"field": "volume_anomaly", "op": ">=", "ref": 1.5}, _ctx())


def test_validate_resume_on_accepts_valid_predicate() -> None:
    validate_resume_on({"field": "close", "op": ">=", "ref": "ema20"}, _ctx())
    validate_resume_on({"rule_id": "first_ma_pullback"}, _ctx())


# ---------------------------------------------------------------- superseded


def test_supersede_same_symbol_direction(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "sup.db")
    plan_a = _make_armed_plan(conn)  # 第一条 armed
    plan_b = _make_armed_plan(conn)  # 第二条 armed，同标的同向
    # plan_b 转 entered -> plan_a 应被顶替
    set_entered(conn, plan_b.plan_id, entered_on="2026-08-04")
    entered = list_plans(conn, symbol="000001.SS", state="entered")[0]
    run_plan_cycle(conn, entered, _ctx())
    a_after = list_plans(conn, symbol="000001.SS")
    a_states = {p.plan_id: p.state for p in a_after}
    assert a_states[plan_a.plan_id] == "superseded"
    assert any("顶替" in a.reason_cn for a in list_annotations(conn, plan_a.plan_id))
    conn.close()


# ---------------------------------------------------------------- valid_until 到期


def test_valid_until_expiry_creates_review_not_change_state(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "exp.db")
    plan = _make_armed_plan(conn, valid_until="2026-08-04")
    run_plan_cycle(conn, plan, _ctx(last_bar_date="2026-08-04"))
    reviews = list_action_items(conn, plan.plan_id, state="open")
    assert any(i.kind == "REVIEW" for i in reviews)
    # plan 状态不变
    assert list_plans(conn, symbol="000001.SS")[0].state == "armed"
    conn.close()


# ---------------------------------------------------------------- dry-run：fixture 取数


def test_context_from_result_on_fixture() -> None:
    """fixture 路径产出的 MonitorContext 非空（dry-run 取数基础）。"""
    from lei_signal.compose.pipeline import analyze_bars
    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet"))
    result = analyze_bars("000001.SS", bars)
    ctx = context_from_result(result, cache_fallback_used=False)
    assert ctx.last_bar_date
    assert ctx.current_close is not None
    assert ctx.ruleset_version == ruleset_version()


def test_context_from_result_fixture_marks_stale() -> None:
    from lei_signal.compose.pipeline import analyze_bars
    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet"))
    result = analyze_bars("000001.SS", bars)
    ctx = context_from_result(result, cache_fallback_used=True)
    assert ctx.cache_fallback_used is True


# ---------------------------------------------------------------- §13 入场阻断优先


def test_entry_block_suppresses_enter_action_item(tmp_path) -> None:  # noqa: ANN001
    """规格 §13「满足任一情况，不开新仓」：入场被阻断时不产 ENTER 待办。

    回归：曾同时产出 ENTRY_BLOCKED_BY_TRADABILITY(block) 与 ENTRY_CONDITIONS_MET，
    并照产 ENTER 待办天天催入场，直接违背 §13。
    """
    conn = connect(tmp_path / "block.db")
    plan = _make_armed_plan(conn)
    ctx = _ctx(tradability_tradable=False,
               tradability_blocking_reasons=("5.横盘反复且无标志性动作",))
    cycle = run_plan_cycle(conn, plan, ctx)
    codes = [a.code for a in cycle.alerts]
    # 两条 alert 都保留（客观事实不删）
    assert "ENTRY_BLOCKED_BY_TRADABILITY" in codes
    assert "ENTRY_CONDITIONS_MET" in codes
    # 但不产 ENTER 待办
    items = list_action_items(conn, plan.plan_id, state="open")
    assert not any(i.kind == "ENTER" for i in items), "阻断时不得产 ENTER 待办"
    conn.close()


def test_entry_block_closes_existing_open_enter(tmp_path) -> None:  # noqa: ANN001
    """先有开放 ENTER 待办，随后环境转为阻断 -> 该待办被关闭，不再催办。"""
    conn = connect(tmp_path / "block2.db")
    plan = _make_armed_plan(conn)
    # 第一轮：可交易，产 ENTER 待办
    run_plan_cycle(conn, plan, _ctx(last_bar_date="2026-08-04"))
    assert any(i.kind == "ENTER" for i in list_action_items(conn, plan.plan_id, state="open"))
    # 第二轮：转为阻断
    plan2 = list_plans(conn, symbol="000001.SS")[0]
    run_plan_cycle(conn, plan2, _ctx(last_bar_date="2026-08-05",
                                     tradability_tradable=False,
                                     tradability_blocking_reasons=("横盘反复",)))
    open_kinds = [i.kind for i in list_action_items(conn, plan.plan_id, state="open")]
    assert "ENTER" not in open_kinds, "阻断后既有 ENTER 待办应被关闭"
    conn.close()


def test_rr_below_ideal_does_not_suppress_enter(tmp_path) -> None:  # noqa: ANN001
    """R/R<3 属 §13 第4条，但决策3定为只提示永不拦截 -> 仍产 ENTER 待办。"""
    conn = connect(tmp_path / "rr.db")
    plan = _make_armed_plan(conn)
    low_rr = OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 1.5, True, "long")
    cycle = run_plan_cycle(conn, plan, _ctx(opportunities=(low_rr,)))
    assert "ENTRY_RR_BELOW_IDEAL" in [a.code for a in cycle.alerts]
    items = list_action_items(conn, plan.plan_id, state="open")
    assert any(i.kind == "ENTER" for i in items), "R/R 不足不得拦截入场待办"
    conn.close()
