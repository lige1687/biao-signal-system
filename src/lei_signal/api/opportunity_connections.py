"""Source-bound links from recent ETF observations to disclosed fund businesses."""

from __future__ import annotations

from datetime import date, datetime

from lei_signal.portfolio.industry_context import build_industry_reference, valid_day


def _checked_day(value: object, as_of: date) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        day = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
    return day.isoformat() if day <= as_of else None


def _https(value: object) -> bool:
    return isinstance(value, str) and value.startswith("https://") and len(value) > 8


def build_opportunity_connections(
    recent: dict, workspace_items: list[dict], *, as_of: date
) -> dict[str, list[dict]]:
    """Match exact recent symbols to qualified, same-market business references.

    The relation describes a past disclosed stock business. It never asserts ETF
    ownership, current fund allocation, or a fund trading condition.
    """
    symbols = {
        row.get("symbol")
        for field in ("items", "waiting", "cleared")
        for row in recent.get(field, []) or []
        if isinstance(row, dict) and isinstance(row.get("symbol"), str)
    }
    result: dict[str, list[dict]] = {symbol: [] for symbol in sorted(symbols)}
    for item in workspace_items:
        if not isinstance(item, dict):
            continue
        holding_id, code, name = item.get("holding_id"), item.get("code"), item.get("name")
        disclosure = item.get("disclosure") or {}
        reference = item.get("industry_reference") or {}
        if not all(isinstance(x, str) and x for x in (holding_id, code, name)):
            continue
        if (disclosure.get("status") != "available"
                or disclosure.get("fund_code") != code
                or disclosure.get("fund_name") != name
                or not valid_day(disclosure.get("report_date"), as_of)):
            continue
        report = disclosure["report_date"]
        published = disclosure.get("published_at")
        checked = _checked_day(disclosure.get("checked_at"), as_of)
        reference_checked = reference.get("reference_checked_on")
        if (not checked or checked < report
                or published is not None and (
                    not valid_day(published, as_of) or published < report or published > checked
                )
                or not valid_day(reference_checked, as_of)):
            continue
        report_url = disclosure.get("official_report_url") or disclosure.get("source_url")
        if not _https(report_url):
            continue
        # Reuse the existing identity, business, weight, and same-market gate.
        qualified = build_industry_reference(code, name, disclosure, today=as_of)
        if qualified.get("reference_checked_on") != reference_checked:
            continue
        supplied = {row.get("symbol") for row in reference.get("references") or []
                    if isinstance(row, dict)}
        for row in qualified["references"]:
            symbol = row.get("symbol")
            if symbol not in symbols or symbol not in supplied or not _https(row.get("source_url")):
                continue
            companies = [
                {"name": company["name"], "business": company["business"],
                 "source_url": company["source_url"]}
                for company in row["companies"]
                if _https(company.get("source_url"))
                and _https(company.get("identity_source_url"))
            ]
            if not companies:
                continue
            sources = sorted({
                report_url, row["source_url"],
                *(company["source_url"] for company in row["companies"]
                  if _https(company.get("source_url"))
                  and _https(company.get("identity_source_url"))),
                *(company["identity_source_url"] for company in row["companies"]
                  if _https(company.get("source_url"))
                  and _https(company.get("identity_source_url"))),
            })
            result[symbol].append({
                "holding_id": holding_id,
                "subject_key": f"holding:{holding_id}",
                "fund_name": name,
                "fund_code": code,
                "account_as_of": (item.get("holding_as_of")
                                  if valid_day(item.get("holding_as_of"), as_of) else None),
                "reference_symbol": symbol,
                "reference_name": row["name"],
                "market": row["market"],
                "relation_type": "disclosed_business_reference",
                "report_date": report,
                "published_at": published,
                "checked_at": checked,
                "reference_checked_on": reference_checked,
                "companies": companies,
                "source_refs": sources,
                "limitation": (
                    f"仅根据截至{report}的基金直接股票披露关联业务；"
                    "不代表基金持有该ETF、当前配置或基金自身买卖条件。"
                    "未披露资产及披露后调仓未知。"
                ),
            })
    for relations in result.values():
        relations.sort(key=lambda row: (row["fund_code"], row["holding_id"]))
    return result
