# -*- coding: utf-8 -*-
"""任务 AN 独立抽查验证：用与主脚本不同的朴素实现（纯列表、无 pandas 索引技巧）
重算 8 个抽查事件的全部度量，与 raw JSON 逐项对照。0 处不符才通过。"""
import json
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
TIMING = CACHE / "timing"
RAW = Path(__file__).resolve().parents[2] / "docs/experiments/raw/agent_AN/top_structure_events.json"

PATHS = {
    "399006": TIMING / "399006.parquet",
    "000300": TIMING / "000300.parquet",
    "512100": TIMING / "512100.parquet",
    "000688.SH": CACHE / "000688.SS.bars.parquet",
    "512480": TIMING / "512480.parquet",
}

SPOT = [
    ("000300", "2024-10-08"), ("399006", "2024-10-08"),
    ("399006", "2015-02-26"), ("000300", "2006-03-01"),
    ("000688.SH", "2020-07-09"), ("512480", "2025-03-17"),
    ("512100", "2019-03-07"), ("399006", "2014-08-06"),
]


def naive_measure(sym, event_date):
    s = pd.read_parquet(PATHS[sym])["close"].dropna()
    dates = [d.date() for d in s.index]
    vals = [float(v) for v in s.values]
    # 去重保最后 + 排序（朴素重放主脚本预处理）
    seen = {}
    for d, v in zip(s.index, vals):
        seen[d] = v
    keys = sorted(seen)
    dates = [k.date() for k in keys]
    vals = [seen[k] for k in keys]
    # 公司行为前复权（朴素：隔夜比 >1.5 或 <1/1.5）
    adj = list(vals)
    for i in range(1, len(adj)):
        r = vals[i] / vals[i - 1]
        if r > 1.5 or r < 1 / 1.5:
            for j in range(i):
                adj[j] = vals[j] * r
    import datetime as dt
    ed = dt.date.fromisoformat(event_date)
    # 对齐：首个 >= 事件日的交易日（<=7 自然日）
    i = next(k for k, d in enumerate(dates) if d >= ed)
    assert (dates[i] - ed).days <= 7
    c0 = adj[i]
    n = len(adj)
    out = {"n_fwd": n - 1 - i}
    for key, lvl in (("t5", .95), ("t10", .90), ("t20", .80)):
        t = None
        for k in range(1, min(250, n - 1 - i) + 1):
            if adj[i + k] <= c0 * lvl:
                t = k
                break
        out[key] = t
    t = None
    for k in range(1, min(250, n - 1 - i) + 1):
        if adj[i + k] < c0:
            t = k
            break
    out["t_below"] = t
    for w in (20, 60, 120, 250):
        out[f"r{w}"] = round((adj[i + w] / c0 - 1) * 100, 2) if i + w < n else None
    out["dd60_pct"] = round((min(adj[i + 1:i + 61]) / c0 - 1) * 100, 2) if i + 61 <= n and i + 1 < n else None
    seg = adj[i:i + 121]
    out["upside120_pct"] = round((max(seg) / c0 - 1) * 100, 2)
    out["t_peak120"] = seg.index(max(seg))
    out["new_high120"] = max(seg[1:]) > c0
    return out


def main():
    data = json.loads(RAW.read_text())
    idx = {(e["symbol"], e["event_date"]): e for e in data["main_85"]["events"]}
    n_bad = 0
    for sym, evd in SPOT:
        ref = idx[(sym, evd)]
        got = naive_measure(sym, evd)
        for k, v in got.items():
            r = ref[k]
            ok = (r == v) or (isinstance(v, float) and abs((r or 0) - v) < 1e-9)
            if not ok:
                n_bad += 1
                print(f"MISMATCH {sym} {evd} {k}: json={r} naive={v}")
        print(f"checked {sym} {evd}: type={ref['type']} censored={ref['censored']} OK")
    print("total mismatches:", n_bad)
    return 1 if n_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
