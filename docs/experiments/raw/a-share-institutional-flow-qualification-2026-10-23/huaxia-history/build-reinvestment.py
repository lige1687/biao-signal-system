"""Bind each half-year dividend amount to source report rows and event dates."""

import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
SERIES = json.loads((HERE / "history-series.json").read_text())
CHECKS = json.loads((HERE / "cross-checks.json").read_text())
REPORTS = {r["key"]: r for r in SERIES["reports"]}
MONEY = re.compile(r"-?[\d,]+\.\d{2}")
EVENTS = {2019: ("2019-11-06", 32), 2020: ("2020-12-17", 33),
          2021: ("2021-12-17", 36), 2023: ("2023-01-12", 26),
          2025: ("2025-09-22", 37)}


def amounts(line):
    return [Decimal(x.replace(",", "")) for x in MONEY.findall(line)]


def pdf_source(key, page, line):
    r = REPORTS[key]
    return {"report": key, "pdf_page": page, "original_line": line,
            "official_pdf_path": r["pdf_path"], "official_pdf_sha256": r["pdf_sha256"],
            "announcement_date": r["announcement_date"]}


def annual_row_source(year, row):
    return pdf_source(f"{year}FY", 7, row) if row else None


halves = []
for year in range(2019, 2026):
    v = CHECKS["dividends"][str(year)]
    h1_report, fy_report = REPORTS[f"{year}H1"], REPORTS[f"{year}FY"]
    h1_reader, fy_reader = PdfReader(h1_report["pdf_path"]), PdfReader(fy_report["pdf_path"])
    annual_cash, annual_reinvest = Decimal(v["annual_cash_cny"]), Decimal(v["annual_reinvested_cny"])
    annual_total = Decimal(v["annual_total_cny"])
    if annual_cash + annual_reinvest != annual_total:
        raise ValueError(f"{year}: annual cash/reinvestment order or sum mismatch")
    # The annual accounting statement independently confirms the year's total.
    fy_distributed = []
    for page in range(16, min(34, len(fy_reader.pages))):
        for line in fy_reader.pages[page - 1].extract_text(extraction_mode="layout").splitlines():
            if "本期已分配利润" in line:
                fy_distributed.append((page, line.strip(), amounts(line)))
    if len(fy_distributed) != 1:
        raise ValueError(f"{year}: annual current distribution row ambiguous")
    fy_statement_page, fy_statement_line, fy_values = fy_distributed[0]
    if (-fy_values[0] if fy_values else Decimal(0)) != annual_total:
        raise ValueError(f"{year}: annual income statement vs annual dividend row mismatch")
    h1_distributed = Decimal(v["h1_total_cny"])
    if annual_total:
        event_date, event_page = EVENTS[year]
        event_report = f"{year}H1" if year == 2023 else f"{year}FY"
        if (year == 2023) != (event_date <= f"{year}-06-30"):
            raise ValueError("event half-year assignment mismatch")
        event_reader = h1_reader if year == 2023 else fy_reader
        event_text = event_reader.pages[event_page - 1].extract_text(extraction_mode="layout")
        if not all(str(x) in event_text.replace(",", "") for x in (annual_cash, annual_reinvest, annual_total)):
            raise ValueError(f"{year}: cash/reinvestment not shown in event-detail row")
        # The 2025 and 2023 reports wrap the printed date across lines; store
        # the whole event section excerpt rather than a manufactured single row.
        event_lines = event_text.splitlines()
        cash_line = next(i for i, line in enumerate(event_lines) if str(annual_cash) in line.replace(",", ""))
        event_excerpt = " | ".join(s.strip() for s in event_lines[max(0, cash_line - 1):cash_line + 2])
        if year not in (2023, 2025) and event_date not in event_excerpt:
            raise ValueError(f"{year}: date not on event row")
        if year in (2023, 2025) and event_date.split("-")[0] not in event_text:
            raise ValueError(f"{year}: wrapped event date not in report section")
        event_source = pdf_source(event_report, event_page, event_excerpt)
    else:
        event_date, event_source = None, None

    # H1's own section 6.4.11 provides direct absence or the 2023 event.
    h1_sections = []
    for page in range(20, min(31, len(h1_reader.pages))):
        text = h1_reader.pages[page - 1].extract_text(extraction_mode="layout")
        match = re.search(r"6\.4\.11\s*利润分配情况", text)
        if match:
            h1_sections.append((page, text[match.start():].split("6.4.12", 1)[0]))
    if len(h1_sections) != 1:
        raise ValueError(f"{year}H1: section 6.4.11 missing/ambiguous")
    h1_section_page, h1_section = h1_sections[0]
    if year == 2023:
        if event_date not in h1_section or str(annual_reinvest) not in h1_section.replace(",", ""):
            raise ValueError("2023 H1 event detail missing")
        h1_cash, h1_reinvest = annual_cash, annual_reinvest
        h1_line = next(line.strip() for line in h1_section.splitlines() if str(annual_reinvest) in line.replace(",", ""))
    else:
        if "本基金本报告期无利润分配事项。" not in h1_section:
            raise ValueError(f"{year}H1: no-distribution statement missing")
        h1_cash = h1_reinvest = Decimal(0)
        h1_line = "本基金本报告期无利润分配事项。"
    if h1_cash + h1_reinvest != h1_distributed:
        raise ValueError(f"{year}H1: event amount != current statement distribution")
    halves.append({"period": f"{year}H1", "cash_dividend_cny": str(h1_cash),
                   "dividend_reinvestment_cny": str(h1_reinvest),
                   "event_date": event_date if year == 2023 else None,
                   "usable_from_official_announcement_date": h1_report["announcement_date"],
                   "period_source": pdf_source(f"{year}H1", h1_section_page, h1_line),
                   "later_annual_crosscheck_source": annual_row_source(year, v["annual_current_year_row"]),
                   "event_detail_source": event_source if year == 2023 else None,
                   "current_distribution_statement_source": pdf_source(f"{year}H1",
                         v["h1_statement_pdf_page"], v["h1_statement_row"])})

    h2_cash, h2_reinvest = annual_cash - h1_cash, annual_reinvest - h1_reinvest
    if h2_cash < 0 or h2_reinvest < 0:
        raise ValueError(f"{year}: H2 dividend component negative")
    if h2_cash + h2_reinvest != annual_total - h1_distributed:
        raise ValueError(f"{year}: H2 dividend total mismatch")
    if h2_cash or h2_reinvest:
        if event_date <= f"{year}-06-30":
            raise ValueError(f"{year}: H2 event date is not in H2")
        h2_basis = "year-end report §7.4.11 event row; FY minus H1"
        h2_source = event_source
    else:
        if year == 2023:
            h2_basis = "year-end §7.4.11 repeats sole Jan event already counted in H1; FY minus H1 = 0"
            fy_event_lines = fy_reader.pages[36].extract_text(extraction_mode="layout").splitlines()
            fy_cash_line = next(i for i, line in enumerate(fy_event_lines) if str(annual_cash) in line.replace(",", ""))
            h2_source = pdf_source(f"{year}FY", 37,
                                   " | ".join(s.strip() for s in fy_event_lines[max(0, fy_cash_line - 1):fy_cash_line + 2]))
        else:
            h2_basis = "FY statement current distribution zero; FY minus H1 = 0"
            h2_source = pdf_source(f"{year}FY", fy_statement_page, fy_statement_line)
    h2_row = {"period": f"{year}H2", "cash_dividend_cny": str(h2_cash),
                   "dividend_reinvestment_cny": str(h2_reinvest),
                   "event_date": event_date if h2_cash or h2_reinvest else None,
                   "usable_from_official_announcement_date": fy_report["announcement_date"],
                   "derivation": h2_basis, "period_source": h2_source,
                   "annual_current_year_row_source": annual_row_source(year, v["annual_current_year_row"]),
                   "event_detail_source": event_source if h2_cash or h2_reinvest else None,
                   "annual_current_distribution_statement_source": pdf_source(f"{year}FY",
                         fy_statement_page, fy_statement_line),
                   "h1_current_distribution_statement_source": pdf_source(f"{year}H1",
                         v["h1_statement_pdf_page"], v["h1_statement_row"])}
    if year == 2022:
        future_text = fy_reader.pages[39].extract_text(extraction_mode="layout")
        future_line = next(line.strip() for line in future_text.splitlines() if "2023年  1月  10日发布的分红公告" in line)
        h2_row["future_dividend_note_source"] = pdf_source("2022FY", 40, future_line)
        h2_row["future_dividend_note_meaning"] = "2022 annual report mentions a Jan 2023 dividend; not a 2022 distribution"
    halves.append(h2_row)

if len(halves) != 14:
    raise ValueError("not all 14 halves covered")

policy_report = REPORTS["2025FY"]
policy_text = PdfReader(policy_report["pdf_path"]).pages[23].extract_text(extraction_mode="layout")
policy_line = next(line.strip() for line in policy_text.splitlines() if "分红资金按分红实施日" in line)
identity_spot_checks = []
for key, pages, profit, distribution in (
    ("2023H1", (14,), Decimal("-198676862.93"), Decimal("5647586.32")),
    ("2025FY", (18, 19), Decimal("797077126.16"), Decimal("28059428.12")),
):
    r = REPORTS[key]
    text = "\n".join(PdfReader(r["pdf_path"]).pages[p - 1].extract_text(extraction_mode="layout") for p in pages)
    opening = Decimal(r["financial"]["net_assets_open_cny"])
    closing = Decimal(r["financial"]["net_assets_close_cny"])
    sub = Decimal(r["financial"]["subscription_transaction_cny"])
    red = Decimal(r["financial"]["redemption_transaction_cny_signed"])
    if opening + profit + sub + red - distribution != closing:
        raise ValueError(f"{key}: NAV accounting identity fails")
    if f"-{distribution:,.2f}" not in text or f"{profit:,.2f}" not in text:
        raise ValueError(f"{key}: reported profit or distribution figure missing")
    v = CHECKS["dividends"][str(r["year"])]
    if distribution != Decimal(v["annual_total_cny"]):
        raise ValueError(f"{key}: distributed NAV amount not cash + reinvestment")
    distribution_line = next(line.strip() for line in text.splitlines() if f"-{distribution:,.2f}" in line)
    profit_line = next(line.strip() for line in text.splitlines() if f"{profit:,.2f}" in line)
    identity_spot_checks.append({"report": key, "pdf_pages": list(pages),
                                 "opening_nav_cny": str(opening), "profit_cny": str(profit),
                                 "subscription_transaction_cny": str(sub),
                                 "redemption_transaction_cny_signed": str(red),
                                 "distribution_nav_reduction_cny_signed": str(-distribution),
                                 "closing_nav_cny": str(closing),
                                 "reconciliation": "opening + profit + subscription + signed redemption - (cash dividend + reinvestment) = closing",
                                 "distribution_equals_cash_plus_reinvestment": True,
                                 "profit_original_line": profit_line,
                                 "distribution_original_line": distribution_line,
                                 "source": pdf_source(key, pages[-1], distribution_line)})
result = {
    "fund_code": "000001", "unit": "人民币元", "halves": halves,
    "annual_table_columns_in_printed_order": ["年度", "每10份基金份额分红数", "现金形式发放总额",
                                               "再投资形式发放总额", "年度利润分配合计", "备注"],
    "annual_table_pdf_page": 7,
    "accounting_identity_spot_checks": identity_spot_checks,
    "subscription_includes_reinvestment_audit": {
        "direct_literal_note_found": False,
        "status": "supported accounting-structure inference, not an explicit report footnote",
        "policy_source": pdf_source("2025FY", 24, policy_line),
        "policy_meaning": "reinvested dividends convert into additional fund units at the implementation-date NAV",
        "caution": "The PDFs do not separately reconcile reinvestment-generated units with the subscription column or state verbatim that the NAV-change subscription amount includes reinvestment. Treat external-subscription adjustment as conditional pending independent confirmation."
    },
    "scope": "original PDF source qualification; no stock prices, returns, IC, or effect estimate"
}
(HERE / "reinvestment-by-half.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"half_years": len(halves), "nonzero": [h["period"] for h in halves if Decimal(h["dividend_reinvestment_cny"]) > 0]}, ensure_ascii=False))
