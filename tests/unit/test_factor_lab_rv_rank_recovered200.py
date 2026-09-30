"""B14 tests from frozen, hand-designed synthetic price paths."""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from lei_signal.research import definitions
from lei_signal.research.factor_lab.adapters import calculate_batch
from lei_signal.research.factor_lab.contracts import IdentityFormatError

RV_REF = "mixed.rv_percentile@1.0.0"
RECOVERED_REF = "trend.recovered200@1.0.0"


def protocol() -> dict:
    return {
        "protocol_id": "factor-b14-test",
        "version": "1.0.0",
        "kind": "calculation_only",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2026-09-21T15:00:00+08:00",
    }


def panel(rows: int = 810) -> pd.DataFrame:
    dates = pd.bdate_range("2023-01-02", periods=rows)
    rv_missing = {50, 275, 790}
    rv, valid_no, price = [], 0, 100.0
    for raw_no in range(rows):
        if raw_no in rv_missing:
            rv.append(np.nan)
            continue
        if valid_no:
            multiplier = 2.0 if valid_no % 2 else 0.5
            if valid_no in {10, 300}:
                multiplier = 3.0
            elif valid_no in {11, 301}:
                multiplier = 1.0 / 3.0
            price *= multiplier
        rv.append(price)
        valid_no += 1

    recovered_missing = {20, 150, 202}
    recovered, recovered_valid = [], 0
    for raw_no in range(rows):
        if raw_no in recovered_missing:
            recovered.append(np.nan)
            continue
        recovered.append(100.0 if recovered_valid < 200 else 99.0 if recovered_valid == 200 else 101.0)
        recovered_valid += 1
    return pd.DataFrame({"rv_boundary": rv, "recovered_boundary": recovered}, index=dates)


def rows_for(reference: str, prices: pd.DataFrame, entity: str) -> pd.DataFrame:
    batch = calculate_batch(reference, {"prices": prices}, protocol=protocol())
    return (batch.values[batch.values.entity_id == entity]
            .sort_values("observation_date").reset_index(drop=True))


def test_exact_references_metadata_and_first_boundaries():
    prices = panel()
    rv_batch = calculate_batch(RV_REF, {"prices": prices}, protocol=protocol())
    recovered_batch = calculate_batch(RECOVERED_REF, {"prices": prices}, protocol=protocol())
    assert rv_batch.metadata["unit"] == "fraction"
    assert rv_batch.metadata["value_type"] == "continuous"
    assert recovered_batch.metadata["unit"] == "boolean"
    assert recovered_batch.metadata["value_type"] == "boolean"
    assert rv_batch.metadata["production_authorization"] == "not_authorized"
    rv = rows_for(RV_REF, prices, "rv_boundary")
    assert pd.isna(rv.iloc[271].value)
    assert rv.iloc[271].missing_reason == "warmup_history_insufficient"
    assert pd.notna(rv.iloc[272].value)
    assert 0 < rv.iloc[272].value <= 1


def test_rv_uses_valid_quotes_includes_current_average_ties_and_756_window():
    prices = panel()
    rv = rows_for(RV_REF, prices, "rv_boundary")
    assert pd.isna(rv.iloc[50].value) and rv.iloc[50].missing_reason == "price_missing"
    expected = definitions.quote_features(prices.rv_boundary.dropna()).rv_rank.iloc[-1]
    assert rv.dropna(subset=["value"]).iloc[-1].value == pytest.approx(expected, abs=1e-12)
    # Constant prices create exactly-zero RV20 values in both paths, so tie equality is stable.
    tied_prices = pd.DataFrame(
        {"tied": [100.0] * 800},
        index=pd.bdate_range("2020-01-02", periods=800),
    )
    tied = rows_for(RV_REF, tied_prices, "tied")
    assert tied.iloc[271].value == pytest.approx(126.5 / 252, abs=1e-12)
    assert tied.iloc[775].value == pytest.approx(378.5 / 756, abs=1e-12)


def test_recovered_200th_valid_equality_true_below_false_and_missing_preserved():
    recovered = rows_for(RECOVERED_REF, panel(), "recovered_boundary")
    assert pd.isna(recovered.iloc[200].value)
    assert recovered.iloc[200].missing_reason == "warmup_history_insufficient"
    assert recovered.iloc[201].value == 1  # 200th valid price equals SMA200.
    assert pd.isna(recovered.iloc[202].value)
    assert recovered.iloc[202].missing_reason == "price_missing"
    assert recovered.iloc[203].value == 0  # next valid price is below SMA200.


@pytest.mark.parametrize("reference", [RV_REF, RECOVERED_REF])
def test_scale_and_future_append_do_not_change_history(reference):
    prices = panel()
    prefix = prices.iloc[:800]
    base = calculate_batch(reference, {"prices": prices}, protocol=protocol()).values
    scaled = calculate_batch(reference, {"prices": prices * 7}, protocol=protocol()).values
    pd.testing.assert_frame_equal(base.reset_index(drop=True), scaled.reset_index(drop=True))
    partial = calculate_batch(reference, {"prices": prefix}, protocol=protocol()).values
    pd.testing.assert_frame_equal(
        partial.reset_index(drop=True), base[base.observation_date.isin(prefix.index)].reset_index(drop=True)
    )


@pytest.mark.parametrize(
    ("reference", "changed"),
    [
        (RV_REF, {"window": 756, "minimum": 252, "include_current": False, "ties": "average"}),
        (RECOVERED_REF, {"equal": False}),
    ],
)
def test_registered_parameter_drift_is_rejected(reference, changed):
    registry = deepcopy(definitions.load_registry())
    identity = reference.split("@", 1)[0]
    next(item for item in registry["objects"] if item["id"] == identity)["definition"]["parameters"] = changed
    with pytest.raises(IdentityFormatError, match="implementation binding differs"):
        calculate_batch(reference, {"prices": panel()}, protocol=protocol(), registry=registry)
