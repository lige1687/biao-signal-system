"""Check complete stock holdings and unit flows in saved official PDFs."""

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from qualify import HERE, OUT, SOURCES


FILES = {
    "2024H1": ("000001-2024H1-chinaamc.pdf", 36, 35, 45, 49),
    "2024FY": ("000001-2024FY-chinaamc.pdf", 47, 46, 57, 61),
}
ROW = re.compile(r"^\s*(\d+)\s+(\d{6})\s+(.+?)\s+([\d,]+)\s+([\d,]+\.\d{2})\s+([\d.]+)\s*$")
MONEY = re.compile(r"([\d,]+\.\d{2})")
FLOW_LABELS = {
    "opening": "本报告期期初基金份额总额",
    "subscriptions": "本报告期基金总申购份额",
    "redemptions": "本报告期基金总赎回份额",
    "closing": "本报告期期末基金份额总额",
}


def money_from_line(line, *, first=False):
    matches = MONEY.findall(line)
    if not matches or (not first and len(matches) != 1):
        raise ValueError(f"unexpected amount count: {line}")
    return Decimal(matches[0].replace(",", ""))


def parse(period):
    filename, holdings_start, assets_page, flow_page, expected_pages = FILES[period]
    path = OUT / filename
    raw = path.read_bytes()
    reader = PdfReader(str(path))
    if len(reader.pages) != expected_pages or not raw.startswith(b"%PDF-"):
        raise ValueError("PDF identity or page count changed")
    first_page = reader.pages[0].extract_text(extraction_mode="layout")
    assert "华夏成长证券投资基金" in first_page
    assert "华夏基金管理有限公司" in first_page
    asset_text = reader.pages[assets_page].extract_text(extraction_mode="layout")
    asset_lines = [line for line in asset_text.splitlines() if "其中：股票" in line]
    if len(asset_lines) != 1:
        raise ValueError("stock assets row missing")
    stock_assets = money_from_line(asset_lines[0], first=True)

    rows = []
    active = False
    holding_pages = []
    unmatched = []
    for page_number in range(holdings_start, len(reader.pages) + 1):
        page_text = reader.pages[page_number - 1].extract_text(extraction_mode="layout")
        for line in page_text.splitlines():
            if "期末按公允价值占基金资产净值比例大小排序的所有股票投资明细" in line:
                active = True
                continue
            if active and re.match(r"^\s*[78]\.4\s", line):
                active = False
                break
            if not active:
                continue
            match = ROW.match(line)
            if match:
                rows.append({"index": int(match[1]), "stock_code": match[2],
                             "stock_name": match[3].strip(),
                             "shares": int(match[4].replace(",", "")),
                             "fair_value_cny": Decimal(match[5].replace(",", "")),
                             "pct_net_assets": match[6], "pdf_page": page_number})
                if page_number not in holding_pages:
                    holding_pages.append(page_number)
            elif re.match(r"^\s*\d+\s+\d{6}", line):
                unmatched.append({"pdf_page": page_number, "text": line.strip()})
        if rows and not active:
            break
    if unmatched or not rows or [r["index"] for r in rows] != list(range(1, len(rows) + 1)):
        raise ValueError(f"incomplete holding rows: {unmatched[:3]}")
    if len(set(r["stock_code"] for r in rows)) != len(rows):
        raise ValueError("duplicate stock code")
    holdings_sum = sum((r["fair_value_cny"] for r in rows), Decimal("0"))
    if holdings_sum != stock_assets:
        raise ValueError(f"holdings sum {holdings_sum} != stock assets {stock_assets}")

    flow_text = reader.pages[flow_page - 1].extract_text(extraction_mode="layout")
    assert "单位：份" in flow_text
    flows = {}
    for key, label in FLOW_LABELS.items():
        lines = [line for line in flow_text.splitlines() if label in line]
        if len(lines) != 1:
            raise ValueError(f"flow row missing: {label}")
        flows[key] = money_from_line(lines[0])
    if flows["opening"] + flows["subscriptions"] - flows["redemptions"] != flows["closing"]:
        raise ValueError("unit-flow identity fails")
    csv_path = OUT / f"000001-{period}-all-stocks.csv"
    with csv_path.open("x", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("index", "stock_code", "stock_name", "shares", "fair_value_cny", "pct_net_assets", "pdf_page"))
        for row in rows:
            writer.writerow([row[key] for key in ("index", "stock_code", "stock_name", "shares", "fair_value_cny", "pct_net_assets", "pdf_page")])
    return {
        "fund_code": "000001", "fund_name": "华夏成长证券投资基金",
        "manager": "华夏基金管理有限公司", "period": period,
        "period_end": SOURCES[period]["period_end"],
        "announcement_date": SOURCES[period]["announcement_date"],
        "announcement_page": SOURCES[period]["page"],
        "official_pdf_url": SOURCES[period]["pdf"],
        "official_pdf_path": str(path), "official_pdf_sha256": hashlib.sha256(raw).hexdigest(),
        "official_pdf_bytes": len(raw), "pdf_pages": len(reader.pages),
        "holdings_rows": len(rows), "holdings_last_index": rows[-1]["index"],
        "holdings_pages": holding_pages, "shares_unit": "股", "money_unit": "人民币元",
        "holdings_value_sum_cny": str(holdings_sum),
        "stock_assets_cny": str(stock_assets), "holdings_csv": str(csv_path),
        "flow_page": flow_page, "flow_unit": "份",
        "flow": {key: str(value) for key, value in flows.items()},
        "stock_codes": [row["stock_code"] for row in rows],
    }


def main():
    records = {period: parse(period) for period in FILES}
    h1 = {key: Decimal(value) for key, value in records["2024H1"]["flow"].items()}
    fy = {key: Decimal(value) for key, value in records["2024FY"]["flow"].items()}
    h2 = {"opening": h1["closing"],
          "subscriptions": fy["subscriptions"] - h1["subscriptions"],
          "redemptions": fy["redemptions"] - h1["redemptions"],
          "closing": fy["closing"]}
    assert fy["opening"] == h1["opening"]
    assert h2["opening"] + h2["subscriptions"] - h2["redemptions"] == h2["closing"]
    compact = {}
    for period, record in records.items():
        compact[period] = {key: value for key, value in record.items() if key != "stock_codes"}
    compact["2024H2_derived_flow"] = {key: str(value) for key, value in h2.items()}
    compact["common_stock_codes_H1_FY"] = len(set(records["2024H1"]["stock_codes"]) & set(records["2024FY"]["stock_codes"]))
    compact["union_stock_codes_H1_FY"] = len(set(records["2024H1"]["stock_codes"]) | set(records["2024FY"]["stock_codes"]))
    (HERE / "fields.json").write_text(json.dumps(compact, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"rows": {k: v["holdings_rows"] for k, v in records.items()},
                      "stock_values": {k: v["stock_assets_cny"] for k, v in records.items()},
                      "h2_flow": compact["2024H2_derived_flow"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
