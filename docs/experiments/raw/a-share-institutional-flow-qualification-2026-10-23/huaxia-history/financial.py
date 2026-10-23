"""Extract current-period financial-statement figures and build half-year series."""

import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from collect import HERE, OUT, RAW


AMOUNT = re.compile(r"-?[\d,]+\.\d{2}")


def amounts(line):
    return [Decimal(m.replace(",", "")) for m in AMOUNT.findall(line)]


def financial_fields(pdf_path, flow, holdings_first_page):
    reader = PdfReader(str(pdf_path))
    transactions = []
    balance = []
    for i in range(9, min(24, len(reader.pages))):
        for line in reader.pages[i].extract_text(extraction_mode="layout").splitlines():
            nums = amounts(line)
            if len(nums) >= 2 and ("净资产合计" in line or "所有者权益合计" in line):
                balance.append((i + 1, line.strip(), nums))
            if len(nums) >= 2 and ("1.基金申" in line or "2.基金赎" in line):
                transactions.append((i + 1, line.strip(), nums))
    if not balance:
        raise ValueError("balance-sheet net assets missing")
    if len(transactions) < 2:
        raise ValueError("financial subscriptions/redemptions missing")
    sub_page, sub_line, sub_numbers = transactions[0]
    red_page, red_line, red_numbers = transactions[1]
    if "1.基金申" not in sub_line or "2.基金赎" not in red_line:
        raise ValueError("first financial transaction lines are not subscription and redemption")
    if sub_numbers[0] != Decimal(flow["subscriptions"]) or red_numbers[0] != -Decimal(flow["redemptions"]):
        raise ValueError("financial statement unit column disagrees with fund-unit table")
    balance_page, _, balance_numbers = balance[0]
    result = {
        "net_assets_open_cny": str(balance_numbers[1]),
        "net_assets_close_cny": str(balance_numbers[0]),
        "net_assets_balance_pdf_page": balance_page,
        "subscription_transaction_cny": str(sub_numbers[-1]),
        "redemption_transaction_cny_signed": str(red_numbers[-1]),
        "net_transaction_cny": str(sub_numbers[-1] + red_numbers[-1]),
        "transaction_pdf_pages": sorted({sub_page, red_page}),
        "transaction_source_lines": [sub_line, red_line],
        "financial_unit": "CNY",
    }
    liquidity_rows = []
    for page_number in range(max(1, holdings_first_page - 4), holdings_first_page + 1):
        for line in reader.pages[page_number - 1].extract_text(extraction_mode="layout").splitlines():
            if "银行存款和结算备付金" in line and amounts(line):
                liquidity_rows.append((page_number, amounts(line)[0]))
    if len(liquidity_rows) != 1:
        raise ValueError("expected one portfolio bank-deposit and settlement-reserve row")
    liquidity_page, liquidity_amount = liquidity_rows[0]
    result.update({"bank_deposits_and_settlement_reserve_cny": str(liquidity_amount),
                   "liquidity_asset_pdf_page": liquidity_page,
                   "liquidity_label": "银行存款和结算备付金合计; not pure cash"})
    return result


def report(year, kind, status, reused):
    key = f"{year}{kind}"
    if year == 2024:
        d = reused[kind]
        flow = d["flow"]
        pdf = Path(d["official_pdf_path"])
        core = {
            "key": key, "year": year, "kind": kind, "period_end": d["period_end"],
            "announcement_date": d["announcement_date"],
            "stock_assets_cny": d["stock_assets_cny"],
            "holdings_rows": d["holdings_rows"], "holdings_csv": d["holdings_csv"],
            "pdf_sha256": d["official_pdf_sha256"], "pdf_path": str(pdf),
            "flow": flow, "trading_codes_line": "000001 front / 000002 back; same fund",
            "source_state": "qualified in prior huaxia source pack; reused without download or reparse",
        }
    else:
        d = status[key]
        flow = d["flow"]
        pdf = Path(d["pdf_path"])
        core = {
            "key": key, "year": year, "kind": kind, "period_end": d["period_end"],
            "announcement_date": d["announcement_date"],
            "stock_assets_cny": d["stock_assets_cny"],
            "holdings_rows": d["holdings_rows"], "holdings_csv": d["holdings_csv"],
            "pdf_sha256": d["pdf_sha256"], "pdf_path": str(pdf),
            "flow": flow, "trading_codes_line": d["trading_codes_line"],
            "source_state": "qualified from new official original",
        }
    core["financial"] = financial_fields(pdf, flow, d["holdings_pages"][0])
    return core


def half_period(year, kind, h1, fy):
    if kind == "H1":
        opening = Decimal(h1["flow"]["opening"])
        subscriptions = Decimal(h1["flow"]["subscriptions"])
        redemptions = Decimal(h1["flow"]["redemptions"])
        closing = Decimal(h1["flow"]["closing"])
        sub_cny = Decimal(h1["financial"]["subscription_transaction_cny"])
        red_cny = Decimal(h1["financial"]["redemption_transaction_cny_signed"])
        begin_date, end_date = f"{year}-01-01", f"{year}-06-30"
        announced = h1["announcement_date"]
    else:
        opening = Decimal(h1["flow"]["closing"])
        subscriptions = Decimal(fy["flow"]["subscriptions"]) - Decimal(h1["flow"]["subscriptions"])
        redemptions = Decimal(fy["flow"]["redemptions"]) - Decimal(h1["flow"]["redemptions"])
        closing = Decimal(fy["flow"]["closing"])
        sub_cny = Decimal(fy["financial"]["subscription_transaction_cny"]) - Decimal(h1["financial"]["subscription_transaction_cny"])
        red_cny = Decimal(fy["financial"]["redemption_transaction_cny_signed"]) - Decimal(h1["financial"]["redemption_transaction_cny_signed"])
        begin_date, end_date = f"{year}-07-01", f"{year}-12-31"
        announced = fy["announcement_date"]
    if opening + subscriptions - redemptions != closing:
        raise ValueError(f"{year}{kind} half-year unit bridge fails")
    net_units = subscriptions - redemptions
    return {
        "year": year, "kind": kind, "period_start": begin_date, "period_end": end_date,
        "first_known_by_official_date": announced,
        "opening_units": str(opening), "subscriptions_units": str(subscriptions),
        "redemptions_units": str(redemptions), "closing_units": str(closing),
        "net_units": str(net_units),
        "net_units_pct_opening": str((net_units / opening * 100).quantize(Decimal("0.01"))),
        "subscription_transaction_cny": str(sub_cny),
        "redemption_transaction_cny_signed": str(red_cny),
        "net_transaction_cny": str(sub_cny + red_cny),
        "transaction_definition": "reported fund-unit transaction effect on net assets, not verified external cash",
    }


def main():
    attempts = json.loads((HERE / "parse-status.json").read_text())
    if len(attempts) != 12 or any(x["status"] != "qualified" for x in attempts):
        raise ValueError("twelve historical reports not all qualified")
    status = {x["key"]: x["data"] for x in attempts}
    reused = json.loads((RAW / "huaxia" / "fields.json").read_text())
    reused = {"H1": reused["2024H1"], "FY": reused["2024FY"]}
    reports = []
    half_years = []
    for year in range(2019, 2026):
        h1 = report(year, "H1", status, reused)
        fy = report(year, "FY", status, reused)
        if h1["flow"]["opening"] != fy["flow"]["opening"]:
            raise ValueError(f"{year} annual/H1 openings disagree")
        reports.extend((h1, fy))
        half_years.extend((half_period(year, "H1", h1, fy), half_period(year, "H2", h1, fy)))
    for earlier, later in zip(half_years, half_years[1:]):
        if earlier["closing_units"] != later["opening_units"]:
            raise ValueError("adjacent half-year unit totals disagree")
    data = {"fund_code": "000001", "fund_name": "华夏成长证券投资基金",
            "reports": reports, "half_years": half_years,
            "scope": "14 complete semiannual/annual reports; 14 half-year gross unit flows; source qualification only; no returns"}
    (HERE / "history-series.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report_count": len(reports), "half_year_count": len(half_years),
                      "negative_net_unit_half_years": sum(Decimal(x["net_units"]) < 0 for x in half_years),
                      "first": half_years[0], "last": half_years[-1]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
