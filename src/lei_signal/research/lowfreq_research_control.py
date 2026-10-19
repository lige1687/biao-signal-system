"""Read-only contract/receipt guard for the separate low-frequency stock studies.

CLI: python -m lei_signal.research.lowfreq_research_control --contract FILE
It prints a JSON decision. It does not schedule, reserve atomically, or discover
unlisted history. Existing P1/P2 contracts and the native workflow are untouched.

Contract schema ``lowfreq-research-control/1`` has action ``preflight`` or
``acceptance`` and stage ``qualification``, ``diagnostic``, or ``effect``. Required
SHA-bound JSON files in ``bindings`` are design, source_qualification,
prior_manifest, brief, controller_review; runner is SHA-bound code and selector
is SHA-bound source-only CSV. The design contains ``selector_sha256``. History
contains ``reviewed_history_complete: true`` and SHA-bound attempt JSON files.
An attempt has identity_sha256, stage, status (started/completed/failed/paused);
terminal records need a SHA-bound receipt; completed records also need a
SHA-bound manifest. Brief budget_control has core_max/core_used and
followup_max/followup_used. Controller review binds design_sha256,
qualification_sha256, scientific_design_accepted, effects_authorized and, at
acceptance, result_accepted/result_manifest_sha256. Acceptance binds a result
manifest with status/evidence_status and SHA-bound outputs. A process exit code
is never an acceptance condition.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path

SCHEMA = "lowfreq-research-control/1"
SELECTOR_COLUMNS = frozenset({
    "scope", "month", "decision_date", "code", "industry", "eligibility_status", "score",
    "source_publication_date", "announcement_id", "report_year", "momentum",
    "financial_score", "financial_percentile", "value_ratio", "book_value",
    "market_cap", "price_asof", "source_reason",
})
STAGES = {"qualification", "diagnostic", "effect"}
EVIDENCE = {"supported", "not_supported", "inconclusive", "not_evaluated"}


class ControlError(ValueError):
    pass


def _nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ControlError(f"{name} must be nonempty")
    return value


def _hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _bound(binding, *, json_file=True):
    if not isinstance(binding, dict):
        raise ControlError("missing bound file")
    path = Path(_nonempty(binding.get("path"), "bound path"))
    digest = _nonempty(binding.get("sha256"), "bound SHA256")
    if not path.is_absolute() or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ControlError("binding needs absolute path and lowercase SHA256")
    if not path.is_file() or _hash(path) != digest:
        raise ControlError(f"bound file absent or changed: {path}")
    return path, json.loads(path.read_text(encoding="utf-8")) if json_file else None


def _date(value, name):
    try:
        return date.fromisoformat(_nonempty(value, name))
    except ValueError as exc:
        raise ControlError(f"invalid {name}") from exc


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ControlError(f"{name} must be a nonnegative integer")
    return value


def _identity(value):
    if not isinstance(value, dict):
        raise ControlError("scientific identity missing")
    stable = {key: _nonempty(value.get(key), key) for key in ("question", "definition", "formula")}
    uses = value.get("uses")
    if not isinstance(uses, list) or not uses:
        raise ControlError("scientific uses missing")
    stable["uses"] = sorted({_nonempty(item, "use") for item in uses})
    inputs = value.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise ControlError("scientific inputs missing")
    # The path locates bytes, but a copied identical input cannot reset identity.
    for item in inputs:
        _bound(item, json_file=False)
    stable["inputs"] = sorted(item["sha256"] for item in inputs)
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _qualified_rows(source, selector_path, scopes):
    if source.get("status") not in {"terminal", "pending"} or not isinstance(source.get("records"), list):
        raise ControlError("source qualification state/records missing")
    index = {}
    for row in source["records"]:
        scope = row.get("scope", "")
        if scope not in scopes:
            raise ControlError("source scope not in frozen contract")
        key = (scope, _nonempty(row.get("code"), "source code"), _date(row.get("decision_date"), "decision date"))
        if key in index or row.get("status") not in {"qualified", "unknown"}:
            raise ControlError("duplicate/invalid source qualification")
        publication = row.get("publication_date")
        if row["status"] == "qualified":
            if not publication or _date(publication, "publication date") >= key[2]:
                raise ControlError("qualified source was not public before decision")
        elif publication:
            _date(publication, "unknown source publication date")
        index[key] = row
    with selector_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not set(reader.fieldnames) <= SELECTOR_COLUMNS:
            raise ControlError("selector contains a result/weight/future field or duplicate column")
        if not {"code", "decision_date", "eligibility_status", "score"} <= set(reader.fieldnames):
            raise ControlError("selector lacks qualification columns")
        seen = set()
        for row in reader:
            scope = row.get("scope", "")
            if scope not in scopes:
                raise ControlError("selector scope not in frozen contract")
            key = (scope, _nonempty(row.get("code"), "selector code"), _date(row.get("decision_date"), "selector date"))
            if key in seen or key not in index or row["eligibility_status"] != index[key]["status"]:
                raise ControlError("selector source identity/status mismatch")
            seen.add(key)
            if "source_publication_date" in row and row["source_publication_date"] != (index[key].get("publication_date") or ""):
                raise ControlError("selector publication date differs from source qualification")
            if row["eligibility_status"] == "unknown":
                if row["score"] not in ("", None):
                    raise ControlError("unknown source filled with score")
            else:
                try:
                    if not math.isfinite(float(_nonempty(row["score"], "qualified score"))):
                        raise ValueError()
                except ValueError as exc:
                    raise ControlError("qualified score missing/nonfinite") from exc
    if seen != set(index):
        raise ControlError("selector omitted unknown or qualified source records")
    return {"qualified": sum(r["status"] == "qualified" for r in index.values()),
            "unknown": sum(r["status"] == "unknown" for r in index.values())}


def _attempts(history, identity):
    if history.get("reviewed_history_complete") is not True or not isinstance(history.get("attempts"), list):
        raise ControlError("root-reviewed enumerated attempt history required")
    matching, observed = [], []
    for binding in history["attempts"]:
        _, attempt = _bound(binding)
        if attempt.get("schema") != "lowfreq-research-attempt/1" or attempt.get("stage") not in STAGES:
            raise ControlError("attempt record schema/stage invalid")
        status = attempt.get("status")
        if status not in {"started", "completed", "failed", "paused"}:
            raise ControlError("unknown attempt status")
        if status == "started":
            raise ControlError("unsettled attempt needs reconciliation")
        _, receipt = _bound(attempt.get("receipt"))
        if receipt.get("status") != status:
            raise ControlError("terminal receipt differs from attempt")
        if status == "completed":
            manifest_path, _ = _bound(attempt.get("manifest"))
            if receipt.get("manifest_sha256") != _hash(manifest_path):
                raise ControlError("completed attempt has missing/mismatched result receipt")
        if attempt.get("identity_sha256") == identity:
            matching.append(attempt)
        observed.append(attempt)
    return matching, observed


def check(contract):
    if contract.get("schema") != SCHEMA or contract.get("action") not in {"preflight", "acceptance"} or contract.get("stage") not in STAGES:
        raise ControlError("unsupported contract action/stage")
    stage, action = contract["stage"], contract["action"]
    bindings = contract.get("bindings", {})
    required = {"design", "runner", "source_qualification", "prior_manifest", "brief", "controller_review", "selector"}
    if set(bindings) != required:
        raise ControlError("incomplete/extra immutable bindings")
    loaded = {}
    for name, binding in bindings.items():
        loaded[name] = _bound(binding, json_file=name not in {"runner", "selector"})
    design, source, brief, review = (loaded[k][1] for k in ("design", "source_qualification", "brief", "controller_review"))
    if design.get("selector_sha256") != bindings["selector"]["sha256"]:
        raise ControlError("selector not frozen in scientific design")
    identity = _identity(contract.get("scientific_identity"))
    scopes = contract.get("scopes", [""])
    if not isinstance(scopes, list) or not scopes or len(scopes) != len(set(scopes)) or any(
            not isinstance(scope, str) or (not scope and scopes != [""]) for scope in scopes):
        raise ControlError("frozen scope list invalid")
    counts = _qualified_rows(source, loaded["selector"][0], set(scopes))
    if review.get("design_sha256") != bindings["design"]["sha256"] or review.get("qualification_sha256") != bindings["source_qualification"]["sha256"]:
        raise ControlError("controller acceptance not bound to design/source")
    if stage in {"diagnostic", "effect"} and review.get("scientific_design_accepted") is not True:
        raise ControlError("scientific design not accepted")
    if stage in {"diagnostic", "effect"} and review.get("label_access_authorized") is not True:
        raise ControlError("diagnostic/effect outcome access not authorized")
    if stage == "effect" and (review.get("effects_authorized") is not True or source["status"] != "terminal" or counts["qualified"] == 0):
        raise ControlError("effect lacks authority or qualified terminal source")
    matching, observed = _attempts(contract.get("history", {}), identity)
    limits = brief.get("budget_control")
    if not isinstance(limits, dict):
        raise ControlError("bound brief budget_control missing")
    lane = "core" if stage == "effect" else "followup"
    maximum = _integer(limits.get(f"{lane}_max"), f"{lane}_max")
    used = _integer(limits.get(f"{lane}_used"), f"{lane}_used")
    if used > maximum:
        raise ControlError("used budget exceeds ceiling")
    if used < sum(item["stage"] == stage for item in observed):
        raise ControlError("brief understates enumerated attempted runs")
    if action == "preflight":
        if any(item["status"] == "completed" and item["stage"] == stage for item in matching):
            return {"status": "reuse", "identity_sha256": identity, "source_counts": counts,
                    "limit": "enumerated history only; this guard does not schedule or prevent bypass"}
        if used >= maximum:
            raise ControlError("cumulative brief budget exhausted")
        if stage == "qualification":
            return {"status": "source_work_only", "stage": stage,
                    "identity_sha256": identity, "source_counts": counts,
                    "limit": "source checks never authorize outcome evaluation"}
        return {"status": "eligible_for_separate_execution", "stage": stage,
                "identity_sha256": identity, "source_counts": counts,
                "limit": "read-only; no atomic budget reservation; history completeness is controller-declared"}
    result_path, result = _bound(contract.get("result_manifest"))
    if result.get("schema") != "lowfreq-controlled-result/1" or result.get("stage") != stage or result.get("identity_sha256") != identity:
        raise ControlError("result manifest identity/stage differs")
    outputs = result.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        raise ControlError("result output manifest missing")
    for binding in outputs.values():
        _bound(binding, json_file=False)
    if result.get("evidence_status") not in EVIDENCE or result.get("status") not in {"evaluated", "diagnostic_complete", "qualification_complete", "computed_pending_review", "pending_review"}:
        raise ControlError("explicit result/evidence status required")
    acceptable_status = {"qualification": {"qualification_complete", "computed_pending_review"},
                         "diagnostic": {"diagnostic_complete", "computed_pending_review"},
                         "effect": {"evaluated", "computed_pending_review"}}[stage]
    accepted = (review.get("result_accepted") is True and
                review.get("result_manifest_sha256") == _hash(result_path) and
                result["status"] in acceptable_status and
                result["evidence_status"] != "not_evaluated")
    return {"status": "accepted" if accepted else "pending_review", "stage": stage,
            "evidence_status": result["evidence_status"], "identity_sha256": identity,
            "source_counts": counts, "limit": "receipt integrity and declared acceptance only, not scientific truth"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    args = parser.parse_args()
    try:
        _, contract = _bound({"path": str(args.contract.resolve()), "sha256": _hash(args.contract)})
        result = check(contract)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (ControlError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
