"""Verify delivered bytes without granting research or trading permission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def verify(root: Path, require_full_research: bool = False) -> dict:
    root = root.resolve()
    bundle = Path(__file__).resolve().parent.parent
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    checked = 0
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.resolve().is_relative_to(root):
            errors.append({"path": item["path"], "reason": "outside root"})
            continue
        if not path.is_file():
            errors.append({"path": item["path"], "reason": "missing"})
            continue
        content = path.read_bytes()
        if len(content) != item["bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            errors.append({"path": item["path"], "reason": "size or SHA256 differs"})
        checked += 1
    checksum_count = 0
    for line in (bundle / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.resolve().is_relative_to(root) or not path.is_file():
            errors.append({"path": relative, "reason": "checksum file missing or outside root"})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append({"path": relative, "reason": "SHA256SUMS differs"})
        checksum_count += 1
    cp = subprocess.run(["git", "merge-base", "--is-ancestor", manifest["repository"]["content_baseline_commit"], "HEAD"], cwd=root, capture_output=True)
    if cp.returncode != 0:
        errors.append({"path": ".git", "reason": "HEAD is not a descendant of the declared baseline"})
    definition_path = root / "docs/research/definitions.v1.json"
    if definition_path.is_file():
        registry = json.loads(definition_path.read_text(encoding="utf-8"))
    else:
        registry = {"objects": []}
        errors.append({"path": "docs/research/definitions.v1.json", "reason": "registry missing; full research not permitted"})
    missing = [{"object": obj["id"] + "@" + obj["version"], "path": basis}
               for obj in registry["objects"]
               for basis in (obj.get("lifecycle") or {}).get("basis", [])
               if not (root / basis).is_file()]
    qualification_gaps = [item["id"] for item in manifest["gaps"] if item.get("blocks_full_research")]
    if missing and "definition-evidence-closure" not in qualification_gaps:
        qualification_gaps.append("definition-evidence-closure")
    exit_code = 1 if errors else 2 if require_full_research and qualification_gaps else 0
    return {"integrity": "failed" if errors else "passed", "checked_files": checked,
            "checksum_entries": checksum_count, "errors": errors,
            "current_missing_definition_references": len(missing),
            "qualification": "blocked" if qualification_gaps else "not_assessed",
            "qualification_gaps": qualification_gaps,
            "allowed_next_action": "resolve gaps; read-only minimum checks only",
            "full_research_or_production_approved": False, "exit_code": exit_code}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--require-full-research", action="store_true")
    args = parser.parse_args()
    result = verify(args.root, args.require_full_research)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(result["exit_code"])
