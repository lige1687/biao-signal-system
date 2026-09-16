# -*- coding: utf-8 -*-
"""定投埋伏×退出方式实验（2026-09-07，用户口径）。

场景：底部区间不知道哪里是底、不想被频繁打止损（C 模块失灵区）——
定投埋伏替代。问题：埋伏之后**怎么退出**？

与并行 DCA 系列（一~八轮）的边界（跑前澄清）：
- 对方测买入侧（频率/浮动/标的/再平衡/防御性总开关），报告明言
  「无卖出侧止盈」是口径边界；本轮专测**卖出侧**：
  ① 不退出（基线，投到期末持有）；② 趋势止盈（形态转稳涨型后分批清，
  每月卖 1/3）；③ 目标止盈（累计收益达 +40% 全清后停投）；④ 波段再埋伏
  （清仓后若回到下跌型，重启定投）。

口径：周投 1 单位；从 2021-01 起对每个标的用 rolling 形态判定，仅
「下跌型」周投钱（埋伏），非下跌型周停投持仓不动（区别于对方全程平投）；
卖出按收盘价、费用单边 10bp；窗口 2021-01-04 → 2026-08-24。
预注册判定：以「年化 × 回撤性价比」与终值共同看，不做单一指标结论。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

POOL = Path.home() / ".lei_signal_lab" / "backtest_pool"
TARGETS = {
    "512690.SS": "白酒ETF", "513180.SS": "恒生科技", "512010.SS": "医药ETF",
    "512480.SS": "半导体ETF", "510300.SS": "沪深300ETF",
}
START, END = "2021-01-04", "2026-08-24"
FEE = 0.001
TARGET_TP = 0.40


def regime_series(close: pd.Series) -> pd.Series:
    """逐日形态（与 copilot.fit 同口径的向量化近似，仅用截至当日数据）。"""
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema60 = close.ewm(span=60, adjust=False).mean()
    bull = ema20 > ema60
    ema_up = ema20.diff() > 0
    env = (bull & ema_up).rolling(250, min_periods=120).mean()
    ret = close.pct_change(250)
    below = close < ema20 * 0.985
    breaks = below & ~below.shift(1, fill_value=False)
    brk = breaks.rolling(250, min_periods=120).sum()
    out = pd.Series("range", index=close.index)
    out[ret < -0.15] = "downtrend"
    out[(env >= 0.55) & (brk <= 20)] = "steady_uptrend"
    out[(ret > 0.50) & ~((env >= 0.55) & (brk <= 20))] = "fast_uptrend"
    return out


def simulate(sym: str, exit_mode: str) -> dict:
    df = pd.read_parquet(POOL / f"{sym}.bars.parquet")
    df.index = pd.to_datetime(df.index)
    w = df.loc[START:END]
    close = w["close"]
    reg = regime_series(close).reindex(w.index)
    shares = 0.0
    invested = 0.0
    cash_out = 0.0
    weeks_invested = 0
    sell_schedule = 0  # 趋势止盈：剩余分批次数
    cleared = False
    equity_curve: list[float] = []
    last_week = None
    for date, price in close.items():
        r = reg.loc[date]
        # 周投（每周第一个交易日）
        if last_week is None or (date.isocalendar()[1] != last_week or date.year != close.loc[:date].index[-1].year):
            pass
        is_new_week = last_week is None or (
            date.isocalendar()[1], date.isocalendar()[0]
        ) != last_week
        if is_new_week:
            last_week = (date.isocalendar()[1], date.isocalendar()[0])
            if not cleared and r == "downtrend":
                shares += (1 - FEE) / price
                invested += 1.0
                weeks_invested += 1
        # 持仓市值监控（按日）
        value = shares * price
        cost = invested if invested else 1e-9
        unrealized = value / cost - 1 if invested else 0.0
        # 趋势止盈：转稳涨且持仓 → 启动分批（此后每月初卖 1/3，3 次清）
        if exit_mode == "trend" and shares > 0 and r == "steady_uptrend" and sell_schedule == 0 and not cleared:
            sell_schedule = 3
        if sell_schedule > 0 and date.day <= 3 and shares > 0:
            part = shares / sell_schedule
            cash_out += part * price * (1 - FEE)
            shares -= part
            sell_schedule -= 1
            if shares < 1e-9:
                shares = 0.0
                cleared = True
        # 目标注盈：+40% 全清
        if exit_mode == "target" and shares > 0 and unrealized >= TARGET_TP:
            cash_out += shares * price * (1 - FEE)
            shares = 0.0
            cleared = True
        # 波段再埋伏：清仓后回到下跌型重启
        if exit_mode == "trend_rearm" and cleared and r == "downtrend":
            cleared = False
            sell_schedule = 0
        equity_curve.append(cash_out + shares * price)
    eq = pd.Series(equity_curve, index=close.index)
    final = float(eq.iloc[-1])
    years = (close.index[-1] - close.index[0]).days / 365
    peak = eq.cummax()
    mdd = float((eq / peak - 1).min()) if len(eq) else 0.0
    cagr = (final / max(invested, 1e-9)) ** (1 / max(years, 1e-9)) - 1 if final > 0 and invested > 0 else float("nan")
    return {
        "invested": round(invested, 1),
        "weeks": weeks_invested,
        "final": round(final, 2),
        "multiple": round(final / invested, 2) if invested else None,
        "cagr": round(cagr * 100, 1) if cagr == cagr else None,
        "mdd": round(mdd * 100, 1),
    }


def main() -> None:
    modes = ["none", "trend", "target", "trend_rearm"]
    out = {}
    print(f"{'标的':10s}{'退出':12s}{'投入':>7s}{'终值':>8s}{'倍数':>6s}{'年化':>7s}{'最大回撤':>8s}")
    for sym, name in TARGETS.items():
        out[sym] = {"name": name}
        for m in modes:
            r = simulate(sym, m)
            out[sym][m] = r
            label = {"none": "不退出", "trend": "趋势止盈", "target": "目标+40%", "trend_rearm": "止盈+再埋伏"}[m]
            print(f"{name:10s}{label:12s}{r['invested']:>7.0f}{r['final']:>8.0f}"
                  f"{str(r['multiple']):>6s}{str(r['cagr']):>7s}{r['mdd']:>8.1f}%")
    Path("/tmp/ambush_dca_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n结果已存 /tmp/ambush_dca_results.json")


if __name__ == "__main__":
    main()
