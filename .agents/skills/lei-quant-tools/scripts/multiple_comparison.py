"""Read-only, unstandardized joint comparison of saved daily prediction losses."""
from __future__ import annotations

import argparse
from datetime import date
import json
import math
from pathlib import Path
import sys

import numpy as np

from lei_arch_bootstrap.bootstrap.multiple_comparison import SPA
from workflow_bridge import prepare_workflow_input, read_archived_run

SCHEMA = "lei-multiple-losses/1.0"
MAX_REPS = 10000


def _day(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("calendar dates must be ISO strings")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("calendar dates must be YYYY-MM-DD") from exc
    return value


def _integer(value: object, name: str, minimum: int, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be an integer in the allowed range")
    return value


def _loss(value: object, name: str) -> float:
    if type(value) not in (int, float) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    try:
        answer = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} overflows float") from exc
    if not math.isfinite(answer):
        raise ValueError(f"{name} overflows float")
    return answer


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a nonempty exact identifier")
    return value


def compare_losses(packet: dict) -> dict:
    """Compare a complete, ordered date x candidate matrix without fitting."""
    if not isinstance(packet, dict) or packet.get("schema_version") != SCHEMA:
        raise ValueError("unsupported loss packet schema")
    if packet.get("frequency") != "qualified_session":
        raise ValueError("only one loss per complete qualified session is supported")
    unit = packet.get("unit")
    if unit not in ("percentage_point_squared", "probability_squared"):
        raise ValueError("unsupported common loss unit")
    calendar_raw = packet.get("calendar")
    if not isinstance(calendar_raw, list):
        raise ValueError("calendar must be a complete ordered list")
    calendar = [_day(d) for d in calendar_raw]
    if len(calendar) < 3 or calendar != sorted(set(calendar)):
        raise ValueError("calendar needs at least three unique increasing dates")
    n = len(calendar)
    candidate_ids = packet.get("candidate_ids")
    if not isinstance(candidate_ids, list) or not candidate_ids or len(candidate_ids) > 64:
        raise ValueError("require 1-64 declared candidates")
    candidate_ids = [_identity(x, "candidate id") for x in candidate_ids]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate candidate id")
    benchmark_id = _identity(packet.get("benchmark_id"), "benchmark id")
    if benchmark_id in candidate_ids:
        raise ValueError("benchmark cannot also be a candidate")
    block = _integer(packet.get("block_size"), "block_size", 1, n)
    reps = _integer(packet.get("reps"), "reps", 1, MAX_REPS)
    seed = _integer(packet.get("seed"), "seed", 0)
    rows = packet.get("rows")
    if not isinstance(rows, list) or len(rows) != n:
        raise ValueError("one row is required for every calendar date")
    benchmark, models = [], []
    for pos, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"date", "benchmark_loss", "models"}:
            raise ValueError("row fields must be date, benchmark_loss and models")
        if _day(row["date"]) != calendar[pos]:
            raise ValueError("row dates must exactly match complete calendar")
        losses = row["models"]
        if not isinstance(losses, dict) or set(losses) != set(candidate_ids):
            raise ValueError("every row needs exactly the declared candidate ids")
        benchmark.append(_loss(row["benchmark_loss"], "benchmark_loss"))
        models.append([_loss(losses[c], f"model loss {c}") for c in candidate_ids])
    baseline = np.asarray(benchmark, dtype=float)
    candidates = np.asarray(models, dtype=float)
    with np.errstate(over="ignore", invalid="ignore"):
        differences = baseline[:, None] - candidates
    if not np.isfinite(differences).all():
        raise ValueError("loss differential overflow")
    # The vendored variance path squares differences; bound arithmetic, not effect size.
    if np.max(np.abs(differences)) > 1e150:
        raise ValueError("loss differential too large for stable resampling variance")
    for j, candidate_id in enumerate(candidate_ids):
        if np.all(differences[:, j] == differences[0, j]):
            raise ValueError(f"constant loss differential for {candidate_id}")
        for prior in range(j):
            if np.array_equal(candidates[:, j], candidates[:, prior]):
                raise ValueError(f"identical losses for distinct candidates: {candidate_ids[prior]} and {candidate_id}")
    spa = SPA(baseline, candidates, block_size=block, reps=reps,
              bootstrap="circular", studentize=False, nested=False, seed=seed)
    spa.compute()
    # Even varying daily losses can collapse under fixed circular blocks.
    # The upstream strict exceedance then returns zero for an exact tie.
    maxima = np.max(spa._simulated_vals[:, :, 2], axis=0)
    tolerance = 32 * np.finfo(float).eps * max(float(np.max(np.abs(differences))),
                                             np.finfo(float).tiny)
    if not np.isfinite(maxima).all() or np.ptp(maxima) <= tolerance:
        raise ValueError("degenerate resampled maximum distribution; no joint inference")
    upper = float(spa.pvalues["upper"])
    if not math.isfinite(upper) or not 0 <= upper <= 1:
        raise ValueError("joint comparison produced an invalid upper p value")
    means = differences.mean(axis=0)
    if not np.isfinite(means).all():
        raise ValueError("mean loss differential overflow")
    return {
        "status": "computed", "schema_version": SCHEMA, "unit": unit,
        "frequency": "qualified_session", "calendar": calendar,
        "benchmark_id": benchmark_id, "candidate_ids": candidate_ids,
        "daily_rows": n, "block_size": block, "reps": reps, "seed": seed,
        "bootstrap": "circular", "studentize": False, "nested": False,
        "primary_pvalue": "upper", "upper_pvalue": upper,
        "simulation_resolution": 1 / reps,
        "observed_max_mean_improvement": float(np.max(means)),
        "mean_improvements": {key: float(means[j]) for j, key in enumerate(candidate_ids)},
        "interpretation": "Retrospective joint check only for these declared saved candidates, dates, benchmark and common loss unit; no new-market validation, effectiveness probability or trading conclusion.",
    }


def compare_workflows(run_dirs, start, end, baseline, block, reps, seed) -> dict:
    """Qualify archived runs together, then compare their saved daily errors."""
    if not isinstance(run_dirs, (list, tuple)) or not run_dirs:
        raise ValueError("at least one archived run required")
    if baseline not in ("B0", "B1"):
        raise ValueError("workflow baseline must be B0 or B1")
    start, end = _day(start), _day(end)
    if start > end:
        raise ValueError("start after end")
    summaries, prepared = [], []
    for run_dir in run_dirs:
        contract, result, proof, source = read_archived_run(run_dir)
        summary, ready = prepare_workflow_input(contract, result, proof,
                                                 baseline=baseline, start=start, end=end)
        summary["source"] = source
        summaries.append(summary)
        if ready is None:
            return {"status": "not_applicable", "reasons": summary["reasons"],
                    "sources": summaries, "fits": 0}
        # The bridge has already verified receipt, eligible identity and a balanced axis.
        rows = [r for r in result["predictions"] if start <= r["date"] <= end]
        rows.sort(key=lambda r: (r["date"], r["asset"]))
        identity = [(r["asset"], r["date"], r["id"], r["fold"], r["y"], r["label_end"]) for r in rows]
        baseline_values = [r[baseline] for r in rows]
        if not rows or len({r["fold"] for r in rows}) != 1:
            return {"status": "not_applicable", "reasons": ["require one complete fitted evaluation period"], "sources": summaries, "fits": 0}
        prepared.append((contract, ready, identity, baseline_values, rows, source))
    first_contract, first_packet, first_identity, first_baseline, _, _ = prepared[0]
    calendar = first_packet["calendar"]
    for contract, ready, identity, values, _, _ in prepared[1:]:
        if (ready["calendar"] != calendar or ready["unit"] != first_packet["unit"]
                or identity != first_identity or values != first_baseline
                or contract["question"].get("primary_metric") != first_contract["question"].get("primary_metric")):
            return {"status": "not_applicable", "reasons": ["archived runs differ in calendar, unit, row identity, target, baseline or primary metric"], "sources": summaries, "fits": 0}
    ids = []
    for _, _, _, _, _, source in prepared:
        ids.append(source["run_dir"])
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate archived run")
    by_date = {d: [] for d in calendar}
    for row in prepared[0][4]:
        with np.errstate(over="ignore", invalid="ignore"):
            value = np.square(np.subtract(np.float64(row[baseline]), np.float64(row["y"])))
        if not np.isfinite(value):
            raise ValueError("archived baseline squared error overflow")
        by_date[row["date"]].append(value)
    candidate_daily = []
    for _, _, _, _, rows, _ in prepared:
        values = {d: [] for d in calendar}
        for row in rows:
            with np.errstate(over="ignore", invalid="ignore"):
                value = np.square(np.subtract(np.float64(row["B2"]), np.float64(row["y"])))
            if not np.isfinite(value):
                raise ValueError("archived candidate squared error overflow")
            values[row["date"]].append(value)
        candidate_daily.append(values)
    packet = {
        "schema_version": SCHEMA, "unit": first_packet["unit"],
        "frequency": "qualified_session", "calendar": calendar,
        "benchmark_id": baseline, "candidate_ids": ids,
        "block_size": block, "reps": reps, "seed": seed,
        "rows": [
            {"date": d, "benchmark_loss": float(np.mean(by_date[d])),
             "models": {key: float(np.mean(candidate_daily[j][d])) for j, key in enumerate(ids)}}
            for d in calendar
        ],
    }
    answer = compare_losses(packet)
    answer.update(sources=summaries, fits=0, evaluation_range=[start, end],
                  asset_count=len(first_contract["universe"]["assets"]),
                  weighting="same complete asset pool each day; arithmetic mean per day")
    return answer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    losses = sub.add_parser("compare-losses")
    losses.add_argument("input")
    workflows = sub.add_parser("compare-workflows")
    workflows.add_argument("run_dirs", nargs="+")
    workflows.add_argument("--start", required=True)
    workflows.add_argument("--end", required=True)
    workflows.add_argument("--baseline", choices=["B0", "B1"], required=True)
    workflows.add_argument("--block-size", type=int, required=True)
    workflows.add_argument("--reps", type=int, required=True)
    workflows.add_argument("--seed", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "compare-losses":
            result = compare_losses(json.loads(Path(args.input).read_text()))
        else:
            result = compare_workflows(args.run_dirs, args.start, args.end, args.baseline,
                                       args.block_size, args.reps, args.seed)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0 if result["status"] == "computed" else 2
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
