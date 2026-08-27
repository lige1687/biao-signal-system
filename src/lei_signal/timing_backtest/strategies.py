"""宽度择时策略：阶梯 / 极值反转 / 趋势闸门 / 波动率目标 → 逐日目标仓位（0-1）。

纯函数，只用当日及以前的数据（T 日收盘值 → T+1 开盘由引擎执行）。
资金管理维度：批次比例（金字塔/等分/递增）、买卖分批独立、档位步长、
阶梯陡度 gamma、档位边界收缩（low/high edge）、底仓、波动率目标。
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
    min_weight: float = 0.0  # 底仓：档位仓位线性压缩到 [min_weight, 1]
    gamma: float = 1.0  # 陡度：>1 仅深极值才重仓（深价值），<1 浅极值就重仓（早重仓）
    low_edge: float = 0.0  # 档位边界下沿（满仓侧），如 15
    high_edge: float = 100.0  # 档位边界上沿（空仓侧），如 85


@dataclass(frozen=True)
class ReversalParams:
    indicator: str = "b200"
    low_extreme: float = 20.0
    high_extreme: float = 80.0
    confirm: float = 5.0
    batch_mode: str = "time"  # time | band
    batches: int = 5
    batch_ratio: float = 1.0  # 相邻批次资金比：>1 首批重（金字塔），<1 递增（越跌买越多）
    band_step: float = 10.0  # band 模式每批之间的宽度点数
    sell_batches: int | None = None  # 卖出分批数（None=同买入）
    sell_ratio: float | None = None  # 卖出批次资金比（None=同买入）


@dataclass(frozen=True)
class TrendGate:
    mode: str = "off"  # off | ma200
    cap: float = 0.0  # 指数 < MA200 时的仓位上限


def _fixed_edges(n_bands: int, low_edge: float = 0.0, high_edge: float = 100.0) -> np.ndarray:
    span = np.linspace(0.0, 1.0, n_bands + 1)[1:-1]
    return float(low_edge) + (float(high_edge) - float(low_edge)) * span


def ladder_target(
    b: pd.Series, params: LadderParams, warmup_b: pd.Series | None = None
) -> pd.Series:
    """B 值阶梯映射目标仓位：contrarian 低宽度高仓位；档边界值归属上一档（side=right）。"""
    n = max(2, int(params.n_bands))
    edges = _fixed_edges(n, params.low_edge, params.high_edge)
    if params.edge_mode == "preq":
        obs = None if warmup_b is None else warmup_b.dropna()
        if obs is not None and len(obs) >= _PREQ_MIN_OBS:
            edges = np.asarray(obs.quantile(list(edges / 100.0)), dtype=float)
    if params.direction == "contrarian":
        levels = np.linspace(1.0, 0.0, n)
    else:
        levels = np.linspace(0.0, 1.0, n)
    gamma = float(params.gamma) if params.gamma and params.gamma > 0 else 1.0
    levels = levels ** gamma
    floor = float(np.clip(params.min_weight, 0.0, 1.0))
    levels = floor + (1.0 - floor) * levels  # 底仓压缩：空仓档位也保留 min_weight
    idx_pos = np.searchsorted(edges, b.to_numpy(dtype=float), side="right")
    return pd.Series(levels[idx_pos], index=b.index)


def _batch_weights(n: int, ratio: float) -> np.ndarray:
    """N 个批次的资金权重（和为 1）：ratio>1 首批重（金字塔），<1 递增（越跌买越多）。"""
    exps = np.arange(max(1, n) - 1, -1, -1, dtype=float)  # 首批指数最大
    w = np.power(float(ratio), exps)
    return w / w.sum()


def reversal_target(b: pd.Series, params: ReversalParams) -> pd.Series:
    """极值反转分批：跌破下极值后回升确认 → 按批次权重分批买入；上极值回落确认 → 分批卖出。

    - time 模式每日一批、band 模式每 band_step 个宽度点一批；触发当日即第一批
    - 买卖批次独立（sell_batches/sell_ratio，None=沿用买入侧）
    - armed 触发即消费；B 冲上上极值取消进行中的买入程序（顶部不再加仓）；
      B 崩至下极值不取消卖出程序（崩跌中继续减仓），只武装新一轮买入
    """
    vals = b.to_numpy(dtype=float)
    buy_w = _batch_weights(int(params.batches), params.batch_ratio)
    sell_n = int(params.sell_batches) if params.sell_batches else int(params.batches)
    sell_r = params.sell_ratio if params.sell_ratio is not None else params.batch_ratio
    sell_w = _batch_weights(sell_n, sell_r)
    step = max(1.0, float(params.band_step))

    target, prog, anchor = 0.0, 0, 0.0
    armed_low = armed_high = False
    direction = 0  # +1 买入程序 / -1 卖出程序 / 0 空闲
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
            direction, anchor, prog, armed_low = 1, x, 0, False
        elif armed_high and direction != -1 and x <= params.high_extreme - params.confirm:
            direction, anchor, prog, armed_high = -1, x, 0, False
        if direction == 1:
            if prog == 0:  # 触发当日即第一批
                target = min(1.0, target + buy_w[0])
                prog, anchor = 1, x
            elif params.batch_mode == "time":
                target = min(1.0, target + buy_w[prog])
                prog += 1
            else:
                while (x - anchor) >= step and prog < len(buy_w):
                    target = min(1.0, target + buy_w[prog])
                    prog += 1
                    anchor += step
            if prog >= len(buy_w):
                direction = 0
        elif direction == -1:
            if prog == 0:
                target = max(0.0, target - sell_w[0])
                prog, anchor = 1, x
            elif params.batch_mode == "time":
                target = max(0.0, target - sell_w[prog])
                prog += 1
            else:
                while (anchor - x) >= step and prog < len(sell_w):
                    target = max(0.0, target - sell_w[prog])
                    prog += 1
                    anchor -= step
            if prog >= len(sell_w):
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


def apply_vol_target(
    close: pd.Series, target: pd.Series, vol_target: float, window: int = 20
) -> pd.Series:
    """波动率目标：按截至当日的已实现年化波动把仓位缩到 vol_target（只减不加）。"""
    if vol_target <= 0:
        return target
    ret = close.pct_change()
    realized = ret.rolling(window, min_periods=window).std() * np.sqrt(252.0)
    scale = (vol_target / realized).clip(upper=1.0)
    out = target * scale.fillna(1.0)
    return pd.Series(np.clip(out.to_numpy(), 0.0, 1.0), index=target.index)


def build_target(
    aligned: pd.DataFrame,
    ladder: LadderParams | None,
    reversal: ReversalParams | None,
    gate: TrendGate,
    warmup: pd.DataFrame | None,
    vol_target: float = 0.0,
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
    target = apply_gate(target, trend_gate_cap(aligned["close"], gate))
    return apply_vol_target(aligned["close"], target, vol_target)
