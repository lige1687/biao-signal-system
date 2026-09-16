"""语义七前置验证（agent AD）——报告用补充描述统计（不参与判定）。

从 results.json 与已落盘数据中提取报告正文需要、但未进入判定逻辑的数字：
  - ΔB50 无条件日波动（std）与均值，用于衡量桶间差的相对大小
  - up/down 桶次日宽度扩张/收缩的"方向命中率"（大白话用）
  - ^IXIC 全期与滚动窗口 Q1 摘要
  - 年度窗 p 值表
确定性：只读排序数组与确定性函数，双跑哈希一致。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = REPO / "docs/experiments/raw/overnight-us-cn-2026-09-03"

UP_EDGE, DOWN_EDGE = 1.0, -1.0


def bucketize(r: float) -> str:
    if r >= UP_EDGE:
        return "up"
    if r <= DOWN_EDGE:
        return "down"
    return "flat"


def main() -> None:
    res = json.loads((RAW / "results.json").read_text())

    # 重建观察表（与 run_precheck 同逻辑，只用于描述统计）
    import sys
    sys.path.insert(0, str(REPO / "scripts/agent_AD"))
    from run_precheck import align, load_inputs

    data = load_inputs()
    obs, _ = align(data["gspc"], data["breadth"], data["csi300"])
    db = obs["dB50"]
    print(f"ΔB50 无条件: mean={db.mean():.4f}pp std={db.std(ddof=1):.4f}pp n={len(db)}")
    bk = obs["r_us"].apply(bucketize)
    up_db = obs.loc[bk == "up", "dB50"]
    down_db = obs.loc[bk == "down", "dB50"]
    flat_db = obs.loc[bk == "flat", "dB50"]
    print(f"方向命中率: up桶次日宽度扩张比例={float((up_db > 0).mean()) * 100:.1f}%  "
          f"down桶次日宽度收缩比例={float((down_db < 0).mean()) * 100:.1f}%  "
          f"flat桶扩张比例={float((flat_db > 0).mean()) * 100:.1f}%")

    qi = res["q1_ixic_full"]
    print(f"^IXIC Q1: up={qi['mean']['up']:.4f} flat={qi['mean']['flat']:.4f} "
          f"down={qi['mean']['down']:.4f} diff={qi['diff_up_down']:.4f} "
          f"p={qi['welch']['up_vs_down']['p']:.5f} n={qi['n']}")
    q2i = res["q2_fwd10_ixic_full"]
    print(f"^IXIC Q2: up={q2i['mean']['up']:.3f}% flat={q2i['mean']['flat']:.3f}% "
          f"down={q2i['mean']['down']:.3f}%")
    q2g_nono = res["q2_fwd10_gspc_nonoverlap"]
    print(f"Q2 gspc 非重叠子样均值: {q2g_nono['mean']} n={q2g_nono['n_sub']}")

    print("年度窗 (gspc Q1): name, diff_pp, p, n")
    for name, w in res["q1_gspc_year_windows"].items():
        d = w["diff_up_down"]
        p = w["welch"]["up_vs_down"]["p"]
        n = sum(w["n"].values())
        print(f"  {name}: {d:.4f}, {p:.4f}, {n}")

    print("主窗口 ^GSPC Q1 全指标:")
    for name, w in res["q1_gspc_windows"].items():
        print(f"  {name}: means={ {k: round(v, 4) for k, v in w['mean'].items()} } "
              f"p_updown={w['welch']['up_vs_down']['p']:.5f}")

    med = res["q1_gspc_full"]["median"]
    print(f"Q1 gspc 桶中位数: {med}")


if __name__ == "__main__":
    main()
