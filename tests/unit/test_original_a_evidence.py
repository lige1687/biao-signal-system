"""Synthetic evidence checks; no market observations or trading conclusions."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lei_signal.research.original_a_evidence import (
    ConditionEvidence, evaluate_confirmation as _evaluate_confirmation, reward_risk_bounds,
)


UTC = timezone.utc
DECISION = datetime(2026, 10, 18, 15, tzinfo=UTC)


def evidence(initial_value, initial_role, **changes):
    fields = dict(value=initial_value, asset="ETF", role=initial_role,
                  timeframe="1d" if initial_role == "bottom" else "60m",
                  definition_ref="original:4.4",
                  source_ref="synthetic:1", basis="original_verified",
                  observed_at=DECISION - timedelta(minutes=2),
                  available_at=DECISION - timedelta(minutes=1), valid_at=DECISION)
    fields.update(changes)
    return ConditionEvidence(**fields)


def evaluate_confirmation(bottom, lower_trend, *, asset, decision_at,
                          bottom_timeframe="1d", lower_timeframe="60m"):
    return _evaluate_confirmation(bottom, lower_trend, asset=asset,
                                  bottom_timeframe=bottom_timeframe,
                                  lower_timeframe=lower_timeframe,
                                  decision_at=decision_at)


@pytest.mark.parametrize("bottom,trend,status,unknown,failed", [
    (True, True, "pass", [], []),
    (True, False, "fail", [], ["lower_trend"]),
    (True, None, "unknown", ["lower_trend"], []),
    (False, True, "fail", [], ["bottom"]),
    (False, False, "fail", [], ["bottom", "lower_trend"]),
    (False, None, "fail", ["lower_trend"], ["bottom"]),
    (None, True, "unknown", ["bottom"], []),
    (None, False, "fail", ["bottom"], ["lower_trend"]),
    (None, None, "unknown", ["bottom", "lower_trend"], []),
])
def test_three_valued_and(bottom, trend, status, unknown, failed):
    result = evaluate_confirmation(evidence(bottom, "bottom"),
                                   evidence(trend, "lower_trend"),
                                   asset="ETF", decision_at=DECISION)
    assert (result["status"], result["unknown_components"], result["failed_components"]) == (
        status, unknown, failed)
    assert result["scope"] == "original_A_structure_only"
    assert result["decision_at"] == DECISION.isoformat()
    assert result["components"]["bottom"]["raw_value"] is bottom
    assert result["not_full_A"] and result["order_allowed"] is False


@pytest.mark.parametrize("value", [True, False])
def test_proxy_truth_and_falsehood_do_not_decide_original(value):
    result = evaluate_confirmation(evidence(value, "bottom", basis="research_proxy"),
                                   evidence(True, "lower_trend"), asset="ETF",
                                   decision_at=DECISION)
    assert result["status"] == "unknown"
    assert result["components"]["bottom"]["raw_value"] is value
    assert result["components"]["bottom"]["qualified_value"] is None


def test_future_arrival_and_same_instant_with_different_timezone():
    late = evidence(True, "bottom", observed_at=DECISION,
                    available_at=DECISION + timedelta(minutes=1))
    result = evaluate_confirmation(late, evidence(True, "lower_trend"),
                                   asset="ETF", decision_at=DECISION)
    assert result["status"] == "unknown"
    assert "bottom:not_available_at_decision" in result["reasons"]
    plus_eight = timezone(timedelta(hours=8))
    equivalent = evidence(True, "bottom", valid_at=DECISION.astimezone(plus_eight))
    assert evaluate_confirmation(equivalent, evidence(True, "lower_trend"),
                                 asset="ETF", decision_at=DECISION)["status"] == "pass"


@pytest.mark.parametrize("changes,reason", [
    ({"valid_at": DECISION - timedelta(days=1)}, "not_valid_at_decision"),
    ({"invalidated_at": DECISION}, "invalidated_at_decision"),
    ({"source_ref": " "}, "missing_source_ref"),
    ({"asset": "OTHER"}, "asset_mismatch"),
    ({"role": "lower_trend"}, "role_mismatch"),
    ({"timeframe": "1w"}, "timeframe_mismatch"),
])
def test_unqualified_observations_remain_unknown(changes, reason):
    result = evaluate_confirmation(evidence(True, "bottom", **changes),
                                   evidence(True, "lower_trend"), asset="ETF",
                                   decision_at=DECISION)
    assert result["status"] == "unknown"
    assert f"bottom:{reason}" in result["reasons"]


def test_lower_trend_with_wrong_timeframe_cannot_pass():
    result = evaluate_confirmation(evidence(True, "bottom"),
                                   evidence(True, "lower_trend", timeframe="1w"),
                                   asset="ETF", decision_at=DECISION)
    assert result["status"] == "unknown"
    assert "lower_trend:timeframe_mismatch" in result["reasons"]
    assert result["components"]["lower_trend"]["timeframe"] == "1w"


def test_component_metadata_is_traceable_even_if_unqualified():
    bottom = evidence(False, "bottom", basis="research_proxy",
                      invalidated_at=DECISION)
    result = evaluate_confirmation(bottom, None, asset="ETF", decision_at=DECISION)
    item = result["components"]["bottom"]
    assert item["raw_value"] is False and item["qualified_value"] is None
    assert {key: item[key] for key in ("asset", "role", "timeframe", "definition_ref",
                                     "source_ref", "basis")} == {
        "asset": "ETF", "role": "bottom", "timeframe": "1d",
        "definition_ref": "original:4.4", "source_ref": "synthetic:1",
        "basis": "research_proxy"}
    for name in ("observed_at", "available_at", "valid_at", "invalidated_at"):
        assert item[name] == getattr(bottom, name).isoformat()
        assert result["components"]["lower_trend"][name] is None
    assert result["components"]["lower_trend"]["source_ref"] is None


def test_qualified_false_dominates_unknown_without_hiding_gap():
    result = evaluate_confirmation(evidence(False, "bottom"), None,
                                   asset="ETF", decision_at=DECISION)
    assert result["status"] == "fail"
    assert result["failed_components"] == ["bottom"]
    assert result["unknown_components"] == ["lower_trend"]
    assert "lower_trend:missing_evidence" in result["reasons"]


@pytest.mark.parametrize("changes", [
    {"value": 1}, {"value": "false"}, {"basis": "verified"},
    {"basis": []}, {"role": "trend"}, {"role": []},
    {"timeframe": " "}, {"timeframe": None},
    {"observed_at": datetime(2026, 10, 18, 14, 58)},
    {"available_at": DECISION - timedelta(minutes=3)},
])
def test_bad_evidence_rejected(changes):
    with pytest.raises(ValueError):
        evidence(True, "bottom", **changes)


def test_bad_decision_time_rejected():
    with pytest.raises(ValueError):
        evaluate_confirmation(None, None, asset="ETF", decision_at=DECISION.replace(tzinfo=None))


@pytest.mark.parametrize("field,value", [
    ("asset", " "), ("bottom_timeframe", " "), ("lower_timeframe", None),
])
def test_required_call_identity_rejected(field, value):
    fields = dict(asset="ETF", bottom_timeframe="1d", lower_timeframe="60m",
                  decision_at=DECISION)
    fields[field] = value
    with pytest.raises(ValueError):
        _evaluate_confirmation(None, None, **fields)


def test_call_requires_both_explicit_timeframes():
    with pytest.raises(TypeError):
        _evaluate_confirmation(None, None, asset="ETF", decision_at=DECISION)


def test_reward_risk_crosses_three_and_requires_definition_qualification():
    values = dict(entry=100, stop=97, target_low=108, target_high=110, required_rr=3)
    approximate = reward_risk_bounds(**values)
    assert approximate["rr_low"] == Decimal("8") / Decimal("3")
    assert approximate["rr_high"] == Decimal("10") / Decimal("3")
    assert approximate["numeric_relation"] == "depends_on_target_price"
    assert approximate["qualified_status"] == "unknown"
    assert reward_risk_bounds(**values, definition_qualified=True)["qualified_status"] == "unknown"


def test_threshold_equality_is_meeting_only_when_qualified():
    values = dict(entry=100, stop=97, target_low=109, target_high=109, required_rr=3)
    approximate = reward_risk_bounds(**values)
    qualified = reward_risk_bounds(**values, definition_qualified=True)
    assert approximate["numeric_relation"] == "all_meet"
    assert approximate["qualified_status"] == "unknown"
    assert qualified["rr_low"] == qualified["rr_high"] == Decimal("3")
    assert qualified["qualified_status"] == "pass"
    assert qualified["not_full_A"] is True


def test_all_below_can_fail_only_when_definition_qualified():
    values = dict(entry=100, stop=97, target_low=107, target_high=108, required_rr=3)
    assert reward_risk_bounds(**values)["qualified_status"] == "unknown"
    result = reward_risk_bounds(**values, definition_qualified=True)
    assert (result["numeric_relation"], result["qualified_status"]) == ("all_below", "fail")


@pytest.mark.parametrize("changes", [
    {"entry": True}, {"stop": 0}, {"target_low": float("nan")},
    {"target_high": float("inf")}, {"required_rr": float("-inf")},
    {"target_low": 100}, {"target_high": 108},
    {"definition_qualified": 1},
])
def test_invalid_reward_risk_inputs(changes):
    values = dict(entry=100, stop=97, target_low=109, target_high=110,
                  required_rr=3, definition_qualified=False)
    values.update(changes)
    with pytest.raises(ValueError):
        reward_risk_bounds(**values)
