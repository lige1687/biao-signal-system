# -*- coding: utf-8 -*-
"""agent_AM 独立数值验证：不复用主脚本的账户路径/回撤函数，用朴素 pandas 循环
对抽查事件重算全部度量，与主脚本 JSON 输出逐项对照。仅验证，不产出结论。
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
TIMING = CACHE / "timing"
ROOT = Path(__file__).resolve().parents[2]
MAIN = json.loads(
    (ROOT / "docs/experiments/raw/agent_AM/extreme_bottom_staged_entry.json").read_text())
FEE = 0.001
MONTH_TD = 21
HOLD = 250

INST = {
    "399006": TIMING / "399006.parquet",
    "000300": TIMING / "000300.parquet",
    "512100": TIMING / "512100.parquet",
    "000688.SH": CACHE / "000688.SS.bars.parquet",
    "512480": TIMING / "512480.parquet",
}


def adjust(close):
    ret = close / close.shift(1)
    adj = close.copy()
    for idx in ret.index[(ret > 1.5) | (ret < 1 / 1.5)]:
        pos = close.index.get_loc(idx)
        adj.iloc[:pos] = adj.iloc[:pos] * float(close.iloc[pos] / close.iloc[pos - 1])
    return adj


def naive_max_dd(path_vals):
    worst = 0.0
    peak = -1e18
    for v in path_vals:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst * 100.0


CHECKS = [
    ("000300", "2008-03-18", 12),   # 单边深跌型
    ("000300", "2008-03-18", 3),
    ("399006", "2016-01-07", 12),   # 过程型深探
    ("399006", "2024-08-22", 6),    # 快速大涨型
    ("512480", "2024-08-22", 12),   # 半导体大涨型 + 对齐口径
    ("512100", "2018-06-15", 6),    # ETF 含拆分修正的事件
]

ev_map = {(e["symbol"], e["event_date"]): e for e in MAIN["events"]}
fails = 0
for sym, d, m in CHECKS:
    raw = pd.read_parquet(INST[sym])["close"].dropna()
    raw = raw[~raw.index.duplicated(keep="last")].sort_index()
    px = adjust(raw)
    i0 = px.index.searchsorted(pd.Timestamp(d))
    p0 = float(px.iloc[i0])
    ev = ev_map[(sym, d)]
    tier = {3: "3m", 6: "6m", 12: "12m"}[m]

    # ---- 主口径：独立重算 ----
    idxs = [i0 + MONTH_TD * k for k in range(m)]
    assert idxs[-1] < len(px)
    units_st = sum((1.0 / m) * (1 - FEE) / float(px.iloc[i]) for i in idxs)
    units_lu = (1 - FEE) / p0
    # lump 度量：窗口 [i0, i0+250]，收益在 i0+250
    dd_lu = naive_max_dd([(1 - FEE) * float(px.iloc[i]) / p0
                          for i in range(i0, i0 + HOLD + 1)])
    ret_lu = (units_lu * float(px.iloc[i0 + HOLD]) - 1) * 100
    # staged 度量：窗口 [i0, b_end+250]，收益在 b_end+250；朴素逐日现金+市值
    vals = []
    for i in range(i0, idxs[-1] + HOLD + 1):
        spent = sum(1.0 / m for j in idxs if j <= i)
        u = sum((1.0 / m) * (1 - FEE) / float(px.iloc[j]) for j in idxs if j <= i)
        vals.append(1.0 - spent + u * float(px.iloc[i]))
    dd_st = naive_max_dd(vals)
    ret_st = (units_st * float(px.iloc[idxs[-1] + HOLD]) - 1) * 100
    harm = m / sum(1.0 / float(px.iloc[i]) for i in idxs)
    cost_diff = (harm / p0 - 1) * 100

    got = ev["tiers"][tier]
    mine = {
        "ret250_pct": ret_st, "dd_pct": dd_st, "cost_diff_pp": cost_diff,
    }
    lu_got = ev["lump"]
    lu_mine = {"ret250_pct": ret_lu, "dd_pct": dd_lu}
    for k, v in mine.items():
        if abs(got[k] - v) > 0.02:
            print(f"MISMATCH {sym} {d} {tier} staged.{k}: main={got[k]} mine={v:.2f}")
            fails += 1
    for k, v in lu_mine.items():
        if abs(lu_got[k] - v) > 0.02:
            print(f"MISMATCH {sym} {d} lump.{k}: main={lu_got[k]} mine={v:.2f}")
            fails += 1
    print(f"OK-verified {sym} {d} {tier}: lump(ret={lu_got['ret250_pct']}, dd={lu_got['dd_pct']}) "
          f"staged(ret={got['ret250_pct']}, dd={got['dd_pct']}, cost={got['cost_diff_pp']})")

    # ---- 对齐口径：独立重算（仅 512480 那条做全对照） ----
    if sym == "512480":
        al = ev["aligned"][tier]
        i_meas = idxs[-1] + HOLD
        lump_ret_al = (units_lu * float(px.iloc[i_meas]) - 1) * 100
        st_ret_al = (units_st * float(px.iloc[i_meas]) - 1) * 100
        dd_lu_al = naive_max_dd([(1 - FEE) * float(px.iloc[i]) / p0
                                 for i in range(i0, i_meas + 1)])
        if (abs(al["lump_ret"] - lump_ret_al) > 0.02
                or abs(al["staged_ret"] - st_ret_al) > 0.02
                or abs(al["lump_dd"] - dd_lu_al) > 0.02
                or abs(al["staged_dd"] - dd_st) > 0.02):
            print(f"MISMATCH aligned {sym} {d} {tier}: {al} vs "
                  f"lump_ret={lump_ret_al:.2f} st_ret={st_ret_al:.2f} "
                  f"lump_dd={dd_lu_al:.2f} st_dd={dd_st:.2f}")
            fails += 1
        else:
            print(f"OK-verified aligned {sym} {d} {tier}: {al}")

print("FAILS:", fails)
