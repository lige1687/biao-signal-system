"""Boundary and paired arithmetic checks for the saved portfolio reviewer."""

from __future__ import annotations

import json
import math

import pytest

from lei_signal.research.incremental_portfolio_review import review


def _payload():
    scope = {
        "universe_id": "fixed-cohort",
        "benchmark_id": "same-pool",
        "currency": "CNY",
        "return_basis": "quote",
        "cost_model": "declared-25bp",
        "frequency": "monthly",
        "unit": "decimal_return",
        "history_status": "previously_seen",
        "source_artifact_sha256": "a" * 64,
    }
    # Candidate gets 2 percentage points more gross than baseline in each month.
    values = [(0.06, 0.04, 0.02), (-0.01, -0.03, -0.02), (0.04, 0.02, 0.01), (0.00, -0.02, 0.00)]
    rows = []
    for i, (candidate, baseline, benchmark) in enumerate(values, 1):
        rows.append(
            {
                "month": f"2020-{i:02d}",
                "candidate": {"gross": candidate, "net": candidate - 0.003, "traded_fraction": 0.4},
                "baseline": {"gross": baseline, "net": baseline - 0.005, "traded_fraction": 0.6},
                "benchmark": {"gross": benchmark, "net": benchmark - 0.001},
            }
        )
    return {"schema": "incremental-portfolio-review/1", "scope": scope, "rows": rows}


def test_paired_finance_arithmetic_and_distinct_correlations():
    result = review(_payload())
    assert result["status"] == "descriptive_comparison_only"
    assert result["increment"]["gross"] == pytest.approx(0.02)
    assert result["increment"]["net"] == pytest.approx(0.022)
    assert result["increment"]["cost_effect"] == pytest.approx(0.002)
    assert result["performance"]["net_common"]["candidate"]["mean_monthly_active"] == pytest.approx(
        0.018
    )
    assert result["traded_fraction"] == pytest.approx(
        {"common_months": 4, "candidate": 0.4, "baseline": 0.6, "relative_reduction": 1 / 3}
    )
    assert result["correlation"]["total_net"] == pytest.approx(1)
    assert result["correlation"]["active_net"] == pytest.approx(1)
    assert result["confidence_interval"] is None


def test_missing_month_keeps_calendar_and_common_gross_mask():
    data = _payload()
    data["rows"][1]["candidate"]["gross"] = None
    data["rows"][1]["candidate"]["net"] = None
    data["rows"][2]["baseline"]["net"] = None
    data["rows"][3]["candidate"].pop("traded_fraction")
    result = review(data)
    assert (result["calendar_months"], result["gross_months"], result["common_months"]) == (4, 3, 2)
    assert result["omitted_months"] == ["2020-02", "2020-03"]
    assert result["common_segments"] == [
        {"start": "2020-01", "end": "2020-01", "months": 1},
        {"start": "2020-04", "end": "2020-04", "months": 1},
    ]
    assert result["performance"]["gross_common"]["candidate"]["n"] == 2
    assert result["traded_fraction"]["common_months"] == 1
    assert result["increment"]["gross"] == pytest.approx(0.02)
    assert result["increment"]["cost_effect"] == pytest.approx(0.002)


def test_zero_is_observed_and_constant_active_ir_is_undefined():
    data = _payload()
    for row in data["rows"]:
        row["candidate"]["gross"] = row["candidate"]["net"] = 0.0
        row["baseline"]["gross"] = row["baseline"]["net"] = 0.0
        row["benchmark"]["gross"] = row["benchmark"]["net"] = 0.0
    result = review(data)
    assert result["common_months"] == 4
    assert result["increment"] == {"gross": 0.0, "net": 0.0, "cost_effect": 0.0}
    assert result["performance"]["net_common"]["candidate"]["annualized_te"] == 0.0
    assert result["performance"]["net_common"]["candidate"]["ir"] is None
    assert result["correlation"] == {"total_net": None, "active_net": None}


def test_total_and_benchmark_relative_correlation_use_different_series():
    data = _payload()
    for row, candidate, baseline, benchmark in zip(
        data["rows"],
        [0.10, 0.20, 0.05, -0.01],
        [0.08, 0.15, 0.04, 0.02],
        [0.07, 0.13, 0.03, -0.02],
        strict=True,
    ):
        for role, value in (
            ("candidate", candidate),
            ("baseline", baseline),
            ("benchmark", benchmark),
        ):
            row[role]["gross"] = row[role]["net"] = value
    result = review(data)
    assert result["correlation"]["total_net"] != pytest.approx(result["correlation"]["active_net"])


def test_gross_only_rows_do_not_create_a_net_comparison():
    data = _payload()
    for row in data["rows"]:
        row["benchmark"]["net"] = None
    result = review(data)
    assert result["gross_months"] == 4
    assert result["common_months"] == 0
    assert result["performance"]["gross_common"]["candidate"]["n"] == 0
    assert result["increment"] == {"gross": None, "net": None, "cost_effect": None}
    assert result["correlation"] == {"total_net": None, "active_net": None}


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -1.01, 1e200, 10**400])
def test_rejects_invalid_returns(value):
    data = _payload()
    data["rows"][0]["candidate"]["gross"] = value
    with pytest.raises(ValueError, match="invalid .*gross"):
        review(data)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -0.1, 1e200])
def test_rejects_invalid_turnover(value):
    data = _payload()
    data["rows"][0]["candidate"]["traded_fraction"] = value
    with pytest.raises(ValueError, match="traded_fraction"):
        review(data)


def test_rejects_net_without_gross_and_net_above_gross():
    data = _payload()
    data["rows"][0]["candidate"]["gross"] = None
    with pytest.raises(ValueError, match="net without gross"):
        review(data)
    data = _payload()
    data["rows"][0]["candidate"]["net"] = 0.07
    with pytest.raises(ValueError, match="net exceeds gross"):
        review(data)


@pytest.mark.parametrize(
    "months",
    [
        ["2020-01", "2020-01", "2020-03", "2020-04"],
        ["2020-01", "2020-03", "2020-04", "2020-05"],
        ["2020-01", "2019-12", "2020-01", "2020-02"],
    ],
)
def test_requires_full_ordered_calendar(months):
    data = _payload()
    for row, month in zip(data["rows"], months, strict=True):
        row["month"] = month
    with pytest.raises(ValueError, match="consecutive months"):
        review(data)


def test_single_common_month_and_partial_turnover():
    data = _payload()
    for row in data["rows"][1:]:
        row["candidate"]["net"] = None
    data["rows"][0]["baseline"]["traded_fraction"] = 0.0
    result = review(data)
    assert result["status"] == "insufficient_common_months"
    assert result["increment"]["net"] == pytest.approx(0.022)
    assert result["performance"]["net_common"]["candidate"]["ir"] is None
    assert result["correlation"]["total_net"] is None
    assert result["traded_fraction"]["relative_reduction"] is None


def test_scope_and_json_result_are_bounded_and_finite():
    data = _payload()
    data["scope"]["source_artifact_sha256"] = "BAD"
    with pytest.raises(ValueError, match="fingerprint"):
        review(data)
    data = _payload()
    data["rows"][0]["candidate"]["gross"] = 1e100
    data["rows"][0]["candidate"]["net"] = 1e100
    assert math.isfinite(review(data)["performance"]["net_common"]["candidate"]["annualized_te"])
    json.dumps(review(_payload()), allow_nan=False)
