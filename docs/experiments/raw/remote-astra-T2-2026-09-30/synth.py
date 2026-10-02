"""人工合成特征表（仅用于语义/实现核验，不是行情）。

SMA 用递推 SMA_t = SMA_{t-1} + (close_t - lag_t)/N，因此 SMA 方向与
“收盘 vs 抵扣价”严格一致（规格 §4.2）；EMA 用 alpha=2/(N+1) 递推。
clock / weekly 为注入值（生产代码里由 clock_series / weekly_env_series 计算）。
"""
from __future__ import annotations

import math

import pandas as pd

ALPHA = {20: 2 / 21, 60: 2 / 61, 120: 2 / 121}
NAN = float("nan")


def make(days: list[dict], init: dict, start: str = "2024-03-04") -> pd.DataFrame:
    s = {n: init[f"sma{n}"] for n in (20, 60, 120)}
    e = {n: init[f"ema{n}"] for n in (20, 60, 120)}
    rows = []
    for d in days:
        if d.get("missing"):
            row = {k: NAN for k in ("open", "high", "low", "close", "volume")}
            for n in (20, 60, 120):
                row[f"sma{n}"] = row[f"ema{n}"] = row[f"close_lag{n}"] = NAN
            row.update(clock=0, weekly=None, signal_color="unknown")
            rows.append(row)
            continue
        row = dict(open=d.get("o", d["c"]), high=d["h"], low=d["l"], close=d["c"],
                   volume=d.get("v", 1e6))
        for n in (20, 60, 120):
            lag = d[f"lag{n}"]
            s[n] += (d["c"] - lag) / n
            e[n] += ALPHA[n] * (d["c"] - e[n])
            row[f"sma{n}"], row[f"ema{n}"], row[f"close_lag{n}"] = s[n], e[n], lag
        row["clock"], row["weekly"] = d.get("clock", 2), d.get("weekly", True)
        c, e20, l20 = row["close"], row["ema20"], row["close_lag20"]
        row["signal_color"] = ("green" if c > e20 and c > l20
                               else "black" if c < e20 and c < l20 else "gray")
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.index = pd.bdate_range(start, periods=len(frame))
    return frame


def rows_of(frame: pd.DataFrame) -> list[dict]:
    out = []
    for ts, r in frame.iterrows():
        row = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
        row["date"] = ts.date().isoformat()
        out.append(row)
    return out


def table(frame: pd.DataFrame, groups=(20, 60)) -> list[dict]:
    """案例说明用的逐日表（保留 3 位小数）。"""
    cols = ["low", "close", "signal_color", "clock", "weekly"]
    for g in groups:
        cols += [f"sma{g}", f"ema{g}", f"close_lag{g}"]
    out = []
    for ts, r in frame[cols].iterrows():
        rec = {"date": ts.date().isoformat()}
        for k, v in r.items():
            rec[k] = round(v, 3) if isinstance(v, float) and not math.isnan(v) else (
                None if isinstance(v, float) else v)
        out.append(rec)
    return out
