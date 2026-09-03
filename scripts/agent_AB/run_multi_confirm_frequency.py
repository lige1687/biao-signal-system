# -*- coding: utf-8 -*-
"""Prompt AB：语义四前置验证——"多重确认"共触发频率统计（纯统计，不回测）。

==============================================================================
预注册协议（本 docstring 在任何统计运行之前写死冻结，跑后不得修改任何
判定线；本文件为新增文件，不改 src/ 与任何既有归档）
==============================================================================

一、候选信号（全部引用已验证/已归档参数，不发明信号；参数来源逐条注明）

  T1  LADDER_CNALL  全A宽度三档逆势引擎事件（现行执行配置 cyb_attack
      [399006] 与 csi1000_attack [512100] 的共同信号源）：
      B200（站上200日线个股占比，cn_all 全A宽度表）3 档 contrarian 阶梯，
      边界 low_edge=30 / high_edge=70 → 档位线 43.33 / 56.67，gamma=1.0。
      来源：kuandu-quanzhan-ARCHIVE-2026-09-01 通过清单"冠军三档"（边界
      30/70→43.3/56.7，gamma1.0）+ src/lei_signal/timing_backtest/service.py
      EXEC_CONFIGS（cyb_attack / csi1000_attack 两配置的 breadth 参数均缺省
      继承 INSTRUMENTS 的 cn_all——见"结构性事实"一节）。
      事件 = B200 跨档位线当日；方向：下穿（档位序数变小，逆势加仓侧）
      = 低位侧 risk_low；上穿 = 高位侧 risk_high。
      有效性：该行 n200 ≥ 50 且 b200 非 NaN。

  T2  LADDER_CYB  创业板专属宽度三档（参数同 T1，驱动序列换成 cn_cyb
      B200）。来源：BREADTH_FILES cn_cyb（breadth_cyb.parquet，宽度组
      "创业板专属 B20/B50/B200"）；参数照抄冠军三档。事件与方向定义同 T1。

  A1  ALARM_DUAL20  双≤20 底部警报（"定心丸"）：cn_all 的 b50≤20 且
      b200≤20；事件 = 条件由假转真当日（episode 起点日）。
      来源：kuandu-quanzhan-ARCHIVE 通过清单"双极值警报"（双≤20 后120日
      13/13 正）+ service.py alert_state()（20/85 现行阈值）。方向 risk_low。

  A2  ALARM_DUAL85  双≥85 热度警戒：b50≥85 且 b200≥85，episode 起点。
      方向 risk_high。（敏感性描述档：双≥90 计数另列，只作描述不进判定。）

  M1  MACRO_E1  融资余额20日急坠（去杠杆）：chg20≤滚动1250日Q5、冷却20日，
      12 事件。来源：ashare-macro-ARCHIVE-2026-09-01（E1，证伪为预警、
      反向现象为底部特征）+ raw/ashare-macro/ashare_macro_results.json。
      方向 risk_low（急跌/底部侧）。
  M2  MACRO_E2  融资余额20日急升（杠杆过热）：chg20≥滚动Q95，9 事件。
      同上来源。方向 risk_high。
  M3  UT_C2DOWN  美债10Y利率20日急降（下行臂，扩张分位≤5），23 事件。
      来源：us-treasury-ARCHIVE-2026-09-01（C2，证伪为触发；观察中下行臂
      =恐慌/紧急宽松窗口）+ raw/us-treasury-signal/c2_down_events.csv。
      方向 risk_low。
  M4  UT_C2UP    美债10Y利率20日急升（上行臂，分位≥95），25 事件。
      来源：同上 c2_up_events.csv。方向 risk_high。
  M5  VIX_S1  VIX9D/VIX 期限倒挂解除，180 事件。来源：
      vix-sentiment-ARCHIVE-2026-09-01（S1，证伪为触发）+
      raw/vix-sentiment/events_S1_term_recontango.csv。
      方向 risk_low（恐慌极值解除侧）。
  M6  VIX_S2  VIX/VIX3M 扩张分位≤10（深度平静），105 事件。来源：同上
      events_S2_vix_vix3m_extreme.csv（S2，证伪；其后 12m 跑输=过热侧）。
      方向 risk_high。

二、信号对（跑前冻结；每对指定 A=技术侧为主事件、B=确认侧）

  P1   T2 × T1   （家族1：两个不同宽度源的技术信号，创业板专属 vs 全A）
  P1P  T1 × T1   （结构性事实核对，非统计对：现行执行配置下创业板与
       中证1000 两个三档信号由同一条 cn_all B200 序列驱动——只登记事实，
       不进三选一判定）
  P2a  T1(risk_low)  × M1      （家族2：技术 × A股宏观）
  P2b  T1(risk_high) × M2
  P2c  T1(risk_low)  × M3      （家族2：技术 × 美债）
  P2d  T1(risk_high) × M4
  P2e  T1(risk_low)  × M5      （家族2：技术 × VIX）
  P2f  T1(risk_high) × M6
  P3a  T1(risk_low)  × A1      （家族3：同市场不同颗粒度）
  P3b  T1(risk_high) × A2

三、统计口径（跑前冻结）

  窗口：每对取两信号各自有效期的自然重叠窗（事件最早/最晚日推导），
  不做截尾。距离与窗口统一用**日历日**（跨市场对无法共用交易日历；
  N 任务 B'/C 中位错开 607 天同为日历日口径，直接可比）。
  同向：两事件方向标签相同（同 risk_low 或同 risk_high）。
  共触发@K：A 的同向事件中，存在 B 的同向事件与其日期差 |Δ|≤K 日历日
  的 A 事件数（K ∈ {0,2,5,10}）。K=0 即"同日同向"。
  比例：共触发@K ÷ 窗口内 A 的同向事件总数（ratioA）；对称地算 B 侧
  （ratioB）。最近邻间隔：每个 A 同向事件到最近 B 同向事件的日历日
  （可同可异号），报告中位数与众数信息；反向同。
  时间分布：共触发@0 事件的逐年计数、覆盖的不同自然年数、最密集的
  连续 3 年窗口内占比（top3yr_share）。

四、"样本够不够"判定线（跑前写死，论证如下）

  判定对象：每对的主指标 N0 = 共触发@0（同日同向的 A 事件数）。

  - 可行（PASS）：N0 ≥ 20 且 覆盖 ≥4 个不同自然年 且 top3yr_share ≤ 60%。
  - 证据不足（WATCH）：10 ≤ N0 < 20；或 N0 ≥ 20 但年分布两条未同时满足。
  - 不可行（FAIL）：N0 < 10；或该对被判定为结构性非独立（如 P1P）。

  论证：① 对齐本仓库 N 任务（module-conflict-resonance-ARCHIVE）预注册
  的"冲突组 n≥20 才有方差可检验"下限——后续阶段要比较"双确认事件 vs
  单信号事件"的质量差异，两格各 ≥20 是估计均值差不至沦为噪声的最低
  经验线（N 任务冲突组 n=1 直接 sample_insufficient 即此先例）；② 对齐
  prompt-W 对短样本的处理原则（短窗口数字不得冒充长期结论，样本不足
  必须如实降级）；③ 年分布约束防"全部共触发挤在同一轮牛熊"——那等于
  一个市场阶段的一个事件被数成 20 次，不是 20 个独立样本。
  K>0 档只作敏感性描述：若某对仅在 K≥5 才达到 20，登记"放宽窗口才够，
  时点同步性弱"，不得单独据此判可行。

五、与 N 任务对齐核对的量（跑前冻结）

  对每对输出：A 同向事件到最近 B 同向事件的中位日历间隔（对照 N 任务
  B'/C 中位 607 天）；±10 日历日内有同向 B 事件的 A 事件占比（对照 N 任务
  同标的同日跨模块共触发≈0、间隔全部>60 天）。

六、红线

  纯统计：不做回测、不算收益、不设计仓位结构、不使用买卖指令词汇。
  双跑：PYTHONHASHSEED=0 / =42 各完整跑一遍，输出 canonical JSON 的
  sha256 必须一致。
==============================================================================
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
CACHE = Path.home() / ".lei_signal_lab/cache/timing"
RAW = REPO / "docs/experiments/raw"
OUT_JSON = REPO / "scripts/agent_AB/results_multi_confirm.json"

# ---------------- 预注册常量（与 docstring 一致，冻结） ----------------
K_GRID = [0, 2, 5, 10]              # 日历日
PASS_N0, PASS_YEARS = 20, 4         # 可行线
PASS_TOP3_SHARE = 0.60              # 最密 3 年窗口占比上限
WATCH_N0 = 10                       # 证据不足下限
LADDER_EDGES = [30 + 40 * 1 / 3, 30 + 40 * 2 / 3]  # 43.33 / 56.67
MIN_STOCKS = 50                     # n50/n200 最低成分数（行有效性）

DUAL_LOW, DUAL_HIGH = 20.0, 85.0    # 警报现行阈值（service.py alert_state）
DUAL_HIGH_SENS = 90.0               # 描述性敏感档（只计数不进判定）


# ---------------- 信号重建 ----------------

def ladder_events(breadth_name: str) -> pd.DataFrame:
    """三档阶梯跨线事件：返回 DataFrame[date, direction]。"""
    df = pd.read_parquet(CACHE / f"{breadth_name}.parquet")
    ok = df["b200"].notna() & (df["n200"] >= MIN_STOCKS)
    b = df.loc[ok, "b200"].sort_index()
    idx = pd.Series(
        np.searchsorted(np.array(LADDER_EDGES), b.to_numpy(float), side="right"),
        index=b.index,
    )
    chg = idx.diff()
    ev = chg[chg != 0].dropna()
    # 方向：档位序数变小 = B200 下穿 = risk_low；变大 = risk_high
    out = pd.DataFrame(
        {
            "date": ev.index.normalize(),
            "direction": ["risk_low" if v < 0 else "risk_high" for v in ev.values],
        }
    )
    return out


def alarm_onsets(threshold_low: bool, level: float) -> pd.DataFrame:
    """双极值警报 episode 起点日。threshold_low=True 为双≤level。"""
    df = pd.read_parquet(CACHE / "breadth_cn_all.parquet")
    ok = (
        df["b50"].notna() & df["b200"].notna()
        & (df["n50"] >= MIN_STOCKS) & (df["n200"] >= MIN_STOCKS)
    )
    sub = df.loc[ok, ["b50", "b200"]].sort_index()
    if threshold_low:
        cond = (sub["b50"] <= level) & (sub["b200"] <= level)
    else:
        cond = (sub["b50"] >= level) & (sub["b200"] >= level)
    onset = cond & ~cond.shift(1, fill_value=False)
    dates = sub.index[onset].normalize()
    return pd.DataFrame(
        {"date": dates, "direction": ["risk_low" if threshold_low else "risk_high"] * len(dates)}
    )


def fixed_events(dates: list, direction: str) -> pd.DataFrame:
    return pd.DataFrame(
        {"date": pd.to_datetime(dates).normalize(), "direction": [direction] * len(dates)}
    )


def load_macro_events() -> dict:
    ev: dict[str, pd.DataFrame] = {}
    res = json.loads((RAW / "ashare-macro/ashare_macro_results.json").read_text())
    ev["M1_E1"] = fixed_events(
        [e["date"] for e in res["events"]["E1_deleveraging"]["list"]], "risk_low"
    )
    ev["M2_E2"] = fixed_events(
        [e["date"] for e in res["events"]["E2_overheating"]["list"]], "risk_high"
    )
    c2d = pd.read_csv(RAW / "us-treasury-signal/c2_down_events.csv")
    ev["M3_C2DOWN"] = fixed_events(sorted(c2d["exec_date"].tolist()), "risk_low")
    c2u = pd.read_csv(RAW / "us-treasury-signal/c2_up_events.csv")
    ev["M4_C2UP"] = fixed_events(sorted(c2u["exec_date"].tolist()), "risk_high")
    s1 = pd.read_csv(RAW / "vix-sentiment/events_S1_term_recontango.csv")
    ev["M5_VIXS1"] = fixed_events(sorted(s1["signal_date"].tolist()), "risk_low")
    s2 = pd.read_csv(RAW / "vix-sentiment/events_S2_vix_vix3m_extreme.csv")
    ev["M6_VIXS2"] = fixed_events(sorted(s2["signal_date"].tolist()), "risk_high")
    return ev


# ---------------- 配对统计 ----------------

def pair_stats(a: pd.DataFrame, b: pd.DataFrame, direction: str) -> dict:
    """A/B 限定同 direction 后做共触发统计（日历日口径）。"""
    ae = a[a["direction"] == direction].sort_values("date").reset_index(drop=True)
    be = b[b["direction"] == direction].sort_values("date").reset_index(drop=True)
    if len(ae) == 0 or len(be) == 0:
        return {
            "direction": direction, "n_a": int(len(ae)), "n_b": int(len(be)),
            "window": None, "co_at_K": {str(k): 0 for k in K_GRID},
            "ratioA_at_K": {str(k): None for k in K_GRID},
            "ratioB_at_K": {str(k): None for k in K_GRID},
            "median_gap_days": None, "gap_within10_ratioA": None,
            "years": {}, "n_years": 0, "top3yr_share": None, "n0": 0,
        }
    start = max(ae["date"].min(), be["date"].min())
    end = min(ae["date"].max(), be["date"].max())
    ae = ae[(ae["date"] >= start) & (ae["date"] <= end)].reset_index(drop=True)
    be = be[(be["date"] >= start) & (be["date"] <= end)].reset_index(drop=True)
    ad = ae["date"].to_numpy()
    bd = be["date"].to_numpy()

    co = {}
    for k in K_GRID:
        # 对每个 A 事件找 |Δ|≤k 的 B 事件（双指针即可，事件量 ≤ 数百）
        matched = 0
        for d in ad:
            lo = pd.Timestamp(d) - pd.Timedelta(days=k)
            hi = pd.Timestamp(d) + pd.Timedelta(days=k)
            j = bd.searchsorted(lo.to_datetime64())
            if j < len(bd) and bd[j] <= hi.to_datetime64():
                matched += 1
        co[str(k)] = int(matched)
    ratio_a = {str(k): (round(co[str(k)] / len(ae), 4) if len(ae) else None) for k in K_GRID}
    ratio_b = {}
    for k in K_GRID:
        matched_b = 0
        for d in bd:
            lo = pd.Timestamp(d) - pd.Timedelta(days=k)
            hi = pd.Timestamp(d) + pd.Timedelta(days=k)
            j = ad.searchsorted(lo.to_datetime64())
            if j < len(ad) and ad[j] <= hi.to_datetime64():
                matched_b += 1
        ratio_b[str(k)] = round(matched_b / len(be), 4) if len(be) else None

    gaps = []
    for d in ad:
        j = bd.searchsorted(d)
            # 最近邻：候选 j 与 j-1
        best = None
        for cand in (j - 1, j):
            if 0 <= cand < len(bd):
                g = abs((pd.Timestamp(d) - pd.Timestamp(bd[cand])).days)
                best = g if best is None else min(best, g)
        gaps.append(best)
    med_gap = int(pd.Series(gaps).median()) if gaps else None
    within10 = round(sum(1 for g in gaps if g is not None and g <= 10) / len(gaps), 4) if gaps else None

    n0 = co["0"]
    matched_dates = [
        str(pd.Timestamp(d).date())
        for d, g in zip(ad, gaps) if g == 0
    ]
    years: dict[str, int] = {}
    for d in matched_dates:
        years[d[:4]] = years.get(d[:4], 0) + 1
    yr_sorted = sorted(years.values(), reverse=True)
    top3 = sum(yr_sorted[:3]) / n0 if n0 else None
    return {
        "direction": direction,
        "n_a": int(len(ae)), "n_b": int(len(be)),
        "window": [str(start.date()), str(end.date())],
        "co_at_K": co, "ratioA_at_K": ratio_a, "ratioB_at_K": ratio_b,
        "median_gap_days": med_gap,
        "gap_within10_ratioA": within10,
        "years": dict(sorted(years.items())),
        "n_years": len(years),
        "top3yr_share": round(top3, 4) if top3 is not None else None,
        "n0": int(n0),
        "matched_dates": matched_dates,
    }


def verdict_of(stats: dict, non_independent: bool = False) -> str:
    """预注册判定线（冻结）：FAIL <10 或非独立；WATCH 10-19 或年分布不达；
    PASS ≥20 且 ≥4 年 且 top3 ≤60%。"""
    if non_independent:
        return "FAIL_结构性非独立"
    n0 = stats["n0"]
    if n0 < WATCH_N0:
        return "FAIL_不可行"
    if n0 >= PASS_N0 and stats["n_years"] >= PASS_YEARS and (
        stats["top3yr_share"] is not None and stats["top3yr_share"] <= PASS_TOP3_SHARE
    ):
        return "PASS_可行"
    return "WATCH_证据不足"


def main() -> int:
    signals: dict[str, pd.DataFrame] = {}
    signals["T1_LADDER_CNALL"] = ladder_events("breadth_cn_all")
    signals["T2_LADDER_CYB"] = ladder_events("breadth_cyb")
    signals["A1_DUAL20"] = alarm_onsets(True, DUAL_LOW)
    signals["A2_DUAL85"] = alarm_onsets(False, DUAL_HIGH)
    signals.update(load_macro_events())

    # 描述性敏感档：双≥90 计数（不进判定）
    a2s = alarm_onsets(False, DUAL_HIGH_SENS)
    sens_dual90_onsets = int(len(a2s))

    pairs = [
        ("P1", "T2_LADDER_CYB", "T1_LADDER_CNALL", ["risk_low", "risk_high"], False),
        ("P1P", "T1_LADDER_CNALL", "T1_LADDER_CNALL", ["risk_low", "risk_high"], True),
        ("P2a", "T1_LADDER_CNALL", "M1_E1", ["risk_low"], False),
        ("P2b", "T1_LADDER_CNALL", "M2_E2", ["risk_high"], False),
        ("P2c", "T1_LADDER_CNALL", "M3_C2DOWN", ["risk_low"], False),
        ("P2d", "T1_LADDER_CNALL", "M4_C2UP", ["risk_high"], False),
        ("P2e", "T1_LADDER_CNALL", "M5_VIXS1", ["risk_low"], False),
        ("P2f", "T1_LADDER_CNALL", "M6_VIXS2", ["risk_high"], False),
        ("P3a", "T1_LADDER_CNALL", "A1_DUAL20", ["risk_low"], False),
        ("P3b", "T1_LADDER_CNALL", "A2_DUAL85", ["risk_high"], False),
    ]

    sig_summary = {}
    for k in sorted(signals):
        s = signals[k]
        per_dir = s.groupby("direction").size().to_dict()
        sig_summary[k] = {
            "n_total": int(len(s)),
            "per_direction": {d: int(per_dir.get(d, 0)) for d in sorted(per_dir)},
            "first": str(s["date"].min().date()) if len(s) else None,
            "last": str(s["date"].max().date()) if len(s) else None,
        }

    results = {"pairs": {}}
    for pid, a_key, b_key, dirs, non_ind in pairs:
        stats_list = [
            pair_stats(signals[a_key], signals[b_key], d) for d in dirs
        ]
        combined_n0 = sum(s["n0"] for s in stats_list)
        if non_ind:
            verdict = verdict_of(stats_list[0], non_independent=True)
        else:
            # 双方向对：按预注册，主指标 = 两方向同日共触发之和，年分布
            # 用合并事件判断
            merged_years: dict[str, int] = {}
            for s in stats_list:
                for y, c in s["years"].items():
                    merged_years[y] = merged_years.get(y, 0) + c
            n_years = len(merged_years)
            yr_sorted = sorted(merged_years.values(), reverse=True)
            top3 = sum(yr_sorted[:3]) / combined_n0 if combined_n0 else None
            merged_stats = {
                "n0": combined_n0, "n_years": n_years,
                "top3yr_share": round(top3, 4) if top3 is not None else None,
            }
            verdict = verdict_of(merged_stats)
        results["pairs"][pid] = {
            "signal_A": a_key, "signal_B": b_key,
            "directions": dirs, "stats": stats_list, "verdict": verdict,
        }

    results["signals"] = sig_summary
    results["sensitivity_dual90_onsets"] = sens_dual90_onsets
    results["meta"] = {
        "breadth_cn_all": str(CACHE / "breadth_cn_all.parquet"),
        "breadth_cyb": str(CACHE / "breadth_cyb.parquet"),
        "macro_sources": [
            str(RAW / "ashare-macro/ashare_macro_results.json"),
            str(RAW / "us-treasury-signal/c2_down_events.csv"),
            str(RAW / "us-treasury-signal/c2_up_events.csv"),
            str(RAW / "vix-sentiment/events_S1_term_recontango.csv"),
            str(RAW / "vix-sentiment/events_S2_vix_vix3m_extreme.csv"),
        ],
        "preregistration": "见脚本 docstring（跑前冻结）",
    }

    OUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    canon = json.dumps(results, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    print(f"sha256={digest}")
    for pid in sorted(results["pairs"]):
        p = results["pairs"][pid]
        for s in p["stats"]:
            print(
                f"{pid} {p['signal_A']}x{p['signal_B']} {s['direction']}: "
                f"n_a={s['n_a']} n_b={s['n_b']} N0={s['n0']} "
                f"ratioA(K=0)={s['ratioA_at_K']['0']} ratioB(K=0)={s['ratioB_at_K']['0']} "
                f"medgap={s['median_gap_days']}d within10={s['gap_within10_ratioA']} "
                f"yrs={s['n_years']}"
            )
        print(f"  -> verdict: {p['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
