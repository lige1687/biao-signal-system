"""单标的三形态对比展示：策略版 vs 纯宽度仓位版 vs 买入持有（2026-08-27 第六轮）。

用户口径（事前写死）：
- 仓位层 = 双线双重确认（B50 与 B200 同时入区才算）：
    双低（两线同时 <= L）→ 目标仓 1.0；双高（两线同时 >= H）→ 0.25；
    其间 → 0.6。两档阈值各测：(L,H) = (20,80) 与 (15,85)；
    (20,80) 另跑双高归 0.0 敏感性。周频判定（每周最后宽度日收盘）、
    次一交易日开盘执行，单边 5bp。
- 每标的三形态（同窗、100 万起、日频权益）：
    STRAT 策略版 = 该标的的模块信号（A门禁/B'/C/D，标的内去重）
      × 1% 风险预算 × 入场日仓位层乘数（合规 <=1.0），逐笔复利，
      持仓期按收盘日度标记，结算按 r_net 口径；
    WIDTH 纯仓位版 = 只按双线状态调仓，无信号；
    BH 买入持有（5bp 入场）。
- 指标：年化、最大回撤；STRAT 另报笔数/累计R。
- 判定：无（效果展示，非假设检验）——按用户要求「看效果、看回撤控制」。

纪律：纯实验脚本；不改 src/configs/web。
输出：docs/experiments/raw/breadth_overlay/symbol_showcase.csv + .json
复现：python3 scripts/run_symbol_showcase.py（约 2 分钟）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_full_stack_sim import gate_a, load_runs  # noqa: E402

from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
COST = 0.0005

# 展示标的 = 观察名单 4+1 + 全流贡献前十（per_symbol_attr.csv）
WATCH = ["518850.SS", "510300.SS", "512400.SS", "515050.SS", "512010.SS"]
TOP = ["603993.SS", "600030.SS", "300003.SZ", "159915.SZ", "512980.SS",
       "300073.SZ", "002371.SZ"]


def dual_state_map(br: pd.DataFrame, low: float, high: float,
                   hi_pos: float, mid_pos: float = 0.6
                   ) -> dict[str, float]:
    """双线双重确认状态表：周频判定 → 次一宽度日生效（ffn 由查询侧做）。"""
    days = br.index
    b50, b200 = br["ma50_pct"], br["ma200_pct"]
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    out: dict[str, float] = {}
    for i in range(len(days)):
        if not is_sig[i] or i + 1 >= len(days):
            continue
        d = days[i]
        if b50[d] <= low and b200[d] <= low:
            pos = 1.0
        elif b50[d] >= high and b200[d] >= high:
            pos = hi_pos
        else:
            pos = mid_pos
        out[str(days[i + 1].date())] = round(pos, 4)
    return out


def ffn(map_: dict[str, float], day: str) -> float:
    keys = sorted(map_)
    if not keys or day < keys[0]:
        return 1.0
    lo, hi = 0, len(keys) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if keys[mid] <= day:
            lo = mid
        else:
            hi = mid - 1
    return map_[keys[lo]]


def sim_width(bars: pd.DataFrame, smap: dict[str, float],
              capital: float = 1_000_000.0) -> pd.Series:
    cash, shares, cur = capital, 0.0, 0.0
    eq = {}
    for d, row in bars.iterrows():
        key = str(d.date())
        tgt = ffn(smap, key)
        if abs(tgt - cur) > 1e-9:  # 生效日开盘调到目标
            eq_now = cash + shares * row["open"]
            want = tgt * eq_now
            delta = want - shares * row["open"]
            fee = abs(delta) * COST
            if delta > 0:
                cash -= delta + fee
                shares += delta / row["open"]
            else:
                cash += -delta - fee
                shares += delta / row["open"]
            cur = tgt
        eq[d] = cash + shares * row["close"]
    return pd.Series(eq).sort_index()


def sim_bh(bars: pd.DataFrame, capital: float = 1_000_000.0) -> pd.Series:
    px0 = bars["open"].iloc[0]
    shares = (capital * (1 - COST)) / px0
    return (shares * bars["close"]).rename("bh")


def strat_trades(runs: dict, symbol: str) -> list[dict]:
    """该标的全部模块信号（A门禁 + B' + C + D），标的内按到达序去重叠。"""
    pool = (gate_a(runs["A"]) + runs["B'"] + runs["C"] + runs["D"])
    ts = sorted((t for t in pool if t["symbol"] == symbol
                 and t["exit_date"] is not None),
                key=lambda t: t["entry_date"])
    kept, last_exit = [], ""
    for t in ts:
        if t["entry_date"] > last_exit:
            kept.append(t)
            last_exit = t["exit_date"]
    return kept


def sim_strat(bars: pd.DataFrame, trades: list[dict], smap: dict[str, float],
              capital: float = 1_000_000.0,
              risk: float = 0.01) -> tuple[pd.Series, int, float]:
    by_entry: dict[str, list[dict]] = {}
    by_exit: dict[str, list[dict]] = {}
    for t in trades:
        by_entry.setdefault(t["entry_date"], []).append(t)
        by_exit.setdefault(t["exit_date"], []).append(t)
    cash, held = capital, None  # held = dict(shares, entry, stop, budget)
    eq, cum_r = {}, 0.0
    for d, row in bars.iterrows():
        key = str(d.date())
        if held and key in by_exit and held["t"] in by_exit[key]:
            t = held["t"]
            cash += held["budget"] * t["r_net"]  # 结算按 r_net（含费）
            cum_r += t["r_net"]
            held = None
        if held is None and key in by_entry:
            for t in by_entry[key]:
                if t is trades[0] or True:
                    mult = min(1.0, ffn(smap, key))
                    budget = cash * risk * mult
                    e, s = float(t["entry_price"]), float(t["stop_price"])
                    if e > s > 0:
                        shares = budget / (e - s)
                        held = {"t": t, "budget": budget, "shares": shares,
                                "entry": e, "stop": s}
                    break
        if held:
            eq[d] = cash + held["budget"] * (
                1 + (row["close"] - held["entry"])
                / (held["entry"] - held["stop"]))
        else:
            eq[d] = cash
    return pd.Series(eq).sort_index(), len(trades), round(cum_r, 1)


def cagr_dd(eq: pd.Series) -> dict:
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")
    dd = float((eq / eq.cummax() - 1).min())
    return {"final": round(float(eq.iloc[-1])), "cagr": round(cagr, 4),
            "max_dd": round(dd, 4)}


def main() -> None:
    runs = load_runs(rerun=False)
    br = load_breadth()
    frames = load_pool_frames()
    states = {
        "W_20_80": dual_state_map(br, 20.0, 80.0, 0.25),
        "W_15_85": dual_state_map(br, 15.0, 85.0, 0.25),
        "W_20_80z": dual_state_map(br, 20.0, 80.0, 0.0),
    }
    rows = []
    for sym in WATCH + [s for s in TOP if s not in WATCH]:
        bars = frames.get(sym)
        if bars is None or len(bars) < 250:
            print(f"[skip] {sym} 无足够行情")
            continue
        tr = strat_trades(runs, sym)
        rec = {"symbol": sym,
               "BH": cagr_dd(sim_bh(bars)),
               "W_20_80": cagr_dd(sim_width(bars, states["W_20_80"])),
               "W_15_85": cagr_dd(sim_width(bars, states["W_15_85"])),
               "W_20_80z": cagr_dd(sim_width(bars, states["W_20_80z"]))}
        if tr:
            eq, n, cum_r = sim_strat(bars, tr, states["W_20_80"])
            rec["STRAT"] = {**cagr_dd(eq), "n": n, "cum_R": cum_r}
        rows.append(rec)
        s = rec
        print(f"\n[{sym}]  窗口 {bars.index[0].date()}→{bars.index[-1].date()}"
              f"  信号 {len(tr)} 笔")
        for k in ("BH", "W_20_80", "W_15_85", "W_20_80z", "STRAT"):
            if k in s:
                m = s[k]
                extra = f" n={m['n']} R={m['cum_R']}" if k == "STRAT" else ""
                print(f"  {k:9s} 终值 {m['final']:>9,} 年化 {m['cagr']:+.1%}"
                      f" 回撤 {m['max_dd']:.1%}{extra}")
    pd.DataFrame([{"symbol": r["symbol"],
                   **{f"{k}_{m}": r[k][m] for k in r if k != "symbol"
                      for m in r[k]}} for r in rows]).to_csv(
        RAW / "symbol_showcase.csv", index=False)
    (RAW / "symbol_showcase.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1, default=str))
    print(f"\n落盘: {RAW}/symbol_showcase.csv")


if __name__ == "__main__":
    main()
