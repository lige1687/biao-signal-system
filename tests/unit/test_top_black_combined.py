"""修复 4：Top+Black 组合状态必须覆盖两种顺序。

  1) 顶部先确认 → 后转黑
  2) 先转黑 → 黑色持续期间顶部才确认
  3) 顶部失效或颜色不再为黑 → 组合状态结束
  4) 重新进入可产生新事件
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from lei_signal.domain.types import StructureStatus
from lei_signal.features.indicators import compute_features
from lei_signal.rules.key_wave import detect_key_wave_events
from lei_signal.rules.lei_color import classify_colors


def _bars(rows: list[dict[str, float]], start: str = "2024-01-02") -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=len(rows))
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _make_top(start_date: date, neckline: float, ref_high: float, confirmed: date, \
    invalidated: date | None = None):
    from lei_signal.domain.types import StructureInstance
    return StructureInstance(
        structure_id=f"top-{confirmed.isoformat()}",
        symbol="TEST",
        structure_type="top_structure",
        side="top",
        detected_date=start_date,
        neckline=neckline,
        reference_high=ref_high,
        confirmed_date=confirmed,
        status=StructureStatus.INVALIDATED if invalidated else StructureStatus.CONFIRMED,
        invalidated_date=invalidated,
        invalidated_reason="top_warning_invalidated_by_new_high" if invalidated else None,
    )


def test_top_first_then_black_creates_top_plus_black() -> None:
    """顺序 1：顶部先确认 → 后转黑 → Top+Black 应被记录。"""
    rows: list[dict[str, float]] = []
    for i in range(50):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 顶部候选 + 确认：day 30 跌破颈线
    # 假设 day 25 是 confirmed
    confirmed_date = pd.bdate_range("2024-01-02", periods=len(rows))[25].date()
    # 后续 day 40 起转黑
    for i in range(40, 50):
        rows[i] = {"open": 50.0, "high": 50.5, "low": 45.0,
                   "close": 45.5, "volume": 1_000_000}
    bars = _bars(rows)
    frame = compute_features(bars)
    frame = classify_colors(frame)
    top = _make_top(
        start_date=confirmed_date - timedelta(days=3),
        neckline=70.0,
        ref_high=80.0,
        confirmed=confirmed_date,
    )
    events = detect_key_wave_events(frame, "TEST", tops=[top])
    sub_rules = {(e.available_date, e.evidence["sub_rule"]) for e in events}
    # 必须有 top_plus_black 事件
    has_top_plus_black = any(sr == "top_plus_black" for _, sr in sub_rules)
    assert has_top_plus_black, "顶部先确认 → 后转黑 应产生 Top+Black"


def test_black_first_then_top_creates_top_plus_black() -> None:
    """顺序 2：先转黑 → 黑色持续期间顶部才确认 → Top+Black 应被记录。"""
    rows: list[dict[str, float]] = []
    for i in range(50):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 早期就转黑
    for i in range(20, 50):
        rows[i] = {"open": 50.0, "high": 50.5, "low": 45.0,
                   "close": 45.5, "volume": 1_000_000}
    bars = _bars(rows)
    frame = compute_features(bars)
    frame = classify_colors(frame)
    # 顶部在 day 30 确认（在黑色已持续 10 天后）
    confirmed_date = pd.bdate_range("2024-01-02", periods=len(rows))[30].date()
    top = _make_top(
        start_date=confirmed_date - timedelta(days=3),
        neckline=60.0,
        ref_high=70.0,
        confirmed=confirmed_date,
    )
    events = detect_key_wave_events(frame, "TEST", tops=[top])
    sub_rules = [(e.available_date, e.evidence["sub_rule"]) for e in events]
    has_top_plus_black = any(sr == "top_plus_black" for _, sr in sub_rules)
    assert has_top_plus_black, "先转黑 → 顶后才确认 也应产生 Top+Black"


def test_top_plus_black_ends_when_color_returns_to_non_black() -> None:
    """颜色转回非黑色时 Top+Black 状态结束，生成 top_plus_black_ended。"""
    rows: list[dict[str, float]] = []
    for i in range(50):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # day 20-30 转黑
    for i in range(20, 30):
        rows[i] = {"open": 50.0, "high": 50.5, "low": 45.0,
                   "close": 45.5, "volume": 1_000_000}
    bars = _bars(rows)
    frame = compute_features(bars)
    frame = classify_colors(frame)
    confirmed_date = pd.bdate_range("2024-01-02", periods=len(rows))[22].date()
    top = _make_top(
        start_date=confirmed_date - timedelta(days=3),
        neckline=60.0, ref_high=70.0,
        confirmed=confirmed_date,
    )
    events = detect_key_wave_events(frame, "TEST", tops=[top])
    ended = [e for e in events if e.evidence["sub_rule"] == "top_plus_black_ended"]
    assert ended, "颜色转回非黑时必须产生 top_plus_black_ended"


def test_top_plus_black_ends_when_top_invalidated() -> None:
    """顶部被新高解除时 Top+Black 状态立即结束。"""
    rows: list[dict[str, float]] = []
    for i in range(50):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 持续转黑
    for i in range(20, 50):
        rows[i] = {"open": 50.0, "high": 50.5, "low": 45.0,
                   "close": 45.5, "volume": 1_000_000}
    bars = _bars(rows)
    frame = compute_features(bars)
    frame = classify_colors(frame)
    confirmed_date = pd.bdate_range("2024-01-02", periods=len(rows))[22].date()
    invalidated_date = pd.bdate_range("2024-01-02", periods=len(rows))[35].date()
    top = _make_top(
        start_date=confirmed_date - timedelta(days=3),
        neckline=60.0, ref_high=70.0,
        confirmed=confirmed_date,
        invalidated=invalidated_date,
    )
    events = detect_key_wave_events(frame, "TEST", tops=[top])
    ended = [e for e in events if e.evidence["sub_rule"] == "top_plus_black_ended"]
    assert ended
    # 结束事件日期必须早于（或等于）顶部失效日期
    assert any(e.available_date <= invalidated_date for e in ended)


def test_reentering_top_plus_black_produces_new_event() -> None:
    """重新进入 Top+Black 必须产生新事件。

    构造：day 25 起转黑（top+black 起始）；
    day 30 回到正常（top+black 结束）；
    day 35 再次转黑（top+black 重新进入）。
    """
    rows: list[dict[str, float]] = []
    # 前 25 根：温和上行（close 一直 > EMA20）
    for i in range(25):
        close = 50.0 + i * 0.3
        rows.append(
            {"open": close - 0.1, "high": close + 0.3, "low": close - 0.2,
             "close": close, "volume": 1_000_000}
        )
    # day 25-29：深跌 → 转黑
    for i in range(25, 30):
        rows.append(
            {"open": 57.0 - (i - 25) * 3.0, "high": 57.0, "low": 40.0,
             "close": 42.0, "volume": 1_000_000}
        )
    # day 30-34：强力反弹 → 回到正常
    for i in range(30, 35):
        close = 45.0 + (i - 30) * 2.0
        rows.append(
            {"open": close - 0.5, "high": close + 1.0, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    # day 35-45：再次深跌 → 再次转黑
    for i in range(35, 46):
        close = 55.0 - (i - 35) * 1.0
        rows.append(
            {"open": close + 0.5, "high": close + 1.0, "low": close - 1.0,
             "close": close, "volume": 1_000_000}
        )
    bars = _bars(rows)
    frame = compute_features(bars)
    frame = classify_colors(frame)
    # 验证序列确实有 black 段
    blacks = [dt.date() for dt in frame.index if frame.loc[dt, "signal_color"] == "black"]
    assert len(blacks) >= 5
    # 顶部在 day 22 确认
    confirmed_date = pd.bdate_range("2024-01-02", periods=len(rows))[22].date()
    top = _make_top(
        start_date=confirmed_date - timedelta(days=3),
        neckline=60.0, ref_high=70.0,
        confirmed=confirmed_date,
    )
    events = detect_key_wave_events(frame, "TEST", tops=[top])
    starts = [e for e in events if e.evidence["sub_rule"] == "top_plus_black"]
    ended = [e for e in events if e.evidence["sub_rule"] == "top_plus_black_ended"]
    assert len(starts) >= 2, f"应至少 2 次 Top+Black 起始，实际 {len(starts)}"
    assert len(ended) >= 1, "应至少 1 次结束事件"
