"""Read-only context for designing a research question; never authorizes execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from lei_signal.research import definitions


ROOT = Path(__file__).resolve().parents[3]
STANDARDS = "docs/research/current-standards.json"
CASES = "docs/research/methods/research-method-cases/cases"
PROMPTS = [
    "相信什么金融现象，适用哪些资产与情形？",
    "为何可能关联目标？这是待检验假设，不是已经证明的原因。",
    "准确计算式、单位、方向是什么，与邻近变体有何区别？",
    "观察值当时何时可知，何时形成决定，何时能够行动？",
    "什么是正例和反例，缺资料及未发生的情形如何保留？",
    "哪些结果会削弱或否定这个想法，结论允许覆盖多大范围？",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bind(root: Path, relative: str, declared: str | None = None) -> dict:
    """Resolve only files inside root, including after symlink resolution."""
    result = {"path": relative, "declared_sha256": declared, "actual_sha256": None}
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        result["status"] = "outside_root"
        return result
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        result["status"] = "outside_root"
    elif not path.is_file():
        result["status"] = "missing"
    else:
        result["actual_sha256"] = _sha(path)
        result["status"] = ("present" if declared is None else
                            "matched" if result["actual_sha256"] == declared else "drift")
        if declared is None:
            result["qualification_note"] = "actual fingerprint only; no declared source anchor"
    return result


def _definition_sources(root: Path, registry: dict, card: dict) -> list[dict]:
    bindings = []
    for item in card["sources"]:
        source = registry["sources"].get(item)
        if source is not None:
            binding = _bind(root, source["path"], source["sha256"])
            binding["source_key"] = item
        elif "/" in item:
            binding = _bind(root, item)
        else:
            binding = {"source_key": item, "status": "unknown_source_key"}
        bindings.append(binding)
    return bindings


def _case_text(case: dict) -> dict[str, str]:
    keys = ("id", "title", "problem", "scope", "object_states", "failure_mode")
    return {key: json.dumps(case.get(key, ""), ensure_ascii=False) for key in keys}


def build_context(root, definition_refs=(), terms=(), case_ids=(), limit=6):
    """Return deterministic discovery context; no model, network, or research run."""
    root = Path(root).resolve()
    if not definition_refs and not case_ids and not any(
        isinstance(term, str) and term.strip() for term in terms
    ):
        raise ValueError("at least one definition_ref, nonblank term, or case_id is required")
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    standards_binding = _bind(root, STANDARDS)
    if standards_binding["status"] != "present":
        raise ValueError("current standards missing or outside root")
    standards = json.loads((root / STANDARDS).read_text(encoding="utf-8"))
    registry_path = standards["definition_registry"]
    registry_binding = _bind(root, registry_path)
    if registry_binding["status"] != "present":
        raise ValueError("definition registry missing or outside root")
    registry = definitions.load_registry(root / registry_path)
    refs = list(dict.fromkeys(definition_refs))
    selected = []
    seen = set()

    def visit(ref):
        if ref in seen:
            return
        card = definitions.resolve(registry, ref)
        seen.add(ref)
        selected.append({"ref": ref, "card": card,
                         "source_bindings": _definition_sources(root, registry, card)})
        for dependency in card["dependencies"]:
            visit(dependency)

    for ref in refs:
        visit(ref)

    needles = [term.strip().casefold() for term in terms if isinstance(term, str) and term.strip()]
    for item in selected:
        card = item["card"]
        needles.extend([card["id"].casefold(), card["name"].casefold()])
    needles = list(dict.fromkeys(needles))
    explicit = set(case_ids)
    base = root / CASES
    found = []
    scanned = 0
    issues = []
    resolved_base = base.resolve()
    search_available = resolved_base.is_relative_to(root) and resolved_base.is_dir()
    if not search_available:
        issues.append({"path": CASES, "status": "case_library_unavailable",
                       "reason": "outside_root" if not resolved_base.is_relative_to(root)
                       else "missing_or_not_directory"})
    for path in sorted(base.glob("*.json")) if search_available else ():
        scanned += 1
        case_binding = _bind(root, str(path.relative_to(root)))
        if case_binding["status"] != "present":
            issues.append(case_binding)
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        fields = _case_text(case)
        reasons = [f"{key}:{needle}" for needle in needles for key, value in fields.items()
                   if needle in value.casefold()]
        if case["id"] in explicit:
            reasons.insert(0, "explicit_case_id")
        if reasons:
            found.append((case, reasons, path))
    found.sort(key=lambda entry: (entry[0]["id"] not in explicit, entry[0]["id"]))
    missing_ids = sorted(explicit - {case["id"] for case, _, _ in found})
    chosen = []
    for case, reasons, path in found[:limit]:
        chosen.append({**case, "match_reasons": reasons,
                       "case_binding": _bind(root, str(path.relative_to(root))),
                       "source_bindings": [_bind(root, source) for source in case.get("references", [])]})
    return {
        "schema": "research-preparation-context/1.0", "execution_authorized": False,
        "definition_status": "resolved_exact" if refs else "idea_definition_only",
        "definitions": selected, "cases": chosen,
        "case_search": {"search_available": search_available,
                        "scanned_count": scanned, "matched_count": len(found),
                        "truncated_count": max(0, len(found) - limit),
                        "undisplayed_ids": [case["id"] for case, _, _ in found[limit:]],
                        "missing_requested_ids": missing_ids,
                        "no_match_note": ("案例库不可用，本次未完成检索；不能据此判断没有风险。"
                                          if not search_available else
                                          "无命中不等于没有风险；可用准确案例ID补查。"
                                          if not found else "")},
        "source_bindings": [standards_binding, registry_binding],
        "issues": issues,
        "financial_review_prompts": PROMPTS,
        "handoff": "将人工判断写回原合同的 claim_mapping、controller_review、source_refs 和 sources；文字匹配不代表语义理解或方法获批准。",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--definition-ref", action="append", default=[])
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args(argv)
    print(json.dumps(build_context(args.root, args.definition_ref, args.term, args.case_id,
                                   args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
