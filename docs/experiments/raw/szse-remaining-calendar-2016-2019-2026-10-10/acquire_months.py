"""Bounded, synchronous acquisition of the frozen 44 SZSE calendar months."""

import argparse
import calendar
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "executor-contract.json").read_text())
PLAN = CONTRACT["output_plan"]
BUDGET = CONTRACT["budgets"]
RUN = Path(PLAN["run_directory"])
LEDGER = ROOT / "request-ledger.json"
MANIFEST = ROOT / "source-manifest.json"
MONTHS = CONTRACT["fixed_months"]
EXPECTED_OPS = {m: f"szse-month-{m}" for m in MONTHS}
assert set(EXPECTED_OPS.values()) == set(CONTRACT["canonical_semantic_operation_enum"])


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def preflight():
    assert RUN.is_dir() and Path(PLAN["output"]).is_dir()
    assert os.stat(RUN).st_dev == PLAN["external_device"]
    assert os.path.realpath(RUN).startswith(os.path.realpath(PLAN["external_mount"]) + os.sep)
    ex = os.statvfs(RUN)
    inside = os.statvfs(ROOT)
    assert ex.f_bavail * ex.f_frsize >= PLAN["external_reserve_bytes"] + PLAN["estimated_bytes"]
    assert inside.f_bavail * inside.f_frsize >= PLAN["internal_reserve_bytes"] + PLAN["internal_metadata_bytes"]
    # The separate storage probe must check the fixed UUID immediately before running.


def new_records():
    return {
        "schema": "szse-remaining44-request-ledger.v1",
        "contract_sha256": hashlib.sha256((ROOT / "executor-contract.json").read_bytes()).hexdigest(),
        "external_run": str(RUN),
        "requests": [],
        "public_http_actions_used": 0,
        "measurable_saved_response_bytes": 0,
        "redirects_followed": 0,
        "stop_reason": None,
    }, {
        "schema": "szse-remaining44-source-manifest.v1",
        "contract_sha256": hashlib.sha256((ROOT / "executor-contract.json").read_bytes()).hexdigest(),
        "sources": [],
    }


def initialize():
    if LEDGER.exists() or MANIFEST.exists():
        assert LEDGER.exists() and MANIFEST.exists(), "one record missing"
        return
    ledger, manifest = new_records()
    write_json(LEDGER, ledger)
    write_json(MANIFEST, manifest)


def canonical(month):
    if month not in EXPECTED_OPS:
        raise ValueError("month outside frozen enum")
    return EXPECTED_OPS[month]


def validate_month(month, body):
    data = json.loads(body)
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise ValueError("missing old data list")
    actual = {}
    for row in data["data"]:
        if not isinstance(row, dict) or not {"jyrq", "jybz", "zrxh"}.issubset(row):
            raise ValueError("old source fields missing")
        day = row["jyrq"]
        try:
            parsed = dt.date.fromisoformat(day)
        except (ValueError, TypeError):
            raise ValueError("invalid calendar date")
        if parsed.strftime("%Y-%m") != month:
            raise ValueError("wrong year or month")
        if day in actual:
            raise ValueError("duplicate date")
        if row["jybz"] not in ("0", "1"):
            raise ValueError("invalid flag")
        actual[day] = row["jybz"]
    year, number = map(int, month.split("-"))
    expected = {f"{month}-{day:02d}" for day in range(1, calendar.monthrange(year, number)[1] + 1)}
    if set(actual) != expected:
        raise ValueError("missing or extraneous natural date")
    return actual


def reserve(ledger, month, url):
    op = canonical(month)
    if len(ledger["requests"]) != ledger["public_http_actions_used"]:
        raise RuntimeError("ledger count mismatch")
    if any(x["status"] == "pending" for x in ledger["requests"]):
        raise RuntimeError("pending prior request requires diagnosis")
    if ledger["stop_reason"]:
        raise RuntimeError("route stopped: " + str(ledger["stop_reason"]))
    if ledger["public_http_actions_used"] >= BUDGET["public_http_actions_max"]:
        raise RuntimeError("global HTTP cap")
    if sum(x["canonical_semantic_operation"] == op for x in ledger["requests"]) >= BUDGET["same_month_semantic_operation_max"]:
        raise RuntimeError("same-month cap")
    if len(ledger["requests"]) >= 2 and all(x["status"] in ("failed_http", "failed_exception", "failed_validation", "redirect") for x in ledger["requests"][-2:]):
        raise RuntimeError("two consecutive source-availability failures")
    n = ledger["public_http_actions_used"] + 1
    row = {"n": n, "month": month, "canonical_semantic_operation": op, "url": url,
           "status": "pending", "started_at_utc": utc_now(), "measurable_response_bytes": 0}
    ledger["requests"].append(row)
    ledger["public_http_actions_used"] = n
    write_json(LEDGER, ledger)
    return row


def fetch_one(month):
    preflight()
    ledger = json.loads(LEDGER.read_text())
    manifest = json.loads(MANIFEST.read_text())
    url = CONTRACT["source_url_template"].replace("{YYYY-MM}", month)
    parts = urlparse(url)
    assert parts.scheme == "http" and parts.hostname == "www.szse.cn"
    assert parts.path == "/api/report/exchange/onepersistenthour/monthList"
    assert parts.query == f"month={month}&random=0.1"
    row = reserve(ledger, month, url)
    body_path = RUN / f"{row['n']:02d}-szse-{month}.json"
    headers_path = RUN / f"{row['n']:02d}-szse-{month}.headers.json"
    digest = hashlib.sha256()
    size = 0
    try:
        session = requests.Session()
        session.trust_env = False
        with session.get(url, stream=True, allow_redirects=False, timeout=(10, 30)) as response:
            write_json(headers_path, {"requested_url": url, "response_url": response.url,
                                      "http_status": response.status_code, "headers": dict(response.headers)})
            row["http_status"] = response.status_code
            row["response_url"] = response.url
            row["redirect_location"] = response.headers.get("Location")
            with body_path.open("wb") as output:
                for chunk in response.iter_content(16384):
                    if not chunk:
                        continue
                    if size + len(chunk) > BUDGET["per_response_bytes_max"]:
                        raise ValueError("per-response byte cap")
                    if ledger["measurable_saved_response_bytes"] + size + len(chunk) > BUDGET["saved_raw_response_bytes_max"]:
                        raise ValueError("aggregate raw byte cap")
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if 300 <= response.status_code < 400:
                row["status"] = "redirect"
                raise RuntimeError("manual redirect review required; no automatic follow")
            if response.status_code != 200:
                row["status"] = "failed_http"
                raise RuntimeError("non-200 source response")
        flags = validate_month(month, body_path.read_bytes())
        row["status"] = "qualified_month_source"
        row["natural_days"] = len(flags)
        row["trading_days"] = sum(v == "1" for v in flags.values())
    except Exception as exc:
        if row["status"] == "pending":
            row["status"] = "failed_validation" if isinstance(exc, (ValueError, json.JSONDecodeError)) else "failed_exception"
        row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    row["measurable_response_bytes"] = size
    row["body_path"] = str(body_path) if body_path.exists() else None
    row["headers_path"] = str(headers_path) if headers_path.exists() else None
    row["body_sha256"] = digest.hexdigest() if body_path.exists() else None
    row["finished_at_utc"] = utc_now()
    ledger["measurable_saved_response_bytes"] += size
    write_json(LEDGER, ledger)
    if body_path.exists():
        manifest["sources"].append({"n": row["n"], "month": month,
                                    "canonical_semantic_operation": canonical(month),
                                    "url": url, "status": row["status"], "http_status": row.get("http_status"),
                                    "body_path": str(body_path), "headers_path": str(headers_path),
                                    "bytes": size, "sha256": digest.hexdigest(),
                                    "natural_days": row.get("natural_days"), "trading_days": row.get("trading_days")})
        write_json(MANIFEST, manifest)
    return row


def self_test():
    month = "2016-02"
    good = {"data": [{"zrxh": 1, "jybz": "0", "jyrq": f"2016-02-{d:02d}"} for d in range(1, 30)], "nowdate": "2026-10-10"}
    assert len(validate_month(month, json.dumps(good))) == 29
    for bad in ["2015-02", "2016-02x"]:
        try: canonical(bad)
        except ValueError: pass
        else: raise AssertionError("bad operation passed")
    broken = []
    x = json.loads(json.dumps(good)); x["data"][0]["jyrq"] = "2026-02-01"; broken.append(x)
    x = json.loads(json.dumps(good)); x["data"].pop(); broken.append(x)
    x = json.loads(json.dumps(good)); x["data"][1]["jyrq"] = x["data"][0]["jyrq"]; broken.append(x)
    x = json.loads(json.dumps(good)); x["data"][0]["jybz"] = "2"; broken.append(x)
    for x in broken:
        try: validate_month(month, json.dumps(x))
        except ValueError: pass
        else: raise AssertionError("bad calendar passed")
    fake = {"requests": [{"status": "failed_exception", "canonical_semantic_operation": canonical(month)} for _ in range(2)],
            "public_http_actions_used": 2, "stop_reason": None}
    try: reserve(fake, month, "test://never-dispatched")
    except RuntimeError: pass
    else: raise AssertionError("same-month cap passed")
    print("self-test passed: wrong-year, missing, duplicate, flag, canonical, attempt cap")


def run():
    preflight()
    initialize()
    for month in MONTHS:
        ledger = json.loads(LEDGER.read_text())
        if any(r["month"] == month and r["status"] == "qualified_month_source" for r in ledger["requests"]):
            continue
        row = fetch_one(month)
        print(json.dumps({k: row.get(k) for k in ("n", "month", "status", "natural_days", "trading_days", "measurable_response_bytes", "error")}, ensure_ascii=False), flush=True)
        if row["status"] != "qualified_month_source":
            ledger = json.loads(LEDGER.read_text())
            ledger["stop_reason"] = f"month {month} failed; diagnose before any retry"
            write_json(LEDGER, ledger)
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["self-test", "run"])
    args = parser.parse_args()
    if args.mode == "self-test": self_test()
    else: run()
