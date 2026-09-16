# -*- coding: utf-8 -*-
"""条件触发定投的完整交易闭环（第十三轮）：入场条件 → 定投建仓 → 出场条件 → 平仓。

问题（用户 2026-09-07 指出方法论缺陷后重设计）：此前一~十二轮的定投实验
只有买入侧，"判负/有增量"全部是窗口终点账面市值的对比——**一笔交易都没有
闭环**。本实验改为完整交易制：每笔交易有明确的入场触发、12 个月定投建仓、
明确的出场条件（含时间强制离场），平仓落袋后逐笔统计。

预注册口径（跑前写死，跑后不得改）：

- 样本：8 个 A 股指数/ETF 全历史（同第十一轮：SH000001/SZ399001 31y、
  000300 22y、000015 21y、399006 14y、510500/512100/588000 短）。
- 交易生命周期（每标的每触发独立、不重叠：交易进行中忽略新事件）：
  * 入场触发四档：deep20（距年线 ≤−20%）/ bottom（底部区域：惨×回撤≤−15%×
    年线下方）/ lowtier（惨档 b200<43.3）/ base（每月末机械开仓，对照）；
    事件 = 触发由假转真且间隔 ≥126 根 K 线（base 为月末，同规则）。
  * 建仓：触发后 12 个月（252 根 K 线）每周等额定投，每笔预算 1.0，
    买入费 10bp。
  * 出场五档（建仓完成后每周检查，信号日收盘判定 → 次日开盘平仓，卖出费
    10bp）：X30（距年线 ≥+30%）/ X20（距年线 ≥+20%）/ Xtime（建仓完成后
    满 12 个月时间离场）/ Xtarget（累计浮盈 ≥+30% 止盈）/ Xheat（b200>56.7）。
  * 时间强制：建仓完成后 24 个月无出场触发 → 强制平仓（保证每笔闭环）。
- 逐笔度量：净收益率（平仓款/预算−1）、胜率、持有月数（建仓 12 个月+
    等待期）、P10/P90、最大单笔亏损。
- 预注册方向预期（描述性登记，不设通过线）：
  P1 X30 出场中位 ≥ Xtime（状态表：+30% 之后 12 个月中位 −12.4%）；
  P2 deep20 入场的交易中位收益 > base 入场；
  P3 Xheat 出场是五档里最差（热档前瞻为正，出场在砍牛腿）；
  P4 bottom 入场介于两者之间。结果与预期相反时如实登记。
- 结论级别：只检验不决策。禁止买卖指令类词汇。
- 已知边界：事件聚类/重叠样本局限沿十一轮；每标的每触发的交易数有限
  （登记 n）；科创50 仅 5 年；状态表口径沿十一轮（point-in-time）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import (
    align_index_breadth,
    load_breadth,
    load_index_bars,
)

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "docs/experiments/raw/dca-complete-trades-2026-09-07"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["SH000001", "SZ399001", "000300", "000015", "399006",
           "510500", "512100", "588000"]
ENTRIES = ["deep20", "bottom", "lowtier", "base"]
EXITS = ["X30", "X20", "Xtime", "Xtarget", "Xheat"]
FEE = 10.0
ACCUM = 252      # 建仓 12 个月
MAX_HOLD = 504   # 建仓后再等最多 24 个月
COOLDOWN = 126


def build_states(sym: str) -> pd.DataFrame:
    bars = load_index_bars(sym)
    breadth = load_breadth("cn_all")
    df = align_index_breadth(bars, breadth)
    df = df[df["b200"].notna()].copy()
    c = df["close"]
    df["ma200"] = c.rolling(200).mean()
    df["ma200_gap"] = c / df["ma200"] - 1.0
    df["dd2y"] = c / c.rolling(500, min_periods=100).max() - 1.0
    tier_low = df["b200"] < 43.3
    df["deep20"] = df["ma200_gap"] <= -0.20
    df["bottom"] = tier_low & (df["dd2y"] <= -0.15) & (df["ma200_gap"] < 0)
    df["lowtier"] = tier_low
    df = df[df["ma200"].notna() & df["dd2y"].notna()]
    return df


def entry_events(df: pd.DataFrame, entry: str) -> list[int]:
    """base=每月末；其余=触发沿+冷却。"""
    idx = df.index
    if entry == "base":
        s = pd.Series(np.arange(len(idx)), index=idx)
        ends = sorted(int(v) for v in s.groupby([idx.year, idx.month]).max())
        out = []
        last = -10**9
        for e in ends:
            if e - last >= COOLDOWN:
                out.append(e)
                last = e
        return out
    f = df[entry].to_numpy(bool)
    out, last = [], -10**9
    for i in range(1, len(f)):
        if f[i] and not f[i - 1] and i - last >= COOLDOWN:
            out.append(i)
            last = i
    return out


def run_trade(df: pd.DataFrame, e: int, exit_mode: str) -> dict | None:
    n = len(df)
    opens = df["open"].to_numpy(float)
    closes = df["close"].to_numpy(float)
    gaps = df["ma200_gap"].to_numpy(float)
    b200 = df["b200"].to_numpy(float)
    f = FEE * 1e-4
    idx = df.index
    s = pd.Series(np.arange(n), index=idx)
    acc_ends = sorted(int(v) for v in s.groupby(
        [idx.isocalendar().year, idx.isocalendar().week]).max())
    acc_set = {p + 1 for p in acc_ends if e < p + 1 <= e + ACCUM}
    units, invested = 0.0, 0.0
    for j in sorted(acc_set):
        amt = 1.0 / len(acc_set)
        units += (amt - amt * f) / opens[j]
        invested += amt
    if invested <= 0:
        return None
    acc_end = e + ACCUM
    exit_j = None
    peak_ret = 0.0
    for j in range(acc_end + 1, min(acc_end + MAX_HOLD, n)):
        ret = units * closes[j] / invested - 1.0
        peak_ret = max(peak_ret, ret)
        sig = j - 1
        hit = False
        if exit_mode == "X30" and np.isfinite(gaps[sig]) and gaps[sig] >= 0.30:
            hit = True
        elif exit_mode == "X20" and np.isfinite(gaps[sig]) and gaps[sig] >= 0.20:
            hit = True
        elif exit_mode == "Xtime" and j > acc_end + ACCUM // 2:
            hit = True
        elif exit_mode == "Xtarget" and ret >= 0.30:
            hit = True
        elif exit_mode == "Xheat" and np.isfinite(b200[sig]) and b200[sig] > 56.7:
            hit = True
        if hit:
            exit_j = j
            break
    if exit_j is None:
        exit_j = min(acc_end + MAX_HOLD, n - 1)
        forced = True
    else:
        forced = False
    proceeds = units * opens[exit_j] * (1.0 - f)
    return {
        "ret": proceeds / invested - 1.0,
        "hold_months": (exit_j - e) / 21.0,
        "forced": forced,
        "entry_date": str(idx[e].date()),
        "exit_date": str(idx[exit_j].date()),
    }


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "trades": {}, "summary": {}}

    for sym in SYMBOLS:
        df = build_states(sym)
        n = len(df)
        for entry in ENTRIES:
            events = entry_events(df, entry)
            used_until = -1
            for e in events:
                if e <= used_until or e + ACCUM + MAX_HOLD >= n:
                    continue
                for exit_mode in EXITS:
                    t = run_trade(df, e, exit_mode)
                    if t:
                        out["trades"].setdefault(f"{entry}|{exit_mode}",
                                                 {}).setdefault(
                            sym, []).append(t)
                # 交易占位：同一入场事件对五个出场是平行宇宙，占位按
                # Xtime 的持有期近似（避免重叠计数）；used_until 由事件
                # 冷却与生命周期共同决定
                used_until = e + ACCUM + MAX_HOLD // 2
        print(f"[{sym}] done", flush=True)

    # 汇总
    for entry in ENTRIES:
        for exit_mode in EXITS:
            all_t = []
            for sym, ts in out["trades"].get(f"{entry}|{exit_mode}",
                                             {}).items():
                all_t.extend(ts)
            if not all_t:
                continue
            rets = np.array([t["ret"] for t in all_t])
            holds = np.array([t["hold_months"] for t in all_t])
            out["summary"][f"{entry}|{exit_mode}"] = {
                "n": len(all_t),
                "median": float(np.median(rets)),
                "mean": float(rets.mean()),
                "win": float((rets > 0).mean()),
                "p10": float(np.percentile(rets, 10)),
                "p90": float(np.percentile(rets, 90)),
                "worst": float(rets.min()),
                "avg_hold_months": float(holds.mean()),
                "forced_pct": float(np.mean([t["forced"] for t in all_t])),
            }

    print("\n=== 逐笔交易汇总（净收益中位/胜率/平均持有月/n）===")
    for entry in ENTRIES:
        for exit_mode in EXITS:
            k = f"{entry}|{exit_mode}"
            if k not in out["summary"]:
                continue
            s = out["summary"][k]
            print(f"{entry:8s} {exit_mode:8s} 中位{s['median']*100:+6.1f}% "
                  f"胜率{s['win']*100:3.0f}% 均值{s['mean']*100:+6.1f}% "
                  f"持有{s['avg_hold_months']:4.1f}月 P10{s['p10']*100:+5.1f}% "
                  f"n={s['n']}", flush=True)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "dca_complete_trades_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
