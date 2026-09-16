"""第十五轮：双速闸（B200 慢线定档 × B20 快线修正），2026-08-28。

动机（来自第十四轮）：过热档收费三次独立确认（2015 CAGR 代价 0.37、
2021、2025 让掉 117.9R）——B200 慢线分不清「健康牛」与「真过热」。
新信息源：B20 快线（timing-sweep 第四轮曾示防守更快，本体系从未用）。

预注册口径（跑前落死）：
- 底座 = split_full（A 腿闸 50 万 + 个股腿无闸 50 万），基线 G0 =
  h80@全A（champion，223.7 万 / 6.9% / 6.7%）。
- 周频（每周最后宽度日收盘，t+1 生效），ETF 腿 cap 规则：
    G0（基线）：B200 五档 h80。
    G1（过热确认）：B200>80 档时若 B20 >= 70 → cap 0.5→0.7 放宽
        （涨势仍宽=健康牛）；B20 < 70 → 维持 0.25（快线掉队=真过热）。
        其余档位同 h80。
    G2（崩盘刹车）：B20 <= 10 → 在 h80 档位上再 ×0.5；否则原样。
    G3（组合）：G1 ∩ G2。
    G4（对照）：fz_80_0（(20,1)(40,.8)(60,.6)(80,0)(999,0) 停新买，
        第十二轮前沿点重列对照）。
- 判定（事前，J-G）：臂胜出 = 终值 >= G0 × 1.10 且 阴跌段 DD <=
  G0 + 3pp 且 2026DD <= G0 + 3pp。另报告 2025 年段（过热收费年）
  与 2015 段（前段口径核验年，纯指数层 G0/G1 对照，样本外方向检查）
  的分年对比（只报告）。
- 声明：B20 阈值（70/10）为事前指定值（timing-sweep 第四轮 B20 防守
  档与手册极值思想的插值），不做网格搜索——多重比较税控制。

输出：raw/breadth_overlay/dual_speed_gate_results.json
复现：python3 scripts/run_dual_speed_gate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_final_form_v2 import H80  # noqa: E402
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

RAW = REPO / "docs/experiments/raw/breadth_overlay"
W1 = lambda s, d: 1.0  # noqa: E731
FZ80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.0), (999, 0.0))


def load_breadth3() -> pd.DataFrame:
    """三线宽度（ma20/50/200）——研究史 full 文件。"""
    full = Path.home() / ".lei_signal_lab/cache/a_share_ma_breadth_full_history.json"
    df = pd.DataFrame(json.loads(full.read_text()))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def composite_map(br: pd.DataFrame, arm: str) -> dict[str, float]:
    days = br.index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    out: dict[str, float] = {}
    for i in range(len(days)):
        if not is_sig[i] or i + 1 >= len(days):
            continue
        b200, b20 = br["ma200_pct"].iloc[i], br["ma20_pct"].iloc[i]
        if pd.isna(b200):
            continue
        cap = next((w for th, w in H80 if b200 <= th), H80[-1][1])
        if arm == "G1" and b200 > 80 and b20 >= 70:
            cap = 0.7
        elif arm == "G2" and b20 <= 10:
            cap = cap * 0.5
        elif arm == "G3":
            if b200 > 80 and b20 >= 70:
                cap = 0.7
            if b20 <= 10:
                cap = cap * 0.5
        out[str(days[i + 1].date())] = round(cap, 4)
    return out


def main() -> None:
    runs = load_runs(rerun=False)
    a_leg = dedup_signals([{**t, "pool": "A_ETF"}
                           for t in gate_a(runs["A"])])[0]
    s_leg = dedup_signals(
        [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
        + [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]])[0]
    br = load_breadth3()
    b200 = {str(d.date()): float(v)
            for d, v in br["ma200_pct"].items() if not pd.isna(v)}

    stock_leg = sim_weighted(s_leg, W1, None, 500_000)
    arms = {"G0": cap_fn_from_map(position_cap_map(b200, H80)),
            "G1": cap_fn_from_map(composite_map(br, "G1")),
            "G2": cap_fn_from_map(composite_map(br, "G2")),
            "G3": cap_fn_from_map(composite_map(br, "G3")),
            "G4": cap_fn_from_map(position_cap_map(b200, FZ80))}
    results, verdicts = {}, {}
    g0 = None
    for name, cap in arms.items():
        a = sim_weighted(a_leg, W1, cap, 500_000)
        m = merge_curves(a, stock_leg)
        results[name] = {"final": round(m["final"]),
                         "seg_dd": seg_max_dd(m["curve"], SEG_LO, SEG_HI),
                         "dd26": m["by_year"].get("2026"),
                         "dd25": m["by_year"].get("2025"),
                         "ret25": None}
        if name == "G0":
            g0 = results[name]
    for name in arms:
        if name == "G0":
            continue
        r = results[name]
        verdicts[name] = {"JG": bool(
            r["final"] >= 1.10 * g0["final"]
            and r["seg_dd"] <= g0["seg_dd"] + 3
            and r["dd26"] is not None and r["dd26"] <= g0["dd26"] + 3)}
    out = {"date": "2026-08-28", "arms": results, "verdicts": verdicts,
           "g0_baseline": g0}
    (RAW / "dual_speed_gate_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
