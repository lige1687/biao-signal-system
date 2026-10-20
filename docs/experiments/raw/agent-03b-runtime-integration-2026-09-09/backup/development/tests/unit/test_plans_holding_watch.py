"""持仓盯盘（plan_kind=holding_watch）判定门禁。

已在场内的标的只监督退出：止盈达到 / 止损击穿 / 信号命中。
入场类判定（可交易性阻断/入场条件/R-R/lifecycle 孤儿/模块未实现）一律不适用。
"""
from __future__ import annotations

import pytest

from lei_signal.plans.models import PLAN_KIND_HOLDING_WATCH, TradePlan
from lei_signal.plans.monitor import (
    ENTRY_BLOCKED_BY_TRADABILITY,
    HOLDING_WATCH_RULE,
    MODULE_NOT_IMPLEMENTED,
    PLAN_ORPHANED,
    SIGNAL_WATCH_TRIGGERED,
    STOP_PRICE_APPROACHING,
    STOP_PRICE_BREACHED,
    TAKE_PROFIT_APPROACHING,
    TAKE_PROFIT_REACHED,
    MonitorContext,
    evaluate_plan,
)
from lei_signal.plans.store import (
    confirm_holding_watch,
    create_plan,
    list_action_items,
)
from lei_signal.storage.sqlite_store import connect


def _plan(
    *,
    direction: str = "long",
    take_profit_price: float | None = None,
    stop_price: float | None = None,
    watch_signal_rule_ids: tuple[str, ...] = (),
    state: str = "entered",
    module: str = "A",
    entry_lifecycle_id: str | None = None,
) -> TradePlan:
    return TradePlan(
        plan_id="p1", symbol="000001.SS", module=module, direction=direction,
        entry_rule_id=None, entry_lifecycle_id=entry_lifecycle_id, entry_trigger_cn=None,
        entry_price_ref=None, invalidation_price=None, target_b_price=None,
        target_b_source=None, reward_risk_at_plan=None, valid_until="2026-12-31",
        state=state, ruleset_version="1.3.0", reason="",
        take_profit_plan_cn="到点分批减", stop_plan_cn="跌破即走",
        plan_kind=PLAN_KIND_HOLDING_WATCH,
        take_profit_price=take_profit_price, stop_price=stop_price,
        watch_signal_rule_ids=watch_signal_rule_ids,
    )


def _ctx(
    close: float | None, *, events: tuple[str, ...] = (), atr: float | None = None
) -> MonitorContext:
    # tradability_tradable=False 故意为假：持仓盯盘不该因环境阻断而报入场类 alert。
    return MonitorContext(
        last_bar_date="2026-08-05", cache_fallback_used=False, current_close=close,
        ema20=None, tradability_tradable=False, atr=atr,
        tradability_blocking_reasons=("横盘不频繁交易",), ruleset_version="1.3.0",
        new_event_rule_ids=events,
    )


def _codes(plan: TradePlan, ctx: MonitorContext) -> list[str]:
    return [a.code for a in evaluate_plan(plan, ctx)]


@pytest.mark.parametrize(
    ("direction", "take_profit", "close", "expected"),
    [
        ("long", 4000.0, 4050.0, True),    # 做多：达到上方止盈
        ("long", 4000.0, 3900.0, False),
        ("short", 3700.0, 3650.0, True),   # 做空：达到下方止盈
        ("short", 3700.0, 3800.0, False),
    ],
)
def test_take_profit_is_direction_aware(
    direction: str, take_profit: float, close: float, expected: bool
) -> None:
    codes = _codes(
        _plan(direction=direction, take_profit_price=take_profit), _ctx(close)
    )
    assert (TAKE_PROFIT_REACHED in codes) is expected


@pytest.mark.parametrize(
    ("direction", "stop", "close", "expected"),
    [
        ("long", 3700.0, 3650.0, True),    # 做多：击穿下方止损
        ("long", 3700.0, 3750.0, False),
        ("short", 4000.0, 4050.0, True),   # 做空：击穿上方止损
        ("short", 4000.0, 3950.0, False),
    ],
)
def test_stop_price_is_direction_aware(
    direction: str, stop: float, close: float, expected: bool
) -> None:
    codes = _codes(_plan(direction=direction, stop_price=stop), _ctx(close))
    assert (STOP_PRICE_BREACHED in codes) is expected


def test_stop_breach_is_block_with_spec_14_provenance() -> None:
    """止损击穿沿用规格 §14 纪律强度：block + 两层标注。"""
    alerts = evaluate_plan(_plan(stop_price=3700.0), _ctx(3650.0))
    stop = next(a for a in alerts if a.code == STOP_PRICE_BREACHED)
    assert stop.severity == "block"
    assert stop.action_kind == "EXIT"
    assert stop.rule_id == HOLDING_WATCH_RULE
    assert stop.principle_source == "规格 §14 原文"
    assert "研究代理" in stop.caveat_cn
    assert "不得事后下移止损" in stop.next_step_cn


def test_take_profit_is_remind_not_block() -> None:
    """止盈是提醒（退出与否仍由人决定），不是阻断。"""
    alerts = evaluate_plan(_plan(take_profit_price=4000.0), _ctx(4050.0))
    tp = next(a for a in alerts if a.code == TAKE_PROFIT_REACHED)
    assert tp.severity == "remind"
    assert tp.action_kind == "EXIT"


def test_signal_watch_triggers_on_new_event_rule_id() -> None:
    """盯的信号（如 lei_color 颜色转换）出现在当日 new_events 即提醒。"""
    plan = _plan(watch_signal_rule_ids=("lei_color", "dual_ma_bull_confirmed"))
    hit = evaluate_plan(plan, _ctx(3800.0, events=("lei_color",)))
    triggered = next(a for a in hit if a.code == SIGNAL_WATCH_TRIGGERED)
    assert triggered.evidence["triggered_rule_ids"] == ["lei_color"]
    assert triggered.action_kind == "EXIT"
    # 未命中不报
    assert SIGNAL_WATCH_TRIGGERED not in _codes(plan, _ctx(3800.0, events=("other",)))


def test_holding_watch_suppresses_entry_class_alerts() -> None:
    """已在场内：不因环境阻断/模块未实现/lifecycle 孤儿而报入场类 alert。"""
    plan = _plan(
        take_profit_price=4000.0,
        module="Z",                      # 未实现模块
        entry_lifecycle_id="missing_lc",  # 当日 DTO 找不到
    )
    codes = _codes(plan, _ctx(4050.0))
    assert ENTRY_BLOCKED_BY_TRADABILITY not in codes
    assert MODULE_NOT_IMPLEMENTED not in codes
    assert PLAN_ORPHANED not in codes
    assert TAKE_PROFIT_REACHED in codes


def test_no_close_price_yields_no_price_alerts() -> None:
    """没有可见收盘价时不猜：不报价位类 alert。"""
    codes = _codes(
        _plan(take_profit_price=4000.0, stop_price=3700.0), _ctx(None)
    )
    assert TAKE_PROFIT_REACHED not in codes
    assert STOP_PRICE_BREACHED not in codes


def test_both_triggers_can_fire_together() -> None:
    """止盈与信号可同时成立（各自独立提醒）。"""
    plan = _plan(take_profit_price=4000.0, watch_signal_rule_ids=("lei_color",))
    codes = _codes(plan, _ctx(4050.0, events=("lei_color",)))
    assert TAKE_PROFIT_REACHED in codes
    assert SIGNAL_WATCH_TRIGGERED in codes


# ---------------- ATR 接近预警（未击穿但在 proximity_atr*atr 带宽内）----------------


def test_take_profit_approaching_within_atr_band() -> None:
    """做多：close 距止盈 50，atr=60（带宽 60）-> 接近预警，未达到。"""
    alerts = evaluate_plan(
        _plan(direction="long", take_profit_price=4000.0), _ctx(3950.0, atr=60.0)
    )
    codes = [a.code for a in alerts]
    assert TAKE_PROFIT_APPROACHING in codes
    assert TAKE_PROFIT_REACHED not in codes
    a = next(x for x in alerts if x.code == TAKE_PROFIT_APPROACHING)
    assert a.severity == "remind"
    assert a.action_kind is None  # 纯提醒，不产 EXIT 待办
    assert a.evidence["distance"] == 50.0
    assert a.evidence["distance_atr"] == pytest.approx(50 / 60)


def test_take_profit_approaching_outside_band_no_alert() -> None:
    """距离超过 1 ATR -> 不报接近。"""
    codes = _codes(
        _plan(direction="long", take_profit_price=4000.0), _ctx(3800.0, atr=60.0)
    )
    assert TAKE_PROFIT_APPROACHING not in codes
    assert TAKE_PROFIT_REACHED not in codes


def test_stop_price_approaching_within_atr_band() -> None:
    """做多：close 距止损 40，atr=60 -> 接近预警，未击穿。"""
    alerts = evaluate_plan(
        _plan(direction="long", stop_price=3700.0), _ctx(3740.0, atr=60.0)
    )
    codes = [a.code for a in alerts]
    assert STOP_PRICE_APPROACHING in codes
    assert STOP_PRICE_BREACHED not in codes
    a = next(x for x in alerts if x.code == STOP_PRICE_APPROACHING)
    assert a.severity == "remind"
    assert a.action_kind is None
    assert "不得事后下移止损" in a.next_step_cn


def test_approaching_suppressed_once_breached() -> None:
    """已击穿/已达 -> 只报击穿，不重复报接近。"""
    # 止损击穿
    codes = _codes(_plan(direction="long", stop_price=3700.0), _ctx(3650.0, atr=60.0))
    assert STOP_PRICE_BREACHED in codes
    assert STOP_PRICE_APPROACHING not in codes
    # 止盈达到
    codes = _codes(
        _plan(direction="long", take_profit_price=4000.0), _ctx(4050.0, atr=60.0)
    )
    assert TAKE_PROFIT_REACHED in codes
    assert TAKE_PROFIT_APPROACHING not in codes


def test_approaching_skipped_when_atr_none() -> None:
    """atr 不可用时静默跳过接近预警（不阻断击穿判定）。"""
    codes = _codes(
        _plan(direction="long", take_profit_price=4000.0, stop_price=3700.0),
        _ctx(3950.0, atr=None),
    )
    assert TAKE_PROFIT_APPROACHING not in codes
    assert STOP_PRICE_APPROACHING not in codes


def test_take_profit_approaching_short_direction() -> None:
    """做空：止盈在下方，close 在其上方 40（未达到），atr=60 -> 接近。"""
    codes = _codes(
        _plan(direction="short", take_profit_price=3700.0), _ctx(3740.0, atr=60.0)
    )
    assert TAKE_PROFIT_APPROACHING in codes
    assert TAKE_PROFIT_REACHED not in codes


def test_stop_approaching_short_direction() -> None:
    """做空：止损在上方，close 在其下方 40（未击穿），atr=60 -> 接近。"""
    codes = _codes(
        _plan(direction="short", stop_price=4000.0), _ctx(3960.0, atr=60.0)
    )
    assert STOP_PRICE_APPROACHING in codes
    assert STOP_PRICE_BREACHED not in codes


def test_approaching_does_not_create_action_item(tmp_path) -> None:
    """接近预警是提醒不是待办：sync_action_items 不应为它建 EXIT 项。"""
    from lei_signal.plans.actions import sync_action_items

    conn = connect(tmp_path / "appr.db")
    plan = create_plan(
        conn, symbol="000001.SS", module="A", direction="long",
        ruleset_version="1.3.0", valid_until="2026-12-31",
        plan_kind=PLAN_KIND_HOLDING_WATCH, take_profit_plan_cn="到点减",
        stop_plan_cn="跌破走", stop_price=3700.0,
    )
    entered = confirm_holding_watch(conn, plan.plan_id, entered_on="2026-08-05")
    alerts = evaluate_plan(entered, _ctx(3740.0, atr=60.0))  # 接近止损，未击穿
    assert STOP_PRICE_APPROACHING in [a.code for a in alerts]
    sync_action_items(conn, entered, alerts)
    assert list_action_items(conn, entered.plan_id, state="open") == []
    conn.close()


def test_confirm_holding_watch_requires_exit_playbook_and_a_trigger(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "hw.db")
    base = dict(
        symbol="000001.SS", module="A", direction="long", ruleset_version="1.3.0",
        valid_until="2026-12-31", plan_kind=PLAN_KIND_HOLDING_WATCH,
    )
    # 缺两项退出预案 -> 拒绝
    p1 = create_plan(conn, **base, stop_price=3700.0)
    with pytest.raises(ValueError, match="持仓盯盘必填字段为空"):
        confirm_holding_watch(conn, p1.plan_id, entered_on="2026-08-05")
    # 有预案但三个触发条件全空 -> 拒绝
    p2 = create_plan(
        conn, **base, take_profit_plan_cn="到点减", stop_plan_cn="跌破走",
    )
    with pytest.raises(ValueError, match="至少需要一个退出触发条件"):
        confirm_holding_watch(conn, p2.plan_id, entered_on="2026-08-05")
    # 齐备 -> 直落 entered（不经 armed）
    p3 = create_plan(
        conn, **base, take_profit_plan_cn="到点减", stop_plan_cn="跌破走",
        take_profit_price=4000.0, watch_signal_rule_ids=["lei_color"],
    )
    entered = confirm_holding_watch(conn, p3.plan_id, entered_on="2026-08-05")
    assert entered.state == "entered"
    assert entered.entered_on == "2026-08-05"
    assert entered.watch_signal_rule_ids == ("lei_color",)
    conn.close()


def test_entry_plan_cannot_use_holding_watch_confirm(tmp_path) -> None:  # noqa: ANN001
    """普通入场计划不得走持仓盯盘确认（绕过五项预案）。"""
    conn = connect(tmp_path / "hw2.db")
    plan = create_plan(
        conn, symbol="000001.SS", module="A", direction="long",
        ruleset_version="1.3.0", valid_until="2026-12-31", stop_price=3700.0,
    )
    with pytest.raises(ValueError, match="只接受 plan_kind=holding_watch"):
        confirm_holding_watch(conn, plan.plan_id, entered_on="2026-08-05")
    conn.close()


def test_draft_to_entered_only_legal_for_holding_watch(tmp_path) -> None:  # noqa: ANN001
    """draft->entered 只对持仓盯盘放开。

    普通入场计划若能直接 entered，就绕过了 confirm_plan 的五项预案必填校验--
    这是必须守住的安全属性。
    """
    from lei_signal.plans.store import transition_state

    conn = connect(tmp_path / "hw4.db")
    entry = create_plan(
        conn, symbol="000001.SS", module="A", direction="long",
        ruleset_version="1.3.0", valid_until="2026-12-31",
    )
    with pytest.raises(ValueError, match="非法状态迁移"):
        transition_state(conn, entry.plan_id, "entered")

    holding = create_plan(
        conn, symbol="000001.SS", module="A", direction="long",
        ruleset_version="1.3.0", valid_until="2026-12-31",
        plan_kind=PLAN_KIND_HOLDING_WATCH, take_profit_plan_cn="减",
        stop_plan_cn="走", stop_price=3700.0,
    )
    assert transition_state(conn, holding.plan_id, "entered").state == "entered"
    conn.close()


def test_holding_watch_exit_alert_produces_exit_action_item(tmp_path) -> None:  # noqa: ANN001
    """止损击穿 -> 走既有 sync_action_items 产 EXIT 待办（复用催办/回执链路）。"""
    from lei_signal.plans.actions import sync_action_items

    conn = connect(tmp_path / "hw3.db")
    plan = create_plan(
        conn, symbol="000001.SS", module="A", direction="long",
        ruleset_version="1.3.0", valid_until="2026-12-31",
        plan_kind=PLAN_KIND_HOLDING_WATCH, take_profit_plan_cn="到点减",
        stop_plan_cn="跌破走", stop_price=3700.0,
    )
    entered = confirm_holding_watch(conn, plan.plan_id, entered_on="2026-08-05")
    alerts = evaluate_plan(entered, _ctx(3650.0))
    sync_action_items(conn, entered, alerts)
    items = list_action_items(conn, entered.plan_id, state="open")
    assert [i.kind for i in items] == ["EXIT"]
    assert items[0].source_alert_code == STOP_PRICE_BREACHED
    conn.close()
