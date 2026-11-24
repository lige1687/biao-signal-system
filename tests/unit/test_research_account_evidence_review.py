"""Synthetic checks for the opt-in account evidence preflight."""

import json
import os

from lei_signal.research.research_account_evidence_review import (
    review_account_evidence,
    review_file,
)


def _account(gross=0.02, fee=0.2):
    return {
        "gross_return": gross, "net_return": gross - fee / 1000,
        "cost_reconciliation": {
            "convention": "linear_end_period", "nav_start": 1000,
            "fee_amount": fee,
            "trades": [{"notional": 100, "rate_bps": fee * 100,
                        "fee_amount": fee}],
        },
    }


def _payload():
    return {
        "schema": "research-account-evidence/1",
        "expected_months": ["2025-01", "2025-02", "2025-03"],
        "rows": [
            {"month": month, "candidate": _account(), "benchmark": _account(0.01, 0.1),
             "selection_exceptions": []}
            for month in ("2025-01", "2025-02", "2025-03")
        ],
        "sample_role": "exploration", "prior_exposure": "seen",
        "history_reference": "trial-ledger-1",
    }


def _codes(items):
    return {item["code"] for item in items}


def test_three_month_declared_arithmetic_and_continuity():
    result = review_account_evidence(_payload())
    assert result["status"] == "checked"
    assert result["execution_authorized"] is False
    assert result["scientific_validity"] == "not_evaluated"
    assert result["source_verified"] is False
    assert result["coverage"]["expected_count"] == 3
    assert result["coverage"]["net_segments"] == [
        {"start": "2025-01", "end": "2025-03", "count": 3}]
    assert result["continuous_metrics_allowed"] == {"gross": True, "net": True}
    assert result["cost_reconciliation"]["candidate"]["checked"] == [
        "2025-01", "2025-02", "2025-03"]


def test_missing_interior_and_end_months_remain_gaps():
    for missing in ("2025-01", "2025-02", "2025-03"):
        data = _payload()
        data["rows"] = [r for r in data["rows"] if r["month"] != missing]
        result = review_account_evidence(data)
        assert result["status"] == "incomplete"
        assert result["coverage"]["missing_rows"] == [missing]
        assert result["coverage"]["expected_months"] == _payload()["expected_months"]
        assert result["continuous_metrics_allowed"] == {"gross": False, "net": False}
        assert sum(s["count"] for s in result["coverage"]["net_segments"]) == 2
    data = _payload()
    data["rows"][1]["benchmark"]["net_return"] = None
    result = review_account_evidence(data)
    assert result["coverage"]["net_segments"] == [
        {"start": "2025-01", "end": "2025-01", "count": 1},
        {"start": "2025-03", "end": "2025-03", "count": 1}]
    assert result["continuous_metrics_allowed"] == {"gross": True, "net": False}


def test_invalid_calendar_rows_and_numbers_block():
    cases = [
        (lambda p: p["expected_months"].__setitem__(1, "2025-03"), "nonconsecutive_calendar"),
        (lambda p: p["expected_months"].__setitem__(1, "2025-00"), "invalid_calendar_month"),
        (lambda p: p["rows"][1].update(month="2025-01"), "duplicate_month"),
        (lambda p: p["rows"][1].update(month="2025-04"), "outside_calendar"),
        (lambda p: p["rows"][0]["candidate"].update(gross_return=True), "invalid_return"),
        (lambda p: p["rows"][0]["candidate"].update(gross_return=float("inf")), "invalid_return"),
    ]
    for mutate, code in cases:
        data = _payload()
        mutate(data)
        result = review_account_evidence(data)
        assert result["status"] == "blocked"
        assert code in _codes(result["errors"])
        assert result["continuous_metrics_allowed"] == {"gross": False, "net": False}

    data = _payload()
    data["schema"] = "wrong"
    result = review_account_evidence(data)
    assert result["status"] == "blocked"
    assert result["continuous_metrics_allowed"] == {"gross": False, "net": False}

    data = _payload()
    data["rows"][0]["candidate"]["gross_return"] = 10**400
    result = review_account_evidence(data)
    assert result["status"] == "blocked"
    assert "invalid_return" in _codes(result["errors"])


def test_cost_convention_unknowns_zero_trades_and_mismatches():
    data = _payload()
    cost = data["rows"][0]["candidate"]["cost_reconciliation"]
    cost["trades"][0]["fee_amount"] = 0.3
    result = review_account_evidence(data)
    assert result["status"] == "blocked"
    assert "trade_fee_mismatch" in _codes(result["errors"])

    data = _payload()
    data["rows"][0]["candidate"]["cost_reconciliation"]["convention"] = "paid_at_start"
    result = review_account_evidence(data)
    assert result["status"] == "incomplete"
    assert "unsupported_cost_convention" in _codes(result["warnings"])

    data = _payload()
    data["rows"][0]["candidate"].pop("cost_reconciliation")
    assert review_account_evidence(data)["status"] == "incomplete"

    data = _payload()
    data["rows"][0]["candidate"]["cost_reconciliation"].pop("nav_start")
    result = review_account_evidence(data)
    assert result["status"] == "incomplete"
    assert "missing_cost_evidence" in _codes(result["warnings"])

    data = _payload()
    account = data["rows"][0]["candidate"]
    account["net_return"] = account["gross_return"]
    account["cost_reconciliation"]["fee_amount"] = 0
    account["cost_reconciliation"]["trades"] = []
    assert review_account_evidence(data)["status"] == "checked"

    data = _payload()
    data["rows"][0]["candidate"]["net_return"] = 0.02
    result = review_account_evidence(data)
    assert "return_fee_mismatch" in _codes(result["errors"])
    assert result["continuous_metrics_allowed"] == {"gross": False, "net": False}

    data = _payload()
    data["rows"][0]["candidate"]["cost_reconciliation"]["fee_amount"] = 0.3
    result = review_account_evidence(data)
    assert "total_fee_mismatch" in _codes(result["errors"])

    data = _payload()
    data["rows"][0]["candidate"]["cost_reconciliation"]["trades"] = {}
    result = review_account_evidence(data)
    assert result["status"] == "blocked"
    assert "invalid_trades" in _codes(result["errors"])

    data = _payload()
    data["rows"][0]["candidate"]["cost_reconciliation"].pop("trades")
    result = review_account_evidence(data)
    assert result["status"] == "incomplete"
    assert "missing_trades" in _codes(result["warnings"])


def test_exceptions_and_seen_holdout_are_warnings_not_threshold_gates():
    data = _payload()
    data["rows"][0]["selection_exceptions"] = [
        {"reason": "small_industry", "affected_count": 1,
         "selected_weight_share": 0.3132}]
    data["sample_role"] = "holdout"
    data["prior_exposure"] = "seen"
    result = review_account_evidence(data)
    assert result["status"] == "checked_with_warnings"
    assert {"exception_review", "holdout_already_seen"} <= _codes(result["warnings"])
    assert result["selection_exceptions"][0]["selected_weight_share"] == 0.3132
    data["prior_exposure"] = "unseen_declared"
    result = review_account_evidence(data)
    assert result["independent_validation"] == "not_established"


def test_relative_wealth_path_requires_each_return_above_minus_one():
    data = _payload()
    account = data["rows"][1]["candidate"]
    account["gross_return"] = -1.0
    account["net_return"] = -1.0002
    result = review_account_evidence(data)
    assert result["status"] == "checked_with_warnings"
    assert result["continuous_metrics_allowed"] == {"gross": False, "net": False}
    assert "relative_wealth_path_ineligible" in _codes(result["warnings"])


def test_bad_role_types_and_cost_numbers_return_blocked_not_exception():
    data = _payload()
    data["sample_role"] = []
    data["prior_exposure"] = {}
    data["rows"][0]["candidate"]["cost_reconciliation"]["nav_start"] = -1
    result = review_account_evidence(data)
    assert result["status"] == "blocked"
    assert {"invalid_sample_role", "invalid_prior_exposure", "invalid_cost_number"} <= _codes(result["errors"])


def test_file_reader_rejects_traversal_symlink_size_and_bad_json(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_payload()), encoding="utf-8")
    result = review_file(tmp_path, "good.json")
    assert result["status"] == "checked"
    assert result["request_binding"]["status"] == "read"
    assert len(result["request_binding"]["sha256"]) == 64
    assert "invalid_path" in _codes(review_file(tmp_path, "../other.json")["errors"])
    assert "invalid_path" in _codes(review_file(tmp_path, good)["errors"])
    assert "invalid_path" in _codes(review_file(tmp_path, None)["errors"])

    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (tmp_path / "escape.json").symlink_to(outside)
    assert "path_escape" in _codes(review_file(tmp_path, "escape.json")["errors"])

    (tmp_path / "large.json").write_bytes(b" " * (256 * 1024 + 1))
    assert "file_too_large" in _codes(review_file(tmp_path, "large.json")["errors"])
    fifo = tmp_path / "pipe.json"
    os.mkfifo(fifo)
    assert "not_regular_file" in _codes(review_file(tmp_path, "pipe.json")["errors"])
    for content in ('{"schema":1,"schema":2}', '{"x":NaN}', "\xff"):
        (tmp_path / "bad.json").write_bytes(content.encode("utf-8") if content != "\xff" else b"\xff")
        assert "invalid_json" in _codes(review_file(tmp_path, "bad.json")["errors"])


def test_preparation_opt_in_practice_context_and_missing_request(tmp_path):
    from lei_signal.research.preparation import build_context

    request = tmp_path / "account-review.json"
    request.write_text(json.dumps(_payload()), encoding="utf-8")
    context = build_context(tmp_path, practice_only=True,
                            account_review_file="account-review.json")
    assert context["practice_context"]["account_evidence_review"]["status"] == "checked"
    assert context["execution_authorized"] is False
    assert "account_evidence_review" not in build_context(
        tmp_path, practice_only=True, terms=["factor"])["practice_context"]
    missing = build_context(tmp_path, practice_only=True,
                            account_review_file="missing.json")
    review = missing["practice_context"]["account_evidence_review"]
    assert review["status"] == "blocked"
    assert "file_unavailable" in _codes(review["errors"])


def test_finite_inputs_with_overflowing_cost_arithmetic_are_blocked():
    data = _payload()
    data["rows"][0]["candidate"]["cost_reconciliation"]["trades"][0].update(
        notional=10**300, rate_bps=10**300)
    review = review_account_evidence(data)
    assert "cost_calculation_overflow" in _codes(review["errors"])
    assert review["status"] == "blocked"
    assert not any(review["continuous_metrics_allowed"].values())

    data = _payload()
    data["rows"][0]["candidate"].update(gross_return=10**308, net_return=-(10**308))
    review = review_account_evidence(data)
    assert "cost_calculation_overflow" in _codes(review["errors"])
    assert review["status"] == "blocked"
    assert review_account_evidence(None)["continuous_metrics_allowed"] == {
        "gross": False, "net": False}
