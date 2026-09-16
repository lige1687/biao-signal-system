#!/usr/bin/env python3
"""Lock executor attempt-01 before independent numeric generation."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent / "execution"
ATTEMPT = EXEC / "attempt-01"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = [EXEC / "run_full_accounts.py", EXEC / "code-lock.json", EXEC / "config.json", EXEC / "source-lock.json"]
files += sorted(p for p in ATTEMPT.rglob("*") if p.is_file())
if len(files) != 39:
    raise SystemExit(f"expected 39 executor files including runner locks, got {len(files)}")
payload = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "locked_before_independent_real_calculation",
    "executor_attempt": str(ATTEMPT.resolve()),
    "files": {str(p.resolve()): sha(p) for p in files},
}
(HERE / "executor-attempt-01-lock.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"locked {len(files)} executor files")
