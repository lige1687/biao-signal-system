"""美股个股 × LEI 执行门——美股拼图的最后一块（预注册）。

背景：宽度层对美股个股三方向全败（25轮），个股风控只剩执行门。
用系统真实规则（classify_colors 三色 + compute_long_trend）做美股个股的持有闸：
  H1 = 非黑（黑色=明确下行离场，灰/绿在场）
  H2 = 非长期空头（EMA60/120 空头才离场）
  H3 = 双门（非黑 ∧ 非bear）
  对照：持有 | MA200 门（Faber 经典）
评估线（预注册）：回撤较持有减 ≥1/3 且全历史年化损失 ≤3pp → 可作美股个股风控层。
12 只大盘股（复权价，缓存自 25 轮），费用 10bp。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.timing_backtest.data import TIMING_CACHE_DIR
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance, summarize_run

STOCKS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",
          "TSLA", "JPM", "XOM", "JNJ", "PG", "KO"]


def gates(bars: pd.DataFrame) -> dict[str, pd.Series]:
    feat = compute_features(bars.assign(volume=1.0)[["open", "high", "low", "close", "volume"]])
    color = classify_colors(feat)["signal_color"]
    trend = compute_long_trend(feat)["long_trend"]
    not_black = (color != "black").astype(float)
    not_bear = (trend != "long_bear").astype(float)
    ma200 = (feat["close"] > feat["close"].rolling(200).mean()).astype(float)
    return {"H1非黑": not_black, "H2非bear": not_bear, "H3双门": not_black * not_bear,
            "M200": ma200}


def main() -> None:
    rows = []
    for ticker in STOCKS:
        path = TIMING_CACHE_DIR / f"US_{ticker}.parquet"
        if not path.exists():
            continue
        bars = pd.read_parquet(path)
        g = gates(bars)
        hold = compute_performance(bars["close"] / bars["close"].iloc[0])
        row = {"股票": f"{ticker}", "持有": f"{hold['cagr']:+.0%}/{hold['mdd']:.0%}"}
        for vtag, gate in g.items():
            res = simulate(bars, gate, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
            m = summarize_run(res.daily, res.trades)
            row[vtag] = f"{m['strategy_cagr']:+.0%}/{m['strategy_mdd']:.0%}"
            row[f"{vtag}_dd_cut"] = 1 - m["strategy_mdd"] / hold["mdd"]
            row[f"{vtag}_cagr_cost"] = hold["cagr"] - m["strategy_cagr"]
        rows.append(row)
    df = pd.DataFrame(rows)
    print("=== 美股个股 × 执行门（全历史→2026-08-14，年化/回撤）===")
    print(df[["股票", "持有", "H1非黑", "H2非bear", "H3双门", "M200"]].to_string(index=False))
    print("\n评估（回撤削减幅度 / 年化代价，均值）：")
    for v in ("H1非黑", "H2非bear", "H3双门", "M200"):
        print(
            f"  {v}: 回撤减 {df[f'{v}_dd_cut'].mean():.0%} / "
            f"年化损失 {df[f'{v}_cagr_cost'].mean():+.1%}pp"
        )


if __name__ == "__main__":
    main()
