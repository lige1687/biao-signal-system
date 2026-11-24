"""Replay saved receipts into a separate audit database, never the live ledger.

This is a deterministic software reconciliation of what was known then. It is
not new forward evidence or an independent test of profitability.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .models import digest
from .service import initialize, process_observation

TABLES = ("run", "observations", "events", "orders", "fills", "actions", "valuations")


def replay_saved(db_path: Path, config: dict, output_root: Path) -> dict:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        source.execute("BEGIN")
        saved = {
            table: [dict(r) for r in source.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in TABLES
        }
    if not saved["run"]:
        raise ValueError("no initialized ledger to replay")
    spec = json.loads(saved["run"][0]["spec"])
    if digest(config) != spec["config_hash"]:
        raise ValueError("replay requires the exact original frozen configuration")
    output = output_root / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    target = output / "replay.db"
    initialize(target, config, spec["frozen_at"])
    source_events = {r["observation_id"]: r for r in saved["events"] if r["kind"] == "source"}
    for row in saved["observations"]:
        event = source_events[row["id"]]
        process_observation(target, json.loads(row["payload"]), event["at"])
    with sqlite3.connect(target) as replay:
        replay.row_factory = sqlite3.Row
        actual = {
            table: [dict(r) for r in replay.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in TABLES
        }
    checks = {table: saved[table] == actual[table] for table in TABLES}
    receipt = {
        "mode": "saved_receipt_replay_not_new_forward_evidence",
        "checked_at": datetime.now(UTC).isoformat(),
        "passed": all(checks.values()),
        "tables": checks,
        "source_counts": {k: len(v) for k, v in saved.items()},
        "source_digest": digest(saved),
        "replay_digest": digest(actual),
        "replay_path": str(target),
    }
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            replay_saved(args.db, json.loads(args.config.read_text()), args.output_root),
            ensure_ascii=False,
            indent=2,
        )
    )
