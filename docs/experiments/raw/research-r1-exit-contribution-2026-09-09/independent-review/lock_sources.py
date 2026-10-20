#!/usr/bin/env python3
"""Freeze independent-review protocol, code and referenced old inputs."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TECH = ROOT.parent / "research-broad-etf-technical-2026-09-08" / "execution"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = [
    ROOT / "protocol.md",
    ROOT / "protocol-lock.json",
    HERE / "review-protocol.md",
    HERE / "independent_check.py",
    TECH / "inputs/execution-config.json",
    TECH / "inputs/actions.json",
    TECH / "inputs/dated-restrictions.json",
    TECH / "inputs/price-limit-regimes.json",
    TECH / "inputs/exit-observations.json.gz",
    TECH / "inputs/source-candidates/diagnostic-candidates.json",
    TECH / "inputs/bars/sh510300-nominal.csv",
    TECH / "inputs/bars/sz159915-nominal.csv",
]
for symbol in ("sh510300", "sz159915"):
    for tag in ("10", "20"):
        base = TECH / f"account-results/{symbol}-R1-fee{tag}bp"
        files.extend(base / name for name in ("daily.csv", "trades.csv", "orders.json", "events.json", "roundtrips.json"))

missing = [str(p) for p in files if not p.is_file()]
if missing:
    raise SystemExit("missing locked sources:\n" + "\n".join(missing))
out = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "before_new_results",
    "new_result_path": None,
    "real_account_calculation_run": False,
    "files": {str(p.resolve()): sha(p) for p in files},
}
(HERE / "review-lock.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"locked {len(files)} files")
