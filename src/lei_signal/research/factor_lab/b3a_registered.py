"""B8 registered research entry for two B3-a synthetic-only descriptions.

The complete cards come from the versioned registry. Numerical calculation reuses
B3-a's existing functions; this module never translates draft references into
registered identities and does not make a trading decision.
"""
from __future__ import annotations

import hashlib

from lei_signal.research.definitions import ROOT, load_registry, resolve
from lei_signal.research.factor_lab.b3a_factors import (
    _bars_from_inputs,
    _cost_basis_values,
    _pullback_ma_values,
)
from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    ResearchBatch,
    build_metadata,
    canonical_json,
    fingerprint_path,
    validate_protocol,
    validate_values_frame,
)

# Captured from resolved definitions.v1.json v1.3.5, SHA256
# 8a3b7af26197c362f43604576ae4321f19dece6ec60c6decea84c431aa0a6421.
# Pin the *calculation contract*, not lifecycle/status: the controller may append
# verified evidence without invalidating the published 1.0.0 calculation.
_CONTRACT_FIELDS = (
    "id", "version", "type", "uses", "not_for", "spec_anchor", "spec_layer",
    "definition", "input", "universe", "time", "dependencies",
)
_BINDINGS = {
    "trend.cost_basis_distance20@1.0.0": "f5a10d8dc5648feec5373b7a634769014c1b3e70b9c68491b0f485d897096098",
    "mixed.pullback_ma_distance@1.0.0": "99b62245216bf8fa8e5d687206ac7959bd5e816a7f6c7fe4c3dfa0eec34554dd",
}
_CODE_FILES = (
    "src/lei_signal/research/factor_lab/b3a_registered.py",
    "src/lei_signal/research/factor_lab/b3a_factors.py",
    "src/lei_signal/research/factor_lab/contracts.py",
    "src/lei_signal/research/definitions.py",
    "src/lei_signal/features/indicators.py",
)


def calculate_registered_b3a(
    reference: str, inputs: dict, *, protocol: dict
) -> ResearchBatch:
    """Resolve and calculate one exact registered card using synthetic OHLCV.

    Unknown/draft versions, semantic drift, or other data modes fail closed.
    Missing numerical observations remain rows with their original reason.
    """
    if reference not in _BINDINGS:
        raise IdentityFormatError(f"unknown exact registered reference: {reference}")
    validate_protocol(protocol, expected_kinds={"calculation_only"})
    if not isinstance(inputs, dict):
        raise IdentityFormatError("inputs must be a dict")
    registry = load_registry()
    card = resolve(registry, reference)
    if card["id"] + "@" + card["version"] != reference:
        raise IdentityFormatError(f"registered identity drift: {reference}")
    contract = {field: card[field] for field in _CONTRACT_FIELDS}
    digest = hashlib.sha256(canonical_json(contract).encode("utf-8")).hexdigest()
    if digest != _BINDINGS[reference]:
        raise IdentityFormatError(f"registered binding drift: {reference}")

    bars = _bars_from_inputs(reference, inputs)
    if reference == "trend.cost_basis_distance20@1.0.0":
        values, findings = _cost_basis_values(reference, bars)
        ambiguity = (
            "definition.parameters 按K线行数 shift(20)，但 universe.warmup 写21根有效报价；"
            "中间缺价时两者结果冲突，等待登记语义裁决"
        )
    else:
        values, findings = _pullback_ma_values(reference, bars)
        ambiguity = (
            "中途缺价后旧 seeded EMA 不再恢复，卡片未明确缺价后是否重启；"
            "即使SMA120窗口恢复完整六线仍不可算，等待登记语义裁决"
        )
    findings.append({
        "code": "registered_identity_binding_ok",
        "detail": "正式编号与登记计算字段指纹吻合；复用旧数值函数；并非语义完整验证",
    })
    findings.append({"code": "semantic_blocked", "detail": ambiguity})
    metadata = build_metadata(
        reference=reference,
        card=card,
        card_kind="registered",
        protocol=protocol,
        entity_axis="instrument",
        value_type="continuous",
        data_identity={
            "inputs": {key: {"kind": type(value).__name__} for key, value in inputs.items()},
            "declared_inputs": protocol.get("inputs", {}),
            "synthetic": True,
            "resolved_contract_sha256": digest,
            "registry_sha256": fingerprint_path(ROOT / "docs/research/definitions.v1.json")["sha256"],
        },
        code_identity={
            "modules": [dict(fingerprint_path(ROOT / path), path=path) for path in _CODE_FILES]
        },
        calendar={"timezone": protocol["timezone"], "note": "合成日历，真实交易日历未验证"},
        time_evidence={
            "observation_time": "合成日线收盘（只用当日及此前价格）",
            "evaluation_cutoff": protocol.get("evaluation_cutoff"),
        },
    )
    # Keep the exact resolved card unaltered, but do not imply its semantic
    # consistency was established merely because the reference and hash match.
    metadata["definition_status"] = "semantic_review_pending"
    metadata["implementation_status"] = "diagnostic_only; semantic_blocked"
    return ResearchBatch(validate_values_frame(values), metadata, findings)
