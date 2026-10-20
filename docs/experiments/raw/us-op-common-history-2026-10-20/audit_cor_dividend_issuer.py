#!/usr/bin/env python3
"""Read-only local SEC/Yahoo source audit for COR ticker reuse and dividends."""
import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent
ZIP_PATH = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/us-op-common-history-20261020/us-op-common-history-20261020-20261020T191922-92db83e55b32/result/sources/sec-fsds-2020q4.zip")
OLD_RESULT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/stock-universe-us-20261015/stock-universe-us-20261015-20261015T194201-82eb0af53148/result")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows_from_zip(zf, member):
    with zf.open(member) as stream:
        yield from csv.DictReader((line.decode("utf-8") for line in stream), delimiter="\t")


def main():
    ledger_path = RAW / "http-ledger.jsonl"
    ledger_rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    zip_record = next((x for x in reversed(ledger_rows) if x.get("name") == ZIP_PATH.name), None)
    if not zip_record or zip_record.get("status") != 200:
        raise ValueError("no successful SEC ZIP record in local HTTP ledger")
    zip_sha = sha(ZIP_PATH)
    if zip_sha != zip_record.get("sha256"):
        raise ValueError("SEC ZIP SHA differs from download ledger")

    prior = json.loads((RAW / "luna-price-source-contract.json").read_text())
    old_attempts_path = OLD_RESULT / "attempts.jsonl"
    old_verification_path = OLD_RESULT / "verification.json"
    if sha(old_attempts_path) != prior["input_binding"]["old_attempts_sha256"]:
        raise ValueError("old attempts SHA mismatch")
    if sha(old_verification_path) != prior["input_binding"]["old_verification_sha256"]:
        raise ValueError("old verification SHA mismatch")
    old_attempts = [json.loads(line) for line in old_attempts_path.read_text().splitlines() if line.strip()]
    cor_attempt = next(x for x in old_attempts if x.get("code") == "COR" and x.get("status") == "ok")
    cor_file = OLD_RESULT / cor_attempt["file"]
    cor_sha = sha(cor_file)
    if cor_sha != cor_attempt.get("sha256"):
        raise ValueError("old saved COR original SHA mismatch")
    cor_result = (json.loads(cor_file.read_text())["chart"]["result"] or [None])[0]
    if not cor_result:
        raise ValueError("old saved COR original has no chart result")
    meta = cor_result.get("meta", {})
    params = cor_attempt.get("params", {})
    retrieved_events = []
    query_start = datetime.fromtimestamp(int(params["period1"]), timezone.utc).date().isoformat()
    for stamp, event in cor_result.get("events", {}).get("dividends", {}).items():
        date = datetime.fromtimestamp(int(stamp), timezone.utc).date().isoformat()
        if "2019-10-01" <= date <= "2020-09-30":
            retrieved_events.append({"date": date, "amount": float(event["amount"])})
    retrieved_events.sort(key=lambda x: x["date"])

    previous_contract = json.loads((RAW / "luna-price-action-contract.json").read_text())
    action_path = next(Path(x["path"]) for x in previous_contract["inputs"] if x["path"].endswith("johnbrick-corporate_action_overrides.csv"))
    action_sha_expected = next(x["sha256"] for x in previous_contract["inputs"] if x["path"].endswith("johnbrick-corporate_action_overrides.csv"))
    if sha(action_path) != action_sha_expected:
        raise ValueError("action overrides SHA mismatch")
    override_rows = [x for x in csv.DictReader(action_path.open(encoding="utf-8-sig")) if x.get("ticker") == "COR" and "2019-10-01" <= x.get("date", "") <= "2020-09-30"]

    target_adsh = "0001140859-20-000050"
    issuer_rows, core_rows = [], []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        bad_member = zf.testzip()
        if bad_member is not None:
            raise ValueError(f"SEC ZIP CRC failure: {bad_member}")
        members = set(zf.namelist())
        required = {"sub.txt", "num.txt", "pre.txt", "tag.txt"}
        if not required.issubset(members):
            raise ValueError(f"required SEC members missing: {sorted(required - members)}")
        sub_issuer = None
        sub_core = None
        for row in rows_from_zip(zf, "sub.txt"):
            if row.get("cik") == "1140859" and row.get("adsh") == target_adsh and row.get("form") == "10-K" and row.get("period") == "20200930":
                sub_issuer = {k: row.get(k) for k in ["adsh", "cik", "name", "form", "filed", "period", "fy", "fp", "accepted"]}
            if row.get("cik") == "1490892" and row.get("period") == "20200930" and row.get("form") in {"10-Q", "10-K"}:
                sub_core = {k: row.get(k) for k in ["adsh", "cik", "name", "form", "filed", "period", "fy", "fp", "accepted"]}
        if not sub_issuer:
            raise ValueError("original AmerisourceBergen 2020 10-K not found in SEC ZIP")

        tags_needed = set()
        for row in rows_from_zip(zf, "num.txt"):
            tag = row.get("tag", "")
            if row.get("adsh") != target_adsh:
                continue
            if "dividend" not in tag.lower() or "pershare" not in tag.lower():
                continue
            ddate = row.get("ddate", "")
            if not ("20191001" <= ddate <= "20200930"):
                continue
            tags_needed.add((tag, row.get("version", "")))
            issuer_rows.append({k: row.get(k) for k in ["adsh", "tag", "version", "ddate", "qtrs", "uom", "value", "coreg", "segments", "footnote"]})

        tag_labels = {}
        for row in rows_from_zip(zf, "tag.txt"):
            key = (row.get("tag", ""), row.get("version", ""))
            if key in tags_needed:
                tag_labels[key] = {k: row.get(k) for k in ["tag", "version", "custom", "datatype", "tlabel", "doc"]}

        for row in rows_from_zip(zf, "pre.txt"):
            if row.get("adsh") == target_adsh and ("dividend" in row.get("tag", "").lower() or "dividend" in row.get("plabel", "").lower()):
                core_rows.append({k: row.get(k) for k in ["adsh", "report", "line", "stmt", "inpth", "tag", "version", "plabel", "negating"]})

    for fact in issuer_rows:
        fact["sec_tag_definition"] = tag_labels.get((fact["tag"], fact["version"]))
    exact_annual = [x for x in issuer_rows if x["tag"] == "CommonStockDividendsPerShareCashPaid" and x["ddate"] == "20200930" and x["qtrs"] == "4"]
    old_observed_total = sum(x["amount"] for x in retrieved_events)
    false_dividend_dates = {"2020-03-30", "2020-06-29", "2020-09-29"}

    result = {
        "task_id": "cor-dividend-issuer-audit-20261020",
        "status": "completed_with_partial_old_event_coverage",
        "network_requests": 0,
        "financial_effect_or_strategy_performance_calculated": False,
        "sec_zip": {"path": str(ZIP_PATH), "ledger_status": zip_record.get("status"), "bytes": ZIP_PATH.stat().st_size, "sha256": zip_sha, "zip_crc": "passed", "required_members_present": sorted(required)},
        "sec_filing": {"issuer": sub_issuer, "core_site_comparison_issuer": sub_core, "cik_1140859_and_1490892_are_distinct": sub_issuer["cik"] != sub_core["cik"] if sub_core else None},
        "dividend_facts_in_sec_10k": {"query": "same accession; tags containing dividend and per-share; ddate 2019-10-01 through 2020-09-30", "matching_num_rows": issuer_rows, "matching_pre_rows": core_rows, "annual_cash_paid_qtrs4_20200930_found": exact_annual, "target_date_per_share_facts_found": [x for x in issuer_rows if x["ddate"] in {"2020-03-30", "2020-06-29", "2020-09-29", "20200330", "20200629", "20200929"}]},
        "old_yahoo_COR_original": {"path": str(cor_file), "sha256": cor_sha, "attempt_record": {k: cor_attempt.get(k) for k in ["code", "original_ticker", "returned_symbol", "url", "params", "retrieved_at", "file", "bytes", "sha256"]}, "metadata": {k: meta.get(k) for k in ["symbol", "longName", "shortName", "exchangeName", "currency", "dataGranularity"]}, "requested_event_window": {"start": "2019-10-01", "end": "2020-09-30"}, "query_event_coverage_start": query_start, "coverage_complete_for_requested_window": query_start <= "2019-10-01", "returned_dividend_events": retrieved_events, "sum_of_returned_events_only": old_observed_total, "full_window_total": old_observed_total if query_start <= "2019-10-01" else None, "missing_event_coverage": None if query_start <= "2019-10-01" else {"start": "2019-10-01", "end": "2019-12-31", "reason": "saved query begins 2020-01-01; unavailable events are unknown, not zero"}},
        "new_vendor_overrides": {"path": str(action_path), "sha256": action_sha_expected, "matching_COR_override_rows": override_rows, "CoreSite_date_old_events_amount_sum": sum(x["amount"] for x in retrieved_events if x["date"] in false_dividend_dates), "issuer_annual_cash_paid_per_share": exact_annual[0]["value"] if exact_annual else None},
        "interpretation_boundary": "The saved data show ticker reuse contamination: the old Yahoo object is labeled COR/Cencora yet carries CoreSite-sized $1.22 distributions on three matching ex-dates, and the saved override table zeros those dates. The 2020 AmerisourceBergen 10-K reports annual common dividends paid of $1.6600 per share (qtrs=4, ddate 20200930). This supports the issuer-mismatch diagnosis; it does not independently verify each ex-date or the full legal distribution history. Missing 2019 Q4 old Yahoo events are unknown, never treated as zero.",
        "input_hashes": {"http_ledger": sha(ledger_path), "sec_zip": zip_sha, "old_attempts": sha(old_attempts_path), "old_verification": sha(old_verification_path), "old_COR_json": cor_sha, "override_csv": action_sha_expected},
    }
    return result


if __name__ == "__main__":
    started_at = datetime.now().astimezone().isoformat()
    audit = main()
    audit_path = RAW / "cor-dividend-issuer-audit.json"
    if audit_path.exists():
        raise FileExistsError(f"refuse to overwrite {audit_path}")
    audit["execution"] = {"started_at": started_at, "completed_at": datetime.now().astimezone().isoformat(), "script_sha256": sha(Path(__file__))}
    with audit_path.open("x", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    readback = json.loads(audit_path.read_text())
    print(json.dumps({"audit_path": str(audit_path), "audit_sha256": sha(audit_path), "bytes": audit_path.stat().st_size, "zip_crc": readback["sec_zip"]["zip_crc"], "issuer": readback["sec_filing"]["issuer"], "annual_cash_paid_per_share": readback["new_vendor_overrides"]["issuer_annual_cash_paid_per_share"], "old_returned_event_sum_partial": readback["old_yahoo_COR_original"]["sum_of_returned_events_only"], "old_window_complete": readback["old_yahoo_COR_original"]["coverage_complete_for_requested_window"]}, ensure_ascii=False))
