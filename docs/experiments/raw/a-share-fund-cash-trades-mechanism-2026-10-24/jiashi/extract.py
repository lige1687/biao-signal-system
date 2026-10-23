"""Qualify disclosed stock-trade totals and cash/settlement balances in 070002 PDFs.

No prices, returns, redemption comparison, or external output are produced.
"""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).parent
OLD = ROOT.parents[1] / "a-share-institutional-flow-qualification-2026-10-23" / "jiashi-history" / "source-manifest.json"
MANIFEST = json.loads(OLD.read_text())
NUM = r"[\d,]+\.\d{2}"
D = Decimal


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def amount(text):
    return D(text.replace(",", ""))


def page_match(pages, pattern, label):
    matches = [(n, m) for n, page in enumerate(pages, 1) for m in re.finditer(pattern, page, re.M)]
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one body match, found {len(matches)}")
    return matches[0]


def parse(meta):
    path = Path(meta["pdf_path"])
    if not path.is_file():
        raise ValueError("missing PDF")
    if sha(path) != meta["pdf_sha256"]:
        raise ValueError("source PDF SHA-256 mismatch")
    pages = [p.extract_text() or "" for p in PdfReader(path).pages]
    full = "\n".join(pages)
    if not re.search(r"基金主代码\s+070002", full):
        raise ValueError("fund main code mismatch")
    cover = pages[0]
    sent = re.search(r"送出日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", cover)
    if not sent:
        raise ValueError("missing cover sent date")
    sent_date = f"{sent.group(1)}-{int(sent.group(2)):02d}-{int(sent.group(3)):02d}"
    if sent_date != meta["official_pub_date"]:
        raise ValueError(f"cover/list dates differ: {sent_date} vs {meta['official_pub_date']}")

    trade_pattern = rf"^\s*买入股票成本（成交）总额\s+({NUM})\s*\n\s*卖出股票收入（成交）总额\s+({NUM})\s*$"
    trade_page, trades = page_match(pages, trade_pattern, "gross stock-trade totals")
    buy, sell = (amount(value) for value in trades.groups())
    if not (buy >= 0 and sell >= 0):
        raise ValueError("negative gross trade amount")
    note_hits = [(n, m) for n, page in enumerate(pages, 1) for m in re.finditer(r"均按买入或卖出成交金额（成交单价乘以成交数量）填列，不考虑相关交易费用", page)]
    if len(note_hits) != 1:
        raise ValueError("missing transaction-fee definition")
    fee_page, fee_note = note_hits[0]
    section = "7.4.3" if meta["period"].endswith("H1") else "8.4.3"
    if section + " 买入股票的成本总额及卖出股票的收入总额" not in pages[trade_page - 1]:
        raise ValueError("stock-trade section heading mismatch")

    cash_page, cash = page_match(pages, rf"^\s*(银行存款|货币资金)\s+(?:\d+(?:\.\d+)+\s+)?({NUM})\s+({NUM})\s*$", "balance-sheet cash row")
    clear_page, clear = page_match(pages, rf"^\s*结算备付金\s+({NUM})\s+({NUM})\s*$", "balance-sheet settlement-reserve row")
    if clear_page not in (cash_page, cash_page + 1):
        raise ValueError("balance-sheet rows not on same or next page")
    cash_current, cash_previous = amount(cash.group(2)), amount(cash.group(3))
    clear_current, clear_previous = amount(clear.group(1)), amount(clear.group(2))
    combo_page, combo = page_match(pages, rf"^\s*7\s+银行存款和结算备付金合计\s+({NUM})\s+\d+\.\d{{2}}\s*$", "asset-composition cash plus settlement")
    combo_current = amount(combo.group(1))
    if cash_current + clear_current != combo_current:
        raise ValueError(f"balance-sheet/asset-composition mismatch {cash_current}+{clear_current}!={combo_current}")
    return {"period": meta["period"], "period_end": meta["period_end"],
            "report_type": "interim" if meta["period"].endswith("H1") else "annual",
            "official_report_title": meta["official_title"], "actual_publication_date": meta["official_pub_date"],
            "cover_sent_date": sent_date, "official_list_url": meta["official_list_url"],
            "pdf_url": meta["pdf_url"], "pdf_path": str(path), "pdf_sha256": meta["pdf_sha256"], "page_count": len(pages),
            "buy_total_cny": str(buy), "sell_total_cny": str(sell),
            "bank_current_cny": str(cash_current), "bank_prior_year_end_cny": str(cash_previous),
            "settlement_current_cny": str(clear_current), "settlement_prior_year_end_cny": str(clear_previous),
            "combined_current_cny": str(combo_current),
            "stock_trades": {"section": section, "pdf_page_1based": trade_page, "currency": "CNY", "scope": "all-stock gross transaction totals, not only the major per-stock lists",
                             "buy_gross_cny": str(buy), "sell_gross_cny": str(sell),
                             "buy_source_field": trades.group(0).splitlines()[0].strip(),
                             "sell_source_field": trades.group(0).splitlines()[-1].strip(),
                             "transaction_fee_note_short": fee_note.group(0), "transaction_fee_note_page_1based": fee_page},
            "cash_and_settlement": {"balance_sheet_page_1based": cash_page,
                                    "settlement_balance_sheet_page_1based": clear_page,
                                    "balance_sheet_cash_label": cash.group(1),
                                    "cash_current_cny": str(cash_current), "cash_previous_year_end_cny": str(cash_previous),
                                    "settlement_reserve_current_cny": str(clear_current),
                                    "settlement_reserve_previous_year_end_cny": str(clear_previous),
                                    "cash_source_field": cash.group(0).strip(), "settlement_source_field": clear.group(0).strip(),
                                    "asset_composition_page_1based": combo_page,
                                    "asset_composition_cash_plus_settlement_cny": str(combo_current),
                                    "asset_composition_source_field": combo.group(0).strip(),
                                    "components_equal_asset_composition": True,
                                    "previous_column_meaning": "previous calendar year end, not the preceding six-month end"}}


def main():
    old_output = ROOT / "reports.json"
    prior_failures = json.loads(old_output.read_text()).get("initial_parser_failures", []) if old_output.exists() else []
    if old_output.exists() and not prior_failures:
        prior_failures = json.loads(old_output.read_text()).get("reports_failed", [])
    reports = []
    failures = []
    for meta in sorted(MANIFEST["reports"], key=lambda x: (x["period"][:4], x["period"].endswith("FY"))):
        try:
            record = parse(meta)
            reports.append(record)
            print(meta["period"], "PASS", record["stock_trades"]["pdf_page_1based"], record["cash_and_settlement"]["balance_sheet_page_1based"])
        except Exception as exc:
            failures.append({"period": meta["period"], "pdf_path": meta["pdf_path"], "error": type(exc).__name__ + ": " + str(exc)})
            print(meta["period"], "FAIL", failures[-1]["error"])
    by = {r["period"]: r for r in reports}
    year_checks = []
    for year in range(2019, 2026):
        h, f = by.get(f"{year}H1"), by.get(f"{year}FY")
        if not h or not f:
            year_checks.append({"year": year, "status": "not_checked_missing_report"})
            continue
        hc, fc = h["cash_and_settlement"], f["cash_and_settlement"]
        same_prior = all(hc[key] == fc[key] for key in ["cash_previous_year_end_cny", "settlement_reserve_previous_year_end_cny"])
        h2_buy = D(f["stock_trades"]["buy_gross_cny"]) - D(h["stock_trades"]["buy_gross_cny"])
        h2_sell = D(f["stock_trades"]["sell_gross_cny"]) - D(h["stock_trades"]["sell_gross_cny"])
        year_checks.append({"year": year, "same_previous_year_end_cash_components": same_prior,
                            "h2_buy_gross_cny_from_fy_minus_h1": str(h2_buy),
                            "h2_sell_gross_cny_from_fy_minus_h1": str(h2_sell),
                            "h2_gross_nonnegative": h2_buy >= 0 and h2_sell >= 0,
                            "h2_opening_cash_plus_settlement_cny_point_in_time": str(D(hc["cash_current_cny"]) + D(hc["settlement_reserve_current_cny"]))})
    adjacent = []
    for year in range(2020, 2026):
        prev, curr = by.get(f"{year-1}FY"), by.get(f"{year}H1")
        if not prev or not curr:
            continue
        a, b = prev["cash_and_settlement"], curr["cash_and_settlement"]
        adjacent.append({"year": year, "previous_fy_to_current_h1_comparison_equal":
                         a["cash_current_cny"] == b["cash_previous_year_end_cny"] and
                         a["settlement_reserve_current_cny"] == b["settlement_reserve_previous_year_end_cny"],
                         "cash_previous_fy_end_cny": a["cash_current_cny"], "cash_current_report_prior_year_cny": b["cash_previous_year_end_cny"],
                         "reserve_previous_fy_end_cny": a["settlement_reserve_current_cny"], "reserve_current_report_prior_year_cny": b["settlement_reserve_previous_year_end_cny"]})
    output = {"schema_version": 1, "fund_code": "070002", "fund_name": "嘉实增长混合",
              "source_manifest": str(OLD), "source_manifest_sha256": sha(OLD),
              "reports_requested": 14, "reports_passed": len(reports), "reports_failed": failures,
              "initial_parser_failures": prior_failures,
              "reports": reports, "same_year_h1_fy_checks": year_checks,
              "adjacent_annual_comparison_checks": adjacent,
              "no_redemption_or_price_effect_computed": True}
    (ROOT / "reports.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    if failures or any(not c.get("same_previous_year_end_cash_components", False) or not c.get("h2_gross_nonnegative", False) for c in year_checks):
        raise ValueError("qualification incomplete; see reports.json")
    print(json.dumps({"passed": len(reports), "failures": len(failures), "years_h2_checked": len(year_checks)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
