"""宽度口径一致性检验：CSI300 成分宽度 vs 全 A 宽度（2026-08-28 第十四轮）。

预注册口径（跑前落死）：
- 背景：CSI300 口径史已回填（csi300_ma_breadth_history.json，2011-07→
  2026-08，当前名单回算幸存者声明）；两口径 B200 全史相关仅 0.699，
  关键期分叉（2021 抱团 23% vs 55%；2024-02 5% vs 16%）。
- J-C1（信号流层）：split_full 底座（A 腿闸 50 万 + 个股腿无闸 50 万）
  重跑四臂：无闸 / h80@全A（=F0 基线 223.7 万）/ h80@CSI300 /
  full_v2@CSI300。判定「口径敏感」= CSI300 口径臂在 任一考题劣化：
  阴跌 DD 比 h80@全A 深 >3pp 或 2026DD 深 >3pp 或终值低 >10%；
  否则「口径稳健」。不设「谁优谁转正」——本轮是敏感性检查。
- J-C2（纯宽度层·前段核验）：沪深300 指数（timing 000300），
  窗口 A = 2011-07→2016-08（CSI300 口径可得窗，含 2015 股灾），
  窗口 B = 2016-08→2026-08（后段对照）。五档目标仓位（h80 表，
  CSI300 口径）周频 vs 买入持有。判定「闸结构成立」= 该窗口有闸版
  maxDD 改善 >= 15% 且 CAGR >= BH 的 80%。两窗口分开判。
- 声明：CSI300 宽度=今日 300 成分回算（幸存者向上偏，与 SP500 同）；
  窗口 A 无 2008（数据不可得），核验覆盖 2015 股灾。

输出：raw/breadth_overlay/caliber_check_results.json
复现：python3 scripts/run_caliber_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_final_form_v2 import H80  # noqa: E402
from run_full_stack_sim import (  # noqa: E402
    SEG_HI,
    SEG_LO,
    gate_a,
    load_runs,
    seg_max_dd,
)
from run_symbol_showcase import cagr_dd, sim_bh, sim_width  # noqa: E402
from run_symbol_tilt import merge_curves, sim_weighted  # noqa: E402

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)

RAW = REPO / "docs/experiments/raw/breadth_overlay"
CACHE = Path.home() / ".lei_signal_lab/cache"
W1 = lambda s, d: 1.0  # noqa: E731


def load_csi_breadth() -> pd.DataFrame:
    df = pd.DataFrame(json.loads(
        (CACHE / "csi300_ma_breadth_history.json").read_text()))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def tier_target_map(br: pd.DataFrame, col: str, tiers) -> dict[str, float]:
    """周频 B200 五档 → 目标仓位表（t+1 生效）。"""
    days = br.index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    out: dict[str, float] = {}
    for i in range(len(days)):
        if not is_sig[i] or i + 1 >= len(days):
            continue
        v = br[col].iloc[i]
        if pd.isna(v):
            continue
        tgt = next((w for th, w in tiers if v <= th), tiers[-1][1])
        out[str(days[i + 1].date())] = tgt
    return out


def main() -> None:
    runs = load_runs(rerun=False)
    a_leg = dedup_signals([{**t, "pool": "A_ETF"}
                           for t in gate_a(runs["A"])])[0]
    s_leg = dedup_signals(
        [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
        + [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]])[0]

    full_br = load_breadth()
    csi_br = load_csi_breadth()
    fa_b200 = {str(d.date()): float(v)
               for d, v in full_br["ma200_pct"].items()}
    cs_b200 = {str(d.date()): float(v)
               for d, v in csi_br["ma200_pct"].items()
               if not pd.isna(v)}
    caps = {
        "none": None,
        "h80_allA": cap_fn_from_map(position_cap_map(fa_b200, H80)),
        "h80_csi": cap_fn_from_map(position_cap_map(cs_b200, H80)),
        "fullv2_csi": cap_fn_from_map(position_cap_map(cs_b200, TIERS_V2)),
    }
    results = {}
    for name, cap in caps.items():
        a = sim_weighted(a_leg, W1, cap, 500_000)
        s = sim_weighted(s_leg, W1, None, 500_000)
        m = merge_curves(a, s)
        results[name] = {"final": round(m["final"]),
                         "seg_dd": seg_max_dd(m["curve"], SEG_LO, SEG_HI),
                         "dd26": m["by_year"].get("2026")}
    base = results["h80_allA"]
    jc1_sensitive = any(
        r["seg_dd"] - base["seg_dd"] > 3 or
        (r["dd26"] is not None and base["dd26"] is not None
         and r["dd26"] - base["dd26"] > 3) or
        r["final"] < base["final"] * 0.9
        for k, r in results.items() if k.startswith(("h80_csi", "fullv2")))

    # ---- J-C2：纯宽度层两窗口 ----
    idx = pd.read_parquet(CACHE / "timing/000300.parquet")[["open", "close"]]
    idx.index = pd.to_datetime(idx.index).tz_localize(None).normalize()
    smap_csi = tier_target_map(csi_br, "ma200_pct", H80)
    smap_allA = tier_target_map(full_br, "ma200_pct", H80)
    # CSI300 口径 B200 自 2017-02 才可用（当前成分名单 2015 年前上市
    # 不足 200 日的比例过高）——窗口 A 用全 A 口径核验，如实标注。
    windows = {"A_2011_2016_allA": ("2011-07-21", "2016-08-31"),
               "B_2016_2026_csi": ("2016-08-31", "2026-08-18"),
               "B_2016_2026_allA": ("2016-08-31", "2026-08-18")}
    jc2 = {}
    for wname, (lo, hi) in windows.items():
        bars = idx.loc[lo:hi]
        if len(bars) < 250:
            continue
        smap = smap_allA if wname.endswith("allA") else smap_csi
        w_eq = sim_width(bars, smap)
        bh_eq = sim_bh(bars)
        w_m, b_m = cagr_dd(w_eq), cagr_dd(bh_eq)
        dd_impr = (abs(b_m["max_dd"]) - abs(w_m["max_dd"])) \
                    / abs(b_m["max_dd"]) * 100
        jc2[wname] = {"gate": w_m, "bh": b_m,
                      "dd_improve_pct": round(dd_impr, 1),
                      "cagr_keep": round(w_m["cagr"] / b_m["cagr"], 3)
                      if b_m["cagr"] > 0 else None,
                      "pass": bool(dd_impr >= 15 and w_m["cagr"]
                                   >= 0.8 * b_m["cagr"])}
    out = {"date": "2026-08-28", "JC1_arms": results,
           "JC1_sensitive": bool(jc1_sensitive),
           "JC1_verdict": "口径敏感（档位复核）" if jc1_sensitive
                          else "口径稳健",
           "JC2_windows": jc2}
    (RAW / "caliber_check_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
