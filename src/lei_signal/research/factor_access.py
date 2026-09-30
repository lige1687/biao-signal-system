"""通用因子研究材料只读接入。

这里只校验索引、正式定义身份、来源文件和已经产生的 ``ResearchBatch``。
不导入计算适配器，不运行因子、行情、回测、SQL、脚本或交易逻辑。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from numbers import Real
from pathlib import Path
from typing import Any

import pandas as pd

from lei_signal.research import definitions
from lei_signal.research.factor_lab.contracts import (
    ENTITY_AXES,
    METADATA_REQUIRED,
    PROTOCOL_KINDS,
    IdentityFormatError,
    ResearchBatch,
    validate_values_frame,
)
from lei_signal.research.factor_runtime import contract_digest

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG = Path("configs/factor-access.v1.json")
DEFAULT_REGISTRY = Path("docs/research/definitions.v1.json")

_PACKET_KEYS = {
    "schema_version",
    "kind",
    "metadata",
    "values",
    "findings",
    "sources",
    "calculated_at",
    "definition_contract_sha256",
}
_CATALOG_KEYS = {"schema_version", "bindings", "comparisons"}
_BINDING_REQUIRED = {
    "reference",
    "aliases",
    "kind",
    "label",
    "definition_notes",
    "sources",
    "evidence",
    "batches",
}
_BINDING_OPTIONAL = {"legacy_panel", "draft_definition"}
_EVIDENCE_KINDS = {
    "calculation_check",
    "data_validation",
    "predictive_study",
    "return_study",
    "risk_description",
}
_EVIDENCE_KEYS = {"kind", "summary", "scope", "limitations", "sources"}
_COMPARISON_KEYS = {"references", "summary", "limitations", "sources"}
_SOURCE_KEYS = {"path", "sha256"}
_SOURCE_PREFIXES = ("docs/experiments/", "docs/research/", "tests/fixtures/")
_FORBIDDEN_CODE_KEYS = {
    "module",
    "callable",
    "function",
    "sql",
    "shell",
    "script",
    "command",
    "runner",
    "python",
}
_REGISTERED_REF = re.compile(r"^[a-z][a-z0-9_.-]+@[0-9]+\.[0-9]+\.[0-9]+$")
_CANDIDATE_REF = re.compile(r"^candidate:[a-z][a-z0-9_.-]+@draft-[1-9][0-9]*$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class AccessError(ValueError):
    """研究材料身份、结构或安全路径不合格。"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_copy(value: Any, *, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise AccessError(f"{label} must be finite JSON data") from exc


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AccessError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _load_json(path: Path, *, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_object)
    except AccessError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AccessError(f"cannot read {label}: {path}") from exc


def _root(root: str | Path | None) -> Path:
    base = Path(root).resolve() if root is not None else ROOT.resolve()
    if not base.is_dir():
        raise AccessError(f"root is not a directory: {base}")
    return base


def _inside(base: Path, path: Path, *, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise AccessError(f"{label} file missing: {path}") from exc
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise AccessError(f"{label} path resolves outside root: {path}") from exc
    if not resolved.is_file():
        raise AccessError(f"{label} is not a file: {path}")
    return resolved


def _path_argument(base: Path, value: str | Path | None, default: Path, *, label: str) -> Path:
    raw = Path(value) if value is not None else default
    candidate = raw if raw.is_absolute() else base / raw
    return _inside(base, candidate, label=label)


def _relative(base: Path, path: Path) -> str:
    return path.resolve().relative_to(base).as_posix()


def _forbid_code_entries(value: Any, *, path: str = "catalog") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in _FORBIDDEN_CODE_KEYS:
                raise AccessError(f"code entry field forbidden: {path}.{key}")
            _forbid_code_entries(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _forbid_code_entries(child, path=f"{path}[{index}]")


def _string_list(value: Any, *, label: str, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise AccessError(f"{label} must be a string list")
    cleaned = [v.strip() for v in value]
    if len(cleaned) != len(set(cleaned)):
        raise AccessError(f"{label} contains duplicates")
    if not allow_empty and not cleaned:
        raise AccessError(f"{label} must not be empty")
    return cleaned


def _source_spec(value: Any, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != _SOURCE_KEYS:
        raise AccessError(f"{label} requires path and sha256")
    path = value.get("path")
    digest = value.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not path.startswith(_SOURCE_PREFIXES)
    ):
        raise AccessError(f"{label} has unsafe or unsupported source path")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise AccessError(f"{label} has invalid sha256")
    return {"path": Path(path).as_posix(), "sha256": digest}


def _source_list(
    value: Any, *, label: str, allow_empty: bool = True
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise AccessError(f"{label} must be a source list")
    out = [_source_spec(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
    if not allow_empty and not out:
        raise AccessError(f"{label} must not be empty")
    keys = [(item["path"], item["sha256"]) for item in out]
    if len(keys) != len(set(keys)):
        raise AccessError(f"{label} contains duplicate sources")
    by_path: dict[str, str] = {}
    for item in out:
        previous = by_path.setdefault(item["path"], item["sha256"])
        if previous != item["sha256"]:
            raise AccessError(f"{label} gives conflicting hashes for {item['path']}")
    return out


def _verify_source(
    base: Path, source: dict[str, str], *, label: str
) -> tuple[Path, dict[str, str]]:
    spec = _source_spec(source, label=label)
    path = _inside(base, base / spec["path"], label=label)
    actual = _sha256(path)
    if actual != spec["sha256"]:
        raise AccessError(
            f"source hash mismatch for {spec['path']}: expected={spec['sha256']} actual={actual}"
        )
    return path, spec


def _validate_evidence(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _EVIDENCE_KEYS:
        raise AccessError(f"{label} has invalid evidence fields")
    if value["kind"] not in _EVIDENCE_KINDS:
        raise AccessError(f"{label} has unknown evidence kind")
    for field in ("summary", "scope"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise AccessError(f"{label}.{field} must be a nonempty string")
    return {
        "kind": value["kind"],
        "summary": value["summary"].strip(),
        "scope": value["scope"].strip(),
        "limitations": _string_list(value["limitations"], label=f"{label}.limitations"),
        "sources": _source_list(
            value["sources"], label=f"{label}.sources", allow_empty=False
        ),
    }


def _validate_binding(value: Any, *, index: int) -> dict[str, Any]:
    label = f"bindings[{index}]"
    if not isinstance(value, dict):
        raise AccessError(f"{label} must be an object")
    keys = set(value)
    if _BINDING_REQUIRED - keys or keys - (_BINDING_REQUIRED | _BINDING_OPTIONAL):
        raise AccessError(f"{label} has invalid binding fields")
    reference = value["reference"]
    kind = value["kind"]
    if kind not in {"registered", "candidate"}:
        raise AccessError(f"{label}.kind must be registered or candidate")
    if not isinstance(reference, str) or (
        kind == "registered" and not _REGISTERED_REF.fullmatch(reference)
    ) or (kind == "candidate" and not _CANDIDATE_REF.fullmatch(reference)):
        raise AccessError(f"{label} has invalid exact reference")
    if not isinstance(value["label"], str) or not value["label"].strip():
        raise AccessError(f"{label}.label must be nonempty")
    if kind == "candidate":
        if (
            not isinstance(value.get("draft_definition"), str)
            or not value["draft_definition"].strip()
        ):
            raise AccessError(f"{label}.draft_definition required for candidate")
        if "legacy_panel" in value:
            raise AccessError(f"{label}.legacy_panel is registered-only")
    elif "draft_definition" in value:
        raise AccessError(f"{label}.draft_definition is candidate-only")
    out = {
        "reference": reference,
        "aliases": _string_list(value["aliases"], label=f"{label}.aliases"),
        "kind": kind,
        "label": value["label"].strip(),
        "definition_notes": _string_list(
            value["definition_notes"], label=f"{label}.definition_notes"
        ),
        "sources": _source_list(value["sources"], label=f"{label}.sources"),
        "evidence": [
            _validate_evidence(item, label=f"{label}.evidence[{evidence_index}]")
            for evidence_index, item in enumerate(value["evidence"])
        ]
        if isinstance(value["evidence"], list)
        else None,
        "batches": _source_list(value["batches"], label=f"{label}.batches"),
    }
    if out["evidence"] is None:
        raise AccessError(f"{label}.evidence must be a list")
    if "legacy_panel" in value:
        legacy = value["legacy_panel"]
        if (
            not isinstance(legacy, dict)
            or set(legacy) != {"field"}
            or not isinstance(legacy["field"], str)
            or not legacy["field"].strip()
        ):
            raise AccessError(f"{label}.legacy_panel requires a nonempty field")
        out["legacy_panel"] = {"field": legacy["field"].strip()}
    if "draft_definition" in value:
        out["draft_definition"] = value["draft_definition"].strip()
    return out


def _validate_comparison(value: Any, *, index: int) -> dict[str, Any]:
    label = f"comparisons[{index}]"
    if not isinstance(value, dict) or set(value) != _COMPARISON_KEYS:
        raise AccessError(f"{label} has invalid comparison fields")
    references = _string_list(value["references"], label=f"{label}.references", allow_empty=False)
    if len(references) < 2:
        raise AccessError(f"{label} needs at least two references")
    for field in ("summary",):
        if not isinstance(value[field], str) or not value[field].strip():
            raise AccessError(f"{label}.{field} must be nonempty")
    return {
        "references": references,
        "summary": value["summary"].strip(),
        "limitations": _string_list(value["limitations"], label=f"{label}.limitations"),
        "sources": _source_list(
            value["sources"], label=f"{label}.sources", allow_empty=False
        ),
    }


def load_access_catalog(
    *,
    root: str | Path | None = None,
    catalog_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """加载并校验数据登记索引；不加载任何代码入口。"""
    base = _root(root)
    catalog_file = _path_argument(base, catalog_path, DEFAULT_CATALOG, label="catalog")
    raw = _load_json(catalog_file, label="catalog")
    if (
        not isinstance(raw, dict)
        or set(raw) != _CATALOG_KEYS
        or type(raw.get("schema_version")) is not int
        or raw["schema_version"] != 1
    ):
        raise AccessError("unsupported catalog schema")
    _forbid_code_entries(raw)
    if not isinstance(raw["bindings"], list) or not isinstance(raw["comparisons"], list):
        raise AccessError("catalog bindings and comparisons must be lists")
    bindings_list = [_validate_binding(item, index=i) for i, item in enumerate(raw["bindings"])]
    references = [item["reference"] for item in bindings_list]
    if len(references) != len(set(references)):
        raise AccessError("duplicate binding reference")

    # 同名别名与同一对象的多版本允许并存；消费者必须把多命中作为歧义处理。
    registry_file = _path_argument(base, registry_path, DEFAULT_REGISTRY, label="registry")
    try:
        registry = definitions.load_registry(registry_file)
        cards = definitions.validate_registry(registry)
    except (OSError, ValueError) as exc:
        raise AccessError(f"invalid definition registry: {registry_file}") from exc
    definitions_by_ref = {
        reference: card
        for reference, card in cards.items()
        if "description" in card["uses"]
    }
    for binding in bindings_list:
        if binding["kind"] != "registered":
            continue
        if binding["reference"] not in definitions_by_ref:
            raise AccessError(
                f"registered reference not resolvable for description: {binding['reference']}"
            )

    comparisons = [
        _validate_comparison(item, index=i) for i, item in enumerate(raw["comparisons"])
    ]
    available_refs = set(references) | set(definitions_by_ref)
    seen_comparison_sets: set[frozenset[str]] = set()
    for comparison in comparisons:
        if not set(comparison["references"]) <= available_refs:
            raise AccessError("comparison contains an unknown reference")
        key = frozenset(comparison["references"])
        if key in seen_comparison_sets:
            raise AccessError("duplicate comparison reference set")
        seen_comparison_sets.add(key)

    return {
        "root": str(base),
        "registry": registry,
        "definitions": definitions_by_ref,
        "bindings": {item["reference"]: item for item in bindings_list},
        "comparisons": comparisons,
        "catalog_source": {
            "path": _relative(base, catalog_file),
            "sha256": _sha256(catalog_file),
        },
        "registry_source": {
            "path": _relative(base, registry_file),
            "sha256": _sha256(registry_file),
        },
    }


def _catalog_root(catalog: dict[str, Any], root: str | Path | None) -> Path:
    return _root(root if root is not None else catalog.get("root"))


def _verified_sources(
    base: Path, sources: list[dict[str, str]], *, label: str
) -> tuple[list[Path], list[dict[str, str]]]:
    paths: list[Path] = []
    verified: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, source in enumerate(sources):
        path, spec = _verify_source(base, source, label=f"{label}[{index}]")
        key = (spec["path"], spec["sha256"])
        if key not in seen:
            paths.append(path)
            verified.append(spec)
            seen.add(key)
    return paths, verified


def _merge_verified_sources(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    by_path: dict[str, str] = {}
    for source in (item for group in groups for item in group):
        previous = by_path.setdefault(source["path"], source["sha256"])
        if previous != source["sha256"]:
            raise AccessError(f"conflicting verified hashes for {source['path']}")
        if not any(existing["path"] == source["path"] for existing in merged):
            merged.append(deepcopy(source))
    return merged


def _registry_path_from_catalog(base: Path, catalog: dict[str, Any]) -> Path:
    source = catalog.get("registry_source")
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        raise AccessError("catalog result lacks registry_source")
    return _inside(base, base / source["path"], label="registry")


def read_materials(
    catalog: dict[str, Any], reference: str, *, root: str | Path | None = None
) -> dict[str, Any]:
    """读取一个对象的已登记材料；坏来源只阻断该对象。"""
    if not isinstance(catalog, dict) or not isinstance(reference, str):
        raise AccessError("catalog and exact reference required")
    base = _catalog_root(catalog, root)
    binding = (catalog.get("bindings") or {}).get(reference)
    if binding is None:
        try:
            card = definitions.resolve(catalog["registry"], reference, purpose="description")
        except (KeyError, ValueError) as exc:
            raise AccessError(f"unknown exact reference: {reference}") from exc
        return {
            "reference": reference,
            "aliases": [],
            "kind": "registered",
            "label": card["name"],
            "definition_notes": [],
            "sources": [],
            "evidence": [],
            "binding": None,
            "definition": card,
            "sources_verified": [],
            "batches": [],
            "batch_files_verified": [],
        }

    material = deepcopy(binding)
    all_sources = list(material["sources"])
    for evidence in material["evidence"]:
        all_sources.extend(evidence["sources"])
    _, verified = _verified_sources(base, all_sources, label=f"materials[{reference}].sources")

    packet_paths, batch_specs = _verified_sources(
        base, material["batches"], label=f"materials[{reference}].batches"
    )
    packets: list[dict[str, Any]] = []
    packet_sources: list[dict[str, str]] = []
    registry_path = _registry_path_from_catalog(base, catalog)
    for path in packet_paths:
        packet = _load_json(path, label="research packet")
        checked = validate_research_packet(packet, root=base, registry_path=registry_path)
        if checked["metadata"]["reference"] != reference:
            raise AccessError(f"batch reference mismatch for {reference}")
        packets.append(checked)
        packet_sources.extend(checked["sources"])
    material["definition"] = catalog.get("definitions", {}).get(reference)
    material["binding"] = deepcopy(binding)
    material["batches"] = packets
    material["sources_verified"] = _merge_verified_sources(
        verified, batch_specs, packet_sources
    )
    material["batch_files_verified"] = batch_specs
    return material


def read_comparison(
    catalog: dict[str, Any], references: list[str], *, root: str | Path | None = None
) -> dict[str, Any] | None:
    """按同一组精确版本读取已有概念对照；没有匹配就返回 ``None``。"""
    requested = _string_list(references, label="references", allow_empty=False)
    requested_set = frozenset(requested)
    match = next(
        (
            comparison
            for comparison in catalog.get("comparisons", [])
            if frozenset(comparison["references"]) == requested_set
        ),
        None,
    )
    if match is None:
        return None
    base = _catalog_root(catalog, root)
    _, verified = _verified_sources(base, match["sources"], label="comparison.sources")
    out = deepcopy(match)
    out["sources_verified"] = verified
    return out


def _load_registry(base: Path, registry_path: str | Path | None) -> tuple[dict, Path]:
    path = _path_argument(base, registry_path, DEFAULT_REGISTRY, label="registry")
    try:
        return definitions.load_registry(path), path
    except (OSError, ValueError) as exc:
        raise AccessError(f"invalid definition registry: {path}") from exc


def _aware_timestamp(value: Any, *, label: str) -> str:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise AccessError(f"{label} is not a valid timestamp") from exc
    if timestamp.tzinfo is None:
        raise AccessError(f"{label} must be timezone-aware")
    return timestamp.isoformat()


def _normalize_values(values: pd.DataFrame, *, value_type: str) -> list[dict[str, Any]]:
    try:
        frame = validate_values_frame(values.copy())
    except IdentityFormatError as exc:
        raise AccessError(str(exc)) from exc
    rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        try:
            observed = pd.Timestamp(row["observation_date"])
        except (TypeError, ValueError) as exc:
            raise AccessError(f"invalid observation_date at row {index}") from exc
        if pd.isna(observed) or observed.tzinfo is not None or observed != observed.normalize():
            raise AccessError(f"observation_date must be a timezone-naive date at row {index}")
        entity = row["entity_id"]
        if not isinstance(entity, str) or not entity.strip():
            raise AccessError(f"entity_id must be nonempty at row {index}")
        value = row["value"]
        reason = row["missing_reason"]
        missing = pd.isna(value)
        if missing:
            if not isinstance(reason, str) or not reason.strip():
                raise AccessError(f"missing value requires missing_reason at row {index}")
            normalized_value = None
            normalized_reason: str | None = reason.strip()
        else:
            if value_type == "boolean":
                if isinstance(value, bool):
                    normalized_value = value
                elif (
                    isinstance(value, Real)
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and float(value) in {0.0, 1.0}
                ):
                    # 既有 ResearchBatch 用浮点 0/1 表达状态；保留该明确表达。
                    normalized_value = float(value)
                else:
                    raise AccessError(
                        f"boolean value must be bool or numeric 0/1 at row {index}"
                    )
            elif value_type in {"continuous", "fraction_bounded"}:
                if (
                    not isinstance(value, Real)
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                ):
                    raise AccessError(
                        f"value must be finite numeric or explained missing at row {index}"
                    )
                normalized_value = float(value)
                if value_type == "fraction_bounded" and not 0.0 <= normalized_value <= 1.0:
                    raise AccessError(f"fraction_bounded value outside [0, 1] at row {index}")
            else:
                raise AccessError(f"unsupported value_type: {value_type}")
            if not pd.isna(reason) and reason not in (None, ""):
                raise AccessError(f"finite value must not carry missing_reason at row {index}")
            normalized_reason = None
        rows.append(
            {
                "observation_date": observed.date().isoformat(),
                "entity_id": entity.strip(),
                "value": normalized_value,
                "missing_reason": normalized_reason,
            }
        )
    keys = [(row["observation_date"], row["entity_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise AccessError("duplicate normalized (observation_date, entity_id) rows")
    return rows


def _validate_metadata(metadata: Any, registry: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(metadata, dict):
        raise AccessError("metadata must be an object")
    missing = METADATA_REQUIRED - metadata.keys()
    if missing:
        raise AccessError(f"metadata missing required keys: {sorted(missing)}")
    reference = metadata.get("reference")
    if not isinstance(reference, str) or not _REGISTERED_REF.fullmatch(reference):
        raise AccessError("metadata.reference must be an exact registered version")
    try:
        card = definitions.resolve(registry, reference, purpose="description")
    except ValueError as exc:
        raise AccessError(f"metadata reference not resolvable: {reference}") from exc
    if metadata.get("card_kind") != "registered" or metadata.get("card") != card:
        raise AccessError("metadata card identity differs from formal definition")
    if metadata.get("type") != card["type"]:
        raise AccessError("metadata type differs from formal definition")
    if metadata.get("unit") != card["definition"]["unit"]:
        raise AccessError("metadata unit differs from formal definition")
    value_type = metadata.get("value_type")
    if value_type not in {"continuous", "boolean", "fraction_bounded"}:
        raise AccessError("metadata value_type is unsupported")
    if (card["definition"]["unit"] == "boolean") != (value_type == "boolean"):
        raise AccessError("metadata value_type differs from formal definition unit")
    if metadata.get("production_authorization") != "not_authorized":
        raise AccessError("production authorization must remain not_authorized")
    synthetic = metadata.get("synthetic")
    if not isinstance(synthetic, bool):
        raise AccessError("metadata.synthetic must be boolean")
    protocol = metadata.get("protocol")
    identity = metadata.get("data_identity")
    if not isinstance(protocol, dict) or not isinstance(identity, dict):
        raise AccessError("metadata protocol and data_identity must be objects")
    if set(protocol) != {"protocol_id", "version", "kind", "data_mode", "sha256"}:
        raise AccessError("metadata protocol has invalid fields")
    if not isinstance(protocol["protocol_id"], str) or not protocol["protocol_id"].strip():
        raise AccessError("metadata protocol_id must be nonempty")
    if not isinstance(protocol["version"], str) or not _SEMVER.fullmatch(protocol["version"]):
        raise AccessError("metadata protocol version must be semantic")
    if protocol["kind"] not in PROTOCOL_KINDS or metadata.get("purpose") != protocol["kind"]:
        raise AccessError("metadata purpose must equal an allowed protocol kind")
    if not isinstance(protocol["sha256"], str) or not _SHA256.fullmatch(protocol["sha256"]):
        raise AccessError("metadata protocol sha256 is invalid")
    if metadata.get("entity_axis") not in ENTITY_AXES:
        raise AccessError("metadata entity_axis is invalid")
    for field in ("code_identity", "calendar", "time_evidence"):
        if not isinstance(metadata.get(field), dict):
            raise AccessError(f"metadata {field} must be an object")
    if identity.get("synthetic") is not synthetic:
        raise AccessError("data_identity.synthetic differs from metadata.synthetic")
    expected_mode, expected_status = (
        ("synthetic", "synthetic_input")
        if synthetic
        else ("historical_reconstruction", "historical_reconstruction")
    )
    if protocol.get("data_mode") != expected_mode or metadata.get("data_status") != expected_status:
        raise AccessError("synthetic/data_mode/data_status combination is not allowed")
    for metadata_key, card_key in (
        ("definition_status", "definition_clarity"),
        ("implementation_status", "implementation"),
        ("effectiveness_status", "effectiveness"),
    ):
        if metadata.get(metadata_key) != card["status"][card_key]:
            raise AccessError(f"metadata {metadata_key} differs from formal definition")
    return _json_copy(metadata, label="metadata"), card


def validate_research_packet(
    packet: dict,
    *,
    root: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """核验标准研究包；返回规范化副本，不修改资格。"""
    if not isinstance(packet, dict) or set(packet) != _PACKET_KEYS:
        raise AccessError("research packet has invalid schema fields")
    if type(packet.get("schema_version")) is not int or packet["schema_version"] != 1:
        raise AccessError("unsupported research packet schema")
    if packet.get("kind") != "research_batch":
        raise AccessError("research packet kind must be research_batch")
    base = _root(root)
    registry, _ = _load_registry(base, registry_path)
    metadata, card = _validate_metadata(packet.get("metadata"), registry)
    calculated_at = _aware_timestamp(packet.get("calculated_at"), label="calculated_at")
    if packet.get("definition_contract_sha256") != contract_digest(card):
        raise AccessError("definition contract digest mismatch")
    if not isinstance(packet.get("values"), list):
        raise AccessError("packet values must be a list")
    try:
        values_frame = pd.DataFrame(packet["values"], columns=[
            "observation_date", "entity_id", "value", "missing_reason"
        ])
    except (TypeError, ValueError) as exc:
        raise AccessError("packet values cannot form the required frame") from exc
    if any(not isinstance(row, dict) or set(row) != {
        "observation_date", "entity_id", "value", "missing_reason"
    } for row in packet["values"]):
        raise AccessError("packet value rows have invalid fields")
    values = _normalize_values(values_frame, value_type=metadata["value_type"])
    findings = packet.get("findings")
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        raise AccessError("findings must be a list of objects")
    findings_copy = _json_copy(findings, label="findings")
    sources = _source_list(
        packet.get("sources"), label="packet.sources", allow_empty=False
    )
    _, verified = _verified_sources(base, sources, label="packet.sources")
    return {
        "schema_version": 1,
        "kind": "research_batch",
        "metadata": metadata,
        "values": values,
        "findings": findings_copy,
        "sources": verified,
        "calculated_at": calculated_at,
        "definition_contract_sha256": contract_digest(card),
    }


def pack_research_batch(
    batch: ResearchBatch,
    *,
    sources: list[dict[str, str]],
    calculated_at: Any,
    root: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """序列化既有 ``ResearchBatch``；不计算、补值或提升资格。"""
    if not isinstance(batch, ResearchBatch):
        raise AccessError("batch must be an existing ResearchBatch")
    base = _root(root)
    registry, _ = _load_registry(base, registry_path)
    metadata, card = _validate_metadata(batch.metadata, registry)
    values = _normalize_values(batch.values, value_type=metadata["value_type"])
    findings = _json_copy(batch.findings, label="findings")
    source_specs = _source_list(sources, label="sources", allow_empty=False)
    _, verified = _verified_sources(base, source_specs, label="sources")
    packet = {
        "schema_version": 1,
        "kind": "research_batch",
        "metadata": metadata,
        "values": values,
        "findings": findings,
        "sources": verified,
        "calculated_at": _aware_timestamp(calculated_at, label="calculated_at"),
        "definition_contract_sha256": contract_digest(card),
    }
    return validate_research_packet(packet, root=base, registry_path=registry_path)


__all__ = [
    "AccessError",
    "DEFAULT_CATALOG",
    "DEFAULT_REGISTRY",
    "ROOT",
    "load_access_catalog",
    "pack_research_batch",
    "read_comparison",
    "read_materials",
    "validate_research_packet",
]
