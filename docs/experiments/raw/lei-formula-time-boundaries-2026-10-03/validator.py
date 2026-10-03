"""Standalone research boundary validator. No LEI imports or external writes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import statistics

BINDING_FILE = Path(__file__).parent / "fixtures/reviewed_binding.json"
BINDING_SHA256 = "f910ae25371050ea723d8058682c770f377269fa10827ebdd424bfaf6a14eccf"


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def reviewed_binding():
    raw = BINDING_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BINDING_SHA256:
        raise ValueError("reviewed binding lock changed; explicit review required")
    return json.loads(raw)


def _differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict):
        out = []
        for key in sorted(set(left) | set(right)):
            p = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                out.append(p)
            else:
                out.extend(_differences(left[key], right[key], p))
        return out
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [path]
        return [p for i, (a, b) in enumerate(zip(left, right))
                for p in _differences(a, b, f"{path}[{i}]")]
    # JSON boolean and numeric parameters have different contract meanings.
    return [] if type(left) is type(right) and left == right else [path]


def validate_formula(candidate):
    """Fail closed on an unreviewed contract or arithmetic description.

    Prose is never executed or automatically translated. The complete resolved
    semantic sections AND transitive dependency contracts are pinned; the typed
    arithmetic description is independently checked. This is one reviewed RV20
    binding, not a proof that arbitrary formula text means the supplied program.
    """
    expected = reviewed_binding()
    if not isinstance(candidate, dict):
        return {"status": "blocked", "reason": "formula_object_required"}
    keys = {"reference", "contract", "dependency_contracts", "semantics"}
    if set(candidate) != keys:
        return {"status": "blocked", "reason": "formula_fields_mismatch"}
    wanted = {k: expected[k] for k in keys}
    differences = _differences(candidate, wanted)
    if differences:
        return {"status": "blocked", "reason": "unreviewed_semantic_contract",
                "changed_fields": differences}
    return {"status": "pass", "reason": "reviewed_contract_and_typed_semantics_match",
            "reference": expected["reference"], "contract_hash": canonical_hash(candidate),
            "scope": "local_binding_only; full_registry_admission_not_certified"}


def rv20_reference(prices):
    """Independent standard-library arithmetic for the reviewed typed contract.

    Last 20 simple returns, including current; sample ddof=1; sqrt(252).
    Explicit NaN/None rows do not consume the quote clock and remain missing.
    Twenty returns require 21 valid prices. No formula eval or price filling.
    """
    quotes, returns, out = [], [], []
    for value in prices:
        if value is None or (isinstance(value, Real) and not isinstance(value, bool)
                             and math.isnan(value)):
            out.append(None)
            continue
        if (not isinstance(value, Real) or isinstance(value, bool)
                or not math.isfinite(value) or value <= 0):
            raise ValueError("price must be finite and positive, or explicit missing")
        value = float(value)
        if quotes:
            returns.append(value / quotes[-1] - 1)
        quotes.append(value)
        out.append(statistics.stdev(returns[-20:]) * math.sqrt(252)
                   if len(returns) >= 20 else None)
    return out


def aware_instant(value):
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("explicit ISO timestamp and timezone required")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError("invalid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("undeclared timezone")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("timestamp exceeds supported UTC range") from exc


def qualify_bar(bar, decision_at):
    """Compare declared actual availability instants, without a market-hour rule.

    A complete declaration is required; this cannot certify source truth. The
    feature must not precede its completed session or any required input. Both
    global and optional per-row decision cutoffs apply; the earlier wins.
    """
    if not isinstance(bar, dict):
        return {"status": "blocked", "reason": "bar_object_required"}
    result = {"id": bar.get("id")}
    try:
        cutoff = aware_instant(decision_at)
        if "decision_at" in bar:
            cutoff = min(cutoff, aware_instant(bar["decision_at"]))
    except ValueError as exc:
        return {**result, "status": "unknown", "reason": "decision_time_unverified",
                "detail": str(exc)}
    fields = ("session_completed_at", "feature_available_at", "required_input_available_at")
    if bar.get("availability_complete") is not True or any(k not in bar for k in fields):
        return {**result, "status": "unknown", "reason": "availability_declaration_incomplete"}
    inputs = bar["required_input_available_at"]
    if not isinstance(inputs, list) or not inputs:
        return {**result, "status": "unknown", "reason": "required_input_availability_missing"}
    try:
        completed = aware_instant(bar["session_completed_at"])
        available = aware_instant(bar["feature_available_at"])
        required = max(completed, *(aware_instant(v) for v in inputs))
    except ValueError as exc:
        return {**result, "status": "unknown", "reason": "availability_time_unverified",
                "detail": str(exc)}
    if available < required:
        return {**result, "status": "blocked", "reason": "feature_precedes_required_input"}
    utc = {"available_at_utc": available.isoformat(), "cutoff_utc": cutoff.isoformat()}
    if available > cutoff:
        return {**result, **utc, "status": "blocked", "reason": "availability_after_cutoff"}
    return {**result, **utc, "status": "pass", "reason": "available_by_absolute_cutoff"}


def validate_time(candidate):
    if (not isinstance(candidate, dict) or "decision_at" not in candidate
            or not isinstance(candidate.get("bars"), list) or not candidate["bars"]):
        return {"status": "blocked", "reason": "nonempty_time_contract_required"}
    rows = [qualify_bar(bar, candidate["decision_at"]) for bar in candidate["bars"]]
    return {"status": "pass" if all(r["status"] == "pass" for r in rows) else "blocked",
            "rows": rows, "admitted": [r.get("id") for r in rows if r["status"] == "pass"],
            "scope": "declared_time_qualification_only; source_truth_not_certified"}


def validate_document(document):
    if (not isinstance(document, dict) or document.get("schema_version") != "lei-boundary-input/1"
            or set(document) - {"schema_version", "formula", "time"}
            or not ("formula" in document or "time" in document)):
        return {"status": "blocked", "reason": "unsupported_input_schema"}
    checks = {}
    if "formula" in document:
        checks["formula"] = validate_formula(document["formula"])
    if "time" in document:
        checks["time"] = validate_time(document["time"])
    return {"status": "pass" if all(c["status"] == "pass" for c in checks.values()) else "blocked",
            "checks": checks, "production_integrated": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON contract; examples are under fixtures/")
    args = parser.parse_args(argv)
    def reject_nonstandard_number(value):
        raise ValueError(f"nonstandard JSON numeric constant: {value}")
    try:
        result = validate_document(json.loads(args.input.read_text(encoding="utf-8"),
                                              parse_constant=reject_nonstandard_number))
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        result = {"status": "blocked", "reason": "input_error", "detail": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
