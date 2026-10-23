"""Read the twelve saved full reports, with per-report failure preservation."""

import csv
import hashlib
import json
import re
from decimal import Decimal

from pypdf import PdfReader

from collect import HERE, OUT, RAW, HISTORY, LEDGER


ROW = re.compile(r"^\s*(\d+)\s+(\d{6})\s+(.+?)\s+([\d,]+)\s+([\d,]+\.\d{1,2})\s+([\d.]+)\s*$")
MONEY = re.compile(r"-?[\d,]+\.\d{2}")
FLOW_LABELS = {
    "opening": "本报告期期初基金份额总额",
    "subscriptions": "本报告期基金总申购份额",
    "redemptions": "本报告期基金总赎回份额",
    "closing": "本报告期期末基金份额总额",
}


def decimal_number(text):
    return Decimal(text.replace(",", ""))


def page_texts(reader):
    return [page.extract_text(extraction_mode="layout") for page in reader.pages]


def parse_one(item, official_request):
    year, kind = item["year"], item["type"]
    key = f"{year}{kind}"
    path = OUT / f"000001-{key}-chinaamc.pdf"
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF-") or hashlib.sha256(raw).hexdigest() != official_request["sha256"]:
        raise ValueError("saved original does not match collection ledger")
    reader = PdfReader(str(path))
    texts = page_texts(reader)
    if "华夏成长证券投资基金" not in texts[0] or "华夏基金管理有限公司" not in texts[0]:
        raise ValueError("wrong fund or manager on title page")
    report_title = "半年度报告" if year == 2019 and kind == "H1" else ("中期报告" if kind == "H1" else "年度报告")
    if report_title not in texts[0].replace(" ", ""):
        raise ValueError("wrong report type or year")
    first_page_date = next((line.strip() for line in texts[0].splitlines() if "送出日期" in line), None)
    if not first_page_date:
        raise ValueError("PDF sent date absent")
    profile = texts[3]
    if "基金主代码" not in profile or "000001" not in profile or "2001" not in profile:
        raise ValueError("fund profile identity missing")
    trading_codes = next((line.strip() for line in profile.splitlines() if "交易代码" in line), None)

    heading = "期末按公允价值占基金资产净值比例大小排序的所有股票投资明细"
    holdings_start = next((i for i, text in enumerate(texts) if i >= 10 and heading in text), None)
    if holdings_start is None:
        raise ValueError("all-stock heading missing")
    rows = []
    unmatched = []
    pages = []
    active = False
    for i in range(holdings_start, len(texts)):
        for line in texts[i].splitlines():
            if heading in line:
                active = True
                continue
            if active and re.match(r"^\s*[78]\.4(?!\d)", line):
                active = False
                break
            if not active:
                continue
            match = ROW.match(line)
            if match:
                rows.append({"rank": int(match[1]), "stock_code": match[2],
                             "stock_name": match[3].strip(),
                             "shares": int(match[4].replace(",", "")),
                             "fair_value_cny": decimal_number(match[5]),
                             "pct_net_assets": match[6], "pdf_page": i + 1})
                if i + 1 not in pages:
                    pages.append(i + 1)
            elif re.match(r"^\s*\d+\s+\d{6}", line):
                unmatched.append((i + 1, line.strip()))
        if rows and not active:
            break
    if unmatched or not rows or [r["rank"] for r in rows] != list(range(1, len(rows) + 1)):
        raise ValueError(f"stock rows missing or noncontiguous: {unmatched[:3]}, {len(rows)} rows")
    if len({r["stock_code"] for r in rows}) != len(rows):
        raise ValueError("duplicate stock code")
    asset_lines = [line for text in texts[max(0, holdings_start - 3):holdings_start]
                   for line in text.splitlines() if "其中：股票" in line]
    if not asset_lines:
        raise ValueError("asset-section stock total absent")
    stock_assets = decimal_number(MONEY.findall(asset_lines[-1])[0])
    holdings_sum = sum((r["fair_value_cny"] for r in rows), Decimal(0))
    if holdings_sum != stock_assets:
        raise ValueError(f"stock value {holdings_sum} differs from asset total {stock_assets}")

    flow_candidates = [(i, text + "\n" + (texts[i + 1] if i + 1 < len(texts) else ""))
                       for i, text in enumerate(texts) if i >= 10 and
                       "开放式基金份额变动" in text and
                       all(label in text + "\n" + (texts[i + 1] if i + 1 < len(texts) else "")
                           for label in FLOW_LABELS.values())]
    if len(flow_candidates) != 1:
        raise ValueError(f"expected one current unit-flow table, got {len(flow_candidates)}")
    flow_page, flow_text = flow_candidates[0]
    if "单位：份" not in flow_text:
        raise ValueError("unit-flow units missing")
    flow = {}
    for name, label in FLOW_LABELS.items():
        lines = [line for line in flow_text.splitlines() if label in line]
        if len(lines) != 1 or len(MONEY.findall(lines[0])) != 1:
            raise ValueError(f"unexpected {name} unit-flow line: {lines}")
        flow[name] = decimal_number(MONEY.findall(lines[0])[0])
    if flow["opening"] + flow["subscriptions"] - flow["redemptions"] != flow["closing"]:
        raise ValueError("fund-unit bridge fails")

    csv_path = OUT / f"000001-{key}-all-stocks.csv"
    if csv_path.exists():
        with csv_path.open(newline="") as existing:
            old_rows = list(csv.DictReader(existing))
        if len(old_rows) != len(rows) or sum((Decimal(r["fair_value_cny"]) for r in old_rows), Decimal(0)) != holdings_sum:
            raise ValueError("existing parsed CSV differs; never overwrite")
    else:
        with csv_path.open("x", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(("rank", "stock_code", "stock_name", "shares", "fair_value_cny", "pct_net_assets", "pdf_page"))
            for row in rows:
                writer.writerow([row[k] for k in ("rank", "stock_code", "stock_name", "shares", "fair_value_cny", "pct_net_assets", "pdf_page")])
    return {
        "key": key, "fund_code": "000001", "fund_name": "华夏成长证券投资基金",
        "manager": "华夏基金管理有限公司", "trading_codes_line": trading_codes,
        "report_type": report_title, "period_end": f"{year}-06-30" if kind == "H1" else f"{year}-12-31",
        "announcement_date": item["announcement_date"], "report_sent_date_text": first_page_date,
        "announcement_page": item["page"], "official_pdf_url": official_request["url"],
        "pdf_path": str(path), "pdf_sha256": official_request["sha256"],
        "pdf_pages": len(reader.pages), "pdf_bytes": len(raw),
        "holdings_rows": len(rows), "holdings_pages": pages,
        "holdings_sum_cny": str(holdings_sum), "stock_assets_cny": str(stock_assets),
        "holdings_unit": "shares and CNY", "holdings_csv": str(csv_path),
        "flow_page": flow_page + 1, "flow_unit": "fund units",
        "flow": {name: str(value) for name, value in flow.items()},
    }


def main():
    ledger = json.loads(LEDGER.read_text())
    pdf_requests = {x["key"]: x for x in ledger if x["kind"] == "official_pdf" and "error" not in x}
    output = []
    for item in HISTORY["reports"]:
        if item["year"] == 2024:
            continue
        key = f'{item["year"]}{item["type"]}'
        try:
            output.append({"key": key, "status": "qualified", "data": parse_one(item, pdf_requests[key])})
        except Exception as exc:
            output.append({"key": key, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        (HERE / "parse-status.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"qualified": sum(x["status"] == "qualified" for x in output),
                      "failures": [x for x in output if x["status"] == "failed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
