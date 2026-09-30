"""B10 synthetic-only checks for the two exact 2.0.0 research descriptions."""
from __future__ import annotations

import copy
import math

import pandas as pd
import pytest

from lei_signal.research.factor_lab.contracts import IdentityFormatError
from lei_signal.research.factor_lab.b3a_registered import calculate_registered_b3a
from lei_signal.research.factor_lab.b3a_registered_v2 import calculate_registered_b3a_v2

COST = "trend.cost_basis_distance20@2.0.0"
PULLBACK = "mixed.pullback_ma_distance@2.0.0"


def protocol(**changes):
    result = {"protocol_id": "B10-synthetic", "version": "1.0.0",
              "kind": "calculation_only", "data_mode": "synthetic", "synthetic": True,
              "timezone": "Asia/Shanghai", "evaluation_cutoff": "2026-09-21T15:00:00+08:00"}
    result.update(changes)
    return result


def bars(prices):
    return {"bars": {"SYN": pd.DataFrame({
        "open": [100 if x is None else x for x in prices],
        "high": [100 if x is None else x for x in prices],
        "low": [100 if x is None else x for x in prices],
        "close": prices, "volume": [1000] * len(prices),
    }, index=[f"SYN-{i:04d}" for i in range(len(prices))])}}


def run(reference, prices, **changes):
    return calculate_registered_b3a_v2(reference, bars(prices), protocol=protocol(**changes))


@pytest.mark.parametrize("reference", [COST, PULLBACK])
def test_exact_v2_identity_and_no_v1_ambiguity(reference):
    result = run(reference, [100] * 130)
    meta = result.metadata
    assert meta["reference"] == reference
    assert meta["card_kind"] == "registered"
    assert meta["card"]["id"] + "@" + meta["card"]["version"] == reference
    assert meta["data_identity"]["registry_sha256"]
    assert meta["data_identity"]["resolved_contract_sha256"]
    assert meta["code_identity"]["modules"]
    assert meta["synthetic"] is True
    assert meta["production_authorization"] == "not_authorized"
    assert meta["implementation_status"] == "v2 synthetic calculation executed; independent controller review pending"
    assert "semantic_blocked" not in str(meta)
    assert not any(f["code"] == "semantic_blocked" for f in result.findings)


@pytest.mark.parametrize("reference", [
    "trend.cost_basis_distance20@1.0.0", "mixed.pullback_ma_distance@1.0.0",
    "candidate:trend.cost_basis_distance20@draft-1", "trend.cost_basis_distance20",
    "trend.cost_basis_distance20@latest", "mixed.pullback_ma_distance@2.0.1",
])
def test_v2_rejects_other_identifiers(reference):
    with pytest.raises(IdentityFormatError, match="exact registered reference"):
        run(reference, [100] * 22)


@pytest.mark.parametrize("changes", [
    {"synthetic": False}, {"data_mode": "qualified"},
    {"data_mode": "historical_reconstruction"}, {"kind": "predictive_diagnostic"},
])
def test_v2_only_accepts_synthetic_calculation(changes):
    with pytest.raises(IdentityFormatError):
        run(COST, [100] * 22, **changes)


@pytest.mark.parametrize("section,field,value", [
    ("definition", "endpoints", "some other row"),
    ("definition", "nan_policy", "fill the missing price"),
    ("universe", "warmup", "21 valid prices"),
    ("input", "price_basis", "different price"),
    ("time", "available_at", "next day"),
])
def test_calculation_contract_drift_rejected(monkeypatch, section, field, value):
    import lei_signal.research.factor_lab.b3a_registered_v2 as module
    original = module.resolve

    def altered(registry, reference):
        card = copy.deepcopy(original(registry, reference))
        card[section][field] = value
        return card

    monkeypatch.setattr(module, "resolve", altered)
    with pytest.raises(IdentityFormatError, match="binding drift"):
        run(COST, [100] * 22)


def test_lifecycle_and_status_changes_do_not_alter_calculation(monkeypatch):
    import lei_signal.research.factor_lab.b3a_registered_v2 as module
    original = module.resolve

    def status_only(registry, reference):
        card = copy.deepcopy(original(registry, reference))
        card["lifecycle"]["state"] = "verified"
        card["status"]["implementation"] = "future independent review"
        return card

    monkeypatch.setattr(module, "resolve", status_only)
    assert run(COST, [100] * 21).values.iloc[20].value == 0


def test_cost_uses_raw_row_and_current_missing_precedence():
    prices = [100] * 42
    prices[10] = None
    prices[21] = None
    result = run(COST, prices).values
    assert result.iloc[20].value == 0
    assert result.iloc[21].missing_reason == "price_missing"
    assert result.iloc[10].missing_reason == "price_missing"
    assert result.iloc[20].value == 0  # missing middle row does not erase row 0
    assert result.iloc[30].missing_reason == "warmup_history_insufficient"


def test_cost_lag_endpoint_missing_and_zero_are_distinct():
    prices = [0] + [100] * 20 + [None] + [100] * 20
    values = run(COST, prices).values
    assert values.iloc[19].missing_reason == "warmup_history_insufficient"
    assert values.iloc[20].missing_reason == "zero_denominator"
    assert values.iloc[21].missing_reason == "price_missing"
    assert values.iloc[41].missing_reason == "warmup_history_insufficient"


def test_pullback_ema_does_not_reseed_after_gap_even_if_sma_recovers():
    prices = [100] * 130 + [None] + [100] * 140
    values = run(PULLBACK, prices).values
    assert values.iloc[119].value == 0
    assert values.iloc[130].missing_reason == "price_missing"
    assert pd.isna(values.iloc[260].value)
    assert values.iloc[260].missing_reason == "warmup_history_insufficient"


def test_pullback_seed_gap_is_permanent_and_zero_ma_has_separate_reason():
    gap = [100] * 20 + [None] + [100] * 130
    assert run(PULLBACK, gap).values.iloc[-1].missing_reason == "warmup_history_insufficient"
    zero = [0] * 125 + [1] * 20
    assert run(PULLBACK, zero).values.iloc[119].missing_reason == "zero_denominator"
    assert math.isclose(run(PULLBACK, zero).values.iloc[144].value, 0.0)


def test_old_registered_entry_unchanged_and_rejects_v2():
    with pytest.raises(IdentityFormatError):
        calculate_registered_b3a(COST, bars([100] * 21), protocol=protocol())
    previous = calculate_registered_b3a(COST.replace("@2.0.0", "@1.0.0"),
                                        bars([100] * 21), protocol=protocol())
    assert previous.values.iloc[20].value == 0
    assert previous.metadata["implementation_status"] == "diagnostic_only; semantic_blocked"
