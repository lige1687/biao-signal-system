"""Non-overwriting backup and backup-only restore of twelve fixed saved account CSVs."""

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "idle-input-recovery-contract.json"
PLAN = HERE / "idle-input-recovery-storage-plan.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_plan():
    contract = json.loads(CONTRACT.read_text())
    plan = json.loads(PLAN.read_text())
    root = Path(contract["external_write_paths"][0])
    if root != Path(plan["run_directory"]) / "recovery-proof":
        raise ValueError("fixed recovery proof path differs from storage plan")
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (not mount.is_mount() or mount.stat().st_dev != plan["external_device"]
            or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("fixed external device mismatch")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free <= plan["external_reserve_bytes"] + plan["estimated_bytes"]:
        raise ValueError("fixed external capacity insufficient")
    if root.stat().st_dev != plan["external_device"]:
        raise ValueError("recovery proof directory is on wrong device")
    return contract, plan, root


def stat_id(path):
    s = path.stat()
    return {"device": s.st_dev, "inode": s.st_ino, "size": s.st_size,
            "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns}


def save_json(path, value):
    with path.open("x") as file:
        json.dump(value, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")


def backup(contract, plan, root):
    target = root / "backup"
    if target.exists():
        raise ValueError("backup already exists; inspect it before any continuation")
    target.mkdir(exist_ok=False)
    rows = []
    for item in contract["input_csvs"]:
        source = Path(item["path"])
        before = stat_id(source)
        raw = source.read_bytes()
        if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
            raise ValueError(f"frozen source mismatch: {source}")
        destination = target / source.name
        with destination.open("xb") as file:
            file.write(raw)
        after = stat_id(source)
        copy = destination.read_bytes()
        if before != after or len(copy) != len(raw) or digest(copy) != item["sha256"]:
            raise ValueError(f"source changed or copy mismatch: {source}")
        rows.append({"source": str(source), "name": source.name,
                     "source_stat_before": before, "source_stat_after_backup": after,
                     "backup": str(destination), "backup_device": destination.stat().st_dev,
                     "bytes": len(copy), "sha256": item["sha256"]})
    result = {"schema_version": 1, "mode": "backup", "pid": os.getpid(),
              "external_device": plan["external_device"], "external_uuid": plan["external_uuid"],
              "files": rows, "file_count": len(rows), "content_bytes": sum(r["bytes"] for r in rows),
              "source_files_preserved": all(r["source_stat_before"] == r["source_stat_after_backup"] for r in rows)}
    save_json(target / "manifest.json", result)
    print(json.dumps({"pid": os.getpid(), "mode": "backup", "files": len(rows),
                      "content_bytes": result["content_bytes"]}))


def restore(plan, root):
    backup_root = root / "backup"
    manifest = json.loads((backup_root / "manifest.json").read_text())
    if manifest.get("mode") != "backup" or manifest.get("file_count") != 12:
        raise ValueError("backup manifest incomplete")
    target = root / "restored"
    if target.exists():
        raise ValueError("restored directory already exists; inspect before continuation")
    target.mkdir(exist_ok=False)
    rows = []
    for item in manifest["files"]:
        source = backup_root / item["name"]
        raw = source.read_bytes()
        if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
            raise ValueError(f"backup copy mismatch: {source}")
        destination = target / item["name"]
        with destination.open("xb") as file:
            file.write(raw)
        recovered = destination.read_bytes()
        if len(recovered) != item["bytes"] or digest(recovered) != item["sha256"]:
            raise ValueError(f"restored copy mismatch: {destination}")
        rows.append({"backup": str(source), "backup_device": source.stat().st_dev,
                     "restored": str(destination), "restored_device": destination.stat().st_dev,
                     "bytes": len(recovered), "sha256": item["sha256"]})
    result = {"schema_version": 1, "mode": "backup_only_restore", "pid": os.getpid(),
              "backup_pid": manifest["pid"], "original_sources_opened_by_restore": False,
              "external_device": plan["external_device"], "external_uuid": plan["external_uuid"],
              "files": rows, "file_count": len(rows), "content_bytes": sum(r["bytes"] for r in rows)}
    save_json(target / "restore-manifest.json", result)
    print(json.dumps({"pid": os.getpid(), "mode": "backup_only_restore", "files": len(rows),
                      "content_bytes": result["content_bytes"]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("backup", "restore"))
    args = parser.parse_args()
    contract, plan, root = checked_plan()
    if args.mode == "backup":
        backup(contract, plan, root)
    else:
        restore(plan, root)


if __name__ == "__main__":
    main()
