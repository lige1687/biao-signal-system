"""筹码分布代理（volume_profile_proxy）。

重要限制：OHLCV 无法知道真实持仓人的成本。本模块是把成交量按价格区间
均匀分配得到的**代理**分布，界面必须写「筹码分布代理」，
不得声称是真实投资者持仓成本。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Provenance


@dataclass(frozen=True, slots=True)
class VolumeProfileProxy:
    """滚动窗口内的成交量分布代理。"""

    poc: float
    val: float
    vah: float
    overhead_supply_ratio: float
    support_density: float
    bin_edges: tuple[float, ...]
    bin_volumes: tuple[float, ...]
    window: int
    bins: int
    value_area: float
    current_price: float
    provenance: Provenance = Provenance.RESEARCH_PROXY
    label_cn: str = "筹码分布代理"

    @property
    def tags(self) -> tuple[str, ...]:
        """标签：靠近代理支撑 / 上方代理套牢较重 / 突破代理密集区。"""
        result: list[str] = []
        if self.support_density >= 0.15:
            result.append("near_volume_support")
        if self.overhead_supply_ratio >= 0.40:
            result.append("heavy_overhead_supply")
        if self.current_price > self.vah:
            result.append("profile_breakout")
        return tuple(result)


def compute_volume_profile(
    bars: pd.DataFrame,
    *,
    window: int | None = None,
    bins: int | None = None,
    value_area: float | None = None,
    support_zone_pct: float | None = None,
) -> VolumeProfileProxy | None:
    """在最近 window 根 K 线内建立成交量分布代理。

    分配方式：每根 K 线的成交量在其 low..high 覆盖的价格箱内均匀分摊。
    这是代理假设——真实成交价分布未知。
    """
    spec = get_rule("volume_profile_proxy")
    window = int(spec.param("window", 120)) if window is None else window
    bins = int(spec.param("bins", 50)) if bins is None else bins
    value_area = float(spec.param("value_area", 0.70)) if value_area is None else value_area
    support_zone_pct = (
        float(spec.param("support_zone_pct", 0.05))
        if support_zone_pct is None
        else support_zone_pct
    )

    if len(bars) < 2 or bins < 2:
        return None

    recent = bars.tail(window)
    low = float(recent["low"].min())
    high = float(recent["high"].max())
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return None

    edges = np.linspace(low, high, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    volumes = np.zeros(bins, dtype=float)

    bar_lows = recent["low"].astype(float).to_numpy()
    bar_highs = recent["high"].astype(float).to_numpy()
    bar_volumes = recent["volume"].astype(float).to_numpy()

    for bar_low, bar_high, bar_volume in zip(bar_lows, bar_highs, bar_volumes, strict=True):
        if bar_volume <= 0:
            continue
        # 找出该 K 线覆盖的箱区间，把成交量按覆盖箱数均分。
        start = int(np.searchsorted(edges, bar_low, side="right") - 1)
        end = int(np.searchsorted(edges, bar_high, side="left"))
        start = max(0, min(start, bins - 1))
        end = max(start + 1, min(end, bins))
        covered = end - start
        volumes[start:end] += bar_volume / covered

    total = volumes.sum()
    if total <= 0:
        return None

    poc_index = int(np.argmax(volumes))
    poc = float(centers[poc_index])

    # 价值区：从 POC 向两侧扩展，直到覆盖 value_area 比例的代理量。
    included = {poc_index}
    covered_volume = volumes[poc_index]
    lower, upper = poc_index - 1, poc_index + 1
    target = total * value_area
    while covered_volume < target and (lower >= 0 or upper < bins):
        lower_volume = volumes[lower] if lower >= 0 else -1.0
        upper_volume = volumes[upper] if upper < bins else -1.0
        if upper_volume > lower_volume:
            included.add(upper)
            covered_volume += upper_volume
            upper += 1
        else:
            included.add(lower)
            covered_volume += lower_volume
            lower -= 1
    val = float(edges[min(included)])
    vah = float(edges[max(included) + 1])

    current_price = float(bars["close"].iloc[-1])
    above_mask = centers > current_price
    overhead_supply_ratio = float(volumes[above_mask].sum() / total)

    support_low = current_price * (1.0 - support_zone_pct)
    support_mask = (centers >= support_low) & (centers <= current_price)
    support_density = float(volumes[support_mask].sum() / total)

    return VolumeProfileProxy(
        poc=poc,
        val=val,
        vah=vah,
        overhead_supply_ratio=overhead_supply_ratio,
        support_density=support_density,
        bin_edges=tuple(float(value) for value in edges),
        bin_volumes=tuple(float(value) for value in volumes),
        window=window,
        bins=bins,
        value_area=value_area,
        current_price=current_price,
    )


__all__ = ["VolumeProfileProxy", "compute_volume_profile"]
