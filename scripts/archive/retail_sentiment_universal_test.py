#!/usr/bin/env python3
"""散户情绪信号·共性检验（2026-09-05）。

用户质疑：信号若只在部分板块有效，说明定义捕捉的不是共性散户情绪。
检验（在全部 161 个一、二级行业上，非仅 8 组）：
1. TS5/TS6 全板块池化效应（按日聚合）；
2. 板块级效应方向分布：TS5 在 161 个板块各自的超额方向——
   多数同向=共性成立；约半正半负=定义有问题；
3. 异质性来源：高/低波动分层、大/小市值分层——若效应集中于
   高波动组，则信号实为「高波动均值回归」而非散户情绪；
4. 对照：随机伪信号（同触发数的随机日）的板块级效应散布，
   用来判断 TS5 板块间离散度是否超出随机水平。
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
from retail_sentiment_ts_backtest import zscore_self

WARMUP = 60
H = 10


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    snap = data  # mv_today / level 已在

    boards = [c for c in close.columns if (data["level"].get(c) or 3) <= 2]
    print(f"参与共性检验的板块：{len(boards)} 个（一、二级行业）")

    def sig_of(code: str) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        c_series = close[code]
        pts = flows.get(code) or []
        recS = {}
        for p in pts:
            d = pd.to_datetime(p["date"])
            if d in c_series.index and p.get("small_yi") is not None and mv.get(code):
                mv_t = mv[code] * float(c_series.loc[d]) / float(c_series.dropna().iloc[-1])
                if mv_t > 0:
                    recS[d] = p["small_yi"] / mv_t
        S = pd.Series(recS).sort_index().reindex(c_series.index)
        z20 = zscore_self(S.rolling(20, min_periods=20).mean())
        r60 = c_series.pct_change(60, fill_method=None)
        ts5 = ((z20 >= 1.5) & (r60 <= -0.10)).fillna(False)
        up = c_series.pct_change(fill_method=None) > 0
        chase = (S * up.shift(1)).rolling(20, min_periods=20).sum()
        ts6 = (zscore_self(chase) >= 1.5).fillna(False)
        return ts5, ts6, S, c_series

    # ① 池化（按触发日聚合）
    for name in ("TS5", "TS6"):
        rows = []
        per_board = []
        for code in boards:
            idx = name == "TS5" and 0 or 1
            ts5, ts6, S, C = sig_of(code)
            sig = (ts5 if name == "TS5" else ts6)
            if int(sig.sum()) == 0:
                continue
            sig = sig.iloc[WARMUP:]
            f = ((C.shift(-H) / C - 1.0).reindex(sig.index))
            vals = f[sig.fillna(False)].dropna()
            base = f.iloc[WARMUP:].dropna().mean()
            if len(vals) < 3:
                continue
            eff = float(vals.mean() - base)
            per_board.append((code, eff, len(vals)))
            for t in vals.index:
                rows.append((t, float(f[t]) - float(base)))
        ser = pd.Series({d: v for d, v in rows}).sort_index()
        daily = ser.groupby(level=0).mean()
        t = float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))))
        effs = np.array([e for _, e, _ in per_board])
        pos = int((effs > 0).sum()); neg = int((effs <= 0).sum())
        print(f"\n[{name}] 池化：{len(rows)} 触发 / {len(daily)} 日，按日聚合 "
              f"{daily.mean()*100:+.2f}%（p={_norm_p(t):.4f}）")
        print(f"   板块级效应分布：正 {pos} / 负 {neg}（正占比 {pos/(pos+neg)*100:.0f}%），"
              f"中位 {np.median(effs)*100:+.2f}%，IQR [{np.percentile(effs,25)*100:+.1f}%, {np.percentile(effs,75)*100:+.1f}%]")

    # ② 异质性来源：波动/市值分层（TS5）
    print("\n[TS5 异质性] 按 60 日波动率三档 × 按市值三档（板块级效应均值，n=板块数）")
    vol_eff, mv_eff = {}, {}
    for code in boards:
        ts5, ts6, S, C = sig_of(code)
        sig = ts5.iloc[WARMUP:]
        if int(sig.sum()) == 0:
            continue
        f = ((C.shift(-H) / C - 1.0).reindex(sig.index))
        vals = f[sig.fillna(False)].dropna()
        base = f.iloc[WARMUP:].dropna().mean()
        if len(vals) < 3:
            continue
        vol = float(C.pct_change(fill_method=None).rolling(60).std().iloc[-1] or 0)
        vol_eff[code] = (vol, float(vals.mean() - base))
        mv_eff[code] = (mv.get(code) or 0, float(vals.mean() - base))
    for label, d in (("波动率", vol_eff), ("市值", mv_eff)):
        if not d:
            continue
        vals = sorted(d.values())
        k = len(vals) // 3
        tiers = [("低", vals[:k]), ("中", vals[k:2*k]), ("高", vals[2*k:])]
        line = []
        for tname, arr in tiers:
            if arr:
                line.append(f"{tname}:{np.mean([e for _, e in arr])*100:+.2f}%(n={len(arr)})")
        print(f"   按{label}：{' | '.join(line)}")

    # ③ 随机对照：与 TS5 总触发数相同的随机信号，板块级效应正占比的散布
    print("\n[随机对照] 20 次随机伪信号（同触发总数）的板块级正占比分布：")
    rng = np.random.default_rng(7)
    total_trigs = sum(int(ts_sum) for ts_sum in [int(sig_of(c)[0].iloc[WARMUP:].sum()) for c in boards[:1]])  # 近似
    ratios = []
    for _ in range(20):
        rand_pos, rand_neg = 0, 0
        for code in boards:
            ts5, _, S, C = sig_of(code)
            n = int(ts5.iloc[WARMUP:].sum())
            if n == 0:
                continue
            f = ((C.shift(-H) / C - 1.0).reindex(ts5.index)).iloc[WARMUP:]
            base = f.dropna().mean()
            pick = f.dropna().sample(n=min(n, len(f.dropna())), random_state=rng.integers(1 << 30))
            if pick.mean() > base:
                rand_pos += 1
            else:
                rand_neg += 1
        if rand_pos + rand_neg:
            ratios.append(rand_pos / (rand_pos + rand_neg))
    if ratios:
        print(f"   随机正占比：均值 {np.mean(ratios)*100:.0f}%，区间 "
              f"[{np.min(ratios)*100:.0f}%, {np.max(ratios)*100:.0f}%]（TS5 实际见上）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
