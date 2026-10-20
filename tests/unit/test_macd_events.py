"""MACD 副图事件序列化（api/macd_events）门禁。

口径（.claude/skills/macd-reading/SKILL.md）：
- 只有四类「当日发生」的交叉事件（金叉/死叉/上穿0轴/下穿0轴）进 macdEvents；
  扩散/收敛等连续状态不打点。
- 每个事件必带盲区补齐：当日 LEI 颜色（破线）与 EMA20 斜率方向（均线拐头）。
- 全部文案来自 rules.macd_strength 的确定性输出，本模块不自算交叉。
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from lei_signal.api.macd_events import build_macd_events


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        index=pd.bdate_range(start="2024-01-02", periods=len(rows)),
        columns=[
            "macd_dif", "macd_dea", "macd_hist", "signal_color", "ema20_slope",
        ],
    )


def _result(rows: list[dict]):
    # build_macd_events 只读 result.frame；用 SimpleNamespace 避免
    # 为一个序列化测试构造完整 AnalysisResult。
    return SimpleNamespace(frame=_frame(rows))


def test_cross_and_zero_cross_days_become_events() -> None:
    """金叉日、上穿0轴日各自成为事件；中间的连续状态日（多头扩散/收敛）不打点。"""
    rows = [
        # DIF 在 DEA 下方（空头，无事件）
        {"macd_dif": -0.5, "macd_dea": -0.4, "macd_hist": -0.2,
         "signal_color": "black", "ema20_slope": -0.8},
        # 金叉：DIF 上穿 DEA
        {"macd_dif": -0.3, "macd_dea": -0.38, "macd_hist": 0.16,
         "signal_color": "gray", "ema20_slope": -0.1},
        # 多头尚早：仍为负值区间的连续状态，无事件
        {"macd_dif": -0.1, "macd_dea": -0.3, "macd_hist": 0.4,
         "signal_color": "gray", "ema20_slope": 0.2},
        # 上穿0轴：DIF 从负转正（两线排列翻转）
        {"macd_dif": 0.15, "macd_dea": -0.2, "macd_hist": 0.7,
         "signal_color": "green", "ema20_slope": 0.5},
        # 多头扩散：连续状态，无事件
        {"macd_dif": 0.3, "macd_dea": -0.1, "macd_hist": 0.8,
         "signal_color": "green", "ema20_slope": 0.6},
    ]
    events = build_macd_events(_result(rows), max_bars=400)  # type: ignore[arg-type]

    assert [e["type"] for e in events] == ["golden_cross", "zero_cross_up"]
    assert events[0]["statusCn"] == "金叉"
    assert events[0]["dimension"] == "支持"
    assert events[1]["statusCn"] == "上穿0轴"


def test_death_cross_and_zero_cross_down() -> None:
    rows = [
        {"macd_dif": 0.4, "macd_dea": 0.3, "macd_hist": 0.2,
         "signal_color": "green", "ema20_slope": 0.3},
        # 死叉：DIF 下穿 DEA
        {"macd_dif": 0.2, "macd_dea": 0.28, "macd_hist": -0.16,
         "signal_color": "gray", "ema20_slope": -0.1},
        # 下穿0轴
        {"macd_dif": -0.1, "macd_dea": 0.2, "macd_hist": -0.6,
         "signal_color": "black", "ema20_slope": -0.5},
    ]
    events = build_macd_events(_result(rows), max_bars=400)  # type: ignore[arg-type]

    assert [e["type"] for e in events] == ["death_cross", "zero_cross_down"]
    assert events[0]["dimension"] == "冲突"


def test_every_event_carries_blind_spot_fill() -> None:
    """讲 MACD 必带盲区补齐：LEI 颜色 + EMA20 斜率方向。"""
    rows = [
        # DIF 一直高于 DEA（无交叉），但 DIF 从负转正 → 纯上穿0轴事件
        {"macd_dif": -0.05, "macd_dea": -0.15, "macd_hist": 0.2,
         "signal_color": "gray", "ema20_slope": 0.4},
        {"macd_dif": 0.1, "macd_dea": -0.1, "macd_hist": 0.4,
         "signal_color": "green", "ema20_slope": -0.2},
    ]
    events = build_macd_events(_result(rows), max_bars=400)  # type: ignore[arg-type]

    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "zero_cross_up"
    # 破线补齐：当日 LEI 颜色；拐头补齐：EMA20 斜率方向（负 = 下行）
    assert ev["colorCn"] == "绿色（强势）"
    assert ev["slopeCn"] == "下行"
    # 数值与解释来自规则层输出，字段齐全
    assert ev["dif"] == 0.1 and ev["dea"] == -0.1
    assert "DIF" in ev["detailCn"]


def test_warmup_nan_rows_are_skipped() -> None:
    """前导 warmup 段（DIF/DEA 为 NaN）不得产生事件，也不得报错。"""
    rows = [
        {"macd_dif": np.nan, "macd_dea": np.nan, "macd_hist": np.nan,
         "signal_color": "unknown", "ema20_slope": np.nan},
        {"macd_dif": np.nan, "macd_dea": np.nan, "macd_hist": np.nan,
         "signal_color": "unknown", "ema20_slope": np.nan},
        {"macd_dif": 0.1, "macd_dea": -0.05, "macd_hist": 0.3,
         "signal_color": "green", "ema20_slope": 0.2},
    ]
    events = build_macd_events(_result(rows), max_bars=400)  # type: ignore[arg-type]
    # 第三行无前一日有效 DIF（前两行 NaN）→ 只有 zero/交叉都判不出，
    # read_macd_strength 返回静态强度（多头扩散），不构成事件。
    assert events == []


def test_max_bars_keeps_events_aligned_with_chart_window() -> None:
    """max_bars 与副图序列同窗：窗口外的旧事件不得泄漏进结果。"""
    rows = [
        {"macd_dif": -0.5, "macd_dea": -0.4, "macd_hist": -0.2,
         "signal_color": "black", "ema20_slope": -0.5},
        {"macd_dif": -0.3, "macd_dea": -0.38, "macd_hist": 0.16,
         "signal_color": "black", "ema20_slope": -0.4},
    ]
    events = build_macd_events(_result(rows), max_bars=1)  # type: ignore[arg-type]
    # 只留最后一根（窗口内），其前一日已被裁掉 → 无交叉可判，无事件
    assert events == []
