"""Read archived workflow results and qualify a daily paired-loss diagnostic.

No fitting, resampling, publishing, or ledger writes. Snapshot integrity is not
current-source requalification or authorization to change a sealed conclusion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from lei_signal.research.workflow import family_ledger
from lei_signal.research.workflow_evaluation import (
    _axis, _config, _date, _folds, _observations, _paired_predictions,
)


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_archived_run(run_dir):
    run = Path(run_dir).resolve()
    if not run.is_relative_to(ROOT / "docs/experiments/raw"):
        raise ValueError("run must be an authorized project experiment artifact")
    paths = {name: run / name for name in
             ("contract.json", "result.json", "preflight.json", "receipt.json")}
    data = {name: json.loads(path.read_text()) for name, path in paths.items()}
    receipt, contract = data["receipt.json"], data["contract.json"]
    if receipt.get("schema_version") != "workflow-receipt/1.0":
        raise ValueError("unsupported receipt schema")
    if receipt.get("contract_sha256") != _hash(paths["contract.json"]):
        raise ValueError("archived contract hash mismatch")
    outputs = receipt.get("outputs", {})
    if not {"preflight.json", "result.json", "report.md"}.issubset(outputs):
        raise ValueError("receipt lacks required archived outputs")
    for name, expected in outputs.items():
        if Path(name).name != name or not (run / name).resolve().is_relative_to(run):
            raise ValueError("invalid archived output path")
        if _hash(run / name) != expected:
            raise ValueError(f"archived output hash mismatch: {name}")
    journal = family_ledger(ROOT, contract["history"]["family"])
    records = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    if not any(r.get("event") == "finish" and r.get("status") == "computed"
               and r.get("run_id") == receipt.get("run_id")
               and r.get("receipt_sha256") == _hash(paths["receipt.json"])
               for r in records):
        raise ValueError("no matching archived execution journal receipt")
    return contract, data["result.json"], data["preflight.json"], {
        "run_dir": str(run.relative_to(ROOT)),
        "files": {name: _hash(path) for name, path in paths.items()},
        "receipt_matches_archived_journal": True,
        "qualification": "archived snapshot only; current sources and code not requalified",
    }


def prepare_workflow_input(contract, result, proof, *, baseline="B1", start=None, end=None):
    """Return readiness and, only for complete balanced daily input, a packet."""
    binary, policy = _config(contract)
    observations = _observations(proof["observations"], binary)
    axis = _axis(contract, observations)
    folds = _folds(contract)
    frame = _paired_predictions(result["predictions"], binary, folds, axis)
    if not len(frame):
        raise ValueError("no saved predictions")
    if baseline not in ({"B0", "B1", "B50"} if binary else {"B0", "B1"}):
        raise ValueError("unsupported baseline")
    lookup = {r["id"]: r for r in observations.to_dict("records")}
    for row in frame.to_dict("records"):
        original = lookup.get(row["id"])
        if original is None or not original["eligible"] or any(
            row[k] != original[k] for k in ("asset", "date", "y", "label_end")
        ):
            raise ValueError("saved prediction differs from eligible observation identity/target")
    if (start is None) != (end is None):
        raise ValueError("supply both start and end, or neither")
    explicit_range = start is not None
    first, last = min(f["eval_start"] for f in folds), max(f["eval_end"] for f in folds)
    start, end = (first, last) if not explicit_range else (
        _date(start, "start"), _date(end, "end")
    )
    if not first <= start <= end <= last:
        raise ValueError("requested range outside declared evaluation period")
    calendar = [d for d in axis if start <= d <= end]
    selected = frame[(frame.date >= start) & (frame.date <= end)].copy()
    expected_assets = sorted(contract["universe"]["assets"])
    if not expected_assets or len(expected_assets) != len(set(expected_assets)):
        raise ValueError("invalid declared asset universe")
    missing_dates = sorted(set(calendar) - set(selected.date))
    by_date = selected.groupby("date").asset.apply(lambda x: sorted(x.tolist())).to_dict()
    incomplete = {d: a for d, a in by_date.items() if a != expected_assets}
    reasons = []
    if contract["dependence"].get("axis_scope") != "evaluation":
        reasons.append("only the original evaluation time axis is supported")
    if contract["question"].get("sampling") != "daily":
        reasons.append("only daily observation contracts are supported")
    if len(calendar) < 2:
        reasons.append("fewer than two declared dates")
    if missing_dates:
        reasons.append("planned dates lack predictions; do not compress or fill the axis")
    if incomplete:
        reasons.append("asset pool is not identical on every date; weights would change")
    selected_folds = sorted(selected.fold.unique().tolist())
    if len(selected_folds) > 1:
        reasons.append("multiple fitted periods; inspect a declared explicit period separately")
    metric = "Brier" if binary else "MSE"
    unit = "probability_squared" if binary else "percentage_point_squared"
    summary = {
        "status": "not_applicable" if reasons else "ready",
        "reasons": reasons, "range": [start, end], "explicit_range": explicit_range,
        "planned_dates": len(calendar), "prediction_dates": int(selected.date.nunique()),
        "prediction_rows": len(selected), "assets": expected_assets,
        "missing_dates": missing_dates, "incomplete_asset_dates": incomplete,
        "folds": selected_folds, "weighting": policy,
        "baseline": baseline, "candidate": "B2", "metric": metric, "unit": unit,
        "positive_means": "candidate has lower squared prediction error",
        "original_primary_metric": contract["question"].get("primary_metric"),
        "scope": "auxiliary calculation on already-seen saved predictions; no new fit or evidence",
    }
    if reasons:
        return summary, None
    with np.errstate(over="ignore", invalid="ignore"):
        old_loss = (selected[baseline].to_numpy(float) - selected.y.to_numpy(float)) ** 2
        new_loss = (selected.B2.to_numpy(float) - selected.y.to_numpy(float)) ** 2
        improvement = old_loss - new_loss
    if not np.isfinite(improvement).all() or not np.isfinite(old_loss).all() or not np.isfinite(new_loss).all():
        raise ValueError("squared error overflow")
    # Same complete asset pool every day makes equal_asset and equal_date agree.
    daily = selected.assign(improvement=improvement).groupby("date").improvement.mean()
    summary["paired_scores"] = {
        "baseline": float(old_loss.mean()), "candidate": float(new_loss.mean()),
        "improvement": float(improvement.mean()),
    }
    packet = {
        "metric": f"{baseline} minus B2 daily {metric} improvement", "unit": unit,
        "frequency": "qualified_session", "calendar": calendar,
        "observations": [{"date": d, "difference": float(daily[d])} for d in calendar],
    }
    return summary, packet


def inspect_workflow(run_dir, *, baseline="B1", start=None, end=None):
    contract, result, proof, integrity = read_archived_run(run_dir)
    summary, packet = prepare_workflow_input(contract, result, proof,
                                           baseline=baseline, start=start, end=end)
    summary["source"] = integrity
    return summary, packet
