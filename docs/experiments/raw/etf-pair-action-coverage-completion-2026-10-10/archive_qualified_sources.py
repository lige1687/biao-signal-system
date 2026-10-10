"""Back up and restore this qualified source set without changing originals."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).parent
PLAN = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/etf-full-actions-output-plan.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def ordinary_bytes(path):
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()
               and not any(x.startswith("._") or x == ".DS_Store" for x in p.relative_to(path).parts))


def stamp():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()


def record(path, data):
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def guard(plan, increment):
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    assert info.get("VolumeUUID", "").upper() == plan["external_uuid"]
    assert mount.stat().st_dev == plan["external_device"] != ROOT.stat().st_dev
    run = Path(plan["run_directory"])
    assert run.is_dir() and run.resolve().is_relative_to(mount.resolve())
    assert run.stat().st_dev == plan["external_device"]
    sv = os.statvfs(mount)
    free = sv.f_bavail * sv.f_frsize
    iv = os.statvfs(ROOT)
    internal = iv.f_bavail * iv.f_frsize
    assert free - increment >= plan["external_reserve_bytes"]
    assert internal - plan["internal_metadata_bytes"] >= plan["internal_reserve_bytes"]
    assert ordinary_bytes(run) + increment <= plan["estimated_bytes"]
    return {"at": stamp(), "uuid": info["VolumeUUID"], "st_dev": mount.stat().st_dev,
            "external_free_bytes": free, "internal_free_bytes": internal,
            "existing_run_ordinary_bytes": ordinary_bytes(run), "increment_bytes": increment,
            "planned_total_limit_bytes": plan["estimated_bytes"], "actual_pid": os.getpid()}


def copy_exact(src, dst, expected):
    assert src.is_file() and not src.is_symlink()
    before = src.stat()
    assert sha(src) == expected
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as f, dst.open("xb") as g:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            g.write(part)
        g.flush()
        os.fsync(g.fileno())
    after = src.stat()
    assert (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns)
    assert sha(src) == sha(dst) == expected and dst.stat().st_size == before.st_size
    return {"bytes": before.st_size, "sha256": expected, "source_inode": before.st_ino,
            "source_mtime_ns": before.st_mtime_ns, "source_unchanged": True}


def main():
    plan = json.loads(PLAN.read_text())
    run = Path(plan["run_directory"])
    mode = sys.argv[1]
    if mode == "backup":
        checks = json.loads((RAW / "coverage-assembly-checks.json").read_text())
        inputs = {}
        for path, meta in checks["source_file_checks"].items():
            inputs[path] = (meta["actual_sha256"], "source_original")
        for path, meta in checks["accepted_evidence_checks"].items():
            inputs[path] = (meta["sha256"], "accepted_review_evidence")
        for name in ["qualified-action-evidence.v1.json", "coverage-assembly-candidate.json",
                     "coverage-assembly-checks.json", "controller-source-acceptance.json",
                     "independent-reuse-review.json", "executor-contract.json", "source-manifest.json",
                     "source-review.json", "request-ledger.json"]:
            p = RAW / name
            inputs[p.relative_to(ROOT).as_posix()] = (sha(p), "stage_binding")
        total = sum((Path(p) if Path(p).is_absolute() else ROOT / p).stat().st_size for p in inputs)
        preflight = guard(plan, total * 2)
        rows = []
        for path, (expected, role) in sorted(inputs.items()):
            src = Path(path) if Path(path).is_absolute() else ROOT / path
            logical = "new-source-originals/" + src.name if Path(path).is_absolute() else path
            dst = run / "result/qualified-source-backups" / logical
            guard(plan, src.stat().st_size)
            copied = copy_exact(src, dst, expected)
            rows.append({"logical_path": logical, "original_path": str(src), "backup_path": str(dst),
                         "role": role, **copied})
        record(RAW / "archive-source-manifest.json", {"schema": "qualified-action-source-backup/1",
            "at": stamp(), "task_id": plan["task_id"], "run_directory": str(run),
            "preflight": preflight, "source_original_count": 25, "files": rows,
            "total_bytes": total, "restore_not_yet_verified": True,
            "same_external_device_only": True, "other_machine_verified": False})
        print(json.dumps({"mode": mode, "files": len(rows), "bytes": total, "pid": os.getpid()}))
    elif mode == "restore":
        manifest = json.loads((RAW / "archive-source-manifest.json").read_text())
        assert os.getpid() != manifest["preflight"]["actual_pid"]
        preflight = guard(plan, manifest["total_bytes"])
        rows = []
        for row in manifest["files"]:
            src = Path(row["backup_path"])
            assert src.resolve().is_relative_to((run / "result/qualified-source-backups").resolve())
            dst = run / "result/restored-qualified-sources" / row["logical_path"]
            guard(plan, row["bytes"])
            copied = copy_exact(src, dst, row["sha256"])
            rows.append({"logical_path": row["logical_path"], "backup_path": str(src),
                         "restored_path": str(dst), "role": row["role"], **copied})
        record(RAW / "archive-restore-readback.json", {"schema": "qualified-action-source-restore/1",
            "at": stamp(), "preflight": preflight, "files": rows, "all_bytes_and_hashes_equal": True,
            "original_source_files_not_used_by_restore": True, "different_process_from_backup": True,
            "same_external_device_only": True, "other_machine_verified": False})
        files = [{"relative_path": p.relative_to(run).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
                 for p in sorted(run.rglob("*")) if p.is_file()
                 and not any(x.startswith("._") or x == ".DS_Store" for x in p.relative_to(run).parts)]
        record(RAW / "result-location.json", {"schema": "qualified-action-result-location/1",
            "at": stamp(), "run_directory": str(run), "device_uuid": plan["external_uuid"],
            "device_number": plan["external_device"], "files": files, "ordinary_file_count": len(files),
            "ordinary_bytes": sum(p["bytes"] for p in files), "metadata_files_excluded_and_preserved": True})
        print(json.dumps({"mode": mode, "files": len(rows), "pid": os.getpid(),
                          "run_ordinary_bytes": sum(p["bytes"] for p in files)}))
    else:
        raise ValueError("mode must be backup or restore")


if __name__ == "__main__":
    main()
