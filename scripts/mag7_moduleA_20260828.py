"""七姐妹 × 咱家模块 A 系统（稳定上涨回调 + R 止损）——用户点名测试。

数据：yfinance auto_adjust 复权 OHLCV（含 volume，池子要求），写入
~/.lei_signal_lab/backtest_pool/{SYM}.bars.parquet（含基准 ^GSPC，runner 的
BENCHMARK_BY_MARKET 需要）。之后 execute_run 原样跑系统：模块 A 默认变体、
盈亏比门槛 3、退出=跌破EMA20+抵扣价、费用档 standard、美股关涨跌停约束。
对照：回测池 A 股全池（若池子规模合理）同参数一跑。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

POOL = Path.home() / ".lei_signal_lab/backtest_pool"
MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]


def fetch_yf_vol(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    hist = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    hist.index = pd.to_datetime(hist.index).tz_localize(None)
    return hist[["Open", "High", "Low", "Close", "Volume"]].astype(float).rename(
        columns={"Open": "open", "High": "high", "Low": "low",
                 "Close": "close", "Volume": "volume"}
    )


def ensure_pool(ticker: str) -> None:
    from lei_signal.data.cache import ParquetCache

    path = POOL / f"{ticker}.bars.parquet"
    if path.exists() and path.with_suffix(".meta.json").exists():
        return
    df = fetch_yf_vol(ticker)
    ParquetCache(POOL).write(ticker, df, kind="bars", provider="yfinance")
    print(f"池子+ {ticker}: {df.index[0].date()}→{df.index[-1].date()} {len(df)} 根")


def main() -> None:
    POOL.mkdir(parents=True, exist_ok=True)
    for t in [*MAG7, "^GSPC"]:
        ensure_pool(t)

    from lei_signal.backtest.service import BacktestParams, execute_run

    res = execute_run(BacktestParams(
        symbols=tuple(MAG7), module="A", rr_min=3.0,
        exit_variant="a6_1_costbasis", fee_label="standard", limit_guard=False,
    ))
    groups = res["groups"]["True"]
    print("=== 七姐妹 × 模块 A（默认参数，费用 standard，无涨跌停约束）===")
    ov = groups["总览"][0]
    keys = ["trade_count", "open_count", "win_rate", "expectancy_r", "profit_factor",
            "max_consecutive_losses", "max_drawdown_1r", "avg_holding_bars", "total_r"]
    print("总览:", {k: ov.get(k) for k in keys})
    print("\n按标的：")
    for m in groups.get("按标的", []):
        print(
            f"  {m['label']:<7} 笔数{m['trade_count']:<4} 胜率{m['win_rate']:.0%} "
            f"期望R{m['expectancy_r']:+.2f} 盈利因子{m['profit_factor']:.2f} "
            f"累计R{m['total_r']:+.1f}"
        )
    dr = res.get("data_range", {})
    print(f"\n数据 {dr.get('start')}→{dr.get('end')}，样本外起点 {dr.get('out_of_sample_start')}")
    funnel = res.get("funnel", {})
    print(f"漏斗: 触碰{funnel.get('touched')} → 信号{funnel.get('confirmed')} → 盈亏比剔除{funnel.get('filtered_by_rr')}")


if __name__ == "__main__":
    main()
