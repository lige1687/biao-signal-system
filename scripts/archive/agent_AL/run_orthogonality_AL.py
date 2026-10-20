"""10Y 创 5 年新高候选信号 × 现有两腿（B9 宽度腿 / LEI 执行腿）正交性检查
（2026-09-03，任务 AL，转正路径第一道门）。

上游（冻结，不得改动）：
- 候选事件 = us-treasury-r2 事后诊断"10Y 滚动 5 年（1260 交易日）分位 ≥85
  段首事件"，滞回 80×60 日，前瞻 12 个月（252 交易日）。事件清单直接引用
  raw/us-treasury-signal-r2/posthoc_rolling_level.json 的 hi_events（11 枚，
  与归档一致），本脚本**不重新定义事件**，只做核对（枚数、日期逐一比对）。
- 两腿 = docs/experiments/raw/combined_cert/combined_curves.csv 的 b9/lei
  净值列（heiti 合体认证归档原腿，2017-03-24 起）——LEI 用真腿，不用代理。
- 标的 = raw/us-treasury-signal-r2/gspc_ohlc_1962.parquet（^GSPC，r2 归档
  已缓存，离线）。

候选信号腿日收益构造（事前写死，与 2026-09-01 Prompt D 正交性检查同构）：
- 信号日收盘确认 → 次一交易日起持有标普共 252 交易日（= 冻结规格的前瞻
  12 个月；收盘对收盘，无前视），权重 = 活跃事件数 / 窗口内总事件数，
  无费用（相关性对费用不敏感，声明）。
- 方向说明：候选的信息方向是"事件后 12 个月偏弱"，实操形态应是防御性
  （降敞口）。防御形态的日收益 = −(上述多头腿收益)，Pearson 只翻符号、
  |r| 不变；本报告主表报多头构造的 r，并注明翻向不影响 |r| 判定。

判定标准（预注册，跑前写死，跑完不得改）：
- AL0（口径校验硬闸）：复算 b9×lei 日收益 Pearson 须落在 heiti 报告值
  −0.003 ± 0.01 内，否则中止全表。
- AL1（正交性通过线）：候选腿与 b9、与 lei 的 |Pearson| 均 < 0.10
  （任务书建议线；论证：两腿互相关仅 −0.003，候选若与两腿同带量级即
  "独立信息资格"的第一必要条件成立。0.10 明显低于同族信号互相关 0.83
  与 E1 边缘案例 0.21 的水平）。
- AL2（高相关否决线）：任一腿 |Pearson| > 0.30 → 判"与现有腿功能同源，
  无分散价值先验"，不通过。
- AL3（边缘带）：最大 |Pearson| ∈ [0.10, 0.30] → 边缘，机制解释义务，
  不判通过也不否决。
- AL4（样本量）：相关窗口内事件数 <3 → 只报告不判定。冻结事件清单
  2017 年后仅 3 枚（2018-01/2022-04/2026-03），恰在下限，如实标注。
- AL5（激活期重叠度，单列必报）：候选持仓日中，b9（或 lei）同日持仓的
  比例（两腿"非零收益日"≈持仓日近似，口径与 2026-09-01 检查一致，声明）。
  预注册线：重叠率 ≤ 该腿全窗口自身持仓占比 + 10 个百分点 → "候选激活期
  不偏好落在该腿持仓期"（即非功能性重叠）；> 该线 → 标注功能重叠嫌疑，
  即使 |r| 低也是假独立，判不通过。
- 双跑：PYTHONHASHSEED=0 / =42 输出 JSON sha256 一致方可引用。

明确不做（红线）：不回测任何组合、不设计权重、不重定义事件、不动冻结
参数；候选仍是观察级，本检查是转正路径第一道门，通过≠转正。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
R2 = REPO / "docs/experiments/raw/us-treasury-signal-r2"
CURVES = REPO / "docs/experiments/raw/combined_cert/combined_curves.csv"
OUT = REPO / "docs/experiments/raw/tsy10y-high-orthogonality"

HOLD_TD = 252              # 冻结：前瞻 12 个月
HEITI_LEG_CORR = -0.003    # AL0 锚
TOL_AL0 = 0.01
PASS_CUT = 0.10            # AL1
HIGH_CUT = 0.30            # AL2
MIN_EVENTS = 3             # AL4
OVERLAP_TOL = 0.10         # AL5：重叠率容差（百分点）

# 归档写死的事件清单（signal 日，核对用）
ARCHIVE_EVENTS = [
    "1967-04-28", "1973-07-27", "1974-03-22", "1978-01-09", "1984-05-30",
    "2000-01-18", "2006-04-13", "2007-01-29", "2018-01-19", "2022-04-18",
    "2026-03-20",
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # -- 事件核对（不重建，只比对） --------------------------------------
    posthoc = json.loads((R2 / "posthoc_rolling_level.json").read_text())
    events = list(posthoc["dgs10"]["hi_events"])
    assert events == ARCHIVE_EVENTS, f"事件清单与归档不一致: {events}"
    sig_days = [pd.Timestamp(d) for d in events]

    # -- 数据加载 ---------------------------------------------------------
    px = pd.read_parquet(R2 / "gspc_ohlc_1962.parquet")
    px.index = pd.to_datetime(px.index)
    curves = pd.read_csv(CURVES, parse_dates=["date"]).set_index("date")
    legs = curves[["b9", "lei"]].dropna()
    leg_ret = legs.pct_change().dropna()

    # AL0 硬闸
    r_b9lei = float(np.corrcoef(leg_ret["b9"], leg_ret["lei"])[0, 1])
    al0_ok = abs(r_b9lei - HEITI_LEG_CORR) <= TOL_AL0
    results = {"AL0": {"b9_x_lei_pearson": round(r_b9lei, 6),
                       "anchor": HEITI_LEG_CORR, "tol": TOL_AL0,
                       "pass": al0_ok}}
    if not al0_ok:
        results["ABORT"] = "AL0 未过，全表中止"
        (OUT / "al_results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2))
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(1)

    window = leg_ret.index  # 相关窗口 = 两腿曲线窗口（2017-03-24 起）

    # -- 候选腿（多头构造；防御形态 = 取负，|r| 不变） ----------------------
    pos = {d: i for i, d in enumerate(px.index)}
    active = np.zeros(len(px.index))
    n_in_window = 0
    for sd in sig_days:
        if sd not in pos:
            continue
        i = pos[sd]
        active[i + 1:min(i + 1 + HOLD_TD, len(active))] += 1.0
        if window[0] <= sd <= window[-1]:
            n_in_window += 1
    active_s = pd.Series(active, index=px.index)
    total_in_window = float(active_s.reindex(window).sum())
    weight = active_s / total_in_window if total_in_window else active_s
    spx_ret = px["close"].pct_change().fillna(0.0)
    cand = (weight * spx_ret).reindex(window).fillna(0.0)

    pearson = {leg: float(np.corrcoef(cand, leg_ret[leg])[0, 1])
               for leg in ("b9", "lei")}
    # 事件后 12 个月窗口内的相关性（任务书要求单列；窗口=候选持仓日 ∩ 腿窗口）
    ev_mask = (weight.reindex(window) > 0).values
    pearson_evwin = {}
    for leg in ("b9", "lei"):
        x, y = cand.values[ev_mask], leg_ret[leg].reindex(window).values[ev_mask]
        pearson_evwin[leg] = (float(np.corrcoef(x, y)[0, 1])
                              if np.std(x) > 0 and np.std(y) > 0 else None)

    # -- AL5 激活期重叠度 --------------------------------------------------
    cand_hold = pd.Series(ev_mask, index=window)
    overlap = {}
    for leg in ("b9", "lei"):
        leg_hold = leg_ret[leg] != 0.0   # 非零收益日 ≈ 持仓日（口径声明）
        base_pct = float(leg_hold.mean())
        ov_pct = float(leg_hold[cand_hold].mean()) if cand_hold.any() else None
        # 事件日（11 枚中落在窗口内的）当日两腿持仓状态逐日表
        overlap[leg] = {
            "leg_holding_pct_full_window": round(base_pct, 4),
            "overlap_pct_on_candidate_days": (round(ov_pct, 4)
                                              if ov_pct is not None else None),
            "overlap_ok": (ov_pct is not None
                           and ov_pct <= base_pct + OVERLAP_TOL),
        }
    event_day_state = []
    for sd in sig_days:
        row = {"signal_date": str(sd.date())}
        for k in range(1, 5):  # 事件后第 1-4 个交易日
            j = pos[sd] + k
            if j >= len(px.index):
                break
            d = px.index[j]
            row[f"exec+{k}"] = str(d.date())
            for leg in ("b9", "lei"):
                v = leg_ret[leg].reindex([d]).iloc[0] if d in leg_ret.index else np.nan
                row[f"{leg}_ret_+{k}"] = (None if pd.isna(v) else
                                          ("holding(nonzero)" if v != 0
                                           else "flat(zero)"))
        event_day_state.append(row)

    # -- 判定 ---------------------------------------------------------------
    m = max(abs(v) for v in pearson.values())
    if n_in_window < MIN_EVENTS:
        verdict = f"report_only(n_events={n_in_window}<{MIN_EVENTS})"
    elif m > HIGH_CUT:
        verdict = "FAIL_high_correlation"
    elif m >= PASS_CUT:
        verdict = "BORDERLINE_mechanism_note_required"
    else:
        verdict = "PASS_orthogonality_gate1"
    overlap_all_ok = all(v["overlap_ok"] for v in overlap.values())
    if verdict == "PASS_orthogonality_gate1" and not overlap_all_ok:
        verdict = "FAIL_functional_overlap_despite_low_corr"

    results.update({
        "events_all": events,
        "events_in_window": n_in_window,
        "window": [str(window[0].date()), str(window[-1].date())],
        "hold_td": HOLD_TD,
        "candidate_leg": {
            "construction": "long SPX 252td from next day after signal; "
                            "weight=active/total_in_window; no costs",
            "holding_days_pct": round(float(cand_hold.mean()), 4),
            "truncated_2026_event": True,  # 2026-03 事件持仓被窗口末端截断
        },
        "pearson_full_window": {k: round(v, 6) for k, v in pearson.items()},
        "pearson_event_windows_only": (
            {k: (round(v, 6) if v is not None else None)
             for k, v in pearson_evwin.items()}),
        "AL5_overlap": overlap,
        "event_day_leg_state": event_day_state,
        "verdict": verdict,
        "note_defensive_flip": "防御形态 r 翻符号，|r| 不变，判定不受影响",
    })
    out_json = OUT / "al_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps({k: results[k] for k in
                      ("AL0", "pearson_full_window",
                       "pearson_event_windows_only", "AL5_overlap",
                       "verdict", "events_in_window", "candidate_leg")},
                     ensure_ascii=False, indent=2))
    print("sha256(al_results.json) =", sha256(out_json))


if __name__ == "__main__":
    main()
