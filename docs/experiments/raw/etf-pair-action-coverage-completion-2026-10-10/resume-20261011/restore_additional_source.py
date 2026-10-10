"""Copy and independently restore only the resumed 510300 2017 source/bindings."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
PLAN = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/etf-full-actions-output-plan.json"
CONTRACT = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/annual-source-resume-contract-20261011.json"
APPROVAL = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/human-approval-20261011.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()


def guard(plan, increment):
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    assert info.get("VolumeUUID", "").upper() == plan["external_uuid"]
    assert mount.stat().st_dev == plan["external_device"] != ROOT.stat().st_dev
    run = Path(plan["run_directory"])
    assert run.is_dir() and run.stat().st_dev == plan["external_device"]
    assert run.resolve().is_relative_to(mount.resolve())
    external_free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    internal_free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    assert external_free - increment >= plan["external_reserve_bytes"]
    assert internal_free - plan["internal_metadata_bytes"] >= plan["internal_reserve_bytes"]
    current = sum(p.stat().st_size for p in run.rglob("*") if p.is_file()
                  and not any(part.startswith("._") or part == ".DS_Store" for part in p.relative_to(run).parts))
    assert current + increment <= plan["estimated_bytes"]
    return {"at": now(), "pid": os.getpid(), "uuid": info["VolumeUUID"],
            "st_dev": run.stat().st_dev, "external_free_bytes": external_free,
            "internal_free_bytes": internal_free, "run_ordinary_bytes": current,
            "increment_bytes": increment, "planned_total_limit_bytes": plan["estimated_bytes"]}


def copy_exact(src, dst, expected):
    assert src.is_file() and not src.is_symlink() and sha(src) == expected
    before = src.stat()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as inp, dst.open("xb") as out:
        shutil.copyfileobj(inp, out, 1024 * 1024)
        out.flush()
        os.fsync(out.fileno())
    after = src.stat()
    assert (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns)
    assert dst.stat().st_size == before.st_size and sha(dst) == expected and sha(src) == expected
    return {"bytes": before.st_size, "sha256": expected, "source_inode": before.st_ino,
            "source_mtime_ns": before.st_mtime_ns, "source_unchanged": True}


def write_new(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main(mode):
    plan = json.loads(PLAN.read_text())
    run = Path(plan["run_directory"])
    source_meta = json.loads((HERE / "source-manifest.json").read_text())["source"]
    original = Path(source_meta["path"])
    assert original.is_relative_to(run / "resume-20261011")
    assert sha(original) == source_meta["sha256"]
    code_sha = sha(Path(__file__))
    if mode == "backup":
        inputs = [original, Path(source_meta["headers_path"]), HERE / "amended-request-ledger.json",
                  HERE / "source-manifest.json", HERE / "source-review.json", Path(__file__), CONTRACT, APPROVAL]
        total = sum(p.stat().st_size for p in inputs)
        preflight = guard(plan, total * 2)
        rows = []
        for src in inputs:
            rel = "original/" + src.name if src == original else "bindings/" + src.name
            dst = run / "resume-20261011/backup" / rel
            copied = copy_exact(src, dst, sha(src))
            rows.append({"logical_path": rel, "source_path": str(src), "backup_path": str(dst), **copied})
        write_new(HERE / "additional-source-backup-manifest.json", {
            "schema": "etf-pair-full-actions-additional-source-backup/1", "at": now(),
            "preflight": preflight, "executed_code_sha256": code_sha,
            "files": rows, "total_bytes": total, "old_42_copied_again": False,
            "same_external_device_only": True, "other_machine_verified": False})
        print(json.dumps({"mode": mode, "pid": os.getpid(), "files": len(rows), "bytes": total}))
    elif mode == "restore":
        manifest = json.loads((HERE / "additional-source-backup-manifest.json").read_text())
        assert code_sha == manifest["executed_code_sha256"]
        assert os.getpid() != manifest["preflight"]["pid"]
        preflight = guard(plan, manifest["total_bytes"])
        rows = []
        for row in manifest["files"]:
            src = Path(row["backup_path"])
            assert src.is_relative_to(run / "resume-20261011/backup")
            dst = run / "resume-20261011/restored" / row["logical_path"]
            copied = copy_exact(src, dst, row["sha256"])
            rows.append({"logical_path": row["logical_path"], "backup_path": str(src),
                         "restored_path": str(dst), "original_source_path": row["source_path"], **copied,
                         "original_unchanged": sha(Path(row["source_path"])) == row["sha256"]})
        write_new(HERE / "additional-source-restore-evidence.json", {
            "schema": "etf-pair-full-actions-additional-source-restore/1", "at": now(),
            "preflight": preflight, "backup_pid": manifest["preflight"]["pid"],
            "restore_pid": os.getpid(), "different_process_from_backup": True,
            "executed_code_sha256": code_sha, "files": rows,
            "all_bytes_and_hashes_equal": True, "originals_unchanged": all(r["original_unchanged"] for r in rows),
            "old_42_copied_again": False, "same_external_device_only": True,
            "other_machine_verified": False})
        print(json.dumps({"mode": mode, "pid": os.getpid(), "files": len(rows)}))
    else:
        raise ValueError("mode must be backup or restore")


if __name__ == "__main__":
    main(sys.argv[1])
