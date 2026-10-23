"""Read disclosed cash/reinvestment dividends; separate current period from future notices."""

import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).parent
MANIFEST = json.loads((ROOT / "source-manifest.json").read_text())
HISTORY = json.loads((ROOT / "history-series.json").read_text())
NUM = r"[\d,]+\.\d{2}"
D = Decimal


def page_at(pages, offset):
    end = 0
    for i, page in enumerate(pages, 1):
        end += len(page)
        if offset < end:
            return i
        end += 1
    raise ValueError("text offset exceeds pages")


def parse(item):
    pages = [page.extract_text() or "" for page in PdfReader(item["pdf_path"]).pages]
    full = "\n".join(pages)
    headings = list(re.finditer(r"(?:6|7)\.4\.11 利润分配情况", full))
    assert headings, item["period"]
    head = headings[-1]
    tail = full[head.end():]
    end = re.search(r"(?:6|7)\.4\.12\s", tail)
    assert end, item["period"]
    section = tail[:end.start()]
    total = re.search(rf"合计\s+(?:-\s+){{3}}\d+\.\d{{4}}\s+({NUM})\s+({NUM})\s+({NUM})\s+-", section)
    if total:
        cash, reinvest, distributed = (D(x.replace(",", "")) for x in total.groups())
        assert cash + reinvest == distributed
        evidence = total.group(0).strip()
        evidence_page = page_at(pages, head.end() + total.start())
        kind = "actual_distribution_table"
    else:
        zero = re.search(r"本基金未实施利润分配。", section)
        assert zero, f"no distribution evidence for {item['period']}"
        cash = reinvest = distributed = D("0")
        evidence = zero.group(0)
        evidence_page = page_at(pages, head.end() + zero.start())
        kind = "explicit_no_distribution_sentence"

    # The annual three-year summary is a second check when it has a current-year row.
    annual_row = None
    annual_page = None
    if item["period"].endswith("FY"):
        summary = list(re.finditer(r"3\.[34] 过去三年基金的利润分配情况", full))
        assert summary
        s = summary[-1]
        summary_tail = full[s.end():s.end() + 1400]
        row = re.search(rf"^{item['period'][:4]}\s*年\s+([^\n]+)$", summary_tail, re.M)
        if row:
            annual_row = row.group(0).strip()
            annual_page = page_at(pages, s.end() + row.start())
            if distributed:
                assert str(cash) in annual_row.replace(",", "") and str(reinvest) in annual_row.replace(",", "")
            else:
                assert re.search(r"(?:-\s*){4}", annual_row)
        else:
            assert not distributed, "missing annual row for a positive distribution"

    # Identify the original report's note that fund subscriptions include dividend reinvestment.
    note_patterns = [r"申购含红利再投、转换入份额", r"基金总申购份额含红利再投、转换入份额",
                     r"红利再投资等引起的实收"]
    notes = [m for pattern in note_patterns for m in re.finditer(pattern, full)]
    note = max(notes, key=lambda m: m.start()) if notes else None
    assert note or reinvest == 0, f"missing reinvestment accounting note: {item['period']}"
    return {"period": item["period"], "period_end": item["period_end"], "announcement_date": item["official_pub_date"],
            "cash_dividend_cny": str(cash), "dividend_reinvestment_cny": str(reinvest),
            "total_distribution_cny": str(distributed), "source_pdf_sha256": item["pdf_sha256"],
            "source_page_1based": evidence_page, "source_section": "6.4.11" if item["period"].endswith("H1") else "7.4.11",
            "evidence_type": kind, "evidence_excerpt": evidence,
            "annual_summary_current_year_row": annual_row, "annual_summary_page_1based": annual_page,
            "subscription_reinvestment_note": note.group(0) if note else None,
            "subscription_reinvestment_note_page_1based": page_at(pages, note.start()) if note else None,
            "future_notice_excluded": item["period"].endswith("FY") and str(int(item["period"][:4]) + 1) in section}


def main():
    reports = {item["period"]: parse(item) for item in MANIFEST["reports"]}
    halves = []
    history = {(h["year"], h["half"]): h for h in HISTORY["half_years"]}
    for year in range(2019, 2026):
        h, f = reports[f"{year}H1"], reports[f"{year}FY"]
        a, b = {key: D(h[key]) for key in ("cash_dividend_cny", "dividend_reinvestment_cny", "total_distribution_cny")}, {key: D(f[key]) for key in ("cash_dividend_cny", "dividend_reinvestment_cny", "total_distribution_cny")}
        assert all(b[key] >= a[key] for key in a)
        for half, values, sources in [(1, a, [f"{year}H1"]), (2, {key: b[key] - a[key] for key in a}, [f"{year}FY", f"{year}H1"])]:
            data = history[(year, half)]
            reinvest = values["dividend_reinvestment_cny"]
            sub_cny = D(data["subscription_net_asset_change_cny"])
            red_cny = D(data["redemption_net_asset_change_cny_signed"])
            assert sub_cny >= reinvest, (year, half)
            # Remove internal dividend reinvestment only. Conversion in/out still remain.
            adjusted_net_redemption = -(sub_cny - reinvest + red_cny)
            halves.append({"year": year, "half": half, "period_end": data["period_end"],
                           "announcement_date": data["announcement_date"], "source_periods": sources,
                           "cash_dividend_cny": str(values["cash_dividend_cny"]),
                           "dividend_reinvestment_cny": str(reinvest),
                           "total_distribution_cny": str(values["total_distribution_cny"]),
                           "reported_subscription_net_asset_change_cny": str(sub_cny),
                           "reported_redemption_net_asset_change_cny_signed": str(red_cny),
                           "net_redemption_excluding_reinvestment_cny": str(adjusted_net_redemption),
                           "opening_net_assets_cny": data["opening_net_assets_cny"],
                           "adjusted_net_redemption_fraction_numerator_cny": str(adjusted_net_redemption),
                           "adjusted_net_redemption_fraction_denominator_cny": data["opening_net_assets_cny"],
                           "qualification": "Removes disclosed dividend reinvestment from subscription transaction amount; conversions remain, so this is not verified external cash flow. Cash dividends are separate and not added to redemptions."})
    output = {"fund_code": "070002", "reports": [reports[x["period"]] for x in MANIFEST["reports"]],
              "half_years": halves, "definition": "Actual distribution period, not financial year to which a January dividend relates. H2 = FY minus H1; positive distributions in this window occurred in H1 2020, 2021 and 2025.",
              "returns_calculated": False}
    (ROOT / "reinvestment-by-half.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"reports": len(reports), "halves": len(halves), "positive_halves": [f"{r['year']}H{r['half']}" for r in halves if D(r["dividend_reinvestment_cny"]) > 0]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
