"""Synthetic, calendar-aware tests; no provider or real market effects."""

from __future__ import annotations

import json
import math
from copy import deepcopy

import pytest

from lei_signal.research.factor_sorting_diagnostics import analyze
from lei_signal.research.fip import hac_mean, month_add


def _rows(month="2020-01", n=30, green_n=None):
    green_n = n if green_n is None else green_n
    return [
        {
            "code": f"C{i:02d}",
            "month": month,
            "holding_month": month_add(month, 1),
            "green": i < green_n,
            "momentum": float(i),
            "high52": 0.5 + i / 100,
            "hot": i / 100,
            "vol60": (i + 1) / 100,
            "return": (i - 15) / 100,
            "adverse": -i / 1000,
            "adverse_flat_as_unknown_return": (i - 15) / 100,
        }
        for i in range(n)
    ]


def _monthly(result, month, universe="green_only", factor="momentum"):
    return next(
        row
        for row in result["monthly"]
        if (row["month"], row["universe"], row["factor"]) == (month, universe, factor)
    )


def _group(result, month, universe="green_only", factor="momentum", group=5):
    return next(
        row
        for row in result["groups"]
        if (row["month"], row["universe"], row["factor"], row["group"])
        == (month, universe, factor, group)
    )


def _increment(result, month, comparison):
    return next(
        row
        for row in result["increments"]
        if (row["month"], row["comparison"]) == (month, comparison)
    )


def _summary(result, period="all", universe="green_only", factor="momentum"):
    return next(
        row
        for row in result["summary"]["sorts"]
        if (row["period"], row["universe"], row["factor"]) == (period, universe, factor)
    )


def test_formation_ties_are_code_deterministic_and_future_missing_cannot_regroup():
    rows = _rows(n=31)
    for row in rows:
        row["momentum"] = 1.0
    complete = analyze(rows, ["2020-01"])
    missing = deepcopy(rows)
    missing[-1]["return"] = None
    after = analyze(missing, ["2020-01"])
    assert [_group(complete, "2020-01", group=g)["n"] for g in range(1, 6)] == [7, 6, 6, 6, 6]
    assert _group(complete, "2020-01")["codes"] == [f"C{i:02d}" for i in range(25, 31)]
    assert _group(after, "2020-01")["codes"] == _group(complete, "2020-01")["codes"]
    assert _group(after, "2020-01")["unknown_weight"] == pytest.approx(1 / 6)
    assert _group(after, "2020-01")["known_contribution"] == pytest.approx(
        sum(row["return"] for row in missing[25:30]) / 31
    )
    assert _group(after, "2020-01")["known_sum_over_n"] == pytest.approx(
        sum(row["return"] for row in missing[25:30]) / 6
    )
    assert _group(after, "2020-01")["complete_return"] is None
    assert _monthly(after, "2020-01")["g5_minus_pool_return"] is None
    assert _monthly(after, "2020-01")["known_subset_g5_minus_pool"] is not None


def test_full_month_axis_keeps_gap_for_hac_and_does_not_bridge_membership():
    months = ["2020-01", "2020-02", "2020-03"]
    first = _rows(months[0])
    last = _rows(months[2])
    for row in last:
        row["return"] = -row["return"]
    result = analyze(first + last, months)
    series = [_monthly(result, month)["g5_minus_pool_return"] for month in months]
    assert series[1] is None
    assert _monthly(result, months[2])["g5_entry_fraction"] is None
    actual = _summary(result)["metrics"]["g5_minus_pool_return"]
    expected = hac_mean(series, lag=3)
    assert actual["n"] == 2
    assert actual["mean"] == pytest.approx(expected["mean"])
    assert actual["se"] == pytest.approx(expected["se"])
    assert _summary(result)["calendar_months"] == 3
    assert _summary(result)["qualified_months"] == 2
    json.dumps(result, allow_nan=False)


def test_consecutive_group_changes_use_only_formation_scores():
    first = _rows("2020-01")
    second = _rows("2020-02")
    for row in second:
        row["momentum"] = -row["momentum"]
    result = analyze(first + second, ["2020-01", "2020-02"])
    assert _group(result, "2020-01")["codes"] == [f"C{i:02d}" for i in range(24, 30)]
    assert _group(result, "2020-02")["codes"] == [f"C{i:02d}" for i in range(5, -1, -1)]
    assert _monthly(result, "2020-02")["g5_entry_fraction"] == 1
    assert _monthly(result, "2020-01")["g5_entry_fraction"] is None


def test_all_and_green_use_their_fixed_pools_and_complete_labels_not_known_subset_as_main():
    rows = _rows(n=40, green_n=30)
    rows[-1]["return"] = None  # missing outcome only for a nongreen qualified name
    result = analyze(rows, ["2020-01"])
    assert _monthly(result, "2020-01", "all_qualified")["g5_minus_pool_return"] is None
    assert _monthly(result, "2020-01", "green_only")["g5_minus_pool_return"] is not None
    assert all(row["complete_return_increment"] is not None for row in result["increments"])
    rows[0]["return"] = None
    changed = analyze(rows, ["2020-01"])
    assert all(row["complete_return_increment"] is None for row in changed["increments"])
    assert all(row["known_increment"] is not None for row in changed["increments"])
    assert all(row["unknown_absolute_weight"] >= 0 for row in changed["increments"])
    assert [row["candidate_weights"] for row in changed["increments"]] == [
        row["candidate_weights"] for row in result["increments"]
    ]
    assert _group(changed, "2020-01")["codes"] == _group(result, "2020-01")["codes"]


def test_stratum_weights_preserve_unequal_counts_and_ordinary_top20_is_separate():
    rows = _rows(n=31)
    result = analyze(rows, ["2020-01"])
    chosen = _increment(result, "2020-01", "high52_vs_green")
    weights = chosen["candidate_weights"]
    assert chosen["candidate_n"] == 15
    assert sum(weights.values()) == pytest.approx(1)
    assert weights["C04"] == pytest.approx(7 / 31 / 3)
    assert weights["C10"] == pytest.approx(6 / 31 / 3)
    assert "C00" not in weights and "C04" in weights
    top = _increment(result, "2020-01", "high52_vs_momentum_top20")
    assert top["baseline_n"] == math.ceil(31 * 0.20) == 7
    assert set(top["baseline_weights"]) == {f"C{i:02d}" for i in range(24, 31)}
    assert top["candidate_weights"] == chosen["candidate_weights"]
    assert chosen["candidate_exposure"]["momentum"] != pytest.approx(
        chosen["baseline_exposure"]["momentum"]
    )


def test_low_volatility_risk_sign_and_known_pair_rank_correlation():
    rows = _rows()
    for row in rows:
        row["return"] = row["momentum"] / 100
        row["adverse"] = -row["vol60"]
    result = analyze(rows, ["2020-01"])
    lowvol = _monthly(result, "2020-01", factor="lowvol")
    assert lowvol["g5_adverse_minus_pool"] > 0  # closer to zero means less entry-relative decline
    assert _increment(result, "2020-01", "lowvol_vs_green")["complete_adverse_increment"] > 0
    momentum = _monthly(result, "2020-01")
    assert momentum["spearman"] == pytest.approx(1)
    assert momentum["spearman_known_pairs"] == 30
    rows[0]["return"] = None
    partial = analyze(rows, ["2020-01"])
    assert _monthly(partial, "2020-01")["spearman_known_pairs"] == 29
    assert _monthly(partial, "2020-01")["spearman"] == pytest.approx(1)
    assert _monthly(partial, "2020-01", factor="lowvol")["g5_adverse_minus_pool"] > 0


def test_restrictive_quote_unknown_stays_separate_and_invalid_features_fail():
    rows = _rows()
    rows[0]["adverse_flat_as_unknown_return"] = None
    result = analyze(rows, ["2020-01"])
    comparison = _increment(result, "2020-01", "lowvol_vs_green")
    assert comparison["complete_return_increment"] is not None
    assert comparison["complete_restrictive_return_increment"] is None
    assert comparison["unknown_restrictive_absolute_weight"] > 0
    assert _group(result, "2020-01", factor="lowvol")["complete_restrictive_return"] is None
    assert _monthly(result, "2020-01", factor="lowvol")["g5_minus_pool_restrictive_return"] is None
    json.dumps(result, allow_nan=False)
    bad = deepcopy(rows)
    bad[0]["high52"] = None
    with pytest.raises(ValueError, match="non-finite past feature"):
        analyze(bad, ["2020-01"])


def test_winner_capture_uses_known_name_counts_and_unknown_label_is_not_zero():
    rows = _rows()
    for row in rows:
        row["return"] = 0.0
    rows[0]["return"] = 0.21
    rows[-1]["return"] = 0.80
    result = analyze(rows, ["2020-01"])
    monthly = _monthly(result, "2020-01")
    assert monthly["winner_known_pool_n"] == 2
    assert monthly["winner_known_g5_n"] == 1
    assert monthly["winner_capture_complete"] == pytest.approx(0.5)
    rows[1]["return"] = None
    partial = _monthly(analyze(rows, ["2020-01"]), "2020-01")
    assert partial["winner_capture_complete"] is None
    assert partial["winner_capture_known"] == pytest.approx(0.5)


def test_under_thirty_names_stays_on_calendar_without_fake_quintiles():
    result = analyze(_rows(n=29), ["2020-01", "2020-02"])
    assert len(result["monthly"]) == 2 * 2 * 4
    assert result["groups"] == [] and result["increments"] == []
    assert all(not row["qualified"] for row in result["monthly"])
    assert _summary(result)["metrics"]["g5_minus_pool_return"]["n"] == 0
    assert _summary(result)["metrics"]["g5_minus_pool_return"]["mean"] is None
    json.dumps(result, allow_nan=False)
