"""Preserve preparation context and verify its declared local evidence for handoff.

This adapter neither delegates work nor interprets budgets or research permission.
Identity/structure checks do not certify facts, completeness, or worker comprehension.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from .component_diagnosis import _pointer
from .llm_output_review import MAX_BYTES, _read_json, read_evidence

# Actual binding slots emitted by preparation, practice_context, attempt_review,
# component_diagnosis and saved-output review. Arbitrary path strings are not refs.
_BINDING_SLOTS = frozenset(
    {
        "source",
        "sources",
        "source_bindings",
        "source_binding",
        "request_binding",
        "catalog_binding",
        "case_binding",
        "registry_source",
        "binding",
        "files",
        "inputs",
        "frozen_files",
        "source_refs",
        "source_checks",
        "code_and_design",
        "context_binding",
        "contract_binding",
    }
)
_HASH_FIELDS = ("sha256", "declared_sha256", "actual_sha256")


def _path(root, relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("source requires a repository-relative path")
    requested = Path(relative)
    path = (root / requested).resolve()
    if requested.is_absolute() or ".." in requested.parts or not path.is_relative_to(root):
        raise ValueError(f"unsafe source path: {relative}")
    return path


def _verify_source(root, value, pointer, refs, caveats):
    if not isinstance(value, dict):
        return
    if "path" not in value:
        if value.get("status") or value.get("source_key"):
            caveats.append({"status": "source_identity_unknown", "binding": copy.deepcopy(value)})
        return
    relative = value["path"]
    path = _path(root, relative)
    hashes = [value[key] for key in _HASH_FIELDS if value.get(key) is not None]
    if not hashes:
        caveats.append({"status": "source_unread_or_unbound", "binding": copy.deepcopy(value)})
        return
    if (
        any(
            not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in hashes
        )
        or len(set(hashes)) != 1
    ):
        raise ValueError(f"invalid or conflicting source hashes: {relative}")
    expected = hashes[0]
    if "pointer" in value and not isinstance(value["pointer"], str):
        raise ValueError(f"invalid source pointer: {relative}")
    selected_pointer = value.get("pointer") or pointer
    if not isinstance(selected_pointer, str):
        raise ValueError(f"invalid source pointer: {relative}")
    reference = {"path": str(Path(relative)), "sha256": expected, "pointer": selected_pointer}
    if not path.is_file():
        raise ValueError(f"bound source must be a regular file: {relative}")
    if selected_pointer:
        read_evidence(root, reference)
    else:
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
        except OSError as exc:
            raise ValueError(f"bound source unavailable: {relative}") from exc
        if len(raw) > MAX_BYTES:
            raise ValueError(f"bound source exceeds 1 MiB: {relative}")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"bound source SHA-256 drift: {relative}")
    refs[(reference["path"], expected, selected_pointer)] = reference
    if len(refs) > 100:
        raise ValueError("source binding count exceeds 100")


def _collect(root, obj, refs, caveats, errors):
    stack = [(obj, "", "", 0)]
    visited = 0
    while stack:
        node, slot, inherited_pointer, depth = stack.pop()
        visited += 1
        if visited > 20000 or depth > 80:
            errors.append(
                "source identity traversal bound exceeded; context preserved, not truncated"
            )
            return
        if isinstance(node, dict):
            if node.get("status") in ("truncated_value", "source_check_limit") and (
                slot in _BINDING_SLOTS or slot == "review"
            ):
                errors.append("critical source identity unavailable under truncated review/binding")
                continue
            if slot in _BINDING_SLOTS:
                try:
                    _verify_source(root, node, inherited_pointer, refs, caveats)
                except (ValueError, OSError) as exc:
                    errors.append(str(exc))
            if slot == "files" and "path" not in node:
                # attempt_review also accepts contract.bindings.files as path->SHA.
                for relative, digest in node.items():
                    if isinstance(digest, str):
                        try:
                            _verify_source(
                                root, {"path": relative, "sha256": digest}, "", refs, caveats
                            )
                        except (ValueError, OSError) as exc:
                            errors.append(str(exc))
            for key, value in node.items():
                # Declaration pointers refer to the enclosing source document.
                field = node.get("field")
                pointer = (
                    field
                    if key == "source" and isinstance(field, str) and field.startswith("/")
                    else ""
                )
                child_slot = (
                    slot
                    if slot in ("inputs", "source_refs", "source_bindings", "sources", "files")
                    and "path" not in node
                    else key
                )
                stack.append((value, child_slot, pointer, depth + 1))
        elif isinstance(node, list):
            stack.extend((value, slot, inherited_pointer, depth + 1) for value in node)


def _required_sources(root, preparation, contract, refs, caveats):
    controls = contract.get("research_controls")
    if not isinstance(controls, dict) or "required_source_pointers" not in controls:
        return []
    pointers = controls["required_source_pointers"]
    if not isinstance(pointers, list) or len(pointers) > 1000:
        raise ValueError("required_source_pointers must be a list of at most 1000 JSON pointers")
    if any(not isinstance(pointer, str) for pointer in pointers) or len(set(pointers)) != len(
        pointers
    ):
        raise ValueError("required_source_pointers must contain unique JSON pointer strings")
    checks = []
    for pointer in pointers:
        try:
            binding = _pointer(preparation, pointer)
        except (ValueError, IndexError, KeyError, TypeError, OverflowError) as exc:
            raise ValueError(f"required source pointer cannot resolve: {pointer}") from exc
        if (
            not isinstance(binding, dict)
            or "path" not in binding
            or binding.get("status") in ("truncated_value", "source_check_limit")
            or not any(binding.get(field) is not None for field in _HASH_FIELDS)
        ):
            raise ValueError(f"required source binding missing, truncated or unbound: {pointer}")
        _verify_source(root, binding, "", refs, caveats)
        checks.append(
            {
                "preparation_pointer": pointer,
                "status": "verified",
                "binding": copy.deepcopy(binding),
            }
        )
    return checks


def build_handoff_context(root, preparation, contract_file):
    """Return a lossless context plus verified refs; failures block, never authorize.

    ``preparation`` is the existing saved preparation object. ``contract_file`` is
    a root-relative JSON path. No inference of a remaining budget or implicit
    research controls is made. Unread unanchored sources remain explicit caveats;
    unsafe or changed anchored evidence blocks the handoff.
    """
    output = {
        "schema": "research-delegation-context/1",
        "status": "blocked",
        "execution_authorized": False,
        "practice_context": "unknown",
        "preparation": {},
        "control": {
            "contract": "unknown",
            "contract_binding": "unknown",
            "research_controls": "unknown",
        },
        "source_bindings": [],
        "required_source_checks": [],
        "caveats": [],
        "errors": [],
        "limitations": [
            "Source identity is checked, not truth, completeness, authorization or comprehension.",
            "History, budgets, errors and truncation retain their original meanings.",
            "No new budget, remaining amount, execution or research permission is inferred.",
            "Only structured binding slots are followed; arbitrary text paths are not sources.",
            "Unanchored unread sources remain unknown; bound sources must be local and <=1 MiB.",
        ],
    }
    refs = {}
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("root must be a directory")
        if not isinstance(preparation, dict):
            raise ValueError("preparation must be an object")
        # Validate JSON serializability/finiteness without modifying unknown values.
        json.dumps(preparation, allow_nan=False)
        output["practice_context"] = copy.deepcopy(preparation.get("practice_context", "unknown"))
        output["preparation"] = copy.deepcopy(
            {key: value for key, value in preparation.items() if key != "practice_context"}
        )
        if preparation.get("schema") != "research-preparation-context/1.0":
            raise ValueError("unsupported preparation schema")
        if not _path(root, contract_file).is_file():
            raise ValueError("delegation contract must be a regular file")
        contract, binding = _read_json(root, contract_file)
        if not isinstance(contract, dict):
            raise ValueError("delegation contract must be an object")
        json.dumps(contract, allow_nan=False)
        binding["pointer"] = ""
        output["control"] = {
            "contract": contract,
            "contract_binding": binding,
            "research_controls": copy.deepcopy(contract.get("research_controls", "unknown")),
        }
        refs[(binding["path"], binding["sha256"], "")] = {
            "path": binding["path"],
            "sha256": binding["sha256"],
            "pointer": "",
        }
        _collect(root, preparation, refs, output["caveats"], output["errors"])
        _collect(root, contract, refs, output["caveats"], output["errors"])
        output["required_source_checks"] = _required_sources(
            root, preparation, contract, refs, output["caveats"]
        )
        if "practice_context" not in preparation:
            output["caveats"].append({"status": "practice_context_unknown"})
        if "research_controls" not in contract:
            output["caveats"].append({"status": "research_controls_unknown"})
        # Contract identity must remain stable through source collection.
        repeated, repeated_binding = _read_json(root, contract_file, binding["sha256"])
        if repeated != contract or repeated_binding["sha256"] != binding["sha256"]:
            raise ValueError("delegation contract drift")
        for reference in list(refs.values()):
            _verify_source(root, reference, "", refs, output["caveats"])
        output["source_bindings"] = sorted(
            refs.values(), key=lambda ref: (ref["path"], ref["pointer"])
        )
        if not output["errors"]:
            output["status"] = "ready_with_declared_limits"
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        output["errors"].append(str(exc))
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--preparation", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        if not _path(root, args.preparation).is_file():
            raise ValueError("saved preparation must be a regular file")
        preparation, binding = _read_json(root, args.preparation)
        binding["pointer"] = ""
        result = build_handoff_context(args.root, preparation, args.contract)
        result["preparation_binding"] = binding
        reference = {key: binding[key] for key in ("path", "sha256", "pointer")}
        if reference not in result["source_bindings"]:
            result["source_bindings"].append(reference)
        if len(result["source_bindings"]) > 100:
            result["status"] = "blocked"
            result["errors"].append("source binding count exceeds 100 including preparation")
    except (ValueError, OSError, TypeError) as exc:
        result = {
            "schema": "research-delegation-context/1",
            "status": "blocked",
            "execution_authorized": False,
            "errors": [str(exc)],
            "source_bindings": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
