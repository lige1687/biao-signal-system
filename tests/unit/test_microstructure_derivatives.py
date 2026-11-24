import math
import json

from lei_signal.market_context.microstructure_derivatives import (
    _sse_rows,
    atm_iv_proxy,
    annualized_basis,
    build_packet,
    put_call_ratios,
    strict_prior_percentiles,
)


def test_put_call_ratios_use_separate_volume_and_open_interest_denominators():
    row = {
        "CALL_VOLUME": "1,000", "PUT_VOLUME": "500",
        "LEAVES_CALL_QTY": "200", "LEAVES_PUT_QTY": "300",
    }
    assert put_call_ratios(row) == (0.5, 1.5)
    row["CALL_VOLUME"] = "0"
    assert put_call_ratios(row) == (None, 1.5)
    row["PUT_VOLUME"] = "-1"
    row["CALL_VOLUME"] = "10"
    assert put_call_ratios(row) == (None, 1.5)


def test_atm_iv_proxy_selects_nearest_expiry_and_balances_put_call():
    rows = [
        {"CONTRACT_ID": "510300C2611M04000", "CONTRACT_TYPE": "认购", "DELTA_VALUE": "0.51", "IMPLC_VOLATLTY": "0.20"},
        {"CONTRACT_ID": "510300P2611M04000", "CONTRACT_TYPE": "认沽", "DELTA_VALUE": "-0.49", "IMPLC_VOLATLTY": "0.24"},
        {"CONTRACT_ID": "510300C2612M04000", "CONTRACT_TYPE": "认购", "DELTA_VALUE": "0.50", "IMPLC_VOLATLTY": "0.50"},
        {"CONTRACT_ID": "510300P2612M04000", "CONTRACT_TYPE": "认沽", "DELTA_VALUE": "-0.50", "IMPLC_VOLATLTY": "0.50"},
    ]
    result = atm_iv_proxy(rows, "2026-11-06", "510300")
    assert result == (22.0, "2611", "04000")


def test_atm_iv_proxy_requires_same_strike_and_positive_iv():
    rows = [
        {"CONTRACT_ID": "510300C2611M04000", "CONTRACT_TYPE": "认购", "DELTA_VALUE": "0.5", "IMPLC_VOLATLTY": "0"},
        {"CONTRACT_ID": "510300P2611M04000", "CONTRACT_TYPE": "认沽", "DELTA_VALUE": "-0.5", "IMPLC_VOLATLTY": "0.2"},
    ]
    assert atm_iv_proxy(rows, "2026-11-06", "510300") is None


def test_etf_option_expiry_is_fourth_wednesday_not_futures_third_friday():
    rows = [
        {"CONTRACT_ID": "510300C2611M04000", "DELTA_VALUE": "0.5", "IMPLC_VOLATLTY": "0.2"},
        {"CONTRACT_ID": "510300P2611M04000", "DELTA_VALUE": "-0.5", "IMPLC_VOLATLTY": "0.2"},
    ]
    assert atm_iv_proxy(rows, "2026-11-23", "510300") == (20.0, "2611", "04000")
    assert atm_iv_proxy(rows, "2026-11-26", "510300") is None


def test_sse_rows_reject_file_date_disagreement_and_future_date(tmp_path):
    (tmp_path / "sse_pcr_20261106.json").write_text(json.dumps({"result": [{"TRADE_DATE": "2026-11-05"}]}))
    (tmp_path / "sse_pcr_20990101.json").write_text(json.dumps({"result": [{"TRADE_DATE": "2099-01-01"}]}))
    assert _sse_rows(tmp_path, "pcr") == {}


def test_cor_history_sorts_deduplicates_and_keeps_missing_close(tmp_path):
    (tmp_path / "cboe_cor3m.csv").write_text("DATE,CLOSE\n11/06/2026,20.4\n11/05/2026,NaN\n11/06/2026,20.5\n")
    card = next(c for c in build_packet(tmp_path)["cards"] if c["id"] == "us-cor3m")
    assert card["points"] == [
        {"date": "2026-11-05", "value": None},
        {"date": "2026-11-06", "value": 20.5},
    ]


def test_strict_prior_percentiles_exclude_current_require_full_window_and_midrank_ties():
    points = [
        {"date": "2026-11-01", "value": 10.0},
        {"date": "2026-11-02", "value": 20.0},
        {"date": "2026-11-03", "value": 20.0},
        {"date": "2026-11-04", "value": None},
        {"date": "2026-11-05", "value": 30.0},
    ]
    result = strict_prior_percentiles(points, 2)
    assert [item["value"] for item in result] == [None, None, 75.0, None, None]
    assert strict_prior_percentiles(points[:3], 2)[-1]["value"] == 75.0


def test_annualized_basis_requires_same_timestamp_and_valid_expiry():
    assert math.isclose(annualized_basis(4100, 4000, "2026-11-06T15:00:00+08:00", "2026-11-06T15:00:00+08:00", "2026-11-20"), 65.17857142857143)
    assert annualized_basis(4100, 4000, "2026-11-06T15:00:00+08:00", "2026-11-06T14:59:00+08:00", "2026-11-20") is None
    assert annualized_basis(4100, 4000, "2026-11-20T15:00:00+08:00", "2026-11-20T15:00:00+08:00", "2026-11-20") is None
    assert annualized_basis(-1, 4000, "2026-11-06T15:00:00+08:00", "2026-11-06T15:00:00+08:00", "2026-11-20") is None
