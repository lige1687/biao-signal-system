"""Permanent regression coverage for the adjudicated RV v1 scale limitation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_lab.adapters import calculate_batch


RV_REF = "mixed.rv_percentile@1.0.0"


class KnownRVScaleMismatch(AssertionError):
    """Only the adjudicated numeric scale mismatch may be expected to fail."""


def _protocol() -> dict:
    return {
        "protocol_id": "factor-rv-known-limitations-test",
        "version": "1.0.0",
        "kind": "calculation_only",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2026-09-22T15:00:00+08:00",
    }


def _rv_boundary_panel(rows: int = 810) -> pd.DataFrame:
    """Reproduce only the hand-built RV column from the frozen B14 panel."""
    dates = pd.bdate_range("2023-01-02", periods=rows)
    missing_rows = {50, 275, 790}
    values: list[float] = []
    valid_no = 0
    price = 100.0
    for raw_no in range(rows):
        if raw_no in missing_rows:
            values.append(np.nan)
            continue
        if valid_no:
            multiplier = 2.0 if valid_no % 2 else 0.5
            if valid_no in {10, 300}:
                multiplier = 3.0
            elif valid_no in {11, 301}:
                multiplier = 1.0 / 3.0
            price *= multiplier
        values.append(price)
        valid_no += 1
    return pd.DataFrame({"rv_boundary": values}, index=dates)


def _rv_ranks(prices: pd.DataFrame) -> pd.Series:
    values = calculate_batch(RV_REF, {"prices": prices}, protocol=_protocol()).values
    return (
        values.loc[values.entity_id == "rv_boundary"]
        .sort_values("observation_date")
        .set_index("observation_date")["value"]
    )


@pytest.mark.xfail(
    strict=True,
    raises=KnownRVScaleMismatch,
    reason="RV v1 exact floating-point ties are not stable under 1.1 price scaling",
)
def test_rv_v1_rank_is_not_stable_when_prices_are_scaled_by_1_1() -> None:
    prices = _rv_boundary_panel()
    base = _rv_ranks(prices)
    scaled = _rv_ranks(prices * 1.1)

    # Shape, missingness and upstream assertion failures are not this limitation.
    pd.testing.assert_index_equal(base.index, scaled.index)
    pd.testing.assert_series_equal(base.isna(), scaled.isna())
    assert base.notna().any(), "the fixture must produce actual ranks"
    try:
        np.testing.assert_allclose(base.to_numpy(), scaled.to_numpy(), rtol=0, atol=1e-10,
                                   equal_nan=True)
    except AssertionError as exc:
        raise KnownRVScaleMismatch(str(exc)) from exc
