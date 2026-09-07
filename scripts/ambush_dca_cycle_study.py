# -*- coding: utf-8 -*-
"""定投埋伏完整规则包实验（2026-09-07，用户口径：不同标的不同时机出规则）。

三问：
- 买入时机（已验证）：下跌型 × 跌穿筹码价值区下沿（VAL×1.02）；
- 卖出时机（本轮）：对称假设——涨进上方套牢区（VAH×0.98）触发分批清
  （解套盘抛压区），对照「趋势止盈（转稳涨清）」；
- 循环（本轮）：清仓后回到「下跌型+跌穿VAL」是否重启埋伏（波段化定投）。

臂设计（全部共用 VAL 触发买入）：
- B1 卖出=趋势止盈（转稳涨分批清，当前最优对照）；
- D1 卖出=筹码止盈（涨进 VAH×0.98 分批清，每月1/3）；
- D2 卖出=筹码止盈全清（涨进 VAH×0.98 一次清）；
- E  = D1 + 再埋伏循环（清后回到 VAL 触发条件重启）。

标的扩到 8（宽基/行业/QDII/商品四类，出分类型规则表）。窗口与费率同前。
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
    "159915.SZ": ("创业板ETF", "宽基"), "510500.SS": ("中证500ETF", "宽基"),
    "512100.SS": ("中证1000ETF", "宽基"),
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


def zones(hist: pd.DataFrame) -> tuple[float | None, float | None]:
    if len(hist) < 60:
        return None, None
    vp = compute_volume_profile(hist)
    if vp is None:
        return None, None
    return float(vp.val), float(vp.vah)


def simulate(sym: str, arm: str) -> dict:
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
    cycles = 0
    trend_locked = False  # F 臂：形态转稳涨后锁定趋势止盈（不再用筹码兜底）
    equity: list[float] = []
    for date, price in close.items():
        r = reg.loc[date]
        if arm == "F" and r == "steady_uptrend":
            trend_locked = True
        wk = (date.isocalendar()[1], date.isocalendar()[0])
        if last_week is None or wk != last_week:
            last_week = wk
            val, _vah = zones(w.loc[:date])
            in_val = val is not None and price <= val * 1.02
            if r == "downtrend" and in_val and not (cleared and arm != "E"):
                shares += (1 - FEE) / price
                invested += 1.0
        # 卖出触发
        _, vah = zones(w.loc[:date])
        in_vah = vah is not None and price >= vah * 0.98
        if shares > 1e-9:
            if arm == "B1":
                if r == "steady_uptrend" and sell_schedule == 0:
                    sell_schedule = 3
            elif arm in ("D1", "E"):
                if in_vah and sell_schedule == 0:
                    sell_schedule = 3
            elif arm == "F":
                # 自适应：形态已转稳涨（趋势确认）→ 只用趋势止盈（禁用筹码，
                # 让利润奔跑）；未转稳涨 → 筹码止盈兜底（涨进套牢区就走）
                if r == "steady_uptrend":
                    if not getattr(simulate, "_trend_locked", False):
                        pass
                    if sell_schedule == 0 and trend_locked:
                        sell_schedule = 3
                elif in_vah and sell_schedule == 0 and not trend_locked:
                    sell_schedule = 3
            elif arm == "D2":
                if in_vah:
                    cash += shares * price * (1 - FEE)
                    shares = 0.0
                    cleared = True
                    cycles += 1
        if sell_schedule > 0 and date.day <= 3 and shares > 0:
            part = shares / sell_schedule
            cash += part * price * (1 - FEE)
            shares -= part
            sell_schedule -= 1
            if shares < 1e-9:
                shares = 0.0
                cleared = True
                cycles += 1
        # E：清仓后可再埋伏（重新允许 in_val 投入）
        equity.append(cash + shares * price)
    eq = pd.Series(equity, index=close.index)
    final = float(eq.iloc[-1])
    peak = eq.cummax()
    mdd = float((eq / peak - 1).min())
    return {
        "invested": round(invested, 0), "final": round(final, 0),
        "multiple": round(final / invested, 2) if invested else None,
        "mdd": round(mdd * 100, 1), "cycles": cycles,
    }


def main() -> None:
    arms = [("B1", "趋势止盈"), ("D1", "筹码止盈分批"), ("D2", "筹码止盈全清"), ("E", "筹码止盈+循环"), ("F", "自适应退出")]
    out = {}
    print(f"{'标的':9s}{'类':4s}{'臂':12s}{'投入':>5s}{'倍数':>6s}{'回撤':>8s}{'循环':>4s}")
    for sym, (name, kind) in TARGETS.items():
        out[sym] = {"name": name, "kind": kind}
        for arm, label in arms:
            r = simulate(sym, arm)
            out[sym][arm] = r
            print(f"{name:9s}{kind:4s}{label:12s}{r['invested']:>5.0f}"
                  f"{str(r['multiple']):>6s}{r['mdd']:>7.1f}%{r['cycles']:>4d}")
    Path("/tmp/ambush_wide_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n已存 /tmp/ambush_cycle_results.json")


if __name__ == "__main__":
    main()
