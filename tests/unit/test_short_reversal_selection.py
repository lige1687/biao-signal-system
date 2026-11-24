"""Synthetic, source-free checks for month-end short-reversal selection."""

from __future__ import annotations

import math

import numpy as np
import pytest

from lei_signal.research.short_reversal_selection import (
    decomposition,
    monthly_features,
    partial_rank_correlations,
    select_weights,
    weighted_month,
    weighted_turnover,
)


def _panel():
    calendar = [f"2024-{month:02d}-{day:02d}" for month in range(1, 13) for day in range(1, 23)]
    calendar += [f"2025-{month:02d}-{day:02d}" for month in range(1, 3) for day in range(1, 23)]
    rows = [
        {"date": day, "close": str(100 + i * 0.1), "tradestatus": "1", "isST": "0", "volume": "100"}
        for i, day in enumerate(calendar)
    ]
    return {
        "rows": rows,
        "break_dates": [],
        "research_price_basis": "raw_ohlc_times_effective_foreAdjustFactor",
    }, calendar


def test_monthly_prefix_endpoints_and_green_20_market_days():
    adapted, calendar = _panel()
    first = monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0]
    assert first["eligible"] and first["green"] is True
    closes = {row["date"]: float(row["close"]) for row in adapted["rows"]}
    assert first["momentum"] == pytest.approx(closes["2024-12-22"] / closes["2024-01-22"] - 1)
    assert first["hot"] == pytest.approx(closes["2025-01-22"] / closes["2024-12-22"] - 1)
    assert first["hot"] != pytest.approx(
        closes["2025-01-22"] / closes[calendar[calendar.index("2025-01-22") - 21]] - 1
    )
    logs = [
        math.log(closes[calendar[j]] / closes[calendar[j - 1]])
        for j in range(22 * 13 - 60, 22 * 13)
    ]
    assert first["vol60"] == pytest.approx(np.std(logs, ddof=1))
    adapted["rows"][-1]["close"] = "9999"  # future February quote
    assert monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0] == first
    adapted["rows"] = [row for row in adapted["rows"] if row["date"] <= "2025-01-22"]
    assert monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0] == first


def test_green_uses_exact_twentieth_prior_market_close():
    adapted, calendar = _panel()
    ix = calendar.index("2025-01-22")
    by_day = {row["date"]: row for row in adapted["rows"]}
    for day in calendar[ix - 19 : ix]:
        by_day[day]["close"] = "100"
    by_day[calendar[ix - 20]]["close"] = "105"
    by_day[calendar[ix - 21]]["close"] = "95"
    by_day[calendar[ix]]["close"] = "103"
    item = monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0]
    assert item["green"] is False and "not_green" in item["reasons"]
    assert float(by_day[calendar[ix]]["close"]) > float(by_day[calendar[ix - 21]]["close"])


def test_missing_row_and_break_reject_without_calendar_compression():
    adapted, calendar = _panel()
    adapted["rows"] = [row for row in adapted["rows"] if row["date"] != "2024-07-12"]
    item = monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0]
    assert not item["eligible"] and "month_calendar_gap_or_invalid_close" in item["reasons"]
    adapted, calendar = _panel()
    adapted["break_dates"] = ["2025-01-12"]
    item = monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0]
    assert not item["eligible"] and "adjusted_price_break_in_window" in item["reasons"]
    assert item["green"] is None  # only ten rows remain after the reset


def test_twenty_day_reference_uses_market_calendar_even_after_missing_row():
    adapted, calendar = _panel()
    target = "2025-01-22"
    lag = calendar[calendar.index(target) - 20]
    adapted["rows"] = [row for row in adapted["rows"] if row["date"] != lag]
    item = monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0]
    assert item["green"] is None and not item["eligible"]


def _features(n):
    return [
        {
            "code": f"C{i:02d}",
            "month": "2025-01",
            "eligible": True,
            "momentum": float(i),
            "hot": float(i % 7),
            "vol60": 0.01 + i / 1000,
        }
        for i in range(n)
    ]


def test_selection_group_mass_odd_middle_and_stable_ties():
    features = _features(35)
    features[1]["momentum"] = features[0]["momentum"]
    features.reverse()
    result = select_weights(features)
    weights, groups = result["weights"], result["groups"]
    assert groups["C00"] == groups["C01"] == 1
    assert weights["all_green"]["C00"] == pytest.approx(1 / 35)
    for group in range(1, 6):
        members = [code for code, label in groups.items() if label == group]
        for arm in ("cool", "hot"):
            assert sum(weights[arm].get(code, 0) for code in members) == pytest.approx(7 / 35)
            assert sum(code in weights[arm] for code in members) == 3
        middle = sorted(members, key=lambda code: (result["scores"][code]["hot"], code))[3]
        assert middle not in weights["cool"] and middle not in weights["hot"]
        assert middle in weights["all_green"]
    assert len(weights["ordinary"]) == math.ceil(35 * 0.30)
    assert sum(weights["ordinary"].values()) == pytest.approx(1)
    assert result["concentration_hhi"]["all_green"] == pytest.approx(1 / 35)
    assert select_weights(list(reversed(features)))["weights"] == weights


def test_unknown_weight_is_neither_zero_nor_renormalized_and_turnover_drifts():
    weights = {"A": 0.25, "B": 0.75}
    outcomes = {
        "A": {"return": 0.2, "adverse": -0.1, "opportunity": 0.3},
        "B": {"return": None, "adverse": None, "opportunity": None},
    }
    item = weighted_month(weights, outcomes)
    assert item["known_weighted_contribution"] == pytest.approx(0.05)
    assert item["unknown_weight"] == pytest.approx(0.75)
    assert item["complete_return"] is None and item["mean_adverse"] is None
    assert item["known_weighted_adverse"] == pytest.approx(-0.025)
    assert item["mean_opportunity"] is None
    assert weighted_turnover(weights, outcomes, {"A": 0.5, "B": 0.5})["traded_gross"] is None
    previous = {"A": 0.5, "B": 0.5}
    known = {"A": {"return": 0.2}, "B": {"return": -0.2}}
    traded = weighted_turnover(previous, known, {"A": 0.5, "B": 0.5})
    assert traded["traded_gross"] == pytest.approx(0.2)  # drift .6/.4 to .5/.5
    assert traded["half_l1"] == pytest.approx(0.1)
    assert weighted_turnover(None, None, previous)["traded_gross"] == 1


def test_explicit_weight_difference_four_signs_and_unknown():
    candidate = {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}
    baseline = {"A": 0.2, "B": 0.1, "C": 0.4, "D": 0.3}
    outcomes = {
        "A": {"return": 0.2},
        "B": {"return": -0.1},
        "C": {"return": -0.2},
        "D": {"return": 0.3},
    }
    result = decomposition(candidate, baseline, outcomes)
    assert result["added_gain"] == pytest.approx(0.04)
    assert result["added_loss"] == pytest.approx(-0.02)
    assert result["avoided_loss"] == pytest.approx(0.04)
    assert result["foregone_gain"] == pytest.approx(-0.06)
    assert result["known_increment"] == pytest.approx(
        sum(result[k] for k in ("added_gain", "added_loss", "avoided_loss", "foregone_gain"))
    )
    outcomes["B"]["return"] = None
    unknown = decomposition(candidate, baseline, outcomes)
    assert unknown["unknown_absolute_weight"] == pytest.approx(0.2)
    assert unknown["complete_increment"] is None


def test_partial_rank_controls_and_singular_rejection():
    features = _features(50)
    for i, row in enumerate(features):
        # Hot rank and future-return rank share momentum, with distinct residual patterns.
        row["hot"] = -i + (i % 5 - 2) * 1.5
        row["vol60"] = (i * 17 % 53) / 53
    groups = {row["code"]: i // 10 + 1 for i, row in enumerate(features)}
    outcomes = {
        row["code"]: {"return": i + (i * 7 % 11 - 5) * 1.5} for i, row in enumerate(features)
    }
    result = partial_rank_correlations(features, outcomes, groups)
    assert result["n"] == 50 and result["raw"] > 0.9
    assert abs(result["momentum"]) < 0.2
    assert result["full"] is not None and abs(result["full"]) < 0.2
    for row in features:
        row["vol60"] = row["momentum"]
    singular = partial_rank_correlations(features, outcomes, groups)
    assert singular["full"] is None and singular["full_reason"] == "rank_deficient"
    assert singular["raw"] is not None


def test_exact_approved_price_bases_and_low_count_result():
    adapted, calendar = _panel()
    adapted["research_price_basis"] = "vendor_adjusted_with_verified_single_code_overlay"
    item = monthly_features(adapted, calendar, "A", "2025-01", "2025-01")[0]
    assert item["price_basis"] == adapted["research_price_basis"] and item["eligible"]
    adapted["research_price_basis"] = "unknown_overlay"
    with pytest.raises(ValueError, match="approved adjusted-price basis"):
        monthly_features(adapted, calendar, "A", "2025-01", "2025-01")
    result = select_weights(_features(29))
    assert result["eligible_n"] == 29 and result["concentration_hhi"] == {}
    assert result["weights"] == {} and result["reason"]
