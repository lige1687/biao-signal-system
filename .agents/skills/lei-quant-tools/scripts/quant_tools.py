"""Bounded research utilities and archived input bridge; no network or writes."""
from __future__ import annotations

import argparse
from datetime import date
import json
import math
from pathlib import Path

import numpy as np

from statsmodels_hac import S_hac_simple


def _date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("require an ISO date")
    return value


def mean_hac(payload):
    for key in ("metric", "unit", "frequency"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"declare {key}")
    calendar = [_date(d) for d in payload["calendar"]]
    if calendar != sorted(set(calendar)) or len(calendar) < 2:
        raise ValueError("calendar must be ordered, unique and contain at least two observations")
    rows = payload["observations"]
    if [_date(r["date"]) for r in rows] != calendar:
        raise ValueError("observations must match the complete declared calendar exactly")
    nlags = payload["nlags"]
    if type(nlags) is not int or not 0 <= nlags < len(rows):
        raise ValueError("nlags must be an explicit integer within the observation count")
    values = []
    for row in rows:
        value = row["difference"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("difference must be a finite number; no missing-value filling")
        values.append(value)
    series = np.asarray(values, dtype=float)
    average = float(series.mean())
    centered = series - average
    variance = float(S_hac_simple(centered, nlags=nlags)[0, 0] / len(series) ** 2)
    if not math.isfinite(average) or not math.isfinite(variance) or variance < 0:
        raise ValueError("nonfinite mean or invalid estimated variance")
    return {
        "metric": payload["metric"], "unit": payload["unit"],
        "frequency": payload["frequency"], "n": len(series), "nlags": nlags,
        "mean_difference": average, "mean_variance": variance,
        "mean_standard_error": math.sqrt(variance),
        "method": "statsmodels-0.15.0 S_hac_simple; Bartlett; no finite-sample correction",
        "scope": "declared consecutive equal-interval observations; not a strategy-effectiveness verdict",
        "warning": "declared calendar is not independently qualified by this utility"
                   + ("; constant series does not establish certainty" if variance == 0 else ""),
    }


def xshg_date(day):
    day = _date(day)
    snapshot_path = Path(__file__).resolve().parents[1] / "references/xshg-2026.json"
    snapshot = json.loads(snapshot_path.read_text())
    result = {"date": day, "exchange": "XSHG", "source_version": snapshot["source_version"],
              "official_crosscheck": snapshot["official_crosscheck"],
              "scope": snapshot["scope"], "historical_arrival": "unknown"}
    if not day.startswith("2026-"):
        return {**result, "status": "unknown", "reason": "outside checked year"}
    closed = date.fromisoformat(day).weekday() >= 5 or day in snapshot["holidays"]
    return {**result, "status": "scheduled_closed" if closed else "scheduled_open",
            "reason": "annual schedule only; does not verify subsequent changes or tradability"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("mean-hac").add_argument("input", type=Path)
    commands.add_parser("xshg-date").add_argument("date")
    preview = commands.add_parser("candidate-preview")
    preview.add_argument("input", type=Path)
    preview.add_argument("--as-of", required=True)
    for command in ("workflow-check", "workflow-hac"):
        sub = commands.add_parser(command)
        sub.add_argument("run_dir", type=Path)
        sub.add_argument("--baseline", choices=["B0", "B1", "B50"], default="B1")
        sub.add_argument("--start")
        sub.add_argument("--end")
        if command == "workflow-hac":
            sub.add_argument("--nlags", required=True, type=int)
    args = parser.parse_args()
    try:
        if args.command == "mean-hac":
            result = mean_hac(json.loads(args.input.read_text()))
        elif args.command == "xshg-date":
            result = xshg_date(args.date)
        elif args.command == "candidate-preview":
            from tsfresh_candidates import candidate_preview
            result = candidate_preview(json.loads(args.input.read_text()), args.as_of)
        else:
            from workflow_bridge import inspect_workflow
            result, packet = inspect_workflow(args.run_dir, baseline=args.baseline,
                                              start=args.start, end=args.end)
            if args.command == "workflow-hac":
                result["hac"] = mean_hac({**packet, "nlags": args.nlags}) if packet else None
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"input rejected: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    if result.get("status") == "not_applicable":
        parser.exit(2)


if __name__ == "__main__":
    main()
