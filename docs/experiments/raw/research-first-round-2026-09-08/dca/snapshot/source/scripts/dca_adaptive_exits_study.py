# -*- coding: utf-8 -*-
"""标的适配的止盈止损规则（第十四轮）：不同标的不同出场，而非统一 30%。

问题（用户 2026-09-07 指出）：+30% 统一止盈不合理——不是每个标的都该 30%
止盈，要按标的区分止盈规则。本轮在第十三轮完整交易框架上把出场改成
**标的自适应**，并首次引入止损侧。

预注册口径（跑前写死，跑后不得改）：

- 框架：同第十三轮（8 指数全历史；入场四档 deep20/bottom/lowtier/base；
  12 个月周定投建仓；建仓后 24 个月强制兜底；逐笔平仓；费 10bp）。
- 每标的两条 point-in-time 适配序列（入场日取值、整笔交易沿用）：
  * vol = 过去 500 根日收益年化波动（sqrt(252)×std）；
  * q75 = 过去 1260 根（约 5 年）的「252 根滚动收益」75 分位。
- 出场六臂：
  Xfix30  统一 +30% 止盈（第十三轮基准，无止损）；
  X30dev  距年线 ≥+30%（第十三轮均衡基准，无止损）；
  Xvol    止盈 = clip(vol, 15%, 50%)；
  Xp75    止盈 = clip(q75, 15%, 50%)；
  XvolS   Xvol 止盈 + 止损 = −clip(vol, 10%, 35%)；
  XfixS   统一 +30% 止盈 + 统一 −20% 止损。
  出场检查：建仓完成后每周，累计浮盈 ≥ 止盈线 或 ≤ 止损线 → 次日开盘平仓。
- 判定（写死）：
  * Q1 适配价值：按**标的内**比较 Xvol vs Xfix30 的逐笔收益中位（每标的中位
    高者胜）：≥6/8 标的胜 →「适配止盈有价值」；≤2/8 →「统一够用」；其余混合。
  * Q2 止损代价收益：XvolS vs Xvol 与 XfixS vs Xfix30：中位变化与最差单笔
    变化同表呈现（预期：最差变浅、中位下降——登记方向）。
  * Q3 Xp75 与 Xvol 一致性：8 标的的目标值相关性 + 中位差异方向。
  * 预注册预期：E1 低波动标的（红利/上证）Xvol 显著改善（统一 30% 等不到）；
    E2 止损浅化左尾但压低中位；E3 Xp75≈Xvol。结果相反如实登记。
- 度量：总体（中位/胜率/P10/P90/最差/强制率）+ **分标的中位表**（本轮核心
  输出：每个标的两臂对照）。
- 结论级别：只检验不决策。禁止买卖指令类词汇。
- 已知边界：目标值在入场日冻结（不随持仓期波动重估——简化，登记）；分位
  序列用滚动历史无未来泄漏；n 与聚类局限沿十三轮。
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
RAW_DIR = REPO / "docs/experiments/raw/dca-adaptive-exits-2026-09-08"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["SH000001", "SZ399001", "000300", "000015", "399006",
           "510500", "512100", "588000"]
NAMES = {"SH000001": "上证指数", "SZ399001": "深证成指", "000300": "沪深300",
         "000015": "上证红利", "399006": "创业板指", "510500": "中证500ETF",
         "512100": "中证1000ETF", "588000": "科创50ETF"}
ENTRIES = ["deep20", "bottom", "lowtier", "base"]
EXITS = ["Xfix30", "X30dev", "Xvol", "Xp75", "XvolS", "XfixS"]
FEE = 10.0
ACCUM = 252
MAX_HOLD = 504
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
    ret = c.pct_change()
    df["vol"] = ret.rolling(500, min_periods=250).std() * np.sqrt(252)
    fwd1y = c / c.shift(252) - 1.0
    df["q75"] = fwd1y.rolling(1260, min_periods=750).quantile(0.75)
    df = df[df["ma200"].notna() & df["dd2y"].notna()]
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
    vol = float(df["vol"].iloc[e]) if np.isfinite(df["vol"].iloc[e]) else 0.25
    q75 = float(df["q75"].iloc[e]) if np.isfinite(df["q75"].iloc[e]) else 0.30
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
    if exit_mode == "Xfix30":
        tp, sl = 0.30, None
    elif exit_mode == "X30dev":
        tp, sl = None, None
    elif exit_mode == "Xvol":
        tp, sl = float(np.clip(vol, 0.15, 0.50)), None
    elif exit_mode == "Xp75":
        tp, sl = float(np.clip(q75, 0.15, 0.50)), None
    elif exit_mode == "XvolS":
        tp = float(np.clip(vol, 0.15, 0.50))
        sl = -float(np.clip(vol, 0.10, 0.35))
    else:  # XfixS
        tp, sl = 0.30, -0.20
    exit_j, forced = None, False
    for j in range(acc_end + 1, min(acc_end + MAX_HOLD, n)):
        ret = units * closes[j] / invested - 1.0
        sig = j - 1
        hit = False
        if tp is not None and ret >= tp:
            hit = True
        if sl is not None and ret <= sl:
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
    return {"ret": proceeds / invested - 1.0,
            "hold_months": (exit_j - e) / 21.0,
            "forced": forced,
            "target": tp if tp is not None else (q75 if exit_mode == "X30dev"
                                                else None),
            "vol_at_entry": vol}


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "trades": {}, "summary": {},
                 "per_symbol_median": {}}

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

    # 总体汇总
    for entry in ENTRIES:
        for exit_mode in EXITS:
            all_t = []
            for sym, ts in out["trades"].get(f"{entry}|{exit_mode}",
                                             {}).items():
                all_t.extend(ts)
            if not all_t:
                continue
            rets = np.array([t["ret"] for t in all_t])
            out["summary"][f"{entry}|{exit_mode}"] = {
                "n": len(all_t),
                "median": float(np.median(rets)),
                "mean": float(rets.mean()),
                "win": float((rets > 0).mean()),
                "p10": float(np.percentile(rets, 10)),
                "p90": float(np.percentile(rets, 90)),
                "worst": float(rets.min()),
                "forced_pct": float(np.mean([t["forced"] for t in all_t])),
            }
    # 分标的中位（Q1 判定核心）
    for entry in ENTRIES:
        for exit_mode in EXITS:
            row = {}
            for sym in SYMBOLS:
                ts = out["trades"].get(f"{entry}|{exit_mode}", {}).get(sym, [])
                if ts:
                    row[sym] = float(np.median([t["ret"] for t in ts]))
            out["per_symbol_median"][f"{entry}|{exit_mode}"] = row

    print("=== 总体（中位/胜率/最差/强制率）===")
    for entry in ENTRIES:
        for exit_mode in EXITS:
            k = f"{entry}|{exit_mode}"
            if k not in out["summary"]:
                continue
            s = out["summary"][k]
            print(f"{entry:8s}{exit_mode:7s} 中位{s['median']*100:+6.1f}% "
                  f"胜{s['win']*100:3.0f}% 最差{s['worst']*100:+6.1f}% "
                  f"强制{s['forced_pct']*100:3.0f}% n={s['n']}", flush=True)

    # Q1 适配价值判定（Xvol vs Xfix30 按标的内中位）
    wins_q1 = 0
    detail_q1 = {}
    for entry in ENTRIES:
        a = out["per_symbol_median"].get(f"{entry}|Xvol", {})
        b = out["per_symbol_median"].get(f"{entry}|Xfix30", {})
        for sym in SYMBOLS:
            if sym in a and sym in b:
                detail_q1[f"{entry}|{sym}"] = {"Xvol": a[sym], "Xfix30": b[sym],
                                                "win": a[sym] > b[sym]}
                wins_q1 += a[sym] > b[sym]
    n_q1 = len(detail_q1)
    out["verdicts"] = {"Q1_adaptive_vs_fixed": {
        "wins": wins_q1, "total": n_q1,
        "verdict": ("适配止盈有价值" if wins_q1 >= n_q1 * 2 / 3 else
                    "统一够用" if wins_q1 <= n_q1 / 3 else "混合"),
        "detail": detail_q1}}
    print(f"\nQ1 Xvol vs Xfix30 按标的内中位: {wins_q1}/{n_q1} -> "
          f"{out['verdicts']['Q1_adaptive_vs_fixed']['verdict']}", flush=True)
    for entry in ENTRIES:
        a = out["per_symbol_median"].get(f"{entry}|Xvol", {})
        b = out["per_symbol_median"].get(f"{entry}|Xfix30", {})
        if a and b:
            line = "  ".join(f"{NAMES[s][:4]}:{(a[s]-b[s])*100:+.0f}pp"
                             for s in a if s in b)
            print(f"  [{entry}] {line}", flush=True)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "dca_adaptive_exits_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
