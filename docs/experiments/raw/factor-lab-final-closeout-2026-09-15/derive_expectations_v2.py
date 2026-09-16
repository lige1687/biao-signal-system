"""独立期望产物 v2（factor-lab-final-closeout S2）。

在 v1 独立算术（derive_expectations.py，不 import lei_signal）基础上，新增
``protocol_expectations`` 段：按案例给出**必查检查ID → 期望值**的完整集合。
这是必查清单的唯一权威来源：协议不得自行声明或裁剪（runner 做值级核对）。
输出：independent-expectations-v2.json（排他创建）。
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
IN = HERE.parent / "factor-research-workbench-v1-2026-09-14" / "synthetic_inputs"


def sha(name: str) -> str:
    return hashlib.sha256((IN / name).read_bytes()).hexdigest()


# ---- 独立算术（与 v1 相同来源，不 import 被测代码） ----

def ema(values, period=20):
    out = [math.nan] * len(values)
    if len(values) < period:
        return out
    out[period - 1] = sum(values[:period]) / period
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def sma(values, period=20):
    s = pd.Series(values).rolling(period, min_periods=period).mean()
    return [math.nan if pd.isna(v) else float(v) for v in s]


def classify(close, e):
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


def bull_state(close, e, s, colors):
    out = []
    for i, c in enumerate(close):
        if i == 0 or math.isnan(e[i]) or math.isnan(s[i]) or math.isnan(e[i - 1]) \
                or math.isnan(s[i - 1]) or colors[i] == "unknown":
            out.append(None)
            continue
        out.append(c > e[i] and c > s[i] and e[i] > e[i - 1] and s[i] > s[i - 1]
                   and colors[i] == "green")
    return out


def build_protocol_expectations() -> dict:
    """三个案例的必查集合与期望值（结构推导 + 独立算术）。"""
    out: dict = {}

    # ---- 案例1 数值 ----
    p3 = pd.read_csv(IN / "numerical_prices_3.csv", parse_dates=["date"]).set_index("date")
    p5 = pd.read_csv(IN / "numerical_prices_5.csv", parse_dates=["date"]).set_index("date")
    row = 252
    mom_a = float(p3["alpha"].iloc[row] / p3["alpha"].iloc[row - 21]
                  - 1) if False else float(
        p3["alpha"].iloc[row - 21] / p3["alpha"].iloc[row - 252] - 1)
    rv_a = float(p3["alpha"].pct_change(fill_method=None)
                 .rolling(20, min_periods=20).std(ddof=1).iloc[row] * math.sqrt(252))
    d50_a = float(p3["alpha"].iloc[row] / p3["alpha"].iloc[row - 49:row + 1].mean() - 1)
    d200_a = float(p3["alpha"].iloc[row] / p3["alpha"].iloc[row - 199:row + 1].mean() - 1)
    # 成熟观察日：0基252..277（共26日）；标签窗21个交易日 → dev/validation 全部8×3跨段，
    # holdout 10×3 全部成熟（最晚标签结束于面板末日，段截止=面板末日15:00）。
    out["numerical"] = {
        "momentum_first_valid_row": 253,
        "momentum_alpha_row252": mom_a,
        "rv20_alpha_row252": rv_a,
        "distance50_alpha_row252": d50_a,
        "distance200_alpha_row252": d200_a,
        "ic_mean_3": 1.0,
        "n_periods_3": int(len(p3)),
        "n_periods_with_value_3": 26,
        "min_n_3": 0,
        "min_n_with_value_3": 3,
        "ic_mean_5": 1.0,
        "n_periods_with_value_5": 26,
        "min_n_5": 0,
        "min_n_with_value_5": 4,
        "max_n_5": 5,
        "scale_invariance_max_diff": 0.0,
        "append_invariance_max_diff": 0.0,
        "dev_label_crossing_n": 24,
        "validation_label_crossing_n": 24,
        "dev_n_usable_clean": 0,
        "validation_n_usable_clean": 0,
        "holdout_n_usable_clean": 30,
        "trial_history_status": "provided",
    }

    # ---- 案例2 状态 ----
    dm = {}
    for tag in ("a", "b"):
        df = pd.read_csv(IN / f"state_bars_dm_{tag}.csv", parse_dates=["date"])
        close = [float(v) for v in df["close"]]
        e = ema(close)
        s = sma(close)
        colors = classify(close, e)
        st = bull_state(close, e, s, colors)
        ready = [i for i, v in enumerate(st) if v is not None]
        true_idx = [i for i, v in enumerate(st) if v is True]
        dm[tag] = {
            "first_ready": ready[0], "not_ready": len(close) - len(ready),
            "true_rows": len(true_idx), "false_rows": len(ready) - len(true_idx),
            "state_last": st[-1], "state_row21": st[20], "state_row25": st[24],
        }
    wide = pd.read_csv(IN / "state_breadth_close.csv", parse_dates=["date"]).set_index("date")
    mem = json.loads((IN / "state_membership.json").read_text())
    membership = {}
    for seg in mem["segments"]:
        for day in pd.bdate_range(seg["start"], seg["end"]):
            membership[str(day.date())] = list(seg["members"])
    means = {c: {n: wide[c].dropna().rolling(n, min_periods=n).mean().reindex(wide.index)
                 for n in (50, 200)} for c in wide}
    b_values, missing_cov = [], 0
    first_valid, at_change, day_before, b200_first = None, None, None, None
    change_date = mem["segments"][1]["start"]
    day_before_date = mem["segments"][0]["end"]
    for i, day in enumerate(wide.index):
        key = str(day.date())
        members = membership[key]
        eligible = [m for m in members if pd.notna(wide.at[day, m])
                    and pd.notna(means[m][200].iloc[i])]
        total, count = len(members), len(eligible)
        coverage = count / total if total else float("nan")
        reason = ("no_eligible_quotes" if count == 0
                  else "coverage_below_minimum" if coverage < 0.9 else None)
        if reason is None:
            b = sum(wide.at[day, m] > means[m][50].iloc[i] for m in eligible) / count
            b200 = sum(wide.at[day, m] > means[m][200].iloc[i] for m in eligible) / count
            b_values.append((b, b200))
            if first_valid is None:
                first_valid = (key, b, b200)
            if key == change_date:
                at_change, at_change200 = b, b200
            if key == day_before_date:
                day_before, _ = b, b200
            if key == str(wide.index[-1].date()):
                last_b = b
        elif reason == "coverage_below_minimum":
            missing_cov += 1
    valid_days = len(b_values)
    out["state"] = {
        "dm_a_not_ready_rows": dm["a"]["not_ready"],
        "dm_a_state_true_rows": dm["a"]["true_rows"],
        "dm_a_state_false_rows": dm["a"]["false_rows"],
        "dm_a_state_at_row21": int(dm["a"]["state_row21"]),
        "dm_a_state_at_row25": int(dm["a"]["state_row25"]),
        "dm_a_state_at_last_row": int(dm["a"]["state_last"]),
        "dm_b_not_ready_rows": dm["b"]["not_ready"],
        "dm_b_state_true_rows": dm["b"]["true_rows"],
        "dm_b_state_false_rows": dm["b"]["false_rows"],
        "dm_b_state_at_last_row": int(dm["b"]["state_last"]),
        "b50_first_valid_date": first_valid[0],
        "b50_valid_days": valid_days,
        "b50_coverage_missing_days": missing_cov,
        "b50_at_first_valid": first_valid[1],
        "b50_day_before_change": day_before,
        "b50_at_change": at_change,
        "b200_first_valid_date": first_valid[0],
        "b200_valid_days": valid_days,
        "b200_coverage_missing_days": missing_cov,
        "b200_at_first_valid": first_valid[2],
        "b200_at_change": at_change200,
        "constant_breadth_ic_status": "not_applicable",
        "so_dm_a_true_n": 8,
        "so_dm_a_false_n": 15,
        "so_dm_b_true_n": 0,
        "so_dm_b_false_n": 23,
        "ts_m1_status": "descriptive_only",
        "ts_m1_n": 39,
    }

    # ---- 案例3 归因（手算账，结构化） ----
    out["attribution"] = {
        "base_status": "reconciled",
        "base_net_contribution": -51.0 + 2.0 + 55.0,
        "base_reconcile_error": 0.0,
        "receivable_status": "reconciled",
        "receivable_net_contribution": -51.0 + 2.0 + 55.0,
        "variant_exit_on_d3_status": "reconciled",
        "variant_exit_on_d3_net_contribution": (55.0 - 0.55) - 51.0 + 2.0,
        "l2_status": "attributable_to_declared_action_only",
        "l2_net_pnl_diff": 5.45 - 6.0,
        "l3_status": "not_run",
        "l3_reason": "no_model_card_provided",
    }
    return out


def main() -> int:
    path = HERE / "independent-expectations-v2.json"
    if path.exists():
        print(f"refusing to overwrite {path}")
        return 3
    v1 = json.loads((HERE.parent / "factor-research-workbench-v1-2026-09-14"
                     / "independent-expectations.json").read_text(encoding="utf-8"))
    result = dict(v1)
    result["protocol_expectations"] = build_protocol_expectations()
    result["inputs_sha256"] = {p.name: sha(p.name) for p in sorted(IN.glob("*"))}
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    for case, checks in result["protocol_expectations"].items():
        print(f"protocol_expectations[{case}]: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
