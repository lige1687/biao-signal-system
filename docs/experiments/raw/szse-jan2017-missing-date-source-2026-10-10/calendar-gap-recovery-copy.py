"""Back up the exact saved Jan 2017 gap evidence and restore from that backup."""

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
PLAN = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/jan2017-source-output-plan.json"
BINDINGS = (
    "executor-contract.json",
    "source-manifest.json",
    "request-ledger.json",
    "source-review.json",
    "independent-review.json",
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def ordinary_bytes(run):
    return sum(
        p.stat().st_size for p in run.rglob("*")
        if p.is_file()
        and not any(x.startswith("._") or x == ".DS_Store" for x in p.relative_to(run).parts)
    )


def guard(plan, increment):
    run = Path(plan["run_directory"])
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    assert info.get("VolumeUUID", "").upper() == plan["external_uuid"]
    assert run.is_dir() and run.resolve().is_relative_to(mount.resolve())
    assert run.stat().st_dev == mount.stat().st_dev == plan["external_device"] != ROOT.stat().st_dev
    external_free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    internal_free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    used = ordinary_bytes(run)
    assert used + increment <= plan["estimated_bytes"]
    assert external_free - increment >= plan["external_reserve_bytes"]
    assert internal_free - plan["internal_metadata_bytes"] >= plan["internal_reserve_bytes"]
    return {
        "at": now(), "pid": os.getpid(), "code_sha256": sha(Path(__file__)),
        "external_uuid": info["VolumeUUID"], "external_st_dev": run.stat().st_dev,
        "run_ordinary_bytes_before": used, "increment_bytes": increment,
        "run_limit_bytes": plan["estimated_bytes"],
        "external_free_bytes": external_free, "internal_free_bytes": internal_free,
    }


def copy_exact(src, dst, expected_sha, expected_bytes):
    assert src.is_file() and not src.is_symlink()
    before = src.stat()
    assert before.st_size == expected_bytes and sha(src) == expected_sha
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as reader, dst.open("xb") as writer:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            writer.write(block)
        writer.flush()
        os.fsync(writer.fileno())
    after = src.stat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    )
    assert sha(src) == sha(dst) == expected_sha and dst.stat().st_size == expected_bytes
    return {
        "bytes": expected_bytes, "sha256": expected_sha,
        "source_st_dev": before.st_dev, "source_inode": before.st_ino,
        "source_mtime_ns": before.st_mtime_ns, "source_unchanged": True,
    }


def backup(plan):
    run = Path(plan["run_directory"])
    base = run / "result/recovery-v1"
    assert not base.exists()
    manifest = json.loads((RAW / "source-manifest.json").read_text())
    assert manifest["external_run"] == str(run) and len(manifest["sources"]) == 3
    inputs = []
    for source in manifest["sources"]:
        p = Path(source["raw_path"])
        assert p.parent.resolve() == run.resolve()
        inputs.append(("saved_response", p.name, p, source["raw_sha256"], source["raw_bytes"]))
        if source["headers_path"]:
            h = Path(source["headers_path"])
            assert h.parent.resolve() == run.resolve()
            inputs.append(("response_header", h.name, h, sha(h), h.stat().st_size))
    for name in BINDINGS:
        p = RAW / name
        inputs.append(("binding", name, p, sha(p), p.stat().st_size))
    assert len(inputs) == 9 and len({(role, name) for role, name, *_ in inputs}) == 9
    assert sum(size for role, _, _, _, size in inputs if role == "saved_response") == 38485
    assert sha(RAW / "independent-review.json") == "fdcda77d4da25550ec68939f1fd0ec973934dee5deb1c867ad5891157ad573f9"
    for _, _, src, expected, size in inputs:
        assert src.is_file() and not src.is_symlink()
        assert src.stat().st_size == size and sha(src) == expected
    total = sum(item[4] for item in inputs)
    code = Path(__file__)
    preflight = guard(plan, 2 * total + code.stat().st_size + 262144)
    base.mkdir(parents=True, exist_ok=False)
    snapshot = base / "code/calendar-gap-recovery-copy.py"
    copy_exact(code, snapshot, preflight["code_sha256"], code.stat().st_size)
    rows = []
    for role, name, src, expected, size in inputs:
        guard(plan, size)
        dst = base / "backup" / role / name
        rows.append({"role": role, "logical_path": name, "original_path": str(src),
                     "backup_path": str(dst), **copy_exact(src, dst, expected, size)})
    write_new(RAW / "calendar-gap-recovery-backup-manifest.json", {
        "schema": "calendar-gap-recovery-backup/1", "at": now(),
        "preflight": preflight, "code_snapshot_path": str(snapshot),
        "run_directory": str(run), "files": rows, "file_count": len(rows),
        "bytes_per_set": total, "same_external_device_only": True,
        "saved_response_is_not_qualified_date_field": True,
    })
    print(json.dumps({"mode": "backup", "pid": os.getpid(), "files": len(rows), "bytes": total}))


def restore(plan):
    run = Path(plan["run_directory"])
    base = run / "result/recovery-v1"
    manifest = json.loads((RAW / "calendar-gap-recovery-backup-manifest.json").read_text())
    assert manifest["run_directory"] == str(run)
    assert os.getpid() != manifest["preflight"]["pid"]
    assert sha(Path(__file__)) == sha(Path(manifest["code_snapshot_path"])) == manifest["preflight"]["code_sha256"]
    preflight = guard(plan, manifest["bytes_per_set"] + 262144)
    rows = []
    backup_root = (base / "backup").resolve()
    for item in manifest["files"]:
        src = Path(item["backup_path"])
        assert src.resolve().is_relative_to(backup_root)
        guard(plan, item["bytes"])
        dst = base / "restored" / item["role"] / item["logical_path"]
        rows.append({"role": item["role"], "logical_path": item["logical_path"],
                     "backup_path": str(src), "restored_path": str(dst),
                     **copy_exact(src, dst, item["sha256"], item["bytes"])})
    write_new(RAW / "calendar-gap-recovery-restore-readback.json", {
        "schema": "calendar-gap-recovery-restore/1", "at": now(),
        "preflight": preflight,
        "backup_manifest_sha256": sha(RAW / "calendar-gap-recovery-backup-manifest.json"),
        "files": rows, "file_count": len(rows), "bytes_per_set": manifest["bytes_per_set"],
        "backup_only_byte_source": True, "different_pid_from_backup": True,
        "same_external_device_only": True, "other_machine_verified": False,
    })
    files = [
        {"relative_path": p.relative_to(run).as_posix(), "bytes": p.stat().st_size,
         "sha256": sha(p), "st_dev": p.stat().st_dev}
        for p in sorted(run.rglob("*")) if p.is_file()
        and not any(x.startswith("._") or x == ".DS_Store" for x in p.relative_to(run).parts)
    ]
    write_new(RAW / "calendar-gap-recovery-result-location.json", {
        "schema": "calendar-gap-recovery-result-location/1", "at": now(),
        "run_directory": str(run), "external_uuid": plan["external_uuid"],
        "external_st_dev": plan["external_device"], "files": files,
        "ordinary_file_count": len(files), "ordinary_bytes": sum(x["bytes"] for x in files),
        "metadata_files_excluded_and_preserved": True,
    })
    print(json.dumps({"mode": "restore", "pid": os.getpid(), "files": len(rows),
                      "bytes": manifest["bytes_per_set"], "run_ordinary_bytes": sum(x["bytes"] for x in files)}))


if __name__ == "__main__":
    plan = json.loads(PLAN.read_text())
    if sys.argv[1] == "backup":
        backup(plan)
    elif sys.argv[1] == "restore":
        restore(plan)
    else:
        raise ValueError("expected backup or restore")
