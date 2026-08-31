"""美股宽指十年表 + 美股个股×宽度预算（用户方向：美股也做，宽指+个股）。

个股数据：yfinance auto_adjust（真复权，避开 sp500_klines 的拆股假摔），
12 只代表性大盘股（成长/科技/周期/防御）。缓存 ~/.lei_signal_lab/cache/timing/US_*.parquet。
预算变体：A 持有 | B 逆势三档(30/70) | C 顺势三档 | D 防守版(顺势+MA200闸+vol_target 0.15)。
宽度用现有 SP500 宽度（⚠ 未复权口径噪声入册，修复排队）。
评估线（预注册）：D 版若回撤较持有减 ≥1/3 且年化损失 ≤2pp → 个股仓位参考可用；
B 版在美股动量市场的预期=重伤（复核）。
指数十年表：^GSPC/^IXIC × {冠军/顺势/防守} 分年代。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import (
    TIMING_CACHE_DIR, align_index_breadth, load_breadth, load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance, summarize_run
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

STOCKS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",
          "TSLA", "JPM", "XOM", "JNJ", "PG", "KO"]


def fetch_yf(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    hist = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    hist.index = pd.to_datetime(hist.index).tz_localize(None)
    return hist[["Open", "High", "Low", "Close"]].astype(float).rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"}
    )


def ensure_stock(ticker: str) -> pd.DataFrame | None:
    path = TIMING_CACHE_DIR / f"US_{ticker}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    try:
        df = fetch_yf(ticker)
        df.to_parquet(path)
        return df
    except Exception as e:  # noqa: BLE001
        print(f"!! {ticker} 拉取失败: {e}")
        return None


def variants_target(aligned: pd.DataFrame) -> dict[str, pd.Series]:
    contra = build_target(
        aligned, LadderParams(indicator="b200", n_bands=3, edge_mode="fixed",
                              direction="contrarian", min_weight=0.0, gamma=1.0,
                              low_edge=30.0, high_edge=70.0),
        None, TrendGate(), aligned.iloc[:0],
    )
    mom = LadderParams(indicator="b200", n_bands=3, edge_mode="fixed",
                       direction="momentum", min_weight=0.0, gamma=1.0,
                       low_edge=30.0, high_edge=70.0)
    plain = build_target(aligned, mom, None, TrendGate(), aligned.iloc[:0])
    defense = build_target(
        aligned, mom, None, TrendGate(mode="ma200"), aligned.iloc[:0], vol_target=0.15
    )
    return {"B逆势": contra, "C顺势": plain, "D防守": defense}


def main() -> None:
    us = load_breadth("sp500")

    # ── 指数十年表 ──
    print("=== 美股宽指 × 组合 × 年代（年化/回撤，对照持有）===")
    for symbol, name in [("^GSPC", "标普500"), ("^IXIC", "纳指")]:
        bars = load_index_bars(symbol)
        aligned = align_index_breadth(bars, us)
        tv = variants_target(aligned)
        decades = [("1986-1995", "1986-01-01", "1995-12-31"),
                   ("1996-2005", "1996-01-01", "2005-12-31"),
                   ("2006-2015", "2006-01-01", "2015-12-31"),
                   ("2016-2026", "2016-01-01", None)]
        print(f"\n[{name}]")
        for dtag, s, e in decades:
            seg = aligned.loc[s:e]
            if len(seg) < 250:
                continue
            hold = compute_performance(seg["close"] / seg["close"].iloc[0])
            line = [f"持有 {hold['cagr']:+.1%}/{hold['mdd']:.0%}"]
            for vtag, tgt in tv.items():
                res = simulate(seg, tgt.loc[seg.index], fee_bps=10.0, cash_rate=0.0,
                               min_trade=0.05)
                m = summarize_run(res.daily, res.trades)
                line.append(f"{vtag} {m['strategy_cagr']:+.1%}/{m['strategy_mdd']:.0%}")
            print(f"  [{dtag}] " + " | ".join(line))

    # ── 个股 ──
    print("\n=== 美股个股 × 宽度预算（复权价，全历史→2026-08-14）===")
    rows = []
    for ticker in STOCKS:
        bars = ensure_stock(ticker)
        if bars is None:
            continue
        aligned = align_index_breadth(bars, us)
        if len(aligned) < 500:
            continue
        tv = variants_target(aligned)
        hold_p = compute_performance(aligned["close"] / aligned["close"].iloc[0])
        row = {"股票": ticker, "持有": f"{hold_p['cagr']:+.0%}/{hold_p['mdd']:.0%}"}
        for vtag, tgt in tv.items():
            res = simulate(aligned, tgt, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
            m = summarize_run(res.daily, res.trades)
            row[vtag] = f"{m['strategy_cagr']:+.0%}/{m['strategy_mdd']:.0%}"
            row[f"{vtag}_cagr"] = m["strategy_cagr"] - hold_p["cagr"]
        rows.append(row)
    df = pd.DataFrame(rows)
    cols = ["股票", "持有", "B逆势", "C顺势", "D防守"]
    print(df[cols].to_string(index=False))
    for v in ("B逆势", "C顺势", "D防守"):
        print(f"{v} 平均超额(年化): {df[f'{v}_cagr'].mean():+.1%}")

    # 关键窗口：2022 熊 + 2020 疫情崩 + 2023-26 AI牛（D 版的用武之地）
    print("\n=== 关键窗口（年化/回撤：持有 → D防守）===")
    for ticker in ["NVDA", "AAPL", "MSFT", "META", "JPM", "XOM"]:
        bars = ensure_stock(ticker)
        if bars is None:
            continue
        aligned = align_index_breadth(bars, us)
        tv = variants_target(aligned)
        for wtag, s, e in [("2020疫情", "2020-02-01", "2020-06-30"),
                           ("2022熊", "2022-01-01", "2022-12-31"),
                           ("2023-26AI牛", "2023-01-01", None)]:
            seg = aligned.loc[s:e]
            if len(seg) < 30:
                continue
            hold = compute_performance(seg["close"] / seg["close"].iloc[0])
            res = simulate(seg, tv["D防守"].loc[seg.index], fee_bps=10.0, cash_rate=0.0,
                           min_trade=0.05)
            m = summarize_run(res.daily, res.trades)
            print(
                f"  {ticker} [{wtag}] 持有 {hold['cagr']:+.0%}/{hold['mdd']:.0%}"
                f" → D防守 {m['strategy_cagr']:+.0%}/{m['strategy_mdd']:.0%}"
            )


if __name__ == "__main__":
    main()
