"""Load one qualified historical price overlay into memory, without statistics.

The vendor response remains immutable and retains its returned adjustment flags.
Callers may pass the returned inputs to the pinned lowfreq_discovery._evaluate;
this module never calls it, _aggregate, or run_study.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from importlib.util import find_spec
from pathlib import Path

from lei_signal.research.lowfreq_input_guard import inspect_contract

FIELDS = ("open", "high", "low", "close", "preclose")
TARGET = "sz.001914"
LEGACY = "sz.000043"
FACTOR = Decimal("0.91352")
EXPECTED_ROWS = 1560
EXPECTED_SOURCES = 600
EXPECTED_BASE_ROWS = 1852185


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bound(binding, label):
    try:
        path = Path(binding["path"])
        _require(_sha(path) == binding["sha256"], f"changed {label} SHA-256")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid bound {label}: {exc}") from exc


def _rows(doc, label):
    fields = doc.get("fields")
    data = doc.get("data") if "data" in doc else doc.get("rows")
    _require(isinstance(fields, list) and all(isinstance(x, str) for x in fields)
             and len(fields) == len(set(fields)) and isinstance(data, list), f"bad {label} table")
    result = []
    for i, values in enumerate(data):
        _require(isinstance(values, list) and len(values) == len(fields), f"bad {label} row {i}")
        result.append(dict(zip(fields, values)))
    return result


def _unique_dates(doc, label):
    result = {}
    for row in _rows(doc, label):
        day = row.get("date")
        _require(isinstance(day, str) and day not in result, f"duplicate/missing {label} date {day}")
        result[day] = row
    return result


def _positive_number(value, label):
    try:
        number = Decimal(value)
    except (TypeError, InvalidOperation) as exc:
        raise ValueError(f"invalid derived price {label}") from exc
    _require(number.is_finite() and number > 0, f"invalid derived price {label}")
    return number


def load_derived_sources(manifest):
    """Return (design, selected, membership, calendar, sources, qualification).

    ``manifest`` is a path or object with schema lowfreq-derived-price-input/1,
    SHA-bound base_contract, overlay, legacy_adjusted, evaluator and prior_review.
    The evaluator is imported only after all source checks pass.
    """
    spec = json.loads(Path(manifest).read_text(encoding="utf-8")) if isinstance(manifest, (str, Path)) else manifest
    _require(isinstance(spec, dict) and spec.get("schema") == "lowfreq-derived-price-input/1", "wrong derived manifest")
    for name in ("base_contract", "overlay", "legacy_adjusted", "evaluator", "prior_review"):
        _require(isinstance(spec.get(name), dict) and {"path", "sha256"} <= set(spec[name]), f"missing {name} binding")
    evaluator_path = Path(spec["evaluator"]["path"]).resolve()
    module_spec = find_spec("lei_signal.research.lowfreq_discovery")
    _require(module_spec is not None and module_spec.origin is not None and
             evaluator_path == Path(module_spec.origin).resolve() and
             _sha(evaluator_path) == spec["evaluator"]["sha256"], "evaluator code changed")
    review = _bound(spec["prior_review"], "prior review")
    _require(review.get("status") == "derived_source_consistency_checked_evaluator_integration_required"
             and review.get("market_statistics_calls") == 0, "prior source review not qualified")
    base = _bound(spec["base_contract"], "base contract")
    overlay = _bound(spec["overlay"], "overlay")
    legacy_doc = _bound(spec["legacy_adjusted"], "legacy source")
    for item in spec.get("bindings", []):
        _require(_sha(item["path"]) == item["sha256"], f"changed supporting binding: {item['path']}")
    original_check = inspect_contract(spec["base_contract"]["path"])
    blockers = original_check["blockers"]
    _require(original_check["source_count"] == EXPECTED_SOURCES and
             original_check["row_count"] == EXPECTED_BASE_ROWS and
             set(blockers) == {"returned_adjustflag"} and
             blockers["returned_adjustflag"]["count"] == EXPECTED_ROWS and
             blockers["returned_adjustflag"].get("by_code") == {TARGET: EXPECTED_ROWS},
             "original 600-source inspection differs from the sole known flag break")
    _require(base.get("schema") == "lowfreq-evaluator-contract/1", "wrong base schema")
    sources_spec = base["sources"]
    _require(len(sources_spec) == EXPECTED_SOURCES and len({s["code"] for s in sources_spec}) == EXPECTED_SOURCES,
             "wrong source inventory")
    target_spec = next((s for s in sources_spec if s["code"] == TARGET), None)
    _require(target_spec is not None and overlay.get("source") == target_spec, "overlay does not bind original vendor source")
    _require(overlay.get("schema") == "research.price-correction-overlay/1"
             and overlay.get("vendor_original") is False
             and overlay.get("original_source_adjustflag_preserved") is True
             and overlay.get("normalization") == "0.91352"
             and overlay.get("allowed_fields") == list(FIELDS), "invalid derived price declaration")
    original_doc = _bound(target_spec, "original target source")
    original = _unique_dates(original_doc, "original")
    legacy = _unique_dates(legacy_doc, "legacy")
    _require(legacy_doc.get("error_code") == "0", "legacy response failed")
    changes = overlay.get("changes")
    _require(isinstance(changes, list) and len(changes) == EXPECTED_ROWS, "wrong overlay row count")
    target_days = {day for day, row in original.items() if row.get("adjustflag") == "3"}
    change_days = [row.get("date") for row in changes if isinstance(row, dict)]
    _require(len(change_days) == EXPECTED_ROWS and len(set(change_days)) == EXPECTED_ROWS
             and set(change_days) == target_days, "overlay does not cover precisely the source flag break")
    projected_doc = deepcopy(original_doc)
    projected = _unique_dates(projected_doc, "projected")
    allowed_keys = {"date", "canonical_code", "source_adjustflag", "source_price_values",
                    "legacy_code", "legacy_adjusted_values", "derived_adjusted_values", "formula"}
    for change in changes:
        _require(set(change) == allowed_keys, "overlay contains missing or activity fields")
        day = change["date"]
        current, earlier, target = original[day], legacy.get(day), projected[day]
        _require(earlier is not None and change["canonical_code"] == current.get("code") == TARGET
                 and change["legacy_code"] == earlier.get("code") == LEGACY
                 and change["source_adjustflag"] == current.get("adjustflag") == "3"
                 and earlier.get("adjustflag") == "2"
                 and change["formula"] == "legacy_adjusted_value * 0.91352", f"source identity/formula differs: {day}")
        for name in ("source_price_values", "legacy_adjusted_values", "derived_adjusted_values"):
            _require(isinstance(change[name], dict) and set(change[name]) == set(FIELDS), f"wrong overlay fields: {day}")
        for field in FIELDS:
            _require(change["source_price_values"][field] == current[field]
                     and change["legacy_adjusted_values"][field] == earlier[field],
                     f"source price mismatch: {day}:{field}")
            value = _positive_number(change["derived_adjusted_values"][field], f"{day}:{field}")
            _require(value == _positive_number(earlier[field], f"legacy:{day}:{field}") * FACTOR,
                     f"derived formula mismatch: {day}:{field}")
            target[field] = str(value)
        prices = {field: Decimal(target[field]) for field in FIELDS}
        _require(prices["low"] <= min(prices["open"], prices["close"])
                 and prices["high"] >= max(prices["open"], prices["close"]), f"derived OHLC inconsistent: {day}")
    _require(all(projected[day][key] == value for day, row in original.items()
                 for key, value in row.items() if key not in FIELDS or day not in target_days),
             "non-price or untargeted row changed")
    date_index = projected_doc["fields"].index("date")
    projected_doc["data"] = [[projected[row[date_index]][field] for field in projected_doc["fields"]]
                             for row in projected_doc["data"]]
    # Re-read all bound bytes after inspection to catch changes during this load.
    for item in (spec["base_contract"], spec["overlay"], spec["legacy_adjusted"], spec["prior_review"],
                 spec["evaluator"], *spec.get("bindings", []), base["design"], base["cohort"], base["calendar"],
                 *sources_spec):
        _require(_sha(item["path"]) == item["sha256"], f"bound input changed during load: {item['path']}")
    from lei_signal.research import lowfreq_discovery as evaluator
    design = _bound(base["design"], "design")
    cohort = _bound(base["cohort"], "cohort")
    calendar_doc = _bound(base["calendar"], "calendar")
    selected, _, membership = evaluator._cohort(cohort, design["universe"]["asof"], design["universe"]["sample_size"])
    calendar = evaluator._calendar(calendar_doc)
    _require(set(selected) == {s["code"] for s in sources_spec}, "frozen cohort mismatch")
    sources = {item["code"]: {"data": projected_doc if item["code"] == TARGET else _bound(item, item["code"]),
                               "request": deepcopy(item["request"])} for item in sources_spec}
    for item in sources_spec:
        _require(_sha(item["path"]) == item["sha256"], f"source changed during materialization: {item['code']}")
    qualification = {"status": "conditional_derived_historical_only", "vendor_original": False,
                     "original_input_status": original_check["status"],
                     "source_count": original_check["source_count"],
                     "row_count": original_check["row_count"],
                     "warnings": original_check.get("warnings", {}),
                     "original_flag_break": {"code": TARGET, "rows": EXPECTED_ROWS},
                     "derived_price_cells": EXPECTED_ROWS * len(FIELDS),
                     "derived_price_basis": overlay["derived_price_basis"],
                     "formula": "legacy_adjusted_value * 0.91352",
                     "source_adjustflag_preserved": True,
                     "provenance": {"base_contract_sha256": spec["base_contract"]["sha256"],
                                    "overlay_sha256": spec["overlay"]["sha256"],
                                    "legacy_adjusted_sha256": spec["legacy_adjusted"]["sha256"],
                                    "evaluator_sha256": spec["evaluator"]["sha256"],
                                    "guard_sha256": _sha(Path(__file__).with_name("lowfreq_input_guard.py")),
                                    "prior_review_sha256": spec["prior_review"]["sha256"]},
                     "limits": ["historical adjusted-quotation diagnostic only", "no nominal-price, size, actual fill, or production claim"]}
    return design, selected, membership, calendar, sources, qualification
