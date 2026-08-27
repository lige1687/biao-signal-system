"""宽度择时策略：阶梯 / 极值反转 / 趋势闸门 → 逐日目标仓位（0-1）。

纯函数，只用当日及以前的数据（T 日收盘值 → T+1 开盘由引擎执行）。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_PREQ_MIN_OBS = 250  # preq 模式要求的回测起点前宽度观测数，不足回退固定档


@dataclass(frozen=True)
class LadderParams:
    indicator: str = "b200"
    n_bands: int = 5
    edge_mode: str = "fixed"  # fixed | preq
    direction: str = "contrarian"  # contrarian | momentum


@dataclass(frozen=True)
class ReversalParams:
    indicator: str = "b200"
    low_extreme: float = 20.0
    high_extreme: float = 80.0
    confirm: float = 5.0
    batch_mode: str = "time"  # time | band
    batches: int = 5


@dataclass(frozen=True)
class TrendGate:
    mode: str = "off"  # off | ma200
    cap: float = 0.0  # 指数 < MA200 时的仓位上限


def _fixed_edges(n_bands: int) -> np.ndarray:
    return 100.0 * np.linspace(0, 1, n_bands + 1)[1:-1]


def ladder_target(
    b: pd.Series, params: LadderParams, warmup_b: pd.Series | None = None
) -> pd.Series:
    """B 值阶梯映射目标仓位：contrarian 低宽度高仓位；档边界值归属上一档（side=right）。"""
    n = max(2, int(params.n_bands))
    edges = _fixed_edges(n)
    if params.edge_mode == "preq":
        obs = None if warmup_b is None else warmup_b.dropna()
        if obs is not None and len(obs) >= _PREQ_MIN_OBS:
            edges = np.asarray(obs.quantile(list(edges / 100.0)), dtype=float)
    if params.direction == "contrarian":
        levels = np.linspace(1.0, 0.0, n)
    else:
        levels = np.linspace(0.0, 1.0, n)
    idx_pos = np.searchsorted(edges, b.to_numpy(dtype=float), side="right")
    return pd.Series(levels[idx_pos], index=b.index)


def reversal_target(b: pd.Series, params: ReversalParams) -> pd.Series:
    """极值反转分批：跌破下极值后回升确认 → 分批买入；升破上极值后回落确认 → 分批卖出。

    - 触发当日即成交第一批；time 模式每日 ±1/N，band 模式每 ±10 宽度点 ±1/N
    - armed 触发即消费；需重新触及极值才能再武装
    - B 冲上上极值会取消进行中的买入程序（顶部不再加仓）；
      B 崩至下极值不取消卖出程序（崩跌中继续减仓），只武装新一轮买入
    """
    vals = b.to_numpy(dtype=float)
    step = 1.0 / max(1, int(params.batches))
    target = 0.0
    armed_low = armed_high = False
    direction = 0  # +1 买入程序 / -1 卖出程序 / 0 空闲
    anchor = 0.0
    out = np.zeros(len(vals))
    for i, x in enumerate(vals):
        if np.isnan(x):
            out[i] = target
            continue
        if x <= params.low_extreme:
            armed_low = True
        if x >= params.high_extreme:
            armed_high = True
            direction = 0 if direction == 1 else direction  # 顶部取消买入程序
        if armed_low and direction != 1 and x >= params.low_extreme + params.confirm:
            direction, anchor, armed_low = 1, x, False
            if params.batch_mode == "band":  # 触发当日即第一批（与 time 模式一致）
                target = min(1.0, target + step)
        elif armed_high and direction != -1 and x <= params.high_extreme - params.confirm:
            direction, anchor, armed_high = -1, x, False
            if params.batch_mode == "band":
                target = max(0.0, target - step)
        if direction == 1:
            if params.batch_mode == "time":
                target = min(1.0, target + step)
            else:
                while x - anchor >= 10.0 and target < 1.0:
                    target = min(1.0, target + step)
                    anchor += 10.0
            if target >= 1.0:
                direction = 0
        elif direction == -1:
            if params.batch_mode == "time":
                target = max(0.0, target - step)
            else:
                while anchor - x >= 10.0 and target > 0.0:
                    target = max(0.0, target - step)
                    anchor -= 10.0
            if target <= 0.0:
                direction = 0
        out[i] = target
    return pd.Series(out, index=b.index)


def trend_gate_cap(close: pd.Series, gate: TrendGate) -> pd.Series:
    """指数收盘 >= MA200 → 上限 1；否则 cap；MA200 未成型不设限。"""
    if gate.mode != "ma200":
        return pd.Series(1.0, index=close.index)
    ma = close.rolling(200, min_periods=200).mean()
    cap = np.where(ma.isna() | (close >= ma), 1.0, gate.cap)
    return pd.Series(cap, index=close.index)


def apply_gate(target: pd.Series, cap: pd.Series) -> pd.Series:
    return pd.Series(np.minimum(target.to_numpy(), cap.to_numpy()), index=target.index)


def build_target(
    aligned: pd.DataFrame,
    ladder: LadderParams | None,
    reversal: ReversalParams | None,
    gate: TrendGate,
    warmup: pd.DataFrame | None,
) -> pd.Series:
    if ladder is not None:
        warmup_b = (
            warmup[ladder.indicator]
            if warmup is not None and ladder.indicator in warmup
            else None
        )
        target = ladder_target(aligned[ladder.indicator], ladder, warmup_b)
    elif reversal is not None:
        target = reversal_target(aligned[reversal.indicator], reversal)
    else:
        raise ValueError("ladder 与 reversal 至少提供一个")
    return apply_gate(target, trend_gate_cap(aligned["close"], gate))
