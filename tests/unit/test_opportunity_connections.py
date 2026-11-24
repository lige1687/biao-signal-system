"""Recent ETF observations may reference disclosed businesses, not ETF ownership."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date

from lei_signal.api.opportunity_connections import build_opportunity_connections
from lei_signal.portfolio import industry_context
from lei_signal.portfolio.disclosure_context import disclosure_for_holding, load_disclosures
from lei_signal.portfolio.industry_context import build_industry_reference

TODAY = date(2026, 10, 19)


def _workspace() -> dict:
    code, name = "001513", "易方达信息产业混合A"
    disclosure = disclosure_for_holding(code, name, load_disclosures(today=TODAY))
    return {
        "holding_id": "local-holding", "code": code, "name": name,
        "holding_as_of": "2026-09-04", "disclosure": disclosure,
        "industry_reference": build_industry_reference(code, name, disclosure, today=TODAY),
        "market_value": 999999,
    }


def _recent(*symbols: str) -> dict:
    return {"items": [{"symbol": symbol} for symbol in symbols], "waiting": [], "cleared": []}


def test_exact_disclosed_business_reference_has_sources_and_no_private_amount():
    links = build_opportunity_connections(
        _recent("515880.SS", "512480.SS", "SOXX"), [_workspace()], as_of=TODAY
    )
    assert len(links["515880.SS"]) == len(links["512480.SS"]) == 1
    assert links["SOXX"] == []
    communication = links["515880.SS"][0]
    assert communication["relation_type"] == "disclosed_business_reference"
    assert communication["fund_code"] == "001513"
    assert communication["report_date"] == "2026-06-30"
    assert communication["published_at"] == "2026-08-31"
    assert communication["reference_checked_on"] == "2026-10-14"
    assert communication["account_as_of"] == "2026-09-04"
    assert any(row["name"] == "新易盛" for row in communication["companies"])
    assert all(url.startswith("https://") for url in communication["source_refs"])
    assert "不代表基金持有该ETF" in communication["limitation"]
    assert "market_value" not in str(links)
    assert "999999" not in str(links)


def test_unqualified_or_future_source_cannot_create_relation():
    for change in (
        lambda item: item["disclosure"].update(report_date="2026-12-31"),
        lambda item: item["disclosure"].update(checked_at="2026-12-31"),
        lambda item: item["disclosure"]["holdings"][0].update(industry_source_url="http://example.test"),
        lambda item: item["industry_reference"].update(reference_checked_on="2026-12-31"),
        lambda item: item["industry_reference"].update(references=[]),
    ):
        item = deepcopy(_workspace())
        change(item)
        links = build_opportunity_connections(_recent("515880.SS"), [item], as_of=TODAY)
        assert links["515880.SS"] == [] or all(
            row["companies"][0]["name"] != "新易盛" for row in links["515880.SS"]
        )


def test_missing_target_binding_and_name_only_match_stay_unlinked():
    item = _workspace()
    assert build_opportunity_connections(_recent("159652.SZ"), [item], as_of=TODAY) == {
        "159652.SZ": []
    }
    item["name"] = "同名但不同代码的基金"
    assert build_opportunity_connections(_recent("515880.SS"), [item], as_of=TODAY) == {
        "515880.SS": []
    }


def test_cross_market_company_binding_cannot_link_etf(monkeypatch, tmp_path):
    item = _workspace()
    catalog = json.loads(industry_context.DEFAULT_PATH.read_text(encoding="utf-8"))
    for company in catalog["companies"].values():
        if "communication_cn" in company["references"]:
            company["market"] = "美股"
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(industry_context, "DEFAULT_PATH", path)
    assert build_opportunity_connections(_recent("515880.SS"), [item], as_of=TODAY) == {
        "515880.SS": []
    }
