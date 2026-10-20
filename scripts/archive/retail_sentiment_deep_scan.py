#!/usr/bin/env python3
"""散户情绪定义·深度扩展轮（探索性，2026-09-05）。

内容：
1. TS6 参数稳健性网格：z∈{1.0,1.5,2.0} × 窗口∈{10,20,40} × 持有期∈{5,10,20,40}
   ——真信号应跨参数稳定，只在一个格子里显著=过拟合迹象；
2. 新定义族 TS8-TS14（单日极端追涨/顶背离/高波动追涨/跌日机构逆势/
   复合过热/散户流入斜率加速/涨跌日强度差）；
3. 胜出定义间相关性（去冗余）与分板块明细。

判定（从严，对抗多重比较）：p<0.01 或方向一致 ≥7/8 才标 ★。
板块组同 retail_sentiment_ts_backtest（用户指定 8 组）。
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
from retail_sentiment_ts_backtest import BOARDS, BASE_WIN, WARMUP, zscore_self

HOLD = (5, 10, 20, 40)


def load_group_series(data) -> dict[str, dict[str, pd.Series]]:
    """每组：S（散户流入强度日值）、J（超大单强度日值）、close、日收益。"""
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    out = {}
    for gname, codes in BOARDS.items():
        S_l, J_l, C_l = [], [], []
        for c in codes:
            if c not in close.columns:
                continue
            s = close[c]
            C_l.append(s)
            pts = flows.get(c) or []
            recS, recJ = {}, {}
            for p in pts:
                d = pd.to_datetime(p["date"])
                if d in s.index and mv.get(c):
                    mv_t = mv[c] * float(s.loc[d]) / float(s.dropna().iloc[-1])
                    if mv_t > 0:
                        if p.get("small_yi") is not None:
                            recS[d] = p["small_yi"] / mv_t
                        if p.get("jumbo_yi") if "jumbo_yi" in p else p.get("super_large_yi") is not None:
                            recJ[d] = (p.get("jumbo_yi") or p.get("super_large_yi")) / mv_t
            S_l.append(pd.Series(recS).sort_index().reindex(s.index))
            J_l.append(pd.Series(recJ).sort_index().reindex(s.index))
        if not C_l:
            continue
        out[gname] = {
            "S": pd.concat(S_l, axis=1).mean(axis=1),
            "J": pd.concat(J_l, axis=1).mean(axis=1),
            "C": pd.concat(C_l, axis=1).mean(axis=1),
        }
    return out


def daily_agg_test(sig_by_group, fwd_by_group, h=10) -> tuple[float, float, int, int, int]:
    """按触发日聚合：返回 (均值%, t, p, n触发, n日)。基准=组内无条件均值。"""
    rows = []
    agree, total = 0, 0
    for g, sig in sig_by_group.items():
        f = fwd_by_group[g][h]
        sig = sig.iloc[WARMUP:]
        if int(sig.sum()) == 0:
            continue
        total += 1
        f = f.reindex(sig.index)
        t_vals = f[sig.fillna(False)].dropna()
        base = f.iloc[WARMUP:].dropna().mean()
        for t in t_vals.index:
            rows.append((t, float(f[t]) - float(base)))
        if len(t_vals) >= 3 and t_vals.mean() < base:
            agree += 1
    if len(rows) < 15:
        return (np.nan, np.nan, np.nan, len(rows), 0), 0, total
    ser = pd.Series({d: v for d, v in rows}).sort_index()
    daily = ser.groupby(level=0).mean()
    t = float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))))
    return (float(daily.mean() * 100), t, _norm_p(t), len(rows), len(daily)), agree, total


def build_defs(gd: dict[str, dict[str, pd.Series]], *, z_th=1.5, win=20) -> dict[str, dict[str, pd.Series]]:
    out: dict[str, dict[str, pd.Series]] = {}
    z20 = zscore_self(gd["S"].rolling(win, min_periods=win).mean())
    jz20 = zscore_self(gd["J"].rolling(win, min_periods=win).mean())
    ret = gd["C"].pct_change(fill_method=None)
    up = ret > 0
    down = ret < 0
    r60 = gd["C"].pct_change(60, fill_method=None)
    # TS6 核心（参数化）
    chase = (gd["S"] * up.shift(1)).rolling(win, min_periods=win).sum()
    out["chase"] = (zscore_self(chase) >= z_th).fillna(False)
    # TS8 单日极端：小单净流入创 60 日新高 且 当日上涨
    out["ts8_extreme_day"] = ((gd["S"] >= gd["S"].rolling(60, min_periods=60).max().shift(1)) & up).fillna(False)
    # TS9 顶背离：价格创 60 日新高 但 chase-z 低于其过去 20 日最大值 -0.5σ
    price_high = gd["C"] >= gd["C"].rolling(60, min_periods=60).max().shift(1)
    cz = zscore_self(chase)
    out["ts9_top_div"] = (price_high & (cz < cz.rolling(20, min_periods=20).max().shift(1) - 0.5)).fillna(False)
    # TS10 高波动追涨：ATR20 z≥1 且 chase-z≥1.0
    atr = (ret.abs().rolling(20, min_periods=20).mean())
    out["ts10_vol_chase"] = ((zscore_self(atr) >= 1.0) & (cz >= 1.0)).fillna(False)
    # TS11 跌日机构接：近20个下跌日的次日超大单净流入合计 z≥1.5（时间序列版机构接刀）
    dip_buy = (gd["J"] * down.shift(1)).rolling(win, min_periods=win).sum()
    out["ts11_dip_jumbo"] = (zscore_self(dip_buy) >= 1.5).fillna(False)
    # TS12 复合过热：5日涨幅z≥1.5 且 chase-z≥1.5
    out["ts12_compound"] = ((zscore_self(gd["C"].pct_change(5, fill_method=None)) >= 1.5) & (cz >= 1.5)).fillna(False)
    # TS13 流入加速：S 的 5 日和 连续 3 日递增 且 处于正区
    s5 = gd["S"].rolling(5, min_periods=5).sum()
    accel = (s5 > s5.shift(1)) & (s5.shift(1) > s5.shift(2)) & (s5.shift(2) > s5.shift(3)) & (s5 > 0)
    out["ts13_accel"] = accel.fillna(False)
    # TS14 涨跌日强度差：（涨日次日散户流入 − 跌日次日散户流入）20日合计 z≥1.5
    down_chase = (gd["S"] * down.shift(1)).rolling(win, min_periods=win).sum()
    out["ts14_asym"] = (zscore_self(chase - down_chase) >= 1.5).fillna(False)
    # TS5 对照（上轮胜出机会信号）
    out["ts5_dip_retail"] = ((z20 >= 1.5) & (r60 <= -0.10)).fillna(False)
    # TS15 主散同向流出：散户z≤-1 且 超大单z≤-1（双杀）
    out["ts15_double_out"] = ((z20 <= -1.0) & (jz20 <= -1.0)).fillna(False)
    return out


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    gs = load_group_series(data)
    fwd = {g: {h: (d["C"].shift(-h) / d["C"] - 1.0) for h in HOLD} for g, d in gs.items()}

    print("== ① TS6 参数稳健性网格（10日持有，单元格=按日聚合均值%/p） ==")
    for z_th in (1.0, 1.5, 2.0):
        row = []
        for win in (10, 20, 40):
            sig = {g: build_defs(d, z_th=z_th, win=win)["chase"] for g, d in gs.items()}
            (m, t, p, n, nd), ag, tot = daily_agg_test(sig, fwd, 10)
            row.append(f"z{z_th}/w{win}: {m:+.1f}% p={p:.3f}(n={n})" if not np.isnan(p) else f"z{z_th}/w{win}: 样本不足")
        print("  " + " | ".join(row))
    print("  持有期敏感性（z1.5/w20）：", end=" ")
    for h in HOLD:
        sig = {g: build_defs(d)["chase"] for g, d in gs.items()}
        (m, t, p, n, nd), ag, tot = daily_agg_test(sig, fwd, h)
        print(f"{h}日:{m:+.1f}%/p={p:.3f}", end="  ")
    print()

    print("\n== ② 新定义族（持有 10 日；★=p<0.01 或一致≥7/8） ==")
    winners = {}
    for g, d in gs.items():
        pass
    names = list(build_defs(next(iter(gs.values()))).keys())
    for name in names:
        sig = {g: build_defs(d)[name] for g, d in gs.items()}
        (m, t, p, n, nd), ag, tot = daily_agg_test(sig, fwd, 10)
        (m20, t20, p20, n20, nd20), ag20, tot20 = daily_agg_test(sig, fwd, 20)
        if np.isnan(p):
            print(f"  {name}: 样本不足(n={n})")
            continue
        star = "★" if (p < 0.01 or ag >= 7) else " "
        print(f" {star}{name}: 10日 {m:+.2f}% p={p:.3f} 一致{ag}/{tot} | 20日 {m20:+.2f}% p={p20:.3f}")
        winners[name] = sig
    return 0


if __name__ == "__main__":
    sys.exit(main())
