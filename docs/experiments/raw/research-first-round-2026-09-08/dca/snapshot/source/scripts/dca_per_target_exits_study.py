# -*- coding: utf-8 -*-
"""分标的出场规则（第十五轮）：每个标的各自测——止盈适合谁、不止盈适合谁。

问题（用户 2026-09-08 再次澄清：**分标的**——不是把统一阈值改成分标的阈值，
而是不同标的存在不同类型的正确出场：趋势长牛资产（美股）止盈可能本身是错的，
大周期均值回归资产（A 股指数）止盈才成立，黄金另说。十四轮只在 A 股池内调
阈值，未回答此问题。本轮把标的池扩成跨资产全家，逐标的对比「止盈类 vs
不止盈类」出场。

预注册口径（跑前写死，跑后不得改）：

- 标的池 11 个（跨资产全家）：A 股 8 指数（SH000001/SZ399001/000300/000015/
  399006/510500/512100/588000）+ 518880 黄金ETF（12.3 年）+ ^GSPC/^IXIC
  （39.9 年）。
- 入场两档（**通用口径，不依赖任何市场宽度**）：deep20（自身年线 ≤−20%）、
  base（每月末对照）；事件冷却与不重叠规则同十三轮。
- 出场五档（建仓完成后周查，24 个月强制兜底）：
  Xhold  不止盈：只等强制兜底（对照：不做主动出场）；
  X30    统一 +30% 止盈；
  X50    统一 +50% 止盈（高波动/长牛资产的空间档）；
  Xvol   波动适配止盈 clip(vol,15%,50%)；
  X30dev 距自身年线 ≥+30%（趋势版出场：不预设收益、等极端过热）。
- 逐笔度量：中位/胜率/最差/n（每标的×入场×出场）。
- 预注册判定（写死，按标的）：
  * 每标的名下「止盈类最优中位」（X30/X50/Xvol 三者最大）vs「不止盈类」
    （Xhold 与 X30dev 中较大者）：差 ≥+5pp 记该标的「止盈占优」、≤−5pp 记
    「不止盈占优」、其间记「相当」；
  * 预注册预期：E1 A 股宽基/成长指数「止盈占优」、E2 美股两标的「不止盈
    占优」（与九轮纳指长持证据同向）、E3 黄金开放。结果相反如实登记。
- 已知边界：美股 39.9 年样本内 base 入场交易数多；黄金仅 12.3 年；deep20
  入场在美股稀少（其历史极少跌破年线 20%+，登记 n）；Xhold 的 24 个月兜底
  截断了长牛复利——**Xhold 在此框架内天然吃亏，故同时报告「Xhold 兜底日
  vs 数据末日」差**以显式登记该截断；沿十三/十四轮全部其余边界。
- 结论级别：只检验不决策。禁止买卖指令类词汇。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import load_index_bars

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "docs/experiments/raw/dca-per-target-exits-2026-09-08"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["SH000001", "SZ399001", "000300", "000015", "399006",
           "510500", "512100", "588000", "518880", "^GSPC", "^IXIC"]
NAMES = {"SH000001": "上证指数", "SZ399001": "深证成指", "000300": "沪深300",
         "000015": "上证红利", "399006": "创业板指", "510500": "中证500ETF",
         "512100": "中证1000ETF", "588000": "科创50ETF", "518880": "黄金ETF",
         "^GSPC": "标普500", "^IXIC": "纳斯达克"}
ENTRIES = ["deep20", "base"]
EXITS = ["Xhold", "X30", "X50", "Xvol", "X30dev"]
FEE = 10.0
ACCUM = 252
MAX_HOLD = 504
COOLDOWN = 126


def build_states(sym: str) -> pd.DataFrame:
    df = load_index_bars(sym).copy()
    c = df["close"]
    df["ma200"] = c.rolling(200).mean()
    df["ma200_gap"] = c / df["ma200"] - 1.0
    df["deep20"] = df["ma200_gap"] <= -0.20
    ret = c.pct_change()
    df["vol"] = ret.rolling(500, min_periods=250).std() * np.sqrt(252)
    df = df[df["ma200"].notna()]
    return df


def entry_events(df: pd.DataFrame, entry: str) -> list[int]:
    idx = df.index
    if entry == "base":
        s = pd.Series(np.arange(len(idx)), index=idx)
        ends = sorted(int(v) for v in s.groupby([idx.year, idx.month]).max())
        out, last = [], -10**9
        for e in ends:
            if e - last >= COOLDOWN:
                out.append(e)
                last = e
        return out
    f = df["deep20"].to_numpy(bool)
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
    vol = float(df["vol"].iloc[e]) if np.isfinite(df["vol"].iloc[e]) else 0.25
    f = FEE * 1e-4
    idx = df.index
    s = pd.Series(np.arange(n), index=idx)
    acc_ends = sorted(int(v) for v in s.groupby(
        [idx.isocalendar().year, idx.isocalendar().week]).max())
    acc_set = {p + 1 for p in acc_ends if e < p + 1 <= e + ACCUM}
    if not acc_set:
        return None
    units, invested = 0.0, 0.0
    for j in sorted(acc_set):
        amt = 1.0 / len(acc_set)
        units += (amt - amt * f) / opens[j]
        invested += amt
    acc_end = e + ACCUM
    if exit_mode == "Xhold":
        tp = None
    elif exit_mode == "X30":
        tp = 0.30
    elif exit_mode == "X50":
        tp = 0.50
    elif exit_mode == "Xvol":
        tp = float(np.clip(vol, 0.15, 0.50))
    else:
        tp = None
    exit_j, forced = None, False
    for j in range(acc_end + 1, min(acc_end + MAX_HOLD, n)):
        ret = units * closes[j] / invested - 1.0
        sig = j - 1
        hit = False
        if tp is not None and ret >= tp:
            hit = True
        if exit_mode == "X30dev" and np.isfinite(gaps[sig]) and gaps[sig] >= 0.30:
            hit = True
        if hit:
            exit_j = j
            break
    if exit_j is None:
        exit_j = min(acc_end + MAX_HOLD, n - 1)
        forced = True
    proceeds = units * opens[exit_j] * (1.0 - f)
    return {"ret": proceeds / invested - 1.0, "forced": forced,
            "exit_j": exit_j, "n_bars": n}


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "trades": {}, "summary": {},
                 "per_target": {}}

    for sym in SYMBOLS:
        df = build_states(sym)
        n = len(df)
        for entry in ENTRIES:
            used_until = -1
            for e in entry_events(df, entry):
                if e <= used_until or e + ACCUM + MAX_HOLD >= n:
                    continue
                for exit_mode in EXITS:
                    t = run_trade(df, e, exit_mode)
                    if t:
                        out["trades"].setdefault(f"{entry}|{exit_mode}",
                                                 {}).setdefault(
                            sym, []).append(t)
                used_until = e + ACCUM + MAX_HOLD // 2

    # 每标的×入场×出场 中位
    for entry in ENTRIES:
        for exit_mode in EXITS:
            grp = out["trades"].get(f"{entry}|{exit_mode}", {})
            for sym, ts in grp.items():
                rets = np.array([t["ret"] for t in ts])
                out["summary"][f"{entry}|{exit_mode}|{sym}"] = {
                    "n": len(ts), "median": float(np.median(rets)),
                    "win": float((rets > 0).mean()),
                    "worst": float(rets.min()),
                    "forced_pct": float(np.mean([t["forced"] for t in ts])),
                }

    # 预注册判定：每标的名下 止盈类 vs 不止盈类
    verdicts = {}
    for sym in SYMBOLS:
        for entry in ENTRIES:
            tp_vals, hold_vals = [], []
            for exit_mode in ("X30", "X50", "Xvol"):
                k = f"{entry}|{exit_mode}|{sym}"
                if k in out["summary"]:
                    tp_vals.append((out["summary"][k]["median"], exit_mode))
            for exit_mode in ("Xhold", "X30dev"):
                k = f"{entry}|{exit_mode}|{sym}"
                if k in out["summary"]:
                    hold_vals.append((out["summary"][k]["median"], exit_mode))
            if not tp_vals or not hold_vals:
                continue
            best_tp = max(tp_vals)
            best_hold = max(hold_vals)
            diff = best_tp[0] - best_hold[0]
            label = ("止盈占优" if diff >= 0.05 else
                     "不止盈占优" if diff <= -0.05 else "相当")
            verdicts[f"{entry}|{sym}"] = {
                "best_tp": {"median": best_tp[0], "exit": best_tp[1]},
                "best_hold": {"median": best_hold[0], "exit": best_hold[1]},
                "diff_pp": diff * 100, "verdict": label}
    out["per_target"] = verdicts

    print("=== 分标的：止盈类最优 vs 不止盈类最优（中位，pp）===")
    for entry in ENTRIES:
        print(f"-- 入场 {entry} --")
        for sym in SYMBOLS:
            v = verdicts.get(f"{entry}|{sym}")
            if not v:
                continue
            print(f"  {NAMES[sym]:8s} 止盈类最优[{v['best_tp']['exit']}]"
                  f"{v['best_tp']['median']*100:+6.1f}% vs "
                  f"不止盈类[{v['best_hold']['exit']}]"
                  f"{v['best_hold']['median']*100:+6.1f}% "
                  f"差{v['diff_pp']:+5.1f}pp -> {v['verdict']}", flush=True)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "dca_per_target_exits_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
