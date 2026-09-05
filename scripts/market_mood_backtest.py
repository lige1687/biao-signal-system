#!/usr/bin/env python3
"""大盘情绪环境 × 板块信号 条件胜率矩阵（research_proxy，2026-09-05）。

问题：同一板块信号（出清反弹/散户过热/接刀冰点），在不同的市场情绪环境
下胜率是否系统性不同？——回答"什么时候该更重视哪种信号"（用户 2026-09-05
提出的语义组合方向）。

环境定义（预注册，全部纯本地数据）：
- CN 情绪（热/冷，三票多数）：
  ① 两融余额 20 日变化率符号（散户杠杆，东财 datacenter）；
  ② 全A散户小单净流入 20 日合计符号（腾讯个股聚合加总，同 tx 试点源）；
  ③ 全A等权指数 20 日收益符号（sector_trend_history 合成）。
  三票 ≥2 正 = 热，≥2 负 = 冷，否则中性（并入相邻档或剔除——预注册：中性剔除）。
- US 情绪（宽/窄）：SP500 成分股站上 MA50 比例（breadth_50，lab.db
  1986 年起）的 60 日滚动分位 > 0.5 = 宽，否则窄。

信号集合：出清反弹 V1 / V2（capitulation_rebound_backtest 同定义）、
diverge 散户过热（横截面 P90）/ 接刀冰点（横截面 P10，20 日口径）。

统计：各 (信号 × CN环境 × US环境) 组合的前向 10/20 日——上涨概率、
平均收益、跑赢全板块基准概率、样本数。样本 < 10 的格子标"样本不足"。

用法：PYTHONPATH=src python3 scripts/market_mood_backtest.py \
      [--flows-file ~/.lei_signal_lab/cache/tx_sector_flow_pilot.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import retail_mania_backtest as rb  # noqa: E402
from capitulation_rebound_backtest import build_signal  # noqa: E402

CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))


def cn_mood_regime(close: pd.DataFrame, flows: dict) -> pd.Series | None:
    """全A情绪：两融变化 + 全A小单净流入 + 等权指数动能，三票多数（+1热/-1冷/0中性）。"""
    try:
        from lei_signal.fundamentals import sources
        hist = sources.fetch_margin_history(lookback_days=900)
        margin = pd.Series({pd.to_datetime(d): v.get("rzye_yi") for d, v in hist.items()
                            if v.get("rzye_yi") is not None}).sort_index()
        v1 = np.sign(margin.pct_change(20))
    except Exception:
        return None
    # 全A小单净流入 20 日合计（腾讯/东财 flows 全板块加总）
    rows = {}
    for code, pts in flows.items():
        for p in pts:
            rows.setdefault(pd.to_datetime(p["date"]), []).append(p.get("small_yi") or 0.0)
    small_all = pd.Series({k: sum(v) for k, v in rows.items()}).sort_index()
    roll = small_all.rolling(20, min_periods=20).sum()
    v2 = np.sign(roll)
    # 全A等权指数 20 日收益（板块等权的等权≈全A近似）
    idx = (1 + close.pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod()
    v3 = np.sign(idx.pct_change(20))
    votes = pd.DataFrame({"m": v1, "s": v2, "g": v3}).dropna()
    score = np.sign(votes.sum(axis=1))
    return score


def us_breadth_regime() -> pd.Series | None:
    """美股环境：SP500 breadth_50 的 60 日滚动分位（>0.5=宽）。返回字符串值宽/窄。"""
    db = Path.home() / ".lei_signal_lab" / "lab.db"
    if not db.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT as_of, breadth_50 FROM market_breadth_snapshots "
            "WHERE market_id='SP500' AND breadth_50 IS NOT NULL ORDER BY as_of"
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return None
    if len(rows) < 120:
        return None
    s = pd.Series({pd.to_datetime(d): v for d, v in rows}).sort_index()
    pct = s.rolling(60, min_periods=60).rank(pct=True)
    out = pd.Series("窄", index=s.index)
    out[pct > 0.5] = "宽"
    out[pct.isna()] = "?"
    return out


def regime_at(reg: pd.Series | None, t) -> str:
    if reg is None:
        return "?"
    k = reg.index.searchsorted(t, side="right") - 1
    if k < 0:
        return "?"
    v = reg.iloc[k]
    return {1.0: "热", -1.0: "冷", 0.0: "中"}.get(v, str(v))


def heat_signals(data: dict, window: int = 20, pct: float = 0.10) -> dict[str, pd.DataFrame]:
    """diverge 口径的过热/冰点触发面板（逐日状态，不去重——环境分层看状态而非事件）。"""
    close = data["close"]
    series = rb.build_metric_series(data["flows"], close, data["mv_today"])
    panel = pd.DataFrame(series["diverge"]).reindex(close.index).sort_index()
    rolled = panel.rolling(window, min_periods=window).mean()
    valid_day = rolled.notna().sum(axis=1) >= 100
    rolled = rolled.where(valid_day, other=np.nan)
    rank = rolled.rank(axis=1, pct=True)
    hot = (rank >= 1 - pct).fillna(False).astype(bool)
    cold = (rank <= pct).fillna(False).astype(bool)
    return {"散户过热(diverge)": hot, "接刀冰点(diverge)": cold}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flows-file", default=str(CACHE / "tx_sector_flow_pilot.json"))
    args = ap.parse_args()

    data = rb.load_panels(args.flows_file)
    close = data["close"]
    print(f"面板: {close.shape[0]} 日 × {close.shape[1]} 板块")

    cn = cn_mood_regime(close, data["flows"])
    us = us_breadth_regime()
    print("CN 情绪环境:", "OK" if cn is not None else "不可用",
          "| 分布:", cn.value_counts().to_dict() if cn is not None else "-")
    print("US 宽度环境:", "OK" if us is not None else "不可用",
          "| 宽日占比:", f"{(us == '宽').mean():.0%}" if us is not None else "-")

    bench = close.pct_change(fill_method=None).mean(axis=1)

    signals: dict[str, pd.DataFrame] = {}
    for ver in ("v1", "v2"):
        trig, _ = build_signal(data, version=ver)
        signals[f"出清反弹{ver}"] = trig
    signals.update(heat_signals(data))

    for name, trig in signals.items():
        print(f"\n== {name} ==")
        for h in (10, 20):
            fwd = (close.shift(-h) / close - 1.0).iloc[:-h]
            fwd = fwd.where(fwd.notna() & (fwd != 0))
            bench_fwd = (1 + bench).rolling(h).apply(lambda x: np.prod(x), raw=True)
            bench_fwd = bench_fwd.shift(-h) - 1.0  # t 日起未来 h 日基准收益
            print(f"  -- 前向 {h} 日 --")
            cells: dict[tuple, list[tuple[float, float]]] = {}
            for t in trig.index.intersection(fwd.index):
                cn_s, us_s = regime_at(cn, t), regime_at(us, t)
                if cn_s not in ("热", "冷") or us_s not in ("宽", "窄"):
                    continue
                f = fwd.loc[t]
                m = trig.loc[t] & f.notna()
                if not m.any():
                    continue
                b = bench_fwd.loc[t] if t in bench_fwd.index else np.nan
                for code in f[m].index:
                    cells.setdefault((cn_s, us_s), []).append(
                        (float(f[code]), float(f[code] - b) if not pd.isna(b) else np.nan))
            for cn_state in ("热", "冷"):
                for us_state in ("宽", "窄"):
                    vals = cells.get((cn_state, us_state)) or []
                    if len(vals) < 10:
                        print(f"    CN{cn_state}×US{us_state}: 样本不足(n={len(vals)})")
                        continue
                    rets = np.array([v[0] for v in vals])
                    excs = np.array([v[1] for v in vals])
                    excs = excs[~np.isnan(excs)]
                    line = (f"    CN{cn_state}×US{us_state}: n={len(rets)} "
                            f"胜率{(rets > 0).mean() * 100:.0f}% "
                            f"均收{rets.mean() * 100:+.2f}%")
                    if len(excs):
                        line += f" 超额均值{excs.mean() * 100:+.2f}% 超额胜率{(excs > 0).mean() * 100:.0f}%"
                    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
