"""Verify a task packet and restore into a NEW, empty directory; no fitting/network."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--supplement", type=Path)
    args = parser.parse_args()
    packet = Path(__file__).resolve().parents[1]
    manifest = json.loads((packet / "manifest.json").read_text())
    for item in manifest["files"]:
        p = packet / item["path"]
        if not p.resolve().is_relative_to(packet) or p.is_symlink():
            raise ValueError("invalid packet path")
        if p.stat().st_size != item["size"] or digest(p) != item["sha256"]:
            raise ValueError("packet integrity mismatch: " + item["path"])
    checksum_lines = (packet / "SHA256SUMS").read_text().splitlines()
    for line in checksum_lines:
        expected, name = line.split("  ", 1)
        p = packet / name
        if not p.resolve().is_relative_to(packet) or digest(p) != expected:
            raise ValueError("SHA256SUMS mismatch: " + name)
    print(json.dumps({"packet": "verified", "file_count": len(manifest["files"])}))
    if args.verify_only:
        return
    if args.output is None:
        parser.error("--output is required unless --verify-only")
    dest = args.output.resolve()
    if dest.exists() and any(dest.iterdir()):
        raise ValueError("destination must be empty; never overlay a shared worktree")
    inventory = json.loads((packet / "evidence/materials-inventory.json").read_text())
    if args.supplement and digest(args.supplement) != inventory["archive"]["sha256"]:
        raise ValueError("supplement archive fingerprint mismatch")
    dest.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads((packet / "evidence/source-snapshot.json").read_text())
    for item in snapshot["files"]:
        target = dest / item["source_path"]
        if not target.resolve().is_relative_to(dest):
            raise ValueError("invalid destination path")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(packet / item["package_path"], target)
        if digest(target) != item["sha256"]:
            raise ValueError("restored code fingerprint mismatch")
    if args.supplement:
        expected = {r["source_path"]: r for r in inventory["files"]}
        with tarfile.open(args.supplement, "r:gz") as archive:
            members = archive.getmembers()
            if len(members) != len(expected) or {m.name for m in members} != set(expected):
                raise ValueError("supplement members differ from inventory")
            for member in members:
                target = dest / member.name
                if not member.isfile() or not target.resolve().is_relative_to(dest) or target.exists():
                    raise ValueError("unsafe or conflicting supplement member")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                record = expected[member.name]
                if target.stat().st_size != record["size"] or digest(target) != record["sha256"]:
                    raise ValueError("restored research material fingerprint mismatch")
    print(json.dumps({"restored": str(dest), "supplement": bool(args.supplement),
                      "qualification": "exact saved snapshot only; source licenses/current authority not requalified"}))


if __name__ == "__main__":
    main()
