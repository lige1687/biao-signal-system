"""Frozen retrospective US ERP rail-crossing observation; no trading simulation."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V13 = ROOT / "docs/ops/breadth-reading-aid-20261101/us-sigma-yields-v13"
INPUTS = {
    "rates-snapshot.json": "9af5debf3c1e956bbda32fc8e80b15ea6d4386640fb2fe21082df419366e0f03",
    "overlay-snapshot.json": "f1d9f446aab9253e732e0db5f93462f91f1e282cffab50b09744826254368f3f",
}
HORIZONS = (21, 63, 126)
SIGMAS = (1.5, 2.0)
BLOCK = 126
BOOTSTRAPS = 2000
SEED = 20261105


def years_before(day: str) -> str:
    d = date.fromisoformat(day)
    try:
        return d.replace(year=d.year - 3).isoformat()
    except ValueError:  # Leap day follows the UI's February 28 fallback.
        return d.replace(year=d.year - 3, day=28).isoformat()


def validate_series(series: dict) -> list[tuple[str, float]]:
    dates, values = series["dates"], series["values"]
    if len(dates) != len(values):
        raise ValueError("date/value length mismatch")
    out = []
    for day, value in zip(dates, values):
        date.fromisoformat(day)
        if out and day <= out[-1][0]:
            raise ValueError("unsorted or duplicate date")
        if value is None or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("missing or nonfinite input")
        out.append((day, float(value)))
    return out


def erp_events(series: list[tuple[str, float]]) -> list[dict]:
    """Replicate usErpBands/usErpEvents: full prior 3 calendar years, population SD."""
    dates = [row[0] for row in series]
    events = []
    prev = None
    for i, (day, value) in enumerate(series):
        cutoff = years_before(day)
        start = bisect.bisect_left(dates, cutoff, 0, i)
        window = [v for _, v in series[start:i]]
        if dates[0] > cutoff or len(window) < 500:
            prev = None
            continue
        mean = sum(window) / len(window)
        sd = math.sqrt(sum((v - mean) ** 2 for v in window) / len(window))
        if sd == 0:
            prev = None
            continue
        if prev and 0 < (date.fromisoformat(day) - date.fromisoformat(prev["date"])).days <= 7:
            for sigma in SIGMAS:
                upper, lower = mean + sigma * sd, mean - sigma * sd
                previous_upper = prev["middle"] + sigma * prev["sigma"]
                previous_lower = prev["middle"] - sigma * prev["sigma"]
                kind = "upper" if prev["value"] <= previous_upper and value > upper else (
                    "lower" if prev["value"] >= previous_lower and value < lower else None
                )
                if kind:
                    events.append({"date": day, "kind": kind, "sigma": sigma,
                                   "erp": value, "middle": mean, "sd": sd,
                                   "rail": upper if kind == "upper" else lower,
                                   "id": f"{sigma:g}:{day}:{kind}"})
        prev = {"date": day, "value": value, "middle": mean, "sigma": sd}
    return sorted(events, key=lambda e: (e["date"], e["sigma"]))


def price_rows(series: list[tuple[str, float]]) -> list[dict]:
    dates = [d for d, _ in series]
    prices = [v for _, v in series]
    if any(v <= 0 for v in prices):
        raise ValueError("nonpositive price")
    rows = []
    for i, (day, price) in enumerate(series):
        if i < 199:
            continue
        ma200 = sum(prices[i - 199:i + 1]) / 200
        prior = prices[i] / prices[i - 63] - 1
        state = f"{'above' if price > ma200 else 'at_or_below'}:{'positive' if prior > 0 else 'negative' if prior < 0 else 'zero'}"
        labels = {}
        for h in HORIZONS:
            if i + 1 + h >= len(prices):
                continue
            entry = prices[i + 1]
            future = prices[i + 2:i + h + 2]  # exclude entry; include end close
            ret = prices[i + 1 + h] / entry - 1
            labels[str(h)] = {"entry_date": dates[i + 1], "end_date": dates[i + 1 + h],
                              "return_pct": 100 * ret,
                              "worst_loss_pct": 100 * min(0.0, min(future) / entry - 1)}
        rows.append({"date": day, "price_index": i, "price": price, "ma200": ma200,
                     "prior63_pct": prior * 100, "state": state, "labels": labels,
                     "block": i // BLOCK})
    return rows


def attach_events(events: list[dict], rows: list[dict], price_dates: list[str]) -> list[dict]:
    by_date = {r["date"]: r for r in rows}
    last_kept = {}
    out = []
    for event in events:
        row = by_date.get(event["date"])
        e = dict(event)
        e["price_match"] = event["date"] in price_dates
        e["feature_eligible"] = row is not None
        e["cooldown_keep"] = False
        if row:
            e.update({k: row[k] for k in ("price_index", "price", "ma200", "prior63_pct", "state", "block")})
            e["labels"] = row["labels"]
            key = (e["sigma"], e["kind"])
            if key not in last_kept or row["price_index"] - last_kept[key] >= 63:
                e["cooldown_keep"] = True
                last_kept[key] = row["price_index"]
        out.append(e)
    return out


def era(day: str) -> str:
    return "2016-2019" if day < "2020-01-01" else "2020-2022" if day < "2023-01-01" else "2023+"


def summarize(rows: list[dict], kind: str, h: int) -> dict:
    rets = [r["labels"][str(h)]["return_pct"] for r in rows]
    losses = [r["labels"][str(h)]["worst_loss_pct"] for r in rows]
    direction = [(r > 0 if kind == "upper" else r < 0) for r in rets]
    return {"n": len(rows), "mean_return_pct": statistics.mean(rets) if rets else None,
            "median_return_pct": statistics.median(rets) if rets else None,
            "correct_direction_rate_pct": 100 * statistics.mean(direction) if direction else None,
            "mean_worst_loss_pct": statistics.mean(losses) if losses else None,
            "median_worst_loss_pct": statistics.median(losses) if losses else None}


def conditional_baseline(events: list[dict], baseline: list[dict], kind: str, h: int) -> dict:
    by_state = defaultdict(list)
    for row in baseline:
        by_state[row["state"]].append(row)
    wanted = Counter(e["state"] for e in events)
    missing = [s for s in wanted if not by_state[s]]
    if missing or not events:
        return {"n": 0, "state_counts": dict(wanted), "baseline_state_support": {s: len(by_state[s]) for s in wanted},
                "missing_states": missing, "mean_return_pct": None, "correct_direction_rate_pct": None,
                "mean_worst_loss_pct": None}
    means = {s: summarize(by_state[s], kind, h) for s in wanted}
    return {"n": len(events), "state_counts": dict(wanted),
            "baseline_state_support": {s: len(by_state[s]) for s in wanted}, "missing_states": [],
            **{field: sum(wanted[s] * means[s][field] for s in wanted) / len(events)
               for field in ("mean_return_pct", "correct_direction_rate_pct", "mean_worst_loss_pct")}}


def paired_difference(candidate: dict, baseline: dict) -> dict:
    return {field: candidate[field] - baseline[field] if candidate[field] is not None and baseline[field] is not None else None
            for field in ("mean_return_pct", "correct_direction_rate_pct", "mean_worst_loss_pct")}


def block_interval(events: list[dict], baseline: list[dict], kind: str, h: int) -> dict:
    blocks = sorted({r["block"] for r in baseline})
    ev = defaultdict(list)
    base = defaultdict(list)
    for row in events:
        ev[row["block"]].append(row)
    for row in baseline:
        base[row["block"]].append(row)
    rng = random.Random(SEED + h + (1 if kind == "upper" else 2) + int(events[0]["sigma"] * 10) if events else SEED)
    draws = {"mean_return_pct": [], "correct_direction_rate_pct": []}
    for _ in range(BOOTSTRAPS):
        chosen = [rng.choice(blocks) for _ in blocks]
        sample_events = [row for block in chosen for row in ev[block]]
        if not sample_events:
            continue
        sample_baseline = [row for block in chosen for row in base[block]]
        candidate = summarize(sample_events, kind, h)
        reference = conditional_baseline(sample_events, sample_baseline, kind, h)
        difference = paired_difference(candidate, reference)
        for field in draws:
            if difference[field] is not None:
                draws[field].append(difference[field])
    result = {"method": "fixed_126_price_session_calendar_blocks", "draws_requested": BOOTSTRAPS,
              "blocks": len(blocks), "distinct_event_blocks": len({e["block"] for e in events})}
    for field, values in draws.items():
        values.sort()
        result[field] = {"valid_draws": len(values), "interval_95":
                         [values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]]
                         if len(values) >= 100 and len({e["block"] for e in events}) >= 3 else None}
    return result


def evaluate(events: list[dict], rows: list[dict]) -> dict:
    output = {}
    for h in HORIZONS:
        eligible = [r for r in rows if str(h) in r["labels"]]
        for sigma in SIGMAS:
            for kind in ("upper", "lower"):
                raw = [e for e in events if e["sigma"] == sigma and e["kind"] == kind and str(h) in e.get("labels", {})]
                cool = [e for e in raw if e["cooldown_keep"]]
                entry = {"eligible_baseline_days": len(eligible), "raw_count": len(raw), "cooldown_count": len(cool)}
                for name, subset in (("raw", raw), ("cooldown", cool)):
                    candidate = summarize(subset, kind, h)
                    unconditional = summarize(eligible, kind, h)
                    conditional = conditional_baseline(subset, eligible, kind, h)
                    entry[name] = {"performance": candidate, "unconditional": unconditional,
                                   "conditional": conditional,
                                   "increment_vs_unconditional": paired_difference(candidate, unconditional),
                                   "increment_vs_conditional": paired_difference(candidate, conditional)}
                    if name == "cooldown" and h == 63:
                        entry[name]["block_interval_conditional"] = block_interval(subset, eligible, kind, h)
                for period in ("2016-2019", "2020-2022", "2023+"):
                    eperiod = [e for e in cool if era(e["date"]) == period and era(e["labels"][str(h)]["end_date"]) == period]
                    bperiod = [r for r in eligible if era(r["date"]) == period and era(r["labels"][str(h)]["end_date"]) == period]
                    candidate = summarize(eperiod, kind, h)
                    comparison = conditional_baseline(eperiod, bperiod, kind, h)
                    entry.setdefault("eras_cooldown", {})[period] = {
                        "baseline_days": len(bperiod), "performance": candidate, "conditional": comparison,
                        "increment_vs_conditional": paired_difference(candidate, comparison)}
                output[f"{sigma:g}:{kind}:{h}"] = entry
    return output


def run(output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    inputs = {}
    for name, sha in INPUTS.items():
        path = V13 / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != sha:
            raise ValueError(f"frozen input changed: {name}: {actual}")
        inputs[name] = json.loads(path.read_text())
    erp = validate_series(inputs["rates-snapshot.json"]["series"]["erp_us"])
    price = validate_series(inputs["overlay-snapshot.json"]["series"]["sp500"])
    events = attach_events(erp_events(erp), price_rows(price), [d for d, _ in price])
    rows = price_rows(price)
    results = evaluate(events, rows)
    summary = {"source_as_of": [inputs[n]["as_of"] for n in INPUTS],
               "input_sha256": INPUTS,
               "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "erp_range": [erp[0][0], erp[-1][0]], "erp_days": len(erp),
               "price_range": [price[0][0], price[-1][0]], "price_days": len(price),
               "event_counts": {"all": len(events), "with_price": sum(e["price_match"] for e in events),
                                "feature_eligible": sum(e["feature_eligible"] for e in events),
                                **{f"mature_{h}": sum(str(h) in e.get("labels", {}) for e in events) for h in HORIZONS}},
               "baseline_counts": {str(h): sum(str(h) in r["labels"] for r in rows) for h in HORIZONS}}
    output_dir.mkdir(parents=False)
    for name, obj in (("events.json", events), ("results.json", results), ("summary.json", summary)):
        (output_dir / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
