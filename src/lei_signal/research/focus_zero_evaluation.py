"""Descriptive, forward-aligned zero-crossing study; never a trading strategy."""
from __future__ import annotations

import csv
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric(value):
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if np.isfinite(result) else None


def upcross(previous, current) -> bool:
    return previous is not None and current is not None and previous <= 0 < current


def build_rows(calendar, prices, features, horizon, start="2015-01-01", end="2025-12-31"):
    """All labels start at the next session close. Missing sessions never bridge."""
    output = []
    for i, day in enumerate(calendar):
        if not start <= day <= end or i < 200 or i + horizon + 1 >= len(calendar):
            continue
        current = features.get(day)
        previous = features.get(calendar[i - 1])
        if not current or not previous:
            continue
        keys = ("focus", "pool_momentum", "breadth")
        if any(numeric(current.get(k)) is None for k in keys) or numeric(previous.get("focus")) is None:
            continue
        history = [prices.get(d) for d in calendar[i - 200:i + 1]]
        future = [prices.get(d) for d in calendar[i + 1:i + horizon + 2]]
        if any(x is None or not np.isfinite(x) or x <= 0 for x in history + future):
            continue
        m20 = history[-1] / history[-21] - 1
        previous_m20 = history[-2] / history[-22] - 1
        trend = history[-1] > np.mean(history[-200:])
        focus = float(current["focus"])
        event = upcross(float(previous["focus"]), focus)
        cell = (int(m20 > 0) + 2 * int(trend) + 4 * int(float(current["pool_momentum"]) > 0)
                + 8 * int(float(current["breadth"]) >= .5))
        output.append({"date": day, "calendar_index": i, "horizon": horizon,
                       "label_start": calendar[i + 1], "label_end": calendar[i + horizon + 1],
                       "forward_return": future[-1] / future[0] - 1,
                       "future_minimum": min(future) / future[0] - 1,
                       "focus": focus, "pool_momentum": float(current["pool_momentum"]),
                       "breadth": float(current["breadth"]), "index_m20": m20,
                       "focus_up": event, "index_up": upcross(previous_m20, m20),
                       "trend": bool(trend), "focus_up_trend": bool(event and trend),
                       "focus_negative": focus < 0, "baseline_cell": cell})
    return output


def performance(rows):
    if not rows:
        return {"count": 0, "mean": None, "median": None, "positive_share": None,
                "mean_future_minimum": None, "worst_future_minimum": None}
    returns = np.array([r["forward_return"] for r in rows])
    lows = np.array([r["future_minimum"] for r in rows])
    return {"count": len(rows), "mean": float(returns.mean()), "median": float(np.median(returns)),
            "positive_share": float((returns > 0).mean()), "mean_future_minimum": float(lows.mean()),
            "worst_future_minimum": float(lows.min())}


def standardized(rows, event_key, weights=None):
    """Reweight non-event controls to the event distribution of past-only cells."""
    weights = np.ones(len(rows)) if weights is None else weights
    total = 0.0
    effect = 0.0
    probability = 0.0
    cells = []
    for cell in range(16):
        yes = np.array([i for i, r in enumerate(rows) if r["baseline_cell"] == cell and r[event_key]], dtype=int)
        no = np.array([i for i, r in enumerate(rows) if r["baseline_cell"] == cell and not r[event_key]], dtype=int)
        wy, wn = weights[yes].sum(), weights[no].sum()
        if wy <= 0 or wn <= 0:
            continue
        y = np.array([rows[i]["forward_return"] for i in yes])
        n = np.array([rows[i]["forward_return"] for i in no])
        difference = float(np.average(y, weights=weights[yes]) - np.average(n, weights=weights[no]))
        pdiff = float(np.average(y > 0, weights=weights[yes]) - np.average(n > 0, weights=weights[no]))
        total += wy
        effect += wy * difference
        probability += wy * pdiff
        cells.append({"cell": cell, "events": int(len(yes)), "controls": int(len(no)), "difference": difference})
    return {"difference": effect / total if total else None,
            "positive_share_difference": probability / total if total else None,
            "supported_event_weight": float(total), "cells": cells}


def conditional_increment(rows, event_key, replicates=2000, seed=20261104, block=126):
    point = standardized(rows, event_key)
    event_count = sum(r[event_key] for r in rows)
    point.update(event_count=event_count, unsupported_event_count=event_count - int(point["supported_event_weight"]))
    if point["difference"] is None or not rows:
        return {**point, "interval": None, "valid_replicates": 0}
    # Preserve actual exchange-session gaps: resample blocks on calendar positions,
    # then select the rows present in each block, rather than compressing missing dates.
    positions = np.array([r["calendar_index"] for r in rows])
    positions -= positions.min()
    n = int(positions.max()) + 1
    length = min(block, n)
    rng = np.random.default_rng(seed)
    cells = np.array([r["baseline_cell"] for r in rows], dtype=int)
    events = np.array([r[event_key] for r in rows], dtype=bool)
    returns = np.array([r["forward_return"] for r in rows])
    values = []
    for _ in range(replicates):
        starts = rng.integers(0, n - length + 1, size=int(np.ceil(n / length)))
        picks = (starts[:, None] + np.arange(length)[None, :]).ravel()[:n]
        counts = np.bincount(picks, minlength=n)[positions]
        yes = counts * events
        no = counts * ~events
        wy = np.bincount(cells, weights=yes, minlength=16)
        wn = np.bincount(cells, weights=no, minlength=16)
        supported = (wy > 0) & (wn > 0)
        if supported.any():
            sy = np.bincount(cells, weights=yes * returns, minlength=16)
            sn = np.bincount(cells, weights=no * returns, minlength=16)
            difference = sy[supported] / wy[supported] - sn[supported] / wn[supported]
            values.append(float(np.average(difference, weights=wy[supported])))
    return {**point, "interval": [float(x) for x in np.quantile(values, [.025, .975])] if values else None,
            "valid_replicates": len(values), "block_sessions": block}


def summarize(rows, replicates=2000):
    masks = ["focus_up", "index_up", "trend", "focus_up_trend", "focus_negative"]
    stats = {"all": performance(rows), **{key: performance([r for r in rows if r[key]]) for key in masks}}
    years = ((date.fromisoformat(rows[-1]["date"]) - date.fromisoformat(rows[0]["date"])).days + 1) / 365.2425 if rows else None
    for result in stats.values():
        result["frequency_per_year"] = result["count"] / years if years else None
        result["observation_span_years"] = years
    raw = stats["all"]["mean"]
    for key in masks:
        mean = stats[key]["mean"]
        stats[key]["mean_minus_all"] = mean - raw if mean is not None and raw is not None else None
    events = [r for r in rows if r["focus_up"]]
    removed = [r for r in events if not r["trend"]]
    kept = [r for r in events if r["trend"]]
    periods = {}
    for name, lower, upper in [("2015-2019", "2015", "2019"), ("2020-2022", "2020", "2022"), ("2023-2025", "2023", "2025")]:
        selected = [r for r in rows if lower <= r["date"][:4] <= upper]
        periods[name] = {"all": performance(selected), "focus_up": performance([r for r in selected if r["focus_up"]]),
                         "conditional": standardized(selected, "focus_up")}
    return {"performance": stats,
            "conditional": {key: conditional_increment(rows, key, replicates) for key in ("focus_up", "focus_up_trend")},
            "trend_filter": {"kept": performance(kept), "removed": performance(removed),
                             "removed_profitable": sum(r["forward_return"] > 0 for r in removed),
                             "removed_loss": sum(r["forward_return"] < 0 for r in removed),
                             "largest_missed_gains": sorted([r for r in removed if r["forward_return"] > 0], key=lambda r: -r["forward_return"])[:5],
                             "largest_avoided_losses": sorted([r for r in removed if r["forward_return"] < 0], key=lambda r: r["forward_return"])[:5]},
            "periods": periods,
            "years": {year: {key: performance([r for r in rows if r["date"].startswith(year) and (key == "all" or r[key])])
                             for key in ("all", "focus_up", "focus_up_trend")}
                      for year in sorted({r["date"][:4] for r in rows})},
            "overlap": {"consecutive_event_list_pairs": max(0, len(events) - 1),
                        "neighboring_overlapping_pairs": sum(b["calendar_index"] - a["calendar_index"] <= a["horizon"]
                                                             for a, b in zip(events, events[1:])),
                        "all_overlapping_pairs": sum(b["calendar_index"] - a["calendar_index"] <= a["horizon"]
                                                     for i, a in enumerate(events) for b in events[i + 1:])}}


def evaluate_pair(calendar, prices, dynamic, fixed, replicates=2000):
    results, all_rows = {}, []
    for horizon in (20, 63):
        candidates = {name: build_rows(calendar, prices, series, horizon) for name, series in (("dynamic", dynamic), ("fixed300", fixed))}
        common = set.intersection(*[{r["date"] for r in rows} for rows in candidates.values()])
        results[str(horizon)] = {"common_count": len(common), "groups": {}}
        for name, source_rows in candidates.items():
            rows = [r for r in source_rows if r["date"] in common]
            if not rows:
                raise ValueError("no common qualified dates")
            results[str(horizon)]["groups"][name] = {"dates_before_common": len(source_rows), "start": rows[0]["date"],
                                                     "end": rows[-1]["date"], **summarize(rows, replicates)}
            all_rows.extend([{**row, "universe": name} for row in rows])
    return results, all_rows


def run(contract_path: Path, output: Path):
    """Execute one previously bound observational comparison, without data fetches."""
    from lei_signal.research.focus_dynamic import _storage_output
    _storage_output(output)
    contract = json.loads(contract_path.read_text())
    if contract.get("status") != "frozen_before_effect" or contract.get("effect_attempt") != 1:
        raise ValueError("an explicit first-effect contract is required")
    for source in contract["sources"].values():
        path = Path(source["path"])
        if sha(path) != source["sha256"]:
            raise ValueError(f"bound source changed: {path}")
    sources = contract["sources"]
    review = json.loads(Path(sources["qualification"]["path"]).read_text())
    if review.get("decision") != "admitted_retrospective_limited":
        raise ValueError("root input qualification is missing")
    calendar = [r["trade_date"] for r in csv.DictReader(Path(sources["calendar"]["path"]).open())]
    if calendar != sorted(set(calendar)):
        raise ValueError("calendar order or duplicates")
    price_rows = list(csv.DictReader(Path(sources["prices"]["path"]).open()))
    prices = {r["trade_date"]: numeric(r["close_cny_index_points"]) for r in price_rows}
    if len(prices) != len(price_rows):
        raise ValueError("duplicate target dates")
    dynamic_rows = json.loads(Path(sources["dynamic"]["path"]).read_text())
    dynamic = {r["date"]: r for r in dynamic_rows}
    fixed_rows = list(csv.DictReader(Path(sources["fixed"]["path"]).open()))
    fixed = {r["date"]: r for r in fixed_rows}
    if len(dynamic) != len(dynamic_rows) or len(fixed) != len(fixed_rows):
        raise ValueError("duplicate feature dates")
    results, rows = evaluate_pair(calendar, prices, dynamic, fixed)
    _storage_output(output)
    output.mkdir(parents=True)
    with (output / "observations.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"status": "descriptive_historical_comparison", "contract_sha256": sha(contract_path),
               "code_sha256": sha(Path(__file__)), "results": results,
               "limitations": review["limitations"],
               "observation_rows_sha256": sha(output / "observations.csv")}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    return {"output": str(output), "summary_sha256": sha(output / "summary.json"), "rows": len(rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.contract, args.out), ensure_ascii=False))
