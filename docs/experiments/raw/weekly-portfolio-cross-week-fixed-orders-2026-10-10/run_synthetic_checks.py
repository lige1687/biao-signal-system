"""Verify the fixed external route, then run version-bound synthetic processes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import cross_week_fixed_orders as core

PRESERVED_V1_MANIFEST_SHA = "071a0caf3622cb1f523277bcb71d44a92ed54a61cfdd8a792e3210592f3e67f9"


def verify_output(contract):
    from lei_signal.research.output_storage import plan_output

    plan = contract["output_plan"]
    fresh = plan_output(
        core.ROOT,
        plan["task_id"],
        plan["estimated_bytes"],
        internal_bytes=plan["internal_metadata_bytes"],
    )
    for key in (
        "schema_version",
        "task_id",
        "external_mount",
        "external_device",
        "external_uuid",
        "estimated_bytes",
        "internal_metadata_bytes",
        "external_reserve_bytes",
        "internal_reserve_bytes",
    ):
        core.require(plan[key] == fresh[key], f"fixed external plan drift: {key}")
    run_directory = Path(plan["run_directory"])
    output = Path(plan["output"])
    core.require(
        run_directory.is_dir() and output.is_dir() and output == run_directory / "result",
        "fixed original run missing",
    )
    core.require(output.stat().st_dev == plan["external_device"], "fixed external device drift")
    preserved = output / "v1-preservation"
    manifest_path = preserved / "preservation-manifest.json"
    core.require(
        core.sha(manifest_path) == PRESERVED_V1_MANIFEST_SHA, "v1 preservation manifest drift"
    )
    old = json.loads(manifest_path.read_text())
    for relative, identity in old["files"].items():
        file = preserved / relative
        core.require(
            file.is_file()
            and core.sha(file) == identity["sha256"]
            and file.stat().st_size == identity["bytes"],
            f"v1 preserved file drift: {relative}",
        )
    core.require(old["v1_state_equal"] is True, "v1 preserved state mismatch")
    return run_directory, output, manifest_path


def run_process(command, log_path, env):
    child = subprocess.Popen(
        command, cwd=core.ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = child.communicate()
    with log_path.open("x") as stream:
        stream.write(stdout + stderr)
    core.require(child.returncode == 0, f"process failed; preserved {log_path.name}")
    value = json.loads(stdout)
    core.require(value["pid"] == child.pid, "actual process PID mismatch")
    return value


def main():
    contract, manifest, fixture, module = core.load_frozen()
    run_directory, output, preservation = verify_output(contract)
    v2 = output / "v2"
    if v2.exists():
        core.require(
            (v2 / "process-acceptance.json").is_file(),
            "v2 partial state preserved; inspect before any further execution",
        )
        receipt = json.loads((v2 / "process-acceptance.json").read_text())
        states = []
        for slot in ("continuous", "split"):
            engine = core.Engine(
                v2 / slot, fixture, manifest, module, strict_fixture_sha=contract["fixture_sha256"]
            )
            states.append(engine.state)
        core.require(
            states[0] == states[1]
            and states[0]["cursor"] == 10
            and core.sha(v2 / "continuous/state.json") == receipt["full_state_sha256"],
            "v2 saved process state drift",
        )
        print(
            core.canonical(
                {
                    "status": "v2_existing_verified",
                    "full_state_equal": True,
                    "process_count": len(receipt["processes"]),
                }
            )
        )
        return
    v2.mkdir(exist_ok=False)
    for name in ("continuous", "split", "logs", "tmp"):
        (v2 / name).mkdir(exist_ok=False)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(core.ROOT / "src")
    env["TMPDIR"] = str(v2 / "tmp")
    test_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(v2 / "tmp/pytest"),
        str(core.HERE / "test_cross_week_fixed_orders.py"),
    ]
    test = subprocess.run(
        test_command, cwd=core.ROOT, env=env, capture_output=True, text=True, check=False
    )
    with (v2 / "logs/pytest.log").open("x") as stream:
        stream.write(test.stdout + test.stderr)
    core.require(test.returncode == 0, "v2 synthetic tests failed; log preserved")
    processes = []
    for slot, stage in (("continuous", "all"), ("split", "week1"), ("split", "week2")):
        command = [
            sys.executable,
            str(core.HERE / "cross_week_fixed_orders.py"),
            "--version",
            "v2",
            "--slot",
            slot,
            "--stage",
            stage,
            "--directory",
            str(v2 / slot),
        ]
        result = run_process(command, v2 / f"logs/{slot}-{stage}.log", env)
        processes.append(
            {
                "slot": slot,
                "stage": stage,
                "pid": result["pid"],
                "cursor": result["cursor"],
                "state_sha256": result["state_sha256"],
            }
        )
    core.require(len({p["pid"] for p in processes}) == 3, "distinct new process PID failure")
    continuous = core.Engine(
        v2 / "continuous", fixture, manifest, module, strict_fixture_sha=contract["fixture_sha256"]
    )
    split = core.Engine(
        v2 / "split", fixture, manifest, module, strict_fixture_sha=contract["fixture_sha256"]
    )
    full_state_equal = (
        continuous.state == split.state
        and continuous.state["cursor"] == 10
        and core.sha(continuous.state_path) == core.sha(split.state_path)
    )
    core.require(full_state_equal, "v2 continuous/split full state mismatch")
    expected = fixture["expected"]
    final = continuous.state["summary"]
    for actual, target in (
        ("cash", "final_cash"),
        ("assets", "final_assets"),
        ("fees", "final_fees"),
    ):
        core.require(
            core.Decimal(final[actual]) == core.Decimal(expected[target]),
            f"v2 final {actual} mismatch",
        )
    source_version = {
        "wrapper_sha256": core.sha(core.__file__),
        "test_sha256": core.sha(core.HERE / "test_cross_week_fixed_orders.py"),
        "runner_sha256": core.sha(__file__),
        "v1_preservation_manifest_sha256": core.sha(preservation),
    }
    core.require(
        continuous.state["executor_sha256"] == source_version["wrapper_sha256"],
        "v2 checkpoint wrapper SHA mismatch",
    )
    receipt = {
        "schema": "cross-week-fixed-orders-v2-process-acceptance/1",
        "source_version": source_version,
        "synthetic_tests": test.stdout.strip().splitlines()[-1],
        "processes": processes,
        "full_state_equal": full_state_equal,
        "full_state_sha256": core.sha(continuous.state_path),
        "final": {key: final[key] for key in ("cash", "assets", "fees", "positions", "inflows")},
        "real_market_requests": 0,
        "real_account_operations": 0,
    }
    with (v2 / "process-acceptance.json").open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        core.canonical(
            {
                "status": "v2_passed",
                "tests": receipt["synthetic_tests"],
                "full_state_equal": full_state_equal,
                "process_count": 3,
                "state_sha256": receipt["full_state_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
