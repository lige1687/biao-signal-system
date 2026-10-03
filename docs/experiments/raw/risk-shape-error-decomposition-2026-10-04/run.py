"""Read-only arithmetic decomposition of the sealed vol_instability20-main predictions."""

import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.workflow import digest  # noqa: E402
from lei_signal.research.workflow_evaluation import (  # noqa: E402
    EvaluationError, _folds, _paired_predictions, _weights,
)

HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / "docs/experiments/raw/risk-shape-information-2026-10-03/run-vol_instability20-main"
NAMES = ("contract.json", "preflight.json", "result.json", "receipt.json", "report.md")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def reject_cases(row, contract):
    folds, axis = _folds(contract), contract["calendar"]
    cases = {}

    def rejects(name, rows):
        try:
            _paired_predictions(rows, False, folds, axis)
        except EvaluationError as exc:
            cases[name] = {"passed": True, "reason": str(exc)}
        else:
            raise AssertionError(f"{name}: invalid synthetic rows accepted")

    rejects("duplicate_id_and_asset_date", [dict(row), dict(row)])
    missing = dict(row)
    del missing["B2"]
    rejects("missing_prediction_column", [missing])
    missing_row = dict(row)
    missing_row["date"] = "2025-01-03"
    missing_row["id"] = "synthetic-missing-partner"
    # A required common partner is not silently recovered from a one-model row.
    del missing_row["B1"]
    rejects("missing_B1_partner", [missing_row])
    for name, bad in (("nan", float("nan")), ("infinity", float("inf"))):
        changed = dict(row)
        changed["B2"] = bad
        rejects(name, [changed])
    same = dict(row)
    same["B2"] = same["B1"]
    same_frame = _paired_predictions([same], False, folds, axis)
    equal_delta = (same_frame.y.iloc[0] - same_frame.B1.iloc[0]) ** 2 - (same_frame.y.iloc[0] - same_frame.B2.iloc[0]) ** 2
    assert equal_delta == 0
    cases["same_prediction_zero_difference"] = {"passed": True, "difference": float(equal_delta)}
    exact = dict(row)
    exact["B1"] = exact["y"]
    exact["B2"] = exact["y"]
    exact_frame = _paired_predictions([exact], False, folds, axis)
    exact_loss = (exact_frame.y.iloc[0] - exact_frame.B1.iloc[0]) ** 2
    assert exact_loss == 0
    cases["zero_error_both"] = {"passed": True, "loss": float(exact_loss)}
    complete = [dict(row, id=f"{asset}|{row['date']}", asset=asset)
                for asset in ("510050.SS", "510500.SS", "588000.SS")]
    assert len(_paired_predictions(complete, False, folds, axis)) == 3
    try:
        require_three_assets(_paired_predictions(complete[:2], False, folds, axis))
    except AssertionError:
        cases["missing_asset_row"] = {"passed": True, "reason": "fixed three-asset date is incomplete"}
    else:
        raise AssertionError("missing_asset_row: incomplete date accepted")
    return cases


def require_three_assets(frame):
    expected = {"510050.SS", "510500.SS", "588000.SS"}
    assert all(set(group.asset) == expected for _, group in frame.groupby("date")), "fixed three-asset date is incomplete"


def main():
    started = time.monotonic()
    contract = json.loads((ORIGINAL / "contract.json").read_text())
    proof = json.loads((ORIGINAL / "preflight.json").read_text())
    result = json.loads((ORIGINAL / "result.json").read_text())
    receipt = json.loads((ORIGINAL / "receipt.json").read_text())
    assert contract["target"]["kind"] == "mae" and contract["target"]["unit"] == "percentage_point"
    assert contract["weights"] == {"policy": "equal_asset", "comparison": "fixed_common"}
    assert len(result["predictions"]) == 951
    hashes = {name: sha(ORIGINAL / name) for name in NAMES}
    assert hashes["contract.json"] == receipt["contract_sha256"]
    for name, expected in receipt["outputs"].items():
        assert hashes[name] == expected, f"old receipt mismatch: {name}"
    assert digest(proof["observations"]) == contract["freeze"]["observations_digest"]
    assert digest({key: val for key, val in proof.items() if key != "observations"}) == contract["freeze"]["preflight_digest"]
    assert proof["cache_keys"] == receipt["cache_keys"]

    # Check every frozen input and binding without modifying its source.
    expected_paths = dict(contract["bindings"]["files"])
    for source in contract["sources"]:
        path, expected = source["path"], source["sha256"]
        assert expected_paths.get(path, expected) == expected, f"source/binding conflict: {path}"
        expected_paths[path] = expected
    checked = []
    for name, expected in sorted(expected_paths.items()):
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        actual = sha(path) if path.is_file() else None
        checked.append({"path": name, "expected_sha256": expected, "actual_sha256": actual,
                        "matches": actual == expected, "exists": path.is_file()})
    mismatches = [x for x in checked if not x["matches"]]

    frame = _paired_predictions(result["predictions"], False, _folds(contract), contract["calendar"])
    weights = _weights(frame, "equal_asset")
    assert len(frame) == 951 and frame.date.nunique() == 317 and frame.asset.nunique() == 3
    assert set(frame.asset) == {"510050.SS", "510500.SS", "588000.SS"}
    require_three_assets(frame)
    assert len(frame) == len(result["predictions"])
    assert len(set(frame.id)) == len(frame)
    assert len(set(zip(frame.asset, frame.date))) == len(frame)
    y, b1, b2 = (frame[c].to_numpy(float) for c in ("y", "B1", "B2"))
    old_loss, new_loss = (y - b1) ** 2, (y - b2) ** 2
    difference = old_loss - new_loss
    contribution = weights * difference
    assert np.isfinite(np.column_stack((weights, old_loss, new_loss, difference, contribution))).all()
    old_mse, new_mse = float(weights @ old_loss), float(weights @ new_loss)
    original = next(x for x in result["increments"] if x["old_model"] == "B1" and x["new_model"] == "B2")
    assert math.isclose(old_mse, original["old_value"], rel_tol=0, abs_tol=1e-12)
    assert math.isclose(new_mse, original["new_value"], rel_tol=0, abs_tol=1e-12)
    assert math.isclose(float(contribution.sum()), original["absolute_error_improvement"], rel_tol=0, abs_tol=1e-12)
    assert math.isclose(old_mse - new_mse, float(contribution.sum()), rel_tol=0, abs_tol=1e-12)

    rows = []
    date_contrib = {}
    for i, raw in enumerate(result["predictions"]):
        sign = "better" if difference[i] > 0 else "worse" if difference[i] < 0 else "same"
        row = {**raw, "weight_equal_asset": float(weights[i]), "B1_squared_error": float(old_loss[i]),
               "B2_squared_error": float(new_loss[i]), "difference_old_minus_new": float(difference[i]),
               "weighted_difference": float(contribution[i]), "direction": sign}
        rows.append(row)
        date_contrib[raw["date"]] = date_contrib.get(raw["date"], 0.0) + float(contribution[i])
    with (HERE / "full-differences.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    signs = {}
    for sign in ("better", "same", "worse"):
        positions = [i for i, row in enumerate(rows) if row["direction"] == sign]
        signs[sign] = {"rows": len(positions), "weight": float(weights[positions].sum()),
                       "signed_contribution": float(contribution[positions].sum())}
    assert sum(item["rows"] for item in signs.values()) == 951
    assert math.isclose(sum(item["weight"] for item in signs.values()), 1.0, abs_tol=1e-12)
    assert math.isclose(sum(item["signed_contribution"] for item in signs.values()), original["absolute_error_improvement"], abs_tol=1e-12)
    ordered = sorted(date_contrib.items(), key=lambda item: (-abs(item[1]), item[0]))
    sensitivity = []
    for n in (1, 5, 10):
        removed = ordered[:n]
        sensitivity.append({"top_absolute_dates": n, "dates": [d for d, _ in removed],
                            "removed_contribution": float(sum(v for _, v in removed)),
                            "remaining_contribution_original_weights": float(contribution.sum() - sum(v for _, v in removed)),
                            "descriptive_only": True})
    summary = {"scope": "fixed saved B1/B2 predictions; no new fits", "unit_prediction": "percentage_point",
               "unit_squared_difference": "percentage_point_squared", "rows": 951, "dates": 317,
               "assets": sorted(frame.asset.unique().tolist()), "weights": "equal_asset over all paired rows",
               "B1_mse": old_mse, "B2_mse": new_mse, "B1_rmse": math.sqrt(old_mse),
               "B2_rmse": math.sqrt(new_mse), "net_weighted_improvement": float(contribution.sum()),
               "relative_percent": float(contribution.sum() / old_mse * 100), "signs": signs,
               "extreme_date_sensitivity": sensitivity, "original_increment": original,
               "date_contribution_count": len(date_contrib)}
    write_json("summary.json", summary)
    cases = reject_cases(result["predictions"][0], contract)
    verification = {"status": "arithmetic_verified", "original_run": str(ORIGINAL.relative_to(ROOT)),
                    "original_hashes_sha256": hashes, "receipt_and_freeze_match": True,
                    "source_and_binding_files_checked": len(checked), "source_and_binding_hash_checks": checked,
                    "source_or_binding_mismatches": mismatches,
                    "note_on_mismatches": "Current files may have changed since the sealed run; old receipt and archived predictions remain intact.",
                    "pairing_validator": "workflow_evaluation._paired_predictions",
                    "weight_validator": "workflow_evaluation._weights", "all_saved_rows_retained": len(rows) == len(result["predictions"]),
                    "every_prediction_date_has_exact_three_assets": True,
                    "mse_and_increment_match_original_at_1e-12": True, "synthetic_counterexamples": cases,
                    "outputs_sha256": {name: sha(HERE / name) for name in ("full-differences.csv", "summary.json")},
                    "elapsed_seconds": time.monotonic() - started,
                    "budget_seconds": 600, "new_fits": 0, "new_labels": 0, "external_requests": 0}
    write_json("verification.json", verification)
    print(json.dumps({"summary": summary, "mismatches": len(mismatches), "elapsed_seconds": verification["elapsed_seconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
