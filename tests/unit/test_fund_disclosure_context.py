"""Disclosed constituents are bounded historical evidence, not live industry weights."""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi import FastAPI, Request

from lei_signal.copilot.portfolio_context import build_portfolio_context
from lei_signal.portfolio.disclosure_context import disclosure_for_holding, load_disclosures

TODAY = date(2026, 10, 12)


def _record(code="000001", *, name="同名基金A", holdings=None):
    return {
        "fund_code": code, "fund_name": name, "checked_at": "2026-10-12T10:00:00+08:00",
        "source_url": "https://example.org/disclosure", "source_name": "公开季报",
        "scope": "direct_stock_top10", "published_at": "2026-08-30",
        "report_period": "2026Q2", "report_date": "2026-06-30",
        "status": "available",
        "holdings": holdings if holdings is not None else [
            {"stock_code": "600001", "stock_name": "甲公司", "weight_pct": 12.5,
             "market": "cn", "industry_label": "工业",
             "industry_source_url": "https://example.org/industry"},
            {"stock_code": "600002", "stock_name": "乙公司", "weight_pct": 7.5,
             "market": "cn", "industry_label": "科技"},
        ],
    }


def _catalog(tmp_path, rows, *, today=TODAY):
    path = tmp_path / "disclosures.json"
    path.write_text(json.dumps({"schema_version": 1, "funds": rows}), encoding="utf-8")
    return load_disclosures(path, today=today)


def test_exact_code_and_partial_industry_do_not_normalize_to_full_fund(tmp_path):
    catalog = _catalog(tmp_path, [_record(), _record("000002", name="同名基金C",
                                                  holdings=[{"stock_code": "600003",
                                                             "stock_name": "丙公司",
                                                             "weight_pct": 5,
                                                             "market": "cn"}])])
    a = disclosure_for_holding("000001", "同名基金A", catalog)
    c = disclosure_for_holding("000002", "同名基金C", catalog)
    assert a["status"] == c["status"] == "available"
    assert a["coverage_pct"] == 20
    assert a["industry_coverage_pct"] == 12.5
    assert a["unknown_pct"] == 80
    assert a["industry_unknown_pct"] == 87.5
    assert a["by_industry_pct"] == {"工业": 12.5}
    assert a["holdings"][1]["industry_label"] is None
    assert c["coverage_pct"] == 5
    assert c["industry_coverage_pct"] == 0
    assert disclosure_for_holding("000003", "同名基金A", catalog)["status"] == "missing"


@pytest.mark.parametrize("change", [
    {"report_period": "2026Q3"},
    {"report_date": "2026-09-30"},
    {"report_date": "2026-12-31", "report_period": "2026Q4"},
    {"published_at": "2026-06-29"},
    {"checked_at": "2026-06-01"},
    {"checked_at": "2026-10-13"},
])
def test_future_or_conflicting_dates_are_invalid(tmp_path, change):
    row = _record()
    row.update(change)
    disclosure = disclosure_for_holding("000001", "甲基金", _catalog(tmp_path, [row]))
    assert disclosure["status"] == "invalid"
    assert disclosure["coverage_pct"] is None
    assert disclosure["holdings"] == []


def test_bad_weights_duplicate_rows_and_unavailable_scope_do_not_claim_coverage(tmp_path):
    row = _record(holdings=[
        {"stock_code": "600001", "stock_name": "甲", "weight_pct": 60, "market": "cn"},
        {"stock_code": "600002", "stock_name": "乙", "weight_pct": 50, "market": "cn"},
    ])
    assert disclosure_for_holding("000001", "甲", _catalog(tmp_path, [row]))["status"] == "invalid"
    row = _record()
    row["holdings"].append(dict(row["holdings"][0]))
    assert disclosure_for_holding("000001", "甲", _catalog(tmp_path, [row]))["status"] == "invalid"
    row = _record()
    row["status"] = "unavailable"
    row["holdings"] = []
    result = disclosure_for_holding("000001", "甲FOF", _catalog(tmp_path, [row]))
    assert result["status"] == "unavailable"
    assert result["coverage_pct"] == 0
    assert "FOF" in " ".join(result["limitations"])


def test_unavailable_public_table_can_have_no_known_report_period(tmp_path):
    row = _record()
    row.update(status="unavailable", holdings=[], report_period=None,
               report_date=None, published_at=None)
    result = disclosure_for_holding("000001", "甲基金", _catalog(tmp_path, [row]))
    assert result["status"] == "unavailable"
    assert result["source_url"] == row["source_url"]
    assert result["checked_at"] == row["checked_at"]
    assert result["coverage_pct"] == 0
    assert result["unknown_pct"] == 100
    assert result["holdings"] == []


def test_zero_rounded_weight_unknown_market_and_classification_note(tmp_path):
    row = _record(holdings=[
        {"stock_code": "005930", "stock_name": "韩国公司", "weight_pct": 0.0,
         "market": "unknown", "industry_label": "半导体",
         "industry_source_url": "https://example.org/classification",
         "classification_note": "主要业务概括，并非营收拆分"},
        {"stock_code": "000660", "stock_name": "另一韩国公司", "weight_pct": 0.0},
    ])
    result = disclosure_for_holding("000001", "甲基金", _catalog(tmp_path, [row]))
    assert result["status"] == "available"
    assert len(result["holdings"]) == 2
    assert result["holdings"][0]["market"] == result["holdings"][1]["market"] == "unknown"
    assert result["holdings"][0]["classification_note"] == "主要业务概括，并非营收拆分"
    assert result["coverage_pct"] == result["industry_coverage_pct"] == 0
    assert result["unknown_pct"] == result["industry_unknown_pct"] == 100
    assert "按各业务收入精确拆分" in " ".join(result["limitations"])


def test_invalid_date_preserves_source_for_review(tmp_path):
    row = _record()
    row["report_period"] = "2026Q3"
    result = disclosure_for_holding("000001", "甲基金", _catalog(tmp_path, [row]))
    assert result["status"] == "invalid"
    assert result["source_url"] == row["source_url"]
    assert result["source_name"] == row["source_name"]
    assert result["checked_at"] == row["checked_at"]
    assert result["report_date"] == row["report_date"]
    assert result["report_period"] == row["report_period"]


def test_source_check_snapshot_requires_recheck_next_day_without_discarding_report(tmp_path):
    row = _record()
    today = disclosure_for_holding("000001", "甲基金", _catalog(tmp_path, [row]))
    tomorrow = disclosure_for_holding("000001", "甲基金", _catalog(
        tmp_path, [row], today=date(2026, 10, 13)))
    assert today["status"] == tomorrow["status"] == "available"
    assert today["is_realtime"] is tomorrow["is_realtime"] is False
    assert today["source_recheck_required"] is False
    assert tomorrow["source_recheck_required"] is True
    assert tomorrow["report_date"] == today["report_date"]
    assert tomorrow["holdings"] == today["holdings"]
    assert "来源上次核对为2026-10-12，本次尚未检查更近披露" in " ".join(tomorrow["limitations"])
    assert disclosure_for_holding("000003", "缺失基金", _catalog(tmp_path, [row]))["source_recheck_required"] is True
    row.update(status="unavailable", holdings=[], report_period=None, report_date=None, published_at=None)
    unavailable = disclosure_for_holding("000001", "甲基金", _catalog(
        tmp_path, [row], today=date(2026, 10, 13)))
    assert unavailable["status"] == "unavailable"
    assert unavailable["source_recheck_required"] is True
    assert "本次尚未检查更近披露" in " ".join(unavailable["limitations"])


def test_portfolio_context_keeps_selected_disclosure_only(monkeypatch):
    from lei_signal.api import portfolio_workspace

    rows = [
        {"holding_id": "A", "code": "000001", "name": "甲", "disclosure": {"fund_code": "000001", "status": "available"}},
        {"holding_id": "C", "code": "000002", "name": "乙", "disclosure": {"fund_code": "000002", "status": "missing"}},
    ]
    monkeypatch.setattr(portfolio_workspace, "build_workspace", lambda _request: {
        "items": rows, "generated_at": "2026-10-12T10:00:00+08:00",
        "review_date": "2026-10-12", "as_of": "2026-10-11", "coverage": {"total": 2},
    })
    request = Request({"type": "http", "app": FastAPI()})
    single = build_portfolio_context(request, "A")["portfolio"]
    assert [item["disclosure"]["fund_code"] for item in single["items"]] == ["000001"]
    assert "group_name和original_note不是行业证据" in single["note_cn"]
    assert [item["disclosure"]["fund_code"] for item in build_portfolio_context(request, None)["portfolio"]["items"]] == [
        "000001", "000002",
    ]
