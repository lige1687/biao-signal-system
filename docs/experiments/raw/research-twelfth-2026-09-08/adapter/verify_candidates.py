"""Independent all-field verification of every adapted A/C/D candidate."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("twelfth_candidate_builder", HERE / "build_candidates.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def main() -> None:
    inputs = builder.source_files() + [
        HERE / "candidates.json.gz", HERE / "run-lock.json", HERE / "completion.json",
        HERE / "summary.json", Path(__file__).resolve(),
    ]
    hashes = {str(path.resolve()): digest(path.resolve()) for path in sorted(set(inputs))}
    save(HERE / "candidate-review-lock.json", {
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "files": hashes,
        "scope": "all 891 adapted candidates; full-field comparison on exact-day and epoch-prefix inputs",
    })
    with gzip.open(builder.RAW_EVENTS, "rt") as handle:
        events = json.load(handle)
    with gzip.open(HERE / "candidates.json.gz", "rt") as handle:
        candidates = json.load(handle)
    expected = {c["source_candidate_id"]: c for c in candidates
                if c["config_id"] not in {"REF_BREAKOUT", "REF_ROAD"}}
    confirmed = [record for record in events if builder.config_for(record) is not None]
    bars, actions = builder.load_inputs()
    epoch_cache = {}
    checked = []
    for index, record in enumerate(confirmed, 1):
        event = record["event"]
        symbol, day, event_id = event["symbol"], event["available_date"], event["event_id"]
        key = (symbol, record["basis_epoch_end"])
        if key not in epoch_cache:
            epoch_cache[key] = builder.raw_asof(symbol, bars, actions, record["basis_epoch_end"])
        epoch_prefix = epoch_cache[key].loc[:day].copy()
        exact_day = builder.raw_asof(symbol, bars, actions, day)
        generated_from_epoch = builder.adapt_event(record, epoch_prefix)
        generated_from_exact = builder.adapt_event(record, exact_day)
        stored = expected[event_id]
        assert generated_from_epoch == generated_from_exact == stored, (event_id, "full_candidate_mismatch")
        checked.append({"source_event_id": event_id, "config_id": stored["config_id"],
                        "symbol": symbol, "signal_date": day, "all_fields_matched": True})
        if index % 100 == 0:
            print(f"reviewed {index}/{len(confirmed)}", flush=True)
    assert len(checked) == len(expected) == 891
    assert len({row["source_event_id"] for row in checked}) == 891
    with gzip.open(HERE / "candidate-field-checks.json.gz", "wt") as handle:
        json.dump(checked, handle, ensure_ascii=False, allow_nan=False)
    save(HERE / "candidate-review-summary.json", {
        "status": "passed", "candidates_checked": len(checked), "all_fields_matched": len(checked),
        "mismatches": 0, "unique_source_events": len({row["source_event_id"] for row in checked}),
        "comparison": "stored candidate == exact-day recomputation == epoch-frame truncated to signal day recomputation",
    })
    assert all(digest(Path(path)) == value for path, value in hashes.items())
    save(HERE / "candidate-review-completion.json", {
        "finished_at_utc": datetime.now(timezone.utc).isoformat(), "input_hashes": hashes,
        "input_hashes_unchanged": True, "checks_sha256": digest(HERE / "candidate-field-checks.json.gz"),
        "summary_sha256": digest(HERE / "candidate-review-summary.json"),
    })
    print("all-field candidate review passed", flush=True)


if __name__ == "__main__":
    main()
