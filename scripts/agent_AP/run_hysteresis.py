# -*- coding: utf-8 -*-
"""AP 任务：滞回带（hysteresis）能否修复二元宽度切换的阈值脆弱性。

背景（AJ 任务 docs/experiments/binary-vs-tiered-vs-dca-2026-09-03.md）：
二元切换（b200<=43.33 满仓否则空仓）在 A 股 4/4 标的赢定投，但进仓线下移
2pp（41.33）即翻车（中证1000/科创50 输定投）。本任务检验：加滞回带后，二元
对阈值（进仓线）位置的敏感度是否显著下降。这是稳健性工程检验，不是收益优化
——判定对象是"跨进仓线的结果离散度"，禁止把任何参数组合表述为推荐或最优。

== 口径（与 AJ 完全一致）==
- 标的（写死 4 个 A 股）：创业板指 399006、沪深300ETF 510300、中证1000ETF
  512100、科创50ETF 588000；宽度全部用 breadth_cn_all（全A、200 日均线口径，
  b200），行情×宽度对齐后取 b200 非 NaN 全样本（load_aligned 逐字复用 AJ）。
- 引擎：src/lei_signal/timing_backtest（T 收盘信号 → T+1 开盘成交，无未来函数；
  min_trade=0.05 与 AJ 相同）；费用单边 {1bp, 10bp}。定投臂 run_dca 逐字复用
  AJ（初始 1.0 均分 min(260, ceil(周数/2)) 份每周投一份，闲置现金 0 收益）。
- 网格（写死，禁止扩展）：进仓线 E ∈ {41.3333, 43.3333, 45.3333}（=AJ 的
  100/3*1.3 ± 2，逐点同值）× 滞回带 b ∈ {0, 1, 2, 3}pp × 费率 {1bp, 10bp}
  × 4 标的 = 96 格。

== 滞回实现口径（跑前写死，含解释）==
- 任务书原文"出仓线 = 进仓线 − b"按字面实现（进仓 b<=E、出仓 b>E−b）是退化
  的：出仓线低于进仓线时，宽度落在 (E−b, E] 区间内系统每日翻转（今天进、
  明天出），抖动反而比单线更严重，与任务书"消除围绕单线的反复抖动""晚出仓
  要挨跌"的表述直接矛盾。因此按工程标准施密特触发器实现（带在进仓线上方）：
  **进仓：b200 <= E（进仓线三个格值原样使用，不随 b 移动）；出仓：b200 > E+b
  （要离开满仓，宽度必须回升穿过整条带）。** b=0 时严格退化为 AJ 的原始二元
  （与 AJ 已发布数字逐格对账，见 parity 检查）。本脚本另跑 1 格字面口径
  （E=43.3333, b=2）作为附录证据，量化其退化（逐日翻转、费用爆炸），不进判定。
- 状态机逐日纯前向：state=0 起步；state==0 且 b<=E → 1；state==1 且 b>E+b → 0；
  b 为 NaN 日沿用状态（A 股样本经 load_aligned 已无 NaN）。

== 度量（跑前写死）==
- 每格终值 V(sym, fee, E, b)（初始 1.0 的倍数）；辅以年化/最大回撤/交易次数/
  在场时间（描述用，不进判定）。
- 离散度（主度量，写死用对数极差）：logrange(sym,fee,b) = ln(max_E V / min_E V)，
  E 取三个进仓线；辅度量（描述用）：绝对差距 gap = max_E V − min_E V。
- 赢定投格：V(sym,fee,E,b) > DCA(sym,fee)。每档 b 共 24 格（4 标的×3 线×2 费），
  其中"线放错"格（E≠43.3333）16 格。
- 滞回代价：cost(sym,fee,b) = V(sym,fee,43.3333,b) / V(sym,fee,43.3333,0)。

== 预注册三选一判定线（跑前写死，跑完不得回头调；数值依据全部来自 AJ 已
   发布的 b=0 基线数字，与本次 b>0 结果无关）==
- 「滞回有效」= 存在同一档 b* ∈ {1,2,3} 同时满足：
  (D) 离散度收窄：8 个（标的×费率）层中 ≥6 层 logrange(b*) < logrange(0)，
      且 8 层 logrange(b*) 的中位数 ≤ 0.5 × logrange(0) 的中位数。
      [依据：AJ b=0 的 8 层对数极差约为 0.09–0.71、中位 ≈0.29，即进仓线挪 2pp
      终值摆动 ~34%；中位对定投优势 ≈37%（ln 1.37≈0.31，恰与极差同量级）——
      只有把极差压掉一半（摆动 ~16%，明显小于优势幅度），"线放错 2pp"才不再
      改变结论方向。]
  (C) 代价容忍：E=43.3333 下 8 格 cost(b*) 的中位数 ≥ 0.90 且全部 ≥ 0.75。
      [依据：中位标的对定投优势 ≈37%，吃掉 ≤10% 不改变赢面；单格 ≥25% 的让渡
      会把最薄的科创50 10bp（优势仅 15.4%）直接翻负——0.75 是单格灾难线。]
  (W) 赢定投恢复：b* 档 24 格中赢定投 ≥ 23，且 16 个"线放错"格中赢定投 ≥ 15。
      [依据：AJ b=0 为 21/24（失格 3 个：512100@41.3/10bp、588000@41.3/1bp、
      588000@41.3/10bp）、线放错格 13/16；≥23 = 至少救回 2 个且全网格至多
      1 个失格。]
- 「滞回无效」= 下列任一：
  (N1) 不存在 b ∈ {1,2,3} 满足 (D)（离散度根本不收窄）；或
  (N2) 满足 (D) 的每一档都不满足 (C)（收窄但以不可接受的收益代价换来）。
- 其余情形 = 「证据不足」（如：收窄成立、代价合格，但 (W) 不达；或层间方向
  不一致勉强过半）。

== 判定输出顺序 ==
全部 96 格数字、度量表、代价表先落盘，判定最后打印——禁止先看结果再定线。
双跑哈希：PYTHONHASHSEED=0 / 42 各跑一次，sha256(canonical json) 必须逐位一致。
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AJ"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    INSTRUMENTS,
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from run_robustness import cagr_maxdd, load_aligned, run_dca  # noqa: E402  逐字复用 AJ

RAW_DIR = REPO / "docs/experiments/raw/agent-AP-binary-hysteresis"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["399006", "510300", "512100", "588000"]
FEES = [1.0, 10.0]
ENTRIES = [100.0 / 3.0 * 1.3 - 2.0, 100.0 / 3.0 * 1.3, 100.0 / 3.0 * 1.3 + 2.0]
BANDS = [0.0, 1.0, 2.0, 3.0]
AJ_RAW = (
    REPO / "docs/experiments/raw/agent-AJ-binary-vs-tiered-vs-dca/"
    "binary_vs_tiered_vs_dca_results.json"
)


def hysteresis_target(
    b: pd.Series, entry: float, band: float, exit_side: str = "above"
) -> pd.Series:
    """滞回二元目标仓位（T 收盘值，引擎 T+1 开盘执行）。

    exit_side='above'（主实现，施密特触发器）：state==0 且 b<=entry → 进仓；
    state==1 且 b>entry+band → 出仓。b=0 严格退化为"b<=entry 满仓否则空仓"。
    exit_side='below'（附录·任务书字面）：出仓线 entry−band（低于进仓线，
    带内逐日翻转——用于量化字面口径的退化，不进判定）。
    """
    vals = b.to_numpy(dtype=float)
    out = np.zeros(len(vals))
    state = 0.0
    exit_line = entry + band if exit_side == "above" else entry - band
    for i, x in enumerate(vals):
        if not np.isnan(x):
            if state == 0.0 and x <= entry:
                state = 1.0
            elif state == 1.0 and x > exit_line:
                state = 0.0
        out[i] = state
    return pd.Series(out, index=b.index)


def run_signal(aligned: pd.DataFrame, target: pd.Series, fee_bps: float) -> dict:
    res = simulate(aligned, target, fee_bps=fee_bps, min_trade=0.05)
    cagr, mdd, calmar = cagr_maxdd(res.daily["equity"])
    return {
        "final": float(res.daily["equity"].iloc[-1]),
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "n_trades": len(res.trades),
        "time_in_market": float((res.daily["weight"] > 0).mean()),
    }


def median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "symbols": {}, "config": {
        "entries": ENTRIES, "bands": BANDS, "fees": FEES, "symbols": SYMBOLS,
    }}

    # ---- 96 格主网格 + 定投基线 + 字面口径附录 ----
    for sym in SYMBOLS:
        aligned = load_aligned(sym)
        rec = {
            "start": str(aligned.index[0].date()),
            "end": str(aligned.index[-1].date()),
            "n_days": len(aligned),
            "dca": {}, "cells": {},
        }
        for fee in FEES:
            f = int(fee)
            rec["dca"][f] = run_dca(aligned, fee)
            for E in ENTRIES:
                for band in BANDS:
                    key = f"E{E:.4f}_b{int(band)}_fee{f}"
                    tgt = hysteresis_target(aligned["b200"], E, band)
                    rec["cells"][key] = run_signal(aligned, tgt, fee)
            # 附录：任务书字面口径（出仓线 = E − band），仅 E=43.33, b=2
            tgt_lit = hysteresis_target(
                aligned["b200"], ENTRIES[1], 2.0, exit_side="below"
            )
            rec["cells"][f"LITERAL_E43.3333_b2_fee{f}"] = run_signal(
                aligned, tgt_lit, fee
            )
        out["symbols"][sym] = rec
        print(f"[{sym}] {rec['start']}->{rec['end']} done", flush=True)

    # ---- b=0 parity 检查：与 AJ 已发布二元数字逐格对账 ----
    aj = json.loads(AJ_RAW.read_text())
    parity = []
    for sym in SYMBOLS:
        for fee in FEES:
            f = int(fee)
            for E, aj_key in [
                (ENTRIES[0], f"bin_pert_m2_fee{f}"),
                (ENTRIES[1], f"bin_base_fee{f}"),
                (ENTRIES[2], f"bin_pert_p2_fee{f}"),
            ]:
                mine = out["symbols"][sym]["cells"][f"E{E:.4f}_b0_fee{f}"]["final"]
                theirs = aj["symbols"][sym]["cells"][aj_key]["final"]
                parity.append(
                    {"sym": sym, "fee": f, "E": E,
                     "mine": mine, "aj": theirs, "absdiff": abs(mine - theirs)}
                )
    max_parity_diff = max(p["absdiff"] for p in parity)
    out["parity_vs_AJ"] = {"n_cells": len(parity), "max_absdiff": max_parity_diff}

    # ---- 度量（预注册）----
    metrics: dict = {"logrange": {}, "gap": {}, "win_dca": {}, "cost": {}}
    for sym in SYMBOLS:
        for fee in FEES:
            f = int(fee)
            dca_final = out["symbols"][sym]["dca"][f]["final"]
            for band in BANDS:
                b = int(band)
                finals = [
                    out["symbols"][sym]["cells"][f"E{E:.4f}_b{b}_fee{f}"]["final"]
                    for E in ENTRIES
                ]
                mx, mn = max(finals), min(finals)
                metrics["logrange"][f"{sym}|fee{f}|b{b}"] = math.log(mx / mn)
                metrics["gap"][f"{sym}|fee{f}|b{b}"] = mx - mn
                metrics["win_dca"][f"{sym}|fee{f}|b{b}"] = {
                    f"E{E:.4f}": (
                        out["symbols"][sym]["cells"][f"E{E:.4f}_b{b}_fee{f}"]["final"]
                        > dca_final
                    )
                    for E in ENTRIES
                }
                v_b = out["symbols"][sym]["cells"][f"E{43.3333:.4f}_b{b}_fee{f}"]["final"]
                v_0 = out["symbols"][sym]["cells"][f"E{43.3333:.4f}_b0_fee{f}"]["final"]
                metrics["cost"][f"{sym}|fee{f}|b{b}"] = v_b / v_0
    out["metrics"] = metrics

    # ---- 预注册判定（最后计算）----
    layers = [f"{s}|fee{f}" for s in SYMBOLS for f in (1, 10)]
    lr = {b: [metrics["logrange"][f"{l}|b{b}"] for l in layers] for b in (0, 1, 2, 3)}
    med_lr = {b: median(lr[b]) for b in (0, 1, 2, 3)}

    def win_counts(b: int) -> dict:
        total = wrong = wrong_pass = 0
        for sym in SYMBOLS:
            for f in (1, 10):
                for E in ENTRIES:
                    w = metrics["win_dca"][f"{sym}|fee{f}|b{b}"][f"E{E:.4f}"]
                    total += w
                    if abs(E - ENTRIES[1]) > 1e-9:
                        wrong += 1
                        wrong_pass += w
        return {"total_pass_of_24": total, "wrongline_pass_of_16": wrong_pass}

    wc = {b: win_counts(b) for b in (0, 1, 2, 3)}

    cond_D, cond_C, cond_W = {}, {}, {}
    for b in (1, 2, 3):
        narrow = sum(1 for l in layers
                     if metrics["logrange"][f"{l}|b{b}"] < metrics["logrange"][f"{l}|b0"])
        cond_D[b] = {
            "layers_narrowed_of_8": narrow,
            "median_logrange": med_lr[b],
            "median_logrange_b0": med_lr[0],
            "half_median_ok": med_lr[b] <= 0.5 * med_lr[0],
            "pass": narrow >= 6 and med_lr[b] <= 0.5 * med_lr[0],
        }
        costs = [metrics["cost"][f"{l}|b{b}"] for l in layers]
        cond_C[b] = {
            "costs": {l: metrics["cost"][f"{l}|b{b}"] for l in layers},
            "median_cost": median(costs),
            "min_cost": min(costs),
            "pass": median(costs) >= 0.90 and min(costs) >= 0.75,
        }
        cond_W[b] = dict(wc[b])
        cond_W[b]["pass"] = wc[b]["total_pass_of_24"] >= 23 and wc[b]["wrongline_pass_of_16"] >= 15

    d_pass_bands = [b for b in (1, 2, 3) if cond_D[b]["pass"]]
    effective = [b for b in d_pass_bands if cond_C[b]["pass"] and cond_W[b]["pass"]]
    if effective:
        verdict = "滞回有效"
    elif not d_pass_bands:
        verdict = "滞回无效(N1:离散度不收窄)"
    elif all(not cond_C[b]["pass"] for b in d_pass_bands):
        verdict = "滞回无效(N2:收窄但代价不可接受)"
    else:
        verdict = "证据不足"

    out["verdict_inputs"] = {
        "median_logrange_by_band": med_lr,
        "win_counts_by_band": wc,
        "cond_D": cond_D,
        "cond_C": cond_C,
        "cond_W": cond_W,
        "parity_vs_AJ": out["parity_vs_AJ"],
    }
    out["verdict"] = verdict

    # 全部数字落盘在前，判定打印在后（stdout 顺序即证据顺序）
    payload = json.dumps(out, ensure_ascii=False, sort_keys=True, default=float)
    h = hashlib.sha256(payload.encode()).hexdigest()
    (RAW_DIR / "binary_hysteresis_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float)
    )
    (RAW_DIR / "HASH.txt").write_text(h + "\n")

    print("VERDICT:", verdict)
    print("median logrange by band:", {b: round(med_lr[b], 4) for b in med_lr})
    print("win counts by band:", wc)
    print("parity max absdiff vs AJ:", max_parity_diff)
    print("HASH:", h)


if __name__ == "__main__":
    main()
