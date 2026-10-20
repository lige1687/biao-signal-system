#!/usr/bin/env python3
"""M5 跨市场候选 walk-forward 终审·预注册（2026-08-28，跑前写死，跑后不改）。

M5（bform-global-report）：A 腿（创业板/300/红利）× B200 三档 + 美腿
（标普/纳指）无闸。欠账：walk-forward、安慰剂。本脚本跑前者。
美腿无参数；选参仅作用于 A 腿档位线。

【预注册协议】
窗口 2010-06-01→2026-08-18。选样时点 2011/2013/…/2023 各年末（训练=窗
起点→该年末，1.5 年起步），网格 24 格（low∈{35,40,43.3,45,50}×
high∈{50,55,56.7,60,65}），按训练段 Calmar 选优冻结，OOS = 次两年段
（首段 2012-01 起）。
判定（冻结）：
- W1：WF-OOS 年化 ≥ H5 同窗 +1.0pp；
- W2：WF-OOS 最大回撤较 H5 同窗浅 ≥8pp；
- W3：WF-OOS 年化 ≥ 6%。
PASS = W1∧W2∧W3。附冻结 43.3/56.7 参考臂。

输出：docs/experiments/raw/portfolio_split/m5_walkforward_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_m5_walkforward.py
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
from run_bform_global import A_LEGS, load_px  # noqa: E402
from run_bform_dynamic import simulate_direct  # noqa: E402

LOWS = [35.0, 40.0, 43.3, 45.0, 50.0]
HIGHS = [50.0, 55.0, 56.7, 60.0, 65.0]
SEL_DATES = ["2011-12-31", "2013-12-31", "2015-12-31", "2017-12-31",
             "2019-12-31", "2021-12-31", "2023-12-31"]
OOS_START = "2012-01-01"
W1_GAP, W2_DD, W3_MIN = 1.0, 8.0, 6.0


def tier_for(b200, dates, low, high):
    bw, bsig = rps.weekly_last(b200)
    w = bw.map(lambda v: 1.0 if v < low else (0.5 if v < high else 0.0))
    out = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(bsig.values))
    for p, wt in zip(pos, w.values):
        if p + 1 < len(dates):
            out.iloc[p + 1] = wt
    return out.ffill().fillna(0.0)


def m5_eq(px, b200, low, high):
    n = px.shape[1]
    tier = tier_for(b200, px.index, low, high)
    expo = pd.DataFrame(1.0, index=px.index, columns=px.columns)
    for c in px.columns:
        if c in A_LEGS:
            expo[c] = tier
    return simulate_direct(px, expo / n)


def seg_metrics(eq, lo, hi):
    seg = eq[(eq.index >= pd.Timestamp(lo)) & (eq.index <= pd.Timestamp(hi))]
    seg = seg / seg.iloc[0]
    n = len(seg)
    ann = float(seg.iloc[-1] ** (252.0 / n) - 1) * 100
    dd = float((seg / seg.cummax() - 1).min()) * 100
    return ann, dd


def main() -> None:
    b200 = rps.load_breadth()
    px = load_px()
    dates = px.index
    n = px.shape[1]
    ones = pd.DataFrame(1.0, index=dates, columns=px.columns)
    h5 = simulate_direct(px, ones / n)

    picks = {}
    for sel in SEL_DATES:
        best, best_cal = None, -9e9
        for low in LOWS:
            for high in HIGHS:
                if low >= high:
                    continue
                eq = m5_eq(px, b200, low, high)
                ann, dd = seg_metrics(eq, px.index[0], sel)
                cal = ann / abs(dd) if dd < 0 else -9e9
                if cal > best_cal:
                    best_cal, best = cal, (low, high)
        picks[sel] = best

    bounds = [pd.Timestamp(OOS_START)] + [pd.Timestamp(d) for d in SEL_DATES[1:]] + [dates[-1]]
    eq_parts, cum, segs = [], 1.0, []
    for i, sel in enumerate(SEL_DATES):
        low, high = picks[sel]
        eq = m5_eq(px, b200, low, high)
        seg = eq[(eq.index >= bounds[i]) & (eq.index <= bounds[i + 1])]
        seg = seg / seg.iloc[0]
        segs.append(float(seg.iloc[-1] - 1) * 100)
        eq_parts.append(seg * cum)
        cum *= float(seg.iloc[-1])
    wf_eq = pd.concat(eq_parts)
    oos_days = (bounds[-1] - bounds[0]).days / 365.25 * 252
    total = float(wf_eq.iloc[-1] / 1.0)
    ann_wf = (cum ** (252.0 / oos_days) - 1) * 100
    dd_wf = float((wf_eq / wf_eq.cummax() - 1).min()) * 100

    h5_oos = h5[h5.index >= pd.Timestamp(OOS_START)]
    h5_oos = h5_oos / h5_oos.iloc[0]
    ann_h5 = float(h5_oos.iloc[-1] ** (252.0 / len(h5_oos)) - 1) * 100
    dd_h5 = float((h5_oos / h5_oos.cummax() - 1).min()) * 100

    eq_fix = m5_eq(px, b200, 43.3, 56.7)
    ann_f, dd_f = seg_metrics(eq_fix, OOS_START, "2026-08-18")

    w1 = ann_wf >= ann_h5 + W1_GAP
    w2 = dd_wf >= dd_h5 + W2_DD
    w3 = ann_wf >= W3_MIN
    out = {
        "picks": {s: f"{lo}/{hi}" for s, (lo, hi) in picks.items()},
        "oos": {"ann_pct": round(ann_wf, 2), "maxdd_pct": round(dd_wf, 2),
                "seg_rets_pct": [round(s, 1) for s in segs]},
        "H5_oos": {"ann_pct": round(ann_h5, 2), "maxdd_pct": round(dd_h5, 2)},
        "frozen_ref": {"ann_pct": round(ann_f, 2), "maxdd_pct": round(dd_f, 2)},
        "W1": {"gap": round(ann_wf - ann_h5, 2), "pass": bool(w1)},
        "W2": {"dd_gap": round(dd_wf - dd_h5, 2), "pass": bool(w2)},
        "W3": {"ann": round(ann_wf, 2), "pass": bool(w3)},
        "VERDICT": "PASS" if (w1 and w2 and w3) else "FAIL",
    }
    path = SRC / "portfolio_split/m5_walkforward_results.json"
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
