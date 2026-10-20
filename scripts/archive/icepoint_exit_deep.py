#!/usr/bin/env python3
"""冰点机会·退出规则深化（2026-09-06 第二轮）。

1. 时间衰减曲线：触发后第 1-40 日的逐日累计收益与胜率（收益峰在哪天）；
2. 新退出规则：环境退出（CN情绪转热即走）/警报退出（触发强热即走）/
   分批退出（半仓10日+半仓20日）/波动自适应；
3. 稳健性：剔除单一极端板块、7月事件 vs 其他时段分段、入场价敏感
   （触发日收盘 vs 次日"开盘"近似）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import retail_mania_backtest as rb  # noqa: E402
from retail_sentiment_ts_backtest import zscore_self
from market_mood_backtest import cn_mood_regime, regime_at

MAX_HOLD = 40


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    cn = cn_mood_regime(close, flows)
    boards = [c for c in close.columns if (data["level"].get(c) or 3) <= 2]

    events = []
    for code in boards:
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
        z = zscore_self(S.rolling(20, min_periods=20).mean())
        r60 = C.pct_change(60, fill_method=None)
        sig = ((z >= 1.5) & (r60 <= -0.10)).fillna(False)
        for t in sig.index[60:][sig.iloc[60:].fillna(False)]:
            if regime_at(cn, t) == "冷":
                events.append((code, t, C.index.get_loc(t), float(C.loc[t])))
    print(f"事件 {len(events)} 个（{min(e[1] for e in events).date()} ~ {max(e[1] for e in events).date()}）")

    # ── 1. 时间衰减曲线 ──
    print("\n== ① 时间衰减曲线（累计收益% / 胜率%） ==")
    line_r, line_w = [], []
    for h in range(2, MAX_HOLD + 1, 2):
        rets = []
        for code, t, i0, base in events:
            C = close[code]
            if i0 + h < len(C):
                v = float(C.iloc[i0 + h]) / base - 1
                if not pd.isna(v):
                    rets.append(v)
        if rets:
            r = np.array(rets)
            line_r.append(f"{h}d:{r.mean()*100:+.1f}/{(r>0).mean()*100:.0f}%")
    print("  " + "  ".join(line_r))

    # ── 2. 新退出规则 ──
    def sim(exit_fn):
        rets, holds = [], []
        for code, t, i0, base in events:
            C = close[code]
            seg = C.iloc[i0 + 1:i0 + 1 + MAX_HOLD].dropna()
            if len(seg) < 5:
                continue
            e = exit_fn(code, seg, base, t)
            px = float(seg.iloc[e]) if e < len(seg) else float(seg.iloc[-1])
            rets.append(px / base - 1)
            holds.append(min(e + 1, len(seg)))
        r = np.array(rets)
        return r.mean() * 100, (r > 0).mean() * 100, np.mean(holds)

    def env_exit(max_d=25):
        """CN 情绪转热即走（恐慌修复完成）或到最长天数。"""
        def f(code, seg, base, t):
            for i, dt in enumerate(seg.index):
                if i >= 2 and regime_at(cn, dt) == "热":
                    return i
            return min(max_d - 1, len(seg) - 1)
        return f

    def batch_exit():
        """分批：一半第10日、一半第20日。"""
        def f(code, seg, base, t):
            return min(9, len(seg) - 1)  # 返回一半仓位的天数；另一半模拟时翻倍难，此处近似为均值口径
        return f

    print("\n== ② 新退出规则 ==")
    for name, fn in (
        ("环境退出（CN转热即走,≤25日）", env_exit()),
        ("固定15日（对照）", lambda c, s, b, t: min(14, len(s) - 1)),
    ):
        ret, win, days = sim(fn)
        print(f"  {name:26s} {ret:+.2f}% 胜率{win:.0f}% 持有{days:.1f}日")

    # 分批近似：直接算两个固定的均值
    r10 = np.mean([float(close[c].iloc[i0 + 10]) / b - 1 for c, t, i0, b in events
                   if i0 + 10 < len(close[c])])
    r20 = np.mean([float(close[c].iloc[i0 + 20]) / b - 1 for c, t, i0, b in events
                   if i0 + 20 < len(close[c])])
    print(f"  分批（半10日+半20日）        {(r10 + r20) / 2 * 100:+.2f}%（近似）")

    # ── 3. 稳健性 ──
    print("\n== ③ 稳健性 ==")
    # 剔除贡献最大的单一板块
    by_board = {}
    for code, t, i0, base in events:
        C = close[code]
        if i0 + 15 < len(C):
            by_board.setdefault(code, []).append(float(C.iloc[i0 + 15]) / base - 1)
    means = {k: np.mean(v) for k, v in by_board.items()}
    top = max(means, key=means.get)
    rest = [x for k, v in by_board.items() if k != top for x in v]
    print(f"  剔除最强板块({top}, {len(by_board[top])}例)后：均值{np.mean(rest)*100:+.2f}% 胜率{np.mean([x>0 for x in rest])*100:.0f}%")
    # 按时段分段（7月中 vs 7月底8月）
    early = [e for e in events if str(e[1].date()) <= "2026-07-22"]
    late = [e for e in events if str(e[1].date()) > "2026-07-22"]
    for label, evs in (("前半段(7-15~22)", early), ("后半段(7-23之后)", late)):
        rets = [float(close[c].iloc[i0 + 15]) / b - 1 for c, t, i0, b in evs
                if i0 + 15 < len(close[c])]
        if rets:
            print(f"  {label}: n={len(rets)} 均值{np.mean(rets)*100:+.2f}% 胜率{np.mean([x>0 for x in rets])*100:.0f}%")
    # 入场价敏感：次日收盘入场（晚一天）
    rets_d1 = []
    for code, t, i0, base in events:
        C = close[code]
        if i0 + 1 < len(C) and i0 + 16 < len(C):
            b1 = float(C.iloc[i0 + 1])
            rets_d1.append(float(C.iloc[i0 + 16]) / b1 - 1)
    print(f"  次日收盘入场+15日：均值{np.mean(rets_d1)*100:+.2f}% 胜率{np.mean([x>0 for x in rets_d1])*100:.0f}%（n={len(rets_d1)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
