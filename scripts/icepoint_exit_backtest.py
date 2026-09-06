#!/usr/bin/env python3
"""冰点机会信号·退出策略回测（2026-09-06）。

对全板块 154 次 C4 触发（§10 口径），逐日模拟以下退出规则的
平均收益/胜率/持有天数/峰值捕获率（实现收益 ÷ 60日内最大涨幅）：
- 固定持有：10/15/20 日（基准）
- 移动止盈：峰值回撤 5%/8%/10% 即走（至少持有 2 日）
- 目标位：+8%/+12% 即走
- 信号消失：散户 20 日 z 跌破 0 即走（至少 5 日）
- 复合：最长 20 日 + 峰回 8%
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

MAX_HOLD = 60


def main() -> int:
    data = rb.load_panels(str(rb.CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    cn = cn_mood_regime(close, flows)
    boards = [c for c in close.columns if (data["level"].get(c) or 3) <= 2]

    events = []
    z_paths = {}
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
        z_paths[code] = z
        r60 = C.pct_change(60, fill_method=None)
        sig = ((z >= 1.5) & (r60 <= -0.10)).fillna(False)
        for t in sig.index[60:][sig.iloc[60:].fillna(False)]:
            if regime_at(cn, t) == "冷":
                events.append((code, t, C.index.get_loc(t), float(C.loc[t])))

    print(f"C4 触发事件：{len(events)} 个")

    def sim(exit_fn) -> dict:
        rets, holds, captures = [], [], []
        for code, t, i0, base in events:
            C = close[code]
            seg = C.iloc[i0 + 1:i0 + 1 + MAX_HOLD].dropna()
            if len(seg) < 5:
                continue
            exit_i = exit_fn(code, seg, base, t)
            px = float(seg.iloc[exit_i]) if exit_i < len(seg) else float(seg.iloc[-1])
            mfe = float(seg.max()) / base - 1
            rets.append(px / base - 1)
            holds.append(exit_i + 1 if exit_i < len(seg) else len(seg))
            captures.append((px / base - 1) / mfe if mfe > 0.005 else np.nan)
        r = np.array(rets)
        return {"n": len(r), "ret": r.mean() * 100, "win": (r > 0).mean() * 100,
                "days": np.mean(holds),
                "capture": np.nanmean(captures) * 100 if captures else np.nan}

    def fixed(n: int):
        return lambda code, seg, base, t: min(n - 1, len(seg) - 1)

    def trail(dd: float):
        def f(code, seg, base, t):
            peak = base
            for i, px in enumerate(seg.values):
                peak = max(peak, px)
                if i >= 1 and px / peak - 1 <= -dd:
                    return i
            return len(seg) - 1
        return f

    def target(tp: float):
        def f(code, seg, base, t):
            for i, px in enumerate(seg.values):
                if px / base - 1 >= tp:
                    return i
            return len(seg) - 1
        return f

    def z_gone(min_days: int = 5):
        def f(code, seg, base, t):
            z = z_paths.get(code)
            for i, dt in enumerate(seg.index):
                if i + 1 >= min_days and z is not None:
                    zv = z.get(dt)
                    if zv is not None and not pd.isna(zv) and zv < 0:
                        return i
            return min(19, len(seg) - 1)
        return f

    def combo(max_d: int = 20, dd: float = 0.08):
        def f(code, seg, base, t):
            peak = base
            for i, px in enumerate(seg.values):
                peak = max(peak, px)
                if i >= 1 and (px / peak - 1 <= -dd or i + 1 >= max_d):
                    return i
            return len(seg) - 1
        return f

    rules = [
        ("固定持有10日", fixed(10)), ("固定持有15日", fixed(15)), ("固定持有20日", fixed(20)),
        ("移动止盈 峰回5%", trail(0.05)), ("移动止盈 峰回8%", trail(0.08)),
        ("移动止盈 峰回10%", trail(0.10)),
        ("目标位 +8%", target(0.08)), ("目标位 +12%", target(0.12)),
        ("信号消失(z<0)即走", z_gone()),
        ("复合 最长20日+峰回8%", combo()),
    ]
    print(f"{'退出规则':18s} {'n':>4s} {'均收益':>8s} {'胜率':>6s} {'均持有':>6s} 峰值捕获")
    for name, fn in rules:
        s = sim(fn)
        cap = f"{s['capture']:.0f}%" if s["capture"] == s["capture"] else "-"
        print(f"{name:20s} {s['n']:4d} {s['ret']:+7.2f}% {s['win']:5.0f}% {s['days']:5.1f}日 {cap}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
