"""Exact, bounded backup and backup-only restore of frozen calendar inputs."""

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
NEW = ROOT / "docs/experiments/raw/szse-remaining-calendar-2016-2019-2026-10-10"
PLAN = RAW / "remaining44-calendar-output-plan.json"
CONTRACT = RAW / "reused-and-remaining-calendar-recovery-contract.json"
NEW_BINDINGS = (
    "executor-contract.json",
    "source-manifest.json",
    "request-ledger.json",
    "date-field-candidate.json",
    "source-review.json",
    "independent-review.json",
)
ROOT_BINDINGS = (
    "calendar-reused-input-recovery-readiness.json",
    "reused-and-remaining-calendar-recovery-contract.json",
)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def preflight(plan, contract, increment):
    mount = Path(plan["external_mount"])
    run = Path(plan["run_directory"])
    device = mount.stat().st_dev
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    assert info.get("VolumeUUID", "").upper() == plan["external_uuid"]
    assert device == run.stat().st_dev == plan["external_device"] != ROOT.stat().st_dev
    assert run.resolve().is_relative_to(mount.resolve())
    assert str(run) == contract["external_run"]
    free_external = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    free_internal = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    before = ordinary_bytes(run)
    assert before + increment <= contract["external_original_run_total_max_bytes"] == plan["estimated_bytes"]
    assert free_external - increment >= plan["external_reserve_bytes"]
    assert free_internal - plan["internal_metadata_bytes"] >= plan["internal_reserve_bytes"]
    return {
        "at": now(), "pid": os.getpid(), "code_sha256": sha(Path(__file__)),
        "external_uuid": info["VolumeUUID"], "external_st_dev": device,
        "run_ordinary_bytes_before": before, "planned_increment_bytes": increment,
        "run_limit_bytes": plan["estimated_bytes"],
        "external_free_bytes": free_external, "internal_free_bytes": free_internal,
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


def backup_inputs(contract):
    readiness = json.loads((RAW / "calendar-reused-input-recovery-readiness.json").read_text())
    source_manifest = json.loads((NEW / "source-manifest.json").read_text())
    assert len(readiness["merged_calendar_monthly_provenance"]["monthly_bodies"]) == 82
    assert len(source_manifest["sources"]) == 44
    inputs = []
    for item in readiness["exact_reused_inputs"][:2]:
        inputs.append(("nominal_csv", Path(item["path"]).name, ROOT / item["path"], item["sha256"], item["bytes"]))
    for item in readiness["merged_calendar_monthly_provenance"]["monthly_bodies"]:
        inputs.append(("old_month_body", Path(item["path"]).name, ROOT / item["path"], item["recorded_body_sha256"], item["recorded_body_bytes"]))
    for item in source_manifest["sources"]:
        assert item["status"] in ("qualified_month_source", "failed_validation")
        body = Path(item["body_path"])
        header = Path(item["headers_path"])
        assert body.parent == Path(contract["external_run"]) and header.parent == body.parent
        inputs.append(("new_month_body", body.name, body, item["sha256"], item["bytes"]))
        inputs.append(("new_month_header", header.name, header, sha(header), header.stat().st_size))
    for name in NEW_BINDINGS:
        p = NEW / name
        inputs.append(("binding_new", name, p, sha(p), p.stat().st_size))
    for name in ROOT_BINDINGS:
        p = RAW / name
        inputs.append(("binding_root", name, p, sha(p), p.stat().st_size))
    assert len(inputs) == 180
    assert len({(role, logical) for role, logical, *_ in inputs}) == 180
    assert sum(size for role, _, _, _, size in inputs if role == "nominal_csv") == 882923
    assert sum(size for role, _, _, _, size in inputs if role == "old_month_body") == 107496
    assert sum(size for role, _, _, _, size in inputs if role == "new_month_body") == 57648
    for _, _, src, expected, size in inputs:
        assert src.is_file() and not src.is_symlink()
        assert src.stat().st_size == size and sha(src) == expected
    components = []
    for part in readiness["merged_calendar_monthly_provenance"]["component_calendars"]:
        p = ROOT / part["path"]
        assert p.is_file() and sha(p) == part["sha256"]
        components.append({"path": part["path"], "sha256": part["sha256"], "bytes": p.stat().st_size,
                           "binding_mode": "verified_original_path_only_no_copy"})
    return inputs, components


def backup(plan, contract):
    run = Path(plan["run_directory"])
    base = run / "result/recovery-v1"
    assert not base.exists()
    inputs, components = backup_inputs(contract)
    total = sum(item[4] for item in inputs)
    code_path = Path(__file__)
    code_sha = sha(code_path)
    guard = preflight(plan, contract, 2 * total + code_path.stat().st_size + 524288)
    base.mkdir(parents=True, exist_ok=False)
    snapshot = base / "code/calendar-recovery-copy.py"
    code_copy = copy_exact(code_path, snapshot, code_sha, code_path.stat().st_size)
    rows = []
    for role, logical, src, expected, size in inputs:
        preflight(plan, contract, size)
        dst = base / "backup" / role / logical
        detail = copy_exact(src, dst, expected, size)
        rows.append({"role": role, "logical_path": logical, "original_path": str(src),
                     "backup_path": str(dst), **detail})
    write_new(RAW / "calendar-recovery-backup-manifest.json", {
        "schema": "calendar-recovery-backup-manifest/1", "at": now(),
        "contract_sha256": sha(CONTRACT), "run_directory": str(run),
        "preflight": guard, "code_snapshot_path": str(snapshot), "code_snapshot": code_copy,
        "component_calendar_references": components, "files": rows,
        "file_count": len(rows), "bytes_per_set": total,
        "originals_not_removed": True, "same_external_device_only": True,
    })
    print(json.dumps({"mode": "backup", "pid": os.getpid(), "files": len(rows), "bytes": total}))


def restore(plan, contract):
    run = Path(plan["run_directory"])
    base = run / "result/recovery-v1"
    manifest = json.loads((RAW / "calendar-recovery-backup-manifest.json").read_text())
    assert manifest["run_directory"] == str(run)
    assert manifest["contract_sha256"] == sha(CONTRACT)
    assert os.getpid() != manifest["preflight"]["pid"]
    assert sha(Path(__file__)) == sha(Path(manifest["code_snapshot_path"])) == manifest["preflight"]["code_sha256"]
    guard = preflight(plan, contract, manifest["bytes_per_set"] + 524288)
    rows = []
    backup_root = (base / "backup").resolve()
    for item in manifest["files"]:
        src = Path(item["backup_path"])
        assert src.resolve().is_relative_to(backup_root)
        preflight(plan, contract, item["bytes"])
        dst = base / "restored" / item["role"] / item["logical_path"]
        detail = copy_exact(src, dst, item["sha256"], item["bytes"])
        rows.append({"role": item["role"], "logical_path": item["logical_path"],
                     "backup_path": str(src), "restored_path": str(dst), **detail})
    write_new(RAW / "calendar-recovery-restore-readback.json", {
        "schema": "calendar-recovery-restore-readback/1", "at": now(),
        "preflight": guard, "code_snapshot_sha256": manifest["preflight"]["code_sha256"],
        "backup_manifest_sha256": sha(RAW / "calendar-recovery-backup-manifest.json"),
        "files": rows, "file_count": len(rows), "bytes_per_set": manifest["bytes_per_set"],
        "backup_only_byte_source": True, "different_pid_from_backup": True,
        "same_external_device_only": True, "other_machine_verified": False,
    })
    all_files = [
        {"relative_path": p.relative_to(run).as_posix(), "bytes": p.stat().st_size,
         "sha256": sha(p), "st_dev": p.stat().st_dev}
        for p in sorted(run.rglob("*")) if p.is_file()
        and not any(x.startswith("._") or x == ".DS_Store" for x in p.relative_to(run).parts)
    ]
    write_new(RAW / "calendar-recovery-result-location.json", {
        "schema": "calendar-recovery-result-location/1", "at": now(),
        "run_directory": str(run), "external_uuid": plan["external_uuid"],
        "external_st_dev": plan["external_device"], "files": all_files,
        "ordinary_file_count": len(all_files), "ordinary_bytes": sum(f["bytes"] for f in all_files),
        "metadata_files_excluded_and_preserved": True,
    })
    print(json.dumps({"mode": "restore", "pid": os.getpid(), "files": len(rows),
                      "bytes": manifest["bytes_per_set"], "run_ordinary_bytes": sum(f["bytes"] for f in all_files)}))


if __name__ == "__main__":
    plan = json.loads(PLAN.read_text())
    contract = json.loads(CONTRACT.read_text())
    if sys.argv[1] == "backup":
        backup(plan, contract)
    elif sys.argv[1] == "restore":
        restore(plan, contract)
    else:
        raise ValueError("mode must be backup or restore")
