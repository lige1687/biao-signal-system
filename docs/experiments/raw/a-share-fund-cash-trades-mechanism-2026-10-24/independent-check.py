"""Independent source-to-matrix arithmetic audit; no return or fit computation."""

import hashlib
import json
import re
from decimal import Decimal, getcontext
from pathlib import Path
from statistics import median

from pypdf import PdfReader


getcontext().prec = 45
HERE = Path(__file__).parent
OLD = HERE.parent / "a-share-institutional-flow-qualification-2026-10-23"
D = Decimal
NUM = r"[\d,]+\.\d{2}"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def money(s):
    return D(str(s).replace(",", ""))


def pack(group):
    if not group:
        return {"n": 0, "net_selling_n": 0, "net_buying_n": 0, "zero_n": 0,
                "net_selling_fraction": None, "median_net_sale_cny": None,
                "median_net_sale_over_nav": None, "D_over_nav_range": None, "periods": []}
    sale = [x["N"] for x in group]
    ratio = [x["N"] / x["NAV"] for x in group]
    dr = [x["D"] / x["NAV"] for x in group]
    return {"n": len(group), "net_selling_n": sum(x > 0 for x in sale),
            "net_buying_n": sum(x < 0 for x in sale), "zero_n": sum(x == 0 for x in sale),
            "net_selling_fraction": sum(x > 0 for x in sale) / len(group),
            "median_net_sale_cny": str(median(sale)),
            "median_net_sale_over_nav": str(median(ratio)),
            "D_over_nav_range": [str(min(dr)), str(max(dr))],
            "periods": [x["period"] for x in group]}


def compare_group(independent, frozen, prefix, differences):
    for field in ("n", "net_selling_n", "net_buying_n", "zero_n", "periods"):
        if independent[field] != frozen[field]:
            differences.append({"where": prefix + "." + field, "independent": independent[field], "frozen": frozen[field]})
    for field in ("net_selling_fraction", "median_net_sale_cny", "median_net_sale_over_nav"):
        x, y = independent[field], frozen[field]
        if (x is None) != (y is None) or (x is not None and abs(D(str(x)) - D(str(y))) > D("1e-24")):
            differences.append({"where": prefix + "." + field, "independent": x, "frozen": y})
    x, y = independent["D_over_nav_range"], frozen["D_over_nav_range"]
    if (x is None) != (y is None) or (x is not None and any(abs(D(a) - D(b)) > D("1e-24") for a, b in zip(x, y))):
        differences.append({"where": prefix + ".D_over_nav_range", "independent": x, "frozen": y})


def source_rows():
    jtr = {r["period"]: r for r in read(HERE / "jiashi/reports.json")["reports"]}
    htr = {r["period"]: r for r in read(HERE / "huaxia/reports.json")["reports"]}
    jflow = {r["period"]: r for r in read(OLD / "jiashi-history/qualification.json")["reports"]}
    hflow = {r["key"]: r["financial"] for r in read(OLD / "huaxia-history/history-series.json")["reports"]}
    jr = {f"{r['year']}H{r['half']}": r for r in read(OLD / "jiashi-history/reinvestment-by-half.json")["half_years"]}
    hr = {r["period"]: r for r in read(OLD / "huaxia-history/reinvestment-by-half.json")["halves"]}
    rows = []
    issues = []
    for fund, tr, fl, ri in (("070002", jtr, jflow, jr), ("000001", htr, hflow, hr)):
        if len(tr) != 14 or len(fl) != 14 or len(ri) != 14:
            issues.append({"where": fund, "source_count": [len(tr), len(fl), len(ri)]})
        for year in range(2019, 2026):
            h, f = tr[f"{year}H1"], tr[f"{year}FY"]
            hf, ff = fl[f"{year}H1"], fl[f"{year}FY"]
            def flow(x):
                if fund == "070002":
                    return money(x["subscription_net_asset_change_cny"]), money(x["redemption_net_asset_change_cny"])
                return money(x["subscription_transaction_cny"]), money(x["redemption_transaction_cny_signed"])
            hs, hd = flow(hf)
            fs, fd = flow(ff)
            for half in (1, 2):
                period = f"{year}H{half}"
                if half == 1:
                    buy, sell = money(h["buy_total_cny"]), money(h["sell_total_cny"])
                    bank, settle = money(h["bank_prior_year_end_cny"]), money(h["settlement_prior_year_end_cny"])
                    sub, red_signed = hs, hd
                    nav = money(hf["opening_net_assets_cny"] if fund == "070002" else hf["net_assets_open_cny"])
                else:
                    buy = money(f["buy_total_cny"]) - money(h["buy_total_cny"])
                    sell = money(f["sell_total_cny"]) - money(h["sell_total_cny"])
                    bank, settle = money(h["bank_current_cny"]), money(h["settlement_current_cny"])
                    sub, red_signed = fs - hs, fd - hd
                    nav = money(hf["closing_net_assets_cny"] if fund == "070002" else hf["net_assets_close_cny"])
                reinvest = money(ri[period]["dividend_reinvestment_cny"])
                C0 = bank + settle
                d_report = -sub - red_signed
                row = {"fund_code": fund, "period": period, "buy": buy, "sell": sell,
                       "N": sell - buy, "bank": bank, "settlement": settle, "C0": C0,
                       "NAV": nav, "D_report": d_report, "reinvest": reinvest,
                       "D_adjusted": d_report + reinvest}
                if buy < 0 or sell < 0 or nav <= 0:
                    issues.append({"where": fund + " " + period, "issue": "invalid gross total or NAV"})
                rows.append(row)
    return rows, issues


def source_cross(rows, frozen_inputs, raw_old, adjusted_old):
    issues = []
    mapped = {(x["fund_code"], x["period"]): x for x in rows}
    if len(mapped) != 28 or len(frozen_inputs["half_years"]) != 28:
        issues.append({"where": "row count", "independent": len(mapped), "frozen": len(frozen_inputs["half_years"])})
    bindings = {"stock_buy_gross_cny": "buy", "stock_sell_gross_cny": "sell", "net_stock_sell_cny": "N",
                "bank_open_cny": "bank", "settlement_open_cny": "settlement", "C0_cny": "C0",
                "open_nav_cny": "NAV", "D_report_cny": "D_report", "reinvestment_cny": "reinvest",
                "D_adjusted_cny": "D_adjusted"}
    for x in frozen_inputs["half_years"]:
        a = mapped.get((x["fund_code"], x["period"]))
        if a is None:
            issues.append({"where": "missing input " + x["fund_code"] + " " + x["period"]})
            continue
        for frozen_name, own_name in bindings.items():
            if a[own_name] != money(x[frozen_name]):
                issues.append({"where": x["fund_code"] + " " + x["period"] + " " + frozen_name,
                               "independent": str(a[own_name]), "frozen": x[frozen_name]})
    raw_by = {x["period"]: x for x in raw_old["periods"]}
    adj_by = {x["period"]: x for x in adjusted_old["periods"]}
    for a in rows:
        p = a["period"]
        key = "jiashi_amount_pressure" if a["fund_code"] == "070002" else "huaxia_amount_pressure"
        old_raw = money(raw_by[p][key])
        old_adj = money(adj_by[p]["funds"][a["fund_code"]]["adjusted_pressure"])
        for definition, old in (("report", old_raw), ("adjusted", old_adj)):
            own = max(D(0), a["D_" + definition] / a["NAV"])
            if abs(own - old) > D("1e-24"):
                issues.append({"where": "old pressure " + a["fund_code"] + " " + p + " " + definition,
                               "independent": str(own), "frozen": str(old)})
    return issues


def group_audit(rows, summary):
    differences = []
    own_groups = []
    own_years = []
    for definition in ("report", "adjusted"):
        frozen_definition = "adjusted_conditional" if definition == "adjusted" else definition
        for fund in ("070002", "000001"):
            pool = []
            for source in rows:
                if source["fund_code"] == fund:
                    pool.append({**source, "D": source["D_" + definition]})
            groups = {"all": pool, "net_redemption": [x for x in pool if x["D"] > 0],
                      "non_net_redemption": [x for x in pool if x["D"] <= 0],
                      "redemption_above_C0": [x for x in pool if x["D"] > 0 and x["D"] > x["C0"]],
                      "redemption_at_or_below_C0": [x for x in pool if x["D"] > 0 and x["D"] <= x["C0"]]}
            frozen = next(x for x in summary["results"] if x["definition"] == frozen_definition and x["fund_code"] == fund)
            result = {"definition": frozen_definition, "fund_code": fund, "groups": {k: pack(v) for k, v in groups.items()}}
            for k, v in result["groups"].items():
                compare_group(v, frozen["groups"][k], definition + " " + fund + " " + k, differences)
            above, below = groups["redemption_above_C0"], groups["redemption_at_or_below_C0"]
            if above and below:
                ar = [x["D"] / x["NAV"] for x in above]
                br = [x["D"] / x["NAV"] for x in below]
                overlap = max(min(ar), min(br)) <= min(max(ar), max(br))
            else:
                overlap = False
            if overlap != frozen["cash_cells_redemption_size_ranges_overlap"]:
                differences.append({"where": definition + " " + fund + " cash range overlap",
                                    "independent": overlap, "frozen": frozen["cash_cells_redemption_size_ranges_overlap"]})
            result["cash_cells_redemption_size_ranges_overlap"] = overlap
            result["counterexample_periods"] = [x["period"] for x in groups["net_redemption"] if x["N"] <= 0]
            result["above_C0_counterexamples"] = [x["period"] for x in above if x["N"] <= 0]
            for k in ("counterexample_periods", "above_C0_counterexamples"):
                if result[k] != frozen[k]:
                    differences.append({"where": definition + " " + fund + " " + k,
                                        "independent": result[k], "frozen": frozen[k]})
            all_rate = result["groups"]["net_redemption"]["net_selling_fraction"]
            for frozen_field, group_name in (("gap_minus_all_net_redemption_selling_rate", "redemption_above_C0"),
                                             ("covered_minus_all_net_redemption_selling_rate", "redemption_at_or_below_C0")):
                rate = result["groups"][group_name]["net_selling_fraction"]
                own = None if rate is None or all_rate is None else rate - all_rate
                if own is None or abs(own - frozen[frozen_field]) > 1e-14:
                    differences.append({"where": definition + " " + fund + " " + frozen_field,
                                        "independent": own, "frozen": frozen[frozen_field]})
            own_groups.append(result)
        for year in range(2019, 2026):
            group = [{**x, "D": x["D_" + definition]} for x in rows if x["period"].startswith(str(year))]
            redemption = [x for x in group if x["D"] > 0]
            result = {"definition": frozen_definition, "year": year, "fund_halves": len(group),
                      "redemption_cases": len(redemption),
                      "redemption_and_net_sell": sum(x["N"] > 0 for x in redemption),
                      "redemption_but_net_buy_or_zero": [x["fund_code"] + " " + x["period"] for x in redemption if x["N"] <= 0]}
            frozen = next(x for x in summary["by_year"] if x["definition"] == frozen_definition and x["year"] == year)
            for k, v in result.items():
                if v != frozen[k]:
                    differences.append({"where": definition + " " + str(year) + " " + k,
                                        "independent": v, "frozen": frozen[k]})
            own_years.append(result)
    return own_groups, own_years, differences


def pdf_spot_checks(huaxia):
    outputs = []
    for period in ("2019H1", "2019FY", "2024H1"):
        r = huaxia[period]
        path = Path(r["pdf_path"])
        actual_sha = sha(path)
        if actual_sha != r["pdf_sha256"]:
            raise ValueError(period + " original PDF SHA mismatch")
        reader = PdfReader(path)
        parts = {}
        for field, page_field, line_field in (("buy", "stock_buy_pdf_page", "stock_buy_original_line"),
                                              ("sell", "stock_sell_pdf_page", "stock_sell_original_line"),
                                              ("bank", "balance_sheet_bank_pdf_page", "balance_sheet_bank_original_line"),
                                              ("settlement", "balance_sheet_settlement_pdf_page", "balance_sheet_settlement_original_line")):
            page = r[page_field]
            text = reader.pages[page - 1].extract_text() or ""
            original = r[line_field]
            lines = [line for line in text.splitlines() if re.sub(r"\s+", "", line) == re.sub(r"\s+", "", original)]
            if len(lines) != 1:
                raise ValueError(period + " " + field + " original line not uniquely present")
            amounts = [money(x) for x in re.findall(NUM, lines[0])]
            if field in ("buy", "sell"):
                expected = [money(r[field + "_total_cny"])]
            elif field == "bank":
                expected = [money(r["bank_current_cny"]), money(r["bank_prior_year_end_cny"])]
            else:
                expected = [money(r["settlement_current_cny"]), money(r["settlement_prior_year_end_cny"])]
            if amounts != expected:
                raise ValueError(period + " " + field + " PDF amounts differ")
            parts[field] = {"pdf_page_1based": page, "amounts_cny": [str(x) for x in amounts]}
        outputs.append({"period": period, "pdf_path": str(path), "pdf_sha256": actual_sha, "fields": parts})
    return outputs


def main():
    freeze = read(HERE / "freeze.json")
    bindings = freeze["bindings"]
    binding_differences = []
    root = HERE.parents[3]
    for relative, expected in bindings.items():
        actual = sha(root / relative)
        if actual != expected:
            binding_differences.append({"path": relative, "expected": expected, "actual": actual})
    inputs = read(HERE / "inputs.json")
    summary = read(HERE / "summary.json")
    old_raw = read(OLD / "history-comparison.json")
    old_adj = read(OLD / "adjusted-history-comparison.json")
    rows, source_issues = source_rows()
    input_differences = source_cross(rows, inputs, old_raw, old_adj)
    groups, by_year, group_differences = group_audit(rows, summary)
    hx = {r["period"]: r for r in read(HERE / "huaxia/reports.json")["reports"]}
    pdf_checks = pdf_spot_checks(hx)
    out = {"scope": "independent source and arithmetic audit only; no price/return/fit run",
           "source_bindings_checked": len(bindings), "source_binding_differences": binding_differences,
           "source_qualification_issues": source_issues,
           "input_reconstruction_differences": input_differences,
           "group_matrix_differences": group_differences,
           "independent_rows": len(rows),
           "independent_half_years": [{k: str(v) if isinstance(v, D) else v for k, v in row.items()} for row in rows],
           "independent_groups": groups,
           "independent_by_year": by_year, "huaxia_pdf_spot_checks": pdf_checks,
           "limits": ["two continuing funds and fourteen shared historical half-years",
                      "D_report is financial-statement fund-share transaction change, not verified outside cash",
                      "D_adjusted conditionally subtracts reinvestment under an accounting-structure inference",
                      "C0 is opening book bank money plus settlement reserve, not intra-half available liquidity",
                      "gross all-stock buys/sells exclude fees and cannot identify compelled sales",
                      "report publication after period end means no contemporaneous signal"]}
    (HERE / "independent-check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "binding_differences": len(binding_differences),
                      "source_issues": len(source_issues), "input_differences": len(input_differences),
                      "group_differences": len(group_differences), "pdf_spots": len(pdf_checks)}, ensure_ascii=False))
    if binding_differences or source_issues or input_differences or group_differences:
        raise ValueError("independent audit differs; see independent-check.json")


if __name__ == "__main__":
    main()
