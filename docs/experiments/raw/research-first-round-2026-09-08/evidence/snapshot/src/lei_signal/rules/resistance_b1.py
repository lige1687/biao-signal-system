"""B1 第一阻力。

B1 = 信号发生前**已经确认**、过去两年内、时间上最近、
     价格高于当时收盘价的摆动高点。

修复 7：B1 默认窗口 = 真实过去两年（lookback_years=2，≈ 730 自然日），
        不再使用 504 个自然日。规则配置、代码、界面、测试保持一致。

B1 是第一阻力，不是强制止盈目标，也不是 3R 入场门槛。
B1 不存在仍允许产生信号（门禁 10）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Pivot
from lei_signal.features.pivots import swing_highs


@dataclass(frozen=True, slots=True)
class B1Resistance:
    """第一阻力位。"""

    price: float
    pivot_date: date
    available_date: date
    distance_pct: float
    distance_r: float | None = None   # 只有存在 C 时才有意义

    @property
    def label_cn(self) -> str:
        return f"B1第一阻力 {self.price:.4f}（{self.pivot_date}确认于{self.available_date}）"


def _lookback_days() -> int:
    """根据配置的真实年限返回自然日数量。"""
    spec = get_rule("resistance_b1")
    years = float(spec.param("lookback_years", 2))
    return int(round(365.25 * years))


def find_b1(
    pivots: tuple[Pivot, ...],
    *,
    as_of: date,
    current_close: float,
    c_price: float | None = None,
    lookback_days: int | None = None,
) -> B1Resistance | None:
    """寻找 B1。返回 None 表示不存在——这**不**阻止信号产生。

    严格性：只使用 available_date <= as_of 的摆动高点，
    即信号发生时已经确认的高点，不使用尚未确认的拐点。
    """
    window = _lookback_days() if lookback_days is None else lookback_days
    earliest = as_of - timedelta(days=window)

    candidates = [
        pivot
        for pivot in swing_highs(pivots)
        if pivot.available_date <= as_of          # 当时已确认
        and pivot.pivot_date >= earliest          # 窗口内
        and pivot.price > current_close           # 高于当时收盘价
    ]
    if not candidates:
        return None

    # 时间上最近（先按 pivot_date，再按 index 解决同日并列）
    nearest = max(candidates, key=lambda p: (p.pivot_date, p.index))
    distance_pct = (nearest.price - current_close) / current_close * 100.0
    distance_r: float | None = None
    if c_price is not None and current_close > c_price:
        risk = current_close - c_price
        if risk > 0:
            distance_r = (nearest.price - current_close) / risk

    return B1Resistance(
        price=float(nearest.price),
        pivot_date=nearest.pivot_date,
        available_date=nearest.available_date,
        distance_pct=float(distance_pct),
        distance_r=distance_r,
    )


def b1_series(
    frame: pd.DataFrame,
    pivots: tuple[Pivot, ...],
    *,
    lookback_days: int | None = None,
) -> pd.DataFrame:
    """逐日 B1，用于研究层统计到达率与突破后延伸。"""
    rows: list[dict[str, object]] = []
    for timestamp, row in frame.iterrows():
        as_of = timestamp.date()
        b1 = find_b1(
            pivots,
            as_of=as_of,
            current_close=float(row["close"]),
            lookback_days=lookback_days,
        )
        rows.append(
            {
                "date": timestamp,
                "b1_price": b1.price if b1 else None,
                "b1_pivot_date": b1.pivot_date if b1 else None,
                "b1_available_date": b1.available_date if b1 else None,
                "distance_to_b1_pct": b1.distance_pct if b1 else None,
            }
        )
    result = pd.DataFrame(rows).set_index("date")
    result.index.name = "date"
    return result


__all__ = ["B1Resistance", "b1_series", "find_b1"]
