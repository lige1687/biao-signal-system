"""signpost_stats 单测：合成数据验证含金量统计口径（任务书 #1）。

覆盖：
- 与 fixed_horizon_stats 单标的口径一致性（胜率/均值同数）；
- 基准池化正确（信号=全样本日时超额=0）；
- 盈亏比计算；
- 零样本 / 单样本 / 未完成样本边界。
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.research.scenario_backtest_common import fixed_horizon_stats
from lei_signal.research.signpost_stats import (
    SIGNPOST_CATALOG,
    build_signal_edge_report,
)


def _make_frame(n: int = 120, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.001, 0.02, n))
    idx = pd.bdate_range("2024-01-02", periods=n)
    return pd.DataFrame(
        {
            "open": close * 0.998,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
        },
        index=idx,
    )


def _make_event(rule_id: str, sub_rule: str, day: date, symbol: str = "TEST.SZ") -> SignalEvent:
    return SignalEvent(
        event_id=f"{rule_id}:{sub_rule}:{day.isoformat()}",
        symbol=symbol,
        timeframe="1d",
        event_date=day,
        available_date=day,
        rule_id=rule_id,
        rule_version="1.0.0",
        direction=Direction.NEUTRAL,
        severity=Severity.INFO,
        strength=50,
        reason_cn="",
        provenance="research_proxy",
        evidence={"sub_rule": sub_rule},
    )


def _row_by_key(report, key: str):
    return next(r for r in report.rows if r.key == key)


def test_report_covers_catalog_and_equivalence_with_fixed_horizon():
    """单标的上，模块A口径与 fixed_horizon_stats 完全一致（不许另造口径）。"""
    frame = _make_frame(120)
    # 制造 5 个模块A确认事件（每 15 根一个）
    events = [
        _make_event("first_ma_pullback", "first_ma_pullback_confirmed",
                    frame.index[i].date())
        for i in range(20, 95, 15)
    ]
    report = build_signal_edge_report([(frame, events)])
    assert report is not None
    assert len(report.rows) == len(SIGNPOST_CATALOG)

    entries = list(range(20, 95, 15))
    expected = {s.key: s for s in fixed_horizon_stats(frame, entries)}
    row = _row_by_key(report, "module_a_entry")
    assert row.total_signals == len(entries)
    for h in row.horizons:
        assert h.horizon in (5, 10, 20, 60)
        exp = expected[f"day_{h.horizon}"]
        assert h.sample_count == exp.sample_count
        assert h.win_rate == pytest.approx(exp.win_rate)
        assert h.mean_return == pytest.approx(exp.mean_return)
        assert h.incomplete_count == exp.incomplete_count


def test_baseline_and_excess_zero_when_signal_is_every_day():
    """信号=全部交易日 ⇒ 胜率与基准相等、超额=0（基准池化正确性）。"""
    frame = _make_frame(80)
    all_days = [frame.index[i].date() for i in range(len(frame))]
    events = [
        _make_event("volume_proxies", "volume_up_surge", d) for d in all_days
    ]
    report = build_signal_edge_report([(frame, events)])
    row = _row_by_key(report, "volume_up_surge")
    for h in row.horizons:
        assert h.win_rate is not None and h.baseline_win_rate is not None
        assert h.win_rate == pytest.approx(h.baseline_win_rate)
        assert h.excess_win_rate == pytest.approx(0.0, abs=1e-12)
        assert h.excess_mean_return == pytest.approx(0.0, abs=1e-9)


def test_payoff_computed_on_deterministic_path():
    """盈亏比=平均盈利/|平均亏损|，用确定的涨跌路径验证。"""
    n = 12
    # 路径：事件日在 0 和 6；5 日后分别 +10% 和 -5%
    closes = [100.0] * n
    closes[5] = 110.0
    closes[6] = 100.0
    closes[11] = 95.0
    idx = pd.bdate_range("2024-01-02", periods=n)
    frame = pd.DataFrame(
        {"open": closes, "high": [c * 1.01 for c in closes],
         "low": [c * 0.99 for c in closes], "close": closes},
        index=idx,
    )
    events = [
        _make_event("volume_proxies", "volume_up_surge", idx[0].date()),
        _make_event("volume_proxies", "volume_up_surge", idx[6].date()),
    ]
    report = build_signal_edge_report([(frame, events)])
    h5 = next(h for h in _row_by_key(report, "volume_up_surge").horizons if h.horizon == 5)
    assert h5.sample_count == 2
    assert h5.mean_return == pytest.approx((10.0 - 5.0) / 2)
    assert h5.payoff == pytest.approx(10.0 / 5.0)


def test_zero_sample_and_single_sample_edges():
    """零样本：win_rate/mean/payoff 全 None；单样本：可算且盈亏比 None。"""
    frame = _make_frame(60)
    # 1) 无任何事件 → 该行 total_signals=0，各 horizon sample_count=0、None
    report = build_signal_edge_report([(frame, [])])
    row = _row_by_key(report, "top_structure_confirmed")
    assert row.total_signals == 0
    assert all(h.sample_count == 0 and h.win_rate is None and h.payoff is None
               for h in row.horizons)
    # 基准仍可算（同一批标的全样本日；60 日持有在 60 根 K 线上无法完成 → None）
    for h in row.horizons:
        if h.horizon < len(frame):
            assert h.baseline_win_rate is not None
        else:
            assert h.baseline_win_rate is None

    # 2) 单样本（路径上行）→ win_rate=1，payoff None（无亏损样本）
    events = [_make_event("top_structure", "top_structure_confirmed",
                          frame.index[10].date())]
    report2 = build_signal_edge_report([(frame, events)])
    row2 = _row_by_key(report2, "top_structure_confirmed")
    h5 = next(h for h in row2.horizons if h.horizon == 5)
    assert h5.sample_count == 1
    assert h5.payoff is None  # 单边无亏损样本


def test_incomplete_samples_excluded():
    """靠近数据末尾的事件：不足持有期 → incomplete 计数、不进胜率。"""
    n = 30
    idx = pd.bdate_range("2024-01-02", periods=n)
    closes = [100.0 + i for i in range(n)]  # 单边上行
    frame = pd.DataFrame(
        {"open": closes, "high": [c + 1 for c in closes],
         "low": [c - 1 for c in closes], "close": closes},
        index=idx,
    )
    events = [
        _make_event("lei_color", "lei_color_gray_started", idx[5].date()),
        # 距末尾仅 3 根：5/10/20/60 日全都不完整
        _make_event("lei_color", "lei_color_gray_started", idx[-2].date()),
    ]
    report = build_signal_edge_report([(frame, events)])
    row = _row_by_key(report, "lei_color_gray_started")
    assert row.total_signals == 2
    h5 = next(h for h in row.horizons if h.horizon == 5)
    assert h5.sample_count == 1
    assert h5.incomplete_count == 1
    assert h5.win_rate == 1.0  # 上行路径


def test_multi_symbol_pooling():
    """跨标的池化：样本数与胜率按两标的合并计算。"""
    f1 = _make_frame(80, seed=1)
    f2 = _make_frame(80, seed=2)
    ev1 = [_make_event("volume_proxies", "bearish_expansion", f1.index[i].date())
           for i in (10, 30)]
    ev2 = [_make_event("volume_proxies", "bearish_expansion", f2.index[i].date())
           for i in (20, 40, 60)]
    report = build_signal_edge_report([(f1, ev1), (f2, ev2)])
    assert report.n_symbols == 2
    row = _row_by_key(report, "bearish_expansion")
    assert row.total_signals == 5
    h5 = next(h for h in row.horizons if h.horizon == 5)
    assert h5.sample_count == 5  # 全部可完成


def test_no_usable_samples_returns_none():
    empty = pd.DataFrame()
    assert build_signal_edge_report([(empty, [])]) is None
    missing_cols = pd.DataFrame({"close": [1.0, 2.0]})
    assert build_signal_edge_report([(missing_cols, [])]) is None
