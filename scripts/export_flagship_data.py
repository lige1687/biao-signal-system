#!/usr/bin/env python3
"""导出旗舰组合数据到前端（web/src/data/flagshipCombos.ts）。

供 /research 页 FlagshipSection 组件使用：每周降采样（保留档位变化周），
输出日期/组合净值/持有净值/仓位%/买卖点事件。复现 PYTHONHASHSEED=0。
"""
from __future__ import annotations

import sys
from pathlib import Path

import json
import pandas as pd


def json_dump(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_ashare_axes import siphon_daily  # noqa: E402
from run_bform_dynamic import simulate_direct  # noqa: E402
from run_bform_mini import load_series  # noqa: E402
from run_m5_walkforward import tier_for  # noqa: E402

E = lambda c: f"etf_breadth/{c}_close.parquet"  # noqa: E731
COMBOS = [
    ("两只版", "创业板×三档+虹吸 + 纳指持有（2010-06→，16年全周期）",
     [("创业板指", "siphon_detector/cyb_399006_close.parquet", "A"),
      ("纳斯达克", "portfolio_split/ixic_close.parquet", "H")], "2010-06-01"),
    ("B9+虹吸", "九标的×三档+虹吸（2015-06→，唯一全套认证）",
     [(k, v, "A") for k, v in {**rps.GATED, **rps.TREND}.items()], "2015-06-16"),
    ("ETF可交易版", "新能车+传媒+证券ETF×三档+虹吸 + 纳指ETF（2020-03→）",
     [("新能车ETF", E("sh515030"), "A"), ("传媒ETF", E("sh512980"), "A"),
      ("证券ETF", E("sh512880"), "A"), ("纳指ETF", E("sh513100"), "H")], "2020-03-04"),
]


def main() -> None:
    b200 = rps.load_breadth()
    blocks = []
    meta = []
    for name, desc, legs, start in COMBOS:
        frames = {n: load_series(rel) for n, rel, _ in legs}
        px = pd.DataFrame(frames)
        a_names = [n for n, _, k in legs if k == "A"]
        if any(k == "H" for _, _, k in legs):
            cn = px[a_names[0]].dropna().index
            px = px.reindex(cn).ffill()
        px = px[(px.index >= pd.Timestamp(start)) & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
        n = px.shape[1]
        t0 = tier_for(b200, px.index, 43.3, 56.7)
        sip = siphon_daily(px.index)
        bud = t0.copy()
        bud[(t0 <= 0.001) & sip] = 0.5
        expo = pd.DataFrame(1.0, index=px.index, columns=px.columns)
        for c in a_names:
            expo[c] = bud
        expo = expo / n
        ones = pd.DataFrame(1.0, index=px.index, columns=px.columns) / n
        eq = simulate_direct(px, expo)
        hold = simulate_direct(px, ones)
        pos_pct = (bud * len(a_names) + (n - len(a_names))) / n * 100
        yrs = (eq.index[-1] - eq.index[0]).days / 365.25
        ann = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100
        dd = float((eq / eq.cummax() - 1).min()) * 100
        annh = ((hold.iloc[-1] / hold.iloc[0]) ** (1 / yrs) - 1) * 100
        ddh = float((hold / hold.cummax() - 1).min()) * 100
        ch = bud.diff().fillna(0)
        events = []
        for d in px.index[ch != 0]:
            cur, prev = bud.loc[d], (bud.iloc[px.index.get_loc(d) - 1] if px.index.get_loc(d) else 1.0)
            events.append({"d": str(d.date()),
                           "t": "买" if cur > prev else "卖",
                           "s": "满" if cur == 1.0 else ("半" if cur == 0.5 else "空")})
        # 周采样：保留事件日
        wk_idx = pd.Series(px.index).groupby(pd.Series(px.index).dt.to_period("W")).max().tolist()
        ev_dates = [pd.Timestamp(e["d"]) for e in events if pd.Timestamp(e["d"]) in px.index]
        idx = sorted(set(wk_idx + ev_dates))
        dates = [str(d.date()) for d in idx]
        eqs = [round(float(eq.loc[d] / eq.iloc[0]), 4) for d in idx]
        hos = [round(float(hold.loc[d] / hold.iloc[0]), 4) for d in idx]
        pos = [round(float(pos_pct.loc[d]), 1) for d in idx]
        date_list = dates
        ev_idx = []
        for e in events:
            key = e["d"]
            ev_idx.append({"i": date_list.index(key) if key in date_list else None, **e})
        ev_out = [{"i": e["i"], "d": e["d"], "t": e["t"], "s": e["s"]} for e in ev_idx if e["i"] is not None]
        blocks.append(
            f'  {{\n    name: "{name}", desc: "{desc}",\n'
            f'    ann: {ann:.1f}, dd: {dd:.1f}, annHold: {annh:.1f}, ddHold: {ddh:.1f}, nEvents: {len(events)},\n'
            f'    dates: {json_dump(dates)}, equity: {json_dump(eqs)}, hold: {json_dump(hos)},\n'
            f'    pos: {json_dump(pos)}, events: {json_dump(ev_out)}\n  }}')
        meta.append((name, ann, dd))
    ts = ("// 自动生成：scripts/export_flagship_data.py（PYTHONHASHSEED=0）\n"
          "export interface FlagshipCombo {\n"
          "  name: string; desc: string;\n"
          "  ann: number; dd: number; annHold: number; ddHold: number; nEvents: number;\n"
          "  dates: string[]; equity: number[]; hold: number[]; pos: number[];\n"
          "  events: { i: number; d: string; t: string; s: string }[];\n}\n"
          "export const FLAGSHIP_COMBOS: FlagshipCombo[] = [\n" + ",\n".join(blocks) + "\n];\n")
    out = Path(REPO / "web/src/data/flagshipCombos.ts")
    out.write_text(ts)
    print("written:", out, len(ts), "bytes")
    for m in meta:
        print("  ", m)


if __name__ == "__main__":
    main()
