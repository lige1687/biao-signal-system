"""缺口事件（规格 §4.8 / §10，账本 gap_events v2.0.0，手册 2.5 标志性动作）。

判定（只用当日与此前已完成日 K，严格前向）：
- gap_up(t)   = Low(t) > High(t-1) 且 Low(t) − High(t-1) >= gap_min_atr × ATR20(t)；
- gap_down(t) = High(t) < Low(t-1) 且 Low(t-1) − High(t) >= gap_min_atr × ATR20(t)；
- 回补：缺口出现后，后续任一 K 线价格回到缺口区间即「已回补」--
  向上缺口区间 [High(t-1), Low(t)]，回补 = 后续 Low(s) <= 区间上沿 Low(t)；
  向下缺口区间 [High(t), Low(t-1)]，回补 = 后续 High(s) >= 区间下沿 High(t)。
  回补日 = 首次回到区间的那根 K 线；未回补缺口才有目标位意义（规格 §10）。

目标 B 接入（规格 §10 优先级第 2 档，经引擎 gap_target 开关启用、默认关）：
信号日上方最近的未回补向上缺口，缺口上沿 Low(t) 作目标候选；「未回补」按
信号日视角判定（filled_date 为空或晚于信号日），不使用任何未来信息。

缺口属路牌层（标志性动作，只预警不必然反向）。不灌 live 事件日志（与
strict_structure 同纪律），供回测与 API 按需读取。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.features.indicators import average_true_range

RULE_ID = "gap_events"

DIRECTION_UP = "up"
DIRECTION_DOWN = "down"


@dataclass(frozen=True, slots=True)
class GapEvent:
    """一个已识别的缺口及其回补状态（回补按全数据段判定，前向无泄漏）。"""

    direction: str                # "up" | "down"
    gap_date: date
    zone_low: float               # 向上缺口 = High(t-1)；向下缺口 = High(t)
    zone_high: float              # 向上缺口 = Low(t)；向下缺口 = Low(t-1)
    size_atr: float               # 缺口幅度 / 当日 ATR
    filled_date: date | None      # 首次回到缺口区间的日子；None = 至数据末尾未回补


def _params() -> tuple[float, int]:
    spec = get_rule(RULE_ID)
    gap_min_atr = float(spec.param("gap_min_atr", 0.25))
    atr_period = int(spec.param("atr_period", 20))
    if gap_min_atr <= 0 or atr_period <= 0:
        raise ValueError("gap_events 的 gap_min_atr / atr_period 必须为正")
    return gap_min_atr, atr_period


def detect_gaps(frame: pd.DataFrame) -> list[GapEvent]:
    """识别全部缺口并判定回补（回补日只依赖其后已发生 K 线，前向无泄漏）。"""
    gap_min_atr, atr_period = _params()
    if frame.empty or len(frame) < 2:
        return []
    required = {"high", "low"}
    if not required.issubset(frame.columns):
        return []
    atr = average_true_range(frame, atr_period)

    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    gaps: list[GapEvent] = []
    for position in range(1, len(frame)):
        atr_value = float(atr.iloc[position])
        if not pd.notna(atr_value) or atr_value <= 0:
            continue
        prev_high = float(high.iloc[position - 1])
        prev_low = float(low.iloc[position - 1])
        cur_high = float(high.iloc[position])
        cur_low = float(low.iloc[position])
        day = frame.index[position].date()
        if cur_low > prev_high and (cur_low - prev_high) >= gap_min_atr * atr_value:
            gaps.append(
                GapEvent(
                    direction=DIRECTION_UP,
                    gap_date=day,
                    zone_low=prev_high,
                    zone_high=cur_low,
                    size_atr=(cur_low - prev_high) / atr_value,
                    filled_date=None,
                )
            )
        elif cur_high < prev_low and (prev_low - cur_high) >= gap_min_atr * atr_value:
            gaps.append(
                GapEvent(
                    direction=DIRECTION_DOWN,
                    gap_date=day,
                    zone_low=cur_high,
                    zone_high=prev_low,
                    size_atr=(prev_low - cur_high) / atr_value,
                    filled_date=None,
                )
            )

    # 回补判定：向上缺口看后续 Low 是否 <= 区间上沿；向下缺口看后续 High
    # 是否 >= 区间下沿。区间边界按开区间进入（触及边界即视为回到区间）。
    highs = high.to_numpy()
    lows = low.to_numpy()
    dates = [ts.date() for ts in frame.index]
    filled: list[GapEvent] = []
    for gap in gaps:
        start = frame.index.get_loc(pd.Timestamp(gap.gap_date))
        fill_day: date | None = None
        if gap.direction == DIRECTION_UP:
            for position in range(start + 1, len(frame)):
                if lows[position] <= gap.zone_high:
                    fill_day = dates[position]
                    break
        else:
            for position in range(start + 1, len(frame)):
                if highs[position] >= gap.zone_low:
                    fill_day = dates[position]
                    break
        filled.append(
            GapEvent(
                direction=gap.direction,
                gap_date=gap.gap_date,
                zone_low=gap.zone_low,
                zone_high=gap.zone_high,
                size_atr=gap.size_atr,
                filled_date=fill_day,
            )
        )
    return filled


def unfilled_gap_target(
    gaps: list[GapEvent],
    *,
    as_of: date,
    entry_price: float,
) -> tuple[float, date] | None:
    """as_of 视角：入场价上方价格最近的未回补向上缺口。

    返回 (缺口上沿 Low(t), 缺口日)；无候选返回 None。
    - 未回补 = filled_date 为空或晚于 as_of（只用 as_of 及此前可知信息）；
    - 上方 = zone_low（=缺口日昨 High）> entry_price，取 zone_low 最小者。
    """
    best: tuple[float, date] | None = None
    best_zone_low = float("inf")
    for gap in gaps:
        if gap.direction != DIRECTION_UP:
            continue
        if gap.gap_date > as_of:
            continue  # 信号日之后出现的缺口不可用（前向）
        if gap.filled_date is not None and gap.filled_date <= as_of:
            continue  # 信号日前已回补
        if gap.zone_low <= entry_price:
            continue  # 缺口不在入场价上方
        if gap.zone_low < best_zone_low:
            best_zone_low = gap.zone_low
            best = (gap.zone_high, gap.gap_date)
    return best


def recent_unfilled_up_gap(
    gaps: list[GapEvent],
    *,
    as_of: date,
    lookback_bars: int,
    bar_dates: list[date],
) -> GapEvent | None:
    """as_of 前 lookback_bars 根内出现的、as_of 视角未回补的最近向上缺口。

    供缺口动能过滤实验（信号日近 N 日存在未回补向上缺口才做）。
    bar_dates = frame 逐日日期列表（定位 lookback 窗口起点）。
    """
    if lookback_bars <= 0 or as_of not in bar_dates:
        return None
    end = bar_dates.index(as_of)
    start = max(0, end - lookback_bars + 1)
    window_start = bar_dates[start]
    found: GapEvent | None = None
    for gap in gaps:
        if gap.direction != DIRECTION_UP:
            continue
        if not (window_start <= gap.gap_date <= as_of):
            continue
        if gap.filled_date is not None and gap.filled_date <= as_of:
            continue
        if found is None or gap.gap_date > found.gap_date:
            found = gap
    return found


__all__ = [
    "DIRECTION_DOWN",
    "DIRECTION_UP",
    "GapEvent",
    "RULE_ID",
    "detect_gaps",
    "recent_unfilled_up_gap",
    "unfilled_gap_target",
]
