"""Extract report-wide stock turnover and balance-sheet liquidity fields.

Only reads SHA-bound official PDFs from the prior source-qualification pack.
It does not calculate any relation between trades and fund subscriptions.
"""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / "a-share-institutional-flow-qualification-2026-10-23" / "huaxia-history"
MANIFEST = json.loads((OLD / "manifest.json").read_text())
SERIES = {x["key"]: x for x in json.loads((OLD / "history-series.json").read_text())["reports"]}
AMOUNT = re.compile(r"(?<![\d.])-?\d[\d,]*\.\d{2}(?!\d)")


def amounts(line):
    return [Decimal(m.group().replace(",", "")) for m in AMOUNT.finditer(line)]


def one_row(pages, matches, field):
    found = []
    for page in pages:
        for line in page["text"].splitlines():
            if matches(line):
                vals = amounts(line)
                if vals:
                    found.append((page["number"], line.strip(), vals))
    if len(found) != 1:
        raise ValueError(f"{field}: expected one source row, got {len(found)}: {found[:3]}")
    return found[0]


def parse(record):
    key = record["key"]
    base = SERIES[key]
    pdf = Path(record["pdf_path"])
    if not pdf.is_file():
        raise ValueError("official PDF missing")
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if sha != record["pdf_sha256"] or sha != base["pdf_sha256"]:
        raise ValueError("official PDF SHA-256 disagrees with frozen manifest")
    reader = PdfReader(str(pdf))
    balance_page = base["financial"]["net_assets_balance_pdf_page"]
    liquidity_page = base["financial"]["liquidity_asset_pdf_page"]
    source_pages = [{"number": i + 1, "text": p.extract_text(extraction_mode="layout")}
                    for i, p in enumerate(reader.pages)]

    # The stock total is in §7.4.3/§8.4.3, after the thresholded major
    # buy/sell lists. The 2025 sell row continues on the next PDF page.
    buy_page, buy_line, buys = one_row(
        source_pages, lambda s: "买入股票" in s and "成本" in s and "总额" in s and bool(amounts(s)), "stock buys")
    sell_page, sell_line, sells = one_row(
        source_pages, lambda s: "卖出股票" in s and "收入" in s and "总额" in s and bool(amounts(s)), "stock sells")
    if len(buys) != 1 or len(sells) != 1 or buys[0] <= 0 or sells[0] <= 0:
        raise ValueError("buy/sell gross trade amount ambiguous")
    section_text = "\n".join(p["text"] for p in source_pages[max(0, buy_page - 2):buy_page])
    if "买入股票的成本总额及卖出股票的收入总额" not in section_text:
        raise ValueError("trade amount not in total-cost/revenue section")
    note_page = None
    note_excerpt = None
    for p in source_pages[buy_page - 1:sell_page + 1]:
        lines = p["text"].splitlines()
        for i, line in enumerate(lines):
            if "不考虑相关交易费用" in line:
                note_page = p["number"]
                note_excerpt = line.strip()
            elif "不" in line and "买卖成交金额" in line:
                following = next((s for s in lines[i + 1:] if s.strip()), "")
                if "考虑相关交易费用" in following:
                    note_page = p["number"]
                    note_excerpt = line.strip() + " " + following.strip()
    if note_page is None:
        raise ValueError("trade fee-exclusion note missing")
    trade_unit_text = "\n".join(p["text"] for p in source_pages[buy_page - 1:sell_page])
    if "人民币元" not in trade_unit_text:
        raise ValueError("trade amount CNY unit missing")

    # Balance sheet starts on the page before the stored closing-NAV row.
    balance_pages = source_pages[max(0, balance_page - 3):balance_page]
    bank_page, bank_line, bank_vals = one_row(
        balance_pages, lambda s: ("银行存款" in s or "货币资金" in s) and bool(amounts(s)), "bank/money funds")
    settlement_page, settlement_line, settlement_vals = one_row(
        balance_pages, lambda s: "结算备付金" in s and bool(amounts(s)), "settlement reserve")
    if len(bank_vals) != 2 or len(settlement_vals) != 2:
        raise ValueError("balance sheet lacks current/prior CNY columns")
    if not any("单位：人民币元" in p["text"] for p in balance_pages):
        raise ValueError("balance sheet CNY unit missing")
    portfolio = source_pages[liquidity_page - 1]
    portfolio_line = next((line.strip() for line in portfolio["text"].splitlines()
                           if "银行存款和结算备付金" in line and amounts(line)), None)
    if portfolio_line is None:
        raise ValueError("portfolio bank+settlement row missing")
    portfolio_value = amounts(portfolio_line)[0]
    if bank_vals[0] + settlement_vals[0] != portfolio_value:
        raise ValueError("period-end bank + reserve != portfolio bank+reserve")
    if portfolio_value != Decimal(base["financial"]["bank_deposits_and_settlement_reserve_cny"]):
        raise ValueError("portfolio liquidity disagrees with prior qualification")

    return {
        "key": key, "period": key, "fund_code": "000001", "fund_name": "华夏成长证券投资基金",
        "report_type": "中期报告" if key.endswith("H1") else "年度报告",
        "period_start": f"{base['year']}-01-01", "period_end": record["period_end"],
        "announcement_date": record["announcement_date"],
        "official_pdf_url": record["official_pdf_url"], "pdf_path": str(pdf),
        "pdf_sha256": sha, "pdf_pages": len(reader.pages),
        "buy_total_cny": str(buys[0]),
        "stock_buy_gross_cny": str(buys[0]), "stock_buy_pdf_page": buy_page,
        "stock_buy_original_line": buy_line,
        "sell_total_cny": str(sells[0]),
        "stock_sell_gross_cny": str(sells[0]), "stock_sell_pdf_page": sell_page,
        "stock_sell_original_line": sell_line,
        "stock_trades_unit": "人民币元", "trade_fee_note_pdf_page": note_page,
        "trade_fee_original_excerpt": note_excerpt,
        "stock_trade_scope": "report-period gross stock turnover total, excluding trading fees; not only major-buy/sell rows",
        "balance_sheet_bank_label": "银行存款" if "银行存款" in bank_line else "货币资金",
        "bank_current_cny": str(bank_vals[0]),
        "bank_prior_year_end_cny": str(bank_vals[1]),
        "balance_sheet_bank_close_cny": str(bank_vals[0]),
        "balance_sheet_bank_prior_year_end_cny": str(bank_vals[1]),
        "balance_sheet_bank_pdf_page": bank_page, "balance_sheet_bank_original_line": bank_line,
        "settlement_current_cny": str(settlement_vals[0]),
        "settlement_prior_year_end_cny": str(settlement_vals[1]),
        "balance_sheet_settlement_close_cny": str(settlement_vals[0]),
        "balance_sheet_settlement_prior_year_end_cny": str(settlement_vals[1]),
        "balance_sheet_settlement_pdf_page": settlement_page,
        "balance_sheet_settlement_original_line": settlement_line,
        "combined_current_cny": str(portfolio_value),
        "portfolio_bank_plus_settlement_close_cny": str(portfolio_value),
        "portfolio_liquidity_pdf_page": liquidity_page,
        "portfolio_liquidity_original_line": portfolio_line,
        "net_assets_open_cny": base["financial"]["net_assets_open_cny"],
        "net_assets_close_cny": base["financial"]["net_assets_close_cny"],
        "net_assets_balance_pdf_page": balance_page,
        "balance_sheet_unit": "人民币元",
        "comparison_column_scope": f"{base['year'] - 1}-12-31 prior year end, including H1 report",
    }


def main():
    successes, failures = [], []
    for record in MANIFEST["reports"]:
        try:
            successes.append(parse(record))
        except Exception as exc:
            failures.append({"key": record["key"], "error": str(exc)})
    bridges = []
    cross_year_bridges = []
    by_key = {r["key"]: r for r in successes}
    if not failures:
        for year in range(2019, 2026):
            h1, fy = by_key[f"{year}H1"], by_key[f"{year}FY"]
            for part in ("bank", "settlement"):
                field = f"balance_sheet_{part}_prior_year_end_cny"
                if h1[field] != fy[field]:
                    failures.append({"key": str(year), "error": f"H1/FY prior-year {part} columns disagree"})
            for kind in ("buy", "sell"):
                field = f"stock_{kind}_gross_cny"
                diff = Decimal(fy[field]) - Decimal(h1[field])
                if diff < 0:
                    failures.append({"key": str(year), "error": f"FY-H1 {kind} gross amount negative"})
            bridges.append({"year": year, "same_prior_year_end_bank": h1["balance_sheet_bank_prior_year_end_cny"] == fy["balance_sheet_bank_prior_year_end_cny"],
                            "same_prior_year_end_settlement": h1["balance_sheet_settlement_prior_year_end_cny"] == fy["balance_sheet_settlement_prior_year_end_cny"],
                            "fy_minus_h1_buy_nonnegative": Decimal(fy["stock_buy_gross_cny"]) >= Decimal(h1["stock_buy_gross_cny"]),
                            "fy_minus_h1_sell_nonnegative": Decimal(fy["stock_sell_gross_cny"]) >= Decimal(h1["stock_sell_gross_cny"])})
        for year in range(2020, 2026):
            prior, h1 = by_key[f"{year-1}FY"], by_key[f"{year}H1"]
            bridge = {"prior_fy": prior["key"], "next_h1": h1["key"]}
            for part in ("bank", "settlement"):
                prior_field = f"balance_sheet_{part}_close_cny"
                next_field = f"balance_sheet_{part}_prior_year_end_cny"
                bridge[f"{part}_prior_fy_close_cny"] = prior[prior_field]
                bridge[f"{part}_next_h1_prior_year_end_cny"] = h1[next_field]
                bridge[f"{part}_equal"] = prior[prior_field] == h1[next_field]
                if prior[prior_field] != h1[next_field]:
                    failures.append({"key": str(year), "error": f"prior FY close and next H1 opening {part} differ: {prior[prior_field]} vs {h1[next_field]}"})
            cross_year_bridges.append(bridge)
    result = {"scope": "source qualification only; no fund-flow/trading relationship or returns",
              "report_count_expected": 14, "report_count_qualified": len(successes),
              "status": "qualified" if len(successes) == 14 and not failures else "partial",
              "reports": successes, "bridges": bridges,
              "cross_year_bridges": cross_year_bridges, "failures": failures}
    (HERE / "reports.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"qualified": len(successes), "failures": failures}, ensure_ascii=False))


if __name__ == "__main__":
    main()
