"""MACD 副图事件序列化（Web 端展示层）。

判定权在 :mod:`lei_signal.rules.macd_strength`：本模块只把逐日读数筛成
「事件日」（金叉 / 死叉 / 上穿0轴 / 下穿0轴）并附盲区补齐（当日 LEI 颜色
与 EMA20 斜率方向），供 web 前端在 MACD 副图上打标注。

口径约束（.claude/skills/macd-reading/SKILL.md）：
- 只筛四类「当日发生」的交叉事件；扩散/收敛是连续状态，由 DIF 线形态本身
  表达，不打点。
- 每个事件必带盲区补齐——讲 MACD 强度时同时给出破线（LEI 颜色）与均线
  拐头（EMA20 斜率），否则就是违反口径的讲法。
- MACD 是研究代理：金叉/死叉只是强度描述，不产生交易事件、不是买点。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.rules.macd_strength import read_macd_strength

#: 事件状态 → 前端标记类型（Web 端按 type 选图形与配色）。
_EVENT_TYPE: dict[str, str] = {
    "金叉": "golden_cross",
    "死叉": "death_cross",
    "上穿0轴": "zero_cross_up",
    "下穿0轴": "zero_cross_down",
}

_LEI_COLOR_CN: dict[str, str] = {
    "green": "绿色（强势）",
    "gray": "灰色（关注）",
    "black": "黑色（弱势）",
    "unknown": "未知",
}


def _color_cn(row: pd.Series) -> str:
    v = row.get("signal_color")
    if v is None or pd.isna(v):
        return "未知"
    return _LEI_COLOR_CN.get(str(v), "未知")


def _slope_cn(row: pd.Series) -> str:
    v = row.get("ema20_slope")
    if v is None or pd.isna(v):
        return "数据不足"
    v = float(v)
    if v > 0:
        return "上行"
    if v < 0:
        return "下行"
    return "走平"


def build_macd_events(result: AnalysisResult, *, max_bars: int) -> list[dict[str, Any]]:
    """把逐日 MACD 读数筛成事件日列表（按时间升序）。

    与 ``serialize_result`` 的 ``max_bars`` 用同一个值，保证事件标注与
    副图 DIF/DEA 序列的可见范围一致。
    """
    frame = result.frame.tail(max_bars)
    rows = list(frame.iterrows())
    events: list[dict[str, Any]] = []
    for i, (idx, row) in enumerate(rows):
        prev_row = rows[i - 1][1] if i > 0 else None
        reading = read_macd_strength(row, prev_row)
        if reading is None:
            continue
        event_type = _EVENT_TYPE.get(reading.status)
        if event_type is None:
            continue
        events.append({
            "date": idx.strftime("%Y-%m-%d"),
            "type": event_type,
            "statusCn": reading.status,
            "dimension": reading.dimension_value,
            "dif": round(reading.dif, 4),
            "dea": round(reading.dea, 4),
            "hist": round(reading.hist, 4),
            "detailCn": reading.detail_cn,
            # 盲区补齐：破线看 LEI 颜色，均线拐头看 EMA20 斜率
            "colorCn": _color_cn(row),
            "slopeCn": _slope_cn(row),
        })
    return events


__all__ = ["build_macd_events"]
