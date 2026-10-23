"""Derive each half-year's disclosed-share and net-asset-transaction pressure.

H2 entries are annual cumulative minus H1 cumulative; no securities returns.
"""

import csv
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).parent
Q = json.loads((ROOT / "qualification.json").read_text())
OUT = Path(json.loads((ROOT.parent / "storage-plan.json").read_text())["output"]) / "jiashi-history"
D = Decimal


def item(year, half, kind, ann_date, opening, subs, reds, closing, open_nav, sub_cny, red_cny, sources):
    net_units = reds - subs
    net_cny = -(sub_cny + red_cny)
    assert opening + subs - reds == closing
    return {"year": year, "half": half, "kind": kind, "period_end": f"{year}-{'06-30' if half == 1 else '12-31'}",
            "announcement_date": ann_date, "opening_units": str(opening), "subscriptions_units": str(subs),
            "redemptions_units": str(reds), "closing_units": str(closing),
            "net_redeemed_units": str(net_units), "net_redeemed_share_fraction_numerator": str(net_units),
            "net_redeemed_share_fraction_denominator": str(opening),
            "opening_net_assets_cny": str(open_nav), "subscription_net_asset_change_cny": str(sub_cny),
            "redemption_net_asset_change_cny_signed": str(red_cny),
            "net_redeemed_net_asset_change_cny": str(net_cny),
            "net_redeemed_net_asset_fraction_numerator_cny": str(net_cny),
            "net_redeemed_net_asset_fraction_denominator_cny": str(open_nav),
            "source_periods": sources,
            "definition": "Net-asset change from fund share transactions, not direct investor cash; H2 equals full year minus H1. Net redeemed may be negative."}


def main():
    assert Q["periods_passed"] == 14
    reports = {r["period"]: r for r in Q["reports"]}
    periods = []
    for year in range(2019, 2026):
        h, f = (reports[f"{year}{suffix}"] for suffix in ("H1", "FY"))
        assert D(h["opening_units"]) == D(f["opening_units"])
        assert D(h["opening_net_assets_cny"]) == D(f["opening_net_assets_cny"])
        periods.append(item(year, 1, "direct H1", h["official_pub_date"], D(h["opening_units"]),
                            D(h["subscriptions_units"]), D(h["redemptions_units"]), D(h["closing_units"]),
                            D(h["opening_net_assets_cny"]), D(h["subscription_net_asset_change_cny"]),
                            D(h["redemption_net_asset_change_cny"]), [f"{year}H1"]))
        periods.append(item(year, 2, "FY minus H1", f["official_pub_date"], D(h["closing_units"]),
                            D(f["subscriptions_units"]) - D(h["subscriptions_units"]),
                            D(f["redemptions_units"]) - D(h["redemptions_units"]), D(f["closing_units"]),
                            D(h["closing_net_assets_cny"]),
                            D(f["subscription_net_asset_change_cny"]) - D(h["subscription_net_asset_change_cny"]),
                            D(f["redemption_net_asset_change_cny"]) - D(h["redemption_net_asset_change_cny"]),
                            [f"{year}H1", f"{year}FY"]))
    compact = []
    for r in Q["reports"]:
        compact.append({"key": r["period"], "period_end": r["period_end"], "announcement_date": r["official_pub_date"],
                        "stock_assets_cny": r["stock_assets_cny"], "holdings_rows": r["holdings_rows"],
                        "pdf_path": r["pdf_path"], "pdf_sha256": r["pdf_sha256"],
                        "holdings_csv": str(OUT / f"070002-{r['period']}-all-stocks.csv"),
                        "flow": {k: r[k] for k in ("opening_units", "subscriptions_units", "redemptions_units", "closing_units")},
                        "financial": {k: r[k] for k in ("opening_net_assets_cny", "closing_net_assets_cny", "subscription_net_asset_change_cny", "redemption_net_asset_change_cny", "cash_or_bank_deposits_cny")},
                        "source_pages_1based": r["source_pages_1based"]})
    out = {"fund_code": "070002", "fund_name": "嘉实增长开放式证券投资基金", "reports": compact,
           "half_years": periods, "scope": "14 complete H1/FY holdings observations and 14 half-year flow periods, 2019-2025; no security returns or fund performance computed"}
    (ROOT / "history-series.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    all_csv = OUT / "070002-history-holdings.csv"
    with all_csv.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in Q["reports"]:
        selected = [x for x in rows if x["period_end"] == r["period_end"]]
        assert len(selected) == r["holdings_rows"]
        with (OUT / f"070002-{r['period']}-all-stocks.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(selected)
    print(json.dumps({"reports": len(compact), "half_years": len(periods), "holdings_rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
