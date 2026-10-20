# -*- coding: utf-8 -*-
"""AE 报告辅助：从 staged_entry_results.json 提取报告所需明细（只读，不判定）。"""
import json
import sys
from pathlib import Path

import numpy as np

RAW = Path(__file__).resolve().parents[2] / "docs/experiments/raw/agent-AE-staged-entry"
out = json.loads((RAW / "staged_entry_results.json").read_text())
res = out["results"]
events_main = [e for e in out["events_raw"] if e["cluster_main"]]

LADDER_MODES = [f"ladder_{n}x{g}" for n in (3, 4, 5) for g in (5, 10, 20)]
DCA_MODES = ["dca_daily60", "dca_weekly52"]

print("=== 每档位明细（主口径 30 事件） ===")
print(f"{'mode':<16} {'term率':>6} {'配对':>4} {'ret120改善中位':>12} {'正占比':>7} "
      f"{'ret60改善中位':>12} {'dd改善中位':>10} {'ret180改善中位':>12} {'成本差中位':>10} {'费用bp':>7} {'换手':>6}")
for m in ["baseline"] + LADDER_MODES + DCA_MODES:
    term = sum(1 for e in events_main if res[e["exec_date"]][m]["terminated"])
    fees = [res[e["exec_date"]][m]["fee_paid"] * 1e4 for e in events_main]
    tos = [res[e["exec_date"]][m]["turnover"] for e in events_main]
    if m == "baseline":
        print(f"{m:<16} {'-':>6} {'-':>4} {'-':>12} {'-':>7} {'-':>12} {'-':>10} {'-':>12} {'-':>10} "
              f"{np.median(fees):7.0f} {np.median(tos):6.2f}")
        continue
    imp120, imp60, impdd, imp180, cg = [], [], [], [], []
    for e in events_main:
        b = res[e["exec_date"]]["baseline"]
        s = res[e["exec_date"]][m]
        for lst, bk, sk in ((imp120, "ret_120", "ret_120"), (imp60, "ret_60", "ret_60"),
                            (impdd, "dd_build", "dd_build"), (imp180, "ret_aligned_180", "ret_aligned_180")):
            bv, sv = b[bk], s[sk]
            if bv is not None and sv is not None:
                if bk == "dd_build":
                    lst.append(bv - sv)
                else:
                    lst.append(sv - bv)
        if s["cost_gap"] is not None:
            cg.append(s["cost_gap"])
    print(f"{m:<16} {term/len(events_main):6.2f} {len(imp120):4d} "
          f"{np.median(imp120)*100 if imp120 else float('nan'):12.3f} "
          f"{np.mean(np.array(imp120)>0) if imp120 else float('nan'):7.3f} "
          f"{np.median(imp60)*100 if imp60 else float('nan'):12.3f} "
          f"{np.median(impdd)*100 if impdd else float('nan'):10.3f} "
          f"{np.median(imp180)*100 if imp180 else float('nan'):12.3f} "
          f"{np.median(cg)*100 if cg else float('nan'):10.3f} "
          f"{np.median(fees):7.0f} {np.median(tos):6.2f}")

print()
print("=== 分组明细（阶梯中位档 4x10 与定投两档） ===")
for grp_name, flag in (("极端底部组(9)", True), ("普通加仓组(21)", False)):
    evs = [e for e in events_main if e["extreme_bottom"] == flag]
    print(f"--- {grp_name} ---")
    for m in ["ladder_4x10", "dca_daily60", "dca_weekly52"]:
        term = sum(1 for e in evs if res[e["exec_date"]][m]["terminated"])
        imp120, impdd, imp180 = [], [], []
        for e in evs:
            b = res[e["exec_date"]]["baseline"]
            s = res[e["exec_date"]][m]
            if b["ret_120"] is not None and s["ret_120"] is not None:
                imp120.append(s["ret_120"] - b["ret_120"])
            if b["dd_build"] is not None and s["dd_build"] is not None:
                impdd.append(b["dd_build"] - s["dd_build"])
            if b["ret_aligned_180"] is not None and s["ret_aligned_180"] is not None:
                imp180.append(s["ret_aligned_180"] - b["ret_aligned_180"])
        print(f"  {m:<14} 作废率 {term/len(evs):.2f} | ret120配对 {len(imp120)} 改善中位 "
              f"{np.median(imp120)*100 if imp120 else float('nan'):+.2f}pp 正占比 "
              f"{np.mean(np.array(imp120)>0) if imp120 else float('nan'):.2f} | dd改善中位 "
              f"{np.median(impdd)*100 if impdd else float('nan'):+.2f}pp | ret180改善中位 "
              f"{np.median(imp180)*100 if imp180 else float('nan'):+.2f}pp")

print()
print("=== 基准自身 ===")
b120 = [res[e["exec_date"]]["baseline"]["ret_120"] for e in events_main if res[e["exec_date"]]["baseline"]["ret_120"] is not None]
b180 = [res[e["exec_date"]]["baseline"]["ret_aligned_180"] for e in events_main if res[e["exec_date"]]["baseline"]["ret_aligned_180"] is not None]
b180e = [res[e["exec_date"]]["baseline"]["ret_aligned_180"] for e in events_main if e["extreme_bottom"] and res[e["exec_date"]]["baseline"]["ret_aligned_180"] is not None]
b180n = [res[e["exec_date"]]["baseline"]["ret_aligned_180"] for e in events_main if not e["extreme_bottom"] and res[e["exec_date"]]["baseline"]["ret_aligned_180"] is not None]
print(f"基准 ret_120: n={len(b120)} 中位 {np.median(b120)*100:+.2f}% 均值 {np.mean(b120)*100:+.2f}%")
print(f"基准 ret_180(对齐): n={len(b180)} 中位 {np.median(b180)*100:+.2f}% | 极端组 {np.median(b180e)*100:+.2f}% | 普通组 {np.median(b180n)*100:+.2f}%")

print()
print("=== 机械不中断版逐档（sens） ===")
for m in ["ladder_4x10", "dca_daily60", "dca_weekly52"]:
    mk = m + "|mech"
    imp120, impdd, imp180 = [], [], []
    term = 0
    for e in events_main:
        b = res[e["exec_date"]]["baseline"]
        s = res[e["exec_date"]][mk]
        if b["ret_120"] is not None and s["ret_120"] is not None:
            imp120.append(s["ret_120"] - b["ret_120"])
        if b["dd_build"] is not None and s["dd_build"] is not None:
            impdd.append(b["dd_build"] - s["dd_build"])
        if b["ret_aligned_180"] is not None and s["ret_aligned_180"] is not None:
            imp180.append(s["ret_aligned_180"] - b["ret_aligned_180"])
    print(f"  {m:<14} ret120配对 {len(imp120)} 改善中位 {np.median(imp120)*100:+.2f}pp 正占比 "
          f"{np.mean(np.array(imp120)>0):.2f} | dd改善中位 {np.median(impdd)*100:+.2f}pp | ret180改善中位 {np.median(imp180)*100:+.2f}pp 正占比 {np.mean(np.array(imp180)>0):.2f}")

print()
print("=== 事件清单（主口径 30） ===")
for e in events_main:
    print(f"{e['exec_date']} prev={e['prev_w']:.1f} b200={e['b200_at_signal']:6.2f} "
          f"min120={e['b200_min120']:6.2f} {'EXTREME' if e['extreme_bottom'] else 'normal '}")
