"""确认摆动点：区分实际拐点日与最早可用（确认）日。

移植来源
--------
旧路径 : /Users/yongbiaoli/Desktop/licai
          src/trading_v11/indicators/pivots.py
旧commit: a25eae9266f066e3a94ccf058add089e4c130366
改造原因:
  1. 旧实现使用 `window` 表示左右等长窗口，并依赖
     `trading_v11.domain.history.ProxyBar`（Decimal + available_at）。
     新项目改为 pandas DataFrame + float，并显式区分 left / right，
     因为 LEI 默认三左三右，而旧箱体系统默认五左五右。
  2. 旧 `available_at` 是 datetime（含盘后时点）；新项目使用交易日 date
     作为 available_date，与事件日志口径统一。
  3. 保留最重要的设计：`confirmed_through` 点位边界 —— 索引 i 的摆动点
     在 i+right 进入边界之前不可用。历史研究必须使用确认日。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Pivot


def confirmed_pivots(
    bars: pd.DataFrame,
    *,
    left: int | None = None,
    right: int | None = None,
    confirmed_through: int | None = None,
) -> tuple[Pivot, ...]:
    """返回在 confirmed_through（含）之前已经确认的摆动点。

    摆动高点：high 在 left+1+right 窗口内严格最高。
    摆动低点：low 在窗口内严格最低。
    严格性避免把平台整理误判为拐点。
    """
    spec = get_rule("swing_pivots")
    left = int(spec.param("left", 3)) if left is None else left
    right = int(spec.param("right", 3)) if right is None else right
    if left <= 0 or right <= 0:
        raise ValueError("left 与 right 必须为正")

    total = len(bars)
    if total == 0:
        return ()

    through = total - 1 if confirmed_through is None else confirmed_through
    if through < 0:
        return ()
    if through >= total:
        raise ValueError("confirmed_through 超出可用行数")

    highs = bars["high"].astype(float).to_numpy()
    lows = bars["low"].astype(float).to_numpy()
    dates = bars.index

    accepted: list[Pivot] = []
    # 候选中心最晚只能到 through - right，否则右侧尚未完成。
    latest_center = through - right
    for index in range(left, latest_center + 1):
        window_start = index - left
        window_end = index + right + 1
        center_high = highs[index]
        center_low = lows[index]

        neighbours_high = [
            highs[j] for j in range(window_start, window_end) if j != index
        ]
        neighbours_low = [
            lows[j] for j in range(window_start, window_end) if j != index
        ]

        confirm_index = index + right
        if all(center_high > value for value in neighbours_high):
            accepted.append(
                Pivot(
                    kind="high",
                    index=index,
                    pivot_date=dates[index].date(),
                    price=float(center_high),
                    confirmed_index=confirm_index,
                    available_date=dates[confirm_index].date(),
                )
            )
        if all(center_low < value for value in neighbours_low):
            accepted.append(
                Pivot(
                    kind="low",
                    index=index,
                    pivot_date=dates[index].date(),
                    price=float(center_low),
                    confirmed_index=confirm_index,
                    available_date=dates[confirm_index].date(),
                )
            )
    return tuple(accepted)


def pivots_available_on(
    pivots: tuple[Pivot, ...],
    as_of: pd.Timestamp | object,
) -> tuple[Pivot, ...]:
    """筛出在 as_of（含）当天已经确认的摆动点。"""
    cutoff = pd.Timestamp(as_of).date()
    return tuple(p for p in pivots if p.available_date <= cutoff)


def swing_highs(pivots: tuple[Pivot, ...]) -> tuple[Pivot, ...]:
    return tuple(p for p in pivots if p.kind == "high")


def swing_lows(pivots: tuple[Pivot, ...]) -> tuple[Pivot, ...]:
    return tuple(p for p in pivots if p.kind == "low")


__all__ = ["confirmed_pivots", "pivots_available_on", "swing_highs", "swing_lows"]
