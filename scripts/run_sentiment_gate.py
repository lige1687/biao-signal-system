#!/usr/bin/env python3
"""情绪/杠杆信息 vs 股指：两融档位闸实验（2026-08-28 第十六轮）。

用户方向：把「宽度 vs 股指」方法论复制到其他基本面/情绪信息。
本轮数据资产（新增，均落盘 raw/sentiment/）：
- 上交所两融汇总 2018-06→2026-08（融资余额/买入额，akshare）
- 北向资金 2014-11→2024-08（披露停更前；死指标仅历史研究）

预注册口径（跑前落死）：
- 指标 = 融资余额 20 日变化率 → 3 年滚动分位（余额水平有长期趋势，
  必须用变化率+分位；SSE 口径作全市场代理）。
- J-S1（信息量，事件研究）：分位 >=90 / <=10 的信号日后 1/3/6/12
  个月指数远期收益 vs 全样本基线（000300）。
- J-S2（闸测试，2018-06→2026-08 与宽度闸同窗同台）：
  情绪档位 = 分位>90 → 0.5 / 10-90 → 0.8 / <10 → 1.0（周频判定、
  t+1 开盘、5bp）；对照 = 买入持有 与 宽度五档(h80@全A，同窗)。
  情绪闸胜出 = maxDD 改善 >= 15%（vs BH）且 CAGR >= 0.8×BH。
  另设混合臂：min(情绪档, 宽度档)（两闸取更低者）。
- J-S3（北向，仅 2014-2024 历史研究）：北向 20 日净流入速度分位
  极端的事件研究；不做闸（2024-08 后无数据，实盘死指标）。
- 声明：两融 2018 起仅 8 年（错过 2015 杠杆牛熊——最极端样本缺失，
  结论打折）；SSE 单所代理全市场；数据源东财/上交所，非 PIT 成分。

输出：raw/sentiment/sentiment_gate_results.json
复现：python3 scripts/run_sentiment_gate.py
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
from run_caliber_check import tier_target_map  # noqa: E402
from run_final_form_v2 import H80  # noqa: E402
from run_symbol_showcase import (  # noqa: E402
    cagr_dd,
    sim_bh,
    sim_width,
)

RAW = REPO / "docs/experiments/raw/sentiment"
RAW.mkdir(parents=True, exist_ok=True)
CACHE = Path.home() / ".lei_signal_lab/cache"
COST = 0.0005


def load_margin() -> pd.Series:
    df = pd.read_csv("/tmp/margin_sse.csv")
    df["date"] = pd.to_datetime(df["信用交易日期"], format="%Y%m%d")
    s = df.set_index("date")["融资余额"].astype(float).sort_index()
    chg = s.pct_change(20)
    pct = chg.rolling(756, min_periods=250).rank(pct=True)
    return pct.rename("margin_pct")


def load_north() -> pd.Series | None:
    p = Path("/tmp/north_flow.csv")
    if not p.exists():
        return None
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["日期"])
    s = df.set_index("date")["历史累计净买额"].astype(float).sort_index()
    chg = s.diff(20)
    pct = chg.rolling(756, min_periods=250).rank(pct=True)
    return pct.rename("north_pct")


def event_study(sig: pd.Series, bench_close: pd.Series, lo=0.9, hi=0.1,
                horizons=(21, 63, 126, 252)) -> dict:
    fwd = {h: bench_close.shift(-h) / bench_close - 1 for h in horizons}
    out = {"baseline": {h: round(float(f.mean()), 4)
                        for h, f in fwd.items()}}
    for name, mask in ((f">={lo:.0%}", sig >= lo), (f"<={hi:.0%}", sig <= hi)):
        days = sig.index[mask]
        days = days[days <= bench_close.index[-252]]
        res = {}
        for h in horizons:
            vals = [fwd[h].get(d) for d in days if d in fwd[h].index]
            vals = [v for v in vals if pd.notna(v)]
            res[h] = {"n": len(vals),
                      "mean": round(float(pd.Series(vals).mean()), 4)
                      if vals else None}
        out[name] = res
    return out


def sentiment_target_map(sig: pd.Series, hot=0.9, cold=0.1) -> dict[str, float]:
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
        pos = 0.5 if v > hot else (1.0 if v < cold else 0.8)
        out[str(days[i + 1].date())] = pos
    return out


def main() -> int:
    margin = load_margin()
    north = load_north()
    idx = pd.read_parquet(CACHE / "timing/000300.parquet")[["open", "close"]]
    idx.index = pd.to_datetime(idx.index).tz_localize(None).normalize()

    # ---- J-S1 两融信息量（2018-06 起）----
    win = idx.loc[margin.dropna().index[0]:]
    js1 = event_study(margin, win["close"])

    # ---- J-S3 北向（2014-2024）----
    js3 = None
    if north is not None:
        nwin = idx.loc[north.dropna().index[0]:"2024-08-31"]
        js3 = event_study(north, nwin["close"])

    # ---- J-S2 闸测试（同窗：2018-06→2026-08）----
    lo = margin.dropna().index[0]
    bars = idx.loc[lo:]
    s_map = sentiment_target_map(margin)
    br = load_breadth()
    w_map = tier_target_map(br, "ma200_pct", H80)
    mix_map = {}
    for k in set(s_map) | set(w_map):
        mix_map[k] = min(s_map.get(k, 1.0), w_map.get(k, 1.0))

    s_eq = sim_width(bars, s_map)
    w_eq = sim_width(bars, w_map)
    m_eq = sim_width(bars, mix_map)
    bh = sim_bh(bars)
    r = {"sentiment_gate": cagr_dd(s_eq), "breadth_gate": cagr_dd(w_eq),
         "mix_gate": cagr_dd(m_eq), "bh": cagr_dd(bh)}
    sdd_impr = (abs(r["bh"]["max_dd"]) - abs(r["sentiment_gate"]["max_dd"])) \
        / abs(r["bh"]["max_dd"])
    cagr_keep = r["sentiment_gate"]["cagr"] / r["bh"]["cagr"] \
        if r["bh"]["cagr"] != 0 else None
    verdict_js2 = bool(sdd_impr >= 0.15 and cagr_keep is not None
                       and cagr_keep >= 0.8)

    out = {"date": "2026-08-28", "window_js2": [str(bars.index[0].date()),
            str(bars.index[-1].date())],
           "JS1_margin_event": js1, "JS3_north_event": js3,
           "JS2_arms": r,
           "JS2": {"dd_improve": round(float(sdd_impr), 3),
                    "cagr_keep": round(cagr_keep, 3) if cagr_keep else None,
                    "pass": verdict_js2}}
    (RAW / "sentiment_gate_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    margin.dropna().to_frame().to_csv(RAW / "margin_signal.csv")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
