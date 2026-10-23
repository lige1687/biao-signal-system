"""Audit report units, year bridges, statement columns, splits, and dividends."""

import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "history-series.json").read_text())
OLD = json.loads((HERE.parent / "huaxia" / "fields.json").read_text())
NEW = {x["key"]: x["data"] for x in json.loads((HERE / "parse-status.json").read_text())}
REPORTS = {x["key"]: x for x in DATA["reports"]}
MONEY = re.compile(r"-?[\d,]+\.\d{2}")


def nums(line):
    return [Decimal(s.replace(",", "")) for s in MONEY.findall(line)]


report_checks = []
dividends = {}
for key, row in REPORTS.items():
    year = row["year"]
    kind = row["kind"]
    source = OLD[key] if year == 2024 else NEW[key]
    reader = PdfReader(row["pdf_path"])
    flow_page = source["flow_page"]
    flow_text = "\n".join(reader.pages[p - 1].extract_text(extraction_mode="layout") for p in (flow_page - 1, flow_page, flow_page + 1) if 0 < p <= len(reader.pages))
    split_lines = [line.strip() for line in flow_text.splitlines() if "本报告期基金拆分变动份额" in line]
    if len(split_lines) != 1 or not re.search(r"份额\s+-\s*$", split_lines[0]):
        raise ValueError(f"{key}: split row not uniquely shown as dash: {split_lines}")
    if "单位：份" not in flow_text:
        raise ValueError(f"{key}: fund-unit table not labelled shares")
    page = row["financial"]["transaction_pdf_pages"][0]
    statement_text = "\n".join(reader.pages[p - 1].extract_text(extraction_mode="layout") for p in range(max(1, page - 2), page + 1))
    if "单位：人民币元" not in statement_text:
        raise ValueError(f"{key}: financial statement currency unit not shown")
    sub_line, red_line = row["financial"]["transaction_source_lines"]
    sub, red = nums(sub_line), nums(red_line)
    if sub[0] != Decimal(row["flow"]["subscriptions"]) or red[0] != -Decimal(row["flow"]["redemptions"]):
        raise ValueError(f"{key}: current-period amount column selection not verified")
    if sub[-1] != Decimal(row["financial"]["subscription_transaction_cny"]) or red[-1] != Decimal(row["financial"]["redemption_transaction_cny_signed"]):
        raise ValueError(f"{key}: current-period CNY transaction amount mismatch")
    # The first financial-statement table is the current period; following
    # tables contain comparative prior-period figures and must not be selected.
    balance_page = row["financial"]["net_assets_balance_pdf_page"]
    balance_text = "\n".join(reader.pages[p - 1].extract_text(extraction_mode="layout") for p in range(max(1, balance_page - 1), balance_page + 1))
    if "单位：人民币元" not in balance_text:
        raise ValueError(f"{key}: balance-sheet currency unit not shown")
    report_checks.append({"key": key, "flow_pdf_page": flow_page, "split_row": split_lines[0],
                          "flow_unit": "份", "financial_unit": "人民币元",
                          "current_period_statement_column_verified_by_flow_units": True,
                          "balance_sheet_pdf_page": balance_page})
    # Annual section 3.3 has a year-specific line and separately reports
    # cash and dividend reinvestment. Its '合计' includes other years.
    if kind == "FY":
        text = reader.pages[6].extract_text(extraction_mode="layout")
        section = text.split("3.3 过去三年基金的利润分配情况", 1)[1].split("§4", 1)[0]
        matches = [line.strip() for line in section.splitlines() if re.match(rf"^\s*{year}年\s+", line)]
        if len(matches) > 1:
            raise ValueError(f"{key}: multiple current-year dividend rows")
        if matches:
            values = nums(matches[0])
            if len(values) != 4 or values[1] + values[2] != values[3]:
                raise ValueError(f"{key}: dividend cash/reinvestment sum mismatch")
            cash, reinvested, total = values[1:]
        else:
            cash = reinvested = total = Decimal(0)
        dividends[str(year)] = {"annual_cash_cny": str(cash), "annual_reinvested_cny": str(reinvested),
                                "annual_total_cny": str(total), "annual_section_pdf_page": 7,
                                "annual_current_year_row": matches[0] if matches else None}


bridges = []
for year in range(2019, 2026):
    h1, fy = REPORTS[f"{year}H1"], REPORTS[f"{year}FY"]
    if h1["flow"]["opening"] != fy["flow"]["opening"]:
        raise ValueError(f"{year}: annual/H1 unit opening mismatch")
    if h1["financial"]["net_assets_open_cny"] != fy["financial"]["net_assets_open_cny"]:
        raise ValueError(f"{year}: annual/H1 NAV opening mismatch")
    bridge = {"year": year, "same_year_h1_fy_opening_units_equal": True,
              "same_year_h1_fy_opening_nav_cny_equal": True,
              "opening_units": h1["flow"]["opening"], "opening_nav_cny": h1["financial"]["net_assets_open_cny"]}
    if year > 2019:
        prior = REPORTS[f"{year-1}FY"]
        if prior["flow"]["closing"] != h1["flow"]["opening"]:
            raise ValueError(f"{year}: prior FY close units != H1 opening")
        if prior["financial"]["net_assets_close_cny"] != h1["financial"]["net_assets_open_cny"]:
            raise ValueError(f"{year}: prior FY close NAV != H1 opening")
        bridge.update({"prior_fy_close_to_h1_open_units_equal": True,
                       "prior_fy_close_to_h1_open_nav_cny_equal": True})
    bridges.append(bridge)

# The 2023 dividend was already present in the interim report; other interim
# statements state no current-period distribution and annual amounts are H2.
for year in range(2019, 2026):
    row = REPORTS[f"{year}H1"]
    reader = PdfReader(row["pdf_path"])
    reported = []
    for page_no in range(15, min(31, len(reader.pages))):
        for line in reader.pages[page_no - 1].extract_text(extraction_mode="layout").splitlines():
            if "本期已分配利润" in line:
                reported.append((page_no, line.strip(), nums(line)))
    if len(reported) != 1:
        raise ValueError(f"{year}H1: current distribution statement missing/ambiguous")
    page_no, line, values = reported[0]
    h1_amount = -values[0] if values else Decimal(0)
    annual_amount = Decimal(dividends[str(year)]["annual_total_cny"])
    if h1_amount < 0 or h1_amount > annual_amount:
        raise ValueError(f"{year}: H1 distribution exceeds full-year amount")
    dividends[str(year)].update({"h1_total_cny": str(h1_amount), "h2_total_cny": str(annual_amount - h1_amount),
                                 "h1_statement_pdf_page": page_no, "h1_statement_row": line})

result = {"fund_code": "000001", "reports_checked": len(report_checks),
          "cross_year_bridges_checked": len(bridges) - 1,
          "report_checks": report_checks, "bridges": bridges, "dividends": dividends,
          "limits": "Dividend reinvestment is reported in CNY, not a separately reconciled unit count; subscriptions contain conversion and may include dividend-reinvestment units. Financial statement CNY is fund-unit transaction effect on NAV, not verified external cash."}
(HERE / "cross-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"reports_checked": len(report_checks), "cross_year_bridges": len(bridges)-1,
                  "dividend_years": [y for y, v in dividends.items() if Decimal(v["annual_total_cny"]) > 0]}, ensure_ascii=False))
