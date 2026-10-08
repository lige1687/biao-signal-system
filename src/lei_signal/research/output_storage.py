"""Default external outputs for NEW research invocations; never relocates inputs.

This launcher keeps frozen CLI bytes and their scientific checks unchanged.
Space estimates are preflight estimates, not filesystem quotas.
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


class OutputStorageError(ValueError):
    pass


def _require(value, message):
    if not value:
        raise OutputStorageError(message)


def _plain(path):
    path = Path(os.path.abspath(path))
    for current in (path, *path.parents):
        _require(not current.is_symlink(), f"symlink route refused: {current}")
    return path


def _positive(value, name):
    _require(type(value) is int and value > 0, f"{name} must be a positive integer")
    return value


def _read_policy(root):
    root = _plain(root)
    policy = json.loads((root / "configs/research-output-policy.v1.json").read_text())
    storage = json.loads((root / "configs/storage-policy.v1.json").read_text())
    _require(
        isinstance(policy, dict) and isinstance(storage, dict), "storage policies must be objects"
    )
    _require(policy.get("schema_version") == 1, "unknown output policy version")
    _require(policy.get("mode") == "external-for-new-results", "unknown output mode")
    directory = policy.get("external_results_directory")
    _require(
        isinstance(directory, str)
        and directory
        and Path(directory).name == directory
        and directory not in {".", ".."},
        "results directory must be one path component",
    )
    return root, policy, storage


def _probe(root, mount):
    try:
        info = plistlib.loads(
            subprocess.check_output(
                ["/usr/sbin/diskutil", "info", "-plist", str(mount)], timeout=10
            )
        )
        return {
            "info": info,
            "mounted": os.path.ismount(mount),
            "external_device": mount.stat().st_dev,
            "internal_device": root.stat().st_dev,
            "external_free": shutil.disk_usage(mount).free,
            "internal_free": shutil.disk_usage(root).free,
        }
    except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException) as exc:
        raise OutputStorageError(f"cannot verify storage: {exc}") from exc


def plan_output(root, task, estimated_bytes, *, internal_bytes=None, probe=_probe):
    root, policy, storage = _read_policy(root)
    _require(
        isinstance(task, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", task),
        "task must be a simple stable task id",
    )
    estimated_bytes = _positive(estimated_bytes, "estimated result and log bytes")
    internal_bytes = _positive(
        internal_bytes if internal_bytes is not None else policy["default_internal_metadata_bytes"],
        "internal bytes",
    )
    mount = _plain(storage["external_mount"])
    base = _plain(mount / policy["external_results_directory"])
    _require(
        base.is_dir(), "managed external result directory missing; reconnect the registered disk"
    )
    snapshot = probe(root, mount)
    info = snapshot["info"]
    _require(
        snapshot["mounted"]
        and info.get("MountPoint") == str(mount)
        and info.get("VolumeUUID") == storage["external_volume_uuid"]
        and info.get("FilesystemType") == storage["external_filesystem"]
        and info.get("Internal") is False
        and info.get("Writable") is True,
        "external identity, mount or writable state mismatch",
    )
    _require(
        snapshot["external_device"] != snapshot["internal_device"]
        and base.stat().st_dev == snapshot["external_device"],
        "external path/device mismatch",
    )
    reserve = _positive(policy["external_reserve_bytes"], "external reserve")
    local_reserve = _positive(storage["internal_critical_bytes"], "internal reserve")
    _require(
        snapshot["external_free"] >= reserve + estimated_bytes,
        "insufficient external capacity for result/log estimate and reserve",
    )
    _require(
        snapshot["internal_free"] >= local_reserve + internal_bytes,
        "insufficient internal capacity for metadata and 5 GiB reserve",
    )
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    run_id = f"{task}-{stamp}-{uuid.uuid4().hex[:12]}"
    parent = base / task / run_id
    _plain(parent)
    _require(not parent.exists(), "new output already exists")
    return {
        "schema_version": 1,
        "task_id": task,
        "run_id": run_id,
        "run_directory": str(parent),
        "output": str(parent / "result"),
        "external_mount": str(mount),
        "external_device": snapshot["external_device"],
        "external_uuid": storage["external_volume_uuid"],
        "estimated_bytes": estimated_bytes,
        "internal_metadata_bytes": internal_bytes,
        "external_reserve_bytes": reserve,
        "internal_reserve_bytes": local_reserve,
        "execution_authorized": False,
        "quota_enforced": False,
    }


def _has_option(args, protected):
    # Original argparse CLIs accept unique long-option prefixes, including --flag=value.
    # Refuse every prefix of a protected option; complete unrelated flags stay unchanged.
    for arg in args:
        flag = arg.split("=", 1)[0]
        if (
            flag.startswith("--")
            and flag != "--"
            and any(option.startswith(flag) for option in protected)
        ):
            return True
    return False


def build_command(root, entry, args, plan):
    root, policy, _ = _read_policy(root)
    entries = policy["entrypoints"]
    _require(entry in entries, "unregistered entry; inspect its outputs before registration")
    spec = entries[entry]
    source = _plain(root / entry)
    _require(
        source.is_file() and source.is_relative_to(root / "scripts"), "entry missing or aliased"
    )
    _require(
        not _has_option(args, {"--out", "--output", "--output-dir"}),
        "explicit output conflicts with default route; leave frozen replay commands unchanged",
    )
    _require(
        not _has_option(args, spec.get("readonly_flags", [])),
        "read-only review does not need a result route; use the original CLI",
    )
    subcommands = spec.get("subcommands")
    if subcommands:
        _require(bool(args) and args[0] in subcommands, "unsupported/read-only subcommand")
    # Alternate repo-root options could redirect local scientific records to another tree.
    _require(
        not _has_option(args, {"--repo-root", "--root"}),
        "alternate repository root needs a separately checked storage plan",
    )
    return [sys.executable, str(source), *args, spec["output_flag"], plan["output"]]


def _still_mounted(plan):
    p = Path(plan["external_mount"])
    try:
        return os.path.ismount(p) and p.stat().st_dev == plan["external_device"]
    except OSError:
        return False


def _stop_child(child):
    if child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=5)


def execute_new(root, entry, args, plan):
    plan = recheck_saved_plan(
        root, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"]
    )
    command = build_command(root, entry, args, plan)
    _require(_still_mounted(plan), "external disk lost before directory creation")
    parent = _plain(plan["run_directory"])
    # The policy's base already exists on the verified device; never creates /Volumes.
    task_parent = parent.parent
    _require(
        task_parent.parent.is_dir() and task_parent.parent.stat().st_dev == plan["external_device"],
        "external base lost",
    )
    task_parent.mkdir(exist_ok=True)
    _require(_still_mounted(plan), "external disk lost before new output")
    parent.mkdir(exist_ok=False)
    anchor = os.open(parent, os.O_RDONLY)
    child = None
    try:
        _require(os.fstat(anchor).st_dev == plan["external_device"], "output device changed")
        (parent / "storage-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2))
        _require(_still_mounted(plan), "external disk lost before child launch")
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(parent),
            "PYTHONPATH": str(Path(root) / "src"),
        }
        with (
            (parent / "stdout.log").open("wb") as stdout,
            (parent / "stderr.log").open("wb") as stderr,
        ):
            child = subprocess.Popen(
                command,
                cwd=root,
                env=env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                pass_fds=(anchor,),
            )
            while child.poll() is None:
                if not _still_mounted(plan):
                    _stop_child(child)
                    raise OutputStorageError(
                        "external disk lost; only this newly launched child stopped"
                    )
                time.sleep(0.25)
            status = child.returncode
        _require(_still_mounted(plan), "external disk lost at readback")
        receipt = {
            "entry": entry,
            "output": plan["output"],
            "exit_code": status,
            "scientific_result_verified": False,
        }
        (parent / "launcher-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2)
        )
        index = Path(root) / "data/cache/research-output-index"
        _plain(index).mkdir(parents=True, exist_ok=True)
        pointer = index / (plan["run_id"] + ".json")
        with pointer.open("x") as f:
            json.dump({**receipt, "run_directory": str(parent)}, f, ensure_ascii=False)
        return receipt
    finally:
        if child is not None and child.poll() is None:
            _stop_child(child)
        os.close(anchor)


def recheck_saved_plan(root, saved, task, estimated_bytes, internal_bytes=None):
    """Keep an exact generated path while refreshing identity and capacity."""
    fresh = plan_output(root, task, estimated_bytes, internal_bytes=internal_bytes)
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
        _require(saved.get(key) == fresh[key], f"saved route plan mismatch: {key}")
    directory = _plain(saved["run_directory"])
    task_parent = Path(fresh["run_directory"]).parent
    _require(
        directory.parent == task_parent and directory.name == saved["run_id"],
        "saved route directory mismatch",
    )
    _require(
        saved["output"] == str(directory / "result") and not directory.exists(),
        "saved output exists or differs from new result route",
    )
    return saved


def main(argv=None):
    p = argparse.ArgumentParser(description="新实验大结果默认写已核外盘；不迁移旧输入")
    p.add_argument("--task", required=True)
    p.add_argument("--entry", required=True)
    p.add_argument("--estimated-bytes", required=True, type=int)
    p.add_argument("--internal-bytes", type=int)
    p.add_argument("--plan-only", action="store_true")
    p.add_argument("--route-plan", help="复用已生成的准确目录计划，并重新检查设备与容量")
    p.add_argument("arguments", nargs=argparse.REMAINDER)
    a = p.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    args = a.arguments[1:] if a.arguments[:1] == ["--"] else a.arguments
    try:
        if a.route_plan:
            saved = json.loads(_plain(a.route_plan).read_text())
            _require(saved.get("entry") == a.entry, "saved entry mismatch")
            plan = recheck_saved_plan(root, saved, a.task, a.estimated_bytes, a.internal_bytes)
        else:
            plan = plan_output(root, a.task, a.estimated_bytes, internal_bytes=a.internal_bytes)
        build_command(root, a.entry, args, plan)
        result = (
            {**plan, "entry": a.entry} if a.plan_only else execute_new(root, a.entry, args, plan)
        )
        # No caller arguments/credentials are echoed.
        print(json.dumps(result, ensure_ascii=False))
        return 0 if a.plan_only else result["exit_code"]
    except (
        OutputStorageError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        print(
            json.dumps(
                {"storage_refused": str(exc), "fallback_to_internal": False}, ensure_ascii=False
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
