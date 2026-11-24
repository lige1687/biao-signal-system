"""Source-bound industry references; never evaluate a fund's trade conditions."""
from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "configs" / "fund-industry-references.v1.json"


def valid_day(value, today: date) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value and date.fromisoformat(value) <= today
    except ValueError:
        return False


def build_industry_reference(code, name, disclosure, *, today: date, catalog=None, snapshots=None):
    """Match explicit company identity + business. No name-only or code-prefix inference."""
    output = {"status": "unavailable", "report_date": disclosure.get("report_date"),
              "references": [], "fundamentals": [], "note_cn":
              "行业ETF帮助观察相关业务的市场变化；基金自身退出条件须单独核对。披露后的调仓与未覆盖资产仍未知。"}
    if (disclosure.get("status") != "available" or not code or disclosure.get("fund_code") != code
            or not valid_day(disclosure.get("report_date"), today)):
        return output
    if catalog is None:
        try:
            catalog = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return output
    if not valid_day(catalog.get("checked_on"), today):
        return output
    output["reference_checked_on"] = catalog["checked_on"]
    grouped = {}
    for stock in disclosure.get("holdings", []):
        binding = catalog.get("companies", {}).get(stock.get("stock_code"))
        weight = stock.get("weight_pct")
        if (not binding or stock.get("stock_name") != binding["name"]
                or stock.get("industry_label") != binding["industry_label"]
                or not str(stock.get("industry_source_url", "")).startswith("https://")
                or not isinstance(weight, (float, int)) or isinstance(weight, bool)
                or not math.isfinite(weight) or not 0 < weight <= 100):
            continue
        for key in binding["references"]:
            reference = catalog["references"][key]
            if reference["market"] != binding["market"]:
                continue
            row = grouped.setdefault(key, {**reference, "companies": [], "technical": None})
            row["companies"].append({"name": stock["stock_name"], "weight_pct": weight,
                                     "business": stock["industry_label"],
                                     "source_url": stock["industry_source_url"],
                                     "identity_source_url": binding["source_url"]})
    for row in grouped.values():
        snapshot = (snapshots or {}).get(row["symbol"])
        if (snapshot and snapshot.get("symbol") == row["symbol"]
                and valid_day(snapshot.get("as_of"), today)):
            row["technical"] = dict(snapshot)
        output["references"].append(row)
    for fact in catalog.get("fundamentals", []):
        if (fact["fund_code"] == code and fact["fund_name"] == name
                and fact["report_date"] == disclosure["report_date"]
                and valid_day(fact["published_at"], today)):
            output["fundamentals"].append(dict(fact))
    output["status"] = "partial" if output["references"] or output["fundamentals"] else "unavailable"
    return output


def cached_industry_reference(request, code, name, disclosure, now: datetime):
    """Read existing in-memory analyses only; no market fetch, persistence or model call."""
    output = build_industry_reference(code, name, disclosure, today=now.date())
    service = getattr(request.app.state, "analysis_service", None)
    entries = getattr(service, "_entries", {})
    for row in output["references"]:
        entry = entries.get(row["symbol"])
        result = getattr(entry, "result", None)
        if result is None or result.symbol != row["symbol"] or getattr(entry, "error", None):
            continue
        fetched = getattr(entry, "fetched_at", None)
        if not fetched or fetched.tzinfo is None or fetched > now:
            continue
        try:
            from lei_signal.api.routes.symbols import _assessment_dto
            from lei_signal.api.card_mapper import is_intraday_forming
            from lei_signal.api.portfolio_workspace import _expected_bar_date
            assessment = _assessment_dto(result)
            if not valid_day(assessment.as_of, now.date()):
                continue
            output_row = {key: getattr(assessment, key) for key in
                          ("as_of", "stage_cn", "color_cn", "risk_state_cn")}
            row["technical"] = {**output_row, "symbol": row["symbol"],
                                "fetched_at": fetched.isoformat(),
                                "stale": assessment.as_of != _expected_bar_date(row["symbol"], now),
                                "is_intraday_forming": is_intraday_forming(result, fetched_at=fetched, now=now),
                                "cache_fallback_used": bool(result.cache_fallback_used)}
        except (AttributeError, TypeError, ValueError):
            continue
    return output
