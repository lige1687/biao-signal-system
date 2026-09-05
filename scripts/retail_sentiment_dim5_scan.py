#!/usr/bin/env python3
"""散户情绪·第五轮深挖（2026-09-05，聚焦 8 板块组）。

五个新维度（此前未测）：
1. 分板块个体明细：TS5/TS6 在各组各自的触发数与效果（哪些板块灵）；
2. RS 叠加：TS5 × 板块RS高于全A（相对强抄底 vs 相对弱抄底）；
3. 阶段叠加：TS5 × 回算阶段（筑底期 vs 下降期抄底）；
4. 多板块共振：触发日 ≥2 组同时 TS5（普跌中的逆势共识）vs 单组；
5. 执行时点：触发当日 vs 延迟 3/5 日入场的前向收益；
6. C4（冰点抄底）21 次触发全案例明细。
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
from retail_sentiment_ts_backtest import BOARDS, WARMUP, zscore_self
from retail_sentiment_deep_scan import load_group_series
from market_mood_backtest import cn_mood_regime, regime_at

CACHE = rb.CACHE


def group_rs(close: pd.DataFrame, gcode: list[str]) -> pd.Series | None:
    """组等权指数 / 全板块等权基准 的 RS，及其 20 日均线之上布尔。"""
    cs = [close[c] for c in gcode if c in close.columns]
    if not cs:
        return None
    idx = pd.concat(cs, axis=1).mean(axis=1)
    bench = (1 + close.pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod()
    rs = idx / bench
    return rs > rs.rolling(20, min_periods=20).mean()


def group_stage(close: pd.DataFrame, gcode: list[str]) -> pd.Series | None:
    """组级粗阶段：up=价格>SMA60，down=价格<SMA60（粗口径，用于分层）。"""
    cs = [close[c] for c in gcode if c in close.columns]
    if not cs:
        return None
    idx = pd.concat(cs, axis=1).mean(axis=1)
    sma60 = idx.rolling(60, min_periods=60).mean()
    return pd.Series(np.where(idx > sma60, "up", "down"), index=idx.index)


def ts5_sig(gd, dip_th=-0.10, z_th=1.5) -> pd.Series:
    S, C = gd["S"], gd["C"]
    z20 = zscore_self(S.rolling(20, min_periods=20).mean())
    r60 = C.pct_change(60, fill_method=None)
    return ((z20 >= z_th) & (r60 <= dip_th)).fillna(False)


def ts6_sig(gd) -> pd.Series:
    S, C = gd["S"], gd["C"]
    up = C.pct_change(fill_method=None) > 0
    chase = (S * up.shift(1)).rolling(20, min_periods=20).sum()
    return (zscore_self(chase) >= 1.5).fillna(False)


def fwd_ret(C: pd.Series, h: int, delay: int = 0) -> pd.Series:
    return (C.shift(-(h + delay)) / C.shift(-delay) - 1.0)


def main() -> int:
    data = rb.load_panels(str(CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    gs = load_group_series(data)
    cn = cn_mood_regime(close, flows)

    # ── 1. 分板块明细 ──
    print("== ① 分板块个体（TS5 抄底 / TS6 追涨：触发数、10日均收、胜率） ==")
    rows = []
    for g, gd in gs.items():
        C = gd["C"]
        f10 = fwd_ret(C, 10)
        for name, fn in (("TS5", ts5_sig), ("TS6", ts6_sig)):
            sig = fn(gd).iloc[WARMUP:]
            vals = f10.reindex(sig.index)[sig.fillna(False)].dropna()
            base = f10.iloc[WARMUP:].dropna().mean()
            if len(vals) == 0:
                rows.append((g, name, 0, np.nan, np.nan, base))
            else:
                rows.append((g, name, len(vals), vals.mean() * 100,
                             (vals > 0).mean() * 100, base * 100))
    df = pd.DataFrame(rows, columns=["组", "信号", "n", "10日均收%", "胜率%", "基准%"])
    for sig_name in ("TS5", "TS6"):
        sub = df[df["信号"] == sig_name]
        print(f"\n  [{sig_name}]")
        for _, r in sub.iterrows():
            if r["n"] == 0:
                print(f"    {r['组']:10s} n=0")
            else:
                print(f"    {r['组']:10s} n={r['n']:.0f}  {r['10日均收%']:+.2f}%  胜率{r['胜率%']:.0f}%  (基准{r['基准%']:+.2f}%)")

    # ── 2/3. RS 与阶段叠加 ──
    print("\n== ② TS5 × RS / × 阶段 分层（10日超额，基准=组内无条件） ==")
    for label, split in (("RS强", "rs"), ("阶段up/down", "stage")):
        for part in (("RS强", "RS弱") if split == "rs" else ("up", "down")):
            rets, bases = [], []
            for g, gd in gs.items():
                C = gd["C"]
                sig = ts5_sig(gd).iloc[WARMUP:]
                if int(sig.sum()) == 0:
                    continue
                if split == "rs":
                    cond = group_rs(close, BOARDS[g])
                else:
                    cond = group_stage(close, BOARDS[g])
                if cond is None:
                    continue
                cond = cond.reindex(sig.index)
                sel = sig.fillna(False) & (cond == (True if part == "RS强" else part)).fillna(False) \
                    if split == "rs" else sig.fillna(False) & (cond == part).fillna(False)
                f10 = fwd_ret(C, 10).reindex(sig.index)
                vals = f10[sel].dropna()
                b = f10.iloc[WARMUP:].dropna().mean()
                rets.extend((vals - b).tolist())
            if len(rets) >= 8:
                s = pd.Series(rets)
                print(f"    {label}={part}: n={len(rets)} 超额均值{s.mean()*100:+.2f}%")
            else:
                print(f"    {label}={part}: 样本不足(n={len(rets)})")

    # ── 4. 多板块共振 ──
    print("\n== ③ TS5 共振分层（触发日同时触发的组数） ==")
    daily_counts = {}
    for g, gd in gs.items():
        sig = ts5_sig(gd)
        for t in sig.index[sig.fillna(False)]:
            daily_counts[t] = daily_counts.get(t, 0) + 1
    for lo, hi, label in ((2, 99, "≥2组共振"), (1, 1, "单组")):
        rets = []
        for g, gd in gs.items():
            C = gd["C"]
            sig = ts5_sig(gd).iloc[WARMUP:]
            f10 = fwd_ret(C, 10).reindex(sig.index)
            base = f10.iloc[WARMUP:].dropna().mean()
            for t in sig.index[sig.fillna(False)]:
                c = daily_counts.get(t, 0)
                if lo <= c <= hi:
                    v = f10.get(t)
                    if v is not None and not pd.isna(v):
                        rets.append(float(v) - float(base))
        if len(rets) >= 8:
            print(f"    {label}: n={len(rets)} 超额均值{np.mean(rets)*100:+.2f}%")
        else:
            print(f"    {label}: 样本不足(n={len(rets)})")

    # ── 5. 执行时点 ──
    print("\n== ④ TS5 执行时点（触发日 vs 延迟3/5日入场，20日前向） ==")
    for delay in (0, 3, 5):
        rets = []
        for g, gd in gs.items():
            C = gd["C"]
            sig = ts5_sig(gd).iloc[WARMUP:]
            f20 = fwd_ret(C, 20, delay).reindex(sig.index)
            base = fwd_ret(C, 20, 0).iloc[WARMUP:].dropna().mean()
            vals = f20[sig.fillna(False)].dropna()
            rets.extend((vals - base).tolist())
        if rets:
            print(f"    延迟{delay}日入场: n={len(rets)} 超额均值{np.mean(rets)*100:+.2f}%")

    # ── 6. C4 案例明细 ──
    print("\n== ⑤ C4（TS5 × CN冰点）全案例（10/20日后收益） ==")
    events = []
    for g, gd in gs.items():
        C = gd["C"]
        sig = ts5_sig(gd)
        f10, f20 = fwd_ret(C, 10), fwd_ret(C, 20)
        for t in sig.index[sig.fillna(False)]:
            if regime_at(cn, t) == "冷":
                events.append((str(t.date()), g, f10.get(t), f20.get(t)))
    events.sort()
    for d, g, a, b in events:
        fa = f"{a*100:+.1f}%" if a is not None and not pd.isna(a) else "-"
        fb = f"{b*100:+.1f}%" if b is not None and not pd.isna(b) else "-"
        print(f"    {d}  {g:10s} 10日后{fa:8s} 20日后{fb:8s}")
    if events:
        v10 = [e[2] for e in events if e[2] is not None and not pd.isna(e[2])]
        v20 = [e[3] for e in events if e[3] is not None and not pd.isna(e[3])]
        print(f"    合计 {len(events)} 例：10日胜率{np.mean([x>0 for x in v10])*100:.0f}% 均{np.mean(v10)*100:+.2f}%"
              f" | 20日胜率{np.mean([x>0 for x in v20])*100:.0f}% 均{np.mean(v20)*100:+.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
