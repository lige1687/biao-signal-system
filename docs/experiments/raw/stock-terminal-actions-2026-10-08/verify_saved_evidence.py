"""Read-only checks for two fixed terminal-action evidence packages; no network."""
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path


def verify(repo):
    raw = repo / "docs/experiments/raw/stock-terminal-actions-2026-10-08"
    facts = json.loads((raw / "qualified-facts.json").read_text())
    manifest = json.loads((raw / "source-manifest.json").read_text())
    checks, missing = [], []
    anchors = {
        "A1-cash-terms.html": ["2025-032", "3.54元/股", "2025年4月22日", "2025年4月3日"],
        "A2-termination.html": ["中航工业产融", "予以终止上市"],
        "A3-cash-settlement.pdf": ["2025-038", "4,134,072,543", "股份已过户", "资金将在5个工作日内"],
        "A4-delisting-effective.pdf": ["2025-047", "2025年5月27日", "不进入退市整理期"],
        "A5-final-trading-schedule.pdf": ["2025-023", "投资者可于2025年4月2日（星期三）正常交易本公司股票", "2025年4月3日（星期四）开市起停牌"],
        "C1-suspension.pdf": ["临2025-052", "2025年8月12日为公司股票最后一个交易日", "2025年8月13日", "随机"],
        "C2-termination.html": ["601989", "2025年9月5日"],
        "C3-conversion-result.html": ["600150", "2025-069", "0.1339", "2025年9月4日", "2025年9月11日", "2025年9月16日", "22,802,035,324", "3,053,192,530", "1,454,168,398", "6个月内不得转让"],
    }
    for s in manifest["sources"]:
        p = raw / s["filename"]
        if not p.exists():
            missing.append(str(p.relative_to(repo)))
            continue
        checks.append({"check": s["filename"] + " source hash", "passed": hashlib.sha256(p.read_bytes()).hexdigest() == s["sha256"]})
        t = raw / (s["filename"] + ".txt")
        if not t.exists():
            missing.append(str(t.relative_to(repo)))
            continue
        checks.append({"check": s["filename"] + " extracted hash", "passed": hashlib.sha256(t.read_bytes()).hexdigest() == s["extracted_sha256"]})
        norm = re.sub(r"\s+", "", t.read_text()).replace("\x00", "")
        checks.append({"check": s["filename"] + " scoped factual anchors", "passed": all(v in norm for v in anchors[s["filename"]])})
    ship = facts["601989"]
    continuous = Decimal(ship["actual_old_shares"]) * Decimal(ship["new_shares_per_old_share"])
    diff = Decimal(ship["actual_new_shares"]) - continuous
    checks.append({"check": "ship aggregate conversion arithmetic", "passed": continuous == Decimal("3053192529.8836") and diff == Decimal("0.1164")})
    nominal_cash = Decimal(facts["600705"]["cash_election"]["actual_validly_declared_shares"]) * Decimal("3.54")
    checks.append({"check": "cash arithmetic and no invented credit date", "passed": nominal_cash == Decimal("14634616802.22") and facts["600705"]["cash_election"]["actual_cash_credit_date"] is None and not facts["600705"]["automatic_redemption"]})
    rel = "docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/run-01/normalized/daily_raw/daily-3-sh-601989.json"
    vp = repo / rel
    vendor = None
    if vp.exists():
        digest = hashlib.sha256(vp.read_bytes()).hexdigest()
        checks.append({"check": "original B01 ship source hash", "passed": digest == "2c8f857954d527c93089d9e80358ac8e837c2fe9e69fb654d35c2ff2b7528bd1"})
        rows = json.loads(vp.read_text())["records"]
        post = [r for r in rows if r["date"] >= "2025-08-13"]
        vendor = {"path": rel, "sha256": digest, "total_rows": len(rows), "post_suspension_rows": len(post), "first_placeholder": post[0]["date"], "last_placeholder": post[-1]["date"], "last_status1_date": max(r["date"] for r in rows if r["tradestatus"] == "1"), "all_post_status0_empty_turnover": all(r["tradestatus"] == "0" and r["volume"] == r["amount"] == "" for r in post)}
        checks.append({"check": "17 ship placeholders align with official halt", "passed": vendor["last_status1_date"] == "2025-08-12" and len(post) == 17 and vendor["all_post_status0_empty_turnover"]})
    else:
        missing.append(rel)
    return {"status": "passed_local_factual_checks" if not missing and all(c["passed"] for c in checks) else "incomplete_or_failed", "checks": checks, "missing_local_sources": missing, "arithmetic": {"ship_continuous_entitlement": str(continuous), "ship_actual_integer_issue_difference": str(diff), "ship_specified_locked_shares": "1454168398", "ship_remaining_shares_before_other_holder_restrictions": str(Decimal("3053192530")-Decimal("1454168398")), "cash_nominal_gross_all_valid_applications_CNY": str(nominal_cash), "cash_actual_net_account_receipts": "unknown; announcement states future credit within five working days"}, "vendor_crosscheck": vendor, "new_fits": 0, "new_labels": 0, "price_repairs": 0, "independent_agent_review": False, "source_limits": "Original source files and vendor observations are local only; missing originals must not pass in pure Git recovery."}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    result = verify(p.parse_args().repo)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed_local_factual_checks" else 2)
