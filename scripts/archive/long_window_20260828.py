"""超长窗口检验——用户问「能否测 10/20 年以上」。

新增上证指数（1990-12→2026-08，35.7 年）与深证成指（1991-04→，35.3 年），
加全A等权合成序列（1990→，open=close 近似），跑冠军三档的：
全窗 / 前半 / 后半 / 四个十年段；再组「36 年渐进组合」（上证1990 起，深成/沪深300/
创业板/有色/通信/银行/新能车/证券/白酒 依次入队）等权，对比持有组合。

诚实声明（必须随结果一起读）：
- 宽度按当前存续个股回算，1990 年代幸存者偏差最重（当时仅百余只，现存回算）；
- 上证/深成为价格指数不含股息（策略与基准同口径，相对结论可参考）；
- 1990-1995 市场规模极小，结论以 2000 年后为主看。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import (
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)


def perf(eq: pd.Series) -> str:
    p = compute_performance(eq)
    return f"年化{p['cagr']:+6.1%}/回撤{p['mdd']:5.0%}/Calmar{p['calmar']:5.2f}"


def bars_of(symbol: str) -> pd.DataFrame:
    return load_index_bars(symbol)


def champion_pair(
    bars: pd.DataFrame, breadth: pd.DataFrame
) -> tuple[pd.Series, pd.Series, pd.Series]:
    aligned = align_index_breadth(bars, breadth)
    tgt = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
    res = simulate(aligned, tgt, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
    res_h = simulate(aligned, pd.Series(1.0, index=aligned.index), fee_bps=10.0,
                     cash_rate=0.0, min_trade=0.05)
    return res.daily["equity"], res_h.daily["equity"], aligned.index


def main() -> None:
    breadth = load_breadth("cn_all")
    wide = pd.read_parquet(TIMING_CACHE_DIR.parent / "a_share_klines_full.parquet")
    ew_close = (1 + wide.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0)).cumprod()
    ew_bars = pd.DataFrame(
        {"open": ew_close, "high": ew_close, "low": ew_close, "close": ew_close}
    )

    series = {}
    for name, bars in [("上证指数", bars_of("SH000001")), ("深证成指", bars_of("SZ399001")),
                       ("全A等权(合成)", ew_bars)]:
        eq, eq_h, idx = champion_pair(bars, breadth)
        series[name] = (eq, eq_h, idx)

    wins = [
        ("全窗(35年+)", None, None), ("前半(1991-2009)", None, "2009-12-31"),
        ("后半(2010-2026)", "2010-01-01", None),
        ("1991-2000", "1991-01-01", "2000-12-31"), ("2001-2010", "2001-01-01", "2010-12-31"),
        ("2011-2020", "2011-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", None),
    ]
    print("=== 冠军三档 · 超长窗口（超额=年化差）===")
    for wtag, s, e in wins:
        print(f"\n[{wtag}]")
        for name, (eq, eq_h, _idx) in series.items():
            seg = eq.loc[s:e].dropna()
            seg_h = eq_h.loc[s:e].dropna()
            if len(seg) < 250:
                print(f"  {name:<12} 样本不足")
                continue
            p, ph = compute_performance(seg), compute_performance(seg_h)
            print(
                f"  {name:<12} 策略 {p['cagr']:+6.1%}/回撤{p['mdd']:5.0%} | "
                f"持有 {ph['cagr']:+6.1%}/{ph['mdd']:5.0%} | 超额 {p['cagr'] - ph['cagr']:+6.1%}"
            )

    # 36 年渐进组合：sleeve 依次入队等权（冠军 vs 持有）
    sleeves = ["SH000001", "SZ399001", "000300", "399006", "000819", "980030",
               "399976", "399986", "399975", "399997"]
    strat_r, hold_r = [], []
    for sym in sleeves:
        eq, eq_h, _ = champion_pair(bars_of(sym), breadth)
        strat_r.append(eq.pct_change().fillna(0))
        hold_r.append(eq_h.pct_change().fillna(0))
    eq_port = (1 + pd.concat(strat_r, axis=1).mean(axis=1)).cumprod()
    eq_port_h = (1 + pd.concat(hold_r, axis=1).mean(axis=1)).cumprod()
    print("\n=== 36 年渐进组合（10 sleeve 依次入队等权，1990-12→2026-08）===")
    for label, eq in [("冠军组合", eq_port), ("持有组合", eq_port_h)]:
        seg = eq.dropna()
        print(f"  {label}: {perf(seg)}")
    # 分段
    for wtag, s, e in [("1991-2005(早期,幸存者偏差重)", "1991-01-01", "2005-12-31"),
                       ("2006-2016", "2006-01-01", "2016-12-31"),
                       ("2017-2026", "2017-01-01", None)]:
        line = [f"[{wtag}]"]
        for label, eq in [("冠军组合", eq_port), ("持有组合", eq_port_h)]:
            seg = eq.loc[s:e].dropna()
            p = compute_performance(seg)
            line.append(f"{label} {p['cagr']:+.1%}/{p['mdd']:.0%}")
        print("  " + " | ".join(line))


if __name__ == "__main__":
    main()
