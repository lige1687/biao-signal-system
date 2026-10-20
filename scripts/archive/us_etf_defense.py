"""美股 ETF × 宽度防守版——用户指令：别测个股了，测 ETF。

标的：宽基/行业/商品 ETF 共 19 只（yfinance 复权 OHLCV，走本机代理入美股池）。
GLD 为阴性对照（与 SP500 宽度无耦合，方法有效性检验）。
变体（预注册）：持有 | 防守A（40/80 边界 vol0.15 gamma1.5） | 防守B（30/70 vol0.10
gamma1.5，A 股原始边界对照）。宽度 = SP500 复权宽度。
通过线（预注册）：全窗回撤 ≤ 持有的 50% 且全窗年化 ≥ 持有 −3pp 且后半窗年化 ≥ 持有 −3pp。
窗口：全窗 / 前半 / 后半 / 2008 / 2022。费用 10bp。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import align_index_breadth, load_breadth
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance, summarize_run
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

ETFS = [
    ("SPY", "宽基标普"), ("QQQ", "宽基纳指"), ("DIA", "宽基道指"), ("IWM", "小盘罗素"),
    ("XLK", "科技"), ("XLE", "能源"), ("XLF", "金融"), ("XLV", "医疗"),
    ("XLY", "可选消费"), ("XLP", "必选消费"), ("XLI", "工业"), ("XLB", "材料"),
    ("XLRE", "地产"), ("XLU", "公用"), ("SMH", "半导体"), ("XBI", "生物科技"),
    ("EFA", "发达市场"), ("EEM", "新兴市场"), ("GLD", "黄金(对照)"),
]
POOL = Path.home() / ".lei_signal_lab/backtest_pool_us"


def fetch_yf_vol(ticker: str) -> pd.DataFrame | None:
    import yfinance as yf

    h = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    h.index = pd.to_datetime(h.index).tz_localize(None)
    df = h[["Open", "High", "Low", "Close", "Volume"]].astype(float).rename(
        columns={"Open": "open", "High": "high", "Low": "low",
                 "Close": "close", "Volume": "volume"}
    )
    if len(df) < 500:
        return None
    return df


def ensure_bars(ticker: str) -> pd.DataFrame | None:
    path = POOL / f"{ticker}.bars.parquet"
    if path.exists():
        return pd.read_parquet(path)
    df = fetch_yf_vol(ticker)
    if df is None:
        return None
    from lei_signal.data.cache import ParquetCache

    ParquetCache(POOL).write(ticker, df, kind="bars", provider="yfinance")
    time.sleep(1.0)
    return df


def perf_str(eq: pd.Series) -> str:
    p = compute_performance(eq)
    return f"{p['cagr']:+6.1%}/{p['mdd']:5.0%}"


def main() -> int:
    us = load_breadth("sp500")
    A_DEF = LadderParams(indicator="b200", n_bands=3, edge_mode="fixed",
                         direction="momentum", min_weight=0.0, gamma=1.5,
                         low_edge=40.0, high_edge=80.0)
    B_DEF = LadderParams(indicator="b200", n_bands=3, edge_mode="fixed",
                         direction="momentum", min_weight=0.0, gamma=1.5,
                         low_edge=30.0, high_edge=70.0)
    rows = []
    for ticker, name in ETFS:
        bars = ensure_bars(ticker)
        if bars is None:
            print(f"!! {ticker} 数据不足，跳过")
            continue
        aligned = align_index_breadth(bars, us)
        if len(aligned) < 500:
            continue
        tA = build_target(aligned, A_DEF, None, TrendGate(mode="ma200"), aligned.iloc[:0],
                          vol_target=0.15)
        tB = build_target(aligned, B_DEF, None, TrendGate(mode="ma200"), aligned.iloc[:0],
                          vol_target=0.10)
        resA = simulate(aligned, tA, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
        resB = simulate(aligned, tB, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
        eqA, eqB = resA.daily["equity"], resB.daily["equity"]
        hold_p = compute_performance(aligned["close"] / aligned["close"].iloc[0])
        mid = len(aligned) // 2
        h2A = compute_performance(eqA.iloc[mid:] / eqA.iloc[mid])
        hold_h2 = compute_performance(
            aligned["close"].iloc[mid:] / aligned["close"].iloc[mid]
        )
        w22 = aligned.loc["2022-01-01":"2022-12-31"]
        if len(w22) > 60:
            res22 = simulate(w22, tA.loc[w22.index], fee_bps=10.0, cash_rate=0.0,
                             min_trade=0.05)
            m22 = summarize_run(res22.daily, res22.trades)
            hold22 = compute_performance(w22["close"] / w22["close"].iloc[0])
            s22 = (f"{m22['strategy_cagr']:+.0%}/{m22['strategy_mdd']:.0%}"
                   f" vs {hold22['cagr']:+.0%}/{hold22['mdd']:.0%}")
        else:
            s22 = "—"
        pa = compute_performance(eqA)
        passed = (
            pa["mdd"] >= hold_p["mdd"] / 2
            and pa["cagr"] >= hold_p["cagr"] - 0.03
            and h2A["cagr"] >= hold_h2["cagr"] - 0.03
        )
        rows.append(dict(
            etf=f"{ticker}·{name}", 起=aligned.index[0].strftime("%Y-%m"),
            持有=f"{hold_p['cagr']:+.1%}/{hold_p['mdd']:.0%}",
            防守A_40_80=f"{pa['cagr']:+.1%}/{pa['mdd']:.0%}",
            防守B_30_70=f"{compute_performance(eqB)['cagr']:+.1%}/"
                        f"{compute_performance(eqB)['mdd']:.0%}",
            后半差=f"{h2A['cagr'] - hold_h2['cagr']:+.1%}",
            熊22=s22, 判定="✓" if passed else "✗",
        ))
        print(f"ok {ticker}", file=sys.stderr)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    out = Path(__file__).parents[1] / "docs/timing-sweep/us_etf_defense.csv"
    df.to_csv(out, index=False)
    print(f"\n通过 {int((df['判定'] == '✓').sum())}/{len(df)} → {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
