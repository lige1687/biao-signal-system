"""Synthetic execution outcomes must be reported with their actual holding state."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pandas as pd
import pytest

from lei_signal.backtest import engine, metrics


def _frame(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["open", "high", "low", "close"],
        index=pd.date_range("2024-01-01", periods=len(rows)),
    )


def _simulate(frame: pd.DataFrame, position: int = 0, *,
              symbol: str = "TEST", guard: bool = False) -> engine.Trade:
    spec = engine.EntrySpec(
        symbol=symbol, signal_date=frame.index[position].date(),
        signal_position=position, entry_ref_price=10, stop_price=9,
        target_price=14, target_source="synthetic", reward_risk=4,
        entry_variant="early", is_first_touch=True, ma_period=20,
        clock_type=2, weekly_bull_env=True, event_id="reporting-regression",
    )
    return engine.simulate_trade(
        frame, spec, exit_variant=engine.EXIT_STRUCTURE_STOP,
        fee=engine.FeeModel("none", 0.0, 0.0), limit_guard=guard,
        prepared={"costbasis_cond": pd.Series(False, index=frame.index),
                  "top_structures": []},
    )


@pytest.fixture
def executions() -> dict[str, engine.Trade]:
    normal = (10, 10.5, 9.5, 10)
    frame = _frame([normal] * 3)
    return {
        "open": _simulate(frame),
        "pending_entry": _simulate(frame, position=2),
        "invalid": _simulate(_frame([normal, (8, 8.5, 7.5, 8), (8, 8.5, 7.5, 8)])),
        "skipped": _simulate(_frame([normal, (11, 11.5, 10.5, 11),
                                     (11, 11.5, 10.5, 11)]),
                             symbol="600001.SS", guard=True),
        "closed": _simulate(_frame([normal, (10, 10.5, 8, 8.5),
                                    (12, 12.5, 11.5, 12)])),
    }


@pytest.mark.parametrize(("state", "reason", "open_count", "closed_count"), [
    ("open", "open_at_end", 1, 0),
    ("pending_entry", "signal_at_end_not_entered", 0, 0),
    ("invalid", "invalid_nonpositive_risk", 0, 0),
    ("skipped", "skipped_limit_up_at_entry", 0, 0),
    ("closed", "structure_stop_C", 0, 1),
])
def test_execution_state_counts(executions, state, reason, open_count, closed_count):
    trade = executions[state]
    assert trade.exit_reason == reason
    result = metrics.compute_metrics([trade])
    assert result.open_count == open_count
    assert result.trade_count == closed_count


def test_mixed_states_preserve_closed_trade_statistics(executions):
    result = metrics.compute_metrics(list(executions.values()))
    assert (result.open_count, result.trade_count) == (1, 1)
    assert result.total_r == pytest.approx(2)
    assert result.win_rate == 1
    assert result.avg_holding_bars == 1


def _restricted_frame() -> pd.DataFrame:
    return _frame([
        (10, 10.5, 9.5, 10), (10, 10.5, 8, 8.5),
        (7.6, 8, 7.4, 7.5), (6.7, 7, 6.5, 6.8), (6.1, 6.3, 5.9, 6.2),
    ])


def test_blocked_exit_counts_holding_through_last_observed_bar():
    trade = _simulate(_restricted_frame(), symbol="600001.SS", guard=True)
    assert trade.exit_reason == "structure_stop_C(数据末尾未执行)"
    assert trade.is_open
    assert trade.holding_bars == 3
    assert trade.exit_date is None
    assert trade.r_net is None and trade.r_gross is None
    assert metrics.compute_metrics([trade]).open_count == 1


def test_final_bar_exit_signal_remains_open():
    trade = _simulate(_frame([(10, 10.5, 9.5, 10)] * 2 + [(10, 10.5, 8, 8.5)]))
    assert trade.is_open
    assert trade.holding_bars == 1
    assert trade.exit_reason == "structure_stop_C(数据末尾未执行)"


def test_later_executable_exit_keeps_actual_execution_and_profit():
    frame = _restricted_frame()
    frame.loc[frame.index[-1], "open"] = 6.3
    trade = _simulate(frame, symbol="600001.SS", guard=True)
    assert trade.exit_date == date(2024, 1, 5)
    assert trade.exit_price == 6.3
    assert trade.holding_bars == 3
    assert trade.r_net == pytest.approx(-3.7)
    assert trade.r_gross == pytest.approx(-3.7)


def test_split_labels_match_unchanged_membership(executions):
    split = date(2024, 1, 2)
    trades = [replace(executions["closed"], signal_date=split + timedelta(days=offset))
              for offset in (-1, 0, 1)]
    groups = metrics.full_group_metrics(trades, net=True, sample_split=split)["样本内外"]
    assert [group.trade_count for group in groups] == [1, 2]
    assert [group.total_r for group in groups] == pytest.approx([2, 4])
    assert [group.label for group in groups] == ["样本内（< 切分日）", "样本外（>= 切分日）"]
