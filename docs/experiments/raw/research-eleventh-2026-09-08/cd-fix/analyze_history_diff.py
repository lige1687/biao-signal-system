"""Read-only C/D comparison between the tenth and eleventh raw event archives."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
ELEVENTH = HERE.parent
TENTH = HERE.parents[1] / "research-tenth-2026-09-08"
OLD_RAW = TENTH / "history-diagnostic" / "raw-events.json.gz"
NEW_RAW = ELEVENTH / "history-diagnostic" / "raw-events.json.gz"
DIAGNOSE = ELEVENTH / "diagnose_history.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


source_hashes = {str(path): sha256(path) for path in (OLD_RAW, NEW_RAW, DIAGNOSE)}
spec = importlib.util.spec_from_file_location("eleventh_diagnose_history_readonly", DIAGNOSE)
assert spec and spec.loader
diagnose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnose)  # imports helpers; __name__ != '__main__', so main is not run

from lei_signal.features.indicators import compute_features  # noqa: E402
from lei_signal.features.pivots import confirmed_pivots, swing_lows  # noqa: E402
from lei_signal.domain.rules_config import get_rule  # noqa: E402
from lei_signal.rules import module_d_false_breakout as module_d  # noqa: E402
from lei_signal.rules.clock_classifier import TYPE3_SIDEWAYS, clock_series  # noqa: E402
from lei_signal.rules.dense_breakout import _bandwidth_condition, _state_age_series  # noqa: E402


def load(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as handle:
        return json.load(handle)


def key(record: dict) -> tuple[str, str, str, str]:
    return (
        record["module"],
        record["basis_epoch_start"],
        record["basis_epoch_end"],
        record["event"]["event_id"],
    )


def confirmed(record: dict) -> bool:
    return "confirmed" in record["event"]["evidence"].get("sub_rule", "")


old = {key(record): record for record in load(OLD_RAW) if record["module"] in {"C", "D"}}
new = {key(record): record for record in load(NEW_RAW) if record["module"] in {"C", "D"}}
assert len(old) == len(set(old)) and len(new) == len(set(new))

comparison: dict[str, dict] = {}
for module in ("C", "D"):
    old_keys = {item for item in old if item[0] == module}
    new_keys = {item for item in new if item[0] == module}
    common = old_keys & new_keys
    removed = old_keys - new_keys
    added = new_keys - old_keys
    changed = {item for item in common if old[item]["event"] != new[item]["event"]}
    comparison[module] = {
        "old": len(old_keys),
        "new": len(new_keys),
        "removed": len(removed),
        "added": len(added),
        "common": len(common),
        "common_field_changes": len(changed),
        "old_confirmed": sum(confirmed(old[item]) for item in old_keys),
        "new_confirmed": sum(confirmed(new[item]) for item in new_keys),
        "removed_confirmed": sum(confirmed(old[item]) for item in removed),
        "added_confirmed": sum(confirmed(new[item]) for item in added),
        "added_event_ids": sorted(item[3] for item in added),
    }

bars, actions = diagnose.load_inputs()


def audit_removed(record: dict) -> dict:
    event = record["event"]
    evidence = event["evidence"]
    raw = diagnose.raw_asof(event["symbol"], bars, actions, record["basis_epoch_end"])
    lows = swing_lows(confirmed_pivots(raw))
    reference_date = pd.Timestamp(event["lifecycle_id"].rsplit(":", 1)[-1]).date()
    breakdown_date = pd.Timestamp(evidence["breakdown_date"]).date()
    reference_price = float(evidence.get("l1_price", evidence.get("valley_price")))
    newer = [
        pivot for pivot in lows
        if reference_date < pivot.available_date < breakdown_date
    ]
    return {
        "module": record["module"],
        "event_id": event["event_id"],
        "symbol": event["symbol"],
        "available_date": event["available_date"],
        "sub_rule": evidence["sub_rule"],
        "reference_confirmed_date": reference_date.isoformat(),
        "reference_price": reference_price,
        "breakdown_date": breakdown_date.isoformat(),
        "newer_confirmed_lows_before_breakdown": [
            {
                "confirmed_date": pivot.available_date.isoformat(),
                "pivot_date": str(raw.index[pivot.index].date()),
                "price": float(pivot.price),
            }
            for pivot in newer
        ],
        "verified_stale_reference": bool(newer),
    }


removed_confirmed = sorted(
    (old[item] for item in old.keys() - new.keys() if confirmed(old[item])),
    key=lambda record: (record["event"]["available_date"], record["event"]["event_id"]),
)
assert len(removed_confirmed) >= 3
sample_positions = sorted({0, len(removed_confirmed) // 2, len(removed_confirmed) - 1})
samples = [audit_removed(removed_confirmed[position]) for position in sample_positions]
assert len(samples) == 3 and all(sample["verified_stale_reference"] for sample in samples)


def legacy_zone_intervals(frame: pd.DataFrame, threshold: float, minimum: int, exit_bars: int):
    active = (
        (clock_series(frame) == TYPE3_SIDEWAYS)
        & _bandwidth_condition(frame, threshold)
        & (_state_age_series(clock_series(frame) == TYPE3_SIDEWAYS, exit_bars=exit_bars) >= minimum)
    ).to_numpy()
    intervals, start, loose = [], None, 0
    for position, flag in enumerate(active):
        if flag:
            if start is None:
                start = position
            loose = 0
        elif start is not None:
            loose += 1
            if loose > exit_bars:
                intervals.append((start, position - loose + 1))
                start, loose = None, 0
    if start is not None:
        intervals.append((start, len(frame)))
    return intervals


d_added_explanations = []
for item in sorted(new.keys() - old.keys()):
    if item[0] != "D":
        continue
    record = new[item]
    event = record["event"]
    raw = diagnose.raw_asof(event["symbol"], bars, actions, record["basis_epoch_end"])
    frame = compute_features(raw)
    _, threshold, minimum, exit_bars = module_d._params(get_rule(module_d.RULE_ID))
    position_by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    reference_date = pd.Timestamp(event["lifecycle_id"].rsplit(":", 1)[-1]).date()
    reference_position = position_by_day[reference_date]
    old_intervals = legacy_zone_intervals(frame, threshold, minimum, exit_bars)
    new_intervals = module_d._zone_intervals(frame, threshold, minimum, exit_bars)
    old_contains = any(start <= reference_position < end for start, end in old_intervals)
    new_contains = any(start <= reference_position < end for start, end in new_intervals)
    d_added_explanations.append({
        "event_id": event["event_id"],
        "available_date": event["available_date"],
        "sub_rule": event["evidence"]["sub_rule"],
        "reference_confirmed_date": reference_date.isoformat(),
        "legacy_zone_contains_reference": old_contains,
        "repaired_zone_contains_reference": new_contains,
        "zone_end_fix_directly_explains_addition": (not old_contains and new_contains),
    })

result = {
    "scope": "read-only raw-event comparison; no returns; counts are events, not independent opportunities",
    "key": ["module", "basis_epoch_start", "basis_epoch_end", "event_id"],
    "comparison": comparison,
    "removed_confirmed_fixed_samples": samples,
    "d_added_explanations": d_added_explanations,
    "diagnose_import": {
        "path": str(Path(diagnose.__file__).resolve()),
        "main_executed": False,
        "functions_used": ["load_inputs", "raw_asof"],
    },
    "source_hashes": source_hashes,
}
assert all(sha256(Path(path)) == digest for path, digest in source_hashes.items())
(HERE / "history-diff-explanation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps({"comparison": comparison, "samples": len(samples), "d_added": d_added_explanations}, ensure_ascii=False))
