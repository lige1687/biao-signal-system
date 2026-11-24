"""Read valid definition/dependency closures for display without changing research admission.

Malformed objects stay in the authoritative file. This view cannot qualify a run:
the research runner continues using definitions.load_registry on the original.
"""
from __future__ import annotations

import json
from pathlib import Path

from lei_signal.research import definitions


def load_description_registry(path: Path) -> tuple[dict, dict[str, str]]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("invalid definition registry")
    # Validate the shared envelope first, without allowing bad object identities
    # or duplicate identities to be silently dropped from the view.
    envelope = {**registry, "objects": [], "models": []}
    envelope.pop("research_references", None)
    try:
        definitions.validate_registry(envelope)
    except ValueError as exc:
        if str(exc) != "empty registry":
            raise
    objects = registry.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("empty or invalid definition objects")
    indexed = {}
    for obj in objects:
        if not isinstance(obj, dict):
            raise ValueError("invalid definition object")
        identity, version = obj.get("id"), obj.get("version")
        if not isinstance(identity, str) or not isinstance(version, str):
            raise ValueError("invalid definition identity")
        ref = f"{identity}@{version}"
        if ref in indexed:
            raise ValueError(f"duplicate identity: {ref}")
        indexed[ref] = obj

    def closure(ref: str, included: dict, active: set):
        if ref in active:
            raise ValueError(f"cyclic dependency: {ref}")
        if ref in included:
            return
        if ref not in indexed:
            raise ValueError(f"unresolved dependency/version: {ref}")
        obj = indexed[ref]
        card = definitions._expand(registry, obj)
        deps = card.get("dependencies")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise ValueError(f"invalid dependencies: {ref}")
        active.add(ref)
        for dep in deps:
            closure(dep, included, active)
        active.remove(ref)
        included[ref] = obj

    errors = {}
    for ref in indexed:
        try:
            selected = {}
            closure(ref, selected, set())
            definitions.validate_registry({**envelope, "objects": list(selected.values())})
        except (ValueError, KeyError, TypeError) as exc:
            errors[ref] = str(exc)
    view = {**registry, "objects": [obj for ref, obj in indexed.items() if ref not in errors]}
    # All shared models/research references and the union of admitted objects
    # must still pass the original complete validator. This is not a repair.
    definitions.validate_registry(view)
    return view, errors
