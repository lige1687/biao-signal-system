"""B's only prospective historical entry; frozen release REQUIRED to execute.

No historical run is permitted by this file's creation. Unregistered research
entry uses plan_output with its own checked closure and descriptor writes.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import traceback

from execution_guard import (TASK, PATH_IDS, sha256, require, verify_file, now,
                             validate_release, actual_attempts, claim_batch, claim_path, append_record)
from input_adapter import load_bound_dataset, saved_period_fee
from monthly_account import monthly_targets, simulate_monthly, metrics, number, opportunity_description

HERE = Path(__file__).resolve().parent
STORAGE_ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
ESTIMATED_BYTES, INTERNAL_BYTES = 16*1024*1024, 1024*1024
CODE_FILES = ["monthly_account.py", "execution_guard.py", "input_adapter.py", "runner.py", "synthetic_checks.py", "bind_inputs.py"]


def read_json(path):
    return json.loads(Path(path).read_text())


def storage_module(contract):
    entry = next(item for item in contract["sources"] if item["path"] == str(STORAGE_ROOT/"src/lei_signal/research/output_storage.py"))
    verify_file(entry)
    spec = importlib.util.spec_from_file_location("monthly_risk_storage", entry["path"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_artifact(reference, required_task):
    require(reference["task_id"] == required_task, "artifact owner task mismatch")
    role_dir = "inputs" if required_task == "leisignal-risk-input-20261009" else "review"
    require(reference["path"].startswith("docs/experiments/raw/monthly-risk-comparison-2026-10-09/"+role_dir+"/"), "foreign artifact path")
    data = subprocess.check_output(["git", "show", reference["commit"]+":"+reference["path"]], cwd=HERE)
    require(hashlib.sha256(data).hexdigest() == reference["sha256"], "Git artifact hash drift")
    return json.loads(data)


def load_execution_release():
    require((HERE/"contract.json").is_file(), "A-bound frozen contract missing; preparation only")
    contract = read_json(HERE/"contract.json")
    for item in contract["sources"]:
        verify_file(item)
    binding = read_json(verify_file(contract["consumption_binding"]))
    A_manifest = git_artifact(contract["A_git_reference"], "leisignal-risk-input-20261009")
    require(contract["A_git_reference"]["sha256"] == contract["inputs"]["sha256"] == binding["A_manifest"]["sha256"],
            "A Git/local/contract hash mismatch")
    require(contract["A_git_reference"]["commit"] == binding["A_result_commit"], "A commit binding mismatch")
    require(A_manifest, "empty A manifest")
    code = {name: sha256(HERE/name) for name in CODE_FILES}
    require(code == contract["code_sha256"], "frozen implementation drift")
    verify_file(contract["synthetic_evidence"])
    auth = read_json(HERE/"authorization.json")
    reference = read_json(HERE/"C-review-reference.json")
    review = git_artifact(reference, "leisignal-risk-review-20261009")
    attempted, started = actual_attempts(HERE/"attempts")
    release = validate_release(contract, sha256(HERE/"contract.json"), auth, review,
                               code, contract["inputs"]["sha256"], attempted, started)
    return contract, binding, release


class ExternalRun:
    """All large files anchored to the verified external device; no fallback."""
    def __init__(self, storage, plan):
        self.storage, self.plan = storage, plan
        self.run = Path(plan["run_directory"])
        self.output = Path(plan["output"])
        self.fd = None
        self.run_fd = None

    def check(self):
        require(self.storage._still_mounted(self.plan), "external disk lost; no internal fallback")
        if self.run_fd is not None:
            require(os.fstat(self.run_fd).st_dev == self.plan["external_device"], "run descriptor device mismatch")
        if self.fd is not None:
            require(os.fstat(self.fd).st_dev == self.plan["external_device"], "output descriptor device mismatch")

    def __enter__(self):
        self.check()
        self.storage._plain(self.run)
        self.storage._plain(self.output)
        parent = self.run.parent
        require(parent.parent.is_dir() and parent.parent.stat().st_dev == self.plan["external_device"], "external base lost")
        parent.mkdir(exist_ok=True)
        self.check()
        self.run.mkdir(exist_ok=False)
        self.run_fd = os.open(self.run, os.O_RDONLY|os.O_NOFOLLOW)
        self.check()
        os.mkdir("result", dir_fd=self.run_fd)
        self.fd = os.open("result", os.O_RDONLY|os.O_NOFOLLOW, dir_fd=self.run_fd)
        self.check()
        self.write("storage-plan.json", self.plan, run=True)
        os.environ["TMPDIR"] = str(self.run)
        return self

    def write(self, filename, value, run=False):
        require(Path(filename).name == filename, "only new direct output files allowed")
        self.check()
        data = (json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode()
        fd = os.open(filename, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600,
                     dir_fd=self.run_fd if run else self.fd)
        with os.fdopen(fd, "wb") as f:
            require(os.fstat(f.fileno()).st_dev == self.plan["external_device"], "file on wrong device")
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        self.check()
        path = (self.run if run else self.output)/filename
        require(path.read_bytes() == data, "external bytes readback differs")
        return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "device": self.plan["external_device"]}

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
        if self.run_fd is not None:
            os.close(self.run_fd)


def execute():
    contract, binding, release = load_execution_release()
    dataset = load_bound_dataset(binding)
    storage = storage_module(contract)
    plan = read_json(HERE/"storage-plan.json")
    storage.recheck_saved_plan(STORAGE_ROOT, plan, TASK, ESTIMATED_BYTES, INTERNAL_BYTES)
    # Fixed saved-account risk arithmetic; no new-account attempt yet. Failures
    # here consume no path and never turn invalid source data into a ratio.
    schedule = monthly_targets({name: dataset["accounts"][name+"-base"] for name in ("A_ALL", "A_SMA", "B0")},
                               dataset["trading_days"])
    start, end = contract["scope"]["start"], contract["scope"]["end"]
    outcomes, pointers = {}, {}
    run_id = plan["run_id"]
    with ExternalRun(storage, plan) as output:
        output.write("run-log.json", {"started_at": now(), "release": release, "run_id": run_id}, run=True)
        pointers["monthly-targets"] = output.write("monthly-targets.json", schedule)
        claim_batch(HERE/"attempts", release, run_id)
        for path_id in PATH_IDS:
            output.check()
            reference, fee_name = path_id.split("-")
            initial = number(dataset["initial_states"][path_id]["wealth"])
            fee = number(contract["scope"]["fees"][fee_name])
            claim_path(HERE/"attempts", path_id, release, run_id)
            try:
                account = simulate_monthly(cash=initial, fee=fee, targets=schedule[reference],
                                           quotes=dataset["quotes"], trading_days=dataset["period_trading"],
                                           restrictions=dataset["restrictions"], actions=dataset["actions"])
                own_metrics = metrics(account["daily"], initial, dataset["period_trading"], start, end)
                own_metrics.update(fees_2026h1=account["fees"], trade_count=len(account["fills"]))
                saved = [r for r in dataset["accounts"][path_id] if start <= r["date"] <= end]
                old_metrics = metrics(saved, initial, dataset["period_trading"], start, end)
                prior = dataset["maps"][path_id]["2025-12-31"]
                old_metrics["fees_2026h1"] = str(saved_period_fee(prior, saved[-1]))
                old_metrics["trade_count"] = sum(start <= f["date"] <= end for f in dataset["ledgers"][path_id]["fills"])
                sigma_a = old_metrics["trading_day_volatility"]
                ratio = own_metrics["trading_day_volatility"]/sigma_a if sigma_a else None
                b0 = [r for r in dataset["accounts"]["B0-"+fee_name] if start <= r["date"] <= end]
                b0_prior = dataset["maps"]["B0-"+fee_name]["2025-12-31"]["wealth"]
                outcome = {"path_id": path_id, "account": account, "metrics": own_metrics,
                           "saved_A_metrics": old_metrics, "volatility_ratio": ratio,
                           "within_0_90_to_1_10": ratio is not None and .90 <= ratio <= 1.10,
                           "end_wealth_minus_saved_A": str(number(own_metrics["end_wealth"])-number(old_metrics["end_wealth"])),
                           "opportunity_description": opportunity_description(account["daily"], initial, b0, b0_prior, start, end)}
                pointers[path_id] = output.write(path_id+".json", outcome)
                outcomes[path_id] = {k: v for k, v in outcome.items() if k not in ("account", "opportunity_description")}
                append_record(HERE/"attempts", path_id+"-finished.json",
                              {"status": "executed_pending_C_review", "finished_at": now(), **pointers[path_id]})
            except BaseException:
                failure = {"path_id": path_id, "status": "attempt_failed_no_rerun", "failed_at": now(),
                           "failure": traceback.format_exc(), "counts_as_attempt": True}
                append_record(HERE/"attempts", path_id+"-failed.json", failure)
                if storage._still_mounted(plan):
                    output.write(path_id+"-failure.json", failure, run=True)
                raise
        summary = {"task_id": TASK, "status": "executed_pending_C_review", "run_id": run_id,
                   "scope": contract["scope"], "release": release, "path_attempts": 4, "outcomes": outcomes,
                   "both_fees_risk_matched": {ref: all(outcomes[ref+"-"+fee]["within_0_90_to_1_10"] for fee in ("base", "stress"))
                                              for ref in ("A_ALL", "A_SMA")},
                   "scientific_acceptance_by_B": False, "new_A_replays": 0, "new_labels_fits_downloads": 0}
        pointers["summary"] = output.write("summary.json", summary)
        pointers["execution-log"] = output.write("execution-log.json", {"finished_at": now(), "path_attempts": 4,
                    "status": "executed_pending_C_review", "pointers": pointers}, run=True)
        output.check()
    append_record(HERE/"attempts", "result-location.json", {"run_id": run_id, "pointers": pointers,
                  "actual_path_attempts": len(actual_attempts(HERE/"attempts")[0]), "C_numeric_acceptance": False})
    print(json.dumps({"status": "executed_pending_C_review", "actual_path_attempts": 4, "run_id": run_id}))


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan-only", action="store_true")
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.plan_only:
        contract = read_json(HERE/"contract-draft.json")
        storage = storage_module(contract)
        plan = storage.plan_output(STORAGE_ROOT, TASK, ESTIMATED_BYTES, internal_bytes=INTERNAL_BYTES)
        with (HERE/"storage-plan.json").open("x") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(json.dumps({"status": "plan_only_no_execution_permission", "plan": plan}))
    elif args.preflight:
        contract, binding, release = load_execution_release()
        dataset = load_bound_dataset(binding)
        print(json.dumps({"status": "release_identity_checked_not_executed", "paths": release["authorized_path_ids"],
                          "period_trading_dates": len(dataset["period_trading"])}))
    else:
        execute()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "refused_or_failed", "reason": str(exc),
                          "started_path_ids": actual_attempts(HERE/"attempts")[0]}), file=sys.stderr)
        raise SystemExit(1)
