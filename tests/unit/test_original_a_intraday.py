"""Synthetic qualification cases; no vendor or market data access."""
import copy
import json

from lei_signal.research.original_a_intraday import SLOTS_15, SLOTS_60, audit_intraday_asset

CODE = "sh.600000"
DAY = "2026-10-16"


def fixture(day=DAY):
    stamp = day.replace("-", "")
    q = []
    for slot in SLOTS_15:
        q.append({"date": day, "time": stamp + slot + "00000", "code": CODE,
                  "open": "10.0000", "high": "11.0000", "low": "9.0000", "close": "10.0000",
                  "volume": "1", "amount": "10.0000", "adjustflag": "3"})
    h = []
    for slot in SLOTS_60:
        h.append({**q[0], "time": stamp + slot + "00000", "volume": "4", "amount": "40.0000"})
    raw = [{"date": day, "code": CODE, "open": "10", "high": "11", "low": "9",
            "close": "10", "volume": "16", "amount": "160", "preclose": "10",
            "tradestatus": "1", "pctChg": "0", "adjustflag": "3"}]
    back = [{**raw[0], "open": "20", "high": "22", "low": "18", "close": "20", "adjustflag": "1"}]
    factor = [{"code": CODE, "dividOperateDate": day, "backAdjustFactor": "2",
               "foreAdjustFactor": "0.5", "adjustFactor": "2"}]
    return [q, h, raw, back, factor, [day]]


def run(case):
    return audit_intraday_asset(CODE, *case)


def kinds(report):
    return {(f["layer"], f["kind"]) for f in report["findings"]}


def test_complete_case_is_only_numerically_qualified():
    result = run(fixture())
    json.dumps(result)
    assert result["qualified_for_price_descriptive_use"]
    assert result["days"][0]["qualified_for_quantity_use"]
    assert result["comparisons"]["15_to_60"]["matched"] == 4
    assert result["comparisons"]["60_to_daily"]["matched"] == 1
    assert result["comparisons"]["backadj_ratio"]["matched"] == 1
    assert result["comparisons"]["factor_ratio"]["matched"] == 1
    assert result["adjusted_basis_qualified"]
    assert result["longest_run"] == {"start": DAY, "end": DAY, "trading_days": 1}
    assert not result["qualified_for_full_A"]
    assert result["arrival_unknown"] and result["revisions_unknown"]


def test_missing_and_duplicate_bars_reject_day():
    missing = fixture()
    missing[0].pop(8)  # first afternoon slot: never invent a lunch bar
    result = run(missing)
    assert not result["qualified_for_price_descriptive_use"]
    assert ("bars15", "incomplete") in kinds(result)
    assert result["days"][0]["bars15"] == 15
    duplicate = fixture()
    duplicate[0].append(copy.deepcopy(duplicate[0][-1]))
    result = run(duplicate)
    assert ("bars15", "duplicate") in kinds(result)
    assert ("bars15", "order") in kinds(result)
    assert not result["qualified_for_price_descriptive_use"]


def test_price_and_quantity_discrepancies_have_separate_uses():
    case = fixture()
    case[1][0]["volume"] = "4.1"
    result = run(case)
    assert result["qualified_for_price_descriptive_use"]
    assert not result["days"][0]["qualified_for_quantity_use"]
    assert result["intraday_15_to_60_internal_qualified"]
    assert not result["intraday_15_to_60_quantity_qualified"]
    assert result["comparisons"]["15_to_60"]["mismatched"] == 1
    case = fixture()
    case[1][0]["close"] = "10.01"
    result = run(case)
    assert not result["qualified_for_price_descriptive_use"]


def test_daily_close_difference_preserves_ohl_and_internal_evidence():
    case = fixture()
    case[2][0]["close"] = "10.001"
    result = run(case)
    assert not result["qualified_for_price_descriptive_use"]
    assert result["daily_ohl_qualified"]
    assert result["intraday_15_to_60_internal_qualified"]
    assert ("60_to_daily", "daily_close_difference") in kinds(result)
    assert result["comparisons"]["60_to_daily"]["fields"]["close"]["mismatched"] == 1
    assert result["comparisons"]["60_to_daily"]["fields"]["high"]["matched"] == 1


def test_future_factor_not_backfilled_and_ratio_mismatch_reported():
    case = fixture()
    case[4][0]["dividOperateDate"] = "2026-10-19"
    result = run(case)
    assert ("factors", "no_prior_factor") in kinds(result)
    assert "factor_date" not in result["days"][0]
    case = fixture()
    case[3][0]["high"] = "22.2"
    result = run(case)
    assert ("backadj_ratio", "mismatch") in kinds(result)
    case = fixture()
    case[4][0]["backAdjustFactor"] = "3"
    result = run(case)
    assert ("factor_ratio", "mismatch") in kinds(result)


def test_nonfinite_and_order_rejected():
    case = fixture()
    case[0][0]["close"] = "NaN"
    assert ("bars15", "invalid_row") in kinds(run(case))
    case = fixture()
    case[0][0]["amount"] = "Infinity"
    assert ("bars15", "invalid_row") in kinds(run(case))
    case = fixture()
    case[0][0], case[0][1] = case[0][1], case[0][0]
    assert ("bars15", "order") in kinds(run(case))


def test_suspension_is_not_missing_daily_and_splits_runs():
    case = fixture()
    second = "2026-10-19"
    case[2].append({"date": second, "code": CODE, "tradestatus": "0", "adjustflag": "3"})
    case[5].append(second)
    result = run(case)
    assert result["days"][1]["status"] == "suspended"
    assert ("daily_raw", "missing") not in kinds(result)
    assert result["longest_run"]["trading_days"] == 1
    case = fixture()
    case[5].append(second)
    result = run(case)
    assert result["days"][1]["status"] == "daily_unknown"
    assert ("daily_raw", "missing") in kinds(result)


def test_daily_row_order_and_zero_volume_do_not_imply_execution():
    case = fixture()
    second = "2026-10-19"
    later = fixture(second)
    case[0].extend(later[0])
    case[1].extend(later[1])
    case[2].extend(later[2])
    case[3].extend(later[3])
    case[5].append(second)
    case[2].reverse()
    result = run(case)
    assert ("daily_raw", "order_or_duplicate") in kinds(result)
    case = fixture()
    for row in case[0] + case[1] + case[2]:
        row["volume"] = "0"
        row["amount"] = "0"
    result = run(case)
    assert result["qualified_for_price_descriptive_use"]
    assert result["trading_executability_unknown"]


def test_daily_adjustment_flags_and_factor_asset_identity():
    case = fixture()
    case[2][0]["adjustflag"] = "1"
    result = run(case)
    assert ("daily_raw", "invalid_row") in kinds(result)
    assert not result["qualified_for_price_descriptive_use"]
    assert not result["adjusted_basis_qualified"]
    case = fixture()
    case[3][0]["adjustflag"] = "3"
    result = run(case)
    assert ("daily_backadj", "invalid_row") in kinds(result)
    assert result["qualified_for_price_descriptive_use"]
    assert not result["adjusted_basis_qualified"]
    case = fixture()
    case[4][0]["code"] = "sz.000001"
    result = run(case)
    assert ("factors", "invalid_row") in kinds(result)
    assert not result["adjusted_basis_qualified"]


def test_factor_price_precision_and_ambiguous_effective_record():
    case = fixture()
    case[4][0]["backAdjustFactor"] = "2.0000000005"
    result = run(case)
    assert result["adjusted_basis_qualified"]
    assert result["comparisons"]["factor_ratio"]["matched"] == 1
    assert result["comparisons"]["factor_ratio"]["max_abs_diff"]["ratio"] != "0"
    case = fixture()
    case[4].append({**case[4][0], "backAdjustFactor": "3"})
    result = run(case)
    assert ("factors", "ambiguous_effective_factor") in kinds(result)
    assert not result["adjusted_basis_qualified"]
    case = fixture()
    case[4][0]["foreAdjustFactor"] = "NaN"
    result = run(case)
    assert ("factors", "ambiguous_effective_factor") in kinds(result)
    assert not result["adjusted_basis_qualified"]


def test_missing_backadj_and_factor_keep_raw_descriptive_use():
    case = fixture()
    case[3] = []
    result = run(case)
    assert result["qualified_for_price_descriptive_use"]
    assert not result["adjusted_basis_qualified"]
    case = fixture()
    case[4] = []
    result = run(case)
    assert result["qualified_for_price_descriptive_use"]
    assert not result["adjusted_basis_qualified"]
