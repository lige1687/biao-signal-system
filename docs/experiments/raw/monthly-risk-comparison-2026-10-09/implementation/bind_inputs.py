"""One preparation binding to the exact A delivery; computes no new ratios/accounts."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True

import csv
import json
from pathlib import Path
import subprocess

from execution_guard import sha256, verify_file, require, PATH_IDS, now
from input_adapter import load_bound_dataset
from runner import HERE, CODE_FILES, storage_module, STORAGE_ROOT, TASK, ESTIMATED_BYTES, INTERNAL_BYTES

A_COMMIT = "29337ec9e6560171c459019834638ce2c6993ef9"
A_MANIFEST = Path("/Users/yongbiaoli/.codex/worktrees/leisignal-risk-input-20261009/lei-signal-lab/docs/experiments/raw/monthly-risk-comparison-2026-10-09/inputs/manifest.json")
A_HASH = "9f1c326b46e7afc22d2ad6454e9f754e64540442e120412326ce270a50799baf"
A_RELATIVE = "docs/experiments/raw/monthly-risk-comparison-2026-10-09/inputs/manifest.json"


def save_new(path, value):
    with path.open("x") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    require(not (HERE/"contract.json").exists(), "binding already frozen; preserve it before any authorized correction")
    raw = subprocess.check_output(["git", "show", A_COMMIT+":"+A_RELATIVE], cwd=HERE)
    require(A_MANIFEST.read_bytes() == raw and sha256(A_MANIFEST) == A_HASH, "A local/Git manifest mismatch")
    A = json.loads(raw)
    require(A["status"] == "inputs_ready_with_retrospective_limits" and not A["blocking_missing_inputs"], "A not ready")
    draft = json.loads((HERE/"contract-draft.json").read_text())
    storage = storage_module(draft)
    plan = json.loads((HERE/"storage-plan.json").read_text())
    storage.recheck_saved_plan(STORAGE_ROOT, plan, TASK, ESTIMATED_BYTES, INTERNAL_BYTES)
    closure = [{"id": a["id"], "path": a["read_path"], "sha256": a["sha256"], "bytes": a["bytes"]} for a in A["artifacts"]]
    source = {a["id"]: a for a in closure}
    mapping = {f"A_{name.upper()}-{fee}": f"original_a_{name}_{fee}_daily"
               for name in ("all", "sma") for fee in ("base", "stress")}
    mapping.update({f"A_{name.upper()}-{fee}-ledger": f"original_a_{name}_{fee}_ledger"
                    for name in ("all", "sma") for fee in ("base", "stress")})
    for fee in ("base", "stress"):
        mapping[f"B0-{fee}"] = f"original_b0_{fee}_daily"
        mapping[f"B0-{fee}-ledger"] = f"original_b0_{fee}_ledger"
    mapping.update(quotes="original_nominal_quotes", calendar="original_calendar",
                   execution_reference="original_510300_execution_reference",
                   mapped_actions="original_510300_mapped_actions")
    initial = {}
    for path_id in PATH_IDS:
        item = source[mapping[path_id]]
        verify_file(item)
        with Path(item["path"]).open(newline="") as f:
            row = next(r for r in csv.DictReader(f) if r["date"] == "2025-12-31")
        fee = path_id.split("-")[1]
        require(row["cash"] == A["initial_new_comparison_cash"][fee], "A initial cash manifest disagrees")
        initial[path_id] = {k: row[k] for k in ("date", "cash", "units", "receivable", "wealth")}
    binding = {"schema": "monthly-risk-consumption-binding/1", "status": "bound_to_A_inputs_ready",
               "created_at": now(), "A_task_id": "leisignal-risk-input-20261009", "A_result_commit": A_COMMIT,
               "A_manifest": {"path": str(A_MANIFEST), "sha256": A_HASH, "bytes": len(raw)},
               "source_closure": closure, "files": {role: source[name] for role, name in mapping.items()},
               "initial_states": initial, "monthly_calendar_cutoffs": A["monthly_cutoffs"],
               "retained_A_qualification_limits": A["qualification_limits"],
               "B_qualification_not_replacing_A": True}
    dataset = load_bound_dataset(binding)
    # Only input consumption compatibility is checked, never any new account.
    save_new(HERE/"consumption-binding.json", binding)
    synthetic = sorted(HERE.glob("synthetic-evidence-*.json"))[-1]
    require(json.loads(synthetic.read_text())["engineering_checks_passed"], "latest artificial evidence failed")
    contract = {**draft, "status": "frozen_for_C_review", "frozen_at": now(),
                "inputs": {"status": "A_inputs_ready_with_retrospective_limits", "path": str(A_MANIFEST),
                           "sha256": A_HASH, "result_commit": A_COMMIT},
                "A_git_reference": {"task_id": "leisignal-risk-input-20261009", "commit": A_COMMIT,
                                    "path": A_RELATIVE, "sha256": A_HASH},
                "consumption_binding": {"path": str(HERE/"consumption-binding.json"),
                                        "sha256": sha256(HERE/"consumption-binding.json"),
                                        "bytes": (HERE/"consumption-binding.json").stat().st_size},
                "code_sha256": {name: sha256(HERE/name) for name in CODE_FILES},
                "synthetic_evidence": {"path": str(synthetic), "bytes": synthetic.stat().st_size,
                                       "sha256": sha256(synthetic)},
                "monthly_calendar_cutoffs": A["monthly_cutoffs"],
                "retained_input_limits": A["qualification_limits"],
                "author_budget_owner": "B; exact human authorization remains not_granted; no run release from this binding"}
    contract["rules"]["cutoff"] = "Jan..Jun每月以此前完整自然月末为资料截止，观察止于该月最后官方交易日；只用过去63共同日。两档费用共用各A基础费比例。"
    contract["rules"]["month_end"] = "目标只在自然月末结束后供次月开盘使用；同时保存自然月末截止和最后交易日，不把休市日当新行情。"
    save_new(HERE/"contract.json", contract)
    receipt = {"status": "implementation_ready_for_review", "A_manifest_sha256": A_HASH,
               "A_result_commit": A_COMMIT, "source_closure_verified": len(closure),
               "period_trading_dates": len(dataset["period_trading"]), "period_natural_dates": 181,
               "in_period_actions": dataset["actions"], "restrictions": dataset["restrictions"],
               "historical_ratios_computed": 0, "historical_path_attempts": 0,
               "C_acceptance": False, "user_authorized_paths": 0,
               "contract_sha256": sha256(HERE/"contract.json"), "generated_at": now()}
    save_new(HERE/"input-consumption-receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
