"""Independent admission checks; synthetic documents and probes only."""
import sys
sys.dont_write_bytecode = True
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

storage = load(ROOT / "src/lei_signal/research/storage_preflight.py", "independent_storage")
cli = load(ROOT / "scripts/run_factor_lab.py", "independent_cli")
case = RAW / ("independent-case-" + uuid4().hex)
case.mkdir()
source = case / "input.json"
source.write_text(json.dumps({"history": {"family": "independent-new-engineering"}}))
output = case / "output"
plan_path = case / "storage-plan.json"
plan = {
    "schema_version": "research-storage-plan/1.0",
    "binding": {"mode": "workflow-contract",
        "input": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "out": str(output), "register_report": False, "reuse_predictions": None},
    "growth_bytes": {"output": 101, "current_journal": 202, "current_lock": 303},
    "volumes": [{"id": "known-test-device", "kind": "internal", "mount_path": str(case),
        "device": case.stat().st_dev, "reserve_bytes": 404}],
}

def save():
    plan_path.write_text(json.dumps(plan))

def snapshot():
    return {str(p.relative_to(case)): ("directory" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
        for p in case.rglob("*") if not p.is_symlink()}

def check(free=1010):
    return storage.check_storage_plan(plan_path, mode="workflow-contract", input_path=source,
        output_dir=output, root=case, is_mount=lambda p: True,
        disk_usage=lambda p: SimpleNamespace(free=free))

results = []
save()
proof = check()
assert proof["devices"][0]["growth_bytes"] == 606
assert proof["devices"][0]["required_bytes"] == 1010
encoded = json.dumps("independent-new-engineering", ensure_ascii=False, sort_keys=True, separators=(",", ":"))
expected = case / "docs/experiments/raw/research-workflow-ledgers-2026-09-29" / hashlib.sha256(encoded.encode()).hexdigest()[:24] / "attempts.jsonl"
assert proof["targets"]["current_journal"] == str(expected)
assert not expected.parent.exists()
results.append("independently calculated journal digest and cumulative space agree")

before = snapshot()
try:
    check(1009)
    raise AssertionError("aggregate low space passed")
except storage.StoragePreflightError:
    assert snapshot() == before
results.append("same-device aggregate rejection leaves all files and directories unchanged")

for role in tuple(plan["growth_bytes"]):
    value = plan["growth_bytes"].pop(role)
    save()
    before = snapshot()
    try:
        check()
        raise AssertionError("omitted role passed: " + role)
    except storage.StoragePreflightError:
        assert snapshot() == before
    plan["growth_bytes"][role] = value
results.append("each current write-role omission independently rejected")
save()

for alias in ["//Volumes/missing/new-output", "/Volumes/missing/new-output"]:
    plan["binding"]["out"] = alias
    save()
    before = snapshot()
    try:
        storage.check_storage_plan(plan_path, mode="workflow-contract", input_path=source,
            output_dir=alias, root=case, is_mount=lambda p: True,
            disk_usage=lambda p: SimpleNamespace(free=1010))
        raise AssertionError("missing-volume alias passed")
    except storage.StoragePreflightError:
        assert snapshot() == before
results.append("actual CLI-bound single/double-slash missing external routes rejected")
plan["binding"]["out"] = str(output)
save()

expected.mkdir(parents=True)
before = snapshot()
try:
    check()
    raise AssertionError("directory at journal filename passed")
except storage.StoragePreflightError:
    assert snapshot() == before
results.append("directory at journal path rejected without side effects")

# Distinct synthetic root, no original workflow or research execution.
case2 = RAW / ("independent-callback-" + uuid4().hex)
case2.mkdir()
source2 = case2 / "input.json"
source2.write_bytes(source.read_bytes())
plan2 = json.loads(json.dumps(plan))
plan2["binding"]["input"] = {"path": str(source2), "sha256": hashlib.sha256(source2.read_bytes()).hexdigest()}
plan2["binding"]["out"] = str(case2 / "output")
plan2["volumes"][0]["mount_path"] = str(case2)
planfile2 = case2 / "plan.json"
planfile2.write_text(json.dumps(plan2))
events = []
def checker(*args, **kwargs):
    result = storage.check_storage_plan(*args, **kwargs, is_mount=lambda p: True,
        disk_usage=lambda p: SimpleNamespace(free=1010))
    events.append("actual_check_completed")
    return result
def executor(args):
    assert events == ["actual_check_completed"]
    events.append("safe_callback")
    return 0
rc = cli.main(["--workflow-contract", str(source2), "--out", str(case2 / "output"),
    "--storage-plan", str(planfile2)], root=case2, storage_checker=checker, workflow_executor=executor)
assert rc == 0 and events == ["actual_check_completed", "safe_callback"]
assert not (case2 / "output").exists()
assert not any(k == "lei_signal" or k.startswith("lei_signal.") for k in sys.modules)
results.append("real admission then safe callback; no project research import or output")
print(json.dumps({"checks_passed": len(results), "results": results,
    "market_runs": 0, "fits": 0, "labels": 0}, ensure_ascii=False, indent=2))
