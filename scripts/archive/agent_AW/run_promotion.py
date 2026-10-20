# -*- coding: utf-8 -*-
"""AW 任务：滞回二元（进 43.3 / 带 2pp / 出仓线 = 进仓线 + 带）的转正验证——
与现役三档冠军的正面对比。证据供给任务：判定对象是"证据格局"，不是"谁更好"
的单选；本脚本不回答"要不要换"，那是用户的决策。

== 三臂（全部逐字复用既有认证实现，禁止重写引擎）==
  - T3（现役冠军三档）：LadderParams(n_bands=3, contrarian, low_edge=30,
    high_edge=70, gamma=1.0)，b200 档位线 43.33/56.67，满/半/空三档，
    min_trade=0.05（与 AJ 三档臂逐字同参，参数冻结来自 champion_cyb.json）。
  - HYB（候选·滞回二元）：AP 施密特触发器逐字 import（hysteresis_target，
    exit_side='above'）：进仓 b200 <= 43.3333，出仓 b200 > 45.3333（带宽
    2pp，AP 唯一同时过 (D)(C)(W) 三线的档；参数冻结，禁止再调）。
  - BIN0（对照锚·纯二元）：hysteresis_target(b, E, band=0)，严格退化为
    "b200<=43.3333 满仓否则空仓"（AP 已 parity 对账 = AJ 原始二元）。
  全部 T 收盘信号 → T+1 开盘成交（引擎 simulate），费率单边 {1bp, 10bp}。

== 标的（写死）==
  主判定：399006 创业板指。外推性：510300 沪深300ETF、512100 中证1000ETF、
  588000 科创50ETF。样本窗逐字沿用 AJ 的 load_aligned（行情×宽度对齐后取
  b200 非 NaN 全样本）；宽度全部 breadth_cn_all（全A、b200）。

== 度量（写死）==
  每格（4 标的 × 2 费率 × 3 臂 = 24 格）：终值（初始 1.0 的倍数）、年化、
  最大回撤、收益回撤性价比（年化÷|最大回撤|）、换手名义倍数（逐笔 |Δ仓位|
  之和）、交易次数、在场时间。
  分段稳定性：样本对半切（位置 mid=n//2；前半 = 第 0..mid-1 日，起点 1.0；
  后半 = 第 mid-1..n-1 日，边界日共享，两臂同窗故对比精确），各臂分段年化；
  方向一致性 = (HYB−T3) 分段年化差在前/后半是否同号（(HYB−BIN0) 同表描述）。

== 脆弱性上下文（AR 报告时段，日期直接取用）==
  2018-01-24→2018-10-18（AR 五大回撤之 #1，组合 −28.51%）与
  2022-07-04→2024-02-05（#2，组合 −25.32%）。在创业板 399006、费率 10bp
  （AR 组合主仓费用口径）下，对三臂各算时段收益（窗口前最后收盘净值→窗口
  末净值）与窗口内最大回撤；引擎 benchmark（持有）作参考行。

== parity 对账（防实现漂移）==
  本脚本 BIN0 与 T3 的 8 层终值 vs AJ 已发布 raw（bin_base / t3_base）
  逐层对账；HYB 与 BIN0 的 8 层终值 vs AP 已发布 raw（E43.3333_b2 /
  E43.3333_b0）逐层对账。期望最大绝对差 = 0。

== 预注册三选一判定线（跑前写死，跑完不得回头调；数值依据全部来自
   AJ/AP/AU 已发布数字，与本次输出无关）==
  层面：8 层 = 4 标的 × 2 费率；主标的创业板 399006 占 2 层，其余 6 层外推。
  基本量：win(layer) = HYB 终值 > T3 终值；
          cost(layer) = T3 年化 − HYB 年化（pp，正 = 滞回让出收益）；
          mdd_gain(layer) = HYB 最大回撤 − T3 最大回撤（小数，正 = 滞回更浅）。

  A「证据支持候选成立」= A1 ∧ A2 ∧ A3：
   A1 收益代价容忍（主标的）：创业板两费率层 cost 均 ≤ 1.5pp。
      [依据：AJ 已发布创业板二元对定投年化优势 ≈6.9pp（14.5% vs 7.6%，1bp），
      1.5pp ≈ 优势的 1/5，是"简化执行形态"愿意付出的明确上限；AP 已测 2pp
      带代价中位 +1.6%、AU 已测创业板滞回年化反而更高（13.9% vs 13.0%，10bp），
      此线主要防本次复跑出现回归性退化。]
   A2 明确占优维度（主标的，回撤或稳健性至少一项）：
    A2a 回撤占优：创业板至少一层 mdd_gain ≥ +0.02（浅 2pp 以上），且两层
        mdd_gain 均 > −0.02（不得净恶化 2pp 以上）。
        [依据：2pp 为回撤口径上有体感的最小差异（AR 报告修复时长/深度皆以
        pp 计），AJ 已发布科创50 二元较三档回撤浅 8-10pp、创业板二元浅 2-3pp，
        滞回方向应保持；−0.02 容忍与 AU J3 同型。]
    A2b 稳健占优：(i) 创业板两费率的 (HYB−T3) 年化差对半分段同号（前/后半
        方向一致——防"全靠某一段行情撑结论"），且 (ii) 创业板至少一费率层
        HYB 交易次数较 BIN0 下降 ≥20%。
        [依据：(i) 分段同号是 AJ"分段稳定性"指标的自然形式；(ii) AP 已测
        43.3 线交易次数 −27%（151→111），此处复核滞回确实消抖，若消抖消失
        则候选形态与纯二元无异、转正无意义。]
   A3 外推一致：6 个外推层中 win ≥ 4，且不存在任何标的两费率层 HYB 终值
      都 < 0.95 × T3 终值。
      [依据：AJ 已显示 512100 上 T3 ≥ 二元（4.49 vs 4.42，1bp）为已知格局，
      容许单标的小幅让渡；0.95 线与 AU J2 同型（"低不过 5%"）。]

  B「证据不支持」= B1 ∨ B3（与任务书口径逐字对应：收益代价超线或外推翻转）：
   B1 = 创业板任一层 cost > 1.5pp（收益代价超线）；
   B3 = 外推翻转：6 外推层中 win < 3（≥4 层输）且其中 ≥2 层 HYB 终值
        < 0.95 × T3 终值（不仅输且输得实质）。

  C「混合/中间态」= 其余情形（含：主标的与外推方向相反；或 A2 占优维度
    不成立但代价与外推均在界内的中间态），逐项写明各自格局。

  判定对象是"证据格局"：A ≠ "应替换"（那是用户决策），B ≠ "三档永远保持"。
  判定输出顺序：全部数字先落盘，判定最后打印。双跑哈希 PYTHONHASHSEED=0/42
  逐位一致。红线：参数冻结（43.3/56.7/2pp 全部来自已验证值），不产生买卖
  指令（满仓/空仓指目标仓位 1.0/0 的形态描述）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AJ"))
sys.path.insert(0, str(REPO / "scripts" / "agent_AP"))

from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target  # noqa: E402
from run_robustness import cagr_maxdd, load_aligned  # noqa: E402  AJ 逐字复用
from run_hysteresis import hysteresis_target  # noqa: E402  AP 逐字复用

RAW_DIR = REPO / "docs/experiments/raw/agent-AW-hysteresis-promotion"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["399006", "510300", "512100", "588000"]
MAIN = "399006"
FEES = [1.0, 10.0]
ENTRY = 100.0 / 3.0 * 1.3  # 43.3333，AJ/AP 同值，冻结
BAND = 2.0                  # AP 唯一全过档，冻结
T3_PARAMS = LadderParams(
    indicator="b200", n_bands=3, direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)
AR_WINDOWS = [
    ("2018-01-24", "2018-10-18"),   # AR #1 组合 −28.51%
    ("2022-07-04", "2024-02-05"),   # AR #2 组合 −25.32%
]
AR_FEE = 10.0  # AR 组合主仓费用口径
AJ_RAW = (
    REPO / "docs/experiments/raw/agent-AJ-binary-vs-tiered-vs-dca"
    / "binary_vs_tiered_vs_dca_results.json"
)
AP_RAW = (
    REPO / "docs/experiments/raw/agent-AP-binary-hysteresis"
    / "binary_hysteresis_results.json"
)


def run_arm(aligned: pd.DataFrame, target: pd.Series, fee_bps: float) -> tuple[dict, np.ndarray, np.ndarray]:
    res = simulate(aligned, target, fee_bps=fee_bps, min_trade=0.05)
    eq = res.daily["equity"]
    cagr, mdd, calmar = cagr_maxdd(eq)
    metrics = {
        "final": float(eq.iloc[-1]),
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "n_trades": len(res.trades),
        "turnover_notional": float(sum(t["turnover"] for t in res.trades)),
        "fees": float(sum(t["fee"] for t in res.trades)),
        "time_in_market": float((res.daily["weight"] > 0).mean()),
    }
    return metrics, eq.to_numpy(dtype=float), res.daily["benchmark"].to_numpy(dtype=float)


def seg_cagr(growth: float, n_days: int) -> float:
    if growth <= 0 or n_days <= 0:
        return -1.0
    return growth ** (252.0 / n_days) - 1.0


def window_stats(eq: np.ndarray, idx: pd.DatetimeIndex, start: str, end: str) -> dict:
    i0 = int(idx.searchsorted(pd.Timestamp(start)))
    i1 = int(idx.searchsorted(pd.Timestamp(end), side="right")) - 1
    if i0 <= 0 or i1 < i0:
        return {"available": False}
    pre = eq[i0 - 1]
    seg = eq[i0:i1 + 1]
    peak = np.maximum.accumulate(seg)
    mdd = float(((seg / peak) - 1.0).min())
    return {
        "available": True,
        "start": str(idx[i0].date()),
        "end": str(idx[i1].date()),
        "n_days": int(i1 - i0 + 1),
        "period_return": float(seg[-1] / pre - 1.0),
        "mdd_in_window": mdd,
    }


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "config": {
        "symbols": SYMBOLS, "main": MAIN, "fees": FEES,
        "entry": ENTRY, "band": BAND, "t3": str(T3_PARAMS),
        "ar_windows": AR_WINDOWS, "ar_fee": AR_FEE,
    }, "symbols": {}}
    equity_store: dict[tuple, np.ndarray] = {}
    bench_store: dict[tuple, np.ndarray] = {}

    for sym in SYMBOLS:
        aligned = load_aligned(sym)
        idx = aligned.index
        rec = {
            "start": str(idx[0].date()), "end": str(idx[-1].date()),
            "n_days": len(idx), "cells": {}, "split_half": {}, "ar_windows": {},
        }
        t3_tgt = ladder_target(aligned["b200"], T3_PARAMS)
        hyb_tgt = hysteresis_target(aligned["b200"], ENTRY, BAND)
        bin0_tgt = hysteresis_target(aligned["b200"], ENTRY, 0.0)
        for fee in FEES:
            f = int(fee)
            for arm, tgt in (("t3", t3_tgt), ("hyb", hyb_tgt), ("bin0", bin0_tgt)):
                m, eq, bh = run_arm(aligned, tgt, fee)
                rec["cells"][f"{arm}_fee{f}"] = m
                equity_store[(sym, f, arm)] = eq
                bench_store[(sym, f, arm)] = bh
            # 分段稳定性（对半切，边界日共享，两臂同窗）
            n = rec["n_days"]
            mid = n // 2
            half = {}
            for arm in ("t3", "hyb", "bin0"):
                eq = equity_store[(sym, f, arm)]
                h1 = seg_cagr(eq[mid - 1] / eq[0], mid)
                h2 = seg_cagr(eq[-1] / eq[mid - 1], n - mid + 1)
                half[arm] = {"h1_cagr": h1, "h2_cagr": h2,
                             "split_date": str(idx[mid - 1].date())}
            d_hyb_t3 = {
                "h1_diff": half["hyb"]["h1_cagr"] - half["t3"]["h1_cagr"],
                "h2_diff": half["hyb"]["h2_cagr"] - half["t3"]["h2_cagr"],
            }
            d_hyb_bin0 = {
                "h1_diff": half["hyb"]["h1_cagr"] - half["bin0"]["h1_cagr"],
                "h2_diff": half["hyb"]["h2_cagr"] - half["bin0"]["h2_cagr"],
            }
            d_hyb_t3["same_sign"] = (
                (d_hyb_t3["h1_diff"] > 0) == (d_hyb_t3["h2_diff"] > 0)
            )
            d_hyb_bin0["same_sign"] = (
                (d_hyb_bin0["h1_diff"] > 0) == (d_hyb_bin0["h2_diff"] > 0)
            )
            rec["split_half"][f"fee{f}"] = {
                "split_date": half["hyb"]["split_date"],
                "cagr": half, "diff_hyb_vs_t3": d_hyb_t3,
                "diff_hyb_vs_bin0": d_hyb_bin0,
            }
        # AR 脆弱时段（仅主标的创业板进入判定叙事；其余标的同表描述）
        if sym == MAIN:
            f = int(AR_FEE)
            for w_start, w_end in AR_WINDOWS:
                key = f"{w_start}_{w_end}"
                rec["ar_windows"][key] = {
                    arm: window_stats(equity_store[(sym, f, arm)], idx, w_start, w_end)
                    for arm in ("t3", "hyb", "bin0")
                }
                rec["ar_windows"][key]["hold_benchmark"] = window_stats(
                    bench_store[(sym, f, "t3")], idx, w_start, w_end
                )
        out["symbols"][sym] = rec
        print(f"[{sym}] {rec['start']}->{rec['end']} done", flush=True)

    # ---- parity 对账（AJ bin_base/t3_base；AP E43.3333_b0/b2）----
    aj = json.loads(AJ_RAW.read_text())
    ap = json.loads(AP_RAW.read_text())
    parity = {"vs_AJ": [], "vs_AP": []}
    for sym in SYMBOLS:
        for fee in FEES:
            f = int(fee)
            mine_bin = out["symbols"][sym]["cells"][f"bin0_fee{f}"]["final"]
            mine_t3 = out["symbols"][sym]["cells"][f"t3_fee{f}"]["final"]
            mine_hyb = out["symbols"][sym]["cells"][f"hyb_fee{f}"]["final"]
            parity["vs_AJ"].append({
                "sym": sym, "fee": f, "arm": "bin0",
                "mine": mine_bin, "ref": aj["symbols"][sym]["cells"][f"bin_base_fee{f}"]["final"],
            })
            parity["vs_AJ"].append({
                "sym": sym, "fee": f, "arm": "t3",
                "mine": mine_t3, "ref": aj["symbols"][sym]["cells"][f"t3_base_fee{f}"]["final"],
            })
            parity["vs_AP"].append({
                "sym": sym, "fee": f, "arm": "hyb",
                "mine": mine_hyb,
                "ref": ap["symbols"][sym]["cells"][f"E{ENTRY:.4f}_b2_fee{f}"]["final"],
            })
            parity["vs_AP"].append({
                "sym": sym, "fee": f, "arm": "bin0",
                "mine": mine_bin,
                "ref": ap["symbols"][sym]["cells"][f"E{ENTRY:.4f}_b0_fee{f}"]["final"],
            })
    for k in parity:
        for p in parity[k]:
            p["absdiff"] = abs(p["mine"] - p["ref"])
    out["parity"] = {
        k: {
            "n_cells": len(v),
            "max_absdiff": max(p["absdiff"] for p in v),
            "detail": v,
        }
        for k, v in parity.items()
    }

    # ---- 预注册判定输入（全部数字已在上文落盘结构中）----
    layers = [(s, f) for s in SYMBOLS for f in (1, 10)]
    main_layers = [(MAIN, f) for f in (1, 10)]
    ext_layers = [(s, f) for s in SYMBOLS if s != MAIN for f in (1, 10)]

    def cell(s: str, f: int, arm: str) -> dict:
        return out["symbols"][s]["cells"][f"{arm}_fee{f}"]

    win = {f"{s}|{f}": cell(s, f, "hyb")["final"] > cell(s, f, "t3")["final"]
           for s, f in layers}
    cost = {f"{s}|{f}": (cell(s, f, "t3")["cagr"] - cell(s, f, "hyb")["cagr"]) * 100.0
            for s, f in layers}
    mdd_gain = {f"{s}|{f}": cell(s, f, "hyb")["mdd"] - cell(s, f, "t3")["mdd"]
                for s, f in layers}
    ratio = {f"{s}|{f}": cell(s, f, "hyb")["final"] / cell(s, f, "t3")["final"]
             for s, f in layers}
    calmar_hyb_gt_t3 = {f"{s}|{f}": cell(s, f, "hyb")["calmar"] > cell(s, f, "t3")["calmar"]
                        for s, f in layers}
    trade_cut = {
        f"{s}|{f}": 1.0 - cell(s, f, "hyb")["n_trades"] / max(1, cell(s, f, "bin0")["n_trades"])
        for s, f in layers
    }

    A1 = all(cost[f"{s}|{f}"] <= 1.5 for s, f in main_layers)
    A2a = (any(mdd_gain[f"{s}|{f}"] >= 0.02 for s, f in main_layers)
           and all(mdd_gain[f"{s}|{f}"] > -0.02 for s, f in main_layers))
    main_same_sign = {
        f"{s}|{f}": out["symbols"][s]["split_half"][f"fee{f}"]["diff_hyb_vs_t3"]["same_sign"]
        for s, f in main_layers
    }
    A2b_i = all(main_same_sign[f"{s}|{f}"] for s, f in main_layers)
    A2b_ii = any(trade_cut[f"{s}|{f}"] >= 0.20 for s, f in main_layers)
    A2b = A2b_i and A2b_ii
    A2 = A2a or A2b
    ext_win = sum(1 for s, f in ext_layers if win[f"{s}|{f}"])
    ext_ratio_floor = {}
    for s in SYMBOLS:
        if s == MAIN:
            continue
        rs = [ratio[f"{s}|{f}"] for f in (1, 10)]
        ext_ratio_floor[s] = min(rs)
    A3_no_crush = all(v >= 0.95 for v in ext_ratio_floor.values())
    A3 = ext_win >= 4 and A3_no_crush

    B1 = any(cost[f"{s}|{f}"] > 1.5 for s, f in main_layers)
    ext_loss_crush = sum(
        1 for s, f in ext_layers
        if (not win[f"{s}|{f}"]) and ratio[f"{s}|{f}"] < 0.95
    )
    B3 = (ext_win < 3) and (ext_loss_crush >= 2)

    if A1 and A2 and A3:
        verdict = "证据支持候选成立"
    elif B1 or B3:
        verdict = "证据不支持"
    else:
        verdict = "混合/中间态"

    out["verdict_inputs"] = {
        "win_hyb_gt_t3": win,
        "cost_pp": cost,
        "mdd_gain": mdd_gain,
        "final_ratio_hyb_over_t3": ratio,
        "calmar_hyb_gt_t3": calmar_hyb_gt_t3,
        "trade_cut_hyb_vs_bin0": trade_cut,
        "main_split_same_sign": main_same_sign,
        "A1": {"pass": A1, "main_costs_pp": {f"{s}|{f}": cost[f"{s}|{f}"] for s, f in main_layers}},
        "A2a": {"pass": A2a, "main_mdd_gains": {f"{s}|{f}": mdd_gain[f"{s}|{f}"] for s, f in main_layers}},
        "A2b": {"pass": A2b, "split_same_sign": main_same_sign,
                "main_trade_cuts": {f"{s}|{f}": trade_cut[f"{s}|{f}"] for s, f in main_layers}},
        "A2": {"pass": A2, "via": ("A2a" if A2a else "") + ("|A2b" if A2b else "")},
        "A3": {"pass": A3, "ext_win_of_6": ext_win,
               "ext_min_ratio_by_symbol": ext_ratio_floor,
               "ext_loss_crush_layers": ext_loss_crush},
        "B1": {"pass": B1},
        "B3": {"pass": B3, "ext_win_of_6": ext_win, "ext_loss_crush": ext_loss_crush},
    }
    out["verdict"] = verdict

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True, default=float)
    h = hashlib.sha256(payload.encode()).hexdigest()
    (RAW_DIR / "hysteresis_promotion_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float)
    )
    (RAW_DIR / "HASH.txt").write_text(h + "\n")

    # 判定最后打印（stdout 顺序即证据顺序）
    print("parity max absdiff vs AJ:", out["parity"]["vs_AJ"]["max_absdiff"],
          "| vs AP:", out["parity"]["vs_AP"]["max_absdiff"])
    print("main costs (pp):", {k: round(v, 3) for k, v in
                               out["verdict_inputs"]["A1"]["main_costs_pp"].items()})
    print("main mdd_gain:", {k: round(v, 4) for k, v in
                             out["verdict_inputs"]["A2a"]["main_mdd_gains"].items()})
    print("main split same_sign:", main_same_sign,
          "| main trade cuts:", {k: round(v, 3) for k, v in
                                 out["verdict_inputs"]["A2b"]["main_trade_cuts"].items()})
    print("ext win:", ext_win, "/6 | ext min ratio:", ext_ratio_floor)
    print("A1:", A1, "A2a:", A2a, "A2b:", A2b, "A3:", A3, "B1:", B1, "B3:", B3)
    print("VERDICT:", verdict)
    print("HASH:", h)


if __name__ == "__main__":
    main()
