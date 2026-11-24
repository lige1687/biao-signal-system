"""Read-only factor catalog and bounded combination diagnostics.

Registered definitions are descriptive source records, not validated signals.
No function here backtests, optimizes weights, or authorizes forward trading.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import statistics

from lei_signal.research import osap_reference, preparation
from lei_signal.research.mechanism_review import review_mechanism


SCOPE_FIELDS = ("market", "universe_id", "frequency", "currency", "return_basis", "series_kind")
RULE_FIELDS = ("universe", "signal", "decision_time", "execution_time", "allocation",
               "rebalance", "exit", "missing_data", "costs", "benchmark")
CHECK_FIELDS = ("historical_membership", "point_in_time", "prices_and_exits", "holdings",
                "transaction_costs", "parent_benchmark", "unseen_validation")
RELATIONSHIPS = ("return", "co_losses", "score", "holdings")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _binding(path: Path, root: Path | None = None, declared: str | None = None) -> dict:
    path = path.resolve()
    if not path.is_file() or root is not None and not path.is_relative_to(root.resolve()):
        raise ValueError(f"source missing or outside root: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if declared is not None and actual != declared:
        raise ValueError(f"source SHA-256 drift: {path}")
    return {"path": str(path), "sha256": actual}


def _annotated(card: dict, annotation: dict) -> None:
    for source, target in (("family", "family"), ("financial_meaning", "financial_meaning"),
                           ("markets", "market"), ("assets", "assets"),
                           ("purposes", "uses"), ("horizon", "horizon")):
        if source in annotation:
            native = card[target]
            supplied = annotation[source]
            if target in ("market", "assets", "uses") and native not in (None, [], ""):
                native_set = set(native if isinstance(native, list) else [native])
                supplied_set = set(supplied if isinstance(supplied, list) else [supplied])
                if not supplied_set or (supplied_set != native_set if target != "uses"
                                        else not supplied_set <= native_set):
                    raise ValueError(f"annotation conflicts with native {target}: {card['key']}")
            card[target] = annotation[source]
            card.setdefault("annotation_only_fields", []).append(target)
    card["annotation"] = annotation


def build_catalog(root, profiles_path=None, osap_manifest=None) -> dict:
    root = Path(root).resolve()
    standards_path = root / "docs/research/current-standards.json"
    standards_binding = _binding(standards_path, root)
    standards = _read(standards_path)
    registry_path = root / standards["definition_registry"]
    registry_binding = _binding(registry_path, root)
    registry = _read(registry_path)  # Old schemas remain native; no global validation claim.
    cards = {}
    for section, prefix in (("objects", "object"), ("research_references", "reference")):
        for item in registry.get(section, []):
            key = f"{prefix}:{item['id']}@{item['version']}"
            if key in cards:
                raise ValueError(f"duplicate exact identity: {key}")
            if prefix == "object":
                scope = item.get("scope") if isinstance(item.get("scope"), dict) else {}
                native_market = scope.get("market")
                native_assets = scope.get("assets")
                native_horizon = item.get("time", {}).get("horizon") if isinstance(item.get("time"), dict) else None
                native_sources = item.get("sources", [])
                kind = item.get("type")
            else:
                native_market = item.get("market")
                native_assets = item.get("asset_type")
                native_horizon = None  # Observation frequency is not a decision horizon.
                native_sources = [item.get("source")] if item.get("source") else []
                kind = item.get("kind")
            cards[key] = {
                "key": key, "name": item.get("name"), "kind": kind,
                "definition_ref": f"{item['id']}@{item['version']}",
                "native_metadata": item, "market": native_market, "assets": native_assets,
                "uses": item.get("uses"), "family": None, "financial_meaning": None,
                "horizon": native_horizon, "evidence": [],
                "unknown_fields": [field for field, value in
                                   (("market", native_market), ("assets", native_assets),
                                    ("family", None), ("financial_meaning", None),
                                    ("horizon", native_horizon)) if value is None],
                "source_bindings": {"definition_registry": registry_binding,
                                    "native_sources_unverified": native_sources},
                "validation_status": "registered_native_only_not_globally_validated",
                "annotation_only_fields": [],
            }
    bindings = {"standards": standards_binding, "definition_registry": registry_binding}
    if profiles_path is not None:
        supplied_profile = Path(profiles_path)
        profile_path = (supplied_profile if supplied_profile.is_absolute() else root / supplied_profile).resolve()
        profile_binding = _binding(profile_path, root)
        profiles = _read(profile_path)
        if profiles.get("schema") != "factor-combination-profiles/1" or not isinstance(profiles.get("annotations"), list):
            raise ValueError("invalid profile schema")
        seen = set()
        for ann in profiles["annotations"]:
            key = ann.get("key")
            if key not in cards or key in seen:
                raise ValueError(f"unknown or duplicate annotation key: {key}")
            seen.add(key)
            evidence_bindings = []
            for ev in ann.get("evidence", []):
                path = Path(ev["path"])
                if not path.is_absolute():
                    path = root / path
                evidence_bindings.append(_binding(path, root, ev["sha256"]))
            _annotated(cards[key], ann)
            cards[key]["evidence"] = evidence_bindings
            cards[key]["source_bindings"]["annotation_profile"] = profile_binding
            cards[key]["source_bindings"]["annotation_evidence"] = evidence_bindings
            cards[key]["unknown_fields"] = [field for field in ("market", "assets", "uses", "family",
                "financial_meaning", "horizon") if cards[key][field] in (None, [], "")]
        bindings["profiles"] = profile_binding
    if osap_manifest is not None:
        supplied_manifest = Path(osap_manifest)
        manifest_path = (supplied_manifest if supplied_manifest.is_absolute() else root / supplied_manifest).resolve()
        loaded = osap_reference.load_reference(manifest_path)
        spec = loaded["manifest"]
        manifest_binding = _binding(manifest_path)
        catalog_path = Path(spec["catalog"]["path"])
        returns_path = Path(spec["returns"]["path"])
        source_bindings = {"manifest": manifest_binding,
                           "catalog": _binding(catalog_path if catalog_path.is_absolute() else manifest_path.parent / catalog_path,
                                               declared=spec["catalog"]["sha256"]),
                           "returns": _binding(returns_path if returns_path.is_absolute() else manifest_path.parent / returns_path,
                                               declared=spec["returns"]["sha256"])}
        for acronym, row in loaded["catalog"].items():
            key = f"osap:{acronym}@{source_bindings['catalog']['sha256'][:12]}"
            period_raw = row.get("Portfolio Period", "").strip()
            period_months = int(period_raw) if period_raw.isdecimal() and int(period_raw) > 0 else None
            cards[key] = {
                "key": key, "name": acronym, "kind": "published_reference",
                "definition_ref": None, "native_metadata": row, "market": "US", "assets": "stock",
                "uses": ["descriptive_reference"], "family": row.get("Cat.Economic") or None,
                "financial_meaning": row.get("LongDescription") or None,
                "meaning_status": "source_description_not_reviewed_mechanism",
                "horizon": None, "portfolio_period_months": period_months,
                "portfolio_period_source_value": period_raw or None,
                "portfolio_period_note": "Source holding period in months; not a forecast horizon or observation frequency.",
                "frequency": "monthly_published_long_short_returns", "evidence": [],
                "unknown_fields": [field for field, value in (("family", row.get("Cat.Economic")),
                                    ("horizon", None), ("portfolio_period_months", period_months)) if not value],
                "source_bindings": source_bindings,
                "native_categories": {name: row.get(name) for name in
                                      ("Cat.Economic", "Cat.Data", "Sign", "Portfolio Period", "Filter")},
                "validation_status": "published_long_short_reference_not_stock_score",
                "annotation_only_fields": [],
                "return_direction": "published_long_short_do_not_apply_sign_again",
            }
        bindings["osap"] = source_bindings
    return {"schema": "factor-combination-catalog/1", "root": str(root), "cards": cards,
            "total": len(cards), "source_bindings": bindings,
            "validation_status": "native_registry_not_globally_validated"}


def query_catalog(catalog: dict, term=None, market=None, family=None, purpose=None,
                  limit: int = 50) -> dict:
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be positive integer")
    selected = []
    for card in catalog["cards"].values():
        if term and term.casefold() not in json.dumps(card, ensure_ascii=False).casefold():
            continue
        if market and market not in ([card["market"]] if isinstance(card["market"], str) else card["market"] or []):
            continue
        if family and (card["family"] is None or family.casefold() not in str(card["family"]).casefold()):
            continue
        if purpose and purpose not in (card["uses"] or []):
            continue
        selected.append(card)
    return {"selected": selected[:limit], "total": len(selected),
            "truncated": len(selected) > limit}


def _scope(left: dict, right: dict, kind: str) -> None:
    for scope in (left, right):
        if any(not isinstance(scope.get(field), str) or not scope[field].strip() for field in SCOPE_FIELDS):
            raise ValueError("incomplete relationship scope")
        if scope["series_kind"] != kind:
            raise ValueError(f"expected series_kind={kind}")
    if any(left[field] != right[field] for field in SCOPE_FIELDS):
        raise ValueError("incompatible relationship scopes")


def _day(value: str, frequency: str) -> str:
    if not isinstance(value, str):
        raise ValueError("date must be text")
    if frequency not in ("monthly", "daily"):
        raise ValueError("date precision requires monthly or daily frequency")
    if frequency == "monthly" and (len(value) != 7 or value[4:5] != "-"):
        raise ValueError("monthly dates require YYYY-MM")
    if frequency == "daily" and (len(value) != 10 or value[4:5] != "-" or value[7:8] != "-"):
        raise ValueError("daily dates require YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value + "-01" if frequency == "monthly" else value)
    except ValueError:
        raise ValueError(f"invalid date: {value}") from None
    if value != (parsed.isoformat()[:7] if frequency == "monthly" else parsed.isoformat()):
        raise ValueError(f"invalid date: {value}")
    return value


def _next_month(month: str) -> str:
    year, part = int(month[:4]), int(month[5:])
    return f"{year + (part == 12):04d}-{1 if part == 12 else part + 1:02d}"


def _coverage(left: set[str], right: set[str], usable: set[str],
              left_scope: dict, right_scope: dict) -> dict:
    left_expected = left_scope.get("expected_dates")
    right_expected = right_scope.get("expected_dates")
    if left_expected != right_expected:
        raise ValueError("expected_dates must match on both scopes")
    frequency = left_scope["frequency"]
    if left_expected is not None:
        if (not isinstance(left_expected, list) or not left_expected or
                any(not isinstance(value, str) for value in left_expected) or
                len(set(left_expected)) != len(left_expected)):
            raise ValueError("expected_dates must be a nonempty unique list")
        expected = [_day(value, frequency) for value in left_expected]
        if expected != sorted(expected):
            raise ValueError("expected_dates must be ordered")
        if frequency == "monthly" and any(_next_month(first) != second
                                           for first, second in zip(expected, expected[1:])):
            raise ValueError("monthly expected_dates must be continuous")
        if not (left | right) <= set(expected):
            raise ValueError("observed date outside expected_dates")
        declared = True
    elif frequency == "monthly" and (left or right):
        first, last = min(left | right), max(left | right)
        expected = [first]
        while expected[-1] < last:
            expected.append(_next_month(expected[-1]))
        declared = False
    else:
        expected, declared = [], False
    left_missing = sorted(set(expected) - left)
    right_missing = sorted(set(expected) - right)
    usable_missing = sorted(set(expected) - usable)
    status = ("incomplete" if usable_missing else "complete" if declared else "undeclared")
    return {"expected_dates_count": len(expected) if expected else None,
            "expected_dates_declared": declared,
            "left_missing_dates": left_missing, "right_missing_dates": right_missing,
            "usable_missing_dates": usable_missing, "coverage_status": status,
            "coverage_note": ("Declared target dates checked; missing observations remain missing."
                              if declared else "No complete target calendar declared; monthly interior gaps are detected only within observed bounds.")}


def _numeric(value, *, nullable=False, nonnegative=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("value must be finite numeric or explicitly null")
    if nonnegative and value < 0:
        raise ValueError("negative weight")
    return float(value)


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3:
        return None
    lm, rm = statistics.mean(left), statistics.mean(right)
    lx, rx = [x - lm for x in left], [x - rm for x in right]
    den = math.sqrt(sum(x*x for x in lx) * sum(x*x for x in rx))
    return sum(x*y for x, y in zip(lx, rx)) / den if den else None


def _series(rows: list[dict], frequency: str) -> dict:
    result = {}
    for row in rows:
        day = _day(row["date"], frequency)
        if day in result:
            raise ValueError(f"duplicate date: {day}")
        result[day] = _numeric(row["value"], nullable=True)
    return result


def return_relationship(left, right, left_scope, right_scope) -> dict:
    _scope(left_scope, right_scope, "return")
    frequency = left_scope["frequency"]
    a, b = _series(left, frequency), _series(right, frequency)
    common_dates = sorted(set(a) & set(b))
    usable = [day for day in common_dates if a[day] is not None and b[day] is not None]
    losses = [{"date": day, "left": a[day], "right": b[day], "joint_sum": a[day] + b[day]}
              for day in usable if a[day] < 0 and b[day] < 0]
    left_only = sum(a[day] < 0 and b[day] >= 0 for day in usable)
    right_only = sum(b[day] < 0 and a[day] >= 0 for day in usable)
    coverage = _coverage(set(a), set(b), set(usable), left_scope, right_scope)
    return {"left_scope": left_scope, "right_scope": right_scope, **coverage,
            "left_dates": len(a), "right_dates": len(b),
            "left_missing": sum(v is None for v in a.values()),
            "right_missing": sum(v is None for v in b.values()),
            "calendar_intersection": len(common_dates), "common_periods": len(usable),
            "excluded_from_intersection": len(common_dates) - len(usable),
            "correlation": _pearson([a[d] for d in usable], [b[d] for d in usable]),
            "common_loss_count": len(losses),
            "common_loss_share": len(losses) / len(usable) if usable else None,
            "left_only_loss_count": left_only, "right_only_loss_count": right_only,
            "left_down_right_up_count": sum(a[day] < 0 and b[day] > 0 for day in usable),
            "right_down_left_up_count": sum(b[day] < 0 and a[day] > 0 for day in usable),
            "joint_loss_mean_left": statistics.mean(x["left"] for x in losses) if losses else None,
            "joint_loss_mean_right": statistics.mean(x["right"] for x in losses) if losses else None,
            "min_joint_month_sum": min((x["joint_sum"] for x in losses), default=None),
            "common_loss_months": losses,
            "joint_sum_note": "Descriptive sum of two series values in common-loss months; not account return.",
            "qualification_note": "Matched declared scopes permit description only; historical investability and actual underlying pools are not inferred."}


def _panel(rows, frequency: str, *, holding=False):
    panel = defaultdict(dict)
    totals = defaultdict(float)
    for row in rows:
        day, symbol = _day(row["date"], frequency), row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip() or symbol in panel[day]:
            raise ValueError("blank or duplicate date-symbol")
        value = _numeric(row["weight"] if holding else row["value"],
                         nullable=not holding, nonnegative=holding)
        panel[day][symbol] = value
        if holding:
            totals[day] += value
    if holding and any(total > 1 + 1e-12 for total in totals.values()):
        raise ValueError("holding weights exceed one")
    return dict(panel)


def _ranks(values):
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        rank = ((i + 1) + j) / 2
        for index, _ in ordered[i:j]:
            result[index] = rank
        i = j
    return result


def score_relationship(left, right, left_scope, right_scope) -> dict:
    _scope(left_scope, right_scope, "score")
    frequency = left_scope["frequency"]
    a, b = _panel(left, frequency), _panel(right, frequency)
    rows = []
    for day in sorted(set(a) & set(b)):
        common = set(a[day]) & set(b[day])
        usable = sorted(symbol for symbol in common if a[day][symbol] is not None and b[day][symbol] is not None)
        correlation = _pearson(_ranks([a[day][s] for s in usable]),
                               _ranks([b[day][s] for s in usable]))
        rows.append({"date": day, "left_n": len(a[day]), "right_n": len(b[day]),
                     "common_n": len(common), "n": len(usable),
                     "missing_or_null_common": len(common) - len(usable),
                     "spearman": correlation})
    values = [row["spearman"] for row in rows if row["spearman"] is not None]
    coverage = _coverage(set(a), set(b), {row["date"] for row in rows if row["n"]},
                         left_scope, right_scope)
    return {"left_scope": left_scope, "right_scope": right_scope, **coverage,
            "left_dates": len(a), "right_dates": len(b),
            "common_dates": len(rows), "per_date": rows,
            "mean_spearman": statistics.mean(values) if values else None,
            "valid_correlation_dates": len(values),
            "direction_note": "Scores used as supplied; caller must normalize direction explicitly."}


def holdings_relationship(left, right, left_scope, right_scope) -> dict:
    _scope(left_scope, right_scope, "holding")
    frequency = left_scope["frequency"]
    a, b = _panel(left, frequency, holding=True), _panel(right, frequency, holding=True)
    rows = []
    for day in sorted(set(a) & set(b)):
        shared = set(a[day]) & set(b[day])
        rows.append({"date": day, "left_symbols": len(a[day]), "right_symbols": len(b[day]),
                     "shared_symbols": len(shared),
                     "capital_overlap": sum(min(a[day][s], b[day][s]) for s in shared),
                     "left_invested": sum(a[day].values()), "right_invested": sum(b[day].values())})
    coverage = _coverage(set(a), set(b), {row["date"] for row in rows},
                         left_scope, right_scope)
    return {"left_scope": left_scope, "right_scope": right_scope, **coverage,
            "left_dates": len(a), "right_dates": len(b),
            "common_dates": len(rows), "per_date": rows,
            "cash_note": "Unlisted capital remains cash; weights are not normalized."}


def assess_candidate(catalog, candidate: dict, evidence: dict, *, mechanism_path=None) -> dict:
    components = candidate.get("component_keys")
    if not isinstance(components, list) or not components:
        raise ValueError("candidate requires nonempty component_keys")
    if len(set(components)) != len(components) or any(key not in catalog["cards"] for key in components):
        raise ValueError("unknown or duplicate exact component identity")
    markets = []
    for key in components:
        market = catalog["cards"][key]["market"]
        markets.extend(market if isinstance(market, list) else [market])
    known = {market for market in markets if market}
    if len(known) > 1:
        raise ValueError("cross-market candidate requires separate design")
    scope = candidate.get("scope") or {}
    if known and scope.get("market") not in known:
        raise ValueError("candidate market conflicts with component market")
    metadata_issues = []
    for key in components:
        card = catalog["cards"][key]
        for field in ("market", "assets", "uses", "family", "financial_meaning", "horizon"):
            value = card.get(field)
            if value is None or value == "" or value == []:
                metadata_issues.append(f"{key}:{field}:unknown")
        for field, expected in (("market", scope.get("market")),
                                ("assets", scope.get("asset_type")),
                                ("uses", scope.get("purpose"))):
            value = card.get(field)
            values = value if isinstance(value, list) else [value]
            if expected and value not in (None, [], "") and expected not in values:
                metadata_issues.append(f"{key}:{field}:scope_mismatch")
        if card.get("meaning_status") == "source_description_not_reviewed_mechanism":
            metadata_issues.append(f"{key}:financial_meaning:source_description_unreviewed")
    if candidate.get("mode") not in ("joint_selection", "strategy_allocation"):
        raise ValueError("unsupported candidate mode")
    if not isinstance(candidate.get("financial_hypothesis"), str) or not candidate["financial_hypothesis"].strip():
        raise ValueError("financial hypothesis required")
    if not isinstance(candidate.get("competing_explanation"), str) or not candidate["competing_explanation"].strip():
        raise ValueError("competing explanation required")
    rules = candidate.get("rules") or {}
    missing_rules = [field for field in RULE_FIELDS if not isinstance(rules.get(field), str) or not rules[field].strip()]
    for field in ("market", "asset_type", "purpose", "universe_id", "frequency", "currency"):
        if not isinstance(scope.get(field), str) or not scope[field].strip():
            missing_rules.append("scope." + field)
    checks = evidence.get("checks") or {}
    for field in CHECK_FIELDS:
        if field not in checks or type(checks[field]) not in (bool, type(None)):
            raise ValueError(f"invalid or absent check: {field}")
    root = Path(catalog["root"])
    declared_check_bindings = evidence.get("check_bindings") or {}
    checked_bindings = {}
    unqualified = []
    for field in CHECK_FIELDS:
        items = declared_check_bindings.get(field) or []
        if not isinstance(items, list):
            raise ValueError(f"check_bindings.{field} must be a list")
        verified = []
        for item in items:
            path = Path(item["path"])
            verified.append(_binding(path if path.is_absolute() else root / path,
                                     root, item["sha256"]))
        checked_bindings[field] = verified
        if checks[field] is not True or not verified:
            unqualified.append(field)
    prior = evidence.get("prior_results") or []
    prior_bindings = []
    for item in prior:
        path = Path(item["path"])
        prior_bindings.append(_binding(path if path.is_absolute() else root / path,
                                       root, item["sha256"]))
    relationships = evidence.get("relationships") or {}
    mechanism = review_mechanism(root, mechanism_path, expected_candidate=candidate)
    state = "blocked_inputs" if missing_rules or unqualified or metadata_issues else "qualified_for_research_design"
    mechanism_status = mechanism["status"]
    new_research_status = (
        "ready_for_manual_review" if mechanism_status == "complete_for_manual_review" and
        state == "qualified_for_research_design" else
        "blocked_inputs" if state == "blocked_inputs" else
        f"mechanism_{mechanism_status}"
    )
    return {"candidate": candidate, "evidence": evidence,
            "component_keys": components,
            "component_source_bindings": {key: catalog["cards"][key]["source_bindings"] for key in components},
            "metadata_issues": metadata_issues,
            "verified_check_bindings": checked_bindings,
            "prior_result_bindings": prior_bindings,
            "reuse_existing_results": bool(prior),
            "missing_rules": missing_rules, "unqualified_checks": unqualified,
            "missing_relationships": [name for name in RELATIONSHIPS if name not in relationships],
            "state": state, "mechanism_review": mechanism,
            "new_research_status": new_research_status,
            "forward_eligible": False,
            "note": "Relationship values and prior performance do not confer research or trading approval."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cat = sub.add_parser("catalog")
    cat.add_argument("--root", required=True)
    cat.add_argument("--profiles")
    cat.add_argument("--osap-manifest")
    for field in ("term", "market", "family", "purpose"):
        cat.add_argument("--" + field)
    cat.add_argument("--limit", type=int, default=50)
    context = sub.add_parser("context")
    context.add_argument("--root", required=True)
    context.add_argument("--term", action="append", default=[])
    context.add_argument("--definition-ref", action="append", default=[])
    context.add_argument("--reference-ref", action="append", default=[])
    context.add_argument("--case-id", action="append", default=[])
    context.add_argument("--limit", type=int, default=6)
    review = sub.add_parser("review")
    review.add_argument("--root", required=True)
    review.add_argument("--profiles")
    review.add_argument("--osap-manifest")
    review.add_argument("--request", required=True)
    review.add_argument("--mechanism")
    review.add_argument("--require-mechanism", action="store_true")
    mechanism = sub.add_parser("mechanism-review")
    mechanism.add_argument("--root", required=True)
    mechanism.add_argument("--request", required=True)
    portfolio = sub.add_parser("portfolio-review", help="Compare saved monthly gross/net returns")
    portfolio.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    if args.command == "portfolio-review":
        from lei_signal.research import incremental_portfolio_review

        return incremental_portfolio_review.main(["--request", args.request])
    if args.command == "mechanism-review":
        result = review_mechanism(args.root, args.request)
    elif args.command == "context":
        result = preparation.build_context(args.root, definition_refs=args.definition_ref,
                                           terms=args.term, reference_refs=args.reference_ref,
                                           case_ids=args.case_id, limit=args.limit)
    else:
        catalog = build_catalog(args.root, args.profiles, args.osap_manifest)
        if args.command == "catalog":
            result = {"catalog_sources": catalog["source_bindings"],
                      "validation_status": catalog["validation_status"],
                      **query_catalog(catalog, args.term, args.market, args.family,
                                      args.purpose, args.limit)}
        else:
            request_path = Path(args.request)
            request_binding = _binding(request_path)
            request = _read(request_path)
            result = assess_candidate(catalog, request["candidate"], request["evidence"],
                                      mechanism_path=args.mechanism)
            result["request_binding"] = request_binding
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if args.command == "mechanism-review" and result["status"] != "complete_for_manual_review":
        raise SystemExit(1)
    if args.command == "review" and args.require_mechanism and result["new_research_status"] != "ready_for_manual_review":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
