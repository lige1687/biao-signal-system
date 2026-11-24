"""Synthetic checks for the frozen high52 source-only adapter."""
from __future__ import annotations

import copy

import pandas as pd

from lei_signal.research.fip import SOURCE_FIELDS
from lei_signal.research.high52_revalidation import (
    ADJUSTMENT_FIELDS, adapt_back_adjusted, adjusted_future_outcome,
    audit_unknowns, candidate_features, decompose_increment,
    pct_identity, price_identity, quoted_price_identity,
)


def payload(fields, data):
    return {"fields": list(fields), "data": data, "error_code": "0", "error_msg": "success"}


def raw(day, close, preclose, pct="0.000000", status="1", volume="100"):
    return [day, "sz.000001", close, close, close, close, preclose, volume, "1000", "3",
            status, pct, "0"]


def test_source_precision_intervals_reject_real_gaps():
    assert quoted_price_identity("10.0000000000", "10.0000100000")["intervals_overlap"] is False
    assert not price_identity("10.00", "1.0", "10.02", "1.0")["intervals_overlap"]
    assert price_identity("10.00", "1.0", "10.02", "1.0",
                          same_effective_factor=False)["intervals_overlap"]
    assert price_identity("11.00", "1.0", "10.00", "1.1")["intervals_overlap"]
    assert price_identity("11.5700", "118.423499", "11.3300", "120.932145")["intervals_overlap"]
    assert not price_identity("11.5700", "118.423499", "13.0000", "120.932145")["intervals_overlap"]
    # Source pctChg pads decimals; preserve the old return check while the
    # adjacent adjusted preclose still needs exact source-interval overlap.
    assert pct_identity("1130.0000", "1183.0000", "-4.480100")
    assert not pct_identity("1130.0000", "1183.0000", "-4.470100")


def test_effective_action_factor_and_break_never_backfilled():
    days = ["2023-01-02", "2023-01-03", "2023-01-04"]
    daily = payload(SOURCE_FIELDS, [raw(days[0], "10.0000", "10.0000"),
                                    raw(days[1], "5.0000", "5.0000"),
                                    raw(days[2], "5.1000", "5.0000", "2.000000")])
    actions = payload(ADJUSTMENT_FIELDS, [
        ["sz.000001", "2020-01-01", "1.000000", "1.000000", "1.000000"],
        ["sz.000001", "2023-01-03", "1.000000", "2.000000", "2.000000"],
    ])
    adapted = adapt_back_adjusted(daily, actions, "sz.000001", days)
    assert adapted["break_dates"] == []
    assert [r["close"] for r in adapted["rows"]] == ["10.0000000000", "10.0000000000", "10.2000000000"]
    broken = copy.deepcopy(daily)
    broken["data"][1][6] = "6.0000"
    result = adapt_back_adjusted(broken, actions, "sz.000001", days)
    assert days[1] in result["break_dates"]
    assert "adjusted_preclose_break" in result["failures"][days[1]]


def test_fore_factor_avoids_back_normalization_jump_without_repairing_quotes():
    days = ["2020-12-30", "2020-12-31", "2021-01-04"]
    daily = payload(SOURCE_FIELDS, [raw(day, "10.0000", "10.0000") for day in days])
    actions = payload(ADJUSTMENT_FIELDS, [
        ["sz.000001", "2020-01-01", "1.000000", "1.000000", "1.000000"],
        ["sz.000001", "2020-12-31", "1.000000", "2.000000", "2.000000"],
    ])
    fore = adapt_back_adjusted(daily, actions, "sz.000001", days,
                               factor_field="foreAdjustFactor")
    back = adapt_back_adjusted(daily, actions, "sz.000001", days,
                               factor_field="backAdjustFactor")
    assert fore["break_dates"] == []
    assert days[1] in back["break_dates"]
    assert all(r["factor_field"] == "foreAdjustFactor" for r in fore["rows"])


def test_only_interval_compatible_preclose_is_normalized_with_raw_provenance():
    days = ["2023-01-02", "2023-01-03", "2023-01-04"]
    daily = payload(SOURCE_FIELDS, [raw(days[0], "10.0000", "10.0000"),
                                    raw(days[1], "10.0100", "10.0001", "0.099000"),
                                    raw(days[2], "10.0200", "10.5000", "-4.571429")])
    actions = payload(ADJUSTMENT_FIELDS, [
        ["sz.000001", "2020-01-01", "1.000000", "1.000000", "1.000000"]])
    result = adapt_back_adjusted(daily, actions, "sz.000001", days,
                                 factor_field="foreAdjustFactor")
    good, bad = result["rows"][1:]
    assert good["normalized_preclose"] is True
    assert good["preclose"] == result["rows"][0]["close"]
    assert good["raw_preclose"] == "10.0001"
    assert good["quoted_adjusted_preclose"] == "10.0001000000"
    assert good["preclose_normalization_delta"] == "-0.0001000000"
    assert good["pctChg"] == "0.099000"  # Vendor raw percent is never relabeled.
    assert good["derived_pctChg"] != good["pctChg"]
    assert bad["normalized_preclose"] is False
    assert days[2] in result["break_dates"]
    assert bad["preclose"] == bad["quoted_adjusted_preclose"]


def test_observed_flat_suspension_with_blank_ohlc_remains_close_qualified():
    days = ["2023-01-02", "2023-01-03", "2023-01-04"]
    halt = raw(days[1], "10.0000", "10.0000", pct="", status="0", volume="")
    halt[2:5] = ["", "", ""]
    halt[12] = ""  # ST is only a decision-day gate, not a missing-halt-price gate.
    daily = payload(SOURCE_FIELDS, [raw(days[0], "10.0000", "10.0000"), halt,
                                    raw(days[2], "10.1000", "10.0000", "1.000000")])
    actions = payload(ADJUSTMENT_FIELDS, [
        ["sz.000001", "2020-01-01", "1.000000", "1.000000", "1.000000"]])
    result = adapt_back_adjusted(daily, actions, "sz.000001", days,
                                 factor_field="foreAdjustFactor")
    assert len(result["rows"]) == 3
    assert result["break_dates"] == []
    assert result["rows"][1]["close"] == result["rows"][0]["close"]
    assert result["rows"][1]["open"] == ""


def test_future_quote_ignores_exit_close_but_retains_break_and_flat_uncertainty():
    days = ["2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
    daily = payload(SOURCE_FIELDS, [
        raw(days[0], "10.0000", "10.0000"),
        [days[1], "sz.000001", "10.0000", "10.1000", "10.0000", "10.1000", "10.0000",
         "100", "1000", "3", "1", "1.000000", "0"],
        [days[2], "sz.000001", "10.1000", "10.2000", "10.1000", "10.2000", "10.1000",
         "100", "1000", "3", "1", "0.990099", "0"],
        [days[3], "sz.000001", "11.0000", "1000.0000", "10.2000", "1000.0000", "10.2000",
         "100", "1000", "3", "1", "", "0"],
    ])
    actions = payload(ADJUSTMENT_FIELDS, [
        ["sz.000001", "2020-01-01", "1.000000", "1.000000", "1.000000"]])
    adapted = adapt_back_adjusted(daily, actions, "sz.000001", days,
                                  factor_field="foreAdjustFactor")
    result = adjusted_future_outcome(adapted, days, days[0], days[1], days[3])
    assert abs(result["return"] - 0.1) < 1e-12
    assert result["adverse"] == 0.0
    assert abs(result["opportunity"] - 0.1) < 1e-12
    assert result["exit_flat_assessment_available"] is True
    broken = {**adapted, "break_dates": [days[2]]}
    assert adjusted_future_outcome(broken, days, days[0], days[1], days[3])["return"] is None
    flat = copy.deepcopy(daily)
    flat["data"][1][2:6] = ["10.1000"] * 4
    flat["data"][1][11] = "1.000000"
    flat_adapted = adapt_back_adjusted(flat, actions, "sz.000001", days,
                                       factor_field="foreAdjustFactor")
    flat_result = adjusted_future_outcome(flat_adapted, days, days[0], days[1], days[3])
    assert flat_result["return"] is not None
    assert flat_result["entry_directional_flat_quote"] is True
    assert flat_result["adverse_flat_as_unknown_return"] is None
    favorable = copy.deepcopy(daily)
    favorable["data"][1][2:6] = ["9.9000"] * 4
    favorable["data"][1][11] = "-1.000000"
    favorable["data"][2][2:7] = ["9.9000", "10.0000", "9.9000", "10.0000", "9.9000"]
    favorable["data"][2][11] = "1.010101"
    favorable["data"][3][2:7] = ["10.1000", "10.1000", "10.1000", "10.1000", "10.0000"]
    favorable["data"][3][11] = "1.000000"
    favorable_adapted = adapt_back_adjusted(favorable, actions, "sz.000001", days,
                                            factor_field="foreAdjustFactor")
    favorable_result = adjusted_future_outcome(favorable_adapted, days, days[0], days[1], days[3])
    assert favorable_result["entry_flat_direction"] == "down"
    assert favorable_result["exit_flat_direction"] == "up"
    assert favorable_result["adverse_flat_as_unknown_return"] == favorable_result["return"]
    assert favorable_result["entry_fill_confirmed"] is False
    assert favorable_result["exit_fill_confirmed"] is False
    halted = copy.deepcopy(daily)
    halted["data"][2][2:7] = ["", "", "", "10.1000", "10.1000"]
    halted["data"][2][7] = ""
    halted["data"][2][10:13] = ["0", "", ""]
    halted["data"][3][6] = "10.1000"
    halted_adapted = adapt_back_adjusted(halted, actions, "sz.000001", days,
                                        factor_field="foreAdjustFactor")
    halted_result = adjusted_future_outcome(halted_adapted, days, days[0], days[1], days[3])
    assert halted_result["return"] is not None
    assert abs(halted_result["return"] - 0.1) < 1e-12
    assert halted_result["adverse"] == 0.0
    bad_halt = copy.deepcopy(halted)
    bad_halt["data"][2][5] = "10.2000"
    bad_adapted = adapt_back_adjusted(bad_halt, actions, "sz.000001", days,
                                     factor_field="foreAdjustFactor")
    bad_result = adjusted_future_outcome(bad_adapted, days, days[0], days[1], days[3])
    assert bad_result["return"] is None


def test_increment_decomposition_reconciles_and_preserves_unknown_weight():
    outcomes = {"a": {"return": 0.2}, "b": {"return": -0.3},
                "c": {"return": 0.4}, "d": {"return": None}}
    result = decompose_increment(["a", "d"], ["b", "c"], outcomes)
    assert abs(result["added_gain"] - 0.1) < 1e-12
    assert abs(result["avoided_loss"] - 0.15) < 1e-12
    assert abs(result["foregone_gain"] + 0.2) < 1e-12
    assert abs(result["known_increment"] - 0.05) < 1e-12
    assert abs(result["unknown_weight_coefficient_same_shock"] - 0.5) < 1e-12
    assert abs(result["adverse_mixed_assignment"] + 0.45) < 1e-12


def test_old_unknown_audit_retains_original_gap_and_quote_delay():
    days = ["2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
    rows = [raw(days[0], "10.0000000000", "10.0000000000"),
            raw(days[1], "10.0000000000", "10.0000000000", status="0", volume="0"),
            raw(days[2], "10.0100000000", "10.0000100000"),
            raw(days[3], "10.0200000000", "10.0100000000")]
    for row in rows:
        row[9] = "2"
    original = {"month": "2022-12", "code": "sz.000001", "decision_date": days[0],
                "entry_date": days[1], "exit_date": days[3], "return": "",
                "reason": "entry_or_exit_not_executable_quote"}
    audit = audit_unknowns([original], {"sz.000001": payload(SOURCE_FIELDS, rows)},
                           days, {"sz.000001": ""})[0]
    assert audit["entry_status"] == "suspended"
    assert audit["entry_first_later_traded_quote"] == days[2]
    assert audit["entry_delay_sessions"] == 1
    assert audit["first_gap_date"] == days[2]
    assert audit["gap_intervals_overlap"] is False
    assert audit["original_reason"] == original["reason"]


def test_same_day_scaling_and_future_rows_do_not_change_decision_features():
    days = pd.bdate_range("2020-01-01", "2023-02-28").strftime("%Y-%m-%d").tolist()
    cut = "2023-01-31"
    prices = [100 + 0.03 * i + 0.7 * ((i % 17) / 17) for i in range(len(days))]
    rows = []
    for i, day in enumerate(days):
        close = prices[i]
        rows.append({"date": day, "code": "sz.000001", "close": str(close),
                     "preclose": str(prices[i-1] if i else close), "volume": "100",
                     "tradestatus": "1", "isST": "0"})
    factors = {}
    months = sorted({d[:7] for d in days})
    for i, month in enumerate(months):
        factors[month] = (0.001, (i % 7) / 200, (i % 11) / 300, (i % 5) / 400)
    base = candidate_features({"rows": [r for r in rows if r["date"] <= cut], "break_dates": []},
                              [d for d in days if d <= cut], factors, "sz.000001", "2023-01", "2023-01")[0]
    scaled = copy.deepcopy(rows)
    for row in scaled:
        row["close"] = str(float(row["close"]) * 2)
        row["preclose"] = str(float(row["preclose"]) * 2)
    changed = candidate_features({"rows": scaled, "break_dates": []}, days, factors,
                                 "sz.000001", "2023-01", "2023-01")[0]
    assert base["eligible"] == changed["eligible"]
    assert base["reasons"] == changed["reasons"]
    assert abs(base["high52"] - changed["high52"]) < 1e-12
    for score in ("ordinary", "arithmetic_control", "scaled_control", "residual"):
        assert abs(base[score] - changed[score]) < 1e-9
    broken = candidate_features({"rows": rows, "break_dates": ["2022-06-15"]}, days, factors,
                                "sz.000001", "2023-01", "2023-01")[0]
    assert not broken["eligible"]
    assert "adjusted_price_break_in_window" in broken["reasons"]
    future_broken = candidate_features({"rows": rows, "break_dates": ["2023-02-15"]}, days, factors,
                                       "sz.000001", "2023-01", "2023-01")[0]
    assert future_broken["eligible"] == base["eligible"]
