"""宽度背离事件研究 + 策略级检验——方法层新信号族②（预注册协议）。

顶背离（主指标预注册）：价格创 60 日新高，且 B200 近 60 日最大值比其前 120 日
最大值低 ≥10pp → 背离态。激活事件 = 冷却 ≥30 日后的首个背离日。
底背离（对照报告）：价格创 60 日新低，B200 近 60 日最小值比前 120 日最小值高 ≥10pp。
灵敏度面 {60,120} 日 × {5,10,15}pp 全展示不挑选。

事件研究：背离激活后 60/120 日收益 vs 无条件基准（A股=全A等权，美股=^GSPC）。
策略级（用户要求年化+风险口径）：高·上格内背离态 → 目标仓位 ×0（离场版）或
×0.5（减半版），其余照冠军三档；对照冠军原版。通过线（预注册）：全窗超额劣化
≤1pp，且 2015 全年/2021 抱团顶/2024-26 科技牛 三窗中 ≥2 窗回撤改善 ≥5pp。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import (
    TIMING_CACHE_DIR, align_index_breadth, load_breadth, load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)


def top_divergence(close: pd.Series, b200: pd.Series, w: int = 60, ref: int = 120,
                   gap: float = 10.0) -> pd.Series:
    px_high = close >= close.rolling(w).max()
    b_recent = b200.rolling(w).max()
    b_prior = b200.rolling(ref).max().shift(w)
    return (px_high & (b_recent < b_prior - gap)).fillna(False)


def bottom_divergence(close: pd.Series, b200: pd.Series, w: int = 60, ref: int = 120,
                      gap: float = 10.0) -> pd.Series:
    px_low = close <= close.rolling(w).min()
    b_recent = b200.rolling(w).min()
    b_prior = b200.rolling(ref).min().shift(w)
    return (px_low & (b_recent > b_prior + gap)).fillna(False)


def activations(state: pd.Series, cooldown: int = 30) -> pd.Series:
    """冷却后的首次激活日。"""
    act = []
    last = -10**9
    for i, ok in enumerate(state.values):
        if ok and i - last > cooldown:
            act.append(i)
            last = i
    s = set(act)
    return pd.Series([i in s for i in range(len(state))], index=state.index)


def fwd(px: pd.Series, days: int) -> pd.Series:
    f = px.shift(-days) / px - 1
    return f.where(f.notna())


def event_study(label: str, close: pd.Series, b200: pd.Series, px_eval: pd.Series) -> None:
    both = pd.concat([close.rename("c"), b200.rename("b")], axis=1, join="inner").dropna()
    close, b200 = both["c"], both["b"]
    px_eval = px_eval.reindex(close.index).ffill()
    print(f"\n=== 事件研究 {label} {close.index[0].date()}→{close.index[-1].date()} ===")
    for name, fn in [("顶背离", top_divergence), ("底背离", bottom_divergence)]:
        act = activations(fn(close, b200))
        n = int(act.sum())
        r60, r120 = fwd(px_eval, 60)[act], fwd(px_eval, 120)[act]
        base120 = fwd(px_eval, 120)
        if n == 0:
            print(f"  [{name}] 无事件")
            continue
        dates = ", ".join(d.strftime("%Y-%m-%d") for d in close.index[act.values])
        print(
            f"  [{name}] {n} 个: {dates}\n"
            f"    后60日中位 {r60.median():+.1%} 正占比 {(r60 > 0).mean():.0%} | "
            f"后120日中位 {r120.median():+.1%} 正占比 {(r120 > 0).mean():.0%} "
            f"(无条件120日中位 {base120.median():+.1%})"
        )
    # 灵敏度面（顶背离）
    print("  顶背离灵敏度（事件数/后120日中位）:")
    for w in (60, 120):
        row = []
        for gap in (5.0, 10.0, 15.0):
            a = activations(top_divergence(close, b200, w=w, gap=gap))
            r = fwd(px_eval, 120)[a]
            row.append(f"gap{gap:.0f}: {int(a.sum())}个/{r.median():+.0%}" if len(r) else f"gap{gap:.0f}: 0")
        print(f"    w={w}  " + "  ".join(row))


def strategy_test(symbol: str, name: str) -> None:
    bars = load_index_bars(symbol)
    aligned = align_index_breadth(bars, load_breadth("cn_all"))
    base = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
    div = top_divergence(aligned["close"], aligned["b200"])
    ma200 = aligned["close"].rolling(200).mean()
    hi_zone = (aligned["b200"] >= 56.7) & (aligned["close"] >= ma200)
    variants = [
        ("冠军", base),
        ("冠军+背离离场", base.where(~(hi_zone & div), 0.0)),
        ("冠军+背离减半", base.where(~(hi_zone & div), base * 0.5)),
    ]
    half = len(aligned) // 2
    wins = [
        ("全窗", aligned), ("前半", aligned.iloc[:half]), ("后半", aligned.iloc[half:]),
        ("2015疯牛股灾", aligned.loc["2015-01-01":"2015-12-31"]),
        ("2021抱团顶", aligned.loc["2020-06-01":"2021-12-31"]),
        ("本轮科技牛", aligned.loc["2024-09-20":]),
    ]
    print(f"\n=== 策略检验 {name}({symbol}) {aligned.index[0].date()}→{aligned.index[-1].date()} ===")
    for wtag, win in wins:
        parts = []
        for vtag, tgt in variants:
            res = simulate(win, tgt.loc[win.index], fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
            m = summarize_run(res.daily, res.trades)
            parts.append(f"{vtag}:超额{m['excess_cagr']:+.1%}/回撤{m['strategy_mdd']:.0%}")
        print(f"  [{wtag}] " + " | ".join(parts))


def main() -> None:
    # 事件研究：A股用全A等权+全A宽度；美股用 ^GSPC+SP500宽度
    wide = pd.read_parquet(TIMING_CACHE_DIR.parent / "a_share_klines_full.parquet")
    ew = (1 + wide.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0)).cumprod()
    cn = load_breadth("cn_all")
    event_study("A股·全A等权×全A宽度", ew, cn["b200"], ew)
    us = load_breadth("sp500")
    gspc = load_index_bars("^GSPC")["close"]
    both_us = pd.concat([gspc, us["b200"]], axis=1, join="inner").dropna()
    event_study("美股·^GSPC×SP500宽度", both_us.iloc[:, 0], both_us.iloc[:, 1], both_us.iloc[:, 0])
    # 策略级：A股代表性标的
    for symbol, name in [("399006", "创业板指"), ("000300", "沪深300"),
                         ("399997", "中证白酒"), ("980017", "国证芯片")]:
        strategy_test(symbol, name)


if __name__ == "__main__":
    main()
