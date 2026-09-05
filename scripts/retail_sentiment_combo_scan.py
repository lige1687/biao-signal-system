#!/usr/bin/env python3
"""散户情绪·组合深挖轮（2026-09-05）。

目标：在已通过检验的三信号（TS6 追涨风险 / TS5 抄底机会 / TS11 机构接刀）
基础上，扫描**语义明确的组合**找最高胜率，并精化参数、给出最佳持有期。

纪律：每个组合必须（a）有清晰叙事（b）n≥20（c）按日聚合 p<0.01——
三者缺一即弃；纯挖矿组合不测（如无语义的三信号交集）。

组合清单（预注册语义）：
  C1  TS5 基准（跌中散户涌入）
  C2  TS5 且 非TS11（散户抄底·机构未接刀=卖压真实衰竭）
  C3  TS5 + 站回MA20（右侧确认版）
  C4  TS5 + CN冰点环境（恐慌极值中的散户涌入）
  C5  TS5 跌幅细化：r60 ≤ -5% / -10% / -15%
  C6  TS5 z 细化：1.0 / 1.5 / 2.0
  C7  TS6 基准
  C8  TS6 + CN热（热市追涨=最拥挤）
  C9  TS6 + US窄（外部风险偏好收缩时的追涨）
  C10 TS11 基准
  C11 TS11 + CN热
持有期曲线：5/10/20/40/60 + MFE 到达日（对胜出者）。
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
from retail_sentiment_deep_scan import load_group_series, daily_agg_test
from market_mood_backtest import cn_mood_regime, us_breadth_regime, regime_at

HOLD = (5, 10, 20, 40, 60)


def signals(gd: dict[str, pd.Series], *, dip_th=-0.10, z_th=1.5) -> dict[str, pd.Series]:
    S, J, C = gd["S"], gd["J"], gd["C"]
    ret = C.pct_change(fill_method=None)
    r60 = C.pct_change(60, fill_method=None)
    z20 = zscore_self(S.rolling(20, min_periods=20).mean())
    up = ret > 0
    down = ret < 0
    chase = (S * up.shift(1)).rolling(20, min_periods=20).sum()
    dip_buy = (J * down.shift(1)).rolling(20, min_periods=20).sum()
    ma20 = C.rolling(20, min_periods=20).mean()
    low_recent = C.rolling(20, min_periods=20).min()
    return {
        "TS5": (z20 >= z_th) & (r60 <= dip_th),
        "TS6": (zscore_self(chase) >= 1.5),
        "TS11": (zscore_self(dip_buy) >= 1.5),
        "right_ma20": (C > ma20) & (ma20.diff() >= 0),
        "no_new_low": low_recent > low_recent.shift(20),
    }


def run_combo(sig_map, gs, fwd, cn, us, h=10):
    rows, agree, total = [], 0, 0
    for g, base in sig_map.items():
        base = base.iloc[WARMUP:]
        f = fwd[g][h].reindex(base.index)
        if int(base.sum()) == 0:
            continue
        total += 1
        t_vals = f[base.fillna(False)].dropna()
        bench = f.iloc[WARMUP:].dropna().mean()
        for t in t_vals.index:
            rows.append((t, float(f[t]) - float(bench)))
        if len(t_vals) >= 3 and t_vals.mean() > bench:  # 机会方向一致
            agree += 1
    if len(rows) < 20:
        return dict(n=len(rows), note="样本不足")
    ser = pd.Series({d: v for d, v in rows}).sort_index()
    daily = ser.groupby(level=0).mean()
    t = float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))))
    # 绝对胜率（触发日收益>0 比例）
    abs_rets = pd.Series({d: v for d, v in rows}, dtype=float)
    return dict(n=len(rows), mean=daily.mean() * 100, t=t, p=_norm_p(t),
                days=len(daily), agree=f"{agree}/{total}")


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    gs = load_group_series(data)
    fwd = {g: {h: (d["C"].shift(-h) / d["C"] - 1.0) for h in HOLD} for g, d in gs.items()}
    cn = cn_mood_regime(data["close"], data["flows"])
    us = us_breadth_regime()

    combos: dict[str, callable] = {}

    def build(name, fn):
        combos[name] = fn

    build("C1 TS5基准", lambda g: signals(gs[g])["TS5"])
    build("C2 TS5+非TS11", lambda g: signals(gs[g])["TS5"] & ~signals(gs[g])["TS11"])
    build("C3 TS5+站回MA20", lambda g: signals(gs[g])["TS5"] & signals(gs[g])["right_ma20"])
    build("C4 TS5+CN冰点", lambda g: _with_regime(signals(gs[g])["TS5"], cn, "冷"))
    build("C5a TS5(跌5%)", lambda g: signals(gs[g], dip_th=-0.05)["TS5"])
    build("C5b TS5(跌15%)", lambda g: signals(gs[g], dip_th=-0.15)["TS5"])
    build("C6a TS5(z1.0)", lambda g: signals(gs[g], z_th=1.0)["TS5"])
    build("C6b TS5(z2.0)", lambda g: signals(gs[g], z_th=2.0)["TS5"])
    build("C7 TS6基准", lambda g: signals(gs[g])["TS6"])
    build("C8 TS6+CN热", lambda g: _with_regime(signals(gs[g])["TS6"], cn, "热"))
    build("C9 TS6+US窄", lambda g: _with_regime(signals(gs[g])["TS6"], us, "窄"))
    build("C10 TS11基准", lambda g: signals(gs[g])["TS11"])
    build("C11 TS11+CN热", lambda g: _with_regime(signals(gs[g])["TS11"], cn, "热"))
    build("C12 TS5+非TS11+不创新低", lambda g: signals(gs[g])["TS5"] & ~signals(gs[g])["TS11"] & signals(gs[g])["no_new_low"])

    print(f"{'组合':24s} {'n':>4s} {'10日超额均':>10s} {'p':>7s} {'天':>4s} 方向一致")
    results = {}
    for name, fn in combos.items():
        sig = {g: fn(g) for g in gs}
        r = run_combo(sig, gs, fwd, cn, us, 10)
        results[name] = (sig, r)
        if "note" in r:
            print(f"{name:24s} {r['n']:4d}  {r['note']}")
        else:
            print(f"{name:24s} {r['n']:4d}  {r['mean']:+9.2f}% {r['p']:7.4f} {r['days']:4d}  {r['agree']}")

    # 胜出者持有期曲线 + MFE
    best = max(((k, v) for k, v in results.items() if "p" in v[1] and v[1]["p"] < 0.01),
               key=lambda kv: kv[1][1]["mean"], default=None)
    if best:
        name, (sig, r) = best
        print(f"\n== 胜出组合「{name}」持有期曲线 ==")
        curve = []
        for h in HOLD:
            rr = run_combo(sig, gs, fwd, cn, us, h)
            if "mean" in rr:
                curve.append(f"{h}日:{rr['mean']:+.2f}%/p={rr['p']:.3f}")
        print("  " + "  ".join(curve))
        # 绝对胜率与 MFE
        abs_rets = []
        mfe_days = []
        for g, base in sig.items():
            base = base.iloc[WARMUP:]
            C = gs[g]["C"]
            for t in base.index[base.fillna(False)]:
                i = C.index.get_loc(t)
                if i + 60 < len(C):
                    v10 = C.iloc[min(i + 10, len(C) - 1)] / C.iloc[i] - 1
                    abs_rets.append(v10)
                    seg = C.iloc[i + 1:i + 61]
                    mfe_days.append(int(np.nanargmax(seg.values)) + 1)
        if abs_rets:
            print(f"  10日绝对胜率 {np.mean([x > 0 for x in abs_rets]) * 100:.0f}%（n={len(abs_rets)}）"
                  f" | MFE峰值中位第 {np.median(mfe_days):.0f} 日")
    return 0


def _with_regime(sig: pd.Series, reg, state: str) -> pd.Series:
    out = sig.copy()
    for t in out.index:
        if out.loc[t] and regime_at(reg, t) != state:
            out.loc[t] = False
    return out


if __name__ == "__main__":
    sys.exit(main())
