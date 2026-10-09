"""Run bounded synthetic checks; logs and all mutable state stay on bound external volume."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import traceback

import whole_buy_recovery as w
from test_whole_buy_recovery import run_groups

MAIN_ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")


def _log(plan, name, value):
    path = Path(plan["output"]) / "logs" / name
    w._external_guard(plan, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    w._external_guard(plan, path)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        stream.flush(); os.fsync(stream.fileno())
    return str(path)


def _worker(plan, scenario, action):
    r = w.Recovery(plan, "normal" if scenario == "success" else "first_rejected",
                   ("process_success" if scenario == "success" else "process_refusal")
                   + os.environ.get("RECOVERY_ATTEMPT_SUFFIX", ""))
    if action == "create_first":
        r.create(); first = r.submit(r.request(0))
        return {"pid": os.getpid(), "action": action, "first": first,
                "after": r.inspect()}
    if action == "restore_second":
        before = r.inspect(); second = r.submit(r.request(1)); after = r.inspect()
        return {"pid": os.getpid(), "action": action, "before": before,
                "second": second, "after": after}
    raise ValueError("unknown worker action")


def _process_trace(plan, scenario, plan_file):
    traces = []
    for action in ("create_first", "restore_second"):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX="/dev/null")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--plan", str(plan_file),
                   "--worker", scenario, action]
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
        traces.append(json.loads(result.stdout))
    first, second = traces
    assert first["pid"] != second["pid"]
    assert first["after"]["runtime"] == second["before"]["runtime"]
    assert first["after"]["state_sha256"] == second["before"]["state_sha256"]
    assert second["second"]["new_order_apply_count"] == 1
    expected = "0.10" if scenario == "success" else "205.30"
    assert second["after"]["cash"] == expected
    return {"scenario": scenario, "first_pid": first["pid"], "second_pid": second["pid"],
            "first_cash": first["after"]["cash"], "final_cash": second["after"]["cash"],
            "first_receipt": first["first"]["receipt"],
            "second_receipt": second["second"]["receipt"],
            "full_runtime_equal_across_restart": True,
            "recovery_replay_apply_count": second["second"]["recovery_replay_apply_count"],
            "new_order_apply_count": second["second"]["new_order_apply_count"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--worker", nargs=2, metavar=("SCENARIO", "ACTION"))
    args = parser.parse_args()
    plan_file = Path(args.plan).resolve()
    plan = json.loads(plan_file.read_text())
    if args.worker:
        print(json.dumps(_worker(plan, *args.worker), ensure_ascii=False, default=str))
        return 0
    sys.path.insert(0, str(MAIN_ROOT / "src"))
    from lei_signal.research.output_storage import recheck_saved_plan
    if not Path(plan["run_directory"]).exists():
        recheck_saved_plan(MAIN_ROOT, plan, plan["task_id"], plan["estimated_bytes"],
                           plan["internal_metadata_bytes"])
    else:
        w._external_guard(plan, Path(plan["output"]) / "logs" / "resume-check.json")
    logs = Path(plan["output"]) / "logs"
    version = 1
    while (logs / f"validation-failed-v{version}.json").exists() or (logs / f"validation-passed-v{version}.json").exists():
        version += 1
    os.environ["RECOVERY_ATTEMPT_SUFFIX"] = "" if version == 1 else f"_v{version}"
    outcome = {"schema": "whole-buy-recovery-validation/1", "run_id": plan["run_id"],
               "groups": {}, "process_traces": {}, "failures": []}
    try:
        outcome["groups"] = run_groups(plan)
        for scenario in ("success", "refusal"):
            outcome["process_traces"][scenario] = _process_trace(plan, scenario, plan_file)
    except BaseException as error:
        outcome["failures"].append({"type": type(error).__name__, "message": str(error),
                                    "traceback": traceback.format_exc()})
        _log(plan, f"validation-failed-v{version}.json", outcome)
        raise
    _log(plan, f"validation-passed-v{version}.json", outcome)
    print(json.dumps({"groups": len(outcome["groups"]), "process_traces": 2,
                      "log": str(Path(plan["output"]) / "logs" / f"validation-passed-v{version}.json")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
