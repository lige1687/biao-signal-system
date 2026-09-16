#!/usr/bin/env python3
"""情绪 × 量能矩阵（2026-09-06，tx_amount_panel 成交额维度）。

板块量能 = 成分股成交额合计的 20 日均值，z 相对自身 120 日基准
（放量 z≥1 / 缩量 z≤-1）。与情绪信号交叉（161 板块池化，10 日）：
1. C4 冰点机会 × 放量/缩量（放量=恐慌加速出清 vs 缩量=阴跌末期？）
2. 散户热(z≥1.5) × 放量/缩量（放量热=真实交锋 vs 缩量热=虚火）
3. 强热警报档 × 放量
4. TS5 抄底 × 放量/缩量
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import retail_mania_backtest as rb  # noqa: E402
from retail_mania_backtest import _norm_p  # noqa: E402
from retail_sentiment_ts_backtest import zscore_self, WARMUP
from market_mood_backtest import cn_mood_regime, regime_at

H = 10


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    cn = cn_mood_regime(close, flows)
    boards = [c for c in close.columns if (data["level"].get(c) or 3) <= 2]
    amt = pd.read_parquet(rb.CACHE / "tx_amount_panel.parquet").apply(pd.to_numeric, errors="coerce")
    amt.index = pd.to_datetime(amt.index)

    print(f"{'组合':26s} {'n':>4s} {'10日超额':>9s} {'p':>7s} 正占比")
    results_cache = {}

    for code in boards:
        C = close[code]
        # 板块量能：成分成交额合计（用 members）
        import json
        members = json.loads((rb.CACHE / "sector_members.json").read_text(encoding="utf-8"))["boards"]
        mem = [s for s in members.get(code, {}).get("members", []) if s in amt.columns]
        if len(mem) < 5 or code not in close.columns:
            continue
        A = amt[mem].sum(axis=1).reindex(C.index)
        vol_z = zscore_self(A.rolling(20, min_periods=20).mean())
        # 情绪分量
        pts = flows.get(code) or []
        recS = {}
        for p in pts:
            d = pd.to_datetime(p["date"])
            if d in C.index and p.get("small_yi") is not None and mv.get(code):
                mv_t = mv[code] * float(C.loc[d]) / float(C.dropna().iloc[-1])
                if mv_t > 0:
                    recS[d] = p["small_yi"] / mv_t
        S = pd.Series(recS).sort_index().reindex(C.index)
        z20 = zscore_self(S.rolling(20, min_periods=20).mean())
        r60 = C.pct_change(60, fill_method=None)
        results_cache[code] = (C, z20, vol_z, r60)

    def run(name, pick):
        rows, per_board = [], []
        for code, (C, z20, vol_z, r60) in results_cache.items():
            sig = pick(z20, vol_z, r60, code)
            if sig is None or int(sig.sum()) == 0:
                continue
            sig = sig.iloc[WARMUP:]
            f = (C.shift(-H) / C - 1.0).reindex(sig.index)
            vals = f[sig.fillna(False)].dropna()
            base = f.iloc[WARMUP:].dropna().mean()
            if len(vals) < 2:
                continue
            per_board.append(float(vals.mean() - base))
            rows.extend((t, float(v) - float(base)) for t, v in vals.items())
        if len(rows) < 15:
            print(f"{name:28s} {len(rows):4d}  样本不足")
            return
        ser = pd.Series({d: v for d, v in rows}).sort_index()
        daily = ser.groupby(level=0).mean()
        t = float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))))
        effs = np.array(per_board)
        pos = (effs > 0).mean() * 100
        star = "★" if _norm_p(t) < 0.01 and pos > 60 else " "
        print(f"{star}{name:27s} {len(rows):4d} {daily.mean()*100:+8.2f}% {_norm_p(t):7.4f} {pos:.0f}%")

    def c4(z20, vol_z, r60, code):
        base = ((z20 >= 1.5) & (r60 <= -0.10)).fillna(False)
        out = base & ((vol_z >= 1.0) | (vol_z <= -1.0)).fillna(False)  # 由档位细分
        return out

    run("C4冰点×放量(z≥1)", lambda z20, vz, r60, c:
        ((z20 >= 1.5) & (r60 <= -0.10) & (vz >= 1.0)).fillna(False))
    run("C4冰点×缩量(z≤-1)", lambda z20, vz, r60, c:
        ((z20 >= 1.5) & (r60 <= -0.10) & (vz <= -1.0)).fillna(False))
    run("C4冰点×量中性", lambda z20, vz, r60, c:
        ((z20 >= 1.5) & (r60 <= -0.10) & (vz > -1.0) & (vz < 1.0)).fillna(False))
    run("散户热×放量", lambda z20, vz, r60, c: ((z20 >= 1.5) & (vz >= 1.0)).fillna(False))
    run("散户热×缩量", lambda z20, vz, r60, c: ((z20 >= 1.5) & (vz <= -1.0)).fillna(False))
    run("散户热×量中性", lambda z20, vz, r60, c:
        ((z20 >= 1.5) & (vz > -1.0) & (vz < 1.0)).fillna(False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
