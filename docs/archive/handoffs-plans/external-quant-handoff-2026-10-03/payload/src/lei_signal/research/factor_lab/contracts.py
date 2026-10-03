"""factor_lab 通用合同：研究批次、协议校验、元数据与身份。

本轮正式输出只接受 synthetic 资料模式；真实只读资格结果不得产出新 IC。
身份/格式失败抛 IdentityFormatError（退出码 3）；合法资料不足以结构化
缺失原因返回，由调用方决定退出码 2；不提供跳过核验或强制通过开关。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

EXIT_OK = 0
EXIT_INSUFFICIENT_DATA = 2
EXIT_IDENTITY_FORMAT = 3

PROTOCOL_KINDS = {
    "calculation_only",
    "predictive_diagnostic",
    "state_diagnostic",
    "strategy_explanation",
}
DATA_MODES = {"synthetic", "historical_reconstruction", "qualified"}
ENTITY_AXES = {"instrument", "universe"}
DIAGNOSTIC_TYPES = {"cross_section_ic", "state_outcomes", "time_series_state"}

VALUES_COLUMNS = ["observation_date", "entity_id", "value", "missing_reason"]

#: 元数据必需键（spec §4.1）；缺任何一项视为实现缺陷而非可跳过项。
METADATA_REQUIRED = {
    "reference",
    "card",
    "card_kind",
    "type",
    "unit",
    "purpose",
    "entity_axis",
    "value_type",
    "protocol",
    "data_identity",
    "code_identity",
    "calendar",
    "time_evidence",
    "synthetic",
    "definition_status",
    "data_status",
    "implementation_status",
    "effectiveness_status",
    "production_authorization",
}


class FactorLabError(Exception):
    """带建议退出码的研究合同异常基类。"""

    exit_code = EXIT_IDENTITY_FORMAT


class IdentityFormatError(FactorLabError):
    """对象身份、协议或输入格式不合法：退出码 3。"""

    exit_code = EXIT_IDENTITY_FORMAT


class InsufficientDataError(FactorLabError):
    """合法资料不足：退出码 2（原因必须完整写入输出）。"""

    exit_code = EXIT_INSUFFICIENT_DATA


@dataclass(frozen=True)
class ResearchBatch:
    """一份定义的一次计算结果：值、元数据、发现。

    values 行键固定为 observation_date, entity_id, value, missing_reason；
    缺值观察不删除，以 NaN + missing_reason 保留。
    """

    values: pd.DataFrame
    metadata: dict
    findings: list[dict] = field(default_factory=list)


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def protocol_sha256(protocol: dict) -> str:
    return hashlib.sha256(canonical_json(protocol).encode("utf-8")).hexdigest()


def fingerprint_path(path: str | Path) -> dict:
    p = Path(path)
    return {"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def validate_protocol(protocol: dict, *, expected_kinds: set[str] | None = None) -> None:
    """协议结构校验；本轮只接受 synthetic 资料模式。"""
    if not isinstance(protocol, dict):
        raise IdentityFormatError("protocol must be a dict")
    for key in ("protocol_id", "version", "kind", "data_mode"):
        if not protocol.get(key):
            raise IdentityFormatError(f"protocol missing key: {key}")
    if protocol["kind"] not in PROTOCOL_KINDS:
        raise IdentityFormatError(f"unknown protocol kind: {protocol['kind']}")
    if expected_kinds is not None and protocol["kind"] not in expected_kinds:
        raise IdentityFormatError(
            f"protocol kind {protocol['kind']} not allowed here; expected one of "
            f"{sorted(expected_kinds)}"
        )
    if protocol["data_mode"] not in DATA_MODES:
        raise IdentityFormatError(f"unknown data_mode: {protocol['data_mode']}")
    if protocol["data_mode"] != "synthetic":
        # 本轮不输出真实资格成功；qualified 接口只能以合成小例测逻辑。
        raise IdentityFormatError(
            f"data_mode={protocol['data_mode']} not accepted this round; "
            "formal outputs are synthetic only"
        )
    if not isinstance(protocol.get("synthetic"), bool) or not protocol["synthetic"]:
        raise IdentityFormatError("protocol.synthetic must be true")
    tz = protocol.get("timezone")
    if not tz:
        raise IdentityFormatError("protocol.timezone required")
    cutoff = protocol.get("evaluation_cutoff")
    if cutoff is not None:
        ts = pd.Timestamp(cutoff)
        if ts.tzinfo is None:
            raise IdentityFormatError("evaluation_cutoff must be timezone-aware")


def require_tz_aware(timestamp, field_name: str) -> pd.Timestamp:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        raise IdentityFormatError(f"{field_name} must be timezone-aware: {timestamp!r}")
    return ts


def build_metadata(
    *,
    reference: str,
    card: dict,
    card_kind: str,
    protocol: dict,
    entity_axis: str,
    value_type: str,
    data_identity: dict,
    code_identity: dict,
    calendar: dict,
    time_evidence: dict,
    universe_identity: dict | None = None,
) -> dict:
    if card_kind not in {"registered", "candidate"}:
        raise IdentityFormatError(f"unknown card_kind: {card_kind}")
    if entity_axis not in ENTITY_AXES:
        raise IdentityFormatError(f"unknown entity_axis: {entity_axis}")
    metadata = {
        "reference": reference,
        "card": card,
        "card_kind": card_kind,
        "type": card["type"],
        "unit": card["definition"]["unit"],
        "purpose": protocol["kind"],
        "entity_axis": entity_axis,
        "value_type": value_type,
        "protocol": {
            "protocol_id": protocol["protocol_id"],
            "version": protocol["version"],
            "kind": protocol["kind"],
            "data_mode": protocol["data_mode"],
            "sha256": protocol_sha256(protocol),
        },
        "data_identity": data_identity,
        "code_identity": code_identity,
        "calendar": calendar,
        "time_evidence": time_evidence,
        "synthetic": True,
        "definition_status": card["status"]["definition_clarity"],
        "data_status": "synthetic_input",
        "implementation_status": card["status"]["implementation"],
        "effectiveness_status": card["status"]["effectiveness"],
        "production_authorization": "not_authorized",
    }
    if universe_identity is not None:
        metadata["universe_identity"] = universe_identity
    missing = METADATA_REQUIRED - metadata.keys()
    if missing:
        raise IdentityFormatError(f"metadata missing keys: {sorted(missing)}")
    return metadata


def validate_values_frame(values: pd.DataFrame) -> pd.DataFrame:
    """行键唯一且列完整；缺值行保留。"""
    if list(values.columns) != VALUES_COLUMNS:
        raise IdentityFormatError(f"values columns must be {VALUES_COLUMNS}")
    if values.duplicated(["observation_date", "entity_id"]).any():
        raise IdentityFormatError("duplicate (observation_date, entity_id) rows")
    return values
