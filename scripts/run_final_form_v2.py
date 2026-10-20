"""第十二轮：完整形态 v2（指数腿补全 + 温和背离压仓），2026-08-27。

目标（用户口径）：更多标的 / 更好收益 / 更低回撤，出一个总结果。

预注册口径（跑前落死）：
- 底座 = split_full（A 腿 h_80 闸 50 万 + B'+C+D 无闸 50 万，分账）。
- 新增部件：
  (a) 指数腿补全：宽基指数 ETF 上的 B' 信号（第 10 轮 Bp_cn_indices
      缓存，6 只宽基 41 笔净 +12.7R）并入 A 腿（同受 h_80 闸）；
  (b) 温和背离压仓：背离路牌（基准 120 日新高 & B200 20 日降 >=5pp，
      周频 t+1）生效日 ETF 腿乘数取 min(h_80, 0.6)——第 4 轮 0.3 版
      饿死收益（155 万），本轮 0.6 温和版只求压 2026 型背离。
- 臂：
    F0 = split_full 复现（自检目标 ~223.7 万）
    F1 = F0 + 指数腿补全
    F2 = F1 + 温和背离压仓
    F3 = F0 + 温和背离压仓（隔离背离贡献）
- 判定（事前）：F2 胜出 = 终值 >= F0 × 1.05 且 阴跌段 DD <= 12% 且
  2026DD <= 10%。F1/F3 各自相对 F0 的增量单独报告。
- 声明：指数 B' 参数为个股标定值跨口径移植（第 10 轮已声明）；F2 若
  胜出仍为建议级，walk-forward 终审前不转正。

输出：raw/breadth_overlay/final_form_v2_results.json
复现：python3 scripts/run_final_form_v2.py（约 2 分钟）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import divergence_map, load_breadth  # noqa: E402
from run_full_stack_sim import (  # noqa: E402
    SEG_HI,
    SEG_LO,
    gate_a,
    load_runs,
    seg_max_dd,
)
from run_symbol_tilt import merge_curves, sim_weighted  # noqa: E402

from lei_signal.backtest.full_sim import (  # noqa: E402
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
H80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))


def main() -> None:
    runs = load_runs(rerun=False)
    br = load_breadth()
    frames = load_pool_frames()
    b200 = {str(d.date()): float(v) for d, v in br["ma200_pct"].items()}
    cap_h80 = cap_fn_from_map(position_cap_map(b200, H80))
    dv06 = cap_fn_from_map(divergence_map(br, frames.get("000300.SS"),
                                          press=0.6))
    cap_dv = lambda day: min(cap_h80(day), dv06(day))  # noqa: E731

    idx_bp = json.loads((RAW / "Bp_cn_indices.json").read_text())
    idx_trades = [{**t, "module": "B'", "pool": "A_ETF"}
                  for t in idx_bp["trades"] if t["exit_date"] is not None]

    a_leg0 = dedup_signals(
        [{**t, "pool": "A_ETF"} for t in gate_a(runs["A"])])[0]
    a_leg1 = dedup_signals(
        [{**t, "pool": "A_ETF"} for t in gate_a(runs["A"])] + idx_trades)[0]
    s_leg = dedup_signals(
        [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
        + [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]])[0]
    print(f"[腿规模] A0={len(a_leg0)} A1(含指数B')={len(a_leg1)} "
          f"个股腿={len(s_leg)}")

    w1 = lambda s, d: 1.0  # noqa: E731
    arms = {
        "F0": (a_leg0, cap_h80),
        "F1": (a_leg1, cap_h80),
        "F2": (a_leg1, cap_dv),
        "F3": (a_leg0, cap_dv),
    }
    results, verdicts = {}, {}
    for name, (leg, cap) in arms.items():
        a = sim_weighted(leg, w1, cap, 500_000)
        s = sim_weighted(s_leg, w1, None, 500_000)
        m = merge_curves(a, s)
        results[name] = {"final": round(m["final"]),
                         "seg_dd": seg_max_dd(m["curve"], SEG_LO, SEG_HI),
                         "dd26": m["by_year"].get("2026"),
                         "n_a_leg": len(leg)}
    f0, f2 = results["F0"], results["F2"]
    verdicts["F2"] = {
        "JT2": bool(f2["final"] >= 1.05 * f0["final"]
                    and f2["seg_dd"] <= 12.0
                    and f2["dd26"] is not None and f2["dd26"] <= 10.0)}
    out = {"date": "2026-08-27", "arms": results, "verdicts": verdicts,
           "f0_sanity_target": 2237072}
    (RAW / "final_form_v2_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
