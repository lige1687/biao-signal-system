"""Read saved LLM evidence for optional diagnostics; never call a model or trade."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .component_diagnosis import _pairs, _pointer

MAX_BYTES = 1024 * 1024


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def _read_json(root, relative, expected_sha=None):
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("repository-relative evidence path required")
    requested = Path(relative)
    path = (root / requested).resolve()
    if requested.is_absolute() or ".." in requested.parts or not path.is_relative_to(root):
        raise ValueError("evidence path must remain inside root")
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError(f"evidence unavailable: {relative}") from exc
    if len(raw) > MAX_BYTES:
        raise ValueError("evidence exceeds 1 MiB review bound")
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and expected_sha != sha:
        raise ValueError("evidence SHA-256 mismatch")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, RecursionError) as exc:
        raise ValueError("invalid JSON evidence") from exc
    return value, {"path": relative, "sha256": sha, "bytes": len(raw),
                   "status": "matched" if expected_sha is not None else "read"}


def read_evidence(root, reference):
    """Return a JSON value and current source binding; identity is not truth."""
    if not isinstance(reference, dict):
        raise ValueError("evidence reference object required")
    sha = reference.get("sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("lowercase SHA-256 required")
    value, binding = _read_json(root, reference.get("path"), sha)
    pointer = reference.get("pointer")
    try:
        selected = _pointer(value, pointer)
    except (ValueError, IndexError, KeyError, TypeError, OverflowError) as exc:
        raise ValueError("evidence JSON pointer does not resolve") from exc
    binding["pointer"] = pointer
    return selected, binding


def review_outputs(root, request):
    """Dispatch only the requested saved-output checks, retaining missing parts."""
    result = {"schema": "llm-output-review-result/1", "status": "blocked",
              "execution_authorized": False, "model_called": False,
              "financial_effect_evaluated": False, "errors": [],
              "perturbation": {"status": "not_requested"},
              "timing": {"status": "not_requested"}}
    if not isinstance(request, dict) or request.get("schema") != "llm-output-review/1":
        result["errors"].append("requires llm-output-review/1 object")
        return result
    sections = [name for name in ("perturbation", "timing") if name in request]
    if not sections:
        result["errors"].append("at least one diagnostic must be requested")
        return result
    for name in sections:
        try:
            if name == "perturbation":
                from .llm_perturbation_review import review_perturbations

                result[name] = review_perturbations(root, request[name])
            else:
                from .llm_timing_review import review_timing

                result[name] = review_timing(root, request[name])
        except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
            result[name] = {"status": "blocked", "errors": [str(exc)]}
    if all(result[name].get("status") != "blocked" for name in sections):
        result["status"] = "reviewed_with_declared_limits"
    return result


def review_file(root, relative):
    """Read a repository-local request without silently following other roots."""
    try:
        request, binding = _read_json(root, relative)
    except ValueError as exc:
        return {"schema": "llm-output-review-result/1", "status": "blocked",
                "execution_authorized": False, "model_called": False,
                "financial_effect_evaluated": False, "errors": [str(exc)]}
    result = review_outputs(root, request)
    result["request_binding"] = binding
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    result = review_file(args.root, args.request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
