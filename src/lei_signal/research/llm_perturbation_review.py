"""Source-bound comparisons of saved LLM outputs; no model execution or causality test."""

import math
import re
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

from .llm_output_review import read_evidence

_CONTEXT = (
    "task_id",
    "model_id",
    "model_version",
    "prompt_template_sha256",
    "settings_sha256",
    "as_of",
    "entity",
    "period",
    "output_unit",
)
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")


def _number(value, *, string_only=False):
    if isinstance(value, bool) or (string_only and not isinstance(value, str)):
        raise ValueError(
            "requires a finite decimal string" if string_only else "requires a finite number"
        )
    if isinstance(value, str):
        if len(value) > 128 or not _DECIMAL.fullmatch(value):
            raise ValueError("requires a finite decimal string of at most 128 characters")
    elif not isinstance(value, (int, float)):
        raise ValueError("requires a finite number")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("invalid decimal") from exc
    if not number.is_finite():
        raise ValueError("requires a finite number")
    return number


def _record(value):
    if not isinstance(value, dict) or value.get("data_mode") not in ("real", "synthetic"):
        raise ValueError("data_mode must be real or synthetic")
    if value.get("answer_origin") != "model":
        raise ValueError(
            "answer_origin must be model; fallback or unknown answers are not controls"
        )
    context = value.get("context")
    if not isinstance(context, dict):
        raise ValueError("context is missing")
    for field in _CONTEXT:
        if not isinstance(context.get(field), str) or not context[field].strip():
            raise ValueError(f"context.{field} is missing or unknown")
        if context[field].strip().lower() in ("unknown", "null", "none", "n/a"):
            raise ValueError(f"context.{field} is unknown")
    for field in ("prompt_template_sha256", "settings_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", context[field]):
            raise ValueError(f"context.{field} must be a SHA-256")
    inputs = value.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("inputs must be a nonempty numeric mapping")
    for field, number in inputs.items():
        if not isinstance(field, str) or not field.strip():
            raise ValueError("input field must be a nonempty string")
        _number(number, string_only=True)
    output = value.get("output")
    if not isinstance(output, dict):
        raise ValueError("output is missing")
    if not isinstance(output.get("score"), (int, float)) or isinstance(output["score"], bool):
        raise ValueError("output.score must be a finite JSON number")
    score = _number(output["score"])
    if not math.isfinite(float(score)):
        raise ValueError("output.score is not finite")
    for field in ("label", "raw_answer"):
        if not isinstance(output.get(field), str) or not output[field].strip():
            raise ValueError(f"output.{field} is missing")
    return value


def _difference(baseline, other):
    delta = float(_number(other["output"]["score"]) - _number(baseline["output"]["score"]))
    if not math.isfinite(delta):
        raise ValueError("score difference is not finite")
    return {
        "score_delta": delta,
        "label_flip": other["output"]["label"] != baseline["output"]["label"],
    }


def _compare(records, transformation):
    baseline, variant, repeat = (records[k] for k in ("baseline", "perturbed", "unchanged_repeat"))
    for key in ("context", "data_mode"):
        if baseline[key] != variant[key] or baseline[key] != repeat[key]:
            raise ValueError(f"{key} differs across saved outputs")
    if repeat["inputs"] != baseline["inputs"]:
        raise ValueError("unchanged_repeat inputs differ from baseline")
    if set(variant["inputs"]) != set(baseline["inputs"]):
        raise ValueError("perturbed input fields differ from baseline")
    if not isinstance(transformation, dict):
        raise ValueError("transformation is missing")
    fields = transformation.get("fields")
    if (
        not isinstance(fields, list)
        or not fields
        or any(not isinstance(f, str) or not f.strip() for f in fields)
        or len(set(fields)) != len(fields)
        or not set(fields) <= set(baseline["inputs"])
    ):
        raise ValueError("transformation.fields must be unique existing input names")
    semantics = transformation.get("semantic_review")
    if (
        not isinstance(semantics, dict)
        or semantics.get("status") != "reviewed"
        or not isinstance(semantics.get("reason"), str)
        or not semantics["reason"].strip()
    ):
        raise ValueError("human semantic_review with reason is required")
    absolute = _number(transformation.get("max_absolute_change"))
    relative = _number(transformation.get("max_relative_change"))
    if absolute < 0 or relative < 0:
        raise ValueError("perturbation limits must be nonnegative")
    changes = []
    for field, text in baseline["inputs"].items():
        changed = text != variant["inputs"][field]
        if changed and field not in fields:
            raise ValueError(f"unallowed input changed: {field}")
        a, b = _number(text), _number(variant["inputs"][field])
        delta = abs(b - a)
        ratio = delta / abs(a) if a else (Decimal(0) if not delta else None)
        if field in fields:
            if delta > absolute or ratio is None or ratio > relative:
                raise ValueError(
                    f"perturbation exceeds declared limits or undefined relative change: {field}"
                )
            changes.append(
                {
                    "field": field,
                    "absolute_change": str(delta),
                    "relative_change": str(ratio),
                    "representation_changed": changed,
                }
            )
    if not any(change["representation_changed"] for change in changes):
        raise ValueError("perturbed inputs contain no allowed representation change")
    return {
        "perturbation": _difference(baseline, variant),
        "unchanged_repeat": _difference(baseline, repeat),
        "input_changes": changes,
        "semantic_preservation": "human_declared_not_certified",
        "same_model_settings_context": True,
        "data_mode": baseline["data_mode"],
        "context": baseline["context"],
    }


def _source_triple(pair):
    if not isinstance(pair, dict):
        return None
    sources = []
    for role in ("baseline", "perturbed", "unchanged_repeat"):
        ref = pair.get(role)
        if not isinstance(ref, dict):
            return None
        sha, pointer = ref.get("sha256"), ref.get("pointer")
        if not isinstance(sha, str) or not isinstance(pointer, str):
            return None
        sources.append((sha, pointer))
    return tuple(sources)


def _summarize(items, requested_count):
    by_mode = {
        mode: {
            "requested_pairs": 0,
            "comparable_pairs": 0,
            "blocked_pairs": 0,
            "perturbation_comparisons": 0,
            "repeat_comparisons": 0,
            "label_flip_count": 0,
            "repeat_label_flip_count": 0,
        }
        for mode in ("real", "synthetic", "unknown")
    }
    for item in items:
        group = by_mode[item.get("data_mode", "unknown")]
        group["requested_pairs"] += 1
        if item["status"] == "comparable":
            group["comparable_pairs"] += 1
            group["perturbation_comparisons"] += 1
            group["repeat_comparisons"] += 1
            group["label_flip_count"] += item["perturbation"]["label_flip"]
            group["repeat_label_flip_count"] += item["unchanged_repeat"]["label_flip"]
        else:
            group["blocked_pairs"] += 1
    unread = requested_count - len(items)
    by_mode["unknown"]["requested_pairs"] += unread
    by_mode["unknown"]["blocked_pairs"] += unread
    comparable_count = sum(group["comparable_pairs"] for group in by_mode.values())
    return {
        "totals_scope": "request_processing_only",
        "requested_pairs": requested_count,
        "comparable_pairs": comparable_count,
        "blocked_pairs": requested_count - comparable_count,
        "by_data_mode": by_mode,
    }


def review_perturbations(root, request):
    """Keep invalid pairs in denominators; comparable means structural controls only.

    Each ref uses read_evidence's repository-contained path/SHA/JSON-pointer binding.
    A result never authorizes execution or identifies memorization or leakage.
    """
    result = {
        "schema": "llm-perturbation-review-result/1",
        "status": "blocked",
        "errors": [],
        "pairs": [],
        "summary": {},
        "limitations": [
            "Compares saved score/label declarations; "
            "does not validate their extraction from raw_answer.",
            "Semantic preservation is a human declaration, "
            "not established by small numeric changes.",
            "Unchanged-input output variation is reported separately; "
            "it does not identify memorization or leakage.",
            "Comparable is a structural control status, not scientific or financial certification.",
            "Distinct evidence references do not certify independent model invocations.",
        ],
        "boundary": {
            name: False
            for name in (
                "execution_authorized",
                "memory_causality_certified",
                "leakage_certified",
                "predictive_accuracy_evaluated",
                "investment_returns_evaluated",
                "repeat_invocation_independence_certified",
            )
        },
    }
    pairs = request.get("pairs") if isinstance(request, dict) else None
    if not isinstance(request, dict) or request.get("schema") != "llm-perturbation-review/1":
        result["errors"].append("schema must be llm-perturbation-review/1")
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= 100:
        result["errors"].append("pairs must contain 1 to 100 saved-output pairs")
    if result["errors"]:
        result["summary"] = _summarize([], len(pairs) if isinstance(pairs, list) else 0)
        return result
    ids = Counter(
        p.get("id") for p in pairs if isinstance(p, dict) and isinstance(p.get("id"), str)
    )
    triples = Counter(_source_triple(p) for p in pairs if _source_triple(p) is not None)
    for index, pair in enumerate(pairs):
        item = {
            "id": pair.get("id") if isinstance(pair, dict) else None,
            "index": index,
            "status": "blocked",
            "errors": [],
            "bindings": {},
            "perturbation": None,
            "unchanged_repeat": None,
        }
        result["pairs"].append(item)
        if not isinstance(pair, dict):
            item["errors"].append("pair must be an object")
            continue
        identifier = pair.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            item["errors"].append("id must be a nonempty string")
        elif ids[identifier] > 1:
            item["errors"].append("duplicate pair id")
        triple = _source_triple(pair)
        if triple is not None and triples[triple] > 1:
            item["errors"].append("duplicate saved-output source triple")
        records = {}
        declared_modes = []
        for role in ("baseline", "perturbed", "unchanged_repeat"):
            try:
                ref = pair.get(role)
                if not isinstance(ref, dict) or not all(
                    k in ref for k in ("path", "sha256", "pointer")
                ):
                    raise ValueError("source path, sha256 and pointer are required")
                selected, binding = read_evidence(root, ref)
                item["bindings"][role] = binding
                declared_modes.append(
                    selected.get("data_mode") if isinstance(selected, dict) else None
                )
                records[role] = _record(selected)
            except ValueError as exc:
                item["errors"].append(f"{role}: {exc}")
        item["data_mode"] = (
            declared_modes[0]
            if len(declared_modes) == 3
            and declared_modes[0] in ("real", "synthetic")
            and all(mode == declared_modes[0] for mode in declared_modes)
            else "unknown"
        )
        if len(records) == 3:
            baseline_binding = item["bindings"]["baseline"]
            repeat_binding = item["bindings"]["unchanged_repeat"]
            if (Path(root) / baseline_binding["path"]).resolve() == (
                Path(root) / repeat_binding["path"]
            ).resolve() and baseline_binding["pointer"] == repeat_binding["pointer"]:
                item["errors"].append("baseline source reused as unchanged_repeat")
            try:
                with localcontext() as context:
                    context.prec = 512
                    comparison = _compare(records, pair.get("transformation"))
                if not item["errors"]:
                    item.update(comparison, status="comparable")
            except ValueError as exc:
                item["errors"].append(str(exc))
    result["summary"] = _summarize(result["pairs"], len(pairs))
    result["status"] = (
        "complete_for_manual_review"
        if result["summary"]["comparable_pairs"] == len(pairs)
        else "blocked"
    )
    return result
