"""Read-only, source-checked projection of saved research progress.

This module checks provenance and DTO shape. It does not infer scientific merit
from files, run experiments, or update the underlying research records.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


DEFAULT_EVIDENCE = Path(
    "docs/experiments/raw/market-style-observation-2026-10-20/"
    "workflow-progress-evidence-20261024.json"
)
ALLOWED_PREFIXES = (
    "docs/experiments/", "docs/research/", "configs/", "web/public/research/"
)
STAGE_IDS = ("meaning", "universe", "data", "definition", "test", "validation", "increment", "decision")
STAGE_STATES = {"done", "partial", "blocked", "not_evaluated", "not_applicable", "unknown"}
EXECUTION_STATES = {"completed", "blocked", "paused", "unknown"}
CONCLUSION_STATES = {"supported_in_role", "limited", "unsupported", "inconclusive", "not_evaluated", "unknown"}
BOTTLENECK_KINDS = {"data", "validation", "definition", "scope", "none"}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _text(value: object, field: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"invalid_{field}")
    return value


def _date(value: object, field: str) -> None:
    raw = _text(value, field)
    try:
        _require(date.fromisoformat(raw).isoformat() == raw, f"invalid_{field}")
    except ValueError as exc:
        raise ValueError(f"invalid_{field}") from exc


def _repo_file(root: Path, raw: str) -> Path:
    """Reject traversal, absolute paths, and symlink escapes before reading."""
    _text(raw, "source_path")
    path = PurePosixPath(raw)
    _require(not path.is_absolute() and "\\" not in raw and ".." not in path.parts,
             "unsafe_source_path")
    _require(any(raw.startswith(prefix) for prefix in ALLOWED_PREFIXES),
             "unsafe_source_path")
    target = (root / raw).resolve()
    _require(any(target.is_relative_to(root.resolve() / prefix.rstrip("/"))
                 for prefix in ALLOWED_PREFIXES), "unsafe_source_path")
    return target


def _refs(value: object, source_ids: set[str], field: str, *, required: bool = False) -> None:
    _require(isinstance(value, list) and all(isinstance(x, str) for x in value),
             f"invalid_{field}")
    _require(len(value) == len(set(value)) and set(value) <= source_ids,
             f"invalid_{field}_reference")
    _require(not required or bool(value), f"missing_{field}_evidence")


def _validate(data: dict, root: Path) -> None:
    _require(data.get("schemaVersion") == 1, "invalid_progress_schema")
    reviewed = _text(data.get("reviewedAt"), "reviewedAt")
    try:
        _require(datetime.fromisoformat(reviewed).tzinfo is not None, "invalid_reviewedAt")
    except ValueError as exc:
        raise ValueError("invalid_reviewedAt") from exc
    _text(data.get("projectionNote"), "projectionNote")
    sources, cases = data.get("sources"), data.get("cases")
    _require(isinstance(sources, list) and isinstance(cases, list), "invalid_progress_lists")
    source_ids: set[str] = set()
    for source in sources:
        _require(isinstance(source, dict), "invalid_source")
        sid = _text(source.get("id"), "source_id")
        _require(sid not in source_ids, "duplicate_source_id")
        source_ids.add(sid)
        _text(source.get("title"), "source_title")
        _text(source.get("locator"), "source_locator")
        _date(source.get("sourceDate"), "source_date")
        sha = source.get("sha256")
        _require(isinstance(sha, str) and SHA256.fullmatch(sha) is not None,
                 "invalid_source_sha256")
        _repo_file(root, source.get("path"))
        if source.get("reportPath") is not None:
            report = source["reportPath"]
            _require(isinstance(report, str) and report.startswith("docs/experiments/")
                     and report.endswith(".md"), "invalid_report_path")
            _repo_file(root, report)
    case_ids: set[str] = set()
    for case in cases:
        _require(isinstance(case, dict), "invalid_case")
        cid = _text(case.get("id"), "case_id")
        _require(cid not in case_ids, "duplicate_case_id")
        case_ids.add(cid)
        _require(case.get("kind") in {"factor", "strategy", "data"}, "invalid_case_kind")
        for field in ("title", "researchVersion", "purpose", "universe", "period"):
            _text(case.get(field), field)
        _date(case.get("evidenceAsOf"), "evidenceAsOf")
        for field in ("definitionRefs", "poolIds", "limitations"):
            _require(isinstance(case.get(field), list) and all(isinstance(x, str) for x in case[field]),
                     f"invalid_{field}")
        _refs(case.get("sourceIds"), source_ids, "case_sourceIds", required=True)
        execution = case.get("execution")
        _require(isinstance(execution, dict) and execution.get("state") in EXECUTION_STATES,
                 "invalid_execution")
        _text(execution.get("label"), "execution_label")
        conclusion = case.get("conclusion")
        _require(isinstance(conclusion, dict) and conclusion.get("state") in CONCLUSION_STATES,
                 "invalid_conclusion")
        _text(conclusion.get("text"), "conclusion_text")
        bottleneck = case.get("bottleneck")
        _require(isinstance(bottleneck, dict) and bottleneck.get("scope") in {"本轮", "扩大用途"}
                 and bottleneck.get("kind") in BOTTLENECK_KINDS, "invalid_bottleneck")
        for field in ("title", "detail", "nextAction", "dependency"):
            _text(bottleneck.get(field), f"bottleneck_{field}")
        _refs(bottleneck.get("sourceIds"), source_ids, "bottleneck_sourceIds",
              required=bottleneck["kind"] != "none")
        stages = case.get("stages")
        _require(isinstance(stages, list) and [x.get("id") for x in stages if isinstance(x, dict)]
                 == list(STAGE_IDS), "invalid_stage_order")
        _require(case.get("currentStageId") in STAGE_IDS, "invalid_current_stage")
        for stage in stages:
            _require(stage.get("status") in STAGE_STATES, "invalid_stage_status")
            _text(stage.get("title"), "stage_title")
            _text(stage.get("summary"), "stage_summary")
            _refs(stage.get("sourceIds"), source_ids, "stage_sourceIds",
                  required=stage["status"] in {"done", "blocked"})
        timeline = case.get("timeline")
        _require(isinstance(timeline, list), "invalid_timeline")
        for event in timeline:
            _require(isinstance(event, dict), "invalid_timeline")
            _date(event.get("date"), "timeline_date")
            _text(event.get("label"), "timeline_label")
            _refs(event.get("sourceIds"), source_ids, "timeline_sourceIds", required=True)
        _validate_selection(case, root)


def _validate_selection(case: dict, root: Path) -> None:
    dataset_id, factor_id = case.get("datasetId"), case.get("factorId")
    if dataset_id is None and factor_id is None:
        _require(not case["poolIds"], "pool_without_dataset")
        return
    _require(isinstance(dataset_id, str) and isinstance(factor_id, str), "incomplete_selection")
    catalog_path = _repo_file(root, "web/public/research/factor-curve-library-20261022/catalog.json")
    try:
        catalog = json.loads(catalog_path.read_text())
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise ValueError("selection_catalog_unavailable") from exc
    dataset = next((x for x in catalog.get("datasets", []) if x.get("id") == dataset_id), None)
    _require(dataset is not None, "unknown_dataset")
    _require(any(x.get("id") == factor_id for x in dataset.get("factors", [])), "unknown_factor")
    valid_pools = {x.get("id") for x in dataset.get("stockPools", [])}
    _require(bool(case["poolIds"]) and set(case["poolIds"]) <= valid_pools,
             "unknown_pool")


def build_progress(root: Path, evidence_path: Path | None = None) -> dict:
    """Build the current display projection from saved decisions and checked files."""
    root = Path(root).resolve()
    path = root / DEFAULT_EVIDENCE if evidence_path is None else Path(evidence_path)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    _require(resolved.is_relative_to(root) and any(
        resolved.is_relative_to(root / prefix.rstrip("/")) for prefix in ALLOWED_PREFIXES
    ), "unsafe_evidence_path")
    raw = json.loads(resolved.read_text())
    _require(isinstance(raw, dict), "invalid_progress_schema")
    _validate(raw, root)
    result = deepcopy(raw)
    status_by_id: dict[str, str] = {}
    for source in result["sources"]:
        try:
            actual = hashlib.sha256(_repo_file(root, source["path"]).read_bytes()).hexdigest()
        except (FileNotFoundError, OSError):
            actual = None
        source["actualSha256"] = actual
        source["status"] = "missing" if actual is None else (
            "verified" if actual == source["sha256"] else "changed"
        )
        status_by_id[source["id"]] = source["status"]
    for case in result["cases"]:
        all_refs = set(case["sourceIds"])
        all_refs.update(case["bottleneck"]["sourceIds"])
        for stage in case["stages"]:
            all_refs.update(stage["sourceIds"])
        for event in case["timeline"]:
            all_refs.update(event["sourceIds"])
        bad = {sid for sid in all_refs if status_by_id[sid] != "verified"}
        case["integrity"] = ("missing" if any(status_by_id[sid] == "missing" for sid in bad)
                             else "changed" if bad else "verified")
        if bad:
            case["lastReviewedExecution"] = case["execution"]
            case["lastReviewedConclusion"] = case["conclusion"]
            case["execution"] = {"state": "unknown", "label": "待重新核对"}
            case["conclusion"] = {"state": "unknown", "text": "证据需复核，原结论暂不作为当前结论"}
            case["bottleneck"] = {
                "scope": "本轮", "kind": "validation", "title": "证据需复核",
                "detail": "引用的原始记录缺失或内容与保存的指纹不同。",
                "nextAction": "核对来源并更新研究记录后再显示原判断。",
                "dependency": "原研究记录和来源核对", "sourceIds": sorted(bad),
            }
            for stage in case["stages"]:
                if bad.intersection(stage["sourceIds"]):
                    stage["lastReviewedStatus"] = stage["status"]
                    stage["status"] = "unknown"
                    stage["summary"] = "本阶段引用的证据需重新核对"
    result["checkedAt"] = datetime.now(timezone.utc).isoformat()
    return result
