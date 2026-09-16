# -*- coding: utf-8 -*-
"""agent_AM 事后补充（未预注册、不参与判定，仅用于与 AE 报告对照的解释性分解）：

主口径回撤是"建仓期+持有首年"全程；AE 测过"仅建仓期"回撤并发现分批改善
（极端组 +6pp）。本脚本补算仅建仓期 [t0, build_end] 的回撤改善中位数，
说明"建仓期的好处为什么在全程口径下消失"。输出写入 raw/agent_AM/。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
TIMING = CACHE / "timing"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/experiments/raw/agent_AM/build_period_dd_posthoc.json"
AK = json.loads(
    (ROOT / "docs/experiments/raw/agent_AK/extreme_bottom_events.json").read_text())
FEE, MONTH_TD = 0.001, 21
TIERS = {"3m": 3, "6m": 6, "12m": 12}
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


def naive_dd(vals):
    peak, worst = -1e18, 0.0
    for v in vals:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst * 100.0


def med(xs):
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    m = len(s) // 2
    return round(s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2, 2)


out = {"note": "post-hoc, 不参与判定", "tiers": {}}
for tier, m in TIERS.items():
    diffs, lu_list, st_list = [], [], []
    for sym, path in INST.items():
        raw = pd.read_parquet(path)["close"].dropna()
        raw = raw[~raw.index.duplicated(keep="last")].sort_index()
        px = adjust(raw)
        for d in AK["clusters"]:
            i0 = px.index.searchsorted(pd.Timestamp(d))
            if i0 >= len(px) or (px.index[i0] - pd.Timestamp(d)).days > 7:
                continue
            idxs = [i0 + MONTH_TD * k for k in range(m)]
            if idxs[-1] >= len(px):
                continue
            p0 = float(px.iloc[i0])
            lump_dd = naive_dd([(1 - FEE) * float(px.iloc[i]) / p0
                                for i in range(i0, idxs[-1] + 1)])
            vals = []
            for i in range(i0, idxs[-1] + 1):
                spent = sum(1.0 / m for j in idxs if j <= i)
                u = sum((1.0 / m) * (1 - FEE) / float(px.iloc[j]) for j in idxs if j <= i)
                vals.append(1.0 - spent + u * float(px.iloc[i]))
            st_dd = naive_dd(vals)
            lu_list.append(lump_dd)
            st_list.append(st_dd)
            diffs.append(round(st_dd - lump_dd, 2))  # 正 = 分批更浅
    out["tiers"][tier] = {
        "n": len(diffs),
        "lump_dd_build_med": med(lu_list),
        "staged_dd_build_med": med(st_list),
        "dd_impr_build_med": med(diffs),
        "staged_shallower_share": round(sum(1 for x in diffs if x > 0) / len(diffs), 3),
    }
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
print(json.dumps(out, ensure_ascii=False, indent=1))
