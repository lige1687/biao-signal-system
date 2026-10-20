"""Execute the one approved diagnostic, preserving launch budget and disk binding."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(MAIN / "src"))
sys.dont_write_bytecode = True
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main():
    contract_path = HERE / "defensive-execution-contract.json"
    contract = json.loads(contract_path.read_text())
    assert contract["status"] == "approved_frozen"
    assert contract["budget"]["attempt_number"] == 9
    assert contract["budget"]["followup_number"] == 3
    assert not (HERE / "defensive-launch.json").exists(), "No automatic retry or budget reset"
    for item in contract["bindings"].values():
        assert sha(item["path"]) == item["sha256"], item["path"]
    for item in contract["additional_bindings"].values():
        assert sha(item["path"]) == item["sha256"], item["path"]
    plan = json.loads(Path(contract["additional_bindings"]["storage_plan"]["path"]).read_text())
    plan = recheck_saved_plan(MAIN, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"])
    assert str(Path(contract["output_directory"])) == plan["output"]
    assert _still_mounted(plan), "Registered external disk unavailable"
    run_dir = Path(plan["run_directory"])
    # Never create an absent /Volumes tree or silently use local storage.
    assert run_dir.parent.parent.is_dir() and run_dir.parent.parent.stat().st_dev == plan["external_device"]
    run_dir.parent.mkdir(exist_ok=True)
    assert run_dir.parent.stat().st_dev == plan["external_device"]
    run_dir.mkdir(exist_ok=False)
    command = [sys.executable, "-B", str(HERE / "defensive_diagnostic.py"),
               "--contract", str(contract_path), "--out", plan["output"]]
    start = dt.datetime.now().astimezone().isoformat()
    save_new(HERE / "defensive-launch.json", {
        "at": start, "status": "real_launch_attempt_recorded", "command": command,
        "contract_sha256": sha(contract_path), "budget": contract["budget"],
        "note": "Attempt consumed before launch; any failure remains counted. No automatic second attempt."})
    log = run_dir / "execution.log"
    stop_reason = None
    with log.open("x") as handle:
        process = subprocess.Popen(command, cwd=HERE.parents[3], stdout=handle, stderr=subprocess.STDOUT,
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, start_new_session=True)
        while process.poll() is None:
            if not _still_mounted(plan):
                stop_reason = "registered_external_disk_disconnected"
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(.25)
        code = process.wait()
    outputs = []
    output = Path(plan["output"])
    if _still_mounted(plan) and output.is_dir():
        outputs = [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size}
                   for p in sorted(output.iterdir()) if p.is_file() and not p.name.startswith("._")]
    result = {"started_at": start, "ended_at": dt.datetime.now().astimezone().isoformat(),
              "exit_code": code, "stop_reason": stop_reason, "budget": contract["budget"],
              "status": "execution_completed_needs_controller_review" if code == 0 else "failed",
              "contract_path": str(contract_path), "contract_sha256": sha(contract_path),
              "log": {"path": str(log), "sha256": sha(log)} if _still_mounted(plan) else {"path": str(log), "unavailable": True},
              "outputs": outputs, "readback_acceptance": False}
    save_new(HERE / "defensive-execution-receipt.json", result)
    print(json.dumps({"status": result["status"], "exit_code": code, "outputs": outputs}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
