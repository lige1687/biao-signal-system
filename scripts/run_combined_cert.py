#!/usr/bin/env python3
"""合体认证·预注册实验：B9 宽度主仓 + LEI 卫星腿分账制（2026-08-31）。

依据：docs/SYSTEM-VALUE-SUMMARY-2026-08-31.md 第七节「合体认证：宽度主仓
+ LEI 卫星腿（分账制）……→ 系统终极形态定型」。本实验是该路线的第一次
认证尝试（宽度层收益引擎 × LEI 执行纪律的正交叠加）。

【预注册协议】（跑前写死，跑后不改）
架构（分账制）：
- 主仓腿 = B9：9 标的等权 × B200 三档（<43.3→1.0，<56.7→0.5，≥56.7→0），
  周频信号次日生效；5% 调仓带；单边 10bp。机械与 run_portfolio_split 的
  B_全宽度闸 臂逐位一致（直接 import 复用）。
- 卫星腿 = LEI 真实可执行信号流（A 门禁 + B' 去重后 217 笔，1% 风险 +
  回撤降级 + 并发上限，无宽度闸）：复用 raw/full_stack/full_stack_results.json
  的 task2.fund_only 曲线（初始 100 万，起点 2017-03-24 = 第一笔建仓日，
  截断无盈亏丢失）。
- 分账 = 两腿独立复利、永不再平衡、无跨腿资金调度；合体权益 = 两腿之和。
  对照臂：月末再平衡 80/20（检验分账 vs 再平衡）。

窗口：2017-03-24 → 2026-07-17（卫星腿曲线首末日；主仓腿同窗截断）。
精度声明：卫星腿曲线为周频（信号扫描口径），对齐日频用 ffill——周内
波动被平滑，卫星腿回撤为低估口径（如实标注，不影响主结论方向）。

臂：持有基准 / B9 单腿 / LEI 单腿 / 合体 w_sat∈{10%,20%,30%} / 月度再平衡 80/20。

判定（冻结）：
- Q1（收益不稀释）：合体(20%) 年化 ≥ B9 同窗年化 − 1.0pp；
- Q2（回撤纪律）：合体(20%) 最大回撤 ≤ B9 同窗最大回撤 + 3.0pp；
- Q3（阴跌段贡献）：2021-06-18→2024-02-29 段内（段前权益起算），
  合体(20%) 回撤 ≤ B9 同段回撤 + 1.0pp；
- Q4（比例敏感性）：w_sat=10% 与 30% 下 Q1∧Q2 方向均不变；
- LOO（留一）：主仓 9 标的去任一，Q1∧Q2 布尔不变 ≥7/9；
- PLC（安慰剂）：B200 循环平移 300 次（seed=0，偏移∈[130,T−130] 均匀抽），
  统计量 = 合体(20%) 年化 − 持有年化，真实值 ≥ 零分布 P95；
- 总 PASS = Q1∧Q2∧Q3∧Q4∧LOO∧PLC。

纪律：不改 configs/web/engine/service；卫星腿 0 个新 execute_run（复用
已留痕 run JSON 曲线）。结论只到「建议」级。
输出：docs/experiments/raw/combined_cert/combined_cert_results.json + curves csv
复现：PYTHONHASHSEED=0 python3 scripts/run_combined_cert.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402

RAW = SRC / "combined_cert"
RAW.mkdir(parents=True, exist_ok=True)

# ── 冻结配置 ──
W_SATS = (0.10, 0.20, 0.30)
W_MAIN_STD = 0.20          # 主口径
Q1_TOL, Q2_TOL, Q3_TOL = 1.0, 3.0, 1.0
SEG_LO, SEG_HI = "2021-06-18", "2024-02-29"
N_SHIFTS, SEED, MIN_OFF = 300, 0, 130
LOO_TH = 7
INIT = 1_000_000.0


def load_sat_curve() -> pd.Series:
    """卫星腿周频权益曲线（full_stack fund_only，初始 100 万）。"""
    d = json.loads((SRC / "full_stack/full_stack_results.json").read_text())
    curve = d["task2"]["fund_only"]["curve"]
    s = pd.Series(
        {pd.Timestamp(p["date"]): float(p["equity"]) for p in curve},
    ).sort_index()
    return s / s.iloc[0] * INIT


def seg_dd(eq: pd.Series, lo: str, hi: str) -> float:
    """段内最大回撤（段前权益起算，与 full_stack 口径一致）。"""
    seg = eq[(eq.index >= pd.Timestamp(lo)) & (eq.index <= pd.Timestamp(hi))]
    base = eq[eq.index < pd.Timestamp(lo)]
    start = float(base.iloc[-1]) if len(base) else float(seg.iloc[0])
    peak = start
    worst = 0.0
    for v in seg.values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst * 100.0


def yearly_returns(eq: pd.Series) -> dict[str, float]:
    out: dict[str, float] = {}
    years = sorted({d.year for d in eq.index})
    prev = float(eq.iloc[0])
    for y in years:
        sub = eq[eq.index.year == y]
        last = float(sub.iloc[-1])
        out[str(y)] = round((last / prev - 1.0) * 100, 1)
        prev = last
    return out


def combine(eq_main_n: pd.Series, eq_sat_n: pd.Series, w_sat: float) -> pd.Series:
    """分账合成：两腿独立复利（归一化曲线），权重只定初始预算。"""
    return eq_main_n * (1.0 - w_sat) + eq_sat_n * w_sat


def rebalance_series(eq_main_n: pd.Series, eq_sat_n: pd.Series,
                     w_sat: float) -> pd.Series:
    """月末再平衡对照：每月末把两腿拉回目标权重。"""
    r_main = eq_main_n.pct_change().fillna(0.0)
    r_sat = eq_sat_n.pct_change().fillna(0.0)
    idx = eq_main_n.index
    months = [(d.year, d.month) for d in idx]
    a, b = 1.0 - w_sat, w_sat           # 两腿当前权重（和为 1）
    vals = []
    for i in range(len(idx)):
        a *= 1.0 + r_main.iloc[i]
        b *= 1.0 + r_sat.iloc[i]
        total = a + b
        vals.append(total)
        if i + 1 < len(idx) and months[i + 1] != months[i]:
            a, b = total * (1.0 - w_sat), total * w_sat
    return pd.Series(vals, index=idx)


def arm_metrics(eq: pd.Series, sat_ref: pd.Series | None = None) -> dict:
    m = rps.metrics(eq)
    m["seg_dd_pct"] = round(seg_dd(eq, SEG_LO, SEG_HI), 2)
    return m


def q12_verdict(ann_c: float, dd_c: float, ann_b9: float, dd_b9: float) -> tuple[bool, bool]:
    q1 = bool(float(ann_c) >= float(ann_b9) - Q1_TOL)
    q2 = bool(float(dd_c) >= float(dd_b9) - Q2_TOL)   # dd 为负数，"不深于 +3pp"
    return q1, q2


def main() -> None:
    # ── 主仓腿（B9 机械复用）──
    b200 = rps.load_breadth()
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    frames = {}
    for name, rel in members:
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    prices_all = pd.DataFrame(frames)
    prices_all = prices_all[(prices_all.index >= pd.Timestamp(rps.WIN_START))
                            & (prices_all.index <= pd.Timestamp(rps.WIN_END))] \
        .dropna(axis=0, how="any")

    # ── 卫星腿（周频 → 日频 ffill）──
    sat = load_sat_curve()
    w_start, w_end = sat.index[0], sat.index[-1]
    prices = prices_all[(prices_all.index >= w_start)
                        & (prices_all.index <= w_end)]
    idx = prices.index
    tier = rps.tier_daily(b200, idx)
    expo_b9 = pd.DataFrame({c: tier for c in prices.columns})
    ones = pd.DataFrame(1.0, index=idx, columns=prices.columns)

    eq_hold = rps.simulate(prices, ones)["eq"]
    eq_b9 = rps.simulate(prices, expo_b9)["eq"]
    sat_daily = sat.reindex(idx).ffill()
    sat_daily.iloc[0] = sat.iloc[0]

    eq_hold_n = eq_hold / eq_hold.iloc[0]
    eq_b9_n = eq_b9 / eq_b9.iloc[0]
    sat_n = sat_daily / sat_daily.iloc[0]

    # ── 各臂 ──
    arms: dict[str, pd.Series] = {
        "hold": eq_hold_n,
        "b9": eq_b9_n,
        "lei": sat_n,
    }
    for w in W_SATS:
        arms[f"combo_{int(w*100)}"] = combine(eq_b9_n, sat_n, w)
    arms["combo_rebal_20"] = rebalance_series(eq_b9_n, sat_n, W_MAIN_STD)

    met = {k: arm_metrics(v) for k, v in arms.items()}
    b9m, cm = met["b9"], met["combo_20"]
    q1, q2 = q12_verdict(cm["ann_pct"], cm["maxdd_pct"], b9m["ann_pct"], b9m["maxdd_pct"])
    q3 = bool(float(cm["seg_dd_pct"]) >= float(b9m["seg_dd_pct"]) - Q3_TOL)
    ok10 = q12_verdict(met["combo_10"]["ann_pct"], met["combo_10"]["maxdd_pct"],
                       b9m["ann_pct"], b9m["maxdd_pct"])
    ok30 = q12_verdict(met["combo_30"]["ann_pct"], met["combo_30"]["maxdd_pct"],
                       b9m["ann_pct"], b9m["maxdd_pct"])
    q4 = all(ok10) and all(ok30)

    # ── 留一（主仓 9 池）──
    loo_ok, loo_detail = 0, {}
    for drop in dict(members):
        sub_frames = {k: v for k, v in frames.items() if k != drop}
        p2 = pd.DataFrame(sub_frames)
        p2 = p2[(p2.index >= w_start) & (p2.index <= w_end)].dropna(axis=0, how="any")
        t2 = rps.tier_daily(b200, p2.index)
        e2 = rps.simulate(p2, pd.DataFrame({c: t2 for c in p2.columns}))["eq"]
        e2n = e2 / e2.iloc[0]
        s2 = sat.reindex(p2.index).ffill()
        s2.iloc[0] = sat.iloc[0]
        s2n = s2 / s2.iloc[0]
        c2 = combine(e2n, s2n, W_MAIN_STD)
        m_b9, m_c = arm_metrics(e2n), arm_metrics(c2)
        j1, j2 = q12_verdict(m_c["ann_pct"], m_c["maxdd_pct"],
                             m_b9["ann_pct"], m_b9["maxdd_pct"])
        loo_detail[drop] = {"ann": m_c["ann_pct"], "maxdd": m_c["maxdd_pct"],
                            "ann_b9": m_b9["ann_pct"], "maxdd_b9": m_b9["maxdd_pct"],
                            "Q1": j1, "Q2": j2}
        loo_ok += int(j1 and j2)
    loo_pass = loo_ok >= LOO_TH

    # ── 安慰剂（B200 平移，只影响主仓腿）──
    b_win = b200[(b200.index >= idx[0]) & (b200.index <= idx[-1])]
    vals, bidx = b_win.values, b_win.index
    rng = np.random.default_rng(SEED)
    ann_hold = met["hold"]["ann_pct"]
    gap_real = met["combo_20"]["ann_pct"] - ann_hold
    gaps = []
    for _ in range(N_SHIFTS):
        off = int(rng.integers(MIN_OFF, len(vals) - MIN_OFF))
        b_shift = pd.Series(np.roll(vals, off), index=bidx)
        t_sh = rps.tier_daily(b_shift, idx)
        e_sh = rps.simulate(prices, pd.DataFrame({c: t_sh for c in prices.columns}))["eq"]
        e_sh_n = e_sh / e_sh.iloc[0]
        c_sh = combine(e_sh_n, sat_n, W_MAIN_STD)
        gaps.append(rps.metrics(c_sh)["ann_pct"] - ann_hold)
    gaps = np.array(gaps)
    p95 = float(np.percentile(gaps, 95))
    plc_pass = bool(gap_real >= p95)

    verdict = {
        "Q1_gain": q1, "Q2_dd": q2, "Q3_seg": q3, "Q4_scale": q4,
        "LOO_pass": loo_pass, "PLC_pass": plc_pass,
        "PASS_all": bool(q1 and q2 and q3 and q4 and loo_pass and plc_pass),
    }
    out = {
        "experiment": "combined_cert_b9_lei",
        "window": [str(w_start.date()), str(w_end.date())],
        "sat_curve_freq": "weekly_ffill(低估回撤口径)",
        "arms": met,
        "yearly": {k: yearly_returns(v) for k, v in arms.items()},
        "verdict_rules": {
            "Q1": f"combo20 ann >= b9 ann - {Q1_TOL}pp",
            "Q2": f"combo20 maxdd <= b9 maxdd + {Q2_TOL}pp",
            "Q3": f"combo20 seg_dd <= b9 seg_dd + {Q3_TOL}pp ({SEG_LO}~{SEG_HI})",
            "Q4": "Q1&Q2 hold at w_sat 10%/30%",
            "LOO": f">={LOO_TH}/9",
            "PLC": f"real gap >= P95 of {N_SHIFTS} shifts",
        },
        "loo_detail": loo_detail, "loo_ok": loo_ok,
        "placebo": {
            "n_shifts": N_SHIFTS, "gap_real": round(gap_real, 2),
            "null_mean": round(float(gaps.mean()), 2),
            "null_p50": round(float(np.percentile(gaps, 50)), 2),
            "null_p95": round(p95, 2),
            "real_percentile": round(float((gaps < gap_real).mean() * 100), 1),
        },
        "verdict": verdict,
    }
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "combined_cert_results.json").write_text(text)

    # 曲线 CSV（研究展示用）
    pd.DataFrame({k: v for k, v in arms.items()}).to_csv(
        RAW / "combined_curves.csv", float_format="%.6f")

    print(json.dumps(out["arms"], ensure_ascii=False, indent=1))
    print("verdict:", json.dumps(verdict, ensure_ascii=False))
    print("placebo:", json.dumps(out["placebo"], ensure_ascii=False))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
