#!/usr/bin/env python3
"""利率档位闸 vs 宽度闸 vs「宽底率顶」混合闸（2026-08-28 第十九轮）。

动机（第十八轮面板）：中债 10Y 是最强反向指标（高利率区 12m −8.9%
vs 低利率 +21.6%）；宽度 B200 长窗哑铃（高宽度后牛市延续长——
过热档收费的宏观根源）。假设：宽度管底部（低宽=放）、利率管顶部
（高利率=压）可能互补。

预注册口径（跑前落死）：
- 窗口 = 2015-01→2026-08（中债 10Y 数据约束），基准 = 沪深300。
- 指标 = 中债 10Y **5 年滚动分位**（防前视——面板的全样本分位仅
  描述性）；全 A B200（研究史）。
- 臂（周频判定 t+1 开盘、5bp、目标仓位）：
    BH   买入持有
    R1   利率档：滚动分位 >=85 → 0.5 / <=15 → 1.0 / 中间 0.8
    W1   宽度五档 h80（同窗）
    M1   宽底率顶：B200<=20 → 1.0；利率分位>=85 → 0.5；否则 0.8
         （假设驱动组合：底部交给宽度、顶部交给利率）
    M2   min(W1 档, R1 档)（朴素混合对照）
- 判定（事前）：
    R1 胜出 = DD 改善 >=15%（vs BH）且 CAGR >= 0.8×BH；
    M1 胜出 = CAGR >= W1 的 CAGR 且 maxDD <= 0.9×W1 的 maxDD
    （对宽度闸的帕累托要求——混合必须明显更好才有存在价值）；
    M2 同 M1 判。
- 声明：滚动分位前 5 年为 NaN（降级用可用段全历史分位，声明）；
  窗口 11.6 年覆盖 2015 股灾/2016-18/2019-20 牛/2021-24 阴跌/2025-26。
  指数层结论，不自动外推到信号流层。

输出：raw/sentiment/rate_gate_results.json
复现：python3 scripts/run_rate_gate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_caliber_check import tier_target_map  # noqa: E402
from run_final_form_v2 import H80  # noqa: E402
from run_symbol_showcase import cagr_dd, sim_bh, sim_width  # noqa: E402

RAW = REPO / "docs/experiments/raw/sentiment"
CACHE = Path.home() / ".lei_signal_lab/cache"


def roll_pct(s: pd.Series, win: int = 1260, minp: int = 500) -> pd.Series:
    return s.rolling(win, min_periods=minp).rank(pct=True)


def weekly_target(sig: pd.Series, rule) -> dict[str, float]:
    days = sig.index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    out: dict[str, float] = {}
    for i in range(len(days)):
        if not is_sig[i] or i + 1 >= len(days):
            continue
        v = sig.iloc[i]
        if pd.isna(v):
            continue
        out[str(days[i + 1].date())] = rule(v)
    return out


def main() -> int:
    b = pd.read_csv(RAW / "cn_bond_yield.csv",
                    parse_dates=["日期"]).set_index("日期").sort_index()
    cn10 = b["中国国债收益率10年"].dropna()
    rate_pct = roll_pct(cn10)

    br = load_breadth()
    idx = pd.read_parquet(CACHE / "timing/000300.parquet")[["open", "close"]]
    idx.index = pd.to_datetime(idx.index).tz_localize(None).normalize()
    bars = idx.loc[cn10.index[0]:]

    w_map = tier_target_map(br, "ma200_pct", H80)
    r_map = weekly_target(rate_pct, lambda v: 0.5 if v >= 0.85
                          else (1.0 if v <= 0.15 else 0.8))
    # M1「宽底率顶」逐周合成（B200 与利率滚动分位联合判定）：
    m1_map = {}
    rk = rate_pct.reindex(br.index).ffill()
    bk = br["ma200_pct"]
    days = bk.index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    for i in range(len(days)):
        if not is_sig[i] or i + 1 >= len(days):
            continue
        bv, rv = bk.iloc[i], rk.iloc[i]
        if pd.isna(bv):
            continue
        t = 1.0 if bv <= 20 else (0.5 if (pd.notna(rv) and rv >= 0.85)
                                  else 0.8)
        m1_map[str(days[i + 1].date())] = t
    m2_map = {}
    for k in set(w_map) | set(r_map):
        m2_map[k] = min(w_map.get(k, 1.0), r_map.get(k, 1.0))

    arms = {"BH": cagr_dd(sim_bh(bars)),
            "R1_rate": cagr_dd(sim_width(bars, r_map)),
            "W1_breadth": cagr_dd(sim_width(bars, w_map)),
            "M1_width_bottom_rate_top": cagr_dd(sim_width(bars, m1_map)),
            "M2_min": cagr_dd(sim_width(bars, m2_map))}
    bh, w1 = arms["BH"], arms["W1_breadth"]
    r1_pass = bool(
        (abs(bh["max_dd"]) - abs(arms["R1_rate"]["max_dd"]))
        / abs(bh["max_dd"]) >= 0.15
        and arms["R1_rate"]["cagr"] >= 0.8 * bh["cagr"])

    def pareto(a):
        return bool(a["cagr"] >= w1["cagr"]
                    and abs(a["max_dd"]) <= 0.9 * abs(w1["max_dd"]))

    out = {"date": "2026-08-28",
           "window": [str(bars.index[0].date()), str(bars.index[-1].date())],
           "arms": arms,
           "verdicts": {
               "R1_pass": r1_pass,
               "M1_pareto_vs_W1": pareto(arms["M1_width_bottom_rate_top"]),
               "M2_pareto_vs_W1": pareto(arms["M2_min"]),
               "rules": "R1: DD改善≥15%且CAGR≥0.8×BH；M1/M2: CAGR≥W1 且 DD≤0.9×W1"}}
    (RAW / "rate_gate_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
