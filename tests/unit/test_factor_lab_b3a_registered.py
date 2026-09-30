"""Frozen B8 synthetic checks for exact registered references, never draft aliases."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research.factor_lab.contracts import IdentityFormatError
from lei_signal.research.factor_lab.b3a_factors import calculate_b3a_batch
from lei_signal.research.factor_lab.b3a_registered import calculate_registered_b3a

FIXTURES = Path(__file__).resolve().parents[2] / "docs/experiments/raw/factor-b3a-2026-09-20/fixtures"
COST = "trend.cost_basis_distance20@1.0.0"
PULLBACK = "mixed.pullback_ma_distance@1.0.0"


def bars(fixture: str) -> dict:
    payload = json.loads((FIXTURES / (fixture + ".json")).read_text())
    return {"bars": {payload["symbol"]: pd.DataFrame(payload["bars"]).set_index("date")}}


def protocol(**changes) -> dict:
    p = {"protocol_id": "B8-frozen", "version": "1.0.0", "kind": "calculation_only",
         "data_mode": "synthetic", "synthetic": True, "timezone": "Asia/Shanghai",
         "evaluation_cutoff": "2026-09-21T15:00:00+08:00"}
    p.update(changes)
    return p


def run(reference: str, fixture: str = "fx3-step", **p):
    return calculate_registered_b3a(reference, bars(fixture), protocol=protocol(**p))


@pytest.mark.parametrize("reference,offset,expected", [(COST, 119, .1),
                                                     (PULLBACK, 119, .0896226415)])
def test_exact_registered_reference_produces_values_and_complete_identity(reference, offset, expected):
    batch = run(reference)
    row = batch.values.iloc[offset]
    assert math.isclose(row.value, expected, abs_tol=1e-6)
    assert row.missing_reason is None
    meta = batch.metadata
    assert meta["reference"] == reference
    assert meta["card_kind"] == "registered"
    assert meta["card"]["id"] + "@" + meta["card"]["version"] == reference
    assert meta["card"]["input"]["frequency"] == "daily"
    assert meta["synthetic"] is True and meta["production_authorization"] == "not_authorized"
    assert meta["data_identity"]["synthetic"] is True
    assert meta["definition_status"] == "semantic_review_pending"
    assert meta["implementation_status"] == "diagnostic_only; semantic_blocked"
    assert any(f["code"] == "semantic_blocked" for f in batch.findings)


@pytest.mark.parametrize("reference,fixture,offset,reason", [
    (COST, "fx2-short", 10, "warmup_history_insufficient"),
    (COST, "fx4-missing-close", 50, "price_missing"),
    (COST, "fx4-missing-close", 70, "warmup_history_insufficient"),
    (COST, "fx5-zero-denominator", 20, "zero_denominator"),
    (PULLBACK, "fx3-step", 118, "warmup_history_insufficient"),
    (PULLBACK, "fx4-missing-close", 50, "price_missing"),
    (PULLBACK, "fx4-missing-close", 100, "warmup_history_insufficient"),
])
def test_missing_reason_is_preserved(reference, fixture, offset, reason):
    row = run(reference, fixture).values.iloc[offset]
    assert pd.isna(row.value) and row.missing_reason == reason


@pytest.mark.parametrize("reference", ["candidate:trend.cost_basis_distance20@draft-1",
                                       "candidate:mixed.pullback_ma_distance@draft-1",
                                       "trend.cost_basis_distance20",
                                       "trend.cost_basis_distance20@2.0.0"])
def test_non_exact_identity_rejected(reference):
    with pytest.raises(IdentityFormatError, match="exact registered reference"):
        run(reference, "fx2-short")


@pytest.mark.parametrize("bad", [dict(synthetic=False), dict(data_mode="qualified"),
                                   dict(data_mode="historical_reconstruction"),
                                   dict(kind="predictive_diagnostic")])
def test_only_explicit_synthetic_calculation_accepted(bad):
    with pytest.raises(IdentityFormatError):
        run(COST, "fx2-short", **bad)


@pytest.mark.parametrize("field,mutate", [
    ("definition", lambda c: c["definition"].update(formula="close[t]/close[t-19]-1")),
    ("parameters", lambda c: c["definition"]["parameters"].update(window=19)),
    ("input", lambda c: c["input"].update(price_basis="未经复权")),
    ("universe", lambda c: c["universe"].update(warmup="19根即可")),
    ("time", lambda c: c["time"].update(available_at="次日")),
])
def test_resolved_card_drift_rejected(monkeypatch, field, mutate):
    import lei_signal.research.factor_lab.b3a_registered as registered
    original = registered.resolve

    def changed(registry, reference):
        card = copy.deepcopy(original(registry, reference))
        mutate(card)
        return card

    monkeypatch.setattr(registered, "resolve", changed)
    with pytest.raises(IdentityFormatError, match="binding drift"):
        run(COST, "fx2-short")


def test_resolved_identity_drift_rejected(monkeypatch):
    import lei_signal.research.factor_lab.b3a_registered as registered
    original = registered.resolve

    def changed(registry, reference):
        card = copy.deepcopy(original(registry, reference))
        card["version"] = "1.0.1"
        return card

    monkeypatch.setattr(registered, "resolve", changed)
    with pytest.raises(IdentityFormatError, match="identity drift"):
        run(COST, "fx2-short")


def test_draft_entry_still_rejects_formal_reference():
    with pytest.raises(IdentityFormatError, match="unknown B3-a candidate"):
        calculate_b3a_batch(COST, bars("fx2-short"), protocol=protocol())


def test_lifecycle_evidence_change_does_not_change_calculation_contract(monkeypatch):
    import lei_signal.research.factor_lab.b3a_registered as registered
    original = registered.resolve

    def changed(registry, reference):
        card = copy.deepcopy(original(registry, reference))
        card["lifecycle"]["state"] = "verified"
        card["status"]["implementation"] = "synthetic rows independently verified"
        return card

    monkeypatch.setattr(registered, "resolve", changed)
    assert math.isclose(run(COST).values.iloc[119].value, 0.1, abs_tol=1e-6)


def test_middle_missing_price_exposes_card_warmup_ambiguity():
    frame = pd.DataFrame({"open": [100.] * 21, "high": [100.] * 21,
                          "low": [100.] * 21, "close": [100.] * 21,
                          "volume": [1000.] * 21},
                         index=[f"SYN-{i:03d}" for i in range(21)])
    frame.iloc[10, frame.columns.get_loc("close")] = float("nan")
    result = calculate_registered_b3a(COST, {"bars": {"SYN.EDGE": frame}}, protocol=protocol())
    assert frame.close.count() == 20  # Card universe says 21 valid quotations.
    assert result.values.iloc[20].value == 0.0  # Row-based shift(20) can calculate.
