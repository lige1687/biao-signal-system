"""Read-only identity qualification for the six frozen D/MAE originals.

This stage does not calculate new features, benchmark V, or outcome Y.  The
private validator is split from the fixed-path reader for mutation tests;
callers cannot supply replacement production paths or expected digests.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import plistlib
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

FEATURE_ID = "local_contract.opportunity.invalidation_distance"
VARIANT_ID = "module_a_event_c_touch_min__signal_close__runtime_tr_sma20"
UNKNOWN_CASE_ID = "case:ded0d0c43677a76957f4"
EXTERNAL_MOUNT = Path("/Volumes/win+mac通用")
EXTERNAL_UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"
EXTERNAL_DEVICE = 16777238
ORIGINAL_ROOT = EXTERNAL_MOUNT / (
    "LeiSignal-新实验结果/research-dispatch-controller/"
    "research-dispatch-controller-20261009T113744-76e813edcc31/result/originals"
)
PROJECT_ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RECOVERY_MANIFEST = PROJECT_ROOT / (
    "docs/experiments/raw/research-dispatch-controller-2026-10-07/"
    "original-recovery-20261009/recovery-manifest.json"
)
WINDOW_METADATA = PROJECT_ROOT / (
    "docs/experiments/raw/native-risk-d-mae-2026-10-07/immutable-handoff/METADATA-ONLY-SUPPORT.json"
)
WINDOW_METADATA_SHA256 = "e985cdca6b03dd5a0f646f6553b07cb2d11e071807ce6dd4e680901ed52b6ceb"
ORIGINALS = {
    "deduplicated-cases.json": (
        "information_test/six_etf_support/deduplicated-cases.json",
        "7540cbe16abec5e6c5dbe9569ab0879d2160d2f4a86c640556f3550aba633bb7",
    ),
    "label-protocol.json": (
        "information_test/six_etf_support/label-protocol.json",
        "64168b19fdca54768e8d4af5589be6df764b007dec81b620404b07b6317dd3c1",
    ),
    "native-early-events.json": (
        "native_generation_resume_v1/run02/published/native-early-events.json",
        "f12dec8224bb33efd7541f1a6be298e6d7e02fe5797d16c7d4b00ef9b5f2bef3",
    ),
    "x-panel-long.json": (
        "native_generation_resume_v1/run02/published/x-panel-long.json",
        "1693b33c4d6ea947920304ae17843a6d507c7095bff068165deb2c744d7b8895",
    ),
    "validated-input-binding.json": (
        "native_generation_resume_v1/deliverable/contracts/validated-input-binding.json",
        "28beb9c4a5ec869de72d5e1c7df8271868be02cbd51ab0026537cc3414562d91",
    ),
    "feature-contract.json": (
        "native_generation_resume_v1/deliverable/contracts/feature-contract.json",
        "c88785ee47baedc37d77f54a789df1e84e930c0c47b4f0f7760ebc3f7df6c8c6",
    ),
}


class IdentityError(ValueError):
    """A frozen input is absent, changed, ambiguous, or internally inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IdentityError(message)


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise IdentityError(f"nonfinite JSON constant: {value}")


def _strict_json(raw: bytes, name: str) -> Any:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs_unique, parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise IdentityError(f"invalid JSON in {name}: {exc}") from exc

    def check(node: Any) -> None:
        if isinstance(node, float):
            _require(math.isfinite(node), f"nonfinite number in {name}")
        elif isinstance(node, dict):
            for child in node.values():
                check(child)
        elif isinstance(node, list):
            for child in node:
                check(child)

    check(value)
    return value


def _read_exact(path: Path, expected_sha: str, name: str) -> Any:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    _require(actual == expected_sha, f"SHA256 mismatch for {name}: {actual}")
    return _strict_json(raw, name)


def _no_symlink_components(path: Path) -> None:
    _require(path.is_absolute() and ".." not in path.parts, f"unsafe path: {path}")
    for parent in (path, *path.parents):
        if parent == Path("/"):
            break
        _require(not parent.is_symlink(), f"unexpected symlink: {parent}")


def _verify_external() -> None:
    _no_symlink_components(EXTERNAL_MOUNT)
    _require(EXTERNAL_MOUNT.is_mount(), f"external mount missing: {EXTERNAL_MOUNT}")
    try:
        result = subprocess.run(
            ["diskutil", "info", "-plist", str(EXTERNAL_MOUNT)],
            capture_output=True,
            check=True,
            timeout=10,
        )
        info = plistlib.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise IdentityError(f"cannot verify external volume UUID: {exc}") from exc
    _require(info.get("VolumeUUID") == EXTERNAL_UUID, "external volume UUID mismatch")
    _require(os.stat(EXTERNAL_MOUNT).st_dev == EXTERNAL_DEVICE, "external device mismatch")
    _require(os.stat(ORIGINAL_ROOT).st_dev == EXTERNAL_DEVICE, "original root device mismatch")


def load_original_identity() -> dict[str, Any]:
    """Verify fixed original bytes and return a full identity audit, without X/V/Y work."""
    _verify_external()
    _no_symlink_components(RECOVERY_MANIFEST)
    _no_symlink_components(WINDOW_METADATA)
    manifest = _strict_json(RECOVERY_MANIFEST.read_bytes(), "recovery-manifest.json")
    _require(
        isinstance(manifest, dict) and len(manifest.get("files", [])) == 6,
        "recovery manifest must name exactly six files",
    )
    manifest_entries = {Path(entry["path"]).name: entry for entry in manifest["files"]}
    _require(set(manifest_entries) == set(ORIGINALS), "recovery manifest file names mismatch")
    verified: dict[str, Any] = {}
    for name, (relative, sha) in ORIGINALS.items():
        path = ORIGINAL_ROOT / relative
        entry = manifest_entries[name]
        _require(
            entry["path"] == str(path)
            and entry["sha256"] == sha
            and entry["expected_sha256"] == sha
            and entry["status"] == "exact_match",
            f"recovery manifest mismatch: {name}",
        )
        _no_symlink_components(path)
        _require(
            path.is_file() and os.stat(path).st_dev == EXTERNAL_DEVICE,
            f"original missing or wrong device: {name}",
        )
        raw = path.read_bytes()
        _require(len(raw) == entry["bytes"], f"original size mismatch: {name}")
        _require(hashlib.sha256(raw).hexdigest() == sha, f"SHA256 mismatch: {name}")
        verified[name] = _strict_json(raw, name)
    metadata = _read_exact(WINDOW_METADATA, WINDOW_METADATA_SHA256, WINDOW_METADATA.name)
    return _validate_identity(verified, metadata)


def _unique_index(
    rows: Any, key: str, expected_count: int, label: str
) -> dict[str, dict[str, Any]]:
    _require(
        isinstance(rows, list) and len(rows) == expected_count,
        f"{label}: expected {expected_count} rows",
    )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict) and isinstance(row.get(key), str), f"{label}: invalid {key}")
        identity = row[key]
        _require(identity not in result, f"{label}: duplicate {key} {identity}")
        result[identity] = row
    return result


def _finite_positive(value: Any, label: str) -> None:
    _require(
        type(value) in (float, int) and math.isfinite(value) and value > 0,
        f"{label}: expected positive finite number",
    )


def _validate_identity(docs: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Compare already verified documents. Private so no caller can override real digests."""
    cases = _unique_index(docs["deduplicated-cases.json"], "case_id", 76, "cases")
    events = _unique_index(docs["native-early-events.json"], "event_id", 84, "events")
    rows = docs["x-panel-long.json"]
    _require(isinstance(rows, list) and len(rows) == 336, "expected 336 long rows")
    binding = docs["validated-input-binding.json"]
    contract = docs["feature-contract.json"]
    protocol = docs["label-protocol.json"]
    _require(protocol["price_cutoff"] == "2026-06-26", "price cutoff mismatch")
    _require(
        metadata["case_sha256"] == ORIGINALS["deduplicated-cases.json"][1]
        and metadata["calendar_sha256"] == binding["calendar_sha256"],
        "window metadata source mismatch",
    )
    _require(
        metadata["exact_cases"] == 76
        and metadata["native_events"] == 84
        and metadata["asset_lifecycle_groups"] == 33
        and metadata["calendar_mature_count"] == 75
        and metadata["new_X_values_computed"] == 0
        and metadata["new_Y_values_computed"] == 0,
        "window metadata counts mismatch",
    )
    features = [f for f in contract["features"] if f.get("feature_id") == FEATURE_ID]
    _require(
        len(features) == 1
        and features[0]["variant_id"] == VARIANT_ID
        and features[0]["atr_definition"]["method"] == "simple_average",
        "frozen D definition or ATR method mismatch",
    )
    expected_sources = [
        binding["bars_sha256"],
        binding["calendar_sha256"],
        ORIGINALS["validated-input-binding.json"][1],
    ]
    _require(
        contract["contract_id"] and len(contract["features"]) == 4,
        "feature contract identity mismatch",
    )
    long_index: dict[tuple[str, str], dict[str, Any]] = {}
    feature_variants = {f["feature_id"]: f["variant_id"] for f in contract["features"]}
    for row in rows:
        eid, fid = row["signal_event_id"], row["feature_id"]
        key = eid, fid
        _require(
            eid in events and fid in feature_variants and key not in long_index,
            f"long row missing/duplicate identity: {key}",
        )
        _require(
            row["variant_id"] == feature_variants[fid]
            and row["contract_sha256"] == ORIGINALS["feature-contract.json"][1]
            and row["contract_id"] == contract["contract_id"]
            and row["source_sha256"] == expected_sources,
            f"long row binding mismatch: {key}",
        )
        event = events[eid]
        _require(
            row["asset_id"] == event["symbol"]
            and row["asof_session_date"] == event["event_date"]
            and row["entry_variant"] == event["evidence"]["entry_variant"]
            and row["price_basis_id"]
            == binding["price_basis_by_asset"][event["symbol"]]["price_basis_id"],
            f"long row event or price basis mismatch: {key}",
        )
        long_index[key] = row
    _require(len(long_index) == 336, "long rows incomplete")

    windows = _unique_index(metadata["all_window_metadata"], "case_id", 76, "all_window_metadata")
    _require(set(windows) == set(cases), "window case identities mismatch")
    membership: dict[str, str] = {}
    audit_cases: list[dict[str, Any]] = []
    groups: set[tuple[str, str]] = set()
    asset_dates: set[tuple[str, str]] = set()
    for cid, case in cases.items():
        asset, date = case["asset"], case["date"]
        _require((asset, date) not in asset_dates, f"repeated asset/date case: {asset}/{date}")
        asset_dates.add((asset, date))
        aliases = case["member_event_ids"]
        periods = case["member_ma_periods"]
        _require(
            isinstance(aliases, list)
            and 1 <= len(aliases) <= 2
            and len(aliases) == len(set(aliases))
            and isinstance(periods, list)
            and len(periods) == len(aliases)
            and case["event_id"] == aliases[0],
            f"case alias identity mismatch: {cid}",
        )
        _require(
            case["price_basis_id"] == binding["price_basis_by_asset"][asset]["price_basis_id"]
            and case["source_sha256"] == expected_sources
            and case["calendar_id"] == rows[0]["calendar_id"],
            f"case source or price basis mismatch: {cid}",
        )
        for name in ("A", "C", "ATR", "D"):
            _finite_positive(case[name], f"{cid}.{name}")
        _require(case["A"] > case["C"], f"case A/C order invalid: {cid}")
        event_periods = []
        event_ma: dict[str, int] = {}
        for eid in aliases:
            _require(
                eid in events and eid not in membership, f"missing/reused event alias: {cid}/{eid}"
            )
            membership[eid] = cid
            event = events[eid]
            evidence = event["evidence"]
            ma = evidence["ma_period"]
            event_periods.append(ma)
            event_ma[eid] = ma
            _require(
                event["symbol"] == asset
                and event["event_date"] == date
                and event["available_date"] == date
                and event["lifecycle_id"] == case["lifecycle"]
                and evidence["touch_date"] == case["touch_date"]
                and evidence["a3_source"] == case["a3_source"]
                and evidence["a3_structure_id"] == case["a3_structure_id"]
                and evidence["entry_ref_close"] == case["A"]
                and evidence["stop_price"] == case["C"]
                and evidence["atr20"] == case["ATR"],
                f"case/event value or identity mismatch: {cid}/{eid}",
            )
            row = long_index[eid, FEATURE_ID]
            _require(
                row["value"] == case["D"]
                and row["formula_value"] is None
                and row["quality_status"] == "ok"
                and row["arrival_certification_status"] == "historical_arrival_unknown"
                and row["live_eligible"] is False
                and row["opportunity_group_key"]
                == [asset, case["lifecycle"], ma, case["touch_date"]],
                f"case/D row mismatch: {cid}/{eid}",
            )
        _require(
            Counter(event_periods) == Counter(periods) and event_ma[case["event_id"]] == case["ma"],
            f"case member MA periods mismatch: {cid}",
        )
        window = windows[cid]
        _require(
            window["asset"] == asset and window["signal_date"] == date,
            f"window case/date mismatch: {cid}",
        )
        groups.add((asset, case["lifecycle"]))
        audit_cases.append(
            {
                "case_id": cid,
                "asset": asset,
                "signal_date": date,
                "lifecycle": case["lifecycle"],
                "touch_date": case["touch_date"],
                "event_ids": aliases,
                "member_ma_periods": periods,
                "event_ma_period": event_ma,
                "A": case["A"],
                "C": case["C"],
                "ATR20_SMA": case["ATR"],
                "D_frozen": case["D"],
                "price_basis_id": case["price_basis_id"],
                "source_sha256": case["source_sha256"],
                "calendar_id": case["calendar_id"],
                "window_metadata": {
                    "label_start": window["label_start"],
                    "label_end": window["label_end"],
                    "calendar_mature_by_20260626": window["calendar_mature_by_20260626"],
                    "reason": window["reason"],
                },
            }
        )
    _require(set(membership) == set(events), "event membership not exhaustive")
    _require(len(groups) == 33, "asset/lifecycle group count mismatch")
    _require(
        len(asset_dates) == metadata["same_asset_signal_date_keys"]
        and metadata["repeated_same_asset_signal_date"] == {},
        "asset/date identity metadata mismatch",
    )
    per_asset = dict(Counter(c["asset"] for c in audit_cases))
    _require(per_asset == metadata["per_asset_case_count"], "per-asset case count mismatch")
    per_asset_mature = dict(
        Counter(
            c["asset"] for c in audit_cases if c["window_metadata"]["calendar_mature_by_20260626"]
        )
    )
    _require(
        per_asset_mature == metadata["per_asset_calendar_mature_count"],
        "per-asset maturity metadata mismatch",
    )
    unknown = [
        c["case_id"] for c in audit_cases if not c["window_metadata"]["calendar_mature_by_20260626"]
    ]
    _require(
        unknown == [UNKNOWN_CASE_ID] and len(audit_cases) - len(unknown) == 75,
        "unknown case identity or maturity mismatch",
    )
    _require(
        metadata["not_date_qualified"] == [windows[UNKNOWN_CASE_ID]],
        "unknown case metadata mismatch",
    )
    return {
        "schema": "native-risk-d-mae-original-identity/1",
        "status": "identity_qualified_only",
        "original_sha256": {name: sha for name, (_, sha) in ORIGINALS.items()},
        "window_metadata_sha256": WINDOW_METADATA_SHA256,
        "feature_id": FEATURE_ID,
        "variant_id": VARIANT_ID,
        "mapping": {
            "date": "signal_date",
            "member_event_ids": "event_ids",
            "ATR": "ATR20_SMA",
            "D": "D_frozen",
        },
        "counts": {
            "cases": 76,
            "events": 84,
            "long_rows": 336,
            "D_rows": 84,
            "asset_lifecycle_groups": 33,
            "calendar_mature": 75,
            "calendar_unknown": 1,
        },
        "per_asset_case_count": per_asset,
        "unknown_case_id": UNKNOWN_CASE_ID,
        "cases": audit_cases,
        "event_to_case": membership,
        "limits": [
            "No new X, V, Y, labels, fits, or future-price reads.",
            "Window dates are from frozen all_window_metadata, not old natural-month labels.",
            "D is a frozen research proxy; source arrival remains unknown.",
        ],
    }
