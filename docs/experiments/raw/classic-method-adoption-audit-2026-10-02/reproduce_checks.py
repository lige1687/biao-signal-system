"""Repository-contained synthetic audit. Never reads market data or fits market models."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from lei_signal.research.workflow import render_report
from lei_signal.research.workflow_evaluation import summarize_predictions


def main():
    batch = 2 if sys.argv[1:] == ["--retry-fixtures"] else 1
    suffix = "" if batch == 1 else "-batch02"
    result_path = OUT / f"check-results{suffix}.json"
    if result_path.exists():
        raise RuntimeError("Preserve recorded check results; do not overwrite")
    unit = runpy.run_path(str(ROOT / "tests/unit/test_workflow_evaluation.py"))
    contract = unit["contract"]()
    contract.update(
        data={"mode": "synthetic"},
        publication={"conclusion": "not_supported"},
        question={"question_id": "classic-adoption-counterexample", "added_information": "新增方法优于原模型但不如简单参照，是否仍清楚展示？", "period": ["2022-01-04", "2022-01-05"]},
        universe={"assets": ["a", "b"]},
        controller_review={"conclusion_scope": "人工手算只验证报告行为"},
        feature={"kind": "sma_distance"},
    )
    rows = [unit["prediction"](asset, day, 0, 0, 3, 2) for asset, day in [("a", 4), ("b", 5)]]
    result = summarize_predictions(rows, contract)
    observed = {item["old_model"]: item["absolute_error_improvement"] for item in result["increments"]}
    assert observed == {"B1": 5.0, "B0": -4.0}, observed
    assert any("underperforms B0" in warning for warning in result["warnings"])
    proof = {"coverage": {"actual_assets": ["a", "b"], "evaluation_rows": 2, "evaluation_dates": 2, "partial": False}, "warnings": []}
    report = render_report(contract, proof, result)
    assert "| B2 相对 B1 | 9 | 4 | 5 |" in report
    assert "| B2 相对 B0 | 0 | 4 | -4 |" in report
    assert "加入候选后的方法在这一对照下更差" in report
    if batch == 1:
        (OUT / "hand-example.json").write_text(json.dumps({"contract": contract, "result": result, "passed": True}, ensure_ascii=False, indent=2) + "\n")
        (OUT / "hand-example-report.md").write_text(report)
    selected = [
        "tests/integration/test_research_workflow_entry.py::test_baseline_or_unit_omission_blocks_publication_not_bad_effect",
        "tests/integration/test_research_workflow_entry.py::test_missing_evaluation_predictions_and_wrong_baseline_block_real_publication",
        "tests/integration/test_research_workflow_entry.py::test_bypassed_outputs_cannot_register_and_existing_outputs_preserved",
        "tests/unit/test_workflow_evaluation.py::test_year_direction_reversal_and_few_dates_warn_not_fail",
        "tests/unit/test_workflow_evaluation.py::test_weighting_good_bad_pair_and_units",
        "tests/unit/test_workflow_evaluation.py::test_b50_exact_and_bad_probability_labels_baselines",
        "tests/unit/test_workflow_evaluation.py::test_negative_complex_prediction_warns_and_does_not_fail",
        "tests/unit/test_workflow_evaluation.py::test_paired_identity_missing_model_duplicate_and_correct_observation",
    ]
    # Never let pytest clean a pre-existing work area or write outside this repository.
    if batch == 2:
        selected = selected[:3]  # Only retry the three fixtures that never ran.
    base = OUT / "engineering" / f"pytest-{batch:02}"
    base.parent.mkdir(parents=True, exist_ok=True)
    if base.exists():
        raise RuntimeError("Preserve previous evidence: choose a fresh directory for an authorized rerun")
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(base), *selected]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / f"engineering-checks{suffix}.txt").write_text(completed.stdout)
    paths = ["src/lei_signal/research/workflow.py", "src/lei_signal/research/workflow_evaluation.py", "tests/integration/test_research_workflow_entry.py", "tests/unit/test_workflow_evaluation.py"]
    summary = {"batch": batch, "synthetic_only": True, "hand_example_passed": True, "selected_tests": selected, "pytest_exit_code": completed.returncode, "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}
    result_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(completed.stdout)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
