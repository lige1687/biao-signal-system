"""Resume independent months after the diagnosed 2017-01 source-content gap.

This leaves the original downloader and its recorded stop/failure untouched.
"""

import hashlib
import json
from pathlib import Path

import acquire_months as original


FAILS = {"failed_http", "failed_exception", "failed_validation", "redirect"}


def reserve_after_diagnosis(ledger, month, url):
    op = original.canonical(month)
    if len(ledger["requests"]) != ledger["public_http_actions_used"]:
        raise RuntimeError("ledger count mismatch")
    if any(x["status"] == "pending" for x in ledger["requests"]):
        raise RuntimeError("pending request requires diagnosis")
    if ledger.get("current_route_stop"):
        raise RuntimeError("current route stopped")
    if ledger["public_http_actions_used"] >= original.BUDGET["public_http_actions_max"]:
        raise RuntimeError("global HTTP cap")
    if sum(x["canonical_semantic_operation"] == op for x in ledger["requests"]) >= original.BUDGET["same_month_semantic_operation_max"]:
        raise RuntimeError("same-month cap")
    if len(ledger["requests"]) >= 2 and all(x["status"] in FAILS for x in ledger["requests"][-2:]):
        raise RuntimeError("two consecutive source-availability/content failures")
    n = ledger["public_http_actions_used"] + 1
    row = {"n": n, "month": month, "canonical_semantic_operation": op, "url": url,
           "status": "pending", "started_at_utc": original.utc_now(), "measurable_response_bytes": 0}
    ledger["requests"].append(row)
    ledger["public_http_actions_used"] = n
    original.write_json(original.LEDGER, ledger)
    return row


def record_diagnosis_resume():
    ledger = json.loads(original.LEDGER.read_text())
    rows = ledger["requests"]
    prior = next((r for r in rows if r["n"] == 13), None)
    assert prior and prior["month"] == "2017-01" and prior["status"] == "failed_validation"
    assert prior["body_sha256"] == "ecb169288a2a9c6a21eadd90d3047243dd28498436568f2d0499b756edf7eae3"
    assert ledger["stop_reason"] == "month 2017-01 failed; diagnose before any retry"
    assert not any(x["month"] == "2017-01" and x["n"] != 13 for x in rows)
    assert ledger["public_http_actions_used"] == len(rows)
    if not ledger.get("diagnosis_resume_events"):
        ledger["diagnosis_resume_events"] = [{
            "at_utc": original.utc_now(),
            "authority": "root confirmed independent fixed months may continue after 2017-01 diagnosed content gap",
            "failed_request_n": 13,
            "missing_date": "2017-01-01",
            "failed_month_remains_unqualified": True,
            "historical_stop_reason_preserved": ledger["stop_reason"],
            "next_independent_month": "2017-02",
            "prior_program": str(original.ROOT / "acquire_months.py"),
            "prior_program_sha256": hashlib.sha256((original.ROOT / "acquire_months.py").read_bytes()).hexdigest(),
        }]
        original.write_json(original.LEDGER, ledger)


def main():
    original.preflight()
    record_diagnosis_resume()
    original.reserve = reserve_after_diagnosis
    for month in original.MONTHS:
        if month <= "2017-01":
            continue
        ledger = json.loads(original.LEDGER.read_text())
        if any(r["month"] == month and r["status"] == "qualified_month_source" for r in ledger["requests"]):
            continue
        row = original.fetch_one(month)
        print(json.dumps({k: row.get(k) for k in ("n", "month", "status", "natural_days", "trading_days", "measurable_response_bytes", "error")}, ensure_ascii=False), flush=True)
        if row["status"] != "qualified_month_source":
            ledger = json.loads(original.LEDGER.read_text())
            ledger["current_route_stop"] = f"month {month} failed; diagnose before any further request"
            original.write_json(original.LEDGER, ledger)
            break


if __name__ == "__main__":
    main()
