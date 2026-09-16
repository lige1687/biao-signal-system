# -*- coding: utf-8 -*-
"""AJ 任务：二元切换 vs 冠军三档 vs 机械周定投——跨大标的稳健性检验。

预注册判定标准（跑前写死，跑后不得改）：
- 标的网格（写死 6 个）：创业板指 399006、沪深300ETF 510300、中证1000ETF 512100、
  科创50ETF 588000、纳指 ^IXIC、标普500 ^GSPC。A 股用全A宽度（breadth_cn_all）、
  美股用 SP500 成分宽度（breadth_sp500），均为 b200（200 日均线宽度），与冠军三档
  同口径。美股宽度本地可得（1986-01→2026-08），无需降级为指数动量对照。
- 策略三臂（同起点同终点同费率，每标的用其行情与宽度对齐后的全样本）：
  1) 冠军三档 T3：n_bands=3, contrarian, low_edge=30, high_edge=70（档位线
     43.33/56.67）, gamma=1.0, min_trade=0.05——参数逐字复用
     raw/kuandu-quanzhan/champion_cyb.json；
  2) 二元 BIN：b200 ≤ 43.33 → 满仓，否则空仓（用 LadderParams n_bands=2、
     low_edge=high_edge=43.333 实现）；
  3) 机械周定投 DCA：初始资金 1.0 均分 n_shares = min(260, ceil(周数/2)) 份
     （口径逐字沿用 breadth-position-report-2026-08-27 的 S1），每周最后交易日
     收盘信号 → 次一交易日开盘买入一份，投完持有，闲置现金 0 收益。
  引擎统一 src/lei_signal/timing_backtest（T 收盘信号 → T+1 开盘执行）；
  费用按换手/买入名义额计，单边 {1bp, 10bp} 两档。
- 度量：终值（初始 1.0）、年化（252 交易日）、最大回撤、收益回撤性价比
  （年化 ÷ |最大回撤|，即 Calmar 的白话叫法）、换手名义倍数、费用拖累。
- 扰动（小邻域 ±2pp，非优化）：T3 边界 30/70±2（→ 28/68 与 32/72，档位线
  41.33/54.67 与 45.33/58.67）；BIN 线 43.33±2（→ 41.33 与 45.33）。
  每个扰动在各费率档重算。扰动只看排名方向是否翻转，不做任何择优。
- 判定单元：6 标的 × 2 费率 = 12 个基础格；每个基础格另配 2 个阈值扰动格
  （同费率），共 36 格。
- 三选一判定线（写死）：
  * 「二元优势稳健」= 同时满足：
    (a) ≥4/6 标的在全部 6 个格（2 费率 × {41.33, 43.33, 45.33} 三档二元线，
        三档臂用对应扰动档）中，二元终值 > 定投终值 且 二元终值 ≥ 三档终值；
    (b) 上述标的在 10bp 口径的基础格全部成立（不能只靠 1bp 撑）；
    (c) 没有任何标的出现「基础格二元 > 定投、但两个扰动方向都翻转到 ≤ 定投」
        的悬崖式翻转。
  * 「不稳健」= 在 12 个基础格中，「二元 > 定投 且 二元 ≥ 三档」成立的
    (标的,费率) 组合只覆盖 ≤1 个标的（优势集中在单一标的），或只在单一费率
    档成立且另一档全败。
  * 其余情况 = 「条件成立」，必须逐条写明成立条件（哪些标的/费率/阈值）。
- 结论级别：只检验不决策，不回答"现役三档要不要改"。禁止买卖指令类词汇。
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import (
    INSTRUMENTS,
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target

REPO = Path(__file__).resolve().parents[2]
RAW_DIR = REPO / "docs/experiments/raw/agent-AJ-binary-vs-tiered-vs-dca"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["399006", "510300", "512100", "588000", "^IXIC", "^GSPC"]
FEES = [1.0, 10.0]
CHAMP = LadderParams(
    indicator="b200", n_bands=3, direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)
BIN43 = LadderParams(
    indicator="b200", n_bands=2, direction="contrarian",
    low_edge=100.0 / 3.0 * 1.3, high_edge=100.0 / 3.0 * 1.3, gamma=1.0,
)  # 43.333：linspace(0,1,3)[1:-1]=[0.5] → edge=low+0.5*(high-low)=43.333
PERT_T3 = [(-2.0, "lo"), (2.0, "hi")]  # 边界 30/70 ±2
PERT_BIN = [-2.0, 2.0]  # 43.333 ±2


def cagr_maxdd(equity: pd.Series) -> tuple[float, float, float]:
    n = len(equity)
    yrs = n / 252.0
    final = float(equity.iloc[-1])
    cagr = final ** (1.0 / yrs) - 1.0 if final > 0 else -1.0
    peak = equity.cummax()
    mdd = float(((equity / peak) - 1.0).min())
    calmar = cagr / abs(mdd) if mdd < 0 else float("inf")
    return cagr, mdd, calmar


def run_dca(aligned: pd.DataFrame, fee_bps: float) -> dict:
    """机械周定投：初始 1.0 均分 min(260, ceil(周数/2)) 份，每周末信号次日开盘买一份。"""
    idx = aligned.index
    weeks = pd.Series(np.arange(len(idx)), index=idx).groupby(
        [idx.isocalendar().year, idx.isocalendar().week]
    ).max()  # 每个自然周最后一根 K 线的位置
    n_shares = min(260, math.ceil(len(weeks) / 2))
    amount = 1.0 / n_shares
    fee_rate = fee_bps * 1e-4
    opens = aligned["open"].to_numpy(float)
    cash, units, turnover, fees_paid = 1.0, 0.0, 0.0, 0.0
    equity = np.empty(len(idx))
    buy_pos = sorted(weeks.tolist())[:n_shares]
    buy_set = set(p + 1 for p in buy_pos if p + 1 < len(idx))
    for i in range(len(idx)):
        if i in buy_set:
            if cash >= amount - 1e-12:
                fee = amount * fee_rate
                cash -= amount
                units += (amount - fee) / opens[i]
                fees_paid += fee
                turnover += amount
        equity[i] = cash + units * aligned["close"].to_numpy(float)[i]
    eq = pd.Series(equity, index=idx)
    cagr, mdd, calmar = cagr_maxdd(eq)
    return {
        "n_shares": n_shares, "final": float(eq.iloc[-1]),
        "cagr": cagr, "mdd": mdd, "calmar": calmar,
        "turnover_notional": turnover, "fees": fees_paid,
    }


def run_signal(aligned: pd.DataFrame, params: LadderParams, fee_bps: float) -> dict:
    target = ladder_target(aligned[params.indicator], params)
    res = simulate(aligned, target, fee_bps=fee_bps, min_trade=0.05)
    cagr, mdd, calmar = cagr_maxdd(res.daily["equity"])
    return {
        "final": float(res.daily["equity"].iloc[-1]),
        "cagr": cagr, "mdd": mdd, "calmar": calmar,
        "n_trades": len(res.trades),
        "turnover_notional": float(sum(t["turnover"] for t in res.trades)),
        "fees": float(sum(t["fee"] for t in res.trades)),
        "time_in_market": float((res.daily["weight"] > 0).mean()),
    }


def load_aligned(symbol: str) -> pd.DataFrame:
    spec = INSTRUMENTS[symbol]
    bars = load_index_bars(symbol)
    breadth = load_breadth(spec.breadth)
    aligned = align_index_breadth(bars, breadth)
    return aligned[aligned["b200"].notna()]


def main() -> None:
    out = {"symbols": {}, "criteria_doc": __doc__}
    for sym in SYMBOLS:
        aligned = load_aligned(sym)
        rec = {
            "start": str(aligned.index[0].date()),
            "end": str(aligned.index[-1].date()),
            "n_days": len(aligned),
            "cells": {},
        }
        for fee in FEES:
            for label, lp in [
                ("t3_base", CHAMP),
                ("bin_base", BIN43),
            ] + [
                (f"t3_pert_{'m' if d < 0 else 'p'}2", LadderParams(
                    indicator="b200", n_bands=3, direction="contrarian",
                    low_edge=30.0 + d, high_edge=70.0 + d, gamma=1.0))
                for d, _ in PERT_T3
            ] + [
                (f"bin_pert_{'m' if d < 0 else 'p'}2", LadderParams(
                    indicator="b200", n_bands=2, direction="contrarian",
                    low_edge=100.0 / 3.0 * 1.3 + d, high_edge=100.0 / 3.0 * 1.3 + d))
                for d in PERT_BIN
            ]:
                key = f"{label}_fee{int(fee)}"
                rec["cells"][key] = run_signal(aligned, lp, fee)
            rec["cells"][f"dca_fee{int(fee)}"] = run_dca(aligned, fee)
        out["symbols"][sym] = rec
        print(f"[{sym}] {rec['start']}→{rec['end']} done", flush=True)

    # ---- 预注册判定 ----
    verdict_cells = {}
    for sym, rec in out["symbols"].items():
        for fee in FEES:
            f = int(fee)
            b = rec["cells"][f"bin_base_fee{f}"]["final"]
            t = rec["cells"][f"t3_base_fee{f}"]["final"]
            d = rec["cells"][f"dca_fee{f}"]["final"]
            verdict_cells[f"{sym}|{f}"] = {
                "bin_gt_dca": b > d, "bin_ge_t3": b >= t, "t3_gt_dca": t > d,
                "finals": {"bin": b, "t3": t, "dca": d},
            }
    # 全 6 格通过（2 费率 × 3 阈值，三档臂用对应扰动档）
    full_pass, tenbp_base_pass, cliff_flips = [], [], []
    for sym, rec in out["symbols"].items():
        ok_all, ok_10bp_base, flips = True, True, 0
        for fee in FEES:
            f = int(fee)
            pairs = [("bin_base", "t3_base"), ("bin_pert_m2", "t3_pert_m2"),
                     ("bin_pert_p2", "t3_pert_p2")]
            for bl, tl in pairs:
                b = rec["cells"][f"{bl}_fee{f}"]["final"]
                t = rec["cells"][f"{tl}_fee{f}"]["final"]
                d = rec["cells"][f"dca_fee{f}"]["final"]
                ok_all &= (b > d) and (b >= t)
            if f == 10:
                b = rec["cells"]["bin_base_fee10"]["final"]
                t = rec["cells"]["t3_base_fee10"]["final"]
                d = rec["cells"]["dca_fee10"]["final"]
                ok_10bp_base &= (b > d) and (b >= t)
        # 悬崖翻转：基础格赢定投但两个扰动方向都翻 ≤ 定投
        for fee in FEES:
            f = int(fee)
            b0 = rec["cells"][f"bin_base_fee{f}"]["final"]
            d0 = rec["cells"][f"dca_fee{f}"]["final"]
            bm = rec["cells"][f"bin_pert_m2_fee{f}"]["final"]
            bp = rec["cells"][f"bin_pert_p2_fee{f}"]["final"]
            if b0 > d0 and bm <= d0 and bp <= d0:
                flips += 1
        if ok_all:
            full_pass.append(sym)
        if ok_10bp_base:
            tenbp_base_pass.append(sym)
        cliff_flips.append((sym, flips))
    base_pass_syms = [
        sym for sym in out["symbols"]
        if all(verdict_cells[f"{sym}|{f}"]["bin_gt_dca"]
               and verdict_cells[f"{sym}|{f}"]["bin_ge_t3"] for f in (1, 10))
    ]
    out["verdict_inputs"] = {
        "verdict_cells": verdict_cells,
        "full_pass_symbols": full_pass,
        "tenbp_base_pass_symbols": tenbp_base_pass,
        "base_pass_symbols_both_fees": base_pass_syms,
        "cliff_flips": dict(cliff_flips),
    }
    n_full, n_base = len(full_pass), len(base_pass_syms)
    if n_full >= 4 and len(tenbp_base_pass) >= 4 and all(
        v == 0 for _, v in cliff_flips
    ):
        verdict = "二元优势稳健"
    elif n_base <= 1:
        verdict = "不稳健"
    else:
        verdict = "条件成立"
    out["verdict"] = verdict
    print("VERDICT:", verdict, "| full_pass:", full_pass,
          "| base_pass:", base_pass_syms)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "binary_vs_tiered_vs_dca_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
