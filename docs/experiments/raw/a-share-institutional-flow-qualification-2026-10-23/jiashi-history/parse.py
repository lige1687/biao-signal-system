"""Qualify complete 070002 H1/FY stock disclosures and fund flow bridges, 2019-25."""

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).parent
MANIFEST = json.loads((ROOT / "source-manifest.json").read_text())
OUT = Path(json.loads((ROOT.parent / "storage-plan.json").read_text())["output"]) / "jiashi-history"
NUM = r"[-]?[\d,]+(?:\.\d+)?"
HOLDING = re.compile(r"^\s*(\d{1,3})\s+([0368]\d{5})\s+(.+?)\s+([\d,]+)\s+([\d,]+\.\d{2})\s+(\d+\.\d{2})\s*$", re.M)


def dec(x):
    return Decimal(x.replace(",", ""))


def one(text, pattern, name, group=1):
    m = re.search(pattern, text, re.M)
    if not m:
        raise ValueError("missing " + name)
    return m.group(group)


def page_for(pages, needle):
    return next((i + 1 for i, page in enumerate(pages) if needle in page), None)


def page_for_pattern(pages, pattern):
    return next((i + 1 for i, page in enumerate(pages) if re.search(pattern, page, re.M)), None)


def page_at_offset(pages, offset):
    end = 0
    for i, page in enumerate(pages, 1):
        end += len(page)
        if offset < end:
            return i
        end += 1  # newline joining pages
    raise ValueError(f"offset outside PDF text: {offset}")


def parse(item):
    path = Path(item["pdf_path"])
    pdf = path.read_bytes()
    assert hashlib.sha256(pdf).hexdigest() == item["pdf_sha256"]
    pages = [p.extract_text() or "" for p in PdfReader(path).pages]
    full = "\n".join(pages)
    cover = pages[0]
    period = item["period"]
    assert period[:4] in cover and "嘉实增长" in cover
    assert re.search("年度报告" if period.endswith("FY") else r"中期\s*报告|半年\s*度报告", cover)
    sent = one(cover, r"送出日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", "cover sent date", group=0)
    sent_parts = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", sent)
    sent_date = f"{sent_parts.group(1)}-{int(sent_parts.group(2)):02d}-{int(sent_parts.group(3)):02d}"
    assert sent_date == item["official_pub_date"], f"cover/list date mismatch {sent_date} {item['official_pub_date']}"
    code = one(full, r"基金主代码\s+(\d{6})", "fund code")
    assert code == "070002"
    assert re.search(r"基金简称\s+嘉实增长混合", full), "fund short name"
    assert re.search(r"基金运作方式\s+契约型开放式", full), "fund operating type"
    flow_start = full.rfind("开放式基金份额变动")
    assert flow_start >= 0
    flow = full[flow_start:]
    shares = {}
    opening_flow_match = re.search(rf"(?:本报告期期初|报告期期初)基金份额总额\s+{NUM}", flow)
    assert opening_flow_match
    for key, pattern in {
        "opening_units": rf"(?:本报告期期初|报告期期初)基金份额总额\s+({NUM})",
        "subscriptions_units": rf"(?:本报告期|报告期期间)基金总申购份额\s+({NUM})",
        "redemptions_units": rf"(?:本报告期|报告期期间)基金总赎回份额\s+({NUM})",
        "closing_units": rf"(?:本报告期期末|报告期期末)基金份额总额\s+({NUM})",
    }.items():
        shares[key] = str(dec(one(flow, pattern, key)))
    bridge = dec(shares["opening_units"]) + dec(shares["subscriptions_units"]) - dec(shares["redemptions_units"]) - dec(shares["closing_units"])
    assert bridge == 0, f"share bridge {bridge}"

    starts = [m.start() for m in re.finditer("所有股票投资明细", full)
              if "股票代" in full[m.end():m.end() + 300]]
    assert len(starts) == 1, f"holdings heading {len(starts)}"
    start = starts[0]
    tail = full[start:]
    end = re.search(r"\n(?:7|8)\.4\s+", tail)
    assert end, "holdings table ending"
    holdings = HOLDING.findall(tail[:end.start()])
    ranks = [int(h[0]) for h in holdings]
    assert ranks and ranks == list(range(1, len(ranks) + 1)), f"holdings ranks {ranks[:5]}..{ranks[-5:]}"
    assert len({h[1] for h in holdings}) == len(holdings), "duplicate stock code"
    stock_assets = dec(one(full, rf"^\s*其中：股票投资\s+(?:\S+\s+)?({NUM})\s+{NUM}\s*$", "stock assets"))
    stock_sum = sum((dec(h[4]) for h in holdings), Decimal(0))
    assert stock_sum == stock_assets, f"holding sum {stock_sum} != assets {stock_assets}"

    # Balance sheet columns: current reporting date, preceding year end.
    net = re.search(rf"^\s*(?:所有者权益合计|净资产合计)\s+({NUM})\s+({NUM})\s*$", full, re.M)
    assert net, "net asset balance-sheet row"
    cash = re.search(rf"^\s*(?:银行存款|货币资金)\s+(?:\S+\s+)?({NUM})\s+({NUM})\s*$", full, re.M)
    assert cash, "cash balance-sheet row"
    # Equity-statement entries are net-asset changes due to share transactions,
    # including reinvestment/conversion; they are not measured investor cash flow.
    subs_value = re.search(rf"^\s*其中：基金申购款\s+({NUM})\s+({NUM})\s+({NUM})\s*$", full, re.M)
    red_value = re.search(rf"^\s*基金赎回款\s+({NUM})\s+({NUM})\s+({NUM})\s*$", full, re.M)
    assert subs_value and red_value, "net-asset transaction value rows"
    assert dec(subs_value.group(3)) > 0 and dec(red_value.group(3)) < 0, "transaction value signs"
    rows = []
    for rank, stock_code, name, quantity, value, pct in holdings:
        rows.append({"fund_code": code, "period_end": item["period_end"], "official_pub_date": item["official_pub_date"], "rank": rank,
                     "stock_code": stock_code, "stock_name": name.strip(), "shares": quantity.replace(",", ""),
                     "fair_value_cny": value.replace(",", ""), "pct_fund_nav": pct, "source_pdf_sha256": item["pdf_sha256"]})
    result = {"period": period, "period_end": item["period_end"], "official_pub_date": item["official_pub_date"],
              "cover_sent_date": sent_date,
              "fund_code": code, "fund_name": "嘉实增长开放式证券投资基金", "fund_type": "契约型开放式",
              "report_kind": "annual" if period.endswith("FY") else "interim", "pdf_path": str(path), "pdf_sha256": item["pdf_sha256"],
              "pdf_bytes": item["pdf_bytes"], "page_count": len(pages), "holdings_rows": len(rows), "holdings_scope": "all",
              "holdings_sum_cny": str(stock_sum), "stock_assets_cny": str(stock_assets), "holdings_sum_equals_stock_assets": True,
              **shares, "share_bridge_residual_units": str(bridge), "shares_unit": "fund shares; subscriptions include conversion-in and sometimes dividend reinvestment; redemptions include conversion-out",
              "opening_net_assets_cny": net.group(2).replace(",", ""), "closing_net_assets_cny": net.group(1).replace(",", ""),
              "cash_or_bank_deposits_cny": cash.group(1).replace(",", ""), "cash_or_bank_deposits_label": cash.group(0).split()[0],
              "subscription_net_asset_change_cny": subs_value.group(3).replace(",", ""),
              "redemption_net_asset_change_cny": red_value.group(3).replace(",", ""),
              "subscription_transaction_source_line": subs_value.group(0).strip(),
              "redemption_transaction_source_line": red_value.group(0).strip(),
              "net_asset_change_definition": "net asset changes due to fund share transactions; not directly investor cash receipts/payments",
              "class_identity_note": "Fund basic-information table has one main code 070002 and one total share-flow line in this original report; no separate class flow is disclosed here.",
              "source_pages_1based": {"fund_code": page_for(pages, "基金主代码"),
                                      "holdings_heading": page_at_offset(pages, start),
                                      "holdings_first_row": page_for(pages, f"1 {holdings[0][1]}"),
                                      "share_flow": page_at_offset(pages, flow_start + opening_flow_match.start()),
                                      "balance_sheet": page_at_offset(pages, net.start()),
                                      "net_asset_change": page_at_offset(pages, subs_value.start())}}
    return result, rows


def main():
    results = []
    all_rows = []
    for item in MANIFEST["reports"]:
        try:
            result, rows = parse(item)
            results.append(result)
            all_rows.extend(rows)
            print(item["period"], "PASS", len(rows))
        except Exception as exc:
            results.append({"period": item["period"], "status": "failed", "error": type(exc).__name__ + ": " + str(exc)})
            print(item["period"], "FAIL", results[-1]["error"])
    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "070002-history-holdings.csv"
    if all_rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
    (ROOT / "qualification.json").write_text(json.dumps({"fund_code": "070002", "periods_requested": 14, "periods_passed": sum("holdings_rows" in x for x in results), "holdings_csv": str(csv_path), "reports": results}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
