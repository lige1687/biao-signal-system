#!/usr/bin/env python3
"""散户情绪·时间序列语义组合回测（聚焦板块版，预注册见
docs/experiments/retail-sentiment-ts-2026-09-05.md）。

与上轮横截面口径正交：各板块跟自身历史比（120 日基准窗 z-score /
分位），定义族 TS1-TS7；板块=用户指定 8 组（红利以银行+公用事业拼组）。

用法：PYTHONPATH=src python3 scripts/retail_sentiment_ts_backtest.py
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

CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))

BOARDS = {
    "通信": ["BK1215"], "半导体": ["BK1036"], "化学制药": ["BK0465"],
    "生物制品": ["BK1044"], "白酒": ["BK1277"], "红利组(近似)": ["BK1283", "BK0427"],
    "有色金属": ["BK0478"], "电池": ["BK1033"],
}
HOLD = (5, 10, 20)
BASE_WIN = 120  # 自身基准窗
WARMUP = 60


def zscore_self(s: pd.Series, win: int = BASE_WIN) -> pd.Series:
    mu = s.rolling(win, min_periods=win).mean().shift(1)
    sd = s.rolling(win, min_periods=win).std().shift(1)
    return (s - mu) / sd.replace(0, np.nan)


def pct_self(s: pd.Series, win: int = 250, q: float = 0.9) -> pd.Series:
    roll = s.rolling(win, min_periods=BASE_WIN)
    return s >= roll.quantile(q).shift(1)


def build_definitions(close: pd.DataFrame, flows: dict, mv: dict) -> dict[str, dict[str, pd.Series]]:
    """{定义名: {板块组名: bool Series}}（红利组内多代码取均值序列）。"""
    out: dict[str, dict[str, pd.Series]] = {f"TS{i}": {} for i in range(1, 8)}
    for gname, codes in BOARDS.items():
        S_list, close_list, ret60_list = [], [], []
        for c in codes:
            if c not in close.columns:
                continue
            s = close[c]
            close_list.append(s)
            ret60_list.append(s.pct_change(60, fill_method=None))
            pts = flows.get(c) or []
            rec = {}
            for p in pts:
                d = pd.to_datetime(p["date"])
                if d in s.index and p.get("small_yi") is not None and mv.get(c):
                    mv_t = mv[c] * float(s.loc[d]) / float(s.dropna().iloc[-1])
                    if mv_t > 0:
                        rec[d] = p["small_yi"] / mv_t
            S_list.append(pd.Series(rec).sort_index().reindex(s.index))
        if not S_list:
            continue
        S = pd.concat(S_list, axis=1).mean(axis=1)
        c_series = pd.concat(close_list, axis=1).mean(axis=1)
        r60 = pd.concat(ret60_list, axis=1).mean(axis=1)
        S20 = S.rolling(20, min_periods=20).mean()
        z = zscore_self(S20)
        # TS1 高温
        out["TS1"][gname] = (z >= 1.5).fillna(False)
        # TS2 持续涌入：连续>=5日 S>0 且期间累计S在自身P80+
        pos = (S > 0).astype(int)
        streak = pos.groupby((pos != pos.shift()).cumsum()).cumsum()
        cum20 = S.rolling(20, min_periods=20).sum()
        cum_rank_ok = cum20 >= cum20.rolling(250, min_periods=BASE_WIN).quantile(0.8).shift(1)
        out["TS2"][gname] = ((streak >= 5) & cum_rank_ok.fillna(False)).fillna(False)
        # TS3 累计极值
        out["TS3"][gname] = pct_self(cum20).fillna(False)
        # TS4 追高型 / TS5 抄底型
        hot = (z >= 1.5)
        out["TS4"][gname] = (hot & (r60 >= 0.15)).fillna(False)
        out["TS5"][gname] = (hot & (r60 <= -0.10)).fillna(False)
        # TS6 追涨日强度：上涨日次日小单净流入合计 z
        up_day = (c_series.pct_change(fill_method=None) > 0).shift(1)
        chase = (S * up_day).rolling(20, min_periods=20).sum()
        out["TS6"][gname] = (zscore_self(chase) >= 1.5).fillna(False)
        # TS7 冰点急升
        z5ago = z.shift(5)
        out["TS7"][gname] = ((z >= 1.0) & (z5ago < 0)).fillna(False)
    return out


def main() -> int:
    data = rb.load_panels(str(CACHE / "tx_sector_flow_pilot.json"))
    close, flows, mv = data["close"], data["flows"], data["mv_today"]
    defs = build_definitions(close, flows, mv)

    # 前向收益（每板块组自身）
    fwd_cache: dict[str, dict[int, pd.Series]] = {}
    for gname, codes in BOARDS.items():
        cs = [close[c] for c in codes if c in close.columns]
        if not cs:
            continue
        idx_series = pd.concat(cs, axis=1).mean(axis=1)
        fwd_cache[gname] = {h: (idx_series.shift(-h) / idx_series - 1.0) for h in HOLD}

    print("定义 | 触发数 | 池化胜率(基准) | 10日均收(基准) | 分板块方向一致性")
    results = []
    for dname, groups in defs.items():
        pool = {h: {"trig": [], "base": []} for h in HOLD}
        dir_ok, dir_all = 0, 0
        for gname, sig in groups.items():
            if gname not in fwd_cache:
                continue
            sig = sig.iloc[WARMUP:]
            n_trig = int(sig.sum())
            if n_trig == 0:
                dir_all += 1
                continue
            dir_all += 1
            # 基准=该组同窗口全部日
            for h in HOLD:
                f = fwd_cache[gname][h].reindex(sig.index)
                t = f[sig.fillna(False)].dropna()
                b = f.iloc[WARMUP:].dropna()
                if len(t):
                    pool[h]["trig"].extend(t.tolist())
                if len(b):
                    pool[h]["base"].extend(b.tolist())
            # 方向一致性按 10 日
            f10 = fwd_cache[gname][10].reindex(sig.index)
            t10 = f10[sig.fillna(False)].dropna()
            b10 = f10.iloc[WARMUP:].dropna()
            if len(t10) >= 3:
                # 方向一致 = 触发后均收益差于该组基准（散户情绪高→更弱）
                if t10.mean() < b10.mean():
                    dir_ok += 1
        n_all_trig = sum(int(s.iloc[WARMUP:].sum()) for s in groups.values() if len(s) > WARMUP)
        if not pool[10]["trig"]:
            print(f"{dname} | 0 | - | - | -")
            continue
        t10 = np.array(pool[10]["trig"]); b10 = np.array(pool[10]["base"])
        t20 = np.array(pool[20]["trig"]); b20 = np.array(pool[20]["base"])
        line = (f"{dname} | {n_all_trig} | 跌{(t10 < 0).mean()*100:.0f}%（基{(b10 < 0).mean()*100:.0f}%）"
                f" | {t10.mean()*100:+.2f}%（基{b10.mean()*100:+.2f}%）"
                f" | 20日跌{(t20 < 0).mean()*100:.0f}%（基{(b20 < 0).mean()*100:.0f}%）"
                f" | 同向{dir_ok}/{dir_all}")
        print(line)
        results.append((dname, n_all_trig, t10, b10))
    # 触发日聚合 t 检验对池化第一名做（简单版：逐触发差 vs 0）
    print("\n说明：基准=该板块组同期无条件表现；判定标准见预注册 §4（跌概率差≥8pp + 按日聚合显著 + 6/8 方向一致）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
