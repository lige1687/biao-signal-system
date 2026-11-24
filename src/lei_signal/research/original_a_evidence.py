"""Small, research-only checks for original Module A evidence.

The caller asserts provenance, structural correctness, and current validity.
These functions cannot inspect charts or establish the full A rule or an order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


_ROLES = frozenset({"bottom", "lower_trend"})
_BASES = frozenset({"original_verified", "research_proxy", "unknown"})


def _aware(value: datetime | None, name: str) -> None:
    if value is not None and (
        not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None
    ):
        raise ValueError(f"{name} must be an aware datetime or None")


@dataclass(frozen=True)
class ConditionEvidence:
    """Caller-qualified observation; ``valid_at`` is an explicit fresh assertion."""

    value: bool | None
    asset: str
    role: str
    timeframe: str
    definition_ref: str
    source_ref: str
    basis: str
    observed_at: datetime | None
    available_at: datetime | None
    valid_at: datetime | None
    invalidated_at: datetime | None = None

    def __post_init__(self) -> None:
        if type(self.value) is not bool and self.value is not None:
            raise ValueError("value must be bool or None")
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("asset must be a nonempty string")
        if not isinstance(self.timeframe, str) or not self.timeframe.strip():
            raise ValueError("timeframe must be a nonempty string")
        if not isinstance(self.role, str) or self.role not in _ROLES:
            raise ValueError("unknown evidence role")
        if not isinstance(self.basis, str) or self.basis not in _BASES:
            raise ValueError("unknown evidence basis")
        for name in ("definition_ref", "source_ref"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be a string")
        for name in ("observed_at", "available_at", "valid_at", "invalidated_at"):
            _aware(getattr(self, name), name)
        if (self.observed_at is not None and self.available_at is not None
                and self.observed_at > self.available_at):
            raise ValueError("observed_at cannot follow available_at")


def _component(evidence: ConditionEvidence | None, role: str, asset: str, timeframe: str,
               decision_at: datetime) -> dict:
    if evidence is None:
        return {"raw_value": None, "qualified_value": None,
                "asset": None, "role": None, "timeframe": None,
                "definition_ref": None, "source_ref": None, "basis": None,
                "observed_at": None, "available_at": None, "valid_at": None,
                "invalidated_at": None, "reasons": ["missing_evidence"]}
    if not isinstance(evidence, ConditionEvidence):
        raise ValueError("component must be ConditionEvidence or None")
    reasons = []
    if evidence.asset != asset:
        reasons.append("asset_mismatch")
    if evidence.role != role:
        reasons.append("role_mismatch")
    if evidence.timeframe != timeframe:
        reasons.append("timeframe_mismatch")
    if not evidence.definition_ref.strip():
        reasons.append("missing_definition_ref")
    if not evidence.source_ref.strip():
        reasons.append("missing_source_ref")
    if evidence.basis != "original_verified":
        reasons.append("basis_not_original_verified")
    if evidence.observed_at is None:
        reasons.append("missing_observed_at")
    if evidence.available_at is None:
        reasons.append("missing_available_at")
    elif evidence.available_at > decision_at:
        reasons.append("not_available_at_decision")
    if evidence.valid_at is None:
        reasons.append("missing_valid_at")
    elif evidence.valid_at != decision_at:
        reasons.append("not_valid_at_decision")
    if evidence.invalidated_at is not None and evidence.invalidated_at <= decision_at:
        reasons.append("invalidated_at_decision")
    if evidence.value is None:
        reasons.append("missing_value")
    return {"raw_value": evidence.value,
            "qualified_value": evidence.value if not reasons else None,
            "asset": evidence.asset, "role": evidence.role,
            "timeframe": evidence.timeframe,
            "definition_ref": evidence.definition_ref,
            "source_ref": evidence.source_ref, "basis": evidence.basis,
            "observed_at": evidence.observed_at.isoformat() if evidence.observed_at else None,
            "available_at": evidence.available_at.isoformat() if evidence.available_at else None,
            "valid_at": evidence.valid_at.isoformat() if evidence.valid_at else None,
            "invalidated_at": evidence.invalidated_at.isoformat() if evidence.invalidated_at else None,
            "reasons": reasons}


def evaluate_confirmation(bottom: ConditionEvidence | None,
                          lower_trend: ConditionEvidence | None, *, asset: str,
                          bottom_timeframe: str, lower_timeframe: str,
                          decision_at: datetime) -> dict:
    """Evaluate only original A's bottom AND lower-level trend structure.

    Source/definition verification and ``valid_at`` freshness are caller assertions.
    No prior true value is carried forward automatically.
    """
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("asset must be a nonempty string")
    for name, value in (("bottom_timeframe", bottom_timeframe),
                        ("lower_timeframe", lower_timeframe)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string")
    _aware(decision_at, "decision_at")
    if decision_at is None:
        raise ValueError("decision_at is required")
    components = {
        "bottom": _component(bottom, "bottom", asset, bottom_timeframe, decision_at),
        "lower_trend": _component(lower_trend, "lower_trend", asset, lower_timeframe, decision_at),
    }
    failed = [name for name, item in components.items() if item["qualified_value"] is False]
    unknown = [name for name, item in components.items() if item["qualified_value"] is None]
    reasons = [f"{name}:{reason}" for name, item in components.items()
               for reason in item["reasons"]]
    return {"scope": "original_A_structure_only",
            "decision_at": decision_at.isoformat(),
            "status": "fail" if failed else "unknown" if unknown else "pass",
            "components": components, "reasons": reasons,
            "unknown_components": unknown, "failed_components": failed,
            "not_full_A": True, "order_allowed": False}


def _positive_decimal(value: object, name: str) -> Decimal:
    if type(value) is bool or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{name} must be a finite positive number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a finite positive number") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return result


def reward_risk_bounds(*, entry: int | float | Decimal, stop: int | float | Decimal,
                       target_low: int | float | Decimal,
                       target_high: int | float | Decimal,
                       required_rr: int | float | Decimal,
                       definition_qualified: bool = False) -> dict:
    """Arithmetic bounds only; the caller verifies first target and invalidation."""
    if type(definition_qualified) is not bool:
        raise ValueError("definition_qualified must be bool")
    entry, stop, target_low, target_high, required_rr = (
        _positive_decimal(value, name) for name, value in (
            ("entry", entry), ("stop", stop), ("target_low", target_low),
            ("target_high", target_high), ("required_rr", required_rr)))
    if not stop < entry < target_low <= target_high:
        raise ValueError("expected stop < entry < target_low <= target_high")
    risk = entry - stop
    rr_low = (target_low - entry) / risk
    rr_high = (target_high - entry) / risk
    relation = ("all_meet" if rr_low >= required_rr else
                "all_below" if rr_high < required_rr else
                "depends_on_target_price")
    status = ("pass" if relation == "all_meet" else
              "fail" if relation == "all_below" else "unknown") if definition_qualified else "unknown"
    return {"rr_low": rr_low, "rr_high": rr_high,
            "numeric_relation": relation, "qualified_status": status,
            "not_full_A": True}
