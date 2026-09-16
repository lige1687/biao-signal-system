#!/usr/bin/env python3
"""Lock accepted fixed-entry attempt 02 before cross-comparison."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXED = HERE.parent / "fixed-entries"
ATTEMPT = FIXED / "attempt-02"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


files = [FIXED / "run_fixed_entries.py", FIXED / "run-lock.json", FIXED / "run-lock-attempt-02.json", FIXED / "config.json", FIXED / "code-attempt-02.diff"]
files += sorted(p for p in ATTEMPT.rglob("*") if p.is_file())
if not all(p.is_file() for p in files):
    raise SystemExit("missing fixed-entry lock target")
payload = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "locked_before_fixed_entry_cross_comparison",
    "accepted_attempt": str(ATTEMPT.resolve()),
    "files": {str(p.resolve()): sha(p) for p in files},
}
(HERE / "fixed-attempt-02-lock.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"locked {len(files)} fixed-entry files")
