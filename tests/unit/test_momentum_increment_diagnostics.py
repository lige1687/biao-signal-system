"""Synthetic formation, calendar, outcome, and saved-statistic checks only."""

import math
from copy import deepcopy

import pytest

from lei_signal.research.momentum_increment_diagnostics import (
    common_score_rows,
    daily_scores,
    groups,
    month_summary,
    monthly_sharpe,
    partial_rank_diagnostic,
    rank_diagnostic,
    rank_mix,
)


def test_fixed_calendar_endpoints_and_future_changes_do_not_rewrite_past():
    dates = [f"d{i:03d}" for i in range(255)]
    prices = {day: 100 + i for i, day in enumerate(dates)}
    before = daily_scores(dates, prices)
    at_252 = before[dates[252]]["scores"]
    assert at_252["mom20"] == pytest.approx(352 / 332 - 1)
    assert at_252["skip20"] == pytest.approx(332 / 100 - 1)
    assert at_252["skip21"] == pytest.approx(331 / 100 - 1)
    assert at_252["skip20"] != at_252["skip21"]
    prices[dates[-1]] = 9999
    assert daily_scores(dates, prices)[dates[252]] == before[dates[252]]


def test_calendar_gap_does_not_compress_and_nonpositive_has_separate_reason():
    dates = [f"d{i:03d}" for i in range(254)]
    prices = {day: float(i + 1) for i, day in enumerate(dates)}
    prices.pop(dates[240])
    missing = daily_scores(dates, prices)[dates[-1]]
    assert missing["scores"]["mom20"] is None
    assert missing["reasons"]["mom20"] == "missing_price"
    assert missing["scores"]["skip21"] is not None
    prices[dates[240]] = 0
    invalid = daily_scores(dates, prices)[dates[-1]]
    assert invalid["reasons"]["mom20"] == "nonpositive_price"
    assert invalid["reasons"]["skip21"] is None


def test_average_tie_ranks_use_same_complete_formation_pool():
    features = {
        "A": {"mom20": 1, "mom60": 1, "mom120": 3},
        "B": {"mom20": 1, "mom60": 2, "mom120": 2},
        "C": {"mom20": 3, "mom60": 3, "mom120": 1},
        "D": {"mom20": 9, "mom60": 9, "mom120": None},
    }
    mixed = rank_mix(features)
    assert mixed["A"]["rank_components"]["mom20"] == pytest.approx(1 / 3)
    assert mixed["B"]["rank_components"]["mom20"] == pytest.approx(1 / 3)
    assert mixed["D"]["mix"] is None
    assert mixed["D"]["rank_components"] == {}
    assert mixed["A"]["mix"] == pytest.approx((1 / 3 + 1 / 6 + 5 / 6) / 3)


def test_unknown_outcome_changes_coverage_but_never_groups_or_weights():
    rows = [{"code": f"C{i:02}", "score": float(i // 2), "return": i / 100} for i in range(10)]
    first = groups(rows, "score", 5)
    changed = deepcopy(rows)
    changed[-1]["return"] = None
    second = groups(changed, "score", 5)
    assert [g["codes"] for g in first["groups"]] == [g["codes"] for g in second["groups"]]
    assert [g["weights"] for g in first["groups"]] == [g["weights"] for g in second["groups"]]
    assert second["groups"][-1]["unknown_weight"] == pytest.approx(0.5)
    assert second["groups"][-1]["complete_return"] is None
    assert second["groups"][-1]["known_contribution"] == pytest.approx(0.08 / 2)
    assert second["rank"]["unknown"] == 1


def test_rank_ties_and_constant_rank_are_explicit():
    rows = [{"score": x, "return": y} for x, y in [(1, 1), (1, 2), (2, 3), (3, None)]]
    result = rank_diagnostic(rows, "score")
    assert result["eligible"] == 4 and result["known"] == 3 and result["unknown"] == 1
    assert result["tie_fraction"] == pytest.approx(1 / 3)
    assert result["spearman"] == pytest.approx(math.sqrt(3) / 2)
    constant = rank_diagnostic([{"score": 1, "return": i} for i in range(4)], "score")
    assert constant["spearman"] is None and constant["reason"] == "constant_rank"


def test_partial_rank_reports_dependent_controls_and_residual_degeneracy():
    rows = [
        {"candidate": i + (i % 3) / 10, "future": i + (i % 2) / 10, "control": i, "copy": i}
        for i in range(12)
    ]
    dependent = partial_rank_diagnostic(rows, "candidate", ["control", "copy"], "future")
    assert dependent["effective_rank"] == 2
    assert dependent["degrees_of_freedom"] == 10
    assert dependent["partial_rank_correlation"] is None
    assert dependent["reason"] == "dependent_controls"
    degenerate = partial_rank_diagnostic(rows, "control", ["copy"], "future")
    assert degenerate["partial_rank_correlation"] is None
    assert degenerate["reason"] == "degenerate_residual"
    too_few = partial_rank_diagnostic(rows[:9], "candidate", ["control"], "future")
    assert too_few["reason"] == "insufficient_common_pairs"


def test_partial_rank_valid_control_and_six_etf_group_geometry():
    rows = [
        {"candidate": i + (i % 3) / 10, "future": (i * 7) % 13,
         "control": (i * 5) % 13}
        for i in range(12)
    ]
    partial = partial_rank_diagnostic(rows, "candidate", ["control"], "future")
    assert partial["effective_rank"] == 2
    assert partial["degrees_of_freedom"] == 10
    assert partial["reason"] is None
    assert -1 <= partial["partial_rank_correlation"] <= 1

    etfs = [{"code": f"E{i}", "score": 1.0, "return": i / 100} for i in range(6)]
    grouped = groups(etfs, "score", 3)["groups"]
    assert [group["codes"] for group in grouped] == [
        ["E0", "E1"], ["E2", "E3"], ["E4", "E5"]
    ]
    assert [group["boundary_tie"] for group in grouped] == [True, True, False]
    assert all(group["weights"] == {code: 0.5 for code in group["codes"]} for group in grouped)


def test_month_summary_keeps_missing_calendar_slot_for_hac():
    months = ["2020-01", "2020-02", "2020-03"]
    actual = month_summary(months, {"2020-01": 1.0, "2020-03": -1.0})
    assert actual["values"] == [1.0, None, -1.0]
    assert actual["valid_count"] == 2
    assert actual["mean"] == pytest.approx(0.0)
    assert actual["se"] == pytest.approx(0.5)
    with pytest.raises(ValueError):
        month_summary(["2020-01", "2020-03"], {"2020-01": 1})


def test_one_valid_month_does_not_claim_zero_uncertainty():
    result = month_summary(["2020-01", "2020-02"], {"2020-02": 0.2})
    assert result["mean"] == 0.2
    assert result["valid_count"] == 1
    assert result["se"] is result["ci_low"] is result["ci_high"] is None
    assert result["reason"] == "fewer_than_two_valid_months"


def test_partial_rank_matches_single_control_correlation_identity():
    x = list(range(1, 13))
    y = [1, 3, 2, 6, 4, 5, 10, 8, 9, 7, 12, 11]
    z = [5, 1, 7, 3, 9, 2, 11, 4, 12, 6, 10, 8]
    # Already unique ranks; Spearman's difference-of-ranks identity provides
    # an independent check without a second least-squares implementation.
    def spearman(a, b):
        return 1 - 6 * sum((u - v) ** 2 for u, v in zip(a, b, strict=True)) / (12 * (12**2 - 1))
    xy, xz, yz = spearman(x, y), spearman(x, z), spearman(y, z)
    expected = (xy - xz * yz) / math.sqrt((1 - xz**2) * (1 - yz**2))
    rows = [{"x": a, "y": b, "z": c} for a, b, c in zip(x, y, z, strict=True)]
    actual = partial_rank_diagnostic(rows, "x", ["z"], "y")
    assert actual["partial_rank_correlation"] == pytest.approx(expected, abs=1e-12)


def test_comparison_pool_excludes_missing_scores_but_keeps_unknown_future():
    rows = [
        {"code": "A", "formation_eligible": True, "mix": 1, "mom60": 1, "return": None},
        {"code": "B", "formation_eligible": True, "mix": None, "mom60": 2, "return": 1},
        {"code": "C", "formation_eligible": False, "mix": 1, "mom60": 3, "return": 1},
    ]
    assert [r["code"] for r in common_score_rows(rows, ["mix", "mom60"])] == ["A"]
    tied = groups([{"code": f"E{i}", "score": 1, "return": i} for i in range(6)], "score", 3)
    assert not tied["sorting_effect_evaluable"]
    assert tied["reason"] == "constant_formation_score"


def test_sharpe_requires_complete_months_and_explicit_monthly_rf_units():
    months = ["2020-01", "2020-02", "2020-03"]
    returns = [0.02, 0.04, 0.03]
    zero_rf = monthly_sharpe(months, returns)
    matched = monthly_sharpe(months, returns, [0.01, 0.01, 0.01])
    assert zero_rf["risk_free_assumption"] == "zero_assumed"
    assert matched["risk_free_assumption"] == "matched_monthly_decimal"
    assert zero_rf["sharpe"] == pytest.approx(0.03 / 0.01 * math.sqrt(12))
    assert matched["sharpe"] == pytest.approx(0.02 / 0.01 * math.sqrt(12))
    assert monthly_sharpe(months, [0.02, None, 0.03])["reason"] == "missing_monthly_value"
    with pytest.raises(ValueError):
        monthly_sharpe(["2020-01", "2020-03"], [0.02, 0.03])
