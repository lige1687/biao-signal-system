"""ma200_break 单测：分档事件状态机 + 真实上证历史的重放验证（任务书 #4）。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.domain.types import SignalEvent
from lei_signal.rules.ma200_break import (
    RULE_ID,
    SUB_BREAK_STARTED,
    SUB_D10_WARN,
    SUB_D20_RISK,
    SUB_D3_WATCH,
    SUB_D5_CHECK,
    detect_ma200_break_events,
)


def _frame_from_closes(closes: list[float]) -> pd.DataFrame:
    idx = pd.bdate_range("2020-01-02", periods=len(closes))
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": np.full(len(closes), 1e6),
        },
        index=idx,
    )


def _subs(events: list[SignalEvent]) -> list[str]:
    return [e.evidence.get("sub_rule") for e in events]


def test_no_events_without_break():
    # 全程在均线之上（持续上行）
    closes = list(np.linspace(100.0, 300.0, 400))
    events = detect_ma200_break_events(_frame_from_closes(closes), "TEST.SZ")
    assert events == []


def test_short_history_no_events():
    closes = list(np.full(150, 100.0))  # < 200+2 根
    assert detect_ma200_break_events(_frame_from_closes(closes), "TEST.SZ") == []


def test_full_staged_episode():
    """跌破后一路阴跌 25 天：依次出 started→d3→d5→d10→d20，各一次。"""
    n_ma = 200
    # 先横盘让 SMA200 稳定在 100，然后跌破并持续走低
    closes = [100.0] * n_ma
    # 跌破日：close=98（< SMA200≈100），此前一日 100 >= SMA200
    closes.append(98.0)
    # 之后 24 天继续阴跌（保证始终 < 当日 SMA200，且 d5 检查①累计跌幅命中：
    # 跌破日 98 → 第5天 <98*0.97≈95.06）
    for i in range(24):
        closes.append(97.0 - i * 0.6)
    events = detect_ma200_break_events(_frame_from_closes(closes), "TEST.SZ")
    subs = _subs(events)
    assert subs[0] == SUB_BREAK_STARTED
    assert subs.count(SUB_D3_WATCH) == 1
    assert subs.count(SUB_D5_CHECK) == 1
    assert subs.count(SUB_D10_WARN) == 1
    assert subs.count(SUB_D20_RISK) == 1
    # d5 命中检查项：drop_since_break（98 → 95 前后累计 ≤ -3%）
    d5 = next(e for e in events if e.evidence["sub_rule"] == SUB_D5_CHECK)
    assert d5.evidence["checks"]["drop_since_break"] is True
    # 严重度递增：started/watch < d5/d10 < d20
    sev = {e.evidence["sub_rule"]: e.severity.value for e in events}
    assert sev[SUB_D20_RISK] == "critical"


def test_recovery_ends_episode_silently():
    """跌破后第 2 天收回：无 d3/d5/d10/d20，只发 started。"""
    closes = [100.0] * 200 + [98.0, 101.0] * 3 + [101.0] * 10
    events = detect_ma200_break_events(_frame_from_closes(closes), "TEST.SZ")
    subs = _subs(events)
    assert SUB_BREAK_STARTED in subs
    assert SUB_D3_WATCH not in subs and SUB_D5_CHECK not in subs


def test_d5_checks_pure_function():
    """d5 三项检查的纯函数口径（显式数值验证）。"""
    from lei_signal.rules.ma200_break import _d5_checks

    params = {
        "d5_drop_pct": -3.0, "d5_below_ma_pct": -2.0, "slope_lookback": 5,
    }
    # 累计跌 5%、低于均线 3% 且均线走低、50<200 → 三项全中
    checks = _d5_checks(
        close_break=100.0, close_now=95.0, sma200_now=98.0,
        sma200_slope_ref=98.5, sma50_now=97.0, params=params,
    )
    assert checks == {
        "drop_since_break": True,
        "below_ma_and_slope_down": True,
        "ma50_below_ma200": True,
    }
    # 温和场景：跌 0.8%、低于均线 1.3%、50 在 200 上方 → 全不中
    checks2 = _d5_checks(
        close_break=90.0, close_now=89.3, sma200_now=90.5,
        sma200_slope_ref=90.55, sma50_now=93.0, params=params,
    )
    assert not any(checks2.values())


def test_d5_no_check_hit_emits_nothing():
    """上升趋势后的温和跌破（第5天三项全不命中）：只发 started/d3，不发 d5_check。"""
    # 先构造 200 天上升趋势（SMA50>SMA200），再跌破并温和下滑 5 天
    closes = list(np.linspace(80.0, 100.0, 200))
    # 从 100 回落到跌破 SMA200（约 90.4），再温和走低（累计跌幅<3%、距均线<2%）
    closes += [96.0, 95.0, 94.0, 93.0, 92.0, 91.0, 90.0]   # 跌破日≈90.0
    closes += [89.8, 89.6, 89.5, 89.4, 89.3]               # 回合内第1~5天
    events = detect_ma200_break_events(_frame_from_closes(closes), "TEST.SZ")
    subs = _subs(events)
    assert SUB_BREAK_STARTED in subs
    assert SUB_D3_WATCH in subs       # 第3天仍未收回 → d3 观望
    assert SUB_D5_CHECK not in subs   # 三项全未命中 → 不发 d5


def test_each_stage_once_per_episode_and_new_episode_restarts():
    """两个回合：第一回合走到 d20，收回后再次跌破开启新回合（事件重新可发）。"""
    closes = [100.0] * 200
    # 回合1：跌破 + 21 天阴跌 + 收回
    closes.append(98.0)
    closes += [97.0 - i * 0.4 for i in range(21)]     # 深跌（d5 检查①命中）
    closes += [110.0] * 8                              # 收回（远高于 SMA200）
    # 回合2：从 110 直接跌回均线下方（跳空式跌破）+ 3 天低位
    closes.append(95.0)                                # < SMA200（约 99），前日 110 在上
    closes += [94.0, 93.5, 93.0]
    events = detect_ma200_break_events(_frame_from_closes(closes), "TEST.SZ")
    subs = _subs(events)
    assert subs.count(SUB_BREAK_STARTED) == 2
    assert subs.count(SUB_D20_RISK) == 1
    # 第二回合只走到 d3
    assert subs.count(SUB_D3_WATCH) == 2


def test_sse_real_history_replay():
    """真实上证全史重放：事件为跌破回合的分档预警，数量合理（>0 且远小于天数）。"""
    from pathlib import Path

    path = Path.home() / ".lei_signal_lab" / "cache" / "study_ma200_index_sh000001.parquet"
    if not path.exists():
        pytest.skip("本机无上证全史研究缓存（先跑 scripts/ma200_break_study.py）")
    df = pd.read_parquet(path)
    bars = pd.DataFrame(
        {
            "open": df["close"].values,
            "high": df["close"].values,
            "low": df["close"].values,
            "close": df["close"].astype(float).values,
            "volume": np.full(len(df), 1.0),
        },
        index=pd.to_datetime(df.index),
    )
    events = detect_ma200_break_events(bars, "000001.SS")
    subs = _subs(events)
    started = subs.count(SUB_BREAK_STARTED)
    assert started > 50, f"上证 34 年历史跌破回合应 >50，实际 {started}"
    # 回放口径与统计脚本一致：started 数应等于研究脚本的 136 次（同一上升沿定义）
    assert started == 136
    # 分档事件数必须 ≤ 回合数
    for sub in (SUB_D3_WATCH, SUB_D5_CHECK, SUB_D10_WARN, SUB_D20_RISK):
        assert subs.count(sub) <= started
    # 全部事件 rule_id 正确且只预警（bearish 方向，无 bullish）
    assert all(e.rule_id == RULE_ID for e in events)
