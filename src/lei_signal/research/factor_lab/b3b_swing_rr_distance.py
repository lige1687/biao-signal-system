"""B3-b 候选 2：mixed.swing_rr_distance（已确认摆动点距离比）最小计算实现。

定义来源：B1 表单 5（fa-20260919-b1-rr-distance，trading-spec §10 盈亏比
过滤的目标结构口径），版本化草案见
docs/experiments/raw/factor-b3b-2026-09-20/swing-rr-distance/definition-draft.md。

边界（G2 重点核查项，实现不得越界）：
- 结构位不自行识别：本模块只消费外部传入的已确认摆动点
  （lei_signal.features.pivots.confirmed_pivots，三左三右口径，
  confirmed_index 为最早可用日）；快照缺结构输入时输出 NaN 并给出
  missing_reason，不临时新增结构识别算法补洞；
- 零后视回填：t 时点只允许使用 confirmed_index <= t 的摆动点，摆动点
  在确认日之前对任何 t 不可见；
- 分母为 close − L_conf；分子为 H_conf − close；任一端 ≤ 0（close 跌破
  摆动低点、或已越过摆动高点）→ NaN，对应 spec"目标不可计算"标记；
- 本因子是纯距离比描述，不是盈亏比（盈亏比需入场价/失效价上下文），
  更不是未来收益 target；不生成任何交易规则。
"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from lei_signal.domain.types import Pivot
from lei_signal.features.pivots import confirmed_pivots

REASON_STRUCTURE = "structure_not_confirmed"
REASON_RANGE = "invalid_range"
REASON_CLOSE = "input_missing_close"


def swing_rr_frame(bars: pd.DataFrame, pivots: Sequence[Pivot]) -> pd.DataFrame:
    """逐日计算已确认摆动点距离比。

    返回列：value（NaN 表示不可算）、missing_reason（''=有值）。
    H_conf/L_conf 取 t 时点最近确认的摆动高/低点（按拐点 index 最新者）。
    """
    closes = bars["close"].astype(float).tolist()
    rows_value: list[float] = []
    rows_reason: list[str] = []
    for t in range(len(closes)):
        close = closes[t]
        highs = [p for p in pivots if p.kind == "high" and p.confirmed_index <= t]
        lows = [p for p in pivots if p.kind == "low" and p.confirmed_index <= t]
        if close != close:  # NaN
            rows_value.append(float("nan"))
            rows_reason.append(REASON_CLOSE)
            continue
        if not highs or not lows:
            rows_value.append(float("nan"))
            rows_reason.append(REASON_STRUCTURE)
            continue
        high = max(highs, key=lambda p: p.index).price
        low = max(lows, key=lambda p: p.index).price
        numerator = high - close
        denominator = close - low
        if numerator <= 0 or denominator <= 0:
            rows_value.append(float("nan"))
            rows_reason.append(REASON_RANGE)
            continue
        rows_value.append(numerator / denominator)
        rows_reason.append("")
    return pd.DataFrame(
        {"value": rows_value, "missing_reason": rows_reason}, index=bars.index
    )


def swing_rr_distance(bars: pd.DataFrame, pivots: Sequence[Pivot]) -> pd.Series:
    return swing_rr_frame(bars, pivots)["value"].rename("swing_rr_distance")


def swing_rr_from_bars(
    bars: pd.DataFrame, *, left: int | None = None, right: int | None = None
) -> pd.DataFrame:
    """便捷入口：先用系统既有 swing 口径确认摆动点，再逐日计算距离比。"""
    pivots = confirmed_pivots(bars, left=left, right=right)
    return swing_rr_frame(bars, pivots)
