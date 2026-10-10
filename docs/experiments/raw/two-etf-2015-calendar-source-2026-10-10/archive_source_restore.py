"""Copy the exact 2015 calendar source set, then restore it from the copy."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
PLAN = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/calendar2015-output-plan.json"
BINDINGS = (
    "executor-contract.json",
    "request-ledger.json",
    "source-review.json",
    "date-field-qualification.json",
    "source-manifest.json",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def stamp():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()


def ordinary_bytes(run):
    return sum(
        path.stat().st_size
        for path in run.rglob("*")
        if path.is_file()
        and not any(
            item.startswith("._") or item == ".DS_Store"
            for item in path.relative_to(run).parts
        )
    )


def preflight(plan, increment):
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    run = Path(plan["run_directory"])
    assert info.get("VolumeUUID", "").upper() == plan["external_uuid"]
    assert mount.stat().st_dev == run.stat().st_dev == plan["external_device"]
    assert ROOT.stat().st_dev != plan["external_device"]
    assert run.is_dir() and run.resolve().is_relative_to(mount.resolve())
    external_free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    internal_free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    assert external_free - increment >= plan["external_reserve_bytes"]
    assert internal_free - plan["internal_metadata_bytes"] >= plan["internal_reserve_bytes"]
    assert ordinary_bytes(run) + increment <= plan["estimated_bytes"]
    return {
        "at": stamp(),
        "external_uuid": info["VolumeUUID"],
        "external_st_dev": run.stat().st_dev,
        "external_free_bytes": external_free,
        "internal_free_bytes": internal_free,
        "ordinary_bytes_before": ordinary_bytes(run),
        "increment_bytes": increment,
        "run_limit_bytes": plan["estimated_bytes"],
        "pid": os.getpid(),
        "code_sha256": digest(Path(__file__)),
    }


def copy_exact(src, dst, expected_sha, expected_bytes):
    assert src.is_file() and not src.is_symlink()
    before = src.stat()
    assert before.st_size == expected_bytes and digest(src) == expected_sha
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as reader, dst.open("xb") as writer:
        for part in iter(lambda: reader.read(1024 * 1024), b""):
            writer.write(part)
        writer.flush()
        os.fsync(writer.fileno())
    after = src.stat()
    assert (before.st_ino, before.st_mtime_ns, before.st_size) == (
        after.st_ino, after.st_mtime_ns, after.st_size
    )
    assert dst.stat().st_size == expected_bytes and digest(dst) == expected_sha
    return {
        "bytes": expected_bytes,
        "sha256": expected_sha,
        "source_inode": before.st_ino,
        "source_mtime_ns": before.st_mtime_ns,
        "source_unchanged": True,
    }


def write_new(path, payload):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def backup(plan):
    run = Path(plan["run_directory"])
    source_manifest = json.loads((RAW / "source-manifest.json").read_text())
    assert source_manifest["external_run"] == str(run)
    assert len(source_manifest["sources"]) == 15
    inputs = []
    for source in source_manifest["sources"]:
        src = Path(source["path"])
        assert src.parent.resolve() == run.resolve()
        inputs.append(("original_response", src.name, src, source["sha256"], source["bytes"]))
    for name in BINDINGS:
        src = RAW / name
        inputs.append(("stage_binding", name, src, digest(src), src.stat().st_size))
    assert len(inputs) == len({logical for _, logical, *_ in inputs}) == 20
    total = sum(size for _, _, _, _, size in inputs)
    assert sum(size for role, _, _, _, size in inputs if role == "original_response") == 93075
    for _, _, src, expected, size in inputs:
        assert src.is_file() and not src.is_symlink()
        assert src.stat().st_size == size and digest(src) == expected
    guard = preflight(plan, total * 2)
    rows = []
    for role, logical, src, expected, size in inputs:
        preflight(plan, size)
        dst = run / "result/calendar-source-backups" / role / logical
        detail = copy_exact(src, dst, expected, size)
        rows.append({
            "role": role,
            "logical_path": logical,
            "original_path": str(src),
            "backup_path": str(dst),
            **detail,
        })
    write_new(RAW / "archive-source-manifest.json", {
        "schema": "two-etf-2015-calendar-source-backup/1",
        "at": stamp(),
        "run_directory": str(run),
        "preflight": guard,
        "files": rows,
        "original_response_count": 15,
        "binding_count": 5,
        "bytes_per_set": total,
        "same_external_device_only": True,
        "other_machine_verified": False,
    })
    print(json.dumps({"mode": "backup", "files": len(rows), "bytes": total, "pid": os.getpid()}))


def restore(plan):
    run = Path(plan["run_directory"])
    manifest = json.loads((RAW / "archive-source-manifest.json").read_text())
    assert manifest["run_directory"] == str(run)
    assert os.getpid() != manifest["preflight"]["pid"]
    assert digest(Path(__file__)) == manifest["preflight"]["code_sha256"]
    guard = preflight(plan, manifest["bytes_per_set"])
    rows = []
    backup_root = (run / "result/calendar-source-backups").resolve()
    for row in manifest["files"]:
        src = Path(row["backup_path"])
        assert src.resolve().is_relative_to(backup_root)
        preflight(plan, row["bytes"])
        dst = run / "result/restored-calendar-sources" / row["role"] / row["logical_path"]
        detail = copy_exact(src, dst, row["sha256"], row["bytes"])
        rows.append({
            "role": row["role"],
            "logical_path": row["logical_path"],
            "backup_path": str(src),
            "restored_path": str(dst),
            **detail,
        })
    write_new(RAW / "archive-restore-readback.json", {
        "schema": "two-etf-2015-calendar-source-restore/1",
        "at": stamp(),
        "preflight": guard,
        "files": rows,
        "bytes_per_set": manifest["bytes_per_set"],
        "different_process_from_backup": True,
        "same_code_sha256_as_backup": True,
        "restore_byte_source": "backup_path_only",
        "same_external_device_only": True,
        "other_machine_verified": False,
    })
    files = [
        {"relative_path": path.relative_to(run).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in sorted(run.rglob("*"))
        if path.is_file()
        and not any(
            item.startswith("._") or item == ".DS_Store"
            for item in path.relative_to(run).parts
        )
    ]
    write_new(RAW / "result-location.json", {
        "schema": "two-etf-2015-calendar-source-result-location/1",
        "at": stamp(),
        "run_directory": str(run),
        "external_uuid": plan["external_uuid"],
        "external_st_dev": plan["external_device"],
        "files": files,
        "ordinary_file_count": len(files),
        "ordinary_bytes": sum(item["bytes"] for item in files),
        "metadata_files_excluded_and_preserved": True,
    })
    print(json.dumps({"mode": "restore", "files": len(rows), "bytes": manifest["bytes_per_set"], "pid": os.getpid()}))


if __name__ == "__main__":
    plan = json.loads(PLAN.read_text())
    if sys.argv[1] == "backup":
        backup(plan)
    elif sys.argv[1] == "restore":
        restore(plan)
    else:
        raise ValueError("expected backup or restore")
