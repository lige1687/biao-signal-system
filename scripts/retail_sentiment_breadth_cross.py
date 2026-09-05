#!/usr/bin/env python3
"""情绪 × 宽度 交叉轮（2026-09-06）。

用户假设：单独证伪的情绪定义，与宽度（板块 b50/全市场宽度）结合可能复活。
宽度数据：sector_trend_history 每板块 b50（板块内成分股站上 MA50 比例）。

八组（预注册语义，全部板块池化+按日聚合，p<0.01 且方向占比超随机上界才采信）：
1. TS6追涨 × 全市场宽度低（普弱中追涨）
2. 接刀冰点(横截面) × 板块宽度背离（价格60日新低 但 b50 高于其60日低点+5pp=卖压衰竭）
3. 散户过热(横截面) × 板块宽度走弱（b50 < 自身20日均值-5pp=外热内冷顶部背离）
4. 出清反弹V1 × 板块b50回升（b50 5日升≥10pp）
5. C4冰点抄底 × 板块宽度背离
6. C4 × 宽度冲刷（b50 20日均<25 且 5日升≥15pp）
7. 宽度冲刷 单信号（对照组）
8. C4 基准（对照复验）
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
from market_mood_backtest import cn_mood_regime, regime_at

WARMUP, H = 60, 10


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv, b50 = data["close"], data["flows"], data["mv_today"], data["b50"]
    cn = cn_mood_regime(close, flows)
    boards = [c for c in close.columns if (data["level"].get(c) or 3) <= 2]

    # 全市场宽度 = 161 板块 b50 中位数
    mkt_breadth = b50[boards].median(axis=1)

    def sigs(code):
        C = close[code]
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
        up = C.pct_change(fill_method=None) > 0
        chase_z = zscore_self((S * up.shift(1)).rolling(20, min_periods=20).sum())
        down = C.pct_change(fill_method=None) < 0
        jz = zscore_self(
            pd.Series({t: 0.0 for t in C.index})  # 占位
        ) if False else None
        # 超大单强度
        recJ = {}
        for p in pts:
            d = pd.to_datetime(p["date"])
            if d in C.index and mv.get(code):
                jv = p.get("jumbo_yi") if "jumbo_yi" in p else p.get("super_large_yi")
                if jv is not None:
                    mv_t = mv[code] * float(C.loc[d]) / float(C.dropna().iloc[-1])
                    if mv_t > 0:
                        recJ[d] = jv / mv_t
        J = pd.Series(recJ).sort_index().reindex(C.index)
        dip_buy_z = zscore_self((J * down.shift(1)).rolling(20, min_periods=20).sum())
        r60 = C.pct_change(60, fill_method=None)
        b = b50[code] if code in b50.columns else None
        return C, S, z20, chase_z, dip_buy_z, r60, b

    def run(name, sig_fn):
        rows, per_board = [], []
        for code in boards:
            C, S, z20, chase_z, dip_buy_z, r60, b = sigs(code)
            if b is None:
                continue
            sig = sig_fn(C, z20, chase_z, dip_buy_z, r60, b, code)
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
            print(f"  {name}: 样本不足(n={len(rows)})")
            return
        ser = pd.Series({d: v for d, v in rows}).sort_index()
        daily = ser.groupby(level=0).mean()
        t = float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))))
        effs = np.array(per_board)
        pos = (effs > 0).mean() * 100
        star = "★" if _norm_p(t) < 0.01 and pos > 60 else " "
        print(f" {star}{name}: n={len(rows)}/{len(daily)}日 {daily.mean()*100:+.2f}% p={_norm_p(t):.4f} 板块正占比{pos:.0f}%")

    print("== 情绪 × 宽度 交叉轮（10日超额，板块池化161，★=p<0.01且正占比>60%） ==")

    def f_ts6_mktlow(C, z20, chase_z, dip_buy_z, r60, b, code):
        m = mkt_breadth.reindex(C.index)
        return ((chase_z >= 1.5) & (m < m.rolling(60, min_periods=60).median().shift(1))).fillna(False)

    def f_knife_div(C, z20, chase_z, dip_buy_z, r60, b, code):
        # 接刀（跌日机构接 z 高）× 宽度底背离：价格60日新低 但 b50 高于其60日低点+5
        price_low = C <= C.rolling(60, min_periods=60).min().shift(1) * 1.001
        b_low = b.rolling(60, min_periods=60).min()
        div = (C <= C.rolling(60).min()) & (b > b_low + 5)
        return ((dip_buy_z >= 1.0) & div.fillna(False)).fillna(False)

    def f_hot_weak_breadth(C, z20, chase_z, dip_buy_z, r60, b, code):
        # 散户情绪z高 × 宽度走弱（b50 低于自身20日均值5pp）
        weak_b = (b < b.rolling(20, min_periods=20).mean() - 5).fillna(False)
        return ((z20 >= 1.0) & weak_b).fillna(False)

    def f_v1_breadth_up(C, z20, chase_z, dip_buy_z, r60, b, code):
        # 出清V1（跌日机构接）× 板块b50 5日升≥10pp
        up_b = (b.diff(5) >= 10).fillna(False)
        return ((dip_buy_z >= 1.5) & up_b).fillna(False)

    def _c4(z20, r60):
        return (z20 >= 1.5) & (r60 <= -0.10)

    def f_c4_div(C, z20, chase_z, dip_buy_z, r60, b, code):
        b_low = b.rolling(60, min_periods=60).min()
        div = (b > b_low + 5).fillna(False)
        base = _c4(z20, r60).fillna(False)
        out = base & div
        # CN 冰点过滤
        return pd.Series([bool(v) and regime_at(cn, t) == "冷" for t, v in out.items()], index=out.index)

    def f_c4_thrust(C, z20, chase_z, dip_buy_z, r60, b, code):
        thrust = ((b.rolling(20, min_periods=20).mean() < 25) & (b.diff(5) >= 15)).fillna(False)
        base = _c4(z20, r60).fillna(False) & thrust
        return pd.Series([bool(v) and regime_at(cn, t) == "冷" for t, v in base.items()], index=base.index)

    def f_thrust(C, z20, chase_z, dip_buy_z, r60, b, code):
        return ((b.rolling(20, min_periods=20).mean() < 25) & (b.diff(5) >= 15)).fillna(False)

    def f_c4(C, z20, chase_z, dip_buy_z, r60, b, code):
        base = _c4(z20, r60).fillna(False)
        return pd.Series([bool(v) and regime_at(cn, t) == "冷" for t, v in base.items()], index=base.index)

    run("1 TS6追涨×全市场宽度低", f_ts6_mktlow)
    run("2 接刀×板块宽度底背离", f_knife_div)
    run("3 散户热×板块宽度走弱", f_hot_weak_breadth)
    run("4 出清V1×板块b50回升", f_v1_breadth_up)
    run("5 C4冰点抄底×宽度底背离", f_c4_div)
    run("6 C4×宽度冲刷", f_c4_thrust)
    run("7 宽度冲刷 单信号(对照)", f_thrust)
    run("8 C4基准(对照复验)", f_c4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
