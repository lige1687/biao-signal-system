"""组合变体小扫（预注册三变体，2026-08-28）：

V1 沪深300 sleeve 换攻守兼备配置（修第19轮已知拖累项——300三档不达标，正确配置为反转版）
V2 2021+ 全配置组合：17 个执行配置（含 ETF 新贵）等权 vs 同池持有，2021-01 起
V3 月度再平衡 vs 逐日等权（冠军组合口径，费用后）
基准：第19轮静态8冠军组合（逐日等权）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import align_index_breadth, load_breadth, load_index_bars
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance
from lei_signal.timing_backtest.service import EXEC_CONFIGS
from lei_signal.timing_backtest.strategies import (
    LadderParams,
    ReversalParams,
    TrendGate,
    build_target,
)

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
STATIC8 = ["399006", "399975", "399976", "399997", "000819", "399986", "980030", "000300"]
HS300_DEFENSE = ReversalParams(
    indicator="b200", low_extreme=10.0, high_extreme=90.0, confirm=5.0,
    batch_mode="band", batches=8, batch_ratio=0.6, sell_batches=1,
)


def perf(eq: pd.Series) -> str:
    p = compute_performance(eq)
    return f"年化{p['cagr']:+6.1%}/回撤{p['mdd']:5.0%}/Calmar{p['calmar']:5.2f}"


def sleeve_returns(symbol: str, kind: str) -> pd.Series:
    aligned = align_index_breadth(load_index_bars(symbol), load_breadth("cn_all"))
    if kind == "ladder":
        tgt = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
    else:
        tgt = build_target(aligned, None, HS300_DEFENSE, TrendGate(mode="ma200"), aligned.iloc[:0])
    res = simulate(aligned, tgt, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
    return res.daily["equity"].pct_change().fillna(0)


def main() -> None:
    # 第19轮基准：静态8冠军（300 用三档）
    base_r = {s: sleeve_returns(s, "ladder") for s in STATIC8}
    eq_base = (1 + pd.DataFrame(base_r).mean(axis=1)).cumprod()

    # V1：300 换攻守
    v1_r = dict(base_r)
    v1_r["000300"] = sleeve_returns("000300", "reversal")
    eq_v1 = (1 + pd.DataFrame(v1_r).mean(axis=1)).cumprod()

    # V3：月度再平衡（每自然月内各 sleeve 复利，月末取均值再投）
    df = pd.DataFrame(base_r)
    monthly = (1 + df).resample("ME").prod() - 1

    # V2：2021+ 全 17 配置（用 EXEC_CONFIGS 原参数）vs 同池持有
    cfg_r, hold_r = {}, {}
    for cfg in EXEC_CONFIGS:
        p = cfg["params"]
        sym = p["symbol"]
        breadth = None if sym in ("SPY", "QQQ") else "cn_all"
        try:
            bars = load_index_bars(sym)
            br = load_breadth("sp500" if breadth is None else "cn_all")
            aligned = align_index_breadth(bars, br)
        except Exception:  # noqa: BLE001
            continue
        if p["strategy"] == "ladder":
            lp = LadderParams(
                indicator=p["indicator"], n_bands=int(p["n_bands"]), edge_mode="fixed",
                direction=p["direction"], min_weight=0.0, gamma=float(p.get("gamma", 1.0)),
                low_edge=float(p.get("low_edge", 0.0)), high_edge=float(p.get("high_edge", 100.0)),
            )
            tgt = build_target(aligned, lp, None, TrendGate(), aligned.iloc[:0])
        else:
            rp = ReversalParams(
                indicator=p["indicator"], low_extreme=float(p["low_extreme"]),
                high_extreme=float(p["high_extreme"]), confirm=float(p["confirm"]),
                batch_mode=p["batch_mode"], batches=int(p["batches"]),
                batch_ratio=float(p["batch_ratio"]), sell_batches=p.get("sell_batches"),
            )
            tgt = build_target(aligned, None, rp, TrendGate(), aligned.iloc[:0])
        fee = float(p.get("fee_bps", 10.0))
        res = simulate(aligned, tgt, fee_bps=fee, cash_rate=0.0, min_trade=0.05)
        cfg_r[sym] = res.daily["equity"].pct_change().fillna(0)
        res_h = simulate(aligned, pd.Series(1.0, index=aligned.index), fee_bps=fee,
                         cash_rate=0.0, min_trade=0.05)
        hold_r[sym] = res_h.daily["equity"].pct_change().fillna(0)
    s21 = pd.Timestamp("2021-01-01")
    eq_v2 = (1 + pd.DataFrame(cfg_r).loc[s21:].mean(axis=1)).cumprod()
    eq_v2h = (1 + pd.DataFrame(hold_r).loc[s21:].mean(axis=1)).cumprod()

    print("=== V1: 沪深300 sleeve 三档 → 攻守兼备（共同窗口 2015-06→） ===")
    for name, eq in [("静态8冠军(300三档)", eq_base), ("V1(300攻守)", eq_v1)]:
        seg = eq.loc["2015-06-16":]
        print(f"  {name:<18} {perf(seg / seg.iloc[0])}")
    print("\n=== V3: 再平衡频率（共同窗口 2015-06→，月度≈费后近似） ===")
    seg = eq_base.loc["2015-06-16":]
    print(f"  {'逐日等权':<18} {perf(seg / seg.iloc[0])}")
    # 月度序列对齐窗口（按 12 期/年 年化）
    m = monthly.loc["2015-06":].mean(axis=1)
    eqm = (1 + m).cumprod()
    cagr = float(eqm.iloc[-1] ** (12 / len(eqm)) - 1)
    mdd = float((eqm / eqm.cummax() - 1).min())
    print(f"  {'月度再平衡':<18} 年化{cagr:+6.1%}/回撤{mdd:5.0%}")
    print("\n=== V2: 2021-01→ 17执行配置等权 vs 同池持有 ===")
    for name, eq in [("全配置·策略", eq_v2), ("全配置·持有", eq_v2h)]:
        print(f"  {name:<18} {perf(eq)}")
    seg8 = eq_base.loc["2021-01-01":]
    print(f"\n（对照）静态8冠军 2021-01→ : {perf(seg8 / seg8.iloc[0])}")


if __name__ == "__main__":
    main()
