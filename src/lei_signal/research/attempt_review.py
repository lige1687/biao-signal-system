"""Read-only evidence index over existing research journals and named study files.

This module never creates a journal, qualifies a result, or follows output links.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGERS = Path("docs/experiments/raw/research-workflow-ledgers-2026-09-29")
STUDY_FILES = (
    "contract.json",
    "manifest.json",
    "checkpoint.json",
    "inputs.json",
    "attempts.json",
    "freeze.json",
    "completion.json",
    "design.json",
    "result-locator.json",
)
INDEPENDENT_FILES = (
    "contract.json",
    "inputs.json",
    "attempts.json",
    "freeze.json",
    "completion.json",
    "design.json",
    "result-locator.json",
)
MAX_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 500
MAX_LEDGER_CANDIDATES = 100
MAX_SOURCE_CHECKS = 500


def _inside(root: Path, value: str | Path) -> tuple[Path, str]:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"path must be repository-relative: {value}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"path resolves outside repository: {value}")
    return target, str(relative)


def _file(root: Path, value: str | Path) -> tuple[dict, bytes | None]:
    target, relative = _inside(root, value)
    binding = {"path": relative, "sha256": None, "status": "unknown"}
    if not target.is_file():
        binding["status"] = "missing"
        return binding, None
    size = target.stat().st_size
    binding["size_bytes"] = size
    if size > MAX_BYTES:
        binding["status"] = "truncated_size_limit"
        return binding, None
    data = target.read_bytes()
    binding.update(sha256=hashlib.sha256(data).hexdigest(), status="read")
    return binding, data


def _json(root: Path, value: str | Path, expected=dict) -> tuple[dict, dict | list | None]:
    binding, raw = _file(root, value)
    if raw is None:
        return binding, None
    try:
        result = json.loads(raw)
        if not isinstance(result, expected):
            raise ValueError(f"top level is not {expected.__name__}")
    except (ValueError, UnicodeDecodeError) as exc:
        binding.update(status="invalid_json", error=str(exc))
        return binding, None
    return binding, result


def _family_path(family: str) -> Path:
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be nonblank")
    encoded = json.dumps(family, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return LEDGERS / hashlib.sha256(encoded.encode()).hexdigest()[:24] / "attempts.jsonl"


def _events(root: Path, relative: Path, term: str | None = None) -> dict:
    binding, raw = _file(root, relative)
    result = {
        "source": binding,
        "family": None,
        "budget": None,
        "events": [],
        "event_count": 0,
        "errors": [],
        "complete": raw is not None,
        "read_complete": raw is not None,
        "evidence_identity_complete": False,
        "seen_history": "unknown",
        "runs": [],
    }
    if raw is None:
        return result
    starts, finishes = {}, {}
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict) or not isinstance(item.get("event"), str):
                raise ValueError("event object with event name required")
        except (ValueError, UnicodeDecodeError) as exc:
            result["errors"].append({"line": number, "error": str(exc)})
            result["complete"] = False
            result["read_complete"] = False
            continue
        if item["event"] == "family":
            if (
                not isinstance(item.get("family"), str)
                or not item["family"].strip()
                or not isinstance(item.get("budget"), dict)
            ):
                result["errors"].append({"line": number, "error": "invalid_family_header"})
                result["complete"] = False
            if result["family"] is None:
                result["family"] = item.get("family")
                result["budget"] = item.get("budget")
            elif item.get("family") != result["family"] or item.get("budget") != result["budget"]:
                result["errors"].append({"line": number, "error": "conflicting family header"})
                result["complete"] = False
        if item["event"] == "start" and item.get("run_id"):
            starts.setdefault(item["run_id"], []).append((number, item))
        if item["event"] == "finish" and item.get("run_id"):
            finishes.setdefault(item["run_id"], []).append((number, item))
        if item.get("results_seen") is True:
            result["seen_history"] = "yes"
        result["event_count"] += 1
        if len(result["events"]) < MAX_EVENTS:
            result["events"].append(
                {
                    "line": number,
                    **{
                        key: item.get(key)
                        for key in (
                            "event",
                            "run_id",
                            "classification",
                            "status",
                            "scientific_key",
                            "time",
                            "results_seen",
                            "receipt_sha256",
                            "data_sha256",
                            "out",
                            "seconds",
                        )
                        if key in item
                    },
                }
            )
    if result["family"] is None:
        result["errors"].append({"error": "missing_family_header"})
        result["complete"] = False
    elif isinstance(result["family"], str) and relative != _family_path(result["family"]):
        result["errors"].append({"error": "family_hash_header_mismatch"})
        result["complete"] = False
    if result["event_count"] > MAX_EVENTS:
        result["complete"] = False
        result["errors"].append(
            {
                "error": "event_display_limit",
                "undisplayed_events": result["event_count"] - MAX_EVENTS,
            }
        )
    for run_id, entries in starts.items():
        last_finish = finishes.get(run_id, [])
        if len(entries) != 1 or len(last_finish) != 1:
            result["errors"].append(
                {"line": entries[0][0], "error": f"unsettled_or_duplicate_run:{run_id}"}
            )
            result["complete"] = False
        result["runs"].append(
            {
                "run_id": run_id,
                "start_count": len(entries),
                "finish_count": len(last_finish),
                "status": last_finish[-1][1].get("status", "unknown")
                if last_finish
                else "unsettled",
                "classification": entries[-1][1].get("classification", "unknown"),
            }
        )
    for run_id, entries in finishes.items():
        if run_id not in starts:
            result["errors"].append(
                {"line": entries[0][0], "error": f"finish_without_start:{run_id}"}
            )
            result["complete"] = False
    result["evidence_identity_complete"] = result["complete"]
    if result["seen_history"] == "unknown" and result["complete"]:
        result["seen_history"] = "no_recorded_result_seen"
    if term and term.casefold() not in str(result["family"] or "").casefold():
        result["excluded_by_term"] = True
    return result


def _study(root: Path, value: str) -> dict:
    target, relative = _inside(root, value)
    if target.suffix == ".json" and target.name not in STUDY_FILES:
        raise ValueError("--study accepts only supported named study JSON files")
    names = (
        [relative]
        if target.suffix == ".json"
        else [str(Path(relative) / name) for name in STUDY_FILES]
    )
    files, objects, errors = [], {}, []
    for name in names:
        binding, obj = _json(root, name, list if Path(name).name == "attempts.json" else dict)
        files.append(binding)
        if obj is not None:
            objects[Path(name).name] = obj
        elif binding["status"] not in {"missing"}:
            errors.append(
                {"path": name, "status": binding["status"], "error": binding.get("error")}
            )
    contract = objects.get("contract.json", {})
    manifest = objects.get("manifest.json", {})
    checkpoint = objects.get("checkpoint.json", {})
    inputs = objects.get("inputs.json", {})
    attempts = objects.get("attempts.json", [])
    freeze_record = objects.get("freeze.json", {})
    completion = objects.get("completion.json", {})
    design = objects.get("design.json", {})
    locator = objects.get("result-locator.json", {})
    independent = any(name in objects for name in INDEPENDENT_FILES[1:])
    if independent:
        for name in INDEPENDENT_FILES:
            if name not in objects:
                errors.append(
                    {"path": str(Path(relative) / name), "status": "missing_required_study_file"}
                )
    if len(attempts) > MAX_EVENTS:
        errors.append(
            {
                "path": "attempts.json",
                "status": "attempt_display_limit",
                "undisplayed": len(attempts) - MAX_EVENTS,
            }
        )
    if any(not isinstance(item, dict) for item in attempts):
        errors.append({"path": "attempts.json", "status": "invalid_attempt_entry"})
    history = contract.get("history") if isinstance(contract.get("history"), dict) else {}
    question = contract.get("question") if isinstance(contract.get("question"), dict) else {}
    validation = question.get("validation") if isinstance(question.get("validation"), dict) else {}
    scope = contract.get("scope") if isinstance(contract.get("scope"), (dict, list)) else {}
    bindings = contract.get("bindings") if isinstance(contract.get("bindings"), dict) else {}
    declared_sources = contract.get("sources") if isinstance(contract.get("sources"), list) else []
    evaluator = contract.get("evaluator") if isinstance(contract.get("evaluator"), dict) else {}
    comparators = {
        market: design[market].get("comparators", "unknown")
        for market in ("cn", "us")
        if isinstance(design.get(market), dict)
    }
    baseline = (
        contract.get("baseline") or evaluator.get("baseline_features") or comparators or "unknown"
    )
    period = contract.get("period") or (
        {"start": contract.get("target_start"), "end": contract.get("target_end")}
        if contract.get("target_start") or contract.get("target_end")
        else "unknown"
    )
    not_applicable = contract.get("not_applicable_methods")
    if not isinstance(not_applicable, list):
        not_applicable = []
    source_checks = []
    declared_checks = [("source", source) for source in declared_sources]
    if independent:
        if not isinstance(inputs, dict) or not inputs:
            declared_checks.append(("input", None))
        else:
            declared_checks.extend(("input", source) for source in inputs.values())
        frozen_files = freeze_record.get("code_and_design")
        if not isinstance(frozen_files, list) or not frozen_files:
            declared_checks.append(("frozen_code_design", None))
        else:
            declared_checks.extend(("frozen_code_design", source) for source in frozen_files)
    binding_files = bindings.get("files")
    if binding_files is not None:
        if not isinstance(binding_files, dict):
            declared_checks.append(("binding_file", None))
        else:
            declared_checks.extend(
                ("binding_file", {"path": path, "sha256": sha})
                for path, sha in binding_files.items()
            )
    for kind, source in declared_checks[:MAX_SOURCE_CHECKS]:
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            source_checks.append({"kind": kind, "status": "unrecognized_source_entry"})
            continue
        try:
            actual, _ = _file(root, source["path"])
        except ValueError:
            actual = {"path": source["path"], "sha256": None, "status": "outside_root"}
        declared = source.get("sha256")
        actual["declared_sha256"] = declared
        actual["kind"] = kind
        if actual["status"] == "read" and isinstance(declared, str) and len(declared) == 64:
            actual["status"] = "matched" if actual["sha256"] == declared else "drift"
        source_checks.append(actual)
    if len(declared_checks) > MAX_SOURCE_CHECKS:
        source_checks.append(
            {"status": "source_check_limit", "unchecked": len(declared_checks) - MAX_SOURCE_CHECKS}
        )
    binding_status = (
        "drift"
        if any(s["status"] == "drift" for s in source_checks)
        else "matched"
        if source_checks and all(s["status"] == "matched" for s in source_checks)
        else "unknown"
    )
    read_complete = bool(objects) and not errors
    evidence_identity_complete = (
        "contract.json" in objects and read_complete and binding_status == "matched"
    )
    return {
        "path": relative,
        "files": files,
        "errors": errors,
        "complete": evidence_identity_complete,
        "read_complete": read_complete,
        "evidence_identity_complete": evidence_identity_complete,
        "id": contract.get("task_id")
        or contract.get("run_id")
        or manifest.get("run_id")
        or "unknown",
        "family": history.get("family", "unknown"),
        "run_id": contract.get("run_id")
        or manifest.get("run_id")
        or checkpoint.get("run_id")
        or "unknown",
        "status": checkpoint.get("status")
        or manifest.get("status")
        or completion.get("status")
        or contract.get("status")
        or "unknown",
        "question": contract["question"]
        if isinstance(contract.get("question"), str)
        else question.get("text", "unknown"),
        "scope": scope or "unknown",
        "baseline": baseline,
        "objects": contract.get("definition_refs")
        or contract.get("object_refs")
        or contract.get("definition_ref")
        or contract.get("definition")
        or "unknown",
        "period": period
        if period != "unknown"
        else {
            market: design[market].get("periods", "unknown")
            for market in ("cn", "us")
            if isinstance(design.get(market), dict)
        }
        or "unknown",
        "declared_validation_stage": validation.get("stage", "unknown"),
        "results_seen": checkpoint.get("results_seen", "unknown"),
        "seen_history_declaration": contract.get("case_selection", "unknown"),
        "all_history_previously_seen_declaration": design.get(
            "all_history_previously_seen", "unknown"
        ),
        "freeze": contract.get("freeze")
        or contract.get("frozen_at")
        or freeze_record.get("frozen_at")
        or "unknown",
        "frozen_at": {
            "contract": contract.get("frozen_at", "unknown"),
            "freeze": freeze_record.get("frozen_at", "unknown"),
        },
        "forward_reference": contract.get("forward") or manifest.get("forward") or "unknown",
        "report_reference": manifest.get("report") or contract.get("report") or "unknown",
        "stop_condition": contract.get("stop") or contract.get("stop_conditions") or "unknown",
        "execution_perturbation": contract.get("execution_perturbation") or "unknown",
        "risk_sources": contract.get("risk_sources") or "unknown",
        "not_applicable_methods": not_applicable,
        "binding_status": binding_status,
        "declared_bindings": bindings or "unknown",
        "source_checks": source_checks,
        "attempts": attempts[:MAX_EVENTS],
        "attempt_count": len(attempts) if "attempts.json" in objects else "unknown",
        "attempt_scope": "declared_study_attempts_only"
        if "attempts.json" in objects
        else "unknown",
        "core_batches_used_declaration": completion.get("core_batches_used", "unknown"),
        "design": {
            "comparators": comparators,
            "periods": {
                market: design[market].get("periods", "unknown")
                for market in ("cn", "us")
                if isinstance(design.get(market), dict)
            },
            "cn_primary_months": design.get("cn", {}).get("primary_months", "unknown")
            if isinstance(design.get("cn"), dict)
            else "unknown",
            "cn_down_periods": design.get("cn", {}).get("down_periods", "unknown")
            if isinstance(design.get("cn"), dict)
            else "unknown",
            "acceptance": design.get("acceptance", "unknown"),
        },
        "result_locator": {
            "status": locator.get("status", "unknown"),
            "commands": locator.get("commands", "unknown"),
            "output_reference": locator.get("output", "unknown"),
            "output_followed": False,
            "files_declared_count": len(locator["files"])
            if isinstance(locator.get("files"), list)
            else "unknown",
        },
        "scientific_effect_status": "not_evaluated_by_index",
    }


def review(root=ROOT, *, family=None, term=None, studies=()) -> dict:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("root must be a directory")
    if not family and not term and not studies:
        raise ValueError("provide --family, --term or --study")
    if term is not None and not str(term).strip():
        raise ValueError("term must be nonblank")
    ledgers, errors = [], []
    if family:
        ledger = _events(root, _family_path(family))
        if ledger["family"] not in (None, family):
            ledger["errors"].append({"error": "family_hash_header_mismatch"})
            ledger["complete"] = False
        ledgers.append(ledger)
    elif term:
        base, _ = _inside(root, LEDGERS)
        candidates = sorted(base.glob("*/attempts.jsonl")) if base.is_dir() else []
        if len(candidates) > MAX_LEDGER_CANDIDATES:
            errors.append(
                {
                    "error": "ledger_candidate_limit",
                    "undisplayed_candidates": len(candidates) - MAX_LEDGER_CANDIDATES,
                }
            )
        for path in candidates[:MAX_LEDGER_CANDIDATES]:
            relative = path.relative_to(root)
            try:
                if not path.resolve().is_relative_to(root):
                    raise ValueError("ledger candidate resolves outside repository")
                with path.open("rb") as stream:
                    prefix = stream.read(65536)
                header = None
                for line in prefix.splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if isinstance(entry, dict) and entry.get("event") == "family":
                        header = entry.get("family")
                        break
                if header is None:
                    errors.append(
                        {"path": str(relative), "error": "family_header_not_found_in_prefix"}
                    )
                elif term.casefold() in str(header).casefold():
                    ledgers.append(_events(root, relative))
            except (OSError, ValueError) as exc:
                errors.append({"path": str(relative), "error": str(exc)})
    indexed_studies = [_study(root, study) for study in studies]
    all_sources_complete = (
        bool(ledgers or indexed_studies)
        and not errors
        and all(x["complete"] for x in ledgers)
        and all(x["complete"] for x in indexed_studies)
    )

    def mark(present: bool, refs: list[str], name: str) -> dict:
        na = [x["path"] for x in indexed_studies if name in x["not_applicable_methods"]]
        if not present and na:
            return {"status": "declared_not_applicable", "references": na}
        return {
            "status": "declared_reference"
            if present
            else "incomplete_source"
            if refs
            else "missing_or_unknown",
            "references": refs,
        }

    methods = {
        "risk_source_separation": mark(
            any(x["risk_sources"] != "unknown" for x in indexed_studies),
            [x["path"] for x in indexed_studies if x["risk_sources"] != "unknown"],
            "risk_source_separation",
        ),
        "all_attempts": mark(
            (bool(ledgers) and all(x["complete"] for x in ledgers))
            or any(isinstance(x["attempt_count"], int) for x in indexed_studies),
            [x["source"]["path"] for x in ledgers]
            + [x["path"] for x in indexed_studies if isinstance(x["attempt_count"], int)],
            "all_attempts",
        ),
        "execution_perturbation": mark(
            any(x["execution_perturbation"] != "unknown" for x in indexed_studies),
            [x["path"] for x in indexed_studies if x["execution_perturbation"] != "unknown"],
            "execution_perturbation",
        ),
        "strong_baseline": mark(
            any(x["baseline"] != "unknown" for x in indexed_studies),
            [x["path"] for x in indexed_studies if x["baseline"] != "unknown"],
            "strong_baseline",
        ),
        "predeclared_failure": mark(
            any(x["stop_condition"] != "unknown" for x in indexed_studies),
            [x["path"] for x in indexed_studies if x["stop_condition"] != "unknown"],
            "predeclared_failure",
        ),
        "historical_forward_separation": mark(
            any(
                x["declared_validation_stage"] != "unknown" or x["forward_reference"] != "unknown"
                for x in indexed_studies
            ),
            [
                x["path"]
                for x in indexed_studies
                if x["declared_validation_stage"] != "unknown"
                or x["forward_reference"] != "unknown"
            ],
            "historical_forward_separation",
        ),
    }
    return {
        "schema": "research-attempt-review/1",
        "read_only": True,
        "complete": all_sources_complete,
        "query": {"family": family, "term": term, "studies": list(studies)},
        "ledgers": ledgers,
        "studies": indexed_studies,
        "methods": methods,
        "errors": errors,
        "note": (
            "References show declarations or a bounded journal index only. "
            "They do not verify forward observation, a complete experiment universe, "
            "or a passed method; missing is unknown, not zero attempts."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--family")
    parser.add_argument("--term")
    parser.add_argument("--study", action="append", default=[])
    args = parser.parse_args(argv)
    print(
        json.dumps(
            review(args.root, family=args.family, term=args.term, studies=args.study),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
