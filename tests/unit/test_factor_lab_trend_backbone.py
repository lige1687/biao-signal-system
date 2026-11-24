"""B13 trend backbone adapter tests from hand-derived synthetic prices."""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from lei_signal.research import definitions
from lei_signal.research.factor_lab.adapters import calculate_batch
from lei_signal.research.factor_lab.contracts import IdentityFormatError


REFERENCES = {
    "sma50": "trend.sma50@1.0.0",
    "above50": "trend.above50@1.0.0",
    "cross50": "trend.cross_up50@1.0.0",
    "sma200": "trend.sma200@1.0.0",
    "above200": "trend.above200@1.0.0",
    "cross200": "trend.cross_up200@1.0.0",
}


def protocol() -> dict:
    return {
        "protocol_id": "factor-b13-test",
        "version": "1.0.0",
        "kind": "calculation_only",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2026-09-21T15:00:00+08:00",
    }


def boundary_panel(rows: int = 215) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=rows)
    fifty = [100.0] * rows
    fifty[50] = np.nan
    fifty[51:] = [102.0 + (i - 51) * 0.25 for i in range(51, rows)]

    two_hundred = [100.0] * rows
    two_hundred[40] = np.nan
    two_hundred[150] = np.nan
    two_hundred[202] = np.nan
    two_hundred[203:] = [102.0 + (i - 203) for i in range(203, rows)]

    discriminator = [50.0] * 150 + [100.0] * (rows - 150)
    return pd.DataFrame(
        {
            "boundary50": fifty,
            "boundary200": two_hundred,
            "window_discriminator": discriminator,
        },
        index=dates,
    )


def rows_for(reference: str, panel: pd.DataFrame, entity: str) -> pd.DataFrame:
    batch = calculate_batch(reference, {"prices": panel}, protocol=protocol())
    return (
        batch.values[batch.values["entity_id"] == entity]
        .sort_values("observation_date")
        .reset_index(drop=True)
    )


@pytest.mark.parametrize(
    ("key", "unit", "value_type"),
    [
        ("sma50", "same_as_P_signal", "continuous"),
        ("above50", "boolean", "boolean"),
        ("cross50", "boolean", "boolean"),
        ("sma200", "same_as_P_signal", "continuous"),
        ("above200", "boolean", "boolean"),
        ("cross200", "boolean", "boolean"),
    ],
)
def test_six_exact_references_expose_registered_metadata(key, unit, value_type):
    batch = calculate_batch(
        REFERENCES[key], {"prices": boundary_panel()}, protocol=protocol()
    )
    assert batch.metadata["reference"] == REFERENCES[key]
    assert batch.metadata["card_kind"] == "registered"
    assert batch.metadata["unit"] == unit
    assert batch.metadata["value_type"] == value_type
    assert batch.metadata["production_authorization"] == "not_authorized"


def test_50_window_current_included_equality_and_previous_valid_cross():
    panel = boundary_panel()
    sma = rows_for(REFERENCES["sma50"], panel, "boundary50")
    above = rows_for(REFERENCES["above50"], panel, "boundary50")
    cross = rows_for(REFERENCES["cross50"], panel, "boundary50")

    assert sma.iloc[48]["missing_reason"] == "warmup_history_insufficient"
    assert sma.iloc[49]["value"] == pytest.approx(100.0)
    assert above.iloc[49]["value"] == 0
    assert pd.isna(cross.iloc[49]["value"])
    assert cross.iloc[49]["missing_reason"] == "warmup_history_insufficient"

    for frame in (sma, above, cross):
        assert pd.isna(frame.iloc[50]["value"])
        assert frame.iloc[50]["missing_reason"] == "price_missing"

    # Raw row 51 compares with raw row 49, the previous valid quote.
    assert sma.iloc[51]["value"] == pytest.approx((49 * 100.0 + 102.0) / 50)
    assert above.iloc[51]["value"] == 1
    assert cross.iloc[51]["value"] == 1
    assert cross.iloc[52]["value"] == 0


def test_200_window_first_comparable_and_missing_interruption():
    panel = boundary_panel()
    sma = rows_for(REFERENCES["sma200"], panel, "boundary200")
    above = rows_for(REFERENCES["above200"], panel, "boundary200")
    cross = rows_for(REFERENCES["cross200"], panel, "boundary200")

    assert sma.iloc[200]["missing_reason"] == "warmup_history_insufficient"
    assert sma.iloc[201]["value"] == pytest.approx(100.0)
    assert above.iloc[201]["value"] == 0
    assert pd.isna(cross.iloc[201]["value"])
    assert cross.iloc[201]["missing_reason"] == "warmup_history_insufficient"
    assert cross.iloc[202]["missing_reason"] == "price_missing"
    assert sma.iloc[203]["value"] == pytest.approx((199 * 100.0 + 102.0) / 200)
    assert above.iloc[203]["value"] == 1
    assert cross.iloc[203]["value"] == 1
    assert cross.iloc[204]["value"] == 0


def test_50_and_200_windows_are_not_interchanged():
    panel = boundary_panel()
    day = panel.index[199]
    sma50 = rows_for(REFERENCES["sma50"], panel, "window_discriminator")
    sma200 = rows_for(REFERENCES["sma200"], panel, "window_discriminator")
    above50 = rows_for(REFERENCES["above50"], panel, "window_discriminator")
    above200 = rows_for(REFERENCES["above200"], panel, "window_discriminator")
    assert sma50.loc[sma50.observation_date == day, "value"].item() == 100.0
    assert sma200.loc[sma200.observation_date == day, "value"].item() == 62.5
    assert above50.loc[above50.observation_date == day, "value"].item() == 0
    assert above200.loc[above200.observation_date == day, "value"].item() == 1


@pytest.mark.parametrize("key", list(REFERENCES))
def test_append_future_does_not_change_history(key):
    full = boundary_panel()
    prefix = full.iloc[:207]
    a = calculate_batch(REFERENCES[key], {"prices": prefix}, protocol=protocol()).values
    b = calculate_batch(REFERENCES[key], {"prices": full}, protocol=protocol()).values
    historical = b[b["observation_date"].isin(prefix.index)]
    pd.testing.assert_frame_equal(
        a.reset_index(drop=True), historical.reset_index(drop=True)
    )


@pytest.mark.parametrize("key", ["sma50", "sma200"])
def test_price_scale_scales_only_moving_average(key):
    panel = boundary_panel()
    base = calculate_batch(REFERENCES[key], {"prices": panel}, protocol=protocol()).values
    scaled = calculate_batch(
        REFERENCES[key], {"prices": panel * 7.0}, protocol=protocol()
    ).values
    valid = base.value.notna()
    np.testing.assert_allclose(scaled.loc[valid, "value"], base.loc[valid, "value"] * 7)
    assert base.loc[~valid, "missing_reason"].tolist() == scaled.loc[
        ~valid, "missing_reason"
    ].tolist()


@pytest.mark.parametrize("key", ["above50", "cross50", "above200", "cross200"])
def test_price_scale_preserves_boolean_states(key):
    panel = boundary_panel()
    base = calculate_batch(REFERENCES[key], {"prices": panel}, protocol=protocol()).values
    scaled = calculate_batch(
        REFERENCES[key], {"prices": panel * 7.0}, protocol=protocol()
    ).values
    pd.testing.assert_frame_equal(base.reset_index(drop=True), scaled.reset_index(drop=True))


@pytest.mark.parametrize(
    ("key", "changed"),
    [
        ("sma50", {"window": 50, "min_periods": 49}),
        ("above50", {"equal": True}),
        (
            "cross50",
            {"equal_current": False, "previous": "上一原始行", "missing_previous": "缺失"},
        ),
        ("sma200", {"window": 199, "min_periods": 199}),
        ("above200", {"equal": True}),
        (
            "cross200",
            {"equal_current": True, "previous": "上一有效报价", "missing_previous": "缺失"},
        ),
    ],
)
def test_registered_parameter_drift_is_rejected(key, changed):
    registry = deepcopy(definitions.load_registry())
    identity = REFERENCES[key].split("@", 1)[0]
    obj = next(item for item in registry["objects"] if item["id"] == identity)
    obj["definition"]["parameters"] = changed
    with pytest.raises(IdentityFormatError, match="implementation binding differs"):
        calculate_batch(
            REFERENCES[key],
            {"prices": boundary_panel()},
            protocol=protocol(),
            registry=registry,
        )
