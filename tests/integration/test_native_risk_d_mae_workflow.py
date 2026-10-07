"""Run the existing Factor Lab CLI through both artificial D-MAE20 stages."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tests.unit.test_native_risk_d_mae_workflow import artificial_inputs

REPO = Path(__file__).resolve().parents[2]


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _call(root, *args):
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, str(root / "scripts/run_factor_lab.py"), *map(str, args)],
                          cwd=root, env=env, capture_output=True, text=True, check=False)


def _contract(stage, x_sha, family, *, y_sha=None, x_receipt_sha=None):
    contract = {
        "schema_version": "research-workflow/d-mae20/1.0",
        "study_id": "frozen_d_close_mae20",
        "stage": stage,
        "feature": {"kind": "native_risk_d_mae20"},
        "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                   "entry_field": "close", "path_field": "close",
                   "unit": "percentage_point", "cutoff": "2026-06-26"},
        "comparison": {"candidate": "D", "benchmark": "V",
                       "evaluator": "signed_spearman_equal_asset_fixed_groups/1.0",
                       "deletion_groups": 33, "fits": 0},
        "data": {"mode": "synthetic", "artificial_only": True,
                 "x_path": "inputs/x.json", "x_sha256": x_sha},
        "sources": {"design_sha256": "ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6",
                    "synthetic_math_sha256": "84f4fee2a538a918352bca099ec9c9b4a38f6d6a19dab5faa564b668c0bd8745"},
        "history": {"family": family},
        "budget": {"execution_seconds": 120, "stage_runs": 2},
        "permissions": {"real_X": False, "real_Y": False, "real_fits": 0,
                        "market_requests": 0, "paid_requests": 0, "production": False},
        "publication": {"conclusion": "synthetic_engineering_only", "register_report": False},
    }
    if stage == "y":
        contract["data"].update({"y_path": "inputs/y.json", "y_sha256": y_sha})
        contract["x_receipt"] = {"path": "runs/x", "sha256": x_receipt_sha}
    return contract


def _isolated_root(tmp_path):
    root = tmp_path / "independent-root"
    shutil.copytree(REPO / "src/lei_signal", root / "src/lei_signal")
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(REPO / "scripts/run_factor_lab.py", root / "scripts/run_factor_lab.py")
    (root / "configs").mkdir(parents=True)
    shutil.copy2(REPO / "configs/strategy-documents.v1.json", root / "configs/strategy-documents.v1.json")
    return root


def test_cli_x_then_one_y_restart_verify_and_repeat_rejection(tmp_path):
    root = _isolated_root(tmp_path)
    x, y = artificial_inputs()
    x_sha = _write_json(root / "inputs/x.json", x)
    y_sha = _write_json(root / "inputs/y.json", y)
    family = "native-d-mae20-synthetic-integration-one"
    _write_json(root / "inputs/draft-x.json", _contract("x", x_sha, family))

    declaration = _call(root, "--review-workflow-contract", "inputs/draft-x.json")
    assert declaration.returncode == 0, declaration.stderr
    assert json.loads(declaration.stdout)["execution_authorized"] is False
    freeze_x = _call(root, "--workflow-draft", "inputs/draft-x.json", "--out", "runs/frozen-x")
    assert freeze_x.returncode == 0, freeze_x.stderr
    run_x = _call(root, "--workflow-contract", "runs/frozen-x/contract.json", "--out", "runs/x")
    assert run_x.returncode == 0, run_x.stderr
    x_result = json.loads((root / "runs/x/result.json").read_text())
    assert x_result["stage"] == "x" and len(x_result["rows"]) == 76
    assert all("Y" not in row and "closes" not in row for row in x_result["rows"])
    assert "validated_paths" not in json.loads((root / "runs/x/preflight.json").read_text())
    assert json.loads((root / "runs/x/state.json").read_text())["evidence"] == "synthetic_engineering_only"

    receipt_sha = hashlib.sha256((root / "runs/x/receipt.json").read_bytes()).hexdigest()
    _write_json(root / "inputs/draft-y.json", _contract("y", x_sha, family, y_sha=y_sha, x_receipt_sha=receipt_sha))
    freeze_y = _call(root, "--workflow-draft", "inputs/draft-y.json", "--out", "runs/frozen-y")
    assert freeze_y.returncode == 0, freeze_y.stderr
    run_y = _call(root, "--workflow-contract", "runs/frozen-y/contract.json", "--out", "runs/y")
    assert run_y.returncode == 0, run_y.stderr
    result = json.loads((root / "runs/y/result.json").read_text())
    assert result["stage"] == "y" and result["mature_count"] == 75
    assert len(result["rows"]) == 76 and sum(row["Y"] is not None for row in result["rows"]) == 75
    assert len(result["statistics"]["leave_one_lifecycle"]) == 33
    assert result["real_X"] == result["real_Y"] == result["fits"] == 0
    assert json.loads((root / "runs/y/state.json").read_text())["execution"] == "completed"

    fresh_process = subprocess.run([sys.executable, "-c",
        "from lei_signal.research.workflow import check_publication; print(check_publication('runs/y')['execution'])"],
        cwd=root, env={**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, check=False)
    assert fresh_process.returncode == 0 and fresh_process.stdout.strip() == "completed", fresh_process.stderr

    repeat = _call(root, "--workflow-contract", "runs/frozen-y/contract.json", "--out", "runs/y-repeat")
    assert repeat.returncode == 3 and "stage already started" in repeat.stderr
    assert (root / "runs/y-repeat/failure.json").is_file()
    journal = next((root / "docs/experiments/raw/research-workflow-ledgers-2026-09-29").glob("*/attempts.jsonl"))
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [r["stage"] for r in events if r["event"] == "start"] == ["x", "y"]
    assert [r["stage"] for r in events if r["event"] == "finish" and r["status"] == "computed"] == ["x", "y"]

    (root / "runs/y/result.json").write_text("{}\n", encoding="utf-8")
    tampered = subprocess.run([sys.executable, "-c",
        "from lei_signal.research.workflow import check_publication; check_publication('runs/y')"],
        cwd=root, env={**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, check=False)
    assert tampered.returncode != 0 and "receipt output changed" in tampered.stderr


def test_real_mode_rejected_before_any_artifact(tmp_path):
    root = _isolated_root(tmp_path)
    x, _ = artificial_inputs()
    x_sha = _write_json(root / "inputs/x.json", x)
    contract = _contract("x", x_sha, "native-d-mae20-synthetic-real-rejection")
    contract["data"]["mode"] = "historical_reconstruction"
    _write_json(root / "inputs/real-attempt.json", contract)
    result = _call(root, "--review-workflow-contract", "inputs/real-attempt.json")
    assert result.returncode == 3
    assert "artificial synthetic inputs only" in result.stdout


def test_bad_y_path_rejects_whole_batch_before_y_start(tmp_path):
    root = _isolated_root(tmp_path)
    x, y = artificial_inputs()
    x_sha = _write_json(root / "inputs/x.json", x)
    family = "native-d-mae20-synthetic-bad-path"
    _write_json(root / "inputs/draft-x.json", _contract("x", x_sha, family))
    assert _call(root, "--workflow-draft", "inputs/draft-x.json", "--out", "runs/frozen-x").returncode == 0
    assert _call(root, "--workflow-contract", "runs/frozen-x/contract.json", "--out", "runs/x").returncode == 0

    first = x["cases"][0]
    bad_day = y["windows"][first["case_id"]]["label_start"]
    y["prices"][first["asset"]][bad_day]["status"] = "halted"
    y_sha = _write_json(root / "inputs/y.json", y)
    receipt_sha = hashlib.sha256((root / "runs/x/receipt.json").read_bytes()).hexdigest()
    _write_json(root / "inputs/draft-y.json", _contract("y", x_sha, family,
                                                       y_sha=y_sha, x_receipt_sha=receipt_sha))
    rejected = _call(root, "--workflow-draft", "inputs/draft-y.json", "--out", "runs/frozen-y")
    assert rejected.returncode != 0
    assert "full 21-close path" in rejected.stderr
    assert not (root / "runs/frozen-y/contract.json").exists()
    journal = next((root / "docs/experiments/raw/research-workflow-ledgers-2026-09-29").glob("*/attempts.jsonl"))
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [r["stage"] for r in events if r["event"] == "start"] == ["x"]
