"""LEI 绿灰黑三色。

严格公式（configs/rules.v1.yaml::lei_color，provenance=lei_explicit）：
    绿色 = Close(t) > EMA20(t) 且 Close(t) > Close(t-20)
    黑色 = Close(t) < EMA20(t) 且 Close(t) < Close(t-20)
    灰色 = 数据已就绪，但绿色与黑色均不成立
    未知 = 数据不足 21 根

灰色表示均线方向产生分歧，需要关注；不等于卖出。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import SignalColor

REASON_GREEN = "收盘价高于EMA20，且高于20个交易日前收盘价"
REASON_BLACK = "收盘价低于EMA20，且低于20个交易日前收盘价"
REASON_GRAY = "EMA20与MA20方向未形成共同向上或共同向下，趋势出现分歧，需要关注"
REASON_UNKNOWN = "数据不足，至少需要21根日K线"


def classify_colors(frame: pd.DataFrame) -> pd.DataFrame:
    """按严格公式逐日分类，并给出中文理由。

    要求输入含 close、ema20、close_lag20。计算是逐行的，
    因此追加未来数据不会改变任何旧日期的结论。
    """
    required = {"close", "ema20", "close_lag20"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"指标数据缺少字段: {', '.join(sorted(missing))}")

    spec = get_rule("lei_color")
    result = frame.copy()

    ready = result[["close", "ema20", "close_lag20"]].notna().all(axis=1)
    above_ema = result["close"] > result["ema20"]
    below_ema = result["close"] < result["ema20"]
    above_lag = result["close"] > result["close_lag20"]
    below_lag = result["close"] < result["close_lag20"]

    green = ready & above_ema & above_lag
    black = ready & below_ema & below_lag

    result["signal_color"] = np.select(
        [~ready, green, black],
        [SignalColor.UNKNOWN.value, SignalColor.GREEN.value, SignalColor.BLACK.value],
        default=SignalColor.GRAY.value,
    )
    # MA20 当日变化量为 (Close(t) - Close(t-20)) / 20，因此收盘价与 20 日前
    # 收盘价的关系即可确定 MA20 当前方向。
    result["ma20_direction"] = np.select(
        [~ready, above_lag, below_lag], ["unknown", "up", "down"], default="flat"
    )
    result["ema20_direction"] = np.select(
        [~ready, above_ema, below_ema], ["unknown", "up", "down"], default="flat"
    )
    result["signal_reason"] = np.select(
        [~ready, green, black],
        [REASON_UNKNOWN, REASON_GREEN, REASON_BLACK],
        default=REASON_GRAY,
    )
    result["color_rule_version"] = spec.version

    previous = result["signal_color"].shift(1)
    result["color_changed"] = (
        ready & previous.notna() & result["signal_color"].ne(previous)
    )
    result["color_ready"] = ready
    return result


def color_at(frame: pd.DataFrame, index: int = -1) -> SignalColor:
    """取某一行的颜色。"""
    return SignalColor(str(frame["signal_color"].iloc[index]))


def color_runs(frame: pd.DataFrame) -> pd.DataFrame:
    """把逐日颜色压缩为连续区段。

    研究要求「连续绿色只算一次开始事件」，此函数提供区段起止，
    供事件层与研究层共同使用。
    """
    if frame.empty:
        return pd.DataFrame(columns=["color", "start_date", "end_date", "bars"])
    colors = frame["signal_color"]
    group = (colors != colors.shift(1)).cumsum()
    grouped = frame.groupby(group)
    runs = pd.DataFrame(
        {
            "color": grouped["signal_color"].first(),
            "start_date": grouped.apply(lambda g: g.index[0]),
            "end_date": grouped.apply(lambda g: g.index[-1]),
            "bars": grouped.size(),
        }
    ).reset_index(drop=True)
    return runs


__all__ = [
    "REASON_BLACK",
    "REASON_GRAY",
    "REASON_GREEN",
    "REASON_UNKNOWN",
    "classify_colors",
    "color_at",
    "color_runs",
]
