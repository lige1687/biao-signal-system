"""多因子入池 × 宽度预算——用户修正方向：不能单看 RS，要结合因子（预注册）。

结构：总仓位 = B200 三档预算（43.3/56.7 线，与冠军同源）× 月度因子选股 Top5 等权。
因子（月末可当时计算，rank 合成 0-1 等权平均）：
  动量=120日收益 | RS=动量−全A等权 | 趋势=收盘>MA200 | 低波=60日波动(反向)
  | 回撤纪律=距250日高点距离(越近越好)
变体（预注册，不挑选）：
  M1 预算×动量族(动量+RS+趋势) | M2 预算×质量族(趋势+低波+回撤)
  M3 预算×全因子 | M0 预算×全池等权（关键对照：选股有无增量）
基准：静态8冠军组合 | 全池持有（无预算）。
通过线：任一 M 变体年化 > M0 +2pp 且 ≥ 静态8冠军（共同窗口）——选股要有真增量。
费用：月度换手×10bp（预算变动不计费，保守低估冠军侧费用，结论偏保守）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import (
    INSTRUMENTS,
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

EXCLUDED = {"159819", "980017", "510500", "000932", "518880", "^GSPC", "^IXIC", "SPY", "QQQ"}
LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
STATIC8 = ["399006", "399975", "399976", "399997", "000819", "399986", "980030", "000300"]
FEE = 0.001
K = 5


def perf(eq: pd.Series) -> str:
    p = compute_performance(eq)
    return f"年化{p['cagr']:+6.1%}/回撤{p['mdd']:5.0%}/Calmar{p['calmar']:5.2f}"


def factors(closes: dict[str, pd.Series], master: pd.Index, ew: pd.Series) -> dict[str, pd.DataFrame]:
    px = pd.DataFrame({s: c.reindex(master).ffill() for s, c in closes.items()})
    ewmom = ew / ew.shift(120)
    mom = px / px.shift(120) - 1
    out = {
        "mom": mom,
        "rs": mom.sub(ewmom, axis=0),
        "trend": (px > px.rolling(200).mean()).astype(float),
        "lowvol": -px.pct_change().rolling(60).std() * np.sqrt(252),
        "dd": px / px.rolling(250).max(),
    }
    return out


def score(fac: dict[str, pd.DataFrame], names: list[str], d) -> pd.Series | None:
    ranks = {}
    for fname in names:
        row = fac[fname].loc[d].dropna()
        if row.empty:
            return None
        ranks[fname] = row.rank(pct=True)
    sc = sum(ranks.values()) / len(ranks)
    return sc


def run_variant(fac, closes, master, budget, ew, pick_names, all_pool=False):
    rets = pd.DataFrame(
        {s: c.reindex(master).ffill().pct_change().fillna(0) for s, c in closes.items()}
    )
    month_ends = master.to_series().groupby(master.to_period("M")).tail(1)
    w = pd.DataFrame(0.0, index=master, columns=rets.columns)
    turnover = pd.Series(0.0, index=master)
    held: list[str] = []
    for d in month_ends:
        i = master.get_loc(d)
        if i + 1 >= len(master):
            break
        elig = [s for s in rets.columns if len(closes[s].loc[:d].dropna()) >= 250]
        if not elig:
            continue
        if all_pool:
            pick = elig
        else:
            sc = score(fac, pick_names, d)
            if sc is None:
                continue
            sc = sc.loc[[s for s in elig if s in sc.index]]
            pick = list(sc.sort_values(ascending=False).index[:K])
        w_old = pd.Series(0.0, index=w.columns)
        if held:
            w_old[held] = 1.0 / len(held)
        w_new = pd.Series(0.0, index=w.columns)
        if pick:
            w_new[pick] = 1.0 / len(pick)
        nxt = master[i + 1]
        w.loc[nxt:] = w_new.values
        turnover.loc[nxt] = float((w_new - w_old).abs().sum())
        held = pick
    gross = (w.shift(1).fillna(0.0) * rets).sum(axis=1) * budget.shift(1).fillna(0.0)
    net = gross - turnover.shift(1).fillna(0.0) * FEE * budget.shift(1).fillna(0.0)
    return (1 + net).cumprod()


def main() -> None:
    wide = pd.read_parquet(TIMING_CACHE_DIR.parent / "a_share_klines_full.parquet")
    ew = (1 + wide.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0)).cumprod()
    closes = {}
    for sym, spec in INSTRUMENTS.items():
        if sym in EXCLUDED or spec.market != "cn":
            continue
        try:
            closes[sym] = load_index_bars(sym)["close"]
        except Exception:  # noqa: BLE001
            continue
    master = ew.index
    fac = factors(closes, master, ew)
    b200 = load_breadth("cn_all")["b200"].reindex(master)
    budget = pd.Series(np.select([b200 < 43.3, b200 >= 56.7], [1.0, 0.0], default=0.5),
                       index=master)

    eqs = {
        "M1·动量族": run_variant(fac, closes, master, budget, ew, ["mom", "rs", "trend"]),
        "M2·质量族": run_variant(fac, closes, master, budget, ew, ["trend", "lowvol", "dd"]),
        "M3·全因子": run_variant(fac, closes, master, budget, ew,
                                 ["mom", "rs", "trend", "lowvol", "dd"]),
        "M0·全池+预算(对照)": run_variant(fac, closes, master, budget, ew, [], all_pool=True),
        "全池持有(无预算)": run_variant(fac, closes, master, pd.Series(1.0, index=master),
                                      ew, [], all_pool=True),
    }
    # 静态8冠军基准
    champ_r = []
    for sym in STATIC8:
        aligned = align_index_breadth(load_index_bars(sym), load_breadth("cn_all"))
        tgt = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        res = simulate(aligned, tgt, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
        champ_r.append(res.daily["equity"].pct_change().fillna(0))
    eqs["静态8·冠军"] = (1 + pd.concat(champ_r, axis=1).mean(axis=1)).cumprod()

    wins = [("起点2013-01", "2013-01-01", None), ("共同窗口2015-06", "2015-06-16", None),
            ("2015股灾", "2015-06-01", "2016-02-29"), ("2018阴跌", "2018-01-01", "2019-01-31"),
            ("本轮科技牛", "2024-09-20", None)]
    print(f"股票池 {len(closes)} 只 | K={K} | 预算=B200三档(43.3/56.7)")
    for wtag, s, e in wins:
        print(f"\n[{wtag}]")
        for name, eq in eqs.items():
            seg = eq.loc[s:e].dropna()
            seg = seg / seg.iloc[0]
            print(f"  {name:<16} {perf(seg)}")


if __name__ == "__main__":
    main()
