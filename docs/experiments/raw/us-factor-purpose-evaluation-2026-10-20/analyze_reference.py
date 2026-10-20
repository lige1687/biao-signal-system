"""Fixed, descriptive US published long-short series comparison.

Contract schema us-factor-purpose-run/1 binds design, runner, loader, source_manifest,
storage_plan, and main-repository storage_module by absolute path and SHA256.
approved must be true. Output is exactly design.output, create-only. Returns are
decimals after the reference loader divides published percent once; they are not
account wealth, a same-stock pool, rank IC, or market-adjusted alpha.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import random
import statistics
from datetime import date
from pathlib import Path

SIGNALS = ("Mom12m", "GP", "BM")
SERIES = ("M", "halfM", "GP", "BM", "mixGP", "mixBM")
COMPARATORS = ("M", "halfM", "candidate_alone")
SCHEMA = "us-factor-purpose-run/1"
MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
STORAGE_MODULE = MAIN / "src/lei_signal/research/output_storage.py"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bound(binding):
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("binding requires exact path and sha256")
    p = Path(binding["path"])
    digest = binding["sha256"]
    if not p.is_absolute() or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("binding path/SHA invalid")
    if not p.is_file() or sha256(p) != digest:
        raise ValueError(f"bound input missing or changed: {p}")
    return p


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def months_between(start, end):
    a, z = (int(s[:4]) * 12 + int(s[5:7]) - 1 for s in (start, end))
    return [f"{k // 12:04d}-{k % 12 + 1:02d}" for k in range(a, z + 1)]


def prepare_rows(series_result, period):
    """Take exact complete months, using loader decimals without a second conversion."""
    needed = months_between(period["start"], period["end"])
    if len(needed) != period["expected_months"]:
        raise ValueError("period calendar/count mismatch")
    by_month = {}
    for raw in series_result["rows"]:
        day = date.fromisoformat(raw["date"])
        month = day.strftime("%Y-%m")
        if month not in needed:
            continue
        if month in by_month:
            raise ValueError(f"duplicate month: {month}")
        values = raw["returns"]
        row = {"month": month, "date": raw["date"]}
        for signal in SIGNALS:
            amount = values[signal]["decimal"]
            published = values[signal]["percent"]
            if amount is None or published is None or not math.isfinite(amount) or not math.isfinite(published):
                raise ValueError(f"missing/nonfinite {signal}: {month}")
            if not math.isclose(amount * 100, published, rel_tol=0, abs_tol=1e-10):
                raise ValueError(f"source percent/decimal mismatch: {signal} {month}")
            row[signal] = amount
        by_month[month] = row
    if sorted(by_month) != needed:
        raise ValueError(f"incomplete period {period['id']}: expected {len(needed)}, got {len(by_month)}")
    return [by_month[m] for m in needed]


def expand(rows):
    out = []
    for row in rows:
        m, gp, bm = (row[k] for k in SIGNALS)
        out.append({**row, "M": m, "halfM": m / 2, "mixGP": (m + gp) / 2,
                    "mixBM": (m + bm) / 2})
    return out


def mean(values):
    return math.fsum(values) / len(values) if values else None


def sd(values):
    return statistics.stdev(values) if len(values) > 1 else None


def corr(a, b):
    if len(a) < 2:
        return None
    ma, mb = mean(a), mean(b)
    va = math.fsum((v - ma) ** 2 for v in a)
    vb = math.fsum((v - mb) ** 2 for v in b)
    if va == 0 or vb == 0:
        return None
    return math.fsum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def describe(rows):
    n = len(rows)
    negative = [r for r in rows if r["M"] < 0]
    positive = [r for r in rows if r["M"] > 0]
    zero = n - len(negative) - len(positive)
    top_n = math.ceil(n / 10)
    top = sorted(rows, key=lambda r: (-r["M"], r["date"]))[:top_n]
    metrics = {}
    for name in SERIES:
        vals = [r[name] for r in rows]
        metrics[name] = {
            "mean": mean(vals), "sample_sd": sd(vals), "worst": min(vals),
            "negative_fraction": sum(v < 0 for v in vals) / n,
            "when_M_negative": mean([r[name] for r in negative]),
            "when_M_positive": mean([r[name] for r in positive]),
            "top_M_month_mean": mean([r[name] for r in top]),
            "correlation_with_M": corr(vals, [r["M"] for r in rows]),
        }
    comparisons = {}
    for candidate in ("GP", "BM"):
        mix = f"mix{candidate}"
        comparisons[candidate] = {}
        for label, other in (("M", "M"), ("halfM", "halfM"), ("candidate_alone", candidate)):
            diffs = [r[mix] - r[other] for r in rows]
            comparisons[candidate][label] = {
                "mean_difference": mean(diffs),
                "sample_sd_difference": metrics[mix]["sample_sd"] - metrics[other]["sample_sd"],
                "when_M_negative_difference": mean([r[mix] - r[other] for r in negative]),
                "when_M_positive_difference": mean([r[mix] - r[other] for r in positive]),
                "top_M_month_difference": mean([r[mix] - r[other] for r in top]),
            }
        comparisons[candidate]["candidate_positive_when_M_negative_fraction"] = (
            sum(r[candidate] > 0 for r in negative) / len(negative) if negative else None)
    return {"months": n, "first_month": rows[0]["month"], "last_month": rows[-1]["month"],
            "M_negative_months": len(negative), "M_positive_months": len(positive),
            "M_zero_months": zero, "top_M_count": top_n,
            "top_M_dates": [r["date"] for r in top],
            "top_M_positive_count": sum(r["M"] > 0 for r in top),
            "top_M_zero_count": sum(r["M"] == 0 for r in top), "series": metrics,
            "comparisons": comparisons}


def circular_indices(n, block, rng):
    out = []
    while len(out) < n:
        start = rng.randrange(n)
        out.extend((start + j) % n for j in range(block))
    return out[:n]


def percentile(values, q):
    values = sorted(values)
    point = (len(values) - 1) * q
    lo, hi = math.floor(point), math.ceil(point)
    return values[lo] + (values[hi] - values[lo]) * (point - lo)


def recent_intervals(rows, *, draws=5000, block=12, seed=20261020):
    """Shared full-row circular draws; recondition on drawn M each time."""
    rng = random.Random(seed)
    samples = {(c, b, k): [] for c in ("GP", "BM") for b in COMPARATORS
               for k in ("mean_difference", "sample_sd_difference", "when_M_negative_difference")}
    empty = {(c, b): 0 for c in ("GP", "BM") for b in COMPARATORS}
    h = hashlib.sha256()
    for _ in range(draws):
        indices = circular_indices(len(rows), block, rng)
        for i in indices:
            h.update(i.to_bytes(2, "big"))
        selected = [rows[i] for i in indices]
        result = describe(selected)["comparisons"]
        for candidate in ("GP", "BM"):
            for baseline in COMPARATORS:
                item = result[candidate][baseline]
                for metric in ("mean_difference", "sample_sd_difference", "when_M_negative_difference"):
                    value = item[metric]
                    if value is not None:
                        samples[(candidate, baseline, metric)].append(value)
                    elif metric == "when_M_negative_difference":
                        empty[(candidate, baseline)] += 1
    intervals = {}
    for (candidate, baseline, metric), values in samples.items():
        intervals.setdefault(candidate, {}).setdefault(baseline, {})[metric] = {
            "bounds_95": [percentile(values, .025), percentile(values, .975)] if values else None,
            "valid_draws": len(values), "missing_draws": draws - len(values)}
    return {"definition": "5000 shared paired circular 12-month blocks over all recent months; within-draw M conditions recalculated",
            "block_months": block, "draws": draws, "seed": seed, "index_sha256_u16be": h.hexdigest(),
            "empty_negative_condition_draws": {c: empty[(c, "M")] for c in ("GP", "BM")},
            "pointwise": intervals}


def calculate(series_result, design, *, draws=None):
    if series_result["signals"] != list(SIGNALS) or series_result["unit"] != "percent" or series_result["direction"] != "published_long_short":
        raise ValueError("wrong source signal/unit/direction")
    if design.get("signals") != list(SIGNALS) or design.get("combination_weights") != {"momentum": .5, "candidate": .5}:
        raise ValueError("changed signals or mixture")
    periods = design["periods"]
    if [(p["id"], p["expected_months"]) for p in periods] != [("recent", 120), ("earlier", 618)]:
        raise ValueError("unexpected periods")
    summaries, output_rows = {}, []
    for period in periods:
        rows = expand(prepare_rows(series_result, period))
        summaries[period["id"]] = describe(rows)
        output_rows.extend({"period": period["id"], **row} for row in rows)
    u = design["uncertainty"]
    if (u["block_months"], u["draws"], u["seed"], u["level"], u.get("interval_periods")) != (12, 5000, 20261020, .95, ["recent"]):
        raise ValueError("changed uncertainty plan")
    summaries["recent"]["uncertainty"] = recent_intervals(
        [r for r in output_rows if r["period"] == "recent"],
        draws=u["draws"] if draws is None else draws, block=u["block_months"], seed=u["seed"])
    return summaries, output_rows


def execute(design_path, contract_path):
    design_path, contract_path = Path(design_path).resolve(), Path(contract_path).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("schema") != SCHEMA or contract.get("approved") is not True:
        raise ValueError("run contract not approved")
    bindings = contract.get("bindings", {})
    required = {"design", "runner", "loader", "source_manifest", "storage_plan", "storage_module"}
    if set(bindings) != required:
        raise ValueError("incomplete run bindings")
    files = {name: bound(binding) for name, binding in bindings.items()}
    if files["design"] != design_path or files["runner"] != Path(__file__).resolve():
        raise ValueError("design/runner path mismatch")
    if files["storage_module"] != STORAGE_MODULE.resolve():
        raise ValueError("storage module is not the fixed main helper")
    design = json.loads(design_path.read_text(encoding="utf-8"))
    if design.get("schema") != "purpose-specific-reference/1" or design.get("status") != "design_before_effects":
        raise ValueError("design state changed")
    for name in ("loader", "source_manifest", "storage_plan"):
        if design[name] != bindings[name]:
            raise ValueError(f"design {name} differs from run contract")
    storage = json.loads(files["storage_plan"].read_text(encoding="utf-8"))
    if contract.get("output") != design["output"] or storage.get("output") != design["output"]:
        raise ValueError("output differs from saved plan")
    out = Path(design["output"])
    if out.exists():
        raise FileExistsError(f"refusing existing output: {out}")
    module = load_module(files["storage_module"], "osap_output_storage")
    module.recheck_saved_plan(MAIN, storage, storage["task_id"], storage["estimated_bytes"],
                              storage["internal_metadata_bytes"])
    if not module._still_mounted(storage):
        raise ValueError("external device not mounted")
    loader = load_module(files["loader"], "osap_reference_bound")
    reference = loader.load_reference(files["source_manifest"])
    source = loader.series(reference, SIGNALS)
    summaries, rows = calculate(source, design)
    if out.exists() or not module._still_mounted(storage):
        raise FileExistsError("output exists or external mount changed before write")
    parent = out.parent
    if parent.parent.exists() and parent.parent.stat().st_dev != storage["external_device"]:
        raise ValueError("external parent device mismatch")
    parent.mkdir(parents=True, exist_ok=False)
    out.mkdir(exist_ok=False)
    with (out / "monthly.csv").open("x", encoding="utf-8", newline="") as f:
        names = ["period", "month", "date", "M", "halfM", "GP", "BM", "mixGP", "mixBM"]
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    metadata = {name: reference["catalog"][name] for name in SIGNALS}
    result = {
        "schema": "us-factor-purpose-result/1", "periods": summaries,
        "source_signal_metadata": metadata,
        "source_metadata_differences": design["source_metadata_notes"],
        "source": {k: source[k] for k in ("manifest_path", "vintage", "market", "retrieved_at", "published_at", "bindings", "unit", "direction")},
        "source_manifest_sha256": sha256(files["source_manifest"]),
        "design_sha256": sha256(design_path), "runner_sha256": sha256(__file__),
        "loader_sha256": sha256(files["loader"]), "storage_plan_sha256": sha256(files["storage_plan"]),
        "contract_sha256": sha256(contract_path),
        "output_csv_sha256": sha256(out / "monthly.csv"),
        "unit": "decimal monthly published long-short return",
        "not_evaluated": design["not_evaluated"],
        "limitations": ["Published long-short arithmetic mixtures, not accounts or same-stock portfolios.",
                        "Earlier period is descriptive context; recent period is already-public exploratory history.",
                        "Half momentum is arithmetic scaling, not a funded cash implementation.",
                        "Pointwise intervals do not account for choosing between candidates or other historical searches."]
    }
    with (out / "result.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.write("\n")
    return {"result": str(out / "result.json"), "sha256": sha256(out / "result.json")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.design, args.contract), ensure_ascii=False))


if __name__ == "__main__":
    main()
