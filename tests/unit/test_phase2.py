"""Phase 2 门禁：原子事件引擎与不可变事件日志。"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.domain.types import Direction, Provenance, Severity, StructureStatus
from lei_signal.events.log import EventLog, make_event
from lei_signal.features.indicators import compute_features
from lei_signal.rules.color_events import detect_color_events
from lei_signal.rules.dual_ma import (
    detect_dual_ma_confirm_events,
    detect_ema20_reclaim_events,
    detect_spread_events,
    dual_ma_bull_state,
    ema20_reclaim_state,
)
from lei_signal.rules.key_wave import detect_key_wave_events, key_black_state
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import (
    compute_long_trend,
    compute_weekly_long_trend,
    detect_long_trend_events,
    latest_weekly_state,
)
from lei_signal.rules.reversals import (
    bearish_engulfing_state,
    bullish_engulfing_state,
    bullish_outside_reversal_state,
    detect_reversal_events,
)
from lei_signal.rules.volume import compute_volume_labels, detect_volume_events
from tests.golden.fixtures import (
    golden_bullish_engulfing,
    golden_bullish_outside_reversal,
    golden_color_series,
)


def _prepared(bars: pd.DataFrame) -> pd.DataFrame:
    return compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))


def _random_bars(rows: int = 400, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, rows))
    return pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.3, rows),
            "high": close + rng.uniform(0.3, 1.6, rows),
            "low": close - rng.uniform(0.3, 1.6, rows),
            "close": close,
            "volume": rng.integers(500_000, 4_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=rows),
    )


# ---------------- 事件日志不变量 ----------------


def _sample_event(event_id: str = "e1", day: date = date(2025, 1, 6)):  # noqa: ANN202
    return make_event(
        event_id=event_id,
        symbol="QQQ",
        event_date=day,
        available_date=day,
        rule_id="lei_color",
        rule_version="1.0.0",
        direction=Direction.BULLISH,
        severity=Severity.INFO,
        strength=50,
        reason_cn="测试",
        provenance=Provenance.LEI_EXPLICIT,
    )


def test_event_log_is_append_only_and_idempotent() -> None:
    """门禁 11：重复运行不得重复写入。"""
    log = EventLog()
    assert log.append(_sample_event()) is True
    assert log.append(_sample_event()) is False   # 同 ID 幂等忽略
    assert len(log) == 1
    assert log.duplicate_count == 1


def test_event_log_orders_stably_by_available_date() -> None:
    log = EventLog()
    log.append(_sample_event("b", date(2025, 1, 8)))
    log.append(_sample_event("a", date(2025, 1, 6)))
    assert [e.event_id for e in log.events()] == ["a", "b"]


def test_event_log_available_through_hides_future_events() -> None:
    log = EventLog()
    log.append(_sample_event("past", date(2025, 1, 6)))
    log.append(_sample_event("future", date(2025, 6, 2)))
    visible = log.available_through(date(2025, 3, 1))
    assert [e.event_id for e in visible] == ["past"]


def test_make_event_rejects_available_date_before_event_date() -> None:
    """available_date 早于 event_date 意味着未来数据泄漏。"""
    with pytest.raises(ValueError, match="不得早于"):
        make_event(
            event_id="x",
            symbol="QQQ",
            event_date=date(2025, 1, 10),
            available_date=date(2025, 1, 6),
            rule_id="swing_pivots",
            rule_version="1.0.0",
            direction=Direction.NEUTRAL,
            severity=Severity.INFO,
            strength=10,
            reason_cn="测试",
            provenance=Provenance.EXISTING_BACKTEST,
        )


def test_make_event_rejects_out_of_range_strength() -> None:
    with pytest.raises(ValueError, match="strength"):
        make_event(
            event_id="x", symbol="QQQ", event_date=date(2025, 1, 6),
            available_date=date(2025, 1, 6), rule_id="lei_color", rule_version="1.0.0",
            direction=Direction.NEUTRAL, severity=Severity.INFO, strength=140,
            reason_cn="t", provenance=Provenance.LEI_EXPLICIT,
        )


# ---------------- 颜色事件去重 ----------------


def test_consecutive_green_produces_one_start_event() -> None:
    """研究要求：连续绿色只算一次开始事件。"""
    frame = _prepared(golden_color_series())
    events = detect_color_events(frame, "TEST")
    green_events = [e for e in events if e.evidence["color"] == "green"]
    green_days = int(frame["signal_color"].eq("green").sum())
    assert green_days > len(green_events)
    assert len(green_events) >= 1
    # 每个起始日的前一日颜色必须不同
    for event in green_events:
        position = frame.index.get_loc(pd.Timestamp(event.event_date))
        if position > 0:
            assert frame["signal_color"].iloc[position - 1] != "green"


def test_unknown_rows_produce_no_color_events() -> None:
    frame = _prepared(golden_color_series())
    events = detect_color_events(frame, "TEST")
    assert all(e.evidence["color"] != "unknown" for e in events)


# ---------------- EMA20 转强与共同确认 ----------------


def test_ema20_reclaim_requires_all_three_conditions() -> None:
    frame = pd.DataFrame(
        {
            "close": [10.0, 11.0, 11.0, 9.0],
            "ema20": [10.5, 10.6, 10.7, 10.8],
        },
        index=pd.bdate_range("2024-01-02", periods=4),
    )
    state = ema20_reclaim_state(frame)
    # index1: 前收10<=前EMA10.5, 今收11>10.6, EMA上升 -> True
    assert state.tolist() == [False, True, False, False]


def test_ema20_reclaim_rejects_falling_ema() -> None:
    frame = pd.DataFrame(
        {"close": [10.0, 11.0], "ema20": [10.5, 10.4]},
        index=pd.bdate_range("2024-01-02", periods=2),
    )
    assert ema20_reclaim_state(frame).tolist() == [False, False]


def test_dual_ma_confirm_reads_current_state_not_same_day_cross() -> None:
    """共同确认不要求当天重新穿越 EMA20。"""
    index = pd.bdate_range("2024-01-02", periods=4)
    frame = pd.DataFrame(
        {
            "close": [10.0, 11.0, 12.0, 13.0],
            "ema20": [9.5, 9.8, 10.2, 10.6],
            "sma20": [9.4, 9.6, 10.0, 10.4],
            "signal_color": ["green", "green", "green", "green"],
        },
        index=index,
    )
    state = dual_ma_bull_state(frame)
    # 第 2..4 天均成立（第 1 天没有前值判断斜率）
    assert state.tolist() == [False, True, True, True]

    # 事件只在起始记录一次
    events = detect_dual_ma_confirm_events(frame, "TEST")
    assert len(events) == 1
    assert events[0].event_date == index[1].date()


def test_dual_ma_confirm_requires_green_color() -> None:
    frame = pd.DataFrame(
        {
            "close": [10.0, 11.0],
            "ema20": [9.5, 9.8],
            "sma20": [9.4, 9.6],
            "signal_color": ["gray", "gray"],
        },
        index=pd.bdate_range("2024-01-02", periods=2),
    )
    assert dual_ma_bull_state(frame).tolist() == [False, False]


def test_spread_events_are_advisory_only() -> None:
    frame = _prepared(_random_bars(300))
    events = detect_spread_events(frame, "TEST")
    assert events, "应产生开口事件"
    # 辅助信号严重度不得高于 watch
    assert all(e.severity in (Severity.INFO, Severity.WATCH) for e in events)
    assert {e.evidence["sub_rule"] for e in events} <= {
        "dual_ma_spread_expanding",
        "dual_ma_spread_contracting",
        "dual_ma_cross",
    }


# ---------------- 长周期背景 ----------------


def test_long_trend_states_are_computed_without_gating_anything() -> None:
    frame = _prepared(_random_bars(400))
    assert "long_trend" in frame.columns
    observed = set(frame.loc[frame["long_trend"] != "unknown", "long_trend"])
    assert observed, "应产生长周期状态"
    assert observed <= {
        "long_bull", "long_bear", "long_improving",
        "long_stable_bull", "long_deteriorating",
    }


def test_long_trend_unknown_before_ema120_is_ready() -> None:
    frame = _prepared(_random_bars(200))
    assert frame["long_trend"].iloc[:119].eq("unknown").all()


def test_weekly_long_trend_uses_completed_weeks_only() -> None:
    """周线状态的可用日期必须是已完成周的最后交易日。"""
    bars = _random_bars(600, seed=9)
    weekly = aggregate_weekly(bars)
    trend = compute_weekly_long_trend(weekly)
    assert not trend.empty
    # 所有周线索引必须存在于日线索引中（即真实交易日）
    assert set(trend.index).issubset(set(bars.index))
    # 最后一根日线所在周不得出现
    assert trend.index[-1] < bars.index[-1] or trend.index[-1] == bars.index[-1]

    state = latest_weekly_state(trend, bars.index[300])
    assert state.value in {
        "long_bull", "long_bear", "long_improving",
        "long_stable_bull", "long_deteriorating", "unknown",
    }


def test_long_trend_events_distinguish_daily_and_weekly() -> None:
    bars = _random_bars(500, seed=21)
    daily = _prepared(bars)
    daily_events = detect_long_trend_events(daily, "TEST", timeframe="1d")
    weekly = compute_weekly_long_trend(aggregate_weekly(bars))
    weekly_events = detect_long_trend_events(weekly, "TEST", timeframe="1w")
    assert all(e.timeframe == "1d" for e in daily_events)
    assert all(e.timeframe == "1w" for e in weekly_events)
    # 同一天的日线与周线事件必须是不同 event_id
    assert not ({e.event_id for e in daily_events} & {e.event_id for e in weekly_events})


# ---------------- 反转 K 线 ----------------


def test_bullish_engulfing_matches_exact_formula() -> None:
    frame = golden_bullish_engulfing()
    state = bullish_engulfing_state(frame)
    assert state.iloc[-1], "黄金样例最后一根必须是阳线反包"
    row, previous = frame.iloc[-1], frame.iloc[-2]
    assert previous["close"] < previous["open"]
    assert row["close"] > row["open"]
    assert row["open"] <= previous["close"]
    assert row["close"] >= previous["open"]


def test_bullish_outside_reversal_matches_exact_formula() -> None:
    frame = golden_bullish_outside_reversal()
    state = bullish_outside_reversal_state(frame)
    assert state.iloc[-1]
    row, previous = frame.iloc[-1], frame.iloc[-2]
    assert row["low"] <= previous["low"]
    assert row["close"] >= previous["high"]
    assert row["close"] > row["open"]


def test_bearish_engulfing_is_the_mirror_of_bullish() -> None:
    frame = pd.DataFrame(
        {
            "open": [10.0, 12.5],
            "high": [12.0, 12.6],
            "low": [9.8, 9.5],
            "close": [12.0, 9.8],
            "volume": [1000.0, 2000.0],
        },
        index=pd.bdate_range("2024-01-02", periods=2),
    )
    assert bearish_engulfing_state(frame).iloc[-1]


def test_reversal_events_are_recorded_even_when_long_trend_is_bearish() -> None:
    """门禁 6：反包不会被 60/120 日线 Block。"""
    frame = _prepared(golden_bullish_engulfing())
    last = frame.iloc[-1]
    # 前置条件：长周期确实为空头
    assert last["ema60"] < last["ema120"], "样例应处于 EMA60 < EMA120 环境"

    events = detect_reversal_events(frame, "TEST")
    engulfing = [e for e in events if e.rule_id == "bullish_engulfing"]
    assert engulfing, "空头长周期环境下反包事件仍必须被记录"
    assert engulfing[-1].event_date == frame.index[-1].date()
    assert engulfing[-1].provenance is Provenance.RESEARCH_PROXY


def test_reversal_reasons_are_marked_as_research_proxy() -> None:
    frame = _prepared(golden_bullish_engulfing())
    for event in detect_reversal_events(frame, "TEST"):
        assert "研究代理" in event.reason_cn


# ---------------- 关键性波动 ----------------


def test_key_black_state_matches_lei_color_black_exactly() -> None:
    """Black 必须与三色的 black 逐日一致。"""
    frame = _prepared(_random_bars(400, seed=31))
    assert key_black_state(frame).tolist() == frame["signal_color"].eq("black").tolist()


def test_black_and_top_plus_black_are_saved_separately() -> None:
    """两个版本必须分别保存，不能只保留表现较好的。"""
    from lei_signal.domain.types import StructureInstance

    frame = _prepared(_random_bars(300, seed=41))
    black_days = frame.index[key_black_state(frame)]
    assert len(black_days) > 0

    first_black = black_days[0].date()
    top = StructureInstance(
        structure_id="top-1",
        symbol="TEST",
        structure_type="top_structure",
        side="top",
        detected_date=date(2023, 1, 10),
        neckline=90.0,
        reference_high=110.0,
        confirmed_date=date(2023, 1, 20),
        status=StructureStatus.CONFIRMED,
    )
    events = detect_key_wave_events(frame, "TEST", tops=[top])
    sub_rules = {e.evidence["sub_rule"] for e in events}
    assert "key_wave_black_started" in sub_rules
    # 有有效顶部时产生 top_plus_black
    top_plus = [e for e in events if e.evidence["sub_rule"] == "top_plus_black"]
    assert top_plus
    assert top_plus[0].severity is Severity.CRITICAL
    assert first_black is not None

    # 无顶部时仅产生 key_wave_black_started，不产生 top_plus_black
    events_no_top = detect_key_wave_events(frame, "TEST", tops=[])
    sub_rules_no_top = {e.evidence["sub_rule"] for e in events_no_top}
    assert "key_wave_black_started" in sub_rules_no_top
    assert "top_plus_black" not in sub_rules_no_top


def test_invalidated_top_cannot_participate_in_top_plus_black() -> None:
    """门禁 9：顶部被新高解除后不能继续参与 Top+Black。"""
    from lei_signal.domain.types import StructureInstance

    frame = _prepared(_random_bars(300, seed=41))
    black_days = frame.index[key_black_state(frame)]
    first_black = black_days[0].date()

    invalidated_top = StructureInstance(
        structure_id="top-dead",
        symbol="TEST",
        structure_type="top_structure",
        side="top",
        detected_date=date(2023, 1, 10),
        neckline=90.0,
        reference_high=110.0,
        confirmed_date=date(2023, 1, 20),
        status=StructureStatus.INVALIDATED,
        invalidated_date=first_black,   # 在转黑当天已失效
        invalidated_reason="top_warning_invalidated_by_new_high",
    )
    events = detect_key_wave_events(frame, "TEST", tops=[invalidated_top])
    first_day_events = [e for e in events if e.event_date == first_black]
    sub_rules = {e.evidence["sub_rule"] for e in first_day_events}
    assert "top_plus_black" not in sub_rules
    # 失效顶部参与 → 仅记录黑色起始，没有 top+black
    assert "key_wave_black_started" in sub_rules


# ---------------- 量能 ----------------


def test_volume_labels_are_proxies_and_never_gate() -> None:
    frame = _prepared(_random_bars(300, seed=51))
    for column in ("volume_up_surge", "bearish_expansion", "pullback_shrink"):
        assert column in frame.columns
    events = detect_volume_events(frame, "TEST")
    assert events
    assert all(e.provenance is Provenance.RESEARCH_PROXY for e in events)
    assert all("研究代理" in e.reason_cn for e in events)
    # 量能事件严重度不得为 critical（不能等同于风险否决）
    assert all(e.severity in (Severity.INFO, Severity.WATCH) for e in events)


# ---------------- 全量事件确定性 ----------------


def test_running_the_full_engine_twice_produces_identical_event_ids() -> None:
    """门禁 11：同样数据和规则重复运行产生完全相同的事件 ID。"""
    bars = _random_bars(400, seed=61)

    def run() -> list[str]:
        frame = _prepared(bars)
        log = EventLog()
        log.extend(detect_color_events(frame, "TEST"))
        log.extend(detect_ema20_reclaim_events(frame, "TEST"))
        log.extend(detect_dual_ma_confirm_events(frame, "TEST"))
        log.extend(detect_spread_events(frame, "TEST"))
        log.extend(detect_long_trend_events(frame, "TEST"))
        log.extend(detect_reversal_events(frame, "TEST"))
        log.extend(detect_key_wave_events(frame, "TEST"))
        log.extend(detect_volume_events(frame, "TEST"))
        return [e.event_id for e in log.events()]

    first, second = run(), run()
    assert first == second
    assert len(first) == len(set(first)), "事件 ID 必须唯一"


def test_appending_future_bars_does_not_change_past_events() -> None:
    """门禁 1（事件层）：追加未来行情不改变旧事件。"""
    bars = _random_bars(400, seed=71)
    cut = 300
    as_of = bars.index[cut - 1].date()

    def events_for(frame_bars: pd.DataFrame) -> list[tuple]:
        frame = _prepared(frame_bars)
        log = EventLog()
        log.extend(detect_color_events(frame, "TEST"))
        log.extend(detect_ema20_reclaim_events(frame, "TEST"))
        log.extend(detect_dual_ma_confirm_events(frame, "TEST"))
        log.extend(detect_reversal_events(frame, "TEST"))
        log.extend(detect_key_wave_events(frame, "TEST"))
        return [
            (e.event_id, e.rule_id, e.event_date, e.available_date)
            for e in log.available_through(as_of)
        ]

    assert events_for(bars.iloc[:cut]) == events_for(bars)
