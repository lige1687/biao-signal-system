"""入场确认过滤器测试（src/lei_signal/backtest/entry_filters.py）。"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from lei_signal.backtest.engine import EntrySpec
from lei_signal.backtest.entry_filters import (
    filter_specs_by_bias,
    filter_specs_by_gap_momentum,
    filter_specs_by_profile,
    filter_specs_by_shrink,
    filter_specs_by_volume,
)
from lei_signal.rules.gap_events import GapEvent


def _frame_with_volume_ratio(ratios: list[float]) -> pd.DataFrame:
    days = pd.bdate_range("2024-01-01", periods=len(ratios))
    return pd.DataFrame(
        {
            "open": [100.0] * len(ratios),
            "high": [101.0] * len(ratios),
            "low": [99.0] * len(ratios),
            "close": [100.0] * len(ratios),
            "volume_ratio20": ratios,
        },
        index=days,
    )


def _spec(position: int, ref_price: float = 100.0, symbol: str = "AAA") -> EntrySpec:
    frame_day = pd.Timestamp("2024-01-01") + pd.tseries.offsets.BDay(position)
    return EntrySpec(
        symbol=symbol,
        signal_date=frame_day.date(),
        signal_position=position,
        entry_ref_price=ref_price,
        stop_price=95.0,
        target_price=None,
        target_source=None,
        reward_risk=None,
        entry_variant="early",
        is_first_touch=True,
        ma_period=20,
        clock_type=2,
        weekly_bull_env=True,
        event_id=f"ev{position}",
    )


# ---------------------------------------------------------------- 量能

def test_volume_window_1_signal_day_only() -> None:
    ratios = [1.0, 1.0, 3.0, 1.0, 1.0, 1.0]
    frame = _frame_with_volume_ratio(ratios)
    # 信号日 ratio=1.0（无异常大量）-> 过滤；阈值来自账本 up_surge_ratio=2.0
    kept, dropped = filter_specs_by_volume(frame, [_spec(5)], window=1)
    assert (len(kept), dropped) == (0, 1)
    # 信号日 ratio=3.0 -> 通过
    kept, dropped = filter_specs_by_volume(frame, [_spec(2)], window=1)
    assert (len(kept), dropped) == (1, 0)


def test_volume_window_5_any_day_counts() -> None:
    ratios = [1.0, 1.0, 1.0, 1.0, 2.5, 1.0, 1.0, 1.0, 1.0, 1.0]
    frame = _frame_with_volume_ratio(ratios)
    # 信号日 position=8（ratio=1.0），但近 5 日窗口（4..8）含 position=4 的 2.5 -> 通过
    kept, dropped = filter_specs_by_volume(frame, [_spec(8)], window=5)
    assert (len(kept), dropped) == (1, 0)
    # 信号日 9：窗口 5..9 全为 1.0 -> 过滤
    kept, dropped = filter_specs_by_volume(frame, [_spec(9)], window=5)
    assert (len(kept), dropped) == (0, 1)


def test_volume_filter_rejects_bad_window_and_missing_column() -> None:
    frame = _frame_with_volume_ratio([1.0])
    with pytest.raises(ValueError, match="volume_confirm_window"):
        filter_specs_by_volume(frame, [], window=0)
    bare = frame.drop(columns=["volume_ratio20"])
    with pytest.raises(ValueError, match="volume_ratio20"):
        filter_specs_by_volume(bare, [], window=1)


# ---------------------------------------------------------------- 筹码

@dataclass
class _FakeProfile:
    poc: float = 99.0
    overhead_supply_ratio: float = 0.20


def _patch_profile(monkeypatch: pytest.MonkeyPatch, profile: _FakeProfile | None) -> None:
    monkeypatch.setattr(
        "lei_signal.backtest.entry_filters.compute_volume_profile",
        lambda bars: profile,
    )


def _prepared(frame: pd.DataFrame) -> dict:
    return {"atr20": pd.Series([2.0] * len(frame), index=frame.index)}


def test_profile_poc_support_pass_when_poc_within_1atr(monkeypatch: pytest.MonkeyPatch) -> None:
    # POC=99 在入场价 100 下方 1.0 <= 1×ATR(2.0) -> 踩峰买成立
    frame = _frame_with_volume_ratio([1.0] * 5)
    _patch_profile(monkeypatch, _FakeProfile(poc=99.0))
    kept, dropped = filter_specs_by_profile(
        frame, [_spec(4)], mode="poc_support", prepared=_prepared(frame)
    )
    assert (len(kept), dropped) == (1, 0)


def test_profile_poc_support_fail_when_poc_too_far(monkeypatch: pytest.MonkeyPatch) -> None:
    # POC=95 距入场价 5.0 > 2.0 -> 踩峰买不成立
    frame = _frame_with_volume_ratio([1.0] * 5)
    _patch_profile(monkeypatch, _FakeProfile(poc=95.0))
    kept, dropped = filter_specs_by_profile(
        frame, [_spec(4)], mode="poc_support", prepared=_prepared(frame)
    )
    assert (len(kept), dropped) == (0, 1)


def test_profile_poc_above_entry_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    # POC 在入场价上方 -> 不是「价下踩峰」
    frame = _frame_with_volume_ratio([1.0] * 5)
    _patch_profile(monkeypatch, _FakeProfile(poc=101.0))
    kept, dropped = filter_specs_by_profile(
        frame, [_spec(4)], mode="poc_support", prepared=_prepared(frame)
    )
    assert (len(kept), dropped) == (0, 1)


def test_profile_vacuum_threshold_from_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame_with_volume_ratio([1.0] * 5)
    # 账本 vacuum_overhead_max=0.30：0.30 通过、0.31 过滤
    _patch_profile(monkeypatch, _FakeProfile(overhead_supply_ratio=0.30))
    kept, _ = filter_specs_by_profile(
        frame, [_spec(4)], mode="vacuum", prepared=_prepared(frame)
    )
    assert len(kept) == 1
    _patch_profile(monkeypatch, _FakeProfile(overhead_supply_ratio=0.31))
    kept, dropped = filter_specs_by_profile(
        frame, [_spec(4)], mode="vacuum", prepared=_prepared(frame)
    )
    assert (len(kept), dropped) == (0, 1)


def test_profile_both_requires_both(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame_with_volume_ratio([1.0] * 5)
    # 踩峰成立 + 套牢超限 -> both 失败；单独 vacuum 也不成立
    _patch_profile(monkeypatch, _FakeProfile(poc=99.0, overhead_supply_ratio=0.5))
    kept, dropped = filter_specs_by_profile(
        frame, [_spec(4)], mode="both", prepared=_prepared(frame)
    )
    assert (len(kept), dropped) == (0, 1)


def test_profile_uncomputable_drops(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame_with_volume_ratio([1.0] * 5)
    _patch_profile(monkeypatch, None)  # 代理数据不可计算 -> 确认不成立
    kept, dropped = filter_specs_by_profile(
        frame, [_spec(4)], mode="vacuum", prepared=_prepared(frame)
    )
    assert (len(kept), dropped) == (0, 1)


def test_profile_cache_reuses_same_week(monkeypatch: pytest.MonkeyPatch) -> None:
    """同 (symbol, ISO周) 只算一次 profile（性能口径，账本 note 已写明）。"""
    frame = _frame_with_volume_ratio([1.0] * 5)
    calls: list[int] = []
    monkeypatch.setattr(
        "lei_signal.backtest.entry_filters.compute_volume_profile",
        lambda bars: calls.append(len(bars)) or _FakeProfile(),
    )
    cache: dict = {}
    # 同周两个信号日（周二、周三）
    specs = [_spec(1), _spec(2)]
    filter_specs_by_profile(frame, specs, mode="vacuum", prepared=_prepared(frame), cache=cache)
    assert len(calls) == 1
    assert len(cache) == 1


def test_profile_mode_validation() -> None:
    frame = _frame_with_volume_ratio([1.0] * 5)
    with pytest.raises(ValueError, match="筹码过滤档"):
        filter_specs_by_profile(frame, [], mode="none", prepared=_prepared(frame))


# ---------------------------------------------------------------- 缺口动能

def test_gap_momentum_requires_recent_unfilled_gap() -> None:
    bar_dates = [d.date() for d in pd.bdate_range("2024-01-01", periods=20)]
    unfilled = [
        GapEvent("up", bar_dates[15], 110.0, 115.0, 2.0, filled_date=None),
    ]
    filled_late = [
        GapEvent("up", bar_dates[15], 110.0, 115.0, 2.0, filled_date=bar_dates[18]),
    ]
    too_old = [
        GapEvent("up", bar_dates[2], 110.0, 115.0, 2.0, filled_date=None),
    ]
    spec_at_18 = _spec(18)
    kept, dropped = filter_specs_by_gap_momentum(
        [spec_at_18], gaps=unfilled, bar_dates=bar_dates, lookback_bars=5
    )
    assert (len(kept), dropped) == (1, 0)
    kept, dropped = filter_specs_by_gap_momentum(
        [spec_at_18], gaps=filled_late, bar_dates=bar_dates, lookback_bars=5
    )
    assert (len(kept), dropped) == (0, 1)
    kept, dropped = filter_specs_by_gap_momentum(
        [spec_at_18], gaps=too_old, bar_dates=bar_dates, lookback_bars=5
    )
    assert (len(kept), dropped) == (0, 1)


def test_gap_momentum_rejects_bad_lookback() -> None:
    with pytest.raises(ValueError, match="gap_momentum_lookback"):
        filter_specs_by_gap_momentum([], gaps=[], bar_dates=[], lookback_bars=0)


# ---------------------------------------------------------------- 缩量回调


def _frame_with_volumes(
    volumes: list[float], ratios: list[float] | None = None
) -> pd.DataFrame:
    days = pd.bdate_range("2024-01-01", periods=len(volumes))
    data: dict[str, object] = {
        "open": [100.0] * len(volumes),
        "high": [101.0] * len(volumes),
        "low": [99.0] * len(volumes),
        "close": [100.0] * len(volumes),
        "volume": volumes,
    }
    if ratios is not None:
        data["volume_ratio20"] = ratios
    return pd.DataFrame(data, index=days)


def test_shrink_keeps_when_recent_mean_below_prior() -> None:
    # 3/3：近 3 日均量 4 < 前 3 日均量 10 -> 缩量成立
    frame = _frame_with_volumes([10.0] * 6 + [4.0] * 3)
    kept, dropped = filter_specs_by_shrink(frame, [_spec(8)])
    assert (len(kept), dropped) == (1, 0)
    # 近 3 日均量 10 > 前 3 日均量 4 -> 放量，过滤
    frame = _frame_with_volumes([4.0] * 6 + [10.0] * 3)
    kept, dropped = filter_specs_by_shrink(frame, [_spec(8)])
    assert (len(kept), dropped) == (0, 1)


def test_shrink_is_strict_less_than() -> None:
    # 均量相等（10 == 10）不算缩量：严格小于
    frame = _frame_with_volumes([10.0] * 9)
    kept, dropped = filter_specs_by_shrink(frame, [_spec(8)])
    assert (len(kept), dropped) == (0, 1)


def test_shrink_warmup_nan_drops() -> None:
    # position=3：前段窗口需 v[-2..0]（越界 NaN）-> 判 False
    frame = _frame_with_volumes([5.0, 5.0, 5.0, 1.0])
    kept, dropped = filter_specs_by_shrink(frame, [_spec(3)])
    assert (len(kept), dropped) == (0, 1)


def test_shrink_window_variants() -> None:
    volumes = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 2.0]
    frame = _frame_with_volumes(volumes)
    # 5/3（p=7）：近5 = mean(v[3..7]) = 8.4 < 前3 = mean(v[0..2]) = 10
    kept, _ = filter_specs_by_shrink(
        frame, [_spec(7)], recent_window=5, prior_window=3
    )
    assert len(kept) == 1
    # 2/5（p=7）：近2 = mean(v[6..7]) = 6 < 前5 = mean(v[2..6]) = 10
    kept, _ = filter_specs_by_shrink(
        frame, [_spec(7)], recent_window=2, prior_window=5
    )
    assert len(kept) == 1
    # 2/5 反例（p=7）：近2 = mean(1,10) = 5.5 > 前5 = 1 -> 过滤
    frame = _frame_with_volumes([1.0] * 7 + [10.0])
    kept, dropped = filter_specs_by_shrink(
        frame, [_spec(7)], recent_window=2, prior_window=5
    )
    assert (len(kept), dropped) == (0, 1)


def test_shrink_vr_max_strict_less_and_nan() -> None:
    # 缩量成立（近3=4 < 前3=10），信号日量比 0.69 < 0.7 -> 通过
    frame = _frame_with_volumes([10.0] * 6 + [4.0] * 3, ratios=[1.0] * 8 + [0.69])
    kept, dropped = filter_specs_by_shrink(frame, [_spec(8)], vr_max=0.7)
    assert (len(kept), dropped) == (1, 0)
    # 量比恰为 0.7：严格 < 不成立 -> 过滤
    frame = _frame_with_volumes([10.0] * 6 + [4.0] * 3, ratios=[1.0] * 8 + [0.70])
    kept, dropped = filter_specs_by_shrink(frame, [_spec(8)], vr_max=0.7)
    assert (len(kept), dropped) == (0, 1)
    # 量比 NaN -> 过滤
    frame = _frame_with_volumes([10.0] * 6 + [4.0] * 3, ratios=[1.0] * 8 + [float("nan")])
    kept, dropped = filter_specs_by_shrink(frame, [_spec(8)], vr_max=0.7)
    assert (len(kept), dropped) == (0, 1)


def test_shrink_default_windows_from_ledger_are_3_3() -> None:
    # 不传窗口 -> 账本 shrink_recent_window/shrink_prior_window（=3/3），
    # 行为应与显式 3/3 完全一致
    volumes = [10.0] * 6 + [4.0] * 3
    frame = _frame_with_volumes(volumes)
    kept_default, _ = filter_specs_by_shrink(frame, [_spec(8)])
    kept_explicit, _ = filter_specs_by_shrink(
        frame, [_spec(8)], recent_window=3, prior_window=3
    )
    assert len(kept_default) == len(kept_explicit) == 1


def test_shrink_rejects_bad_params_and_missing_column() -> None:
    frame = _frame_with_volumes([1.0, 2.0])
    with pytest.raises(ValueError, match="缩量窗口"):
        filter_specs_by_shrink(frame, [], recent_window=0)
    with pytest.raises(ValueError, match="volume_filter_vr_max"):
        filter_specs_by_shrink(frame, [], vr_max=0.0)
    with pytest.raises(ValueError, match="volume_ratio20"):
        filter_specs_by_shrink(frame, [], vr_max=0.7)


# ---------------------------------------------------------------- 深乖离增强


def _frame_with_bias(closes: list[float], ema120: list[float]) -> pd.DataFrame:
    days = pd.bdate_range("2024-01-01", periods=len(closes))
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [1e6] * len(closes),
            "ema120": ema120,
        },
        index=days,
    )


def test_bias_keeps_only_deeply_oversold() -> None:
    # close=85, ema120=100 -> bias=-15%；-15% 档（<=）通过、-25% 档过滤
    frame = _frame_with_bias([85.0], [100.0])
    kept, dropped = filter_specs_by_bias(frame, [_spec(0)], bias_max=-0.15)
    assert (len(kept), dropped) == (1, 0)
    kept, dropped = filter_specs_by_bias(frame, [_spec(0)], bias_max=-0.25)
    assert (len(kept), dropped) == (0, 1)


def test_bias_boundary_is_inclusive() -> None:
    # bias 恰等于档位（-0.25）-> 通过（<= 语义）
    frame = _frame_with_bias([75.0], [100.0])
    kept, _ = filter_specs_by_bias(frame, [_spec(0)], bias_max=-0.25)
    assert len(kept) == 1


def test_bias_rejects_positive_threshold_and_missing_column() -> None:
    frame = _frame_with_bias([85.0], [100.0])
    with pytest.raises(ValueError, match="bias_max"):
        filter_specs_by_bias(frame, [], bias_max=0.0)
    with pytest.raises(ValueError, match="ema120"):
        filter_specs_by_bias(frame.drop(columns=["ema120"]), [], bias_max=-0.15)


def test_bias_warmup_nan_drops() -> None:
    # ema120=NaN -> bias NaN -> 判 False（不通过）
    frame = _frame_with_bias([85.0], [float("nan")])
    kept, dropped = filter_specs_by_bias(frame, [_spec(0)], bias_max=-0.15)
    assert (len(kept), dropped) == (0, 1)
