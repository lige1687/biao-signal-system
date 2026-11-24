"""Bounded synthetic comparison of exact Git snapshots; no market data or fits.

Only prepare_workflow_input is extracted from the owned bridge. Full workflow
imports, data qualification, account policies and root integration are untested.
"""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import subprocess
import sys

import numpy as np

OWN = "59826afc936835e7ef38d3f1d832812b03abdc68"
PUBLISHED = "d444316817e9330c2d72a4a90c655467b45dd5bb"
PACKET = "docs/archive/handoffs-plans/external-quant-handoff-2026-10-03"
EVALUATOR = "src/lei_signal/research/workflow_evaluation.py"
BRIDGE = ".agents/skills/lei-quant-tools/scripts/workflow_bridge.py"


def blob(root, commit, path):
    return subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{path}"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    inventory = json.loads(blob(root, OWN, PACKET + "/evidence/source-snapshot.json"))
    entry = next(r for r in inventory["files"] if r["source_path"] == EVALUATOR)
    frozen = blob(root, OWN, PACKET + "/" + entry["package_path"])
    assert hashlib.sha256(frozen).hexdigest() == entry["sha256"]
    published = blob(root, PUBLISHED, EVALUATOR)
    bridge = blob(root, OWN, BRIDGE)
    node = next(n for n in ast.parse(bridge).body
                if isinstance(n, ast.FunctionDef) and n.name == "prepare_workflow_input")
    prepare_code = compile(ast.Module(body=[node], type_ignores=[]), BRIDGE, "exec")
    environments = {}
    fit_calls = []

    def prohibited(*args, **kwargs):
        fit_calls.append(True)
        raise AssertionError("compatibility check must not fit or evaluate market data")

    for name, source in (("frozen", frozen), ("published", published)):
        namespace = {"__name__": "compatibility_" + name}
        exec(compile(source, EVALUATOR, "exec"), namespace)
        namespace["_ridge"] = prohibited
        namespace["evaluate_observations"] = prohibited
        namespace["np"] = np
        exec(prepare_code, namespace)
        environments[name] = namespace

    days = ["2026-01-02", "2026-01-03", "2026-01-04"]
    contract = {
        "target": {"kind": "forward_return", "unit": "percentage_point"},
        "weights": {"policy": "equal_date", "comparison": "fixed_common"},
        "dependence": {"axis_scope": "evaluation", "block_length": 1, "draws": 1, "seed": 0},
        "question": {"sampling": "daily", "primary_metric": "MSE"},
        "split": {"label_policy": "purge", "folds": [
            {"train_end": "2026-01-01", "eval_start": days[0], "eval_end": days[-1]}]},
        "calendar": days,
        "universe": {"assets": ["synthetic-A", "synthetic-B"]},
    }
    observations, predictions = [], []
    for day in days:
        for i, asset in enumerate(contract["universe"]["assets"]):
            row = {"id": asset + "|" + day, "asset": asset, "date": day,
                   "stratum": asset + "|2026", "features": {}, "eligible": True,
                   "y": float(i + 1), "label_end": day, "label_reason": None,
                   "tested_condition": None}
            observations.append(row)
            predictions.append({k: row[k] for k in ("id", "asset", "date", "y", "label_end")}
                               | {"fold": "0", "B0": 0.0, "B1": 1.0, "B2": 2.0})
    cases = []
    for name in ("complete", "missing_date", "incomplete_asset", "identity_mismatch",
                 "nonfinite_prediction", "duplicate_calendar", "multiple_fitted_periods",
                 "forward_volatility_counterexample"):
        c, rows, proof = copy.deepcopy(contract), copy.deepcopy(predictions), copy.deepcopy(observations)
        if name == "missing_date":
            rows = [r for r in rows if r["date"] != days[1]]
        elif name == "incomplete_asset":
            rows.pop()
        elif name == "identity_mismatch":
            rows[0]["y"] = 9.0
        elif name == "nonfinite_prediction":
            rows[0]["B2"] = float("inf")
        elif name == "duplicate_calendar":
            c["calendar"].append(days[-1])
        elif name == "multiple_fitted_periods":
            c["split"]["folds"] = [
                {"train_end": "2026-01-01", "eval_start": days[0], "eval_end": days[0]},
                {"train_end": days[0], "eval_start": days[1], "eval_end": days[-1]}]
            for r in rows:
                r["fold"] = "0" if r["date"] == days[0] else "1"
        elif name == "forward_volatility_counterexample":
            c["target"]["kind"] = "forward_volatility"
        outcomes = {}
        for version, ns in environments.items():
            try:
                summary, packet = ns["prepare_workflow_input"](c, {"predictions": rows},
                                                               {"observations": proof})
                outcomes[version] = {"status": summary["status"], "summary": summary, "packet": packet}
            except ValueError as exc:
                outcomes[version] = {"status": "rejected", "error": str(exc)}
        same = outcomes["frozen"] == outcomes["published"]
        if name == "forward_volatility_counterexample":
            assert not same and outcomes["frozen"]["status"] == "ready"
            assert outcomes["published"]["status"] == "rejected"
        else:
            assert same, name
        cases.append({"case": name, "same_result": same, "outcomes": outcomes})
    expected = ["ready", "not_applicable", "not_applicable", "rejected",
                "rejected", "rejected", "not_applicable"]
    assert [r["outcomes"]["published"]["status"] for r in cases[:7]] == expected
    assert not fit_calls
    print(json.dumps({"mode": "synthetic extracted-function compatibility only", "own_commit": OWN,
                      "published_commit": PUBLISHED,
                      "source_sha256": {"frozen_evaluator": hashlib.sha256(frozen).hexdigest(),
                                        "published_evaluator": hashlib.sha256(published).hexdigest(),
                                        "owned_bridge": hashlib.sha256(bridge).hexdigest()},
                      "python": sys.version.split()[0], "numpy": np.__version__,
                      "cases": cases, "agreed_current_use_cases": 7,
                      "confirmed_capability_difference": "forward_volatility",
                      "actual_fits": 0, "market_data_reads": 0,
                      "full_import_or_root_integration": "not verified"}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
