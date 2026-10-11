"""Bounded, non-overwriting same-device recovery of forty-four source artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta


HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "source-artifact-recovery-contract.json"
RESULT = HERE / "source-artifact-recovery-result.json"
EXPECTED_DEVICE = 16777238
EXPECTED_UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"
EXTERNAL_MOUNT = Path("/Volumes/win+mac通用")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def snapshot(path: Path) -> dict:
    state = path.stat()
    return {
        "path": str(path),
        "bytes": state.st_size,
        "sha256": digest(path),
        "device": state.st_dev,
        "inode": state.st_ino,
        "mtime_ns": state.st_mtime_ns,
    }


def exclusive_bytes(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def exclusive_json(path: Path, value: dict) -> None:
    exclusive_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def validate_mount(directory: Path) -> dict:
    if (
        not directory.is_dir()
        or directory.stat().st_dev != EXPECTED_DEVICE
        or not directory.is_relative_to(EXTERNAL_MOUNT)
    ):
        raise RuntimeError("external directory is absent or on the wrong device")
    result = subprocess.run(
        ["diskutil", "info", str(EXTERNAL_MOUNT)], capture_output=True, text=True, check=True
    )
    if f"Volume UUID:               {EXPECTED_UUID}" not in result.stdout:
        raise RuntimeError("external UUID mismatch")
    capacity = os.statvfs(directory)
    return {
        "device": directory.stat().st_dev,
        "uuid": EXPECTED_UUID,
        "free_bytes": capacity.f_bavail * capacity.f_frsize,
    }


def contract_data() -> tuple[dict, Path]:
    data = json.loads(CONTRACT.read_text())
    run_directory = Path(data["external_run_directory"])
    destination = run_directory / "source-artifact-recovery"
    if data["external_write_paths"] != [str(destination)]:
        raise RuntimeError("external destination differs from frozen contract")
    if len(data["input_files"]) != 44 or sum(x["bytes"] for x in data["input_files"]) != 338034:
        raise RuntimeError("contract input set changed")
    if [row["path"] for row in data["input_files"]] != data["external_read_paths"]:
        raise RuntimeError("contract source paths differ from registered read paths")
    if not all(Path(row["path"]).is_relative_to(run_directory) for row in data["input_files"]):
        raise RuntimeError("source outside this fixed output route")
    return data, destination


def backup() -> None:
    data, destination = contract_data()
    device = validate_mount(destination)
    if device["free_bytes"] < 676068 + 10737418240:
        raise RuntimeError("external free capacity below planned reserve")
    inputs = data["input_files"]
    before = [snapshot(Path(row["path"])) for row in inputs]
    for frozen, actual in zip(inputs, before, strict=True):
        if actual["bytes"] != frozen["bytes"] or actual["sha256"] != frozen["sha256"]:
            raise RuntimeError(f"source drift: {frozen['path']}")
    backup_dir = destination / "backup"
    backup_dir.mkdir(exist_ok=False)
    rows = []
    for index, (frozen, source) in enumerate(zip(inputs, before, strict=True), 1):
        target = backup_dir / f"{index:02d}-{Path(frozen['path']).name}"
        exclusive_bytes(target, Path(frozen["path"]).read_bytes())
        copied = snapshot(target)
        if copied["bytes"] != source["bytes"] or copied["sha256"] != source["sha256"]:
            raise RuntimeError(f"backup mismatch: {target}")
        rows.append({"source_before": source, "backup": copied})
    after = [snapshot(Path(row["path"])) for row in inputs]
    if before != after:
        raise RuntimeError("original source changed while backing up")
    manifest = {
        "schema": "p1-source-artifact-backup/1",
        "at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "backup_pid": os.getpid(),
        "script_sha256": digest(Path(__file__)),
        "contract_sha256": digest(CONTRACT),
        "device": device,
        "count": len(rows),
        "total_content_bytes": sum(row["backup"]["bytes"] for row in rows),
        "rows": rows,
        "originals_unchanged_after_backup": True,
    }
    exclusive_json(destination / "backup-manifest.json", manifest)
    print(json.dumps({"pid": os.getpid(), "manifest": str(destination / 'backup-manifest.json')}))


def restore(manifest_path: Path) -> None:
    # This process reads the backup manifest and backup bytes only, never original paths.
    destination = manifest_path.parent
    device = validate_mount(destination)
    manifest = json.loads(manifest_path.read_text())
    if manifest["schema"] != "p1-source-artifact-backup/1" or manifest["count"] != 44:
        raise RuntimeError("invalid backup manifest")
    if manifest["script_sha256"] != digest(Path(__file__)):
        raise RuntimeError("script changed between backup and restore")
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
        "schema": "p1-source-artifact-restore/1",
        "at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "restore_pid": os.getpid(),
        "backup_pid": manifest["backup_pid"],
        "script_sha256": digest(Path(__file__)),
        "device": device,
        "count": len(rows),
        "total_content_bytes": sum(row["restored"]["bytes"] for row in rows),
        "rows": rows,
        "source_read_by_restore_process": False,
    }
    if result["backup_pid"] == result["restore_pid"]:
        raise RuntimeError("backup and restore PIDs are identical")
    exclusive_json(destination / "restore-readback.json", result)
    print(json.dumps({"pid": os.getpid(), "receipt": str(destination / 'restore-readback.json')}))


def run() -> None:
    data, destination = contract_data()
    before = [snapshot(Path(row["path"])) for row in data["input_files"]]
    command = [sys.executable, str(Path(__file__).resolve())]
    backup_run = subprocess.run(command + ["backup"], check=True, capture_output=True, text=True)
    restore_run = subprocess.run(
        command + ["restore", str(destination / "backup-manifest.json")],
        check=True, capture_output=True, text=True,
    )
    manifest_path = destination / "backup-manifest.json"
    receipt_path = destination / "restore-readback.json"
    manifest = json.loads(manifest_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    after = [snapshot(Path(row["path"])) for row in data["input_files"]]
    if before != after or manifest["count"] != 44 or receipt["count"] != 44:
        raise RuntimeError("final source or count verification failed")
    if manifest["total_content_bytes"] != 338034 or receipt["total_content_bytes"] != 338034:
        raise RuntimeError("total bytes mismatch")
    if len({manifest["backup_pid"], receipt["restore_pid"], os.getpid()}) != 3:
        raise RuntimeError("process identities are not distinct")
    result = {
        "schema": "p1-source-artifact-recovery-result/1",
        "at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "status": "same_device_backup_and_separate_process_restore_verified",
        "script_sha256": digest(Path(__file__)),
        "contract_sha256": digest(CONTRACT),
        "original_count": 44,
        "new_backup_count": 44,
        "restored_count": 44,
        "bytes_per_set": 338034,
        "backup_plus_restored_content_bytes": 676068,
        "run_pid": os.getpid(),
        "backup_pid": manifest["backup_pid"],
        "restore_pid": receipt["restore_pid"],
        "backup_manifest": {"path": str(manifest_path), "sha256": digest(manifest_path), "bytes": manifest_path.stat().st_size},
        "restore_readback": {"path": str(receipt_path), "sha256": digest(receipt_path), "bytes": receipt_path.stat().st_size},
        "originals_unchanged": before == after,
        "external_device": receipt["device"],
        "reuse_inspection": "Only the forty-four contract-listed newly generated artifacts were copied; prior twenty and older frozen inputs were not recopied.",
        "limits": "Same physical external device for backup and restored copies. No other-machine or disk-failure recovery established; no source discovery or R2 release implied.",
        "child_stdout": [backup_run.stdout.strip(), restore_run.stdout.strip()],
    }
    exclusive_json(RESULT, result)
    print(json.dumps({"result": str(RESULT), "sha256": digest(RESULT), "backup_pid": manifest["backup_pid"], "restore_pid": receipt["restore_pid"]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["backup", "restore", "run"])
    parser.add_argument("manifest", nargs="?", type=Path)
    args = parser.parse_args()
    if args.mode == "backup":
        backup()
    elif args.mode == "restore":
        if args.manifest is None:
            parser.error("restore requires the backup manifest")
        restore(args.manifest)
    else:
        run()


if __name__ == "__main__":
    main()
