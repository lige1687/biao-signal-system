from __future__ import annotations

import importlib.util
import os
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
ELEVENTH = HERE.parents[1] / "research-eleventh-2026-09-08" / "research-package"
ENGINE_PATH = Path(os.environ.get("ENGINE_UNDER_TEST", ELEVENTH / "src/lei_signal/backtest/engine.py"))
sys.path.insert(0, str(ELEVENTH / "src"))


def _load_engine():
    spec = importlib.util.spec_from_file_location("consumer_audit_engine", ENGINE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


engine = _load_engine()


def _frame(keywave_days: set[int]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=10, freq="D")
    close = [90.0 if i in keywave_days else 110.0 for i in range(10)]
    return pd.DataFrame(
        {
            "open": [110.0] * 10,
            "high": [111.0] * 10,
            "low": [89.0] * 10,
            "close": close,
            "volume": [1000.0] * 10,
            "ema20": [100.0] * 10,
            "close_lag20": [100.0] * 10,
            "sma20": [100.0] * 10,
            "sma60": [99.0] * 10,
        },
        index=index,
    )


def _top(frame: pd.DataFrame, confirmed: int, invalidated: int | None):
    return SimpleNamespace(
        side=engine.SIDE_TOP,
        confirmed_date=frame.index[confirmed].date(),
        invalidated_date=(frame.index[invalidated].date() if invalidated is not None else None),
    )


def _trade(monkeypatch: pytest.MonkeyPatch, tops: list, keywave_days: set[int]):
    frame = _frame(keywave_days)
    monkeypatch.setattr(engine, "detect_strict_structures", lambda _: tops)
    prepared = engine.prepare_frame(frame)
    spec = engine.EntrySpec(
        symbol="TEST", signal_date=frame.index[0].date(), signal_position=0,
        entry_ref_price=110.0, stop_price=80.0, target_price=200.0,
        target_source="fixture", reward_risk=3.0, entry_variant="early",
        is_first_touch=True, ma_period=20, clock_type=2, weekly_bull_env=True,
        event_id="fixture",
    )
    return engine.simulate_trade(
        frame, spec, exit_variant=engine.EXIT_TOP_PLUS_KEYWAVE,
        fee=engine.FeeModel("none", 0.0, 0.0), prepared=prepared,
    )


def test_valid_top_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 2, None)], {4})
    assert trade.exit_reason == "exit_a6_2_top_plus_keywave"
    assert trade.exit_date == frame.index[5].date()


def test_previously_invalidated_top_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 2, 3)], {4})
    assert trade.exit_reason == "open_at_end"


def test_top_invalidated_on_keywave_day_does_not_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 2, 4)], {4})
    assert trade.exit_reason == "open_at_end"


def test_future_invalidation_does_not_erase_past_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 2, 7)], {4})
    assert trade.exit_reason == "exit_a6_2_top_plus_keywave"
    assert trade.exit_date == frame.index[5].date()


def test_pre_entry_top_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 0, None)], {4})
    assert trade.exit_reason == "open_at_end"


def test_entry_day_close_top_can_trigger_later(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 1, None)], {4})
    assert trade.exit_reason == "exit_a6_2_top_plus_keywave"


def test_new_top_after_old_invalidation_can_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({5})
    tops = [_top(frame, 2, 3), _top(frame, 4, None)]
    trade = _trade(monkeypatch, tops, {5})
    assert trade.exit_reason == "exit_a6_2_top_plus_keywave"
    assert trade.exit_date == frame.index[6].date()


def test_existing_same_day_confirmation_behavior_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame({4})
    trade = _trade(monkeypatch, [_top(frame, 4, None)], {4})
    assert trade.exit_reason == "exit_a6_2_top_plus_keywave"
