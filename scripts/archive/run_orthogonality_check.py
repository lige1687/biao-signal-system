"""新信号与现有两腿（B9/LEI）正交性检查（2026-09-01，任务书 Prompt D）。

背景：合体组核心方法论是「两条互不相关的腿正交叠加」——B9 宽度腿与 LEI
执行腿日收益相关 −0.003（heiti-ARCHIVE 2026-08-31）。任何新触发信号要有
真正增量，前提是与现有两腿低相关，否则是「卫星腿 RR 门槛」证伪案例的重演。

本轮输入（2026-09-01 状态）：
1. Prompt A（美债）——正版判定 JA1 倒挂解除 report_only_n<5（负向）、JB1
   利率冲击波动预警 falsified（安慰剂 58 分位）、JC1 n=1，**无通过级候选**。
   本脚本纳入的 A2 双臂取自 agent D 的交叉验证实现
   （us-treasury-CROSSCHECK-2026-09-01.md），仅作「低相关 ≠ 信号有效」的
   对照案例行——其 T2「通过」已被正版 JB1 更严标准推翻，不构成候选。
2. Prompt C（A 股宏观，ashare-macro-ARCHIVE-2026-09-01.md）——零通过，但
   其「下一步第 1 条」明确点名本任务：对 E1 去杠杆急坠**反向现象**（预注册
   方向写反未翻案，观察级）做正交性检验，预期若与宽度警报同源则判高相关、
   降级为「警报确认辅助」。E1 口径：12 事件（ashare_macro_results.json
   events.E1_deleveraging），标的创业板指 399006（raw/siphon_detector/
   cyb_399006_close.parquet，只读），持有 60 交易日（与其 fwd60 一致）。
3. Prompt B（VIX/期权情绪）当日无产出；归档后本脚本可增量复跑。

新信号合成腿口径（事前写死）：
- 信号日次一交易日起持有标的共 HOLD_TD 交易日（A2=63 与 T2 波动口径一致；
  E1=60 与 C 组 fwd60 一致；收盘对收盘，信号收盘确认次日建仓，无前视），
  权重 = 活跃事件数 / 窗口内总事件数（事前归一；无活跃事件日权重 0）。
  腿日收益 = 权重 × 标的日收益。无费用（相关性对费用不敏感，声明）。
- 相关窗口 = 两腿曲线窗口 ∩ 新信号腿窗口（两腿曲线 2017-03-24→2026-07-17），
  逐日内积对齐（inner join），Pearson + Spearman 双报。

判定标准（事前写死，跑完不许改；不因 E1 的「预期高相关」而调整任何线）：
- OD0（口径校验，硬闸）：复算 b9×lei 两腿日收益 Pearson 必须落在 heiti
  报告值 −0.003±0.01 内，否则中止并排查口径（防止对齐/复权错位导致
  全表作废）。
- OD1（低相关候选）：新信号腿与 b9、与 lei 的 |Pearson| **均 ≤0.15**
  → 列入「值得设计第三腿正交叠加实验」候选名单。**仅此而已：低相关是
  必要条件非充分条件，不等于叠加后收益/回撤会改善**（叠加有效需后续
  独立实验，本任务不做）。
- OD2（高相关）：任一腿 |Pearson| >0.30 → 高相关如实报告，判「无增量
  先验，不建议进入叠加实验」。E1 若落此档，与 C 组预判一致：降级宽度
  警报「确认辅助」，不得按新腿对待。
- OD3（边缘带）：最大 |Pearson| ∈(0.15, 0.30] → 「边缘」，报告机制解释
  义务（为何可能与该腿共享信息），不下通过/否决结论。
- OD4（样本量下限）：新信号腿在相关窗口内事件数 <3 → 只报告不判定。
- 辅助（不进判定）：持仓日重叠率——新信号腿权重>0 的日子占比，及其与
  b9/lei「非零收益日」（≈持仓日，两腿空仓日收益恒 0 的近似，声明口径）
  的条件重叠率；heiti 两腿相关参照值同表复算列出。

明确不做（任务书原文）：不设计/不跑三腿组合回测本身；不下结论「某信号
肯定该加入系统」。

数据：
- 两腿：docs/experiments/raw/combined_cert/combined_curves.csv（b9/lei 列，
  heiti 合体认证归档，sha256 见其 MANIFEST）。
- A2 双臂：docs/experiments/raw/us-treasury-signal-crosscheck/（CROSSCHECK
  归档，双跑哈希 a8ea1003…）。
- E1 事件：docs/experiments/raw/ashare-macro/ashare_macro_results.json
  （C 组归档，双跑哈希 6e27f802…）；创业板价格 raw/siphon_detector/
  cyb_399006_close.parquet（只读）。

输出：docs/experiments/raw/orthogonality-check/（JSON + 矩阵 CSV）。
双跑：PYTHONHASHSEED=0 / =42 输出 JSON sha256 一致方可引用。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw/us-treasury-signal-crosscheck"
ASHARE = REPO / "docs/experiments/raw/ashare-macro"
SRC_A_MAIN = REPO / "docs/experiments/raw/us-treasury-signal/us_treasury_results.json"
MODULE_E = REPO / "docs/experiments/raw/module_e/module_e_results.json"
CYB = REPO / "docs/experiments/raw/siphon_detector/cyb_399006_close.parquet"
CURVES = REPO / "docs/experiments/raw/combined_cert/combined_curves.csv"
RAW = REPO / "docs/experiments/raw/orthogonality-check"

HOLD_TD_A2 = 63       # A2 腿持有期（与 T2 波动口径一致）
HOLD_TD_E1 = 60       # E1 腿持有期（与 C 组 fwd60 一致）
HEITI_LEG_CORR = -0.003   # heiti 报告的两腿日收益相关（口径校验锚）
TOL_OD0 = 0.01        # OD0 校验容差
LOW_CUT = 0.15        # OD1 低相关线
HIGH_CUT = 0.30       # OD2 高相关线
MIN_EVENTS = 3        # OD4 样本量下限


def judge(corr_b9: float, corr_lei: float, n_events: int) -> str:
    if n_events < MIN_EVENTS:
        return f"report_only(n_events={n_events}<{MIN_EVENTS})"
    m = max(abs(corr_b9), abs(corr_lei))
    if m <= LOW_CUT:
        return "low_correlation_candidate"
    if m > HIGH_CUT:
        return "high_correlation_no_increment_prior"
    return "borderline_needs_mechanism_note"


def synth_leg(price: pd.DataFrame, signal_days: list[pd.Timestamp],
              window: pd.DatetimeIndex,
              hold_td: int) -> tuple[pd.Series, dict]:
    """等权合成信号腿：信号日次一交易日起持有 hold_td 交易日（收盘对收盘，
    信号收盘确认次日建仓，无前视；与两腿净值日收益同构），权重 =
    活跃事件数/窗口内总事件数。"""
    price = price.reindex(window.union(price.index)).ffill().reindex(window)
    ret = price["close"].pct_change().fillna(0.0)
    pos = {d: i for i, d in enumerate(price.index)}
    total = 0
    active = np.zeros(len(price.index))
    for sd in signal_days:
        if sd in pos:
            i = pos[sd]
            active[i + 1:min(i + 1 + hold_td, len(active))] += 1.0
            total += 1
    weight = pd.Series(active / total if total else active, index=price.index)
    meta = {"n_events_in_window": total,
            "holding_days_pct": round(float((weight > 0).mean()), 4),
            "max_weight": round(float(weight.max()), 4)}
    return (weight * ret), meta


def overlap_stats(w: pd.Series, leg_ret: pd.Series) -> dict:
    both = pd.DataFrame({"w": w, "leg": leg_ret}).dropna()
    sig_on = both["w"] > 0
    leg_on = both["leg"].abs() > 1e-12  # 空仓日收益恒 0 的近似
    return {
        "signal_days_pct": round(float(sig_on.mean()), 4),
        "leg_active_days_pct": round(float(leg_on.mean()), 4),
        "overlap_pct_of_signal_days": round(
            float((sig_on & leg_on).sum() / sig_on.sum()), 4) if sig_on.any() else None,
    }


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    curves = pd.read_csv(CURVES, parse_dates=["date"]).set_index("date")
    leg_b9 = curves["b9"].pct_change()
    leg_lei = curves["lei"].pct_change()
    legs = pd.DataFrame({"b9": leg_b9, "lei": leg_lei}).dropna()

    # ---- OD0 口径校验（硬闸）----
    od0 = float(legs["b9"].corr(legs["lei"]))
    od0_pass = abs(od0 - HEITI_LEG_CORR) <= TOL_OD0
    res: dict = {
        "experiment": "orthogonality_check_new_signals_vs_b9_lei",
        "config": {"HOLD_TD_A2": HOLD_TD_A2, "HOLD_TD_E1": HOLD_TD_E1,
                   "HEITI_LEG_CORR": HEITI_LEG_CORR,
                   "TOL_OD0": TOL_OD0, "LOW_CUT": LOW_CUT,
                   "HIGH_CUT": HIGH_CUT, "MIN_EVENTS": MIN_EVENTS},
        "OD0_calibration": {
            "b9_x_lei_pearson_recomputed": round(od0, 4),
            "heiti_reported": HEITI_LEG_CORR,
            "pass": od0_pass,
        },
        "legs_window": [str(legs.index[0].date()), str(legs.index[-1].date())],
        "legs_days": len(legs),
    }
    if not od0_pass:
        res["ABORTED"] = "OD0 口径校验未过，全表作废，需排查对齐/复权后重跑"
        (RAW / "orthogonality_results.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False))
        print(json.dumps(res["OD0_calibration"], indent=2))
        return 1

    # ---- 新信号腿（Prompt A 产出）----
    ut = json.load(open(SRC / "us_treasury_results.json"))
    spx = pd.read_parquet(SRC / "../module_e/us_gspc_ohlc.parquet")
    spx.index = pd.to_datetime(spx.index)

    win = legs.index
    arms: dict[str, dict] = {}
    leg_series: dict[str, pd.Series] = {}
    for side in ("up", "down"):
        days = [pd.Timestamp(d) for d in ut["A2_fast_move"][side]["signal_days"]]
        leg, meta = synth_leg(spx, days, win, HOLD_TD_A2)
        leg_series[f"A2_{side}"] = leg
        corr_b9 = float(leg.corr(legs["b9"]))
        corr_lei = float(leg.corr(legs["lei"]))
        sp_b9 = float(leg.corr(legs["b9"], method="spearman"))
        sp_lei = float(leg.corr(legs["lei"], method="spearman"))
        arms[f"A2_{side}"] = {
            **meta,
            "pearson_vs_b9": round(corr_b9, 4),
            "pearson_vs_lei": round(corr_lei, 4),
            "spearman_vs_b9": round(sp_b9, 4),
            "spearman_vs_lei": round(sp_lei, 4),
            "verdict": judge(corr_b9, corr_lei, meta["n_events_in_window"]),
            "overlap_b9": overlap_stats(leg, legs["b9"]),
            "overlap_lei": overlap_stats(leg, legs["lei"]),
            "signal_days_in_window": [str(d.date()) for d in days
                                      if win[0] <= d <= win[-1]],
        }
    # A1（判负信号，仅参考行；预期重叠窗内 n=1 → OD4 只报告）
    a1_days = [pd.Timestamp(e["un_inversion"]) for e in ut["A1_un_inversion"]["events"]]
    leg_a1, meta_a1 = synth_leg(spx, a1_days, win, HOLD_TD_A2)
    leg_series["A1_ref_only"] = leg_a1
    corr_b9a = float(leg_a1.corr(legs["b9"]))
    corr_leia = float(leg_a1.corr(legs["lei"]))
    arms["A1_un_inversion_falsified_ref_only"] = {
        **meta_a1,
        "pearson_vs_b9": round(corr_b9a, 4),
        "pearson_vs_lei": round(corr_leia, 4),
        "verdict": judge(corr_b9a, corr_leia, meta_a1["n_events_in_window"]),
        "note": "T1 已判负（us-treasury-CROSSCHECK 第二节），此行仅完整性参考",
    }
    # ---- E1 去杠杆急坠反向现象（Prompt C 点名检验；观察级非候选）----
    am = json.load(open(ASHARE / "ashare_macro_results.json"))
    e1_days = [pd.Timestamp(e["date"])
               for e in am["events"]["E1_deleveraging"]["list"]]
    cyb = pd.read_parquet(CYB)
    cyb.index = pd.to_datetime(cyb.index)
    leg_e1, meta_e1 = synth_leg(cyb, e1_days, win, HOLD_TD_E1)
    leg_series["E1_deleverage_reversal"] = leg_e1
    corr_b9e = float(leg_e1.corr(legs["b9"]))
    corr_leie = float(leg_e1.corr(legs["lei"]))
    arms["E1_deleverage_reversal_watch_only"] = {
        **meta_e1,
        "pearson_vs_b9": round(corr_b9e, 4),
        "pearson_vs_lei": round(corr_leie, 4),
        "spearman_vs_b9": round(float(leg_e1.corr(legs["b9"], method="spearman")), 4),
        "spearman_vs_lei": round(float(leg_e1.corr(legs["lei"], method="spearman")), 4),
        "verdict": judge(corr_b9e, corr_leie, meta_e1["n_events_in_window"]),
        "overlap_b9": overlap_stats(leg_e1, legs["b9"]),
        "overlap_lei": overlap_stats(leg_e1, legs["lei"]),
        "signal_days_in_window": [str(d.date()) for d in e1_days
                                  if win[0] <= d <= win[-1]],
        "note": ("C 组 E1 反向现象（ashare-macro-ARCHIVE 三）：预注册方向写反未"
                 "翻案，观察级；C 组预期与宽度警报同源→若判高相关即降级"
                 "「确认辅助」；11/12 事件与双≤20 警报 ±10td 伴生（C 组事后"
                 "辅助分析）"),
    }
    # ---- 正版 A C2 下行臂（A 组点名送测的唯一候选；观察级）----
    ut_main = json.load(open(SRC_A_MAIN))
    c2d_days = [pd.Timestamp(d) for d in
                ut_main["c2_rate_shock"]["line95_down"]["events"]]
    leg_c2d, meta_c2d = synth_leg(spx, c2d_days, win, HOLD_TD_A2)
    leg_series["C2_down_main_impl"] = leg_c2d
    corr_b9c = float(leg_c2d.corr(legs["b9"]))
    corr_leic = float(leg_c2d.corr(legs["lei"]))
    arms["C2_down_main_impl_watch_only"] = {
        **meta_c2d,
        "pearson_vs_b9": round(corr_b9c, 4),
        "pearson_vs_lei": round(corr_leic, 4),
        "spearman_vs_b9": round(float(leg_c2d.corr(legs["b9"], method="spearman")), 4),
        "spearman_vs_lei": round(float(leg_c2d.corr(legs["lei"], method="spearman")), 4),
        "verdict": judge(corr_b9c, corr_leic, meta_c2d["n_events_in_window"]),
        "overlap_b9": overlap_stats(leg_c2d, legs["b9"]),
        "overlap_lei": overlap_stats(leg_c2d, legs["lei"]),
        "signal_days_in_window": [str(d.date()) for d in c2d_days
                                  if win[0] <= d <= win[-1]],
        "note": ("正版 A 观察（其 ARCHIVE 三）：下行臂 n=23 过 ×1.15 波动线且"
                 "12m +13.1% vs +9.7%，但其事件与模块 E 宽度极值高度同期、"
                 "疑为底部利率镜像——A 组下一步 1 点名本任务送测（先验高相关"
                 "预期不增量）；事件集为其 line95_down（持有 63td 与 A2_down"
                 "同构保持可比）"),
    }
    # ---- 辅助（不进 OD 判定）：C2 下行臂 × 模块 E v1 信号日 ±10td 伴生 ----
    me = json.load(open(MODULE_E))
    me_days = [pd.Timestamp(s) for s in me["us"]["arms"]["v1_hedge50"]["signals"]]
    c2d_all = list(c2d_days)  # 全史口径：A 组下一步1要求的是日期级全史核验
    # ±10 交易日 = SPX 交易日轴上的位置差（信号日不在轴上时取次一交易日）
    tdays = list(spx.index)
    tpos = {d: i for i, d in enumerate(tdays)}

    def tpos_of(sig: pd.Timestamp) -> int:
        if sig in tpos:
            return tpos[sig]
        nxt = [d for d in tdays if d > sig]
        return tpos[nxt[0]] if nxt else len(tdays) - 1

    me_pos = {tpos_of(d) for d in me_days}

    def near(sig: pd.Timestamp, span: int = 10) -> bool:
        p = tpos_of(sig)
        return any(abs(p - m) <= span for m in me_pos)

    co_occur = sum(1 for d in c2d_all if near(d))
    arms["AUX_C2down_vs_moduleE_coincidence"] = {
        "c2_down_events_from": str(min(c2d_all).date()) if c2d_all else None,
        "n_c2_down_total_full_history": len(c2d_all),
        "coincident_within_10td": co_occur,
        "pct": round(co_occur / len(c2d_all), 4) if c2d_all else None,
        "module_e_v1_n": len(me_days),
        "note": ("正版 A 下一步 1 的日期级交叉核验：C2 下行臂事件与模块 E "
                 "v1 买入信号（B20&B50≤15）±10 交易日伴生率（沿用 C 组 E1 "
                 "伴生统计口径）；辅助统计不进 OD 判定"),
    }
    res["new_signal_arms"] = arms

    # ---- 相关系数矩阵（全表）----
    matrix = pd.concat([legs] + [pd.Series(v, name=k) for k, v in
                                 leg_series.items()], axis=1).corr(
        method="pearson").round(4)
    matrix.to_csv(RAW / "correlation_matrix_pearson.csv")
    res["matrix_note"] = "见 correlation_matrix_pearson.csv（全窗口 inner join）"

    (RAW / "orthogonality_results.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False))
    brief_arms = {}
    for k, v in arms.items():
        if k.startswith("AUX_"):
            brief_arms[k] = {"coincident_within_10td":
                             v["coincident_within_10td"],
                             "n_total": v["n_c2_down_total_full_history"]}
        else:
            brief_arms[k] = {kk: v[kk] for kk in
                             ("n_events_in_window", "pearson_vs_b9",
                              "pearson_vs_lei", "verdict")}
    print(json.dumps({
        "OD0": res["OD0_calibration"],
        "arms": brief_arms,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
