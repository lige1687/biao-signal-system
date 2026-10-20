#!/usr/bin/env python3
"""情绪 × 宽度档位矩阵（2026-09-06，用户指定档位体系）。

宽度口径：板块 b20/b50/b200（成分股站上 MA20/50/200 比例，从个股 close
全量重算；b200 仅窗口尾段有效，如实标注）。档位：
- 单口径：低 <30 / 高 >70；
- 组合档：b50&b200 同低（深度弱势）、同高（全面强势）、b50高&b200低
  （短修复长弱势=反弹初）、b50低&b200高（短回调长强势=回调中）；
- b20/b50 金叉叉口：b20>50 且 b50<30（宽度刚启动）等。
情绪信号：C4冰点抄底、TS5抄底、散户热、接刀、宽度冲刷（对照）。
输出：各（信号×档位）的 10 日超额池化（161 板块、按日聚合）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import retail_mania_backtest as rb  # noqa: E402
from retail_mania_backtest import _norm_p  # noqa: E402
from retail_sentiment_ts_backtest import zscore_self
from market_mood_backtest import cn_mood_regime, regime_at

CACHE = rb.CACHE
WARMUP, H = 60, 10


def build_breadth_panels() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """个股 MA 站上比例 → 各板块 b20/b50/b200 面板 + 全市场等权 close。"""
    df = pd.read_parquet(CACHE / "a_share_klines.parquet")
    wide = df.pivot(index="date", columns="symbol", values="close").sort_index()
    wide.index = pd.to_datetime(wide.index)
    members = json.loads((CACHE / "sector_members.json").read_text())["boards"]
    snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text())
    canonical = {b["code"] for b in snap["boards"]}

    panels = {}
    for w in (20, 50, 200):
        ma = wide.rolling(w, min_periods=w).mean()
        above = (wide > ma).astype(float)
        above = above.where(wide.notna())  # 上市前不计入分母
        boards_b = {}
        for code, info in members.items():
            if code not in canonical:
                continue
            mem = [s for s in info["members"] if s in wide.columns]
            if len(mem) < 5:
                continue
            sub = above[mem]
            boards_b[code] = sub.mean(axis=1) * 100
        panels[f"b{w}"] = pd.DataFrame(boards_b)
    return panels, wide


def main() -> int:
    data = rb.load_panels(str(CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    cn = cn_mood_regime(close, flows)
    boards = [c for c in close.columns if (data["level"].get(c) or 3) <= 2]

    print("重算板块宽度面板（b20/b50/b200）…", flush=True)
    panels, _ = build_breadth_panels()
    b20, b50, b200 = panels["b20"], panels["b50"], panels["b200"]
    valid200 = b200.dropna(how="all").index
    print(f"b200 有效起点：{valid200[0].date() if len(valid200) else '无'}（样本自动截短）")

    def sigs(code):
        C = close[code]
        pts = flows.get(code) or []
        recS, recJ = {}, {}
        for p in pts:
            d = pd.to_datetime(p["date"])
            if d not in C.index or not mv.get(code):
                continue
            mv_t = mv[code] * float(C.loc[d]) / float(C.dropna().iloc[-1])
            if mv_t <= 0:
                continue
            if p.get("small_yi") is not None:
                recS[d] = p["small_yi"] / mv_t
            jv = p.get("jumbo_yi") if "jumbo_yi" in p else p.get("super_large_yi")
            if jv is not None:
                recJ[d] = jv / mv_t
        S = pd.Series(recS).sort_index().reindex(C.index)
        J = pd.Series(recJ).sort_index().reindex(C.index)
        z20 = zscore_self(S.rolling(20, min_periods=20).mean())
        up, down = C.pct_change(fill_method=None) > 0, C.pct_change(fill_method=None) < 0
        chase_z = zscore_self((S * up.shift(1)).rolling(20, min_periods=20).sum())
        dip_z = zscore_self((J * down.shift(1)).rolling(20, min_periods=20).sum())
        r60 = C.pct_change(60, fill_method=None)
        return C, z20, chase_z, dip_z, r60

    def cn_cold(sig: pd.Series) -> pd.Series:
        return pd.Series([bool(v) and regime_at(cn, t) == "冷" for t, v in sig.items()],
                         index=sig.index)

    # 档位函数：返回 (档位名 -> bool Series)
    def tiers(code):
        C, z20, chase_z, dip_z, r60 = sigs(code)
        idx = C.index
        g = {}
        if code in b50.columns:
            bb20 = b20[code].reindex(idx); bb50 = b50[code].reindex(idx)
            g["b50低"] = (bb50 < 30).fillna(False)
            g["b50高"] = (bb50 > 70).fillna(False)
            g["b20低"] = (bb20 < 30).fillna(False)
            g["b20高"] = (bb20 > 70).fillna(False)
            g["宽度启动(b20高&b50低)"] = g["b20高"] & g["b50低"]
            if code in b200.columns:
                bb200 = b200[code].reindex(idx)
                g["50&200同低(深弱)"] = (bb50 < 30) & (bb200 < 30).fillna(False)
                g["50&200同高(全强)"] = (bb50 > 70).fillna(False) & (bb200 > 70).fillna(False)
                g["50高&200低(反弹初)"] = (bb50 > 50).fillna(False) & (bb200 < 30).fillna(False)
                g["50低&200高(回调中)"] = (bb50 < 50).fillna(False) & (bb200 > 70).fillna(False)
                g = {k: v.fillna(False) for k, v in g.items()}
        return C, z20, chase_z, dip_z, r60, g

    EMOTIONS = {
        "散户热(z≥1.5)": lambda z20, chase, dip, r60: (z20 >= 1.5),
        "追涨热(chase z≥1.5)": lambda z20, chase, dip, r60: (chase >= 1.5),
        "接刀(dip z≥1.5)": lambda z20, chase, dip, r60: (dip >= 1.5),
        "TS5抄底": lambda z20, chase, dip, r60: (z20 >= 1.5) & (r60 <= -0.10),
        "C4冰点抄底": lambda z20, chase, dip, r60: (z20 >= 1.5) & (r60 <= -0.10),
    }

    print(f"\n== 情绪 × 宽度档位矩阵（10日超额，161板块池化；C4 自带 CN 冰点过滤） ==")
    print(f"{'情绪':16s} × {'宽度档':22s} {'n':>4s} {'超额':>8s} {'p':>7s} 正占比")
    for ename, ef in EMOTIONS.items():
        # 收集该情绪的信号与档位
        cache_rows = []
        tier_names = None
        for code in boards:
            C, z20, chase_z, dip_z, r60, g = tiers(code)
            if not g:
                continue
            if tier_names is None:
                tier_names = list(g.keys())
            sig = ef(z20, chase_z, dip_z, r60).fillna(False)
            if ename == "C4冰点抄底":
                sig = cn_cold(sig)
            f = (C.shift(-H) / C - 1.0).reindex(sig.index)
            base = f.iloc[WARMUP:].dropna().mean()
            cache_rows.append((code, sig, f, base, g))
        if not cache_rows or tier_names is None:
            continue
        for tname in tier_names:
            rows, n_pos, n_boards = [], 0, 0
            for code, sig, f, base, g in cache_rows:
                sel = (sig.iloc[WARMUP:] & g[tname].iloc[WARMUP:]).fillna(False)
                vals = f.iloc[WARMUP:][sel].dropna()
                if len(vals) == 0:
                    continue
                n_boards += 1
                if vals.mean() > base:
                    n_pos += 1
                rows.extend((t, float(v) - float(base)) for t, v in vals.items())
            if len(rows) < 15:
                print(f"{ename:16s} × {tname:22s} {len(rows):4d}  样本不足")
                continue
            ser = pd.Series({d: v for d, v in rows}).sort_index()
            daily = ser.groupby(level=0).mean()
            t = float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))))
            pos = n_pos / n_boards * 100 if n_boards else 0
            star = "★" if _norm_p(t) < 0.01 and pos > 60 else " "
            print(f"{ename:16s} ×{tname:23s} {len(rows):4d} {daily.mean()*100:+7.2f}% {_norm_p(t):7.4f} {pos:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
