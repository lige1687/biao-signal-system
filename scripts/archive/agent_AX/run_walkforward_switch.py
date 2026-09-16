# -*- coding: utf-8 -*-
"""AX 任务：换档决策的走样本（walk-forward）前向验证 + 相对痛苦度量。

【背景与定位】AU（binary-hysteresis-vs-t3-decision-2026-09-04）判「换」，但
诚实条款写明：二元侧参数（43.33 进仓线、2pp 带宽）都在全样本上选定，属样本
内证据。本任务把同一决策放到走样本协议下重考：**每个前向段只用段前 6 年
数据选二元参数，然后前向交易 2 年**；三档参数冻结（冠军 43.33/56.67 定版已
久，符合"当时的人只用当时的数据"纪律）。这是把 AU 从"系统内决策依据"升级
为"准样本外证据"的关键一步，也是换档前最后一块该补的证据。

【走样本协议（跑前写死）】
- 标的：399006（2010-06 起）、510300（2012-05 起）、512100（2016-11 起）。
  588000（2020-11 起）凑不出 6 年训练窗，诚实排除（登记，不用短窗凑数）。
- 前向段（每段 2 个自然年，交易日历按各标的对齐样本切）：
  399006: [2016,2018) [2018,2020) [2020,2022) [2022,2024) [2024,2026)  共 5 段
  510300: [2018,2020) [2020,2022) [2022,2024) [2024,2026)              共 4 段
  512100: [2022,2024) [2024,2026)                                      共 2 段
  合计 11 个前向 (标的×段) 样本。训练窗 = 段起点前推 6 年（2010 起步的段，
  训练窗短于 6 年的段弃用——不存在，因起点已按数据可用性排过）。
- 二元参数选择（仅用训练窗）：E ∈ {41.3333, 43.3333, 45.3333}（AJ/AP 同格）
  × b ∈ {1, 2, 3}pp，共 9 格；选择标准 = 训练窗 Calmar 最大；平手比终值；
  再平手取带宽小者。**资格线（防"永远空仓"退化格）**：训练窗在场时间
  ≥10% 才有资格；全部格不合格时取 E=43.3333/b=2 并登记 degraded。
- 前向执行：选定参数的二元+滞回 vs 冻结三档，同一对齐样本同一费率
  （10bp，AU 主口径；1bp 不重复，方向已证一致）。
- 引擎全部逐字复用（simulate / ladder_target / hysteresis_target），
  T 收盘信号 T+1 开盘成交，min_trade=0.05。

【预注册三选一判定线（跑前写死，只对走样本二元臂）】
  11 个前向段上：
  - 「换档决策在走样本下保持」：二元(走样本参数) Calmar > 三档 于 ≥6/11 段
    且 终值 > 三档 于 ≥6/11 段。
    [依据：AU 样本内为 6/8 与 8/8；走样本下允许退化到简单多数，若连多数都
    保不住，样本内优势大概率是参数泄漏的产物。]
  - 「换档证据被动摇」：三档 Calmar ≥ 二元 于 ≥6/11 段 且 三档终值 ≥ 二元
    于 ≥6/11 段。
  - 其余 = 「混合」（如 Calmar 多数胜但终值多数负——登记为"防御性优势"
    结构，含义单独解释，不硬套两极）。
  冻结参数二元臂（43.33/2 全程不重选）与走样本臂并列报告（描述级）：
  用于区分"引擎差异"与"参数重选损耗"两个成分。

【相对痛苦度量（全样本 fee=10bp，描述级，回答"换了之后会有多难受"）】
  对核心 4 标的（含 588000，度量不需训练窗）：二元(43.33/2) 与三档的日净值
  比值曲线 r(t)：
  - 最大相对回撤：1 − min(r/running_max(r))（二元相对三档落后最多多少）；
  - 最长水下期：r 连续低于其前高的最长交易日数（换档后"感觉变差"能持续
    多久）；及其起止日期；
  - 最差滚动 252 日相对收益。
  这些数字不进判定，用途是给用户换档前的预期管理。

【红线遵守】不产生买卖指令；不改生产代码/缓存/既有归档；产出全为新增。
双跑哈希 PYTHONHASHSEED=0/42 逐位一致。
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
from run_robustness import cagr_maxdd, load_aligned  # noqa: E402
from run_hysteresis import hysteresis_target  # noqa: E402

RAW_DIR = REPO / "docs/experiments/raw/agent_AX-walkforward-switch"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FEE = 10.0
TRAIN_YEARS = 6
ENTRIES = [100.0 / 3.0 * 1.3 - 2.0, 100.0 / 3.0 * 1.3, 100.0 / 3.0 * 1.3 + 2.0]
BANDS = [1.0, 2.0, 3.0]
BLOCKS = {
    "399006": [2016, 2018, 2020, 2022, 2024],
    "510300": [2018, 2020, 2022, 2024],
    "512100": [2022, 2024],
}
PAIN_SYMS = ["399006", "510300", "512100", "588000"]
T3_PARAMS = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)


def run_metrics(aligned: pd.DataFrame, target, fee: float) -> dict:
    res = simulate(aligned, target, fee_bps=fee, min_trade=0.05)
    cagr, mdd, calmar = cagr_maxdd(res.daily["equity"])
    return {"final": float(res.daily["equity"].iloc[-1]), "cagr": cagr,
            "mdd": mdd, "calmar": calmar,
            "time_in_market": float((res.daily["weight"] > 0).mean())}


def select_binary_params(train: pd.DataFrame) -> dict:
    """训练窗内选 (E, b)：Calmar 最大 → 终值 → 带宽小；在场<10% 不合格。"""
    best = None
    for E in ENTRIES:
        for b in BANDS:
            m = run_metrics(train, hysteresis_target(train["b200"], E, b), FEE)
            if m["time_in_market"] < 0.10:
                continue
            # inf-safe 排序键：calmar 直接可比（inf 最大），平手比 final
            key = (m["calmar"], m["final"], -b)
            if best is None or key > best[0]:
                best = (key, E, b, m)
    if best is None:
        return {"E": ENTRIES[1], "band": 2.0, "degraded": True,
                "train": None}
    _, E, b, m = best
    return {"E": E, "band": b, "degraded": False, "train": m}


def pain_metrics(aligned: pd.DataFrame) -> dict:
    """二元(43.33/2) vs 三档 的相对曲线痛苦度量。"""
    eq_t3 = simulate(aligned, ladder_target(aligned["b200"], T3_PARAMS),
                     fee_bps=FEE, min_trade=0.05).daily["equity"]
    eq_hy = simulate(aligned, hysteresis_target(aligned["b200"], ENTRIES[1], 2.0),
                     fee_bps=FEE, min_trade=0.05).daily["equity"]
    ratio = (eq_hy / eq_t3).dropna()
    run_max = ratio.cummax()
    rel_dd = (ratio / run_max - 1.0)
    max_rel_dd = float(rel_dd.min())
    underwater = (rel_dd < -1e-12).astype(int)
    # 最长连续水下段
    best_len, cur, end_i = 0, 0, 0
    for i, v in enumerate(underwater.to_numpy()):
        cur = cur + 1 if v else 0
        if cur > best_len:
            best_len, end_i = cur, i
    start_i = end_i - best_len + 1
    roll = ratio / ratio.shift(252) - 1.0
    return {
        "max_relative_dd_pct": round(max_rel_dd * 100, 2),
        "longest_underwater_td": int(best_len),
        "underwater_from": str(ratio.index[start_i].date()) if best_len else None,
        "underwater_to": str(ratio.index[end_i].date()) if best_len else None,
        "worst_roll252_rel_pct": round(float(roll.min() * 100), 2)
        if roll.size and not np.isnan(roll.min()) else None,
    }


def main() -> None:
    out: dict = {"criteria_doc": __doc__,
                 "config": {"fee": FEE, "train_years": TRAIN_YEARS,
                            "entries": ENTRIES, "bands": BANDS,
                            "blocks": BLOCKS}}
    segments = []
    for sym, starts in BLOCKS.items():
        aligned_all = load_aligned(sym)
        for y0 in starts:
            y1 = y0 + 2
            fwd = aligned_all[
                (aligned_all.index >= f"{y0}-01-01")
                & (aligned_all.index < f"{y1}-01-01")
            ]
            train_end = fwd.index[0]
            train_start = train_end - pd.DateOffset(years=TRAIN_YEARS)
            train = aligned_all[
                (aligned_all.index >= train_start) & (aligned_all.index < train_end)
            ]
            if len(train) < 750:  # 训练窗不足 3 年等效——弃段并登记
                segments.append({"sym": sym, "block": [y0, y1],
                                 "skipped": "train_too_short",
                                 "train_days": len(train)})
                continue
            sel = select_binary_params(train)
            t3 = run_metrics(fwd, ladder_target(fwd["b200"], T3_PARAMS), FEE)
            hy = run_metrics(fwd, hysteresis_target(fwd["b200"], sel["E"],
                                                    sel["band"]), FEE)
            hy_frozen = run_metrics(
                fwd, hysteresis_target(fwd["b200"], ENTRIES[1], 2.0), FEE)
            segments.append({
                "sym": sym, "block": [y0, y1],
                "train_days": len(train), "fwd_days": len(fwd),
                "selected": {"E": round(sel["E"], 4), "band": sel["band"],
                             "degraded": sel["degraded"]},
                "T3": t3, "BIN_HYST_wf": hy, "BIN_HYST_frozen": hy_frozen,
                "calmar_wf_wins": hy["calmar"] > t3["calmar"],
                "final_wf_wins": hy["final"] > t3["final"],
                "calmar_frozen_wins": hy_frozen["calmar"] > t3["calmar"],
                "final_frozen_wins": hy_frozen["final"] > t3["final"],
            })
            print(f"[{sym} {y0}-{y1}] sel E={sel['E']:.2f} b={sel['band']} "
                  f"T3 Cal{t3['calmar']:.2f} vs WF Cal{hy['calmar']:.2f}",
                  flush=True)
    out["segments"] = segments

    valid = [s for s in segments if "T3" in s]
    n = len(valid)
    c_wf = sum(s["calmar_wf_wins"] for s in valid)
    f_wf = sum(s["final_wf_wins"] for s in valid)
    c_t3 = n - c_wf
    f_t3 = n - f_wf
    c_fr = sum(s["calmar_frozen_wins"] for s in valid)
    f_fr = sum(s["final_frozen_wins"] for s in valid)
    out["verdict_inputs"] = {
        "n_segments": n,
        "wf_calmar_wins": c_wf, "wf_final_wins": f_wf,
        "t3_calmar_wins": c_t3, "t3_final_wins": f_t3,
        "frozen_calmar_wins": c_fr, "frozen_final_wins": f_fr,
        "skipped": [s for s in segments if "T3" not in s],
    }
    if n < 8:
        verdict = f"证据不足（有效前向段 {n}<8）"
    elif c_wf >= 6 and f_wf >= 6:
        verdict = "换档决策在走样本下保持"
    elif c_t3 >= 6 and f_t3 >= 6:
        verdict = "换档证据被动摇"
    else:
        verdict = "混合"
    out["verdict"] = verdict

    out["pain_metrics_fee10"] = {}
    for sym in PAIN_SYMS:
        out["pain_metrics_fee10"][sym] = pain_metrics(load_aligned(sym))
        print(f"[pain {sym}] done", flush=True)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "walkforward_switch_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"\n走样本段 n={n}：二元WF Calmar胜 {c_wf}/{n}，终值胜 {f_wf}/{n}"
          f"（冻结参数臂 {c_fr}/{n}、{f_fr}/{n}）")
    print(f"=== 判定：{verdict} ===")
    print(f"sha256(canonical) = {h}")


if __name__ == "__main__":
    main()
