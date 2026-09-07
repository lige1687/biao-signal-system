# -*- coding: utf-8 -*-
"""定投埋伏×筹码密集区触发实验（2026-09-07，用户假设）。

假设：反复止损的场景下，在「密集成交区」（筹码价值区）定投效果更好——
买在多数持仓人成本带附近，而不是整段下跌无差别投。

三臂对比（同窗口/费率/退出）：
- A 基线：下跌型周投（ambush_dca_exit_study 口径）；
- B 价值区触发：下跌型 且 收盘进入滚动筹码价值区下沿附近
  （close ≤ VAL×1.02）才投——价格已跌到多数人成本密集带；
- C 密集带贴线：下跌型 且 close ∈ [POC×0.90, POC×1.05]——贴近最大
  成密集价（更窄的口径）。

筹码：compute_volume_profile 滚动 120 日窗口（规则账本默认，无未来数据），
每周末重算一次（周频决策对齐）。退出统一用「趋势止盈」（转稳涨分批清）
与「不退出」两档各跑。窗口 2021-01→2026-08，费率 10bp，预注册：
以倍数与回撤共同看，不加单一指标判定。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.features.volume_profile import compute_volume_profile

POOL = Path.home() / ".lei_signal_lab" / "backtest_pool"
TARGETS = {
    "512690.SS": "白酒ETF", "513180.SS": "恒生科技", "512010.SS": "医药ETF",
    "512480.SS": "半导体ETF", "510300.SS": "沪深300ETF",
}
START, END = "2021-01-04", "2026-08-24"
FEE = 0.001


def regime_series(close: pd.Series) -> pd.Series:
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema60 = close.ewm(span=60, adjust=False).mean()
    env = ((ema20 > ema60) & (ema20.diff() > 0)).rolling(250, min_periods=120).mean()
    ret = close.pct_change(250)
    below = close < ema20 * 0.985
    brk = (below & ~below.shift(1, fill_value=False)).rolling(250, min_periods=120).sum()
    out = pd.Series("range", index=close.index)
    out[ret < -0.15] = "downtrend"
    out[(env >= 0.55) & (brk <= 20)] = "steady_uptrend"
    out[(ret > 0.50) & ~((env >= 0.55) & (brk <= 20))] = "fast_uptrend"
    return out


def profile_zone(hist: pd.DataFrame) -> tuple[float | None, float | None]:
    """滚动筹码窗口的 (POC, VAL)。窗口不足或无有效分布返回 (None, None)。"""
    if len(hist) < 60:
        return None, None
    vp = compute_volume_profile(hist)
    if vp is None:
        return None, None
    return float(vp.poc), float(vp.val)


def simulate(sym: str, arm: str, use_trend_exit: bool) -> dict:
    df = pd.read_parquet(POOL / f"{sym}.bars.parquet")
    df.index = pd.to_datetime(df.index)
    w = df.loc[START:END]
    close = w["close"]
    reg = regime_series(close).reindex(w.index)
    shares = 0.0
    invested = 0.0
    cash = 0.0
    last_week = None
    sell_schedule = 0
    cleared = False
    equity: list[float] = []
    weeks_hit = 0
    for date, price in close.items():
        r = reg.loc[date]
        wk = (date.isocalendar()[1], date.isocalendar()[0])
        if last_week is None or wk != last_week:
            last_week = wk
            invest = False
            if r == "downtrend" and not cleared:
                if arm == "A":
                    invest = True
                else:
                    hist = w.loc[:date]
                    poc, val = profile_zone(hist)
                    if poc is not None and val is not None:
                        if arm == "B":
                            invest = price <= val * 1.02
                        elif arm == "C":
                            invest = poc * 0.90 <= price <= poc * 1.05
            if invest:
                shares += (1 - FEE) / price
                invested += 1.0
                weeks_hit += 1
        if use_trend_exit:
            if shares > 0 and r == "steady_uptrend" and sell_schedule == 0 and not cleared:
                sell_schedule = 3
            if sell_schedule > 0 and date.day <= 3 and shares > 0:
                part = shares / sell_schedule
                cash += part * price * (1 - FEE)
                shares -= part
                sell_schedule -= 1
                if shares < 1e-9:
                    shares = 0.0
                    cleared = True
        equity.append(cash + shares * price)
    eq = pd.Series(equity, index=close.index)
    final = float(eq.iloc[-1])
    years = (close.index[-1] - close.index[0]).days / 365
    peak = eq.cummax()
    mdd = float((eq / peak - 1).min())
    return {
        "invested": round(invested, 0), "weeks": weeks_hit,
        "final": round(final, 0),
        "multiple": round(final / invested, 2) if invested else None,
        "avg_cost_proxy": None,
        "mdd": round(mdd * 100, 1),
    }


def main() -> None:
    arms = [("A", "基线:下跌型投"), ("B", "价值区下沿投"), ("C", "POC密集带投")]
    out = {}
    print(f"{'标的':9s}{'退出':6s}{'臂':14s}{'投入周':>6s}{'倍数':>7s}{'回撤':>8s}")
    for sym, name in TARGETS.items():
        out[sym] = {"name": name}
        for exit_label, use_exit in [("不退", False), ("止盈", True)]:
            for arm, arm_label in arms:
                r = simulate(sym, arm, use_exit)
                key = f"{arm}_{'exit' if use_exit else 'none'}"
                out[sym][key] = r
                print(f"{name:9s}{exit_label:6s}{arm_label:14s}{r['weeks']:>6d}"
                      f"{str(r['multiple']):>7s}{r['mdd']:>7.1f}%")
    Path("/tmp/ambush_chip_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n已存 /tmp/ambush_chip_results.json")


if __name__ == "__main__":
    main()
