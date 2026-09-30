"""B10 exact 2.0.0 synthetic research descriptions; not a trading signal.

Calculation delegates only to the previously tested numerical B3-a functions.
The resolved card's calculation semantics are pinned separately from its mutable
evidence and lifecycle annotations.
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

_CONTRACT_FIELDS = (
    "id", "version", "type", "uses", "not_for", "spec_anchor", "spec_layer",
    "definition", "input", "universe", "time", "dependencies",
)
_BINDINGS = {
    "trend.cost_basis_distance20@2.0.0": "e0fb926d9cbecadad67fcc0b3343e68040085de5c873c57e1b1c80d348bdc1d7",
    "mixed.pullback_ma_distance@2.0.0": "fd6013d8ee302d0e99e7d6dce6a587a2efbeed0c475f8c2d9a88a87e044138a7",
}
_CODE_FILES = (
    "src/lei_signal/research/factor_lab/b3a_registered_v2.py",
    "src/lei_signal/research/factor_lab/b3a_factors.py",
    "src/lei_signal/research/factor_lab/contracts.py",
    "src/lei_signal/research/definitions.py",
    "src/lei_signal/features/indicators.py",
)


def calculate_registered_b3a_v2(
    reference: str, inputs: dict, *, protocol: dict
) -> ResearchBatch:
    """Calculate one exact registered v2 card on synthetic OHLCV rows only."""
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
    if reference == "trend.cost_basis_distance20@2.0.0":
        values, findings = _cost_basis_values(reference, bars)
    else:
        values, findings = _pullback_ma_values(reference, bars)
    findings.append({
        "code": "registered_v2_calculation_binding_ok",
        "detail": "2.0.0精确计算字段与登记相符；仅合成逐行计算，不证明真实行情或投资价值",
    })
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
    # The frozen registry card describes its pre-execution state; preserve the
    # full card, but report this invocation's actual status at metadata level.
    metadata["implementation_status"] = "v2 synthetic calculation executed; independent controller review pending"
    return ResearchBatch(validate_values_frame(values), metadata, findings)
