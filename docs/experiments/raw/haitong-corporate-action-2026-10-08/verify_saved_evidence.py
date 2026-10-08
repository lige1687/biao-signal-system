"""Read-only verification of this factual qualification; no network or model fit."""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def verify(repo: Path):
    raw = repo / "docs/experiments/raw/haitong-corporate-action-2026-10-08"
    facts = json.loads((raw / "qualified-facts.json").read_text())
    manifest = json.loads((raw / "source-manifest.json").read_text())
    missing = []
    checks = []
    for source in manifest["sources"]:
        p = raw / source["filename"]
        if not p.exists():
            missing.append(str(p.relative_to(repo)))
            continue
        checks.append({"check": source["filename"] + " original hash", "passed": hashlib.sha256(p.read_bytes()).hexdigest() == source["sha256"]})
    for source in manifest["failed_original_pdf_responses"]:
        p = raw / source["filename"]
        if p.exists():
            checks.append({"check": source["filename"] + " preserved failure", "passed": hashlib.sha256(p.read_bytes()).hexdigest() == source["sha256"] and not p.read_bytes().startswith(b"%PDF-")})
    expected = {
        "S1-termination.html": ["2025年3月4日", "600837"],
        "S4-conversion-result.extracted.txt": ["2025年3月17日", "2025年3月13日", "5,985,871,332", "9,577,556,713", "77,074,467", "626,174,076", "601211"],
        "S5-suspension.html.extracted.txt": ["2025年2月5日为公司股票最后一个交易日", "2025年2月6日"],
        "S6-conversion-plan.html.extracted.txt": ["2025年3月3日", "0.62", "13.83", "8.57", "随机"],
    }
    for name, tokens in expected.items():
        p = raw / name
        if p.exists():
            text = p.read_text()
            checks.append({"check": name + " source anchors", "passed": all(t in text for t in tokens)})
    c = facts["conversion"]
    total_old = Decimal(c["holder_old_shares"]) + Decimal(c["treasury_old_shares"])
    continuous = total_old * Decimal(c["new_shares_per_old_share"])
    actual = Decimal(c["actual_new_conversion_A_shares"])
    reference_ratio = (Decimal(c["reference_prices"]["old_CNY"]) / Decimal(c["reference_prices"]["new_CNY"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    checks.append({"check": "reference ratio rounds to disclosed 0.62", "passed": reference_ratio == Decimal("0.62")})
    checks.append({"check": "aggregate conversion arithmetic consistent within one integer share", "passed": total_old == 9654631180 and continuous == Decimal("5985871331.60") and actual-continuous == Decimal("0.40")})
    vendor_rel = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/normalized/daily_raw/daily-2-sh-600837.json"
    vp = repo / vendor_rel
    vendor = None
    if vp.exists():
        digest = hashlib.sha256(vp.read_bytes()).hexdigest()
        checks.append({"check": "B01 exact frozen daily source", "passed": digest == "3595b420f1831cbd51a298482c18bd2c88d3c2fd413162ebb6e9887fc27c82ae"})
        rows = json.loads(vp.read_text())["records"]
        post = [r for r in rows if r["date"] >= "2025-02-06"]
        vendor = {"path": vendor_rel, "sha256": digest, "rows": len(rows), "last_status1_date": max(r["date"] for r in rows if r["tradestatus"] == "1"), "post_suspension_rows": len(post), "pre_termination_placeholder_rows": sum(r["date"] < "2025-03-04" for r in post), "on_termination_placeholder_rows": sum(r["date"] == "2025-03-04" for r in post), "all_post_rows_status0_empty_volume_and_amount": all(r["tradestatus"] == "0" and r["volume"] == r["amount"] == "" for r in post), "earlier_status0_outside_this_unit": sum(r["date"] < "2025-02-06" and r["tradestatus"] == "0" for r in rows)}
        checks.append({"check": "2025 vendor placeholders match disclosed trading cessation", "passed": vendor["last_status1_date"] == "2025-02-05" and len(post) == 19 and vendor["all_post_rows_status0_empty_volume_and_amount"]})
    else:
        missing.append(vendor_rel)
    return {"schema": "saved-evidence-verification/1.0", "status": "passed_local_factual_checks" if all(c["passed"] for c in checks) and not missing else "incomplete_or_failed", "checks": checks, "missing_local_sources": missing, "conversion_arithmetic": {"total_old_shares": str(total_old), "continuous_new_share_entitlement": str(continuous), "actual_new_shares": str(actual), "integer_total_difference": str(actual-continuous), "100_old_shares_entitlement": str(Decimal(100)*Decimal("0.62")), "one_old_share_entitlement": "0.62", "one_old_share_actual_allocation": "unknown; not deterministic account rounding", "interpretation": "Aggregate consistency only, not proof of individual account allocation."}, "vendor_crosscheck": vendor, "independent_agent_review": False, "engine_integration": False, "new_market_calculations": 0}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    result = verify(args.repo)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed_local_factual_checks" else 2)
