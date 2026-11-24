"""Read-only timing diagnostics on saved answer fragments and bounded evidence.

Coverage is a supplied declaration, never an authenticity or completeness audit.
No fetching, model calls, financial accuracy certification, or execution authority.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from .financial_revisions import _instant, _interval, load_bundle, select_versions

_MAX_BYTES = 1024 * 1024
_STATUSES = ("future_reference", "stale_version", "stale_period", "matched", "unresolved")


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid {field}")
    return value


def _amount(value):
    try:
        result = Decimal(_text(value, "value"))
        if not result.is_finite():
            raise ValueError("nonfinite value")
        return result
    except InvalidOperation as exc:
        raise ValueError("invalid value") from exc


def _day(value):
    if date.fromisoformat(_text(value, "period_end")).isoformat() != value:
        raise ValueError("invalid period_end")
    return value


def _source_bindings(root, catalog_path, bundle):
    """Preflight before the legacy loader can open any raw source."""
    bindings = []
    for row in bundle["records"]:
        source = row["source"]
        raw_path = Path(_text(source.get("path"), "source.path"))
        path = (catalog_path.parent / raw_path).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("source must be a file inside root")
        if path.stat().st_size > _MAX_BYTES:
            raise ValueError("source exceeds 1 MiB")
        with path.open("rb") as handle:
            payload = handle.read(_MAX_BYTES + 1)
        if len(payload) > _MAX_BYTES:
            raise ValueError("source exceeds 1 MiB")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != source.get("sha256"):
            raise ValueError("source SHA-256 mismatch")
        bindings.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": digest,
                "locator": _text(source.get("locator"), "source.locator"),
            }
        )
    return bindings


def _claim(value, reference):
    if not isinstance(value, dict):
        raise ValueError("claim must bind a saved answer object")
    for name in ("code", "metric", "version", "unit", "raw_answer"):
        _text(value.get(name), name)
    if value.get("data_mode") not in ("real", "synthetic"):
        raise ValueError("invalid data_mode")
    if value.get("question_mode") not in ("exact", "latest"):
        raise ValueError("invalid question_mode")
    if value.get("availability_basis") not in ("public", "vendor"):
        raise ValueError("invalid availability_basis")
    if value.get("answer_origin") != "model":
        raise ValueError("saved model answer required; fallback is not model evidence")
    for name in ("model", "model_version", "response_id"):
        identity_value = _text(value.get("answer_identity", {}).get(name), name)
        if identity_value.strip().lower() in ("unknown", "null", "none", "n/a"):
            raise ValueError(f"answer_identity.{name} is unknown")
    if value.get("answer_locator", {}).get("pointer") != reference.get("pointer"):
        raise ValueError("answer locator must match bound reference pointer")
    _instant(_text(value.get("decision_at"), "decision_at"))
    _day(value.get("period_end"))
    _amount(value.get("value"))
    if value["question_mode"] == "exact":
        _day(value.get("requested_period_end"))
    return value


def _coverage(bundle, claim):
    candidates = [
        row
        for row in bundle.get("coverage", [])
        if isinstance(row, dict)
        and row.get("code") == claim["code"]
        and row.get("metric") == claim["metric"]
    ]
    if len(candidates) != 1:
        return False
    row = candidates[0]
    periods = row.get("period_ends")
    if not isinstance(periods, list) or not periods or len(set(periods)) != len(periods):
        return False
    for period in periods:
        _day(period)
    catalog_periods = {
        item["period_end"]
        for item in bundle["records"]
        if item["code"] == claim["code"] and item["metric"] == claim["metric"]
    }
    if set(periods) != catalog_periods or claim["period_end"] not in periods:
        return False
    if row.get("complete_versions") is not True or not row.get("as_of"):
        return False
    if _instant(row["as_of"]) < _instant(claim["decision_at"]):
        return False
    return claim["question_mode"] == "exact" or row.get("complete_periods") is True


def _review(bundle, claim):
    cutoff = _instant(claim["decision_at"])
    key = (claim["code"], claim["metric"], claim["period_end"])
    rows = [
        row
        for row in bundle["records"]
        if (row["code"], row["metric"], row["period_end"], row["version"])
        == (*key, claim["version"])
    ]
    cited = rows[0] if len(rows) == 1 else None
    mismatch_reasons = []
    if cited is not None and (
        _amount(claim["value"]) != _amount(cited["value"]) or claim["unit"] != cited["unit"]
    ):
        mismatch_reasons.append("value_or_unit_differs_from_cited_version")
    if claim["question_mode"] == "exact" and claim["requested_period_end"] != claim["period_end"]:
        mismatch_reasons.append("answer_period_differs_from_requested_period")
    status, reason, expected = "unresolved", "cited_version_missing", None
    if cited is not None:
        intervals = [_interval(cited.get("published_at"), ZoneInfo(bundle["publication_timezone"]))]
        if claim["availability_basis"] == "vendor":
            intervals.append(
                _interval(
                    cited.get("vendor_available_at"), ZoneInfo(bundle["publication_timezone"])
                )
            )
        if any(interval is not None and interval[0] >= cutoff for interval in intervals):
            status, reason = "future_reference", "cited_version_not_before_decision"
        elif any(interval is None or interval[1] >= cutoff for interval in intervals):
            reason = "cited_version_availability_unknown"
        elif not _coverage(bundle, claim):
            reason = "coverage_not_sufficiently_declared"
        else:
            selected = select_versions(
                bundle, claim["decision_at"], availability_basis=claim["availability_basis"]
            )
            relevant_unknown = [
                item
                for item in selected["unresolved"]
                if item["key"][:2] == key[:2]
                and (claim["question_mode"] == "latest" or tuple(item["key"]) == key)
            ]
            candidates = [
                row
                for row in selected["selected"]
                if (row["code"], row["metric"]) == key[:2]
                and (claim["question_mode"] == "latest" or row["period_end"] == key[2])
            ]
            if relevant_unknown:
                reason = "version_or_period_availability_unknown"
            elif candidates:
                # Most recent reporting period wins; old-period revisions do not.
                expected = max(candidates, key=lambda row: row["period_end"])
                if expected["period_end"] != claim["period_end"]:
                    status, reason = "stale_period", "newer_reporting_period_available"
                elif expected["version"] != claim["version"]:
                    status, reason = "stale_version", "newer_version_of_same_period_available"
                else:
                    status, reason = "matched", "matches_declared_available_version"
            else:
                reason = "no_definitely_available_target"
    return {
        "timing_status": status,
        "reason": reason,
        "fact_mismatch": bool(mismatch_reasons),
        "fact_mismatch_reasons": mismatch_reasons,
        "expected": expected,
        "cited_version_found": cited is not None,
    }


def review_timing(root, request):
    """Review 1–100 source-bound saved answers; malformed evidence raises ValueError.

    ``catalog`` and every item in ``claims`` are {path, sha256, pointer} references.
    Catalog pointer must be empty, binding the full financial-source-versions/1 bundle.
    ``coverage`` declarations belong to that bundle; answer metadata is bound in each
    claim object. See unit fixtures for the deliberately small accepted object shape.
    """
    from .llm_output_review import read_evidence

    try:
        root = Path(root).resolve(strict=True)
        if not isinstance(request, dict) or request.get("schema") != "llm-timing-review/1":
            raise ValueError("unsupported timing review schema")
        references = request.get("claims")
        if not isinstance(references, list) or not 1 <= len(references) <= 100:
            raise ValueError("claims must contain 1 to 100 saved-answer references")
        catalog_ref = request["catalog"]
        if catalog_ref.get("pointer") != "":
            raise ValueError("catalog pointer must bind the full bundle")
        bundle, catalog_binding = read_evidence(root, catalog_ref)
        if not isinstance(bundle, dict) or bundle.get("schema") != "financial-source-versions/1":
            raise ValueError("unsupported financial catalog schema")
        catalog_path = (root / catalog_ref["path"]).resolve(strict=True)
        sources = _source_bindings(root, catalog_path, bundle)
        loaded = load_bundle(catalog_path)
        repeated, repeated_binding = read_evidence(root, catalog_ref)
        if (
            loaded != bundle
            or repeated != bundle
            or repeated_binding != catalog_binding
            or _source_bindings(root, catalog_path, repeated) != sources
        ):
            raise ValueError("catalog or source binding drift")
        results, summary, groups = [], {}, {}
        seen_sources, seen_response_facts = {}, {}
        fact_members, fact_declarations, conflicts = {}, {}, set()
        zone = ZoneInfo(bundle["publication_timezone"])
        for reference in references:
            value, binding = read_evidence(root, reference)
            claim = _claim(value, reference)
            result = _review(bundle, claim)
            result.update(
                {
                    "binding": binding,
                    "answer_identity": claim["answer_identity"],
                    "data_mode": claim["data_mode"],
                    "decision_at": claim["decision_at"],
                    "code": claim["code"],
                    "metric": claim["metric"],
                    "period_end": claim["period_end"],
                    "question_mode": claim["question_mode"],
                }
            )
            source_key = (binding["sha256"], binding["pointer"])
            identity = claim["answer_identity"]
            # Changing wrapper metadata cannot turn the same response/fact into
            # another observation. Values/versions are declarations of that fact.
            fact_key = (
                identity["model"],
                identity["model_version"],
                identity["response_id"],
                claim["code"],
                claim["metric"],
                claim["period_end"],
                _instant(claim["decision_at"]),
                claim["availability_basis"],
                claim["question_mode"],
                claim.get("requested_period_end"),
            )
            declaration = (
                claim["version"],
                claim["value"],
                claim["unit"],
                claim["raw_answer"],
                claim["data_mode"],
            )
            if fact_key in fact_declarations and fact_declarations[fact_key] != declaration:
                conflicts.add(fact_key)
            fact_declarations.setdefault(fact_key, declaration)
            fact_members.setdefault(fact_key, []).append(len(results))
            duplicate_of = seen_sources.get(source_key, seen_response_facts.get(fact_key))
            result["conflicting_duplicate"] = False
            result["duplicate"] = duplicate_of is not None
            result["duplicate_of"] = duplicate_of
            result["included_in_denominators"] = duplicate_of is None
            index = len(results)
            seen_sources.setdefault(source_key, index)
            seen_response_facts.setdefault(fact_key, index)
            results.append(result)
        # Resolve conflicts before any totals: a later conflicting wrapper also
        # invalidates the first apparent success and every exact copy in its group.
        for fact_key in conflicts:
            for index in fact_members[fact_key]:
                row = results[index]
                row["original_timing_status"] = row["timing_status"]
                row["timing_status"] = "unresolved"
                row["reason"] = "conflicting_duplicate"
                row["conflicting_duplicate"] = True
                row["included_in_denominators"] = False
        for result in results:
            mode = result["data_mode"]
            counts = summary.setdefault(
                mode,
                {
                    **dict.fromkeys(_STATUSES, 0),
                    "fact_mismatch": 0,
                    "saved_answer_fragment_count": 0,
                    "eligible_claim_count": 0,
                    "input_reference_count": 0,
                    "duplicate_count": 0,
                    "conflicting_duplicate_count": 0,
                },
            )
            counts["input_reference_count"] += 1
            counts["duplicate_count"] += int(result["duplicate"])
            if result["conflicting_duplicate"]:
                counts["conflicting_duplicate_count"] += 1
                continue
            if result["duplicate"]:
                continue
            counts[result["timing_status"]] += 1
            counts["fact_mismatch"] += int(result["fact_mismatch"])
            counts["saved_answer_fragment_count"] += 1
            counts["eligible_claim_count"] += int(result["timing_status"] != "unresolved")
            # Repeated replies for one metric/date remain one descriptive group.
            groups.setdefault(mode, set()).add(
                (result["code"], result["metric"], cutoff_date(result["decision_at"], zone))
            )
        for mode, counts in summary.items():
            counts["decision_group_count"] = len(groups.get(mode, set()))
            counts["stale_total"] = counts["stale_version"] + counts["stale_period"]
        return {
            "schema": "llm-timing-review-result/1",
            "status": "reviewed",
            "assessment_complete": all(
                not row["conflicting_duplicate"] and row["timing_status"] != "unresolved"
                for row in results
                if not row["duplicate"] or row["conflicting_duplicate"]
            ),
            "catalog_binding": catalog_binding,
            "source_bindings": sources,
            "claims": results,
            "summary": summary,
            "real_error_rate": "not_evaluated",
            "independent_sample_count": "not_evaluated",
            "denominator_definition": "eligible_claim_count excludes unresolved "
            "and duplicate/conflicting saved answer fragments; "
            "decision_group_count groups code/metric/local decision date and is not independence",
            "structured_claim_extraction_verified": False,
            "coverage_certified": False,
            "run_authorized": False,
            "limitations": [
                "Declared coverage is not authenticated or independently certified.",
                "Saved answer fragments are not independent samples or a model accuracy estimate.",
                "No model calls, market tests, financial correctness certification "
                "or trading authorization.",
                "Timing and numeric/unit mismatch are reported separately.",
                "Structured facts are supplied declarations; extraction from raw_answer "
                "is unverified.",
                "Duplicate source fragments or response/fact identities remain visible "
                "but are excluded from all denominators and diagnostic counts.",
                "Conflicting declarations for a response/fact invalidate the entire group; "
                "conflicting_duplicate_count counts retained references, not independent errors.",
            ],
        }
    except (OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError(f"invalid timing evidence: {exc}") from exc


def cutoff_date(value, zone):
    return _instant(value).astimezone(zone).date().isoformat()
