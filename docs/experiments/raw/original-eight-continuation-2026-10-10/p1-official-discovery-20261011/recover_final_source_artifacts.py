"""Prepare a bounded recovery of the exact new-source manifest in a contract.

Required contract fields: ``external_run_directory``, ``external_write_paths``
(one unique destination below that directory), ``external_read_paths`` (ordered
source paths), ``input_files`` (matching ordered objects with ``path``, ``bytes``
and ``sha256``), and ``result_path`` (a local result file). Optional
``input_sha256`` binds supporting control files. The runner derives exact count
and total bytes from ``input_files``; it does not accept caller-supplied counts.
The final immutable contract must be reviewed and supplied explicitly with
``--contract`` before ``run``. Merely preparing this runner performs no recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta


EXPECTED_DEVICE = 16777238
EXPECTED_UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"
EXTERNAL_MOUNT = Path("/Volumes/win+mac通用")
RESERVE_BYTES = 10 * 1024**3


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def snapshot(path: Path) -> dict:
    state = path.stat()
    return {
        "path": str(path), "bytes": state.st_size, "sha256": digest(path),
        "device": state.st_dev, "inode": state.st_ino, "mtime_ns": state.st_mtime_ns,
    }


def exclusive_bytes(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def exclusive_json(path: Path, value: dict) -> None:
    exclusive_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def load_contract(contract_path: Path) -> tuple[dict, Path, Path, int, int]:
    data = json.loads(contract_path.read_text())
    run_directory = Path(data["external_run_directory"])
    write_paths = data["external_write_paths"]
    inputs = data["input_files"]
    read_paths = data["external_read_paths"]
    if not inputs or len(inputs) != len(read_paths):
        raise RuntimeError("contract must contain a non-empty, aligned source manifest")
    if [row["path"] for row in inputs] != read_paths:
        raise RuntimeError("contract input paths differ from registered read paths")
    sources = [Path(row["path"]) for row in inputs]
    if len(set(sources)) != len(sources):
        raise RuntimeError("contract contains duplicate source paths")
    if not all(source.is_relative_to(run_directory) for source in sources):
        raise RuntimeError("source outside the fixed external run directory")
    if any(not isinstance(row["bytes"], int) or row["bytes"] < 0 for row in inputs):
        raise RuntimeError("invalid frozen source byte count")
    if any(len(row["sha256"]) != 64 for row in inputs):
        raise RuntimeError("invalid frozen source SHA-256")
    destination = Path(write_paths[0]) if len(write_paths) == 1 else None
    if destination is None or not destination.is_relative_to(run_directory):
        raise RuntimeError("contract must specify one destination below external_run_directory")
    if len(write_paths) != 1 or str(destination) != write_paths[0]:
        raise RuntimeError("external_write_paths must contain one normalized destination")
    if destination in sources or any(path in (destination, destination.parent) for path in sources):
        raise RuntimeError("destination overlaps a source path")
    if not destination.parent.is_relative_to(EXTERNAL_MOUNT):
        raise RuntimeError("destination is outside the registered external mount")
    result_path = Path(data["result_path"])
    if result_path.is_absolute() is False:
        result_path = (Path.cwd() / result_path).resolve()
    if result_path.is_relative_to(EXTERNAL_MOUNT):
        raise RuntimeError("result_path must be the contract's local result location")
    for control_path, expected_hash in data.get("input_sha256", {}).items():
        if digest(Path(control_path)) != expected_hash:
            raise RuntimeError(f"control binding changed: {control_path}")
    return data, destination, result_path, len(inputs), sum(row["bytes"] for row in inputs)


def validate_mount(directory: Path) -> dict:
    if (not directory.is_dir() or directory.stat().st_dev != EXPECTED_DEVICE
            or not directory.is_relative_to(EXTERNAL_MOUNT)):
        raise RuntimeError("external directory is absent or on the wrong device")
    result = subprocess.run(
        ["diskutil", "info", str(EXTERNAL_MOUNT)], capture_output=True, text=True, check=True
    )
    if f"Volume UUID:               {EXPECTED_UUID}" not in result.stdout:
        raise RuntimeError("external UUID mismatch")
    capacity = os.statvfs(directory)
    return {"device": directory.stat().st_dev, "uuid": EXPECTED_UUID,
            "free_bytes": capacity.f_bavail * capacity.f_frsize}


def assert_source_matches(frozen: dict, actual: dict) -> None:
    if actual["bytes"] != frozen["bytes"] or actual["sha256"] != frozen["sha256"]:
        raise RuntimeError(f"source differs from frozen manifest: {frozen['path']}")


def backup(contract_path: Path) -> None:
    data, destination, _, count, total_bytes = load_contract(contract_path)
    device = validate_mount(destination.parent)
    if device["free_bytes"] < total_bytes * 2 + RESERVE_BYTES:
        raise RuntimeError("external free capacity below two-copy plan plus 10 GiB reserve")
    before = [snapshot(Path(row["path"])) for row in data["input_files"]]
    for frozen, actual in zip(data["input_files"], before, strict=True):
        assert_source_matches(frozen, actual)
    backup_dir = destination / "backup"
    backup_dir.mkdir(exist_ok=False)
    rows = []
    for index, (frozen, source) in enumerate(zip(data["input_files"], before, strict=True), 1):
        target = backup_dir / f"{index:04d}-{Path(frozen['path']).name}"
        exclusive_bytes(target, Path(frozen["path"]).read_bytes())
        copied = snapshot(target)
        if copied["bytes"] != source["bytes"] or copied["sha256"] != source["sha256"]:
            raise RuntimeError(f"backup mismatch: {target}")
        rows.append({"source_before": source, "backup": copied})
    after = [snapshot(Path(row["path"])) for row in data["input_files"]]
    if before != after:
        raise RuntimeError("original source changed during backup")
    manifest = {
        "schema": "p1-final-source-backup/1",
        "at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "backup_pid": os.getpid(), "script_sha256": digest(Path(__file__)),
        "contract_sha256": digest(contract_path), "device": device,
        "count": count, "total_content_bytes": total_bytes, "rows": rows,
        "originals_unchanged_after_backup": True,
    }
    exclusive_json(destination / "backup-manifest.json", manifest)
    print(json.dumps({"pid": os.getpid(), "manifest": str(destination / "backup-manifest.json")}))


def restore(contract_path: Path, manifest_path: Path) -> None:
    # This child reads source identity from the contract, but reads artifact bytes only from backup.
    _, destination, _, count, total_bytes = load_contract(contract_path)
    if manifest_path != destination / "backup-manifest.json":
        raise RuntimeError("manifest path differs from the frozen destination")
    device = validate_mount(destination)
    manifest = json.loads(manifest_path.read_text())
    if (manifest["schema"] != "p1-final-source-backup/1" or manifest["count"] != count
            or manifest["total_content_bytes"] != total_bytes):
        raise RuntimeError("backup manifest does not match dynamic contract count/bytes")
    if manifest["script_sha256"] != digest(Path(__file__)):
        raise RuntimeError("runner changed between backup and restore")
    if manifest["contract_sha256"] != digest(contract_path):
        raise RuntimeError("contract changed between backup and restore")
    restore_dir = destination / "restored"
    restore_dir.mkdir(exist_ok=False)
    rows = []
    for row in manifest["rows"]:
        backup_path = Path(row["backup"]["path"])
        if backup_path.parent != destination / "backup":
            raise RuntimeError("backup path outside fixed directory")
        backup_state = snapshot(backup_path)
        if backup_state != row["backup"]:
            raise RuntimeError(f"backup drift: {backup_path}")
        restored_path = restore_dir / backup_path.name
        exclusive_bytes(restored_path, backup_path.read_bytes())
        restored = snapshot(restored_path)
        if restored["bytes"] != backup_state["bytes"] or restored["sha256"] != backup_state["sha256"]:
            raise RuntimeError(f"restore mismatch: {restored_path}")
        rows.append({"backup": backup_state, "restored": restored})
    result = {
        "schema": "p1-final-source-restore/1",
        "at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "restore_pid": os.getpid(), "backup_pid": manifest["backup_pid"],
        "script_sha256": digest(Path(__file__)), "contract_sha256": digest(contract_path),
        "device": device, "count": count, "total_content_bytes": total_bytes,
        "rows": rows, "source_read_by_restore_process": False,
    }
    if result["backup_pid"] == result["restore_pid"]:
        raise RuntimeError("backup and restore PIDs are identical")
    exclusive_json(destination / "restore-readback.json", result)
    print(json.dumps({"pid": os.getpid(), "receipt": str(destination / "restore-readback.json")}))


def run(contract_path: Path) -> None:
    data, destination, result_path, count, total_bytes = load_contract(contract_path)
    validate_mount(destination.parent)
    destination.mkdir(exist_ok=False)
    validate_mount(destination)
    before = [snapshot(Path(row["path"])) for row in data["input_files"]]
    for frozen, actual in zip(data["input_files"], before, strict=True):
        assert_source_matches(frozen, actual)
    command = [sys.executable, str(Path(__file__).resolve()), "--contract", str(contract_path)]
    backup_run = subprocess.run(command + ["backup"], capture_output=True, text=True)
    if backup_run.returncode:
        exclusive_json(result_path, {"status": "failed_backup_child", "run_pid": os.getpid(),
            "child_exit_code": backup_run.returncode, "child_stdout": backup_run.stdout,
            "child_stderr": backup_run.stderr, "script_sha256": digest(Path(__file__))})
        raise RuntimeError("backup child failed; partial files retained")
    restore_run = subprocess.run(command + ["restore", str(destination / "backup-manifest.json")],
                                 capture_output=True, text=True)
    if restore_run.returncode:
        exclusive_json(result_path, {"status": "failed_restore_child", "run_pid": os.getpid(),
            "backup_stdout": backup_run.stdout, "restore_exit_code": restore_run.returncode,
            "restore_stdout": restore_run.stdout, "restore_stderr": restore_run.stderr,
            "script_sha256": digest(Path(__file__))})
        raise RuntimeError("restore child failed; partial files retained")
    manifest_path = destination / "backup-manifest.json"
    receipt_path = destination / "restore-readback.json"
    manifest, receipt = json.loads(manifest_path.read_text()), json.loads(receipt_path.read_text())
    after = [snapshot(Path(row["path"])) for row in data["input_files"]]
    for frozen, actual in zip(data["input_files"], after, strict=True):
        assert_source_matches(frozen, actual)
    if before != after or manifest["count"] != count or receipt["count"] != count:
        raise RuntimeError("final source or count verification failed")
    if manifest["total_content_bytes"] != total_bytes or receipt["total_content_bytes"] != total_bytes:
        raise RuntimeError("final source byte total mismatch")
    if len({manifest["backup_pid"], receipt["restore_pid"], os.getpid()}) != 3:
        raise RuntimeError("run, backup, and restore PIDs are not distinct")
    result = {
        "schema": "p1-final-source-recovery-result/1",
        "at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "status": "same_device_backup_and_separate_process_restore_verified",
        "script_sha256": digest(Path(__file__)), "contract_sha256": digest(contract_path),
        "original_count": count, "new_backup_count": count, "restored_count": count,
        "bytes_per_set": total_bytes, "backup_plus_restored_content_bytes": 2 * total_bytes,
        "run_pid": os.getpid(), "backup_pid": manifest["backup_pid"],
        "restore_pid": receipt["restore_pid"],
        "backup_manifest": {"path": str(manifest_path), "sha256": digest(manifest_path),
                            "bytes": manifest_path.stat().st_size},
        "restore_readback": {"path": str(receipt_path), "sha256": digest(receipt_path),
                             "bytes": receipt_path.stat().st_size},
        "originals_unchanged": before == after, "external_device": receipt["device"],
        "child_stdout": [backup_run.stdout.strip(), restore_run.stdout.strip()],
        "child_stderr": [backup_run.stderr.strip(), restore_run.stderr.strip()],
        "child_exit_codes": [backup_run.returncode, restore_run.returncode], "failures": [],
        "limits": "Same-device recovery only; no other-machine or device-failure recovery established.",
    }
    exclusive_json(result_path, result)
    print(json.dumps({"result": str(result_path), "sha256": digest(result_path),
                      "backup_pid": manifest["backup_pid"], "restore_pid": receipt["restore_pid"]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("mode", choices=["backup", "restore", "run"])
    parser.add_argument("manifest", nargs="?", type=Path)
    args = parser.parse_args()
    contract_path = args.contract.resolve()
    if args.mode == "backup":
        backup(contract_path)
    elif args.mode == "restore":
        if args.manifest is None:
            parser.error("restore requires the backup manifest")
        restore(contract_path, args.manifest.resolve())
    else:
        if args.manifest is not None:
            parser.error("run does not accept a manifest")
        run(contract_path)


if __name__ == "__main__":
    main()
