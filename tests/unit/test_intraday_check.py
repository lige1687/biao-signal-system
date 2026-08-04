"""盘中快照判定门禁：虚拟今日 bar + actionable 过滤 + 只读不写 DB。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd

from lei_signal.api.quotes import QuoteSnapshot
from lei_signal.plans.models import PLAN_ARMED, TradePlan
from lei_signal.plans.monitor import (
    ENTRY_CONDITIONS_MET,
    ENTRY_RR_BELOW_IDEAL,
    INVALIDATION_BREACHED,
    MonitorContext,
    OpportunityRef,
    evaluate_plan,
)
from lei_signal.storage.sqlite_store import connect

RULESET = "1.3.0"


def _plan(**kw) -> TradePlan:
    d = dict(
        plan_id="p1", symbol="600519.SS", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="站回 SMA20", entry_price_ref=1300.0,
        invalidation_price=1250.0, target_b_price=1450.0, target_b_source="swing_high",
        reward_risk_at_plan=3.5, valid_until="2026-12-31", state=PLAN_ARMED,
        ruleset_version=RULESET, reason="x", thesis_cn="t", invalidation_criteria_cn="i",
        drawdown_playbook_cn="d", take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    d.update(kw)
    return TradePlan(**d)


def test_actionable_filter_only_block_remind() -> None:
    """只推 block/remind 且（有 action_kind 或失效价击穿）的 alert；hint 级不推。"""
    from scripts.intraday_check import _filter_actionable

    ctx = MonitorContext(
        last_bar_date="2026-08-04", cache_fallback_used=False, current_close=1240.0,
        ema20=1300.0, tradability_tradable=True, ruleset_version=RULESET,
        opportunities=(
            OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 1.5, True, "long"),
        ),
    )
    alerts = evaluate_plan(_plan(invalidation_price=1250.0), ctx)
    codes = [a.code for a in alerts]
    assert INVALIDATION_BREACHED in codes
    assert ENTRY_CONDITIONS_MET in codes
    assert ENTRY_RR_BELOW_IDEAL in codes

    actionable = _filter_actionable(alerts)
    actionable_codes = [a.code for a in actionable]
    # INVALIDATION_BREACHED 是 block，armed 时 action_kind=None 但仍推（计划失效信号）
    assert INVALIDATION_BREACHED in actionable_codes
    # ENTRY_CONDITIONS_MET 是 remind + action_kind=ENTER -> 推
    assert ENTRY_CONDITIONS_MET in actionable_codes
    # ENTRY_RR_BELOW_IDEAL 是 hint -> 不推
    assert ENTRY_RR_BELOW_IDEAL not in actionable_codes


def test_no_actionable_means_no_push(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """没有 actionable alert 时不推送。"""
    from scripts.intraday_check import run_intraday_check

    # 建一条 armed 计划，但 ctx 里没有匹配的机会 -> 只有 hint 级 alert
    conn = connect(tmp_path / "intraday.db")
    from lei_signal.plans.store import confirm_plan, create_plan
    plan = create_plan(
        conn, symbol="600519.SS", module="A", direction="long", ruleset_version=RULESET,
        reason="x", valid_until="2026-12-31", entry_rule_id="first_ma_pullback",
        entry_lifecycle_id="ghost", entry_trigger_cn="t", entry_price_ref=1300.0,
        invalidation_price=1000.0, target_b_price=1450.0, target_b_source="swing_high",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    confirm_plan(conn, plan.plan_id)
    conn.close()

    # mock 取数：返回 fixture bars + 盘中价（不会触发 INVALIDATION_BREACHED）
    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet")).iloc[-30:]
    quote = QuoteSnapshot(symbol="600519.SS", price=99999.0, open=99999.0,
                          high=99999.0, low=99999.0)

    pushed = [0]
    original_notify = None

    def fake_notify(title, body, *, dry_run=False):
        pushed[0] += 1

    with patch("scripts.intraday_check.default_provider") as mock_provider, \
         patch("scripts.intraday_check.TencentQuoteProvider") as mock_qp, \
         patch("scripts.intraday_check.analyze_bars") as mock_analyze, \
         patch("scripts.intraday_check._notify", fake_notify):
        mock_provider.return_value.fetch.return_value.bars = bars
        mock_qp.return_value.fetch.return_value = quote
        # 让 analyze_bars 返回一个不会触发 actionable 的结果
        # 用真实 analyze_bars 但 mock ctx
        from lei_signal.compose.pipeline import analyze_bars as real_analyze
        mock_analyze.side_effect = lambda sym, b: real_analyze(sym, b)

        n = run_intraday_check(["600519.SS"], db_path=str(tmp_path / "intraday.db"),
                               dry_run=True)
    # invalidation_price=1000 远低于 fixture 价格 -> 不会 INVALIDATION_BREACHED
    # lifecycle=ghost 不在 DTO -> PLAN_ORPHANED(hint) -> 不推
    assert n == 0, "无 actionable 时不应推送"


def test_intraday_does_not_write_db(tmp_path) -> None:  # noqa: ANN001
    """盘中检查只读判定，不碰 DB（不同步待办、不催办）。"""
    from scripts.intraday_check import run_intraday_check

    conn = connect(tmp_path / "readonly.db")
    from lei_signal.plans.store import confirm_plan, create_plan, list_action_items
    plan = create_plan(
        conn, symbol="600519.SS", module="A", direction="long", ruleset_version=RULESET,
        reason="x", valid_until="2026-12-31", entry_rule_id="first_ma_pullback",
        entry_lifecycle_id="lc1", entry_trigger_cn="t", entry_price_ref=1300.0,
        invalidation_price=99999.0,  # 故意设很高，让 INVALIDATION_BREACHED 触发
        target_b_price=1450.0, target_b_source="swing_high",
        thesis_cn="t", invalidation_criteria_cn="i", drawdown_playbook_cn="d",
        take_profit_plan_cn="tp", stop_plan_cn="s",
    )
    confirm_plan(conn, plan.plan_id)
    items_before = list_action_items(conn, plan.plan_id)
    conn.close()

    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet")).iloc[-30:]
    quote = QuoteSnapshot(symbol="600519.SS", price=3820.0, open=3800.0,
                          high=3830.0, low=3790.0)
    with patch("scripts.intraday_check.default_provider") as mock_provider, \
         patch("scripts.intraday_check.TencentQuoteProvider") as mock_qp:
        mock_provider.return_value.fetch.return_value.bars = bars
        mock_qp.return_value.fetch.return_value = quote
        run_intraday_check(["600519.SS"], db_path=str(tmp_path / "readonly.db"),
                           dry_run=True)

    conn2 = connect(tmp_path / "readonly.db")
    items_after = list_action_items(conn2, plan.plan_id)
    conn2.close()
    # DB 里的待办数量不变（盘中检查不写 DB）
    assert len(items_after) == len(items_before), "盘中检查不得写 DB"
