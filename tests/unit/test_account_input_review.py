"""Account preflight checks field identity and cash conservation, not returns."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy

import pytest

from lei_signal.research.account_input_review import review_account_input


def account():
    return {
        "account_id": "acct-1",
        "as_of": "2026-10-31",
        "source_id": "broker-1",
        "confirmation": {"basis": "broker_statement", "reference": "export-1"},
        "captured_at": "2026-10-31T16:00:00+08:00",
        "currency": "CNY",
        "cash": [
            {
                "currency": "CNY",
                "available": 1000,
                "available_on": "2026-10-31",
                "as_of": "2026-10-31",
                "source_id": "broker-1",
            }
        ],
        "holdings": [
            {
                "code": "510300",
                "currency": "CNY",
                "total_shares": 100,
                "sellable_shares": 80,
                "settlement_date": "2026-10-31",
                "as_of": "2026-10-31",
                "source_id": "broker-1",
            }
        ],
    }


def codes(result):
    return {item["code"] for item in result["findings"]}


def test_confirmed_document_ready_and_no_orders():
    result = review_account_input(account())
    assert result["status"] == "ready"
    assert result["cash_available"] == {"CNY": 1000}
    assert "orders" not in result


def test_existing_portfolio_snapshot_is_only_valuation_evidence():
    result = review_account_input(
        {
            "as_of": "2026-09-04",
            "data_source_cn": "截图",
            "groups": [{"holdings": [{"code": "510300", "market_value": 500}]}],
        }
    )
    assert result["status"] == "incomplete"
    assert result["input_kind"] == "portfolio_snapshot"
    assert {"confirmed_total_shares", "cash", "settlement", "market_value_only"} <= codes(result)


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("total_shares", float("nan"), "total_shares"),
        ("sellable_shares", -1, "sellable_shares"),
        ("sellable_shares", 101, "sellable_exceeds_total"),
        ("settlement_date", "2026-11-01", "unsettled_sellable"),
        ("currency", "USD", "currency_conflict"),
        ("as_of", "2026-10-30", "date_conflict"),
        ("source_id", "other", "source_conflict"),
    ],
)
def test_holding_conflicts(field, value, expected):
    value_input = account()
    value_input["holdings"][0][field] = value
    result = review_account_input(value_input)
    assert result["ready"] is False
    assert expected in codes(result)


def test_implied_shares_do_not_replace_confirmed_shares():
    value_input = account()
    del value_input["holdings"][0]["total_shares"]
    value_input["holdings"][0]["implied_shares"] = 100
    result = review_account_input(value_input)
    assert result["status"] == "invalid"
    assert {"total_shares", "implied_not_confirmed"} <= codes(result)


def test_duplicate_security_and_cash_are_invalid():
    value_input = account()
    value_input["holdings"].append(deepcopy(value_input["holdings"][0]))
    value_input["cash"].append(deepcopy(value_input["cash"][0]))
    assert {"duplicate_security", "duplicate_cash"} <= codes(review_account_input(value_input))


def test_two_cash_requests_share_one_balance_and_failed_sale_does_not_release():
    value_input = account()
    value_input["sale_receipts"] = [
        {
            "id": "sell-1",
            "status": "failed",
            "as_of": "2026-10-31",
            "source_id": "broker-1",
            "account_id": "acct-1",
            "currency": "CNY",
        }
    ]
    value_input["requests"] = [
        {"id": "buy-1", "currency": "CNY", "amount": 700},
        {"id": "buy-2", "currency": "CNY", "amount": 500, "depends_on_sale_id": "sell-1"},
    ]
    result = review_account_input(value_input)
    assert result["status"] == "invalid"
    assert {"shared_cash_exceeded", "sale_cash_unavailable"} <= codes(result)
    assert result["cash_requested"] == {"CNY": 1200}


def test_settled_receipt_is_not_added_twice_to_confirmed_cash():
    value_input = account()
    value_input["sale_receipts"] = [
        {
            "id": "sell-1",
            "status": "settled",
            "as_of": "2026-10-31",
            "source_id": "broker-1",
            "available_on": "2026-10-31",
            "included_in_cash": True,
            "account_id": "acct-1",
            "currency": "CNY",
        }
    ]
    value_input["requests"] = [
        {"id": "buy-1", "currency": "CNY", "amount": 1200, "depends_on_sale_id": "sell-1"}
    ]
    assert "shared_cash_exceeded" in codes(review_account_input(value_input))


def test_cash_future_date_and_nonfinite_amount_rejected():
    value_input = account()
    value_input["cash"][0].update(available=float("inf"), available_on="2026-11-01")
    assert {"invalid_amount", "cash_not_available"} <= codes(review_account_input(value_input))


def test_capture_and_receipt_time_conflicts():
    value_input = account()
    value_input["captured_at"] = "2026-10-30T16:00:00+08:00"
    value_input["sale_receipts"] = [
        {
            "id": "sell-1",
            "status": "settled",
            "as_of": "2026-10-30",
            "source_id": "other",
            "available_on": "2026-11-01",
            "included_in_cash": True,
            "account_id": "acct-1",
            "currency": "CNY",
        }
    ]
    assert {
        "capture_before_effective",
        "date_conflict",
        "source_conflict",
        "sale_cash_unavailable",
    } <= codes(review_account_input(value_input))


def test_malformed_sale_reference_returns_finding_not_exception():
    value_input = account()
    value_input["requests"] = [
        {"id": "r", "currency": "CNY", "amount": 1, "depends_on_sale_id": ["sell-1"]}
    ]
    assert "unknown_sale" in codes(review_account_input(value_input))


def test_huge_numbers_and_malformed_root_date_remain_json_serializable():
    value_input = account()
    value_input["as_of"] = float("nan")
    value_input["cash"][0]["available"] = 10**1000
    value_input["requests"] = [
        {"id": "r1", "currency": "CNY", "amount": 1e308},
        {"id": "r2", "currency": "CNY", "amount": 1e308},
    ]
    result = review_account_input(value_input)
    assert {"invalid_amount", "request_sum_overflow"} <= codes(result)
    json.dumps(result, allow_nan=False)


def test_future_cash_request_is_outside_current_account_snapshot():
    value_input = account()
    value_input["requests"] = [{"id": "r", "currency": "CNY", "amount": 10, "as_of": "2026-11-01"}]
    assert "request_date_conflict" in codes(review_account_input(value_input))


def test_grouped_portfolio_with_added_account_fields_is_ambiguous():
    value_input = account()
    value_input["groups"] = [{"holdings": [{"market_value": 900}]}]
    result = review_account_input(value_input)
    assert result["status"] == "invalid"
    assert result["input_kind"] == "ambiguous"
    assert "ambiguous_portfolio_account" in codes(result)


def test_known_estimates_and_missing_confirmation_cannot_be_ready():
    value_input = account()
    value_input["source_id"] = "portfolio-estimate"
    for row in value_input["cash"] + value_input["holdings"]:
        row["source_id"] = "portfolio-estimate"
        row["estimated"] = True
    value_input["holdings"][0]["implied_shares"] = 100
    del value_input["confirmation"]
    result = review_account_input(value_input)
    assert result["ready"] is False
    assert {
        "valuation_source",
        "estimated_input",
        "implied_not_confirmed",
        "confirmation",
    } <= codes(result)


def test_market_value_allowed_with_declared_confirmation_but_not_authenticated():
    value_input = account()
    value_input["holdings"][0]["market_value"] = 900
    result = review_account_input(value_input)
    assert result["ready"] is True
    assert result["provenance_verification"] == "declared_unverified"


def test_decision_time_availability_is_separate_from_input_completeness():
    value_input = account()
    assert review_account_input(value_input)["availability_at_decision"] == "unknown"
    value_input["decision_at"] = "2026-10-31T15:00:00+08:00"
    earlier = review_account_input(value_input)
    assert earlier["availability_at_decision"] == "unavailable"
    assert "unavailable_at_decision" in codes(earlier)
    value_input["decision_at"] = "2026-10-31T17:00:00+08:00"
    later = review_account_input(value_input)
    assert later["availability_at_decision"] == "declared_available"
    assert later["ready"] is True


def test_sale_dependency_requires_matching_account_currency_and_cash_inclusion():
    value_input = account()
    value_input["sale_receipts"] = [
        {
            "id": "sell-1",
            "status": "settled",
            "as_of": "2026-10-31",
            "source_id": "broker-1",
            "available_on": "2026-10-31",
            "included_in_cash": False,
            "account_id": "other",
            "currency": "USD",
        }
    ]
    value_input["requests"] = [
        {"id": "buy-1", "currency": "CNY", "amount": 500, "depends_on_sale_id": "sell-1"}
    ]
    result = review_account_input(value_input)
    assert result["ready"] is False
    assert {
        "sale_account_conflict",
        "sale_currency_conflict",
        "sale_request_currency_conflict",
        "sale_not_in_cash",
        "sale_cash_unavailable",
    } <= codes(result)


def test_missing_sale_provenance_is_unknown_not_valid_dependency():
    value_input = account()
    value_input["sale_receipts"] = [
        {"id": "sell-1", "status": "settled", "available_on": "2026-10-31"}
    ]
    value_input["requests"] = [
        {"id": "buy-1", "currency": "CNY", "amount": 500, "depends_on_sale_id": "sell-1"}
    ]
    result = review_account_input(value_input)
    assert result["ready"] is False
    assert {
        "row_source",
        "row_as_of",
        "sale_account_id",
        "sale_currency",
        "sale_not_in_cash",
    } <= codes(result)


def test_cli_stdin_emits_json_and_nonready_exit():
    proc = subprocess.run(
        [sys.executable, "-m", "lei_signal.research.account_input_review", "-"],
        input=json.dumps({"groups": []}),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["input_kind"] == "portfolio_snapshot"
