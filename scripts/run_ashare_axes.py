#!/usr/bin/env python3
"""A股新轴三合一·预注册实验（2026-08-31，跑前写死，跑后不改）。

A（P1 流动性轴）：M1 同比环比方向 × 宽度预算。乘数 = M1同比 ≥ 3 个月前
值 → 1.0，否则 0.7；月频，滞后一个月生效（发布延迟）。池 = B9（2015-06→）
与 创业板+纳指（2010-06→）。
判定：A1 三段阴跌（2018/2022/2023）合计改善 ≥8pp；A2 两段 V 反
（2019 / 2024-09→2025-12）合计恶化 ≤3pp；A3 全窗 Calmar ≥ 基线 −0.03。
B（P2 融资余额虹吸识别）：沪市融资余额 20 日增速处于 3 年滚动分位 ≥90%
且连续 20 个交易日 → 虹吸状态 ON；ON 时空仓档改为半仓（不追满），OFF
恢复。池 = 创业板+纳指 与 B9。
判定：B1 科技牛窗（2024-09-19→2026-08-18）超额改善 ≥5pp；B2 股灾段
（2015-06-12→2016-01-28）回撤 ≥ −60%；B3 全窗 Calmar ≥ 基线 −0.03。
C（通用行业组合扫描）：通用框架 =「A股行业/宽基腿 × B200 三档 + 纳指
持有」二腿结构，A 腿候选 14 个（创业板/证券/医疗/有色/军工/煤炭/钢铁/
计算机/传媒/白酒/地产/新能车/半导体399996/国证芯片980017），各自窗口
（多数 2015-06 起；创业板/有色/煤炭/钢铁/传媒/计算机 2010-06；芯片
2019-08）。判定（扫描门槛，非对照）：C1 对自家等权持有回撤浅 ≥8pp 且
Calmar 更高；C2 年化 ≥8.5% 且 Calmar ≥0.30。输出行业适配地图。
声明：C 为 14 次同框架扫视（探索性），排名供入池筛选参考；A/B 为单假设
预注册检验。费用/执行与其他实验一致（周频次日、5% 带、10bp）。

输出：docs/experiments/raw/ashare_axes/ashare_axes_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_ashare_axes.py
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
AX = SRC / "ashare_axes"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_bform_dynamic import simulate_direct  # noqa: E402
from run_bform_mini import load_series  # noqa: E402
from run_m5_walkforward import tier_for  # noqa: E402

PIXIC = ("纳斯达克", "portfolio_split/ixic_close.parquet")
A1_TH, A2_TH, CAL_TOL = 8.0, 3.0, 0.03
B1_TH, B2_DD = 5.0, -60.0
C1_DD, C2_ANN, C2_CAL = 8.0, 8.5, 0.30


def liq_mult_daily(dates) -> pd.Series:
    df = pd.read_csv(AX / "money_supply_m.csv")
    df["m"] = pd.to_datetime(df["月份"].str.replace("年", "-").str.replace("月份", ""), format="%Y-%m")
    df = df.sort_values("m")
    m1 = pd.to_numeric(df["货币(M1)-同比增长"], errors="coerce")
    up = (m1 >= m1.shift(3)).astype(float)  # M1 同比方向
    s = pd.Series(up.values, index=df["m"].values)
    s.index = s.index.to_period("M").to_timestamp("M") + pd.offsets.MonthBegin(1)  # 次月生效
    daily = s.reindex(s.index.union(pd.DatetimeIndex(dates))).ffill().reindex(dates)
    return daily.fillna(1.0).map(lambda v: 1.0 if v >= 1 else 0.7)


def siphon_daily(dates) -> pd.Series:
    df = pd.read_csv(AX / "margin_sh.csv")
    df["date"] = pd.to_datetime(df["日期"])
    df = df.sort_values("date").set_index("date")
    bal = pd.to_numeric(df["融资余额"], errors="coerce").dropna()
    g20 = bal.pct_change(20)
    rank = g20.rolling(750, min_periods=500).rank(pct=True)  # 3年自分位
    on = (rank >= 0.90).rolling(20, min_periods=20).min() == 1  # 连续20日
    on = on.reindex(pd.DatetimeIndex(dates)).ffill().fillna(False)
    return on


def pool_frames(cfg, start):
    frames = {n: load_series(rel) for n, rel in cfg}
    px = pd.DataFrame(frames)
    cn = px[[cfg[0][0]]].dropna().index
    px = px.reindex(cn).ffill()
    px = px[(px.index >= pd.Timestamp(start))
            & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
    return px


def budget(px, b200, a_legs, liq=None, siphon=None):
    tier = tier_for(b200, px.index, 43.3, 56.7)
    if siphon is not None:
        tier = tier.copy()
        mask = (tier <= 0.001) & siphon
        tier[mask] = 0.5
    if liq is not None:
        tier = tier * liq
    ones = pd.DataFrame(1.0, index=px.index, columns=px.columns)
    expo = ones.copy()
    for c in a_legs:
        expo[c] = tier
    return expo / px.shape[1]


def met(px, expo):
    return rps.metrics(simulate_direct(px, expo))


def win(eq_or_px, lo, hi, is_eq=True):
    s = eq_or_px[(eq_or_px.index >= pd.Timestamp(lo)) & (eq_or_px.index <= pd.Timestamp(hi))]
    if len(s) < 2:
        return np.nan
    return float(s.iloc[-1] / s.iloc[0] - 1) * 100


def seg_sum(px, expo, segs):
    eq = simulate_direct(px, expo)
    return sum(win(eq, lo, hi) for lo, hi in segs)


def main() -> None:
    b200 = rps.load_breadth()
    B9 = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    DUO = [("创业板指", "siphon_detector/cyb_399006_close.parquet"),
           ("纳斯达克", "portfolio_split/ixic_close.parquet")]
    out = {}

    # ── A 流动性轴 ──
    liq = None
    for name, cfg, start, a_legs in [("A_B9", B9, "2015-06-16", [k for k, _ in B9]),
                                     ("A_DUO", DUO, "2010-06-01", ["创业板指"])]:
        px = pool_frames(cfg, start)
        liq = liq_mult_daily(px.index)
        base = met(px, budget(px, b200, a_legs))
        test = met(px, budget(px, b200, a_legs, liq=liq))
        segs_bad = [("2018-01-01", "2018-12-31"), ("2022-01-01", "2022-10-31"),
                    ("2023-01-01", "2023-12-31")]
        segs_v = [("2019-01-01", "2019-12-31"), ("2024-09-19", "2025-12-31")]
        imp_bad = seg_sum(px, budget(px, b200, a_legs, liq=liq), segs_bad) - \
            seg_sum(px, budget(px, b200, a_legs), segs_bad)
        imp_v = seg_sum(px, budget(px, b200, a_legs, liq=liq), segs_v) - \
            seg_sum(px, budget(px, b200, a_legs), segs_v)
        a1 = imp_bad >= A1_TH
        a2 = imp_v >= -A2_TH
        a3 = (test["calmar"] or 0) >= (base["calmar"] or 0) - CAL_TOL
        out[name] = {"base": base, "test": test, "阴跌改善pp": round(imp_bad, 1),
                     "V反代价pp": round(imp_v, 1),
                     "A1": bool(a1), "A2": bool(a2), "A3": bool(a3),
                     "PASS": bool(a1 and a2 and a3)}

    # ── B 融资余额虹吸 ──
    for name, cfg, start, a_legs in [("B_DUO", DUO, "2010-06-01", ["创业板指"]),
                                     ("B_B9", B9, "2015-06-16", [k for k, _ in B9])]:
        px = pool_frames(cfg, start)
        sip = siphon_daily(px.index)
        base = met(px, budget(px, b200, a_legs))
        test = met(px, budget(px, b200, a_legs, siphon=sip))
        tech = [("2024-09-19", "2026-08-18")]
        imp_tech = seg_sum(px, budget(px, b200, a_legs, siphon=sip), tech) - \
            seg_sum(px, budget(px, b200, a_legs), tech)
        eq_t = simulate_direct(px, budget(px, b200, a_legs, siphon=sip))
        dd_crash = rps.metrics(eq_t[(eq_t.index >= pd.Timestamp("2015-06-12")) &
                                    (eq_t.index <= pd.Timestamp("2016-01-28"))])["maxdd_pct"]
        b1 = imp_tech >= B1_TH
        b2 = (dd_crash if dd_crash == dd_crash else -100) >= B2_DD
        b3 = (test["calmar"] or 0) >= (base["calmar"] or 0) - CAL_TOL
        out[name] = {"base": base, "test": test, "科技牛改善pp": round(imp_tech, 1),
                     "股灾段回撤": dd_crash, "sip_on_frac": round(float(sip.mean()), 3),
                     "B1": bool(b1), "B2": bool(b2), "B3": bool(b3),
                     "PASS": bool(b1 and b2 and b3)}

    # ── C 通用行业组合扫描 ──
    SECTORS = {
        "创业板指": ("siphon_detector/cyb_399006_close.parquet", "2010-06-01"),
        "国证有色": ("portfolio_split/sz399395_close.parquet", "2010-06-01"),
        "中证煤炭": ("portfolio_split/sz399998_close.parquet", "2015-06-16"),
        "国证钢铁": ("portfolio_split/sz399440_close.parquet", "2010-06-01"),
        "中证传媒": ("portfolio_split/sz399971_close.parquet", "2010-06-01"),
        "中证计算机": ("portfolio_split/sz399363_close.parquet", "2010-06-01"),
        "证券公司": ("siphon_detector/sec_399975_close.parquet", "2015-06-16"),
        "中证医疗": ("portfolio_split/sz399989_close.parquet", "2015-06-16"),
        "中证军工": ("portfolio_split/sz399967_close.parquet", "2015-06-16"),
        "中证白酒": ("portfolio_split/sz399997_close.parquet", "2015-06-16"),
        "国证地产": ("portfolio_split/sz399393_close.parquet", "2015-06-16"),
        "新能车": ("portfolio_split/sz399976_close.parquet", "2015-06-16"),
        "半导体": (str(AX / "sz399996_close.parquet").replace(str(SRC) + "/", ""), "2015-06-16"),
        "国证芯片": ("ashare_axes/sz980017_close.parquet", "2019-08-16"),
    }
    scan = {}
    for name, (rel, start) in SECTORS.items():
        try:
            px = pool_frames([(name, rel), PIXIC], start)
        except Exception:
            continue
        if len(px) < 700:
            continue
        m = met(px, budget(px, b200, [name]))
        h = met(px, pd.DataFrame(1.0, index=px.index, columns=px.columns) / px.shape[1])
        c1 = (m["maxdd_pct"] - h["maxdd_pct"] >= C1_DD) and (m["calmar"] or 0) > (h["calmar"] or 0)
        c2 = (m["ann_pct"] >= C2_ANN) and ((m["calmar"] or 0) >= C2_CAL)
        scan[name] = {"窗口": f"{start}→{rps.WIN_END}", "M版": m, "持有": h,
                      "C1": bool(c1), "C2": bool(c2),
                      "判定": "适配" if (c1 and c2) else ("部分" if c1 else "不适配")}
    out["C_scan"] = scan

    path = AX / "ashare_axes_results.json"
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)
    for k in ["A_B9", "A_DUO", "B_DUO", "B_B9"]:
        r = out[k]
        print(f"[{k}] base ann={r['base']['ann_pct']} calmar={r['base']['calmar']} | "
              f"test ann={r['test']['ann_pct']} calmar={r['test']['calmar']} | PASS={r['PASS']}")
    print("C 扫描:")
    for n, r in sorted(scan.items(), key=lambda kv: -(kv[1]["M版"]["calmar"] or 0)):
        print(f"  {n:6s} [{r['窗口']}] M版 ann={r['M版']['ann_pct']:6.2f}% dd={r['M版']['maxdd_pct']:7.2f}% "
              f"calmar={r['M版']['calmar']:.3f} | 持有 ann={r['持有']['ann_pct']:6.2f}% dd={r['持有']['maxdd_pct']:7.2f}% → {r['判定']}")
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
