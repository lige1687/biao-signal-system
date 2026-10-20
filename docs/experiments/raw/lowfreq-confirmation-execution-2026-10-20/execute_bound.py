"""One explicitly bound local policy run, with checked external output and budget."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from lei_signal.research.output_storage import recheck_saved_plan


ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent


def main():
    plan = json.loads((RAW / "storage-plan.json").read_text())
    plan = recheck_saved_plan(
        ROOT, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"]
    )
    state = json.loads((RAW / "state.json").read_text())
    if state["core_attempts"]:
        raise ValueError("core already attempted; any repair needs a separate recorded amendment")
    remaining = state["cap_seconds"] - state["inherited_market_seconds"] - state["market_seconds_new"]
    if remaining <= 0:
        raise ValueError("no inherited computation budget remains")
    parent = Path(plan["run_directory"])
    assert parent.parent.parent.is_dir()
    assert parent.parent.parent.stat().st_dev == plan["external_device"]
    parent.parent.mkdir(exist_ok=True)
    parent.mkdir(exist_ok=False)
    result = Path(plan["output"])
    result.mkdir(exist_ok=False)
    state.update(core_attempts=1, execution="running", current="core comparison launched")
    (RAW / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    budget = {
        "cumulative_seconds": state["inherited_market_seconds"] + state["market_seconds_new"],
        "core_runs": 0,
        "previous_attempts_in_parent_family": "preserved, total count unknown",
    }
    with (RAW / "run-budget.json").open("x") as handle:
        json.dump(budget, handle, indent=2)
    cmd = [
        sys.executable, str(RAW / "run_comparison.py"), "--run", "--out", str(result),
        "--binding", str(RAW / "frozen-binding.json"),
        "--budget-state", str(RAW / "run-budget.json"),
    ]
    start = time.monotonic()
    child = None
    reason = None
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": str(ROOT / "src"), "TMPDIR": str(parent)}
    with (parent / "stdout.log").open("wb") as stdout, (parent / "stderr.log").open("wb") as stderr:
        try:
            child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            while child.poll() is None:
                mount = Path(plan["external_mount"])
                if not os.path.ismount(mount) or mount.stat().st_dev != plan["external_device"]:
                    reason = "external device unavailable"
                    break
                if time.monotonic() - start >= remaining:
                    reason = "inherited computation budget reached"
                    break
                time.sleep(0.1)
        finally:
            if child is not None and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
    elapsed = time.monotonic() - start
    state["market_seconds_new"] += elapsed
    state["execution"] = "running" if child.returncode == 0 else "paused"
    state["current"] = "independent review pending" if child.returncode == 0 else "failed core retained"
    (RAW / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    receipt = {
        "exit_code": child.returncode, "seconds": elapsed, "stop_reason": reason,
        "output": str(result), "stdout": str(parent / "stdout.log"),
        "stderr": str(parent / "stderr.log"),
        "cumulative_seconds": state["inherited_market_seconds"] + state["market_seconds_new"],
        "scientific_result_verified": False,
    }
    with (RAW / "launcher-receipt.json").open("x") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
    print(json.dumps(receipt, ensure_ascii=False))
    return child.returncode


if __name__ == "__main__":
    raise SystemExit(main())
