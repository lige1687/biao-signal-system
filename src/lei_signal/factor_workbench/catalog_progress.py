"""Read-only progress cards for the complete registered research catalog.

Registration proves only that a definition is listed. Research conclusions stay
with the reviewed research cases that originally made them.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from lei_signal.factor_workbench.progress import STAGE_IDS
from lei_signal.research.factor_combinations import build_catalog


OSAP_JSON = Path("docs/experiments/raw/market-style-observation-2026-10-20/workflow-catalog-osap-20261024.json")
OSAP_MANIFEST = OSAP_JSON.with_suffix(".manifest.json")
LEGACY_CATALOG = Path("web/src/pages/factor-research/catalog.generated.json")
STAGE_TITLES = ("金融含义", "研究范围", "数据核验", "固定定义", "实验测试", "验证反例", "比较增量", "结论处置")


def _inside(root: Path, value: str | Path) -> Path:
    path = Path(value)
    candidate = (path if path.is_absolute() else root / path).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("source outside project root")
    return candidate


def _source(result: dict, root: Path, *, path: Path, title: str, day: str) -> str:
    path = _inside(root, path)
    relative = path.relative_to(root).as_posix()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    existing = next((source for source in result["sources"]
                     if source.get("path") == relative and source.get("sha256") == digest
                     and source.get("status") == "verified"), None)
    if existing is not None:
        return existing["id"]
    stem = "catalog-" + hashlib.sha256(relative.encode()).hexdigest()[:16]
    used = {source["id"] for source in result["sources"]}
    source_id = stem
    suffix = 1
    while source_id in used:
        source_id = f"{stem}-{suffix}"
        suffix += 1
    result["sources"].append({
        "id": source_id, "title": title, "path": relative, "sha256": digest,
        "actualSha256": digest, "status": "verified", "sourceDate": day,
        "locator": "登记目录；仅证明本次读取的文件内容一致",
    })
    return source_id


def _describe(value: object, fallback: str = "目录未注明") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "、".join(map(str, value)) or fallback
    if isinstance(value, dict):
        return "；".join(f"{key}: {_describe(item)}" for key, item in value.items()) or fallback
    return str(value)


def _case(key: str, card: dict, source_ids: list[str], day: str,
          related: list[str], *, external: bool = False) -> dict:
    native = card["native_metadata"]
    reference = key.startswith("reference:")
    record_type = "external_reference" if external else ("registered_reference" if reference else "registered_object")
    object_type = card.get("kind")
    kind = "reference" if reference or external else (
        "strategy" if object_type == "policy/strategy" else
        "benchmark" if object_type == "benchmark" else "factor"
    )
    scope = native.get("scope") or native.get("universe") or native.get("market")
    definition = native.get("definition") or native.get("construction") or native.get("description")
    uses = native.get("uses") or native.get("questions")
    if external:
        purpose = "公开参考；本地用途尚未关联"
        signal_type = {"Predictor": "作者候选", "Placebo": "对照", "Drop": "弃用"}.get(
            native.get("sourceSignalType"), "原目录类别未注明")
        definition_summary = "公开目录描述：" + _describe(native.get("description")) + "；" + signal_type
        data_summary = "只读取公开目录概览，未检查收益资料或预测能力。"
    else:
        purpose = _describe(uses, "登记用途未注明")
        definition_summary = "定义已登记：" + _describe(definition)
        data_summary = "目录含来源或范围说明；资料可用性及历史时点仍需按具体研究核查。"
    summaries = (
        "登记名称与类别：" + _describe(card.get("name")) + "；" + _describe(object_type),
        "登记范围：" + _describe(scope),
        data_summary,
        definition_summary,
        "未关联可直接继承的实验结果。",
        "未按此用途核对反例或独立时期。",
        "未评价相对母指数（有准确绑定时）及既有方法的帮助与代价。",
        "本档案只展示目录登记；研究决定须查看独立研究记录。",
    )
    stages = [{"id": stage_id, "title": title,
               "status": "partial" if stage_id == "definition" and not external else "unknown",
               "summary": summary, "sourceIds": source_ids if stage_id == "definition" else []}
              for stage_id, title, summary in zip(STAGE_IDS, STAGE_TITLES, summaries)]
    return {
        "id": "catalog:" + key, "kind": kind, "recordType": record_type,
        "catalogKey": key, "objectType": object_type,
        "relatedCaseIds": related, "title": _describe(card.get("name"), key),
        "researchVersion": str(native.get("version") or "公开目录版本未注明"),
        "definitionRefs": [card["definition_ref"]] if card.get("definition_ref") else [],
        "purpose": purpose, "universe": _describe(scope),
        "period": "目录未给出本地研究期间", "poolIds": [],
        "execution": {"state": "unknown", "label": "尚未关联研究记录"},
        "conclusion": {"state": "not_evaluated", "text": "该登记项在此用途下没有独立的研究结论。"},
        "bottleneck": {"scope": "扩大用途", "kind": "none", "title": "研究证据未关联",
                       "detail": "目录登记不等于研究执行或金融有效性。",
                       "nextAction": "按准确对象和用途核对相关研究记录。",
                       "dependency": "准确对象、用途和研究证据", "sourceIds": []},
        "currentStageId": "definition", "stages": stages, "timeline": [],
        "evidenceAsOf": day, "sourceIds": source_ids,
        "integrity": "verified", "limitations": [
            "来源指纹仅说明本次登记文件内容一致，不证明因子有效。",
            "原目录生命周期或工程状态只是登记说明，不作为收益或预测结论。",
        ] + (["公开原目录类别：" + signal_type + "；本地用途尚未关联。"] if external else []),
    }


def _external_rows(root: Path) -> tuple[list[dict], Path, Path, str]:
    manifest_path = _inside(root, OSAP_MANIFEST)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("external manifest is not an object")
    path = _inside(root, manifest["path"])
    if path != _inside(root, OSAP_JSON):
        raise ValueError("external catalog path differs from approved local summary")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != manifest.get("sha256"):
        raise ValueError("external catalog SHA-256 mismatch")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("schemaVersion") != 1 or not isinstance(catalog.get("records"), list):
        raise ValueError("external catalog schema invalid")
    rows = catalog["records"]
    if (type(manifest.get("recordCount")) is not int or manifest["recordCount"] != len(rows)
            or catalog.get("originalCatalogSha256") != manifest.get("originalCatalogSha256")):
        raise ValueError("external catalog count or original source mismatch")
    if not catalog.get("retrievedAt") or not manifest.get("sourceManifestPath"):
        raise ValueError("external catalog provenance missing")
    if manifest.get("sourceManifestSha256"):
        source_manifest = _inside(root, manifest["sourceManifestPath"])
        if hashlib.sha256(source_manifest.read_bytes()).hexdigest() != manifest["sourceManifestSha256"]:
            raise ValueError("external source manifest SHA-256 mismatch")
    keys = [row.get("key") if isinstance(row, dict) else None for row in rows]
    if not all(isinstance(key, str) and key for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("external catalog keys invalid or duplicated")
    return rows, path, manifest_path, manifest["originalCatalogSha256"]


def _legacy_items(root: Path) -> tuple[dict[str, dict], list[str]]:
    """Keep old research descriptions, while exposing stale source bindings."""
    path = _inside(root, LEGACY_CATALOG)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != "factor-research/1" or not isinstance(snapshot.get("items"), list):
        raise ValueError("old research catalog schema invalid")
    items: dict[str, dict] = {}
    for item in snapshot["items"]:
        ref = item.get("reference") if isinstance(item, dict) else None
        if not isinstance(ref, str) or not ref or ref in items:
            raise ValueError("old research catalog identity invalid or duplicated")
        items[ref] = item
    issues: list[str] = []
    seen_paths: set[str] = set()
    for source in snapshot.get("sources", []):
        raw_path = source.get("path")
        if not isinstance(raw_path, str) or raw_path in seen_paths:
            raise ValueError("old research catalog source invalid or duplicated")
        seen_paths.add(raw_path)
        try:
            source_path = _inside(root, raw_path)
            if hashlib.sha256(source_path.read_bytes()).hexdigest() != source.get("sha256"):
                issues.append(f"旧研究目录来源已变化：{raw_path}")
        except OSError:
            issues.append(f"旧研究目录来源缺失：{raw_path}")
    return items, issues


def _apply_legacy(case: dict, item: dict, source_id: str) -> None:
    research = item.get("research") or {}
    summary = research.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return
    stage = research.get("stage")
    if stage == "historical":
        case["execution"] = {"state": "unknown", "label": "已有旧记录 · 待核对"}
        case["conclusion"] = {"state": "unknown", "text": "旧目录有研究摘要，当前结论需按原报告与用途复核。"}
        case["stages"][4]["summary"] = "旧目录所载研究：" + summary
        case["stages"][4]["sourceIds"] = [source_id]
        case["limitations"].append("旧目录记录日期：" + _describe(research.get("evidence_date")))
        case["limitations"].append("旧目录摘要是历史记录，未继承为当前已验证结论。")
    elif stage == "calculation_only":
        case["limitations"].append("旧目录仅记载计算检查：" + summary)
    else:
        case["limitations"].append("旧目录说明：" + summary)
    case["legacyCatalogUrl"] = "/factors?tab=catalog&factor=" + quote(item["reference"], safe="")


def extend_progress(root: Path, base: dict) -> dict:
    """Add catalog cards without changing reviewed cases or masking source failures."""
    root = Path(root).resolve()
    result = deepcopy(base)
    day = datetime.fromisoformat(result.get("checkedAt", datetime.now(timezone.utc).isoformat())).date().isoformat()
    for case in result["cases"]:
        case.setdefault("recordType", "reviewed_research")
    reviewed = list(result["cases"])
    existing_ids = {case["id"] for case in reviewed}
    refs: dict[str, list[str]] = {}
    for case in reviewed:
        for ref in case.get("definitionRefs", []):
            refs.setdefault(ref, []).append(case["id"])
    counts = {"registeredObjects": 0, "registeredReferences": 0, "externalReferences": 0,
              "reviewedResearchCases": len(reviewed), "linkedObjects": 0}
    issues: list[str] = []
    legacy: dict[str, dict] = {}
    legacy_source_id: str | None = None
    try:
        legacy, legacy_issues = _legacy_items(root)
        issues.extend(legacy_issues)
        legacy_source_id = _source(result, root, path=_inside(root, LEGACY_CATALOG),
                                   title="既有研究页面历史目录", day=day)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        issues.append(f"既有研究页面目录未能读取：{exc}")
    try:
        catalog = build_catalog(root)
        binding = catalog["source_bindings"]["definition_registry"]
        registry_path = _inside(root, binding["path"])
        if hashlib.sha256(registry_path.read_bytes()).hexdigest() != binding["sha256"]:
            raise ValueError("definition registry changed during read")
        source_id = _source(result, root, path=registry_path, title="当前定义登记表", day=day)
        for key, card in catalog["cards"].items():
            if not key.startswith(("object:", "reference:")):
                raise ValueError(f"unexpected catalog key: {key}")
            case_id = "catalog:" + key
            if case_id in existing_ids:
                raise ValueError(f"catalog case ID collision: {case_id}")
            existing_ids.add(case_id)
            related = refs.get(card["definition_ref"], []) if key.startswith("object:") else []
            case = _case(key, card, [source_id], day, related)
            if key.startswith("object:") and legacy_source_id is not None:
                old = legacy.get(card["definition_ref"])
                if old is not None:
                    _apply_legacy(case, old, legacy_source_id)
            result["cases"].append(case)
            counts["registeredReferences" if key.startswith("reference:") else "registeredObjects"] += 1
            counts["linkedObjects"] += bool(related)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        issues.append(f"定义登记目录未能完整读取：{exc}")
    try:
        rows, path, manifest_path, original_sha = _external_rows(root)
        source_ids = [_source(result, root, path=manifest_path, title="外部目录清单", day=day),
                      _source(result, root, path=path, title="外部目录概览", day=day)]
        for row in rows:
            key = row["key"]
            case_id = "catalog:" + key
            if case_id in existing_ids:
                raise ValueError(f"external case ID collision: {case_id}")
            existing_ids.add(case_id)
            card = {"name": row.get("name") or row["key"], "kind": "published_reference",
                    "definition_ref": None,
                    "native_metadata": {**row, "version": "原目录 " + original_sha[:12]}}
            result["cases"].append(_case(key, card, source_ids, day, [], external=True))
            counts["externalReferences"] += 1
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        issues.append(f"外部目录未能读取或校验：{exc}")
    result["catalog"] = {
        "total": counts["registeredObjects"] + counts["registeredReferences"]
                 + counts["externalReferences"], **counts, "issues": issues,
    }
    return result
