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
    "相对哪一个事前选定的基准才算改善？它与策略的资产池、收益和费用口径是否一致？",
    "谁因什么约束愿意付出这份收益或获得什么服务？优势为何可能持续，还有什么更简单的解释？",
    "哪些证据支持相对收益和机制，哪些旧结果已看过，什么观察会推翻它？",
    "本轮分别能回答因子信息、同股合成或过滤、完整账户中的哪一层？跨层结论还缺哪项直接对照，能否复用旧结果？",
    "若为横截面选股，买入端相对共同基准有多少帮助，坏尾部贡献多少？行业、市值或流动性暴露能否解释，处理前后怎样比较？",
    "信号期限、可得时间、最早成交、持有和换手是否匹配？新增过滤、择时或缓冲相对原规则少亏多少、少赚多少，扣费后还剩什么？",
    "合成或仓位管理相对强单项、简单资金分配及适用的低投入对手有何增量？研究证据、前向观察准备与实盘授权是否分别判断，未测项是否保留未知？",
    "若交付账户收益，月历、费用对账与特殊选股分支有何证据？区分计算错误、事前约束和需解释的变化；可用账户证据预检，但声明自洽不等于来源真实或策略有效。",
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


def _reference_text(reference: dict) -> dict[str, str]:
    """Search only registered descriptive metadata; this does not fetch sources."""
    source = reference.get("source", {})
    if not isinstance(source, dict):
        source = {}
    fields = {
        "id": reference.get("id", ""),
        "name": reference.get("name", ""),
        "aliases": reference.get("aliases", []),
        "source.institution": source.get("institution", ""),
        "source.authors": source.get("authors", []),
    }
    return {key: json.dumps(value, ensure_ascii=False) for key, value in fields.items()}


def _reference_identity(reference: dict) -> str:
    return f"{reference['id']}@{reference['version']}"


def _practice_context(root, *, terms, family, studies, limit, diagnosis_file,
                      llm_review_file=None, account_review_file=None):
    # Loaded here so the original definition resolver remains independently usable.
    from lei_signal.research.practice_context import build_history_context

    history = build_history_context(
        root, terms=terms, family=family, studies=studies, limit=limit,
    ) if terms or family or studies else {
        "status": "not_requested", "matched": [], "read_only": True,
        "note": "No historical query supplied; prior research remains unknown.",
    }
    result = {"history": history,
              "diagnosis": {"status": "not_requested", "run_authorized": False}}
    if diagnosis_file is not None:
        from lei_signal.research.component_diagnosis import review_diagnosis

        relative = Path(diagnosis_file)
        path = (root / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root):
            raise ValueError("diagnosis_file must be a relative path inside root")
        binding = {"path": str(relative), "status": "missing"}
        try:
            with path.open("rb") as stream:
                raw = stream.read(262145)
            if len(raw) > 262144:
                raise ValueError("diagnosis request exceeds 256 KiB")
            binding = {"path": str(relative), "status": "read",
                       "sha256": hashlib.sha256(raw).hexdigest()}
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError("diagnosis request must be an object")
            result["diagnosis"] = review_diagnosis(root, request)
        except (OSError, ValueError) as exc:
            result["diagnosis"] = {"status": "blocked", "run_authorized": False,
                                   "issues": [str(exc)]}
        result["diagnosis"]["request_binding"] = binding
    if llm_review_file is not None:
        from lei_signal.research.llm_output_review import review_file

        result["llm_output_review"] = review_file(root, llm_review_file)
    if account_review_file is not None:
        from lei_signal.research.research_account_evidence_review import review_file

        result["account_evidence_review"] = review_file(root, account_review_file)
    return result


def _with_handoff(root, result, contract_file):
    if contract_file is not None:
        from .delegation_context import build_handoff_context

        result["delegation_context"] = build_handoff_context(root, result, contract_file)
    return result


def build_context(root, definition_refs=(), terms=(), case_ids=(), limit=6,
                  reference_refs=(), *, family=None, studies=(), practice_only=False,
                  diagnosis_file=None, llm_review_file=None, handoff_contract=None,
                  account_review_file=None):
    """Return deterministic discovery context; no model, network, or research run."""
    root = Path(root).resolve()
    if not family and not studies and not diagnosis_file and not llm_review_file and not account_review_file and not handoff_contract and not definition_refs and not reference_refs and not case_ids and not any(
        isinstance(term, str) and term.strip() for term in terms
    ):
        raise ValueError("at least one definition_ref, reference_ref, nonblank term, or case_id is required")
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be a positive integer no greater than 20")
    if practice_only:
        if definition_refs or reference_refs or case_ids:
            raise ValueError("practice_only cannot resolve definitions, references or cases")
        return _with_handoff(root, {
            "schema": "research-preparation-context/1.0", "execution_authorized": False,
            "definition_status": "not_evaluated_practice_only",
            "practice_context": _practice_context(
                root, terms=terms, family=family, studies=studies, limit=limit,
                diagnosis_file=diagnosis_file, llm_review_file=llm_review_file,
                account_review_file=account_review_file,
            ),
            "financial_review_prompts": PROMPTS,
            "handoff": "先核旧结论、适用用途和重开条件，写回原开题；本入口未审查定义或授予运行权限。",
        }, handoff_contract)
    standards_binding = _bind(root, STANDARDS)
    if standards_binding["status"] != "present":
        raise ValueError("current standards missing or outside root")
    standards = json.loads((root / STANDARDS).read_text(encoding="utf-8"))
    registry_path = standards["definition_registry"]
    registry_binding = _bind(root, registry_path)
    if registry_binding["status"] != "present":
        raise ValueError("definition registry missing or outside root")
    registry = definitions.load_registry(root / registry_path)
    references = registry.get("research_references", [])
    reference_by_id = {_reference_identity(item): item for item in references}
    if len(reference_by_id) != len(references):
        raise ValueError("duplicate exact research reference")
    explicit_reference_refs = list(dict.fromkeys(reference_refs))
    for ref in explicit_reference_refs:
        if ref not in reference_by_id:
            raise ValueError(f"unknown exact research reference: {ref}")
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
    reference_matches = []
    for reference in references:
        ref = _reference_identity(reference)
        fields = _reference_text(reference)
        reasons = [f"{field}:{needle}" for needle in needles for field, value in fields.items()
                   if needle in value.casefold()]
        explicit_match = ref in explicit_reference_refs
        if reasons or explicit_match:
            reference_matches.append({
                "ref": ref,
                "card": reference,
                "registered_evidence_status": reference.get("evidence_status", "unknown"),
                "match_reasons": (["explicit_reference_ref"] if explicit_match else []) + reasons,
                "explicit": explicit_match,
            })
    reference_matches.sort(key=lambda item: (not item["explicit"], item["ref"]))
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
    return _with_handoff(root, {
        "schema": "research-preparation-context/1.0", "execution_authorized": False,
        "definition_status": "resolved_exact" if refs else "idea_definition_only",
        "definitions": selected, "cases": chosen,
        "research_references": reference_matches[:limit],
        "reference_search": {
            "registered_count": len(references),
            "matched_count": len(reference_matches),
            "truncated_count": max(0, len(reference_matches) - limit),
            "undisplayed_refs": [item["ref"] for item in reference_matches[limit:]],
            "explicit_refs": explicit_reference_refs,
            "retrieval_scope": "registered_metadata_only",
            "verification_note": "仅返回已有登记；本次未抓取或重新核验来源，不代表已实现或有效。",
            "no_match_note": ("登记表中没有研究参照卡。" if not references else
                              "没有参照卡匹配关键词或准确引用。" if not reference_matches else ""),
        },
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
        "practice_context": _practice_context(
            root, terms=terms or tuple(refs), family=family, studies=studies,
            limit=limit, diagnosis_file=diagnosis_file, llm_review_file=llm_review_file,
            account_review_file=account_review_file,
        ),
        "handoff": "将人工判断写回原合同的 claim_mapping、controller_review、source_refs 和 sources；文字匹配不代表语义理解或方法获批准。",
    }, handoff_contract)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--definition-ref", action="append", default=[])
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--reference-ref", action="append", default=[])
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--family")
    parser.add_argument("--study", action="append", default=[])
    parser.add_argument("--practice-only", action="store_true",
                        help="read prior research/diagnosis without resolving definitions")
    parser.add_argument("--diagnosis-file", help="repository-relative saved diagnosis request")
    parser.add_argument("--llm-review-file", help="repository-relative saved LLM review request")
    parser.add_argument("--account-review-file", help="repository-relative monthly research account evidence; read-only checks")
    parser.add_argument("--handoff-contract", help="repository-relative delegation contract; attach verified context")
    args = parser.parse_args(argv)
    print(json.dumps(build_context(args.root, args.definition_ref, args.term, args.case_id,
                                   args.limit, args.reference_ref, family=args.family,
                                   studies=args.study, practice_only=args.practice_only,
                                   diagnosis_file=args.diagnosis_file,
                                   llm_review_file=args.llm_review_file,
                                   account_review_file=args.account_review_file,
                                   handoff_contract=args.handoff_contract), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
