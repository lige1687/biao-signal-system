"""第十一轮：标的优选软倾斜（RS_60 分档 × 低波降权）× split_full 底座。

预注册口径（2026-08-27，跑前落死）：
- 底座 = split_full（A 腿 h_80 闸 50 万 + B'+C+D 无闸 50 万，分账合并）。
  本脚本自带「按标的加权」的组合模拟器（行为对齐
  src/lei_signal/backtest/portfolio.py 的事件日重放：先平后开、当日开当日平
  立即结算、回撤降级、容量按 cap 缩——研究拷贝，已在 docstring 声明）。
- 倾斜信号（周频：每周最后交易日收盘计算，次一交易日生效，无前视）：
    RS_60 = close/close[-60]-1 在池内截面（~170 只池标的，含未成交标的，
    数据齐全者）的百分位排名；
    VOL_60 = 60 日日收益标准差，池内截最低 20% 分位 → 低波标记。
- 臂（乘数为「入场预算乘数」，与宽度 cap 相乘）：
    T0   基线：weight≡1（应复现 split_full 224.6 万——一致性自检）
    RS3  合规降权：RS 前 1/3 ×1.0 / 中 1/3 ×0.8 / 后 1/3 ×0.5
    RS3b 放大版（观察档，撞 risk_pct<=1% 钉死条款，仅记录）：
         前 1/3 ×1.5 / 中 ×1.0 / 后 ×0.5
    VOLd 低波降权：VOL_60 最低 20% ×0.5，其余 ×1.0
    COMBO：RS 后 1/3 或 低波 → ×0.5；RS 中段 → ×0.8；其余 ×1.0
- 判定（事前）：臂胜出 = 终值 >= 1.10 × T0 且 阴跌段(2021-06-18→
  2024-02-29)DD <= T0 + 3pp 且 2026DD <= T0 + 3pp。
- 声明：池为幸存者结构（已知欠账），RS 截面排名在池内相对化——倾斜
  结论的绝对水平打折，方向可用；黄金不豁免倾斜（其 RS 常居前）。

输出：raw/breadth_overlay/symbol_tilt_results.json
复现：python3 scripts/run_symbol_tilt.py（约 3 分钟）
"""
from __future__ import annotations

import json
import math
import sys
from bisect import bisect_right
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_full_stack_sim import (  # noqa: E402
    SEG_HI,
    SEG_LO,
    gate_a,
    load_runs,
    seg_max_dd,
)

from lei_signal.backtest.full_sim import (  # noqa: E402
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
H80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))


def weekly_cross_section(frames: dict, field: str) -> dict[str, dict[str, float]]:
    """周频截面指标：{symbol: {生效日: 值}}。field='rs'|'vol'。
    计算日 = 每周最后有数据的交易日（以 000300 对齐），生效日 = 次一交易日。"""
    days = frames["000300.SS"].index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    sig = [i for i in range(len(days))
           if i + 1 == len(days) or week_key[i + 1] != week_key[i]]
    closes = {s: f["close"] for s, f in frames.items()}
    rets = {s: f["close"].pct_change() for s, f in frames.items()}
    out: dict[str, dict[str, float]] = {s: {} for s in frames}
    for i in sig:
        d = days[i]
        if i + 1 >= len(days):
            continue
        eff = str(days[i + 1].date())
        vals = {}
        for s in frames:
            if field == "rs":
                c = closes[s]
                if d in c.index:
                    loc = c.index.get_loc(d)
                    if loc >= 60 and pd.notna(c.iloc[loc]) \
                            and pd.notna(c.iloc[loc - 60]) \
                            and c.iloc[loc - 60] > 0:
                        vals[s] = c.iloc[loc] / c.iloc[loc - 60] - 1
            else:
                r = rets[s]
                if d in r.index:
                    loc = r.index.get_loc(d)
                    if loc >= 60:
                        w = r.iloc[loc - 60:loc + 1].dropna()
                        if len(w) >= 40:
                            vals[s] = float(w.std())
        if len(vals) < 20:
            continue
        srt = sorted(vals.items(), key=lambda kv: kv[1])
        n = len(srt)
        for rank, (s, _v) in enumerate(srt):
            out[s][eff] = rank / (n - 1) if n > 1 else 0.5
    return out


def make_weight(arm: str, rs: dict, vol: dict):
    def w(symbol: str, day: str) -> float:
        p = _lookup(rs.get(symbol, {}), day)
        if arm == "T0":
            return 1.0
        if arm == "RS3":
            return 1.0 if p >= 2 / 3 else (0.8 if p >= 1 / 3 else 0.5)
        if arm == "RS3b":
            return 1.5 if p >= 2 / 3 else (1.0 if p >= 1 / 3 else 0.5)
        if arm == "VOLd":
            return 0.5 if _lookup(vol.get(symbol, {}), day) < 0.2 else 1.0
        if arm == "COMBO":
            low_vol = _lookup(vol.get(symbol, {}), day) < 0.2
            if p < 1 / 3 or low_vol:
                return 0.5
            return 0.8 if p < 2 / 3 else 1.0
        raise ValueError(arm)
    return w


_LK_CACHE: dict[int, list[str]] = {}


def _lookup(series: dict[str, float], day: str) -> float:
    """series（周频生效日→值，插入序即时间序）取 <= day 的最近值。"""
    if not series:
        return 0.5
    kid = id(series)
    keys = _LK_CACHE.get(kid)
    if keys is None:
        keys = _LK_CACHE[kid] = sorted(series)
    i = bisect_right(keys, day) - 1
    return series[keys[i]] if i >= 0 else 0.5


def sim_weighted(trades: list[dict], weight, cap_fn, initial: float
                 ) -> dict:
    """按标的加权的事件日重放（研究拷贝，对齐 portfolio.simulate_portfolio
    的顺序与口径：先平后开、当日开当日平立即结算、回撤降级×0.8/10%、
    并发 10 / 池 6 按 cap 缩；预算 = equity×1%×factor×cap×weight）。"""
    by_entry: dict[str, list] = {}
    for t in trades:
        t = dict(t)
        t["pool"] = t.get("pool", "main")
        by_entry.setdefault(t["entry_date"], []).append(t)
    equity = initial
    peak = initial
    open_pos: dict[str, dict] = {}
    curve, taken = [], []
    event_days = sorted(set(by_entry) | {t["exit_date"] for t in trades})
    for day in event_days:
        for sym in sorted(open_pos):
            pos = open_pos[sym]
            if pos["t"]["exit_date"] == day:
                pnl = pos["budget"] * pos["t"]["r_net"]
                equity += pnl
                peak = max(peak, equity)
                taken.append({"symbol": sym, "r_net": pos["t"]["r_net"],
                              "budget": round(pos["budget"], 2),
                              "weight": pos["w"], "pnl": round(pnl, 2)})
                del open_pos[sym]
        day_cap = min(1.0, max(0.0, cap_fn(day))) if cap_fn else 1.0
        for t in by_entry.get(day, []):
            if t["symbol"] in open_pos or equity <= 0:
                continue
            if len(open_pos) >= max(1, math.ceil(10 * day_cap)):
                continue
            w = weight(t["symbol"], day)
            dd = (peak - equity) / peak if peak > 0 else 0
            factor = 0.8 ** int(dd / 0.10)
            budget = equity * 0.01 * factor * day_cap * w
            if budget <= 0:
                continue
            pos = {"t": t, "budget": budget, "w": round(w, 2)}
            if t["exit_date"] == day:
                equity += budget * t["r_net"]
                peak = max(peak, equity)
                taken.append({"symbol": t["symbol"], "r_net": t["r_net"],
                              "budget": round(budget, 2), "weight": pos["w"],
                              "pnl": round(budget * t["r_net"], 2)})
            else:
                open_pos[t["symbol"]] = pos
        curve.append({"date": day, "equity": round(equity, 2)})
    return {"final": equity, "curve": curve, "taken": taken}


def merge_curves(a: dict, b: dict) -> dict:
    ca = {p["date"]: p["equity"] for p in a["curve"]}
    cb = {p["date"]: p["equity"] for p in b["curve"]}
    out, last = [], [next(iter(ca.values()), 0), next(iter(cb.values()), 0)]
    for d in sorted(set(ca) | set(cb)):
        last = [ca.get(d, last[0]), cb.get(d, last[1])]
        out.append({"date": d, "equity": sum(last)})
    by_year, prev = {}, 1_000_000.0
    for y in sorted({p["date"][:4] for p in out}):
        win = [p for p in out if p["date"][:4] == y]
        pk, mdd = prev, 0.0
        for p in win:
            pk = max(pk, p["equity"])
            if pk > 0:
                mdd = max(mdd, (pk - p["equity"]) / pk)
        by_year[y] = round(mdd * 100, 3)
        prev = win[-1]["equity"]
    return {"final": out[-1]["equity"], "curve": out,
            "by_year": by_year, "taken": a["taken"] + b["taken"]}


def main() -> None:
    runs = load_runs(rerun=False)
    frames = load_pool_frames()
    br = load_breadth()
    b200 = {str(d.date()): float(v) for d, v in br["ma200_pct"].items()}
    cap_h80 = cap_fn_from_map(position_cap_map(b200, H80))

    a_leg = dedup_signals([{**t, "pool": "A_ETF"} for t in gate_a(runs["A"])])[0]
    s_leg = dedup_signals(
        [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
        + [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]])[0]

    rs = weekly_cross_section(frames, "rs")
    vol = weekly_cross_section(frames, "vol")

    arms = ("T0", "RS3", "RS3b", "VOLd", "COMBO")
    results, verdicts = {}, {}
    t0 = None
    for arm in arms:
        w = make_weight(arm, rs, vol)
        a = sim_weighted(a_leg, w, cap_h80, 500_000)
        s = sim_weighted(s_leg, w, None, 500_000)
        m = merge_curves(a, s)
        row = {"final": round(m["final"]),
               "seg_dd": seg_max_dd(m["curve"], SEG_LO, SEG_HI),
               "dd26": m["by_year"].get("2026")}
        results[arm] = row
        if arm == "T0":
            t0 = row
    for arm in arms:
        if arm == "T0":
            continue
        r = results[arm]
        verdicts[arm] = {
            "JT1": bool(r["final"] >= 1.10 * t0["final"]
                        and r["seg_dd"] <= t0["seg_dd"] + 3
                        and r["dd26"] is not None
                        and r["dd26"] <= t0["dd26"] + 3),
            "note": "RS3b 为放大观察档（撞 risk_pct<=1% 条款）"
            if arm == "RS3b" else ""}
    out = {"date": "2026-08-27", "arms": results, "verdicts": verdicts,
           "t0_sanity_target": 2246020}
    (RAW / "symbol_tilt_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
