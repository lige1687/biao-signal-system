"""Read-only financial versions, preserving publication precision and raw evidence.

This complements the existing annual source panel, price snapshot reader and
exact-instant selector:
financial periods, metrics and date-only publications cannot be treated as daily
price rows or fabricated midnight availability. No fetching, caching or trading.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def _instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return result


def _interval(value, zone):
    """An uncertainty interval, NOT an imputed publication timestamp."""
    if value is None:
        return None
    if len(value) == 10:
        day = date.fromisoformat(value)
        if day.isoformat() != value:
            raise ValueError("invalid publication date")
        return (datetime.combine(day, time.min, zone),
                datetime.combine(day, time.max, zone))
    point = _instant(value)
    return point, point


def load_bundle(path):
    path = Path(path).resolve()
    bundle = json.loads(path.read_text())
    if bundle.get("schema") != "financial-source-versions/1":
        raise ValueError("unsupported financial versions schema")
    zone = ZoneInfo(bundle["publication_timezone"])
    records = bundle["records"]
    if not isinstance(records, list) or not records:
        raise ValueError("empty records")
    verified, ids, units = {}, set(), {}
    for row in records:
        for field in ("code", "metric", "period_end", "unit", "version", "value"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"missing field: {field}")
        if date.fromisoformat(row["period_end"]).isoformat() != row["period_end"]:
            raise ValueError("invalid financial period")
        try:
            if not Decimal(row["value"]).is_finite():
                raise ValueError("nonfinite amount")
        except InvalidOperation as exc:
            raise ValueError("invalid amount") from exc
        key = row["code"], row["metric"], row["period_end"]
        if units.setdefault(key, row["unit"]) != row["unit"]:
            raise ValueError("unit changed within financial series")
        identity = (*key, row["version"])
        if identity in ids:
            raise ValueError("duplicate version")
        ids.add(identity)
        public = _interval(row.get("published_at"), zone)
        vendor = _interval(row.get("vendor_available_at"), zone)
        retrieved = _instant(row["retrieved_at"])
        if public is not None and public[0] > retrieved:
            raise ValueError("retrieval precedes public release")
        if vendor is not None and (vendor[0] > retrieved or
                                   public is not None and vendor[1] < public[0]):
            raise ValueError("contradictory vendor availability")
        source = row["source"]
        source_path = Path(source["path"])
        if not source_path.is_absolute():
            source_path = path.parent / source_path
        source_path = source_path.resolve()
        if source_path not in verified:
            verified[source_path] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if verified[source_path] != source["sha256"]:
            raise ValueError("source SHA-256 mismatch")
        if not source.get("locator"):
            raise ValueError("source page or locator missing")
    return bundle


def select_versions(bundle, decision_at, *, availability_basis="public"):
    """Select the latest definitely available version of each exact period/metric.

    Releases exactly at the decision instant are conservatively not available.
    A date-only release on that day remains uncertain. For a vendor-path study,
    BOTH public release and vendor arrival must precede the decision.
    """
    if availability_basis not in ("public", "vendor"):
        raise ValueError("availability_basis must be public or vendor")
    cutoff = _instant(decision_at)
    zone = ZoneInfo(bundle["publication_timezone"])
    groups = {}
    for row in bundle["records"]:
        key = row["code"], row["metric"], row["period_end"]
        groups.setdefault(key, []).append(row)
    selected, unresolved, excluded, missing = [], [], [], []
    for key, rows in sorted(groups.items()):
        eligible, unknown = [], []
        for row in rows:
            public = _interval(row.get("published_at"), zone)
            intervals = [public]
            if availability_basis == "vendor":
                intervals.append(_interval(row.get("vendor_available_at"), zone))
            # A future public release is unavailable regardless of vendor metadata.
            if any(item is not None and item[0] >= cutoff for item in intervals):
                excluded.append({"key": key, "version": row["version"], "reason": "not_before_decision"})
                continue
            if any(item is None or item[1] >= cutoff for item in intervals):
                unknown.append(row["version"])
                continue
            # Publication order defines which financial version supersedes which.
            eligible.append((public, row))
        if unknown:
            unresolved.append({"key": key, "reason": "availability_unknown",
                               "versions": unknown})
            continue
        if not eligible:
            excluded.append({"key": key, "reason": "no_available_version"})
            missing.append(key)
            continue
        eligible.sort(key=lambda item: item[0][0])
        latest_interval, latest = eligible[-1]
        # Overlapping publication windows cannot establish a unique latest version.
        if any(interval[1] >= latest_interval[0] for interval, _ in eligible[:-1]):
            unresolved.append({"key": key, "reason": "version_order_ambiguous"})
            continue
        selected.append(latest)
    return {"schema": "financial-version-selection/1", "decision_at": decision_at,
            "availability_basis": availability_basis, "selected": selected,
            "unresolved": unresolved, "excluded": excluded, "missing_series": missing,
            "qualified_for_declared_time_basis": bool(selected) and not unresolved and not missing,
            "limitations": ["Only the supplied versions and declared fields are checked.",
                            "Date-only release times are never imputed.",
                            "Withdrawal, cancellation and complete supersession chains are not checked.",
                            "No relative-period selection or issuer authenticity qualification.",
                            "This is not full-market historical data qualification."],
            "execution_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--decision-at", required=True)
    parser.add_argument("--availability-basis", choices=("public", "vendor"), default="public")
    args = parser.parse_args()
    result = select_versions(load_bundle(args.bundle), args.decision_at,
                             availability_basis=args.availability_basis)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["qualified_for_declared_time_basis"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
