"""Read saved evidence before considering one conditional component comparison.

This module only checks attachment bindings and declared comparisons. It neither
runs experiments nor establishes return validity, scientific validity or cause.
Judgment directions/criteria are declarations from the original contract;
there are no financial thresholds here.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

CONTEXT_FIELDS = (
    "object_id",
    "period",
    "opportunity_set_id",
    "signal_version",
    "benchmark_id",
    "capital_rules",
    "cost_rules",
    "execution_rules",
    "exit_rules",
    "other_rules",
)
COMPONENT_FIELDS = {
    "exit": {"exit_rules"},
    "capital_execution": {"capital_rules", "execution_rules"},
}
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _pointer(document, pointer):
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError("JSON pointer must be empty or start with /")
    if not pointer:
        return document
    current = document
    for token in pointer[1:].split("/"):
        # Reject invalid RFC 6901 escapes instead of interpreting them loosely.
        rest = token.replace("~1", "").replace("~0", "")
        if "~" in rest:
            raise ValueError("invalid JSON pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValueError("invalid JSON pointer array index")
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise ValueError("JSON pointer traverses a scalar")
    return current


def _measured(metrics):
    """Require explicit measured numeric output; zero/negative values are valid."""
    if isinstance(metrics, dict) and metrics:
        return all(_measured(value) for value in metrics.values())
    if isinstance(metrics, list) and metrics:
        return all(_measured(value) for value in metrics)
    return type(metrics) in (int, float) and math.isfinite(metrics)


def review_diagnosis(root, request: dict) -> dict:
    """Review one read-only component-diagnosis/1 request under ``root``.

    Each evidence reference is {path, sha256, pointer, value}. The selected saved
    value contains context, result={evaluated:true,metrics:{numeric outputs}}, and
    judgment={direction,criterion,contract_id}. Context requires CONTEXT_FIELDS.
    ``signal`` and ``account`` are references; an optional ``comparison`` has
    component, baseline and variant references. Without a reusable comparison,
    ``suspected_component`` selects at most one manual review plan.
    """
    root = Path(root).resolve()
    output = {
        "schema": "component-diagnosis-review/1",
        "status": "blocked",
        "issues": [],
        "conflict_detected": None,
        "source_bindings": [],
        "planned_comparisons": [],
        "reused_comparisons": [],
        "max_comparisons": 1,
        "run_authorized": False,
        "executed": False,
        "returns_verified": False,
        "causality_verified": False,
        "scientific_validity_verified": False,
        "limitations": [
            "Directions and criteria are original-contract declarations; "
            "financial judgments are not computed.",
            "Evidence binding and matched context do not establish return validity or causality.",
            "No experiment was run or authorized by this review.",
        ],
    }

    def issue(field, message):
        output["issues"].append({"field": field, "message": message})

    def evidence(ref, field):
        try:
            if not isinstance(ref, dict):
                raise ValueError("evidence reference required")
            supplied = ref.get("path")
            if not isinstance(supplied, str) or not supplied.strip():
                raise ValueError("evidence path required")
            path = (root / supplied).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("missing or outside-root evidence path")
            if path.stat().st_size > MAX_EVIDENCE_BYTES:
                raise ValueError("evidence exceeds review size limit")
            raw = path.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            if sha != ref.get("sha256"):
                raise ValueError("evidence sha256 mismatch")
            document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
            actual = _pointer(document, ref.get("pointer"))
            if "value" not in ref or _canonical(actual) != _canonical(ref["value"]):
                raise ValueError("evidence pointer/value mismatch")
            if not isinstance(actual, dict):
                raise ValueError("selected evidence must be an object")
            context = actual.get("context")
            if not isinstance(context, dict):
                raise ValueError("context object required")
            for key in CONTEXT_FIELDS:
                if (
                    not isinstance(context.get(key), str)
                    or not context[key].strip()
                    or context[key] in {"unknown", "not_evaluated"}
                ):
                    raise ValueError(f"context.{key} requires a known frozen identity")
            result = actual.get("result")
            if (
                not isinstance(result, dict)
                or result.get("evaluated") is not True
                or not isinstance(result.get("metrics"), dict)
                or not _measured(result["metrics"])
            ):
                raise ValueError(
                    "result requires evaluated:true and nonempty finite numeric metrics"
                )
            if "status" in result and result["status"] in {
                "unknown",
                "not_evaluated",
                "pending",
                "failed",
                "incomplete",
                "",
                None,
            }:
                raise ValueError("saved result status is not evaluated")
            judgment = actual.get("judgment")
            if not isinstance(judgment, dict) or judgment.get("direction") not in {
                "positive",
                "negative",
                "neutral",
            }:
                raise ValueError("bound judgment direction required")
            for key in ("criterion", "contract_id"):
                if not isinstance(judgment.get(key), str) or not judgment[key].strip():
                    raise ValueError(f"judgment.{key} requires the original contract declaration")
            output["source_bindings"].append(
                {
                    "field": field,
                    "path": str(path),
                    "sha256": sha,
                    "pointer": ref["pointer"],
                    "value": actual,
                }
            )
            return actual
        except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
            issue(field, str(exc))
            return None

    if not isinstance(request, dict) or request.get("schema") != "component-diagnosis/1":
        issue("schema", "requires component-diagnosis/1 object")
        return output
    signal = evidence(request.get("signal"), "signal")
    account = evidence(request.get("account"), "account")
    if signal is None or account is None:
        return output
    if signal["context"] != account["context"]:
        issue("context", "signal/account frozen contexts differ")
    if signal["judgment"]["contract_id"] != account["judgment"]["contract_id"]:
        issue("judgment.contract_id", "signal/account original contracts differ")
    if output["issues"]:
        return output
    # A declared positive improvement conflicting with no improvement (neutral)
    # is also diagnostic; two layers showing no improvement need no diagnosis.
    conflict = (signal["judgment"]["direction"] == "positive") != (
        account["judgment"]["direction"] == "positive"
    )
    output["conflict_detected"] = conflict
    if not conflict:
        output["status"] = "not_needed"
        return output

    comparison = request.get("comparison")
    if "comparisons" in request:
        issue("comparisons", "only one comparison object is supported")
        return output
    component = (
        comparison.get("component")
        if isinstance(comparison, dict)
        else request.get("suspected_component")
    )
    if not isinstance(component, str) or component not in COMPONENT_FIELDS:
        issue("component", "select exactly one of exit or capital_execution")
        return output
    suspected = request.get("suspected_component")
    if suspected is not None and suspected != component:
        issue(
            "suspected_component", "must select the same single component as the saved comparison"
        )
        return output
    frozen = sorted(set(account["context"]) - COMPONENT_FIELDS[component])
    if comparison is not None:
        if not isinstance(comparison, dict):
            issue("comparison", "requires one comparison object")
            return output
        baseline = evidence(comparison.get("baseline"), "comparison.baseline")
        variant = evidence(comparison.get("variant"), "comparison.variant")
        if baseline is None or variant is None:
            return output
        base_ref, account_ref = comparison["baseline"], request["account"]
        if Path(root / base_ref["path"]).resolve() != Path(
            root / account_ref["path"]
        ).resolve() or any(
            _canonical(base_ref.get(key)) != _canonical(account_ref.get(key))
            for key in ("sha256", "pointer", "value")
        ):
            issue("comparison.baseline", "must bind the original account evidence")
        # Extra context keys are frozen too, so undeclared changes cannot slip through.
        all_context = set(baseline["context"]) | set(variant["context"])
        for key in sorted(all_context - COMPONENT_FIELDS[component]):
            if baseline["context"].get(key) != variant["context"].get(key):
                issue(f"comparison.context.{key}", "nonselected condition must stay frozen")
        if all(
            baseline["context"][key] == variant["context"][key]
            for key in COMPONENT_FIELDS[component]
        ):
            issue("comparison.component", "selected component has no declared change")
        for key in ("contract_id", "criterion"):
            if baseline["judgment"][key] != variant["judgment"][key]:
                issue(f"comparison.judgment.{key}", "baseline/variant original declarations differ")
        if output["issues"]:
            return output
        output["status"] = "reused_for_manual_review"
        output["reused_comparisons"] = [
            {
                "component": component,
                "frozen_fields": frozen,
                "baseline": base_ref,
                "variant": comparison["variant"],
            }
        ]
        return output
    output["status"] = "planned_for_manual_review"
    output["planned_comparisons"] = [
        {
            "component": component,
            "frozen_fields": frozen,
            "frozen_context": account["context"],
            "baseline": request["account"],
            "requires_separate_run_authorization": True,
        }
    ]
    return output
