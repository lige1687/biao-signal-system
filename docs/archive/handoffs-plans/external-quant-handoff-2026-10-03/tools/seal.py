"""Seal relative-path inventories; self-reference excluded explicitly."""
from pathlib import Path
import hashlib
import json

p = Path(__file__).resolve().parents[1]
snapshot = json.loads((p / "evidence/source-snapshot.json").read_text())
records = []
for f in sorted(p.rglob("*")):
    if not f.is_file() or f in (p / "manifest.json", p / "SHA256SUMS") or "__pycache__" in f.parts:
        continue
    if f.is_symlink():
        raise ValueError("symlinks are not portable")
    records.append({"path": str(f.relative_to(p)), "size": f.stat().st_size,
                    "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
manifest = {"schema_version": "lei-task-handoff/1.0", "task": "external-quant-resources",
            "captured_at": snapshot["captured_at"], "repository": "https://github.com/lige1687/biao-signal-system",
            "source_branch": snapshot["branch"], "source_HEAD": snapshot["head"],
            "handoff_branch": "codex/handoff-external-quant-20261003",
            "delivered_commit": "resolve with git log -1 -- this handoff directory; no self-commit loop",
            "self_reference_policy": "manifest excludes itself and SHA256SUMS; SHA256SUMS includes manifest and excludes itself",
            "files": records}
(p / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
records.append({"path": "manifest.json", "sha256": hashlib.sha256((p / "manifest.json").read_bytes()).hexdigest()})
(p / "SHA256SUMS").write_text("".join(r["sha256"] + "  " + r["path"] + "\n" for r in records))
print(json.dumps({"files": len(records), "bytes": sum(r.get("size", 0) for r in records)}))
