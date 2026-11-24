"""Read-only structural review of one strategy-mechanism/1 attachment.

This checks declared scope and bound source identity. It cannot verify an
economic mechanism, measured excess return, or permission to trade.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path


MAX_ATTACHMENT_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
SCOPE_FIELDS = ("market", "universe_id", "frequency", "currency", "asset_type", "purpose")
CLAIM_TYPES = {"relative_return", "net_relative_return"}
RETURN_SOURCES = {"market_exposure", "risk_compensation", "liquidity_service",
                  "information_repricing", "institutional_constraints"}
ROLES = {"parent_index", "investable_alternative", "same_universe_control", "market_reference"}
RETURN_BASES = {"price_return", "gross_total_return", "net_total_return",
                "adjusted_price_proxy", "unknown"}
MEMBERSHIP = {"point_in_time", "fixed_historical_cohort", "current_constituents_backcast", "unknown"}
STAGES = {"hypothesis", "association", "identification_claimed"}
HISTORY = {"already_seen", "protected_unseen_claimed", "unknown"}


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _path(root: Path, supplied, *, max_bytes: int) -> Path:
    if not isinstance(supplied, (str, Path)) or not str(supplied):
        raise ValueError("empty path")
    raw = Path(supplied)
    resolved = (raw if raw.is_absolute() else root / raw).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("missing or outside-root path")
    if resolved.stat().st_size > max_bytes:
        raise ValueError("file exceeds review size limit")
    return resolved


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_mechanism(root, path, expected_candidate=None) -> dict:
    """Check a small local attachment; unknown evidence remains unknown."""
    root = Path(root).resolve()
    base = {"schema": "mechanism-review/1", "status": "not_checked", "issues": [],
            "limitations": [], "source_bindings": [], "attachment_binding": None,
            "candidate_consistency": "not_checked",
            "economic_mechanism_verified": False, "alpha_verified": False,
            "independent_validation_verified": False, "forward_eligible": False}
    if path is None:
        base["limitations"].append("No mechanism attachment was supplied.")
        return base
    invalid = []
    incomplete = []
    warnings = []

    def issue(field, message, *, kind="incomplete"):
        (invalid if kind == "invalid" else incomplete).append(
            {"field": field, "kind": kind, "message": message})

    try:
        attachment = _path(root, path, max_bytes=MAX_ATTACHMENT_BYTES)
        raw = attachment.read_bytes()
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
        base["attachment_binding"] = {"path": str(attachment), "sha256": hashlib.sha256(raw).hexdigest()}
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        issue("attachment", str(exc), kind="invalid")
        base.update(status="invalid", issues=invalid)
        return base
    if not isinstance(document, dict):
        issue("attachment", "top level must be an object", kind="invalid")
        base.update(status="invalid", issues=invalid)
        return base
    if document.get("schema") != "strategy-mechanism/1":
        issue("schema", "requires strategy-mechanism/1", kind="invalid")

    def section(name):
        value = document.get(name)
        if not isinstance(value, dict):
            issue(name, "object required")
            return {}
        return value

    def text(mapping, field, prefix):
        value = mapping.get(field)
        if value is None or value == "":
            issue(f"{prefix}.{field}", "unknown or missing")
        elif not isinstance(value, str) or not value.strip():
            issue(f"{prefix}.{field}", "nonempty text required", kind="invalid")
        return value

    def enum(mapping, field, prefix, allowed):
        value = mapping.get(field)
        if value is None or value == "":
            issue(f"{prefix}.{field}", "unknown or missing")
        elif value == "unknown" and "unknown" in allowed:
            issue(f"{prefix}.{field}", "declared unknown")
        elif not isinstance(value, str) or value not in allowed:
            issue(f"{prefix}.{field}", f"unsupported value: {value}", kind="invalid")
        return value

    identity = section("identity")
    candidate_id = text(identity, "candidate_id", "identity")
    keys = identity.get("component_keys")
    if not isinstance(keys, list) or not keys or any(not isinstance(v, str) or not v for v in keys):
        issue("identity.component_keys", "nonempty exact keys required")
    elif len(set(keys)) != len(keys):
        issue("identity.component_keys", "duplicate exact keys", kind="invalid")
    scope = identity.get("scope")
    if not isinstance(scope, dict):
        issue("identity.scope", "object required")
        scope = {}
    for field in SCOPE_FIELDS:
        text(scope, field, "identity.scope")
    if expected_candidate is not None:
        before_identity = len(invalid)
        if not isinstance(expected_candidate, dict):
            issue("expected_candidate", "object required", kind="invalid")
        else:
            if candidate_id != expected_candidate.get("id"):
                issue("identity.candidate_id", "differs from candidate", kind="invalid")
            expected_keys = expected_candidate.get("component_keys")
            if (not isinstance(expected_keys, list) or
                    any(not isinstance(v, str) for v in expected_keys) or
                    not isinstance(keys, list) or
                    any(not isinstance(v, str) for v in keys) or set(keys) != set(expected_keys)):
                issue("identity.component_keys", "differs from candidate", kind="invalid")
            expected_scope = expected_candidate.get("scope")
            if not isinstance(expected_scope, dict):
                expected_scope = {}
            for field in SCOPE_FIELDS:
                if scope.get(field) != expected_scope.get(field):
                    issue(f"identity.scope.{field}", "differs from candidate", kind="invalid")
        base["candidate_consistency"] = "mismatch" if len(invalid) > before_identity else "matched"
    claim = section("claim")
    claim_type = enum(claim, "type", "claim", CLAIM_TYPES)
    text(claim, "increment_measure", "claim")
    return_sources = claim.get("return_sources")
    if not isinstance(return_sources, list) or not return_sources:
        issue("claim.return_sources", "at least one proposed source required")
    elif (any(not isinstance(v, str) or v not in RETURN_SOURCES for v in return_sources) or
          len(set(return_sources)) != len(return_sources)):
        issue("claim.return_sources", "duplicate or unsupported source", kind="invalid")
    benchmark = section("benchmark")
    for field in ("id", "universe_id", "selection_reason", "currency",
                  "cost_basis", "investability_evidence"):
        text(benchmark, field, "benchmark")
    role = enum(benchmark, "role", "benchmark", ROLES)
    return_basis = enum(benchmark, "return_basis", "benchmark", RETURN_BASES)
    selected_before = benchmark.get("selected_before_results")
    if selected_before is None:
        issue("benchmark.selected_before_results", "unknown selection timing")
    elif type(selected_before) is not bool:
        issue("benchmark.selected_before_results", "boolean or null required", kind="invalid")
    elif selected_before is False:
        warnings.append("Benchmark selected after results; historical comparison remains exploratory.")
    if benchmark.get("currency") and scope.get("currency") and benchmark["currency"] != scope["currency"]:
        issue("benchmark.currency", "conflicts with candidate currency", kind="invalid")
    if (role == "same_universe_control" and benchmark.get("universe_id") and
            scope.get("universe_id") and benchmark["universe_id"] != scope["universe_id"]):
        issue("benchmark.universe_id", "same_universe_control requires the candidate universe_id", kind="invalid")
    mechanism = section("mechanism")
    for field in ("participants_constraints", "compensation_or_service", "persistence",
                  "signal_link", "competing_explanation", "distinguishing_prediction", "falsifier"):
        text(mechanism, field, "mechanism")
    stage = enum(mechanism, "evidence_stage", "mechanism", STAGES)
    universe = section("universe")
    text(universe, "fit_reason", "universe")
    membership = enum(universe, "membership_basis", "universe", MEMBERSHIP)
    text(universe, "negative_control", "universe")
    if membership in ("fixed_historical_cohort", "current_constituents_backcast", "unknown"):
        warnings.append("Historical membership is not established point in time; tradability is unassessed.")
    timing = section("timing")
    created = text(timing, "created_at", "timing")
    if isinstance(created, str) and created:
        try:
            parsed = datetime.fromisoformat(created)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("timezone required")
        except ValueError:
            issue("timing.created_at", "timezone-aware ISO timestamp required", kind="invalid")
    for field in ("information_available", "earliest_execution", "prior_attempts"):
        text(timing, field, "timing")
    history = enum(timing, "history_status", "timing", HISTORY)
    if history == "already_seen":
        warnings.append("Historical outcomes already seen; no unseen validation is established.")
    elif history == "protected_unseen_claimed":
        warnings.append("Protected unseen history is a declaration, not independent verification.")
    controls = section("controls")
    for field in ("strongest_simple_comparator", "risk_exposure_comparator",
                  "cost_capacity_plan", "uncertainty_plan"):
        text(controls, field, "controls")
    sources = document.get("sources")
    source_ids = set()
    if not isinstance(sources, list):
        issue("sources", "list required")
        sources = []
    for position, source in enumerate(sources):
        prefix = f"sources[{position}]"
        if not isinstance(source, dict):
            issue(prefix, "object required", kind="invalid")
            continue
        sid = text(source, "id", prefix)
        if isinstance(sid, str):
            if sid in source_ids:
                issue(prefix + ".id", "duplicate source id", kind="invalid")
            source_ids.add(sid)
        for field in ("locator", "reading_scope"):
            text(source, field, prefix)
        declared = text(source, "sha256", prefix)
        if not isinstance(declared, str) or not declared:
            continue
        if len(declared) != 64 or any(v not in "0123456789abcdef" for v in declared):
            issue(prefix + ".sha256", "lowercase SHA-256 required", kind="invalid")
            continue
        if source.get("path") is None:
            issue(prefix + ".path", "source path required")
            continue
        try:
            bound = _path(root, source["path"], max_bytes=MAX_SOURCE_BYTES)
            actual = _sha(bound)
            if actual != declared:
                issue(prefix + ".sha256", "source SHA-256 drift", kind="invalid")
            else:
                base["source_bindings"].append({"id": sid, "path": str(bound), "sha256": actual,
                                                "locator": source.get("locator"),
                                                "reading_scope": source.get("reading_scope")})
        except (OSError, ValueError) as exc:
            issue(prefix + ".path", str(exc), kind="invalid")
    refs = document.get("source_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(v, str) or not v for v in refs):
        issue("source_refs", "nonempty source IDs required")
    elif len(set(refs)) != len(refs) or any(ref not in source_ids for ref in refs):
        issue("source_refs", "duplicate or unbound source ID", kind="invalid")
    questions = document.get("open_questions")
    if not isinstance(questions, list) or any(not isinstance(q, str) or not q.strip() for q in questions):
        issue("open_questions", "text list required; may be empty", kind="invalid")
    if claim_type == "net_relative_return":
        if role not in ("investable_alternative", "same_universe_control"):
            issue("benchmark.role", "net relative return needs an investable alternative, not an index role")
        if not benchmark.get("investability_evidence") or not benchmark.get("cost_basis"):
            issue("benchmark", "net relative return needs stated costs and investability for both sides")
        if membership in ("current_constituents_backcast", "unknown"):
            issue("universe.membership_basis", "net claim lacks qualified historical membership")
        if return_basis != "net_total_return":
            issue("benchmark.return_basis", "net relative return requires net_total_return")
    if stage == "identification_claimed" and not refs:
        issue("source_refs", "claimed identification needs bound sources")
    base["issues"] = invalid + incomplete
    base["warnings"] = warnings
    base["declared_evidence_stage"] = stage
    base["status"] = ("invalid" if invalid else "incomplete" if incomplete else
                      "complete_for_manual_review")
    base["limitations"] = ["Source hashes verify file identity, not the truth of quoted claims.",
                           "Economic mechanism, relative alpha, and forward use are never certified."]
    return base
