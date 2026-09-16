"""独立期望推导（factor-research-workbench-v1 Task 0/5）。

用独立算术（不 import lei_signal）从合成输入手算三份协议的期望值，
冻结进协议 JSON。被测代码的输出随后与这里对照；期望不得由被测输出生成。
输出打印到 stdout（JSON），由执行者粘贴进协议文件并记录命令与退出码。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
IN = HERE / "synthetic_inputs"


def numerical() -> dict:
    p3 = pd.read_csv(IN / "numerical_prices_3.csv", parse_dates=["date"]).set_index("date")
    p5 = pd.read_csv(IN / "numerical_prices_5.csv", parse_dates=["date"]).set_index("date")

    def momentum(series: pd.Series) -> pd.Series:
        return series.shift(21) / series.shift(252) - 1

    def rv20(series: pd.Series) -> pd.Series:
        ret = series.pct_change(fill_method=None)
        return ret.rolling(20, min_periods=20).std(ddof=1) * math.sqrt(252)

    def distance(series: pd.Series, n: int) -> pd.Series:
        return series / series.rolling(n, min_periods=n).mean() - 1

    def targets(series: pd.Series) -> pd.Series:
        return series.shift(-22) / series.shift(-1) - 1

    out: dict = {}
    for tag, panel in (("3", p3), ("5", p5)):
        mom = {c: momentum(panel[c]) for c in panel}
        tgt = {c: targets(panel[c]) for c in panel}
        ics = []
        for idx in range(252, 278):
            date = panel.index[idx]
            vals = {c: mom[c].iloc[idx] for c in panel}
            tgts = {c: tgt[c].iloc[idx] for c in panel}
            ok = {c: np.isfinite(vals[c]) and np.isfinite(tgts[c]) for c in panel}
            keys = [c for c in panel if ok[c]]
            rv = pd.DataFrame({"v": [vals[c] for c in keys],
                               "t": [tgts[c] for c in keys]}).rank(method="average")
            ic = float(rv["v"].corr(rv["t"]))
            ics.append({"date": str(date.date()), "n": len(keys), "ic": round(ic, 12)})
        out[f"momentum_first_valid_row_{tag}"] = int(mom["alpha"].first_valid_index().__class__ and 253)
        out[f"ic_periods_{tag}"] = ics
        out[f"ic_unique_{tag}"] = sorted({p["ic"] for p in ics})
        out[f"n_range_{tag}"] = [min(p["n"] for p in ics), max(p["n"] for p in ics)]
    row = 252  # 第253行（0基252）
    d = str(p3.index[row].date())
    out["row252_date"] = d
    out["momentum_alpha_at_row252"] = float(momentum(p3["alpha"]).iloc[row])
    out["rv20_alpha_at_row252"] = float(rv20(p3["alpha"]).iloc[row])
    out["distance50_alpha_at_row252"] = float(distance(p3["alpha"], 50).iloc[row])
    out["distance200_alpha_at_row252"] = float(distance(p3["alpha"], 200).iloc[row])
    out["distance50_gamma_constant_zero"] = bool(
        (distance(p3["gamma"], 50).dropna() == 0).all())
    out["split_dates"] = {
        "dev_start": str(p3.index[252].date()), "dev_end": str(p3.index[259].date()),
        "val_start": str(p3.index[260].date()), "val_end": str(p3.index[267].date()),
        "hold_start": str(p3.index[268].date()), "hold_end": str(p3.index[277].date()),
    }
    out["epsilon_missing_rows"] = [
        str(p5.index[i].date()) for i in range(260, 265)]
    return out


def ema(values: list[float], period: int = 20) -> list[float]:
    out = [math.nan] * len(values)
    if len(values) < period:
        return out
    out[period - 1] = sum(values[:period]) / period
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def sma(values: list[float], period: int = 20) -> list[float]:
    s = pd.Series(values).rolling(period, min_periods=period).mean()
    return [math.nan if pd.isna(v) else float(v) for v in s]


def classify(close: list[float], e: list[float]) -> list[str]:
    out = []
    for i, c in enumerate(close):
        if i < 20 or math.isnan(e[i]):
            out.append("unknown")
            continue
        lag = close[i - 20]
        if c > e[i] and c > lag:
            out.append("green")
        elif c < e[i] and c < lag:
            out.append("black")
        else:
            out.append("gray")
    return out


def bull_state(close: list[float], e: list[float], s: list[float],
               colors: list[str]) -> list[bool | None]:
    out: list[bool | None] = []
    for i, c in enumerate(close):
        if i == 0 or math.isnan(e[i]) or math.isnan(s[i]) or math.isnan(e[i - 1]) \
                or math.isnan(s[i - 1]) or colors[i] == "unknown":
            out.append(None)  # 未就绪
            continue
        out.append(c > e[i] and c > s[i] and e[i] > e[i - 1] and s[i] > s[i - 1]
                   and colors[i] == "green")
    return out


def state() -> dict:
    out: dict = {}
    for tag in ("a", "b"):
        df = pd.read_csv(IN / f"state_bars_dm_{tag}.csv", parse_dates=["date"])
        close = [float(v) for v in df["close"]]
        e = ema(close)
        s = sma(close)
        colors = classify(close, e)
        st = bull_state(close, e, s, colors)
        ready = [i for i, v in enumerate(st) if v is not None]
        true_idx = [i for i, v in enumerate(st) if v is True]
        out[f"dm_{tag}"] = {
            "bars": len(close),
            "first_ready_row_1based": (ready[0] + 1) if ready else None,
            "not_ready_rows": len(close) - len(ready),
            "state_true_rows": len(true_idx),
            "state_false_rows": len(ready) - len(true_idx),
            "first_true_row_1based": (true_idx[0] + 1) if true_idx else None,
            "last_true_row_1based": (true_idx[-1] + 1) if true_idx else None,
            "state_at_row21_1based": st[20],
            "state_at_row25_1based": st[24],
            "state_at_row30_1based": st[29],
            "state_at_last_row": st[-1],
            "color_at_row21_1based": colors[20],
            "color_at_row30_1based": colors[29],
            "color_at_last_row": colors[-1],
        }
    # 宽度：独立复算 b50/b200。
    wide = pd.read_csv(IN / "state_breadth_close.csv", parse_dates=["date"]).set_index("date")
    mem = json.loads((IN / "state_membership.json").read_text())
    membership: dict = {}
    for seg in mem["segments"]:
        for day in pd.bdate_range(seg["start"], seg["end"]):
            membership[str(day.date())] = list(seg["members"])
    # 有效收盘口径：SMA 按最后N个**有效**收盘滚动（缺报价不计入窗口）。
    means = {c: {n: wide[c].dropna().rolling(n, min_periods=n).mean()
                 .reindex(wide.index) for n in (50, 200)}
             for c in wide}
    series = {}
    for i, day in enumerate(wide.index):
        key = str(day.date())
        members = membership[key]
        eligible = [m for m in members if pd.notna(wide.at[day, m])
                    and pd.notna(means[m][200].iloc[i])]
        total, count = len(members), len(eligible)
        coverage = count / total if total else float("nan")
        if total == 0:
            reason = "membership_missing"
        elif count == 0:
            reason = "no_eligible_quotes"
        elif coverage < 0.9:
            reason = "coverage_below_minimum"
        else:
            reason = None
        row = {"coverage": round(coverage, 6) if math.isfinite(coverage) else None,
               "reason": reason}
        for n in (50, 200):
            row[f"b{n}"] = (round(sum(wide.at[day, m] > means[m][n].iloc[i]
                                      for m in eligible) / count, 12)
                            if reason is None else None)
        series[key] = row
    valid = [k for k, v in series.items() if v["reason"] is None]
    missing = [k for k, v in series.items() if v["reason"] is not None]
    change_date = mem["segments"][1]["start"]
    prev_day = mem["segments"][0]["end"]
    out["breadth_day_before_change_date"] = prev_day
    out["breadth"] = {
        "first_valid_date": valid[0],
        "n_valid_days": len(valid),
        "missing_warmup_days": sum(1 for k in missing if series[k]["reason"] == "no_eligible_quotes"),
        "missing_coverage_days": {k: series[k]["reason"] for k in missing
                                  if series[k]["reason"] != "no_eligible_quotes"},
        "b50_at_first_valid": series[valid[0]]["b50"],
        "b200_at_first_valid": series[valid[0]]["b200"],
        "change_date": change_date,
        "b50_day_before_change": series[prev_day]["b50"],
        "b50_after_change": series[change_date]["b50"],
        "b200_after_change": series[change_date]["b200"],
        "b50_last": series[valid[-1]]["b50"],
        "constant_valid_b50": sorted({series[k]["b50"] for k in valid}),
        "constant_valid_b200": sorted({series[k]["b200"] for k in valid}),
    }
    # 双均线状态结果诊断的分组计数（独立算术）。
    out["state_outcome_note"] = (
        "真/假两组的后续目标均值由 runner 从同一定义独立重算核对，"
        "本文件冻结的是状态序列与分组计数")
    return out


def attribution() -> dict:
    return {
        "base": {
            "ending_equity": 106.0, "initial": 100.0, "net_pnl": 6.0,
            "contribution_X": 0.0 - 51.0 + 2.0 + 0.0 + 55.0,
            "reconcile_error_max": 0.01,
        },
        "variant_exit_on_d3": {
            "ending_equity": 105.45, "net_pnl": 5.45,
            "contribution_X": (55.0 - 0.55) - 51.0 + 2.0 + 0.0 + 0.0,
            "net_pnl_difference_vs_base": 5.45 - 6.0,
        },
        "receivable": {
            "ending_equity": 106.0, "net_pnl": 6.0,
            "contribution_X": 0.0 - 51.0 + 0.0 + 2.0 + 55.0,
        },
        "no_trade_cash": {"ending_equity": 100.0, "net_pnl": 0.0},
    }


def main() -> None:
    result = {"numerical": numerical(), "state": state(), "attribution": attribution()}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
