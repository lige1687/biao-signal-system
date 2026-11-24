"""Bounded same-supplier retrieval for the frozen 300-stock focus observation.

This module acquires source responses only. It never calculates or publishes a
focus value, and never changes an earlier raw response or frozen bundle.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import signal
import socket
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from lei_signal.research.fip import SOURCE_FIELDS
from lei_signal.research.high52_revalidation import ADJUSTMENT_FIELDS
from lei_signal.research.output_storage import plan_output

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "docs/experiments/raw/focus-stock-momentum-evaluation-2026-10-25"
STAGE = ROOT / "docs/ops/focus-live-and-erp-thresholds-20261102/reopen-home-20261102/data"
EXTERNAL_PARENT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/focus-recent-20261102")
DATES = ("2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02")
PRICE_START, END = DATES[0], DATES[-1]
FACTOR_START = "2026-10-24"
TIMEOUT_SECONDS = 15
MAX_LOGIN_ATTEMPTS = 2
MAX_QUERY_REQUESTS = 600
MAX_CONSECUTIVE_ERRORS = 3
MAX_RAW_BYTES = 100_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixed_codes() -> tuple[list[str], str]:
    inputs = json.loads((OLD / "inputs.json").read_text())
    ref = inputs["source_manifest"]
    path = Path(ref["path"])
    if not path.resolve().is_relative_to("/Volumes/win+mac通用"):
        raise ValueError("manifest outside registered external storage")
    raw = path.read_bytes()
    if sha256(raw) != ref["sha256"]:
        raise ValueError("frozen manifest SHA mismatch")
    assets = json.loads(raw)["asset_sources"]
    codes = sorted(assets)
    if len(codes) != 300 or len(set(codes)) != 300:
        raise ValueError("frozen cohort is not 300 unique codes")
    return codes, ref["sha256"]


@contextmanager
def hard_socket_timeout(seconds: int = TIMEOUT_SECONDS):
    """Bound each BaoStock operation, including a stuck connect or recv."""
    original_socket = socket.socket
    previous_handler = signal.getsignal(signal.SIGALRM)

    def bounded_socket(*args, **kwargs):
        sock = original_socket(*args, **kwargs)
        sock.settimeout(seconds)
        return sock

    def on_timeout(_signum, _frame):
        raise TimeoutError(f"BaoStock operation exceeded {seconds}s")

    socket.socket = bounded_socket
    signal.signal(signal.SIGALRM, on_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        socket.socket = original_socket


def collect_response(result, code: str, fields: tuple[str, ...], kind: str) -> dict:
    if str(result.error_code) != "0":
        raise ValueError(f"supplier error {result.error_code}: {result.error_msg}")
    found = result.fields.split(",") if isinstance(result.fields, str) else result.fields
    if list(found) != list(fields):
        raise ValueError(f"{kind} field mismatch: {found}")
    rows = []
    while result.next():
        row = result.get_row_data()
        if len(row) != len(fields):
            raise ValueError(f"{kind} row width mismatch for {code}")
        if (row[1] if kind == "daily" else row[0]) != code:
            raise ValueError(f"{kind} source code mismatch for {code}")
        day = row[0] if kind == "daily" else row[1]
        lo = PRICE_START if kind == "daily" else FACTOR_START
        if not lo <= day <= END:
            raise ValueError(f"{kind} source date out of requested range for {code}: {day}")
        if rows and day <= (rows[-1][0] if kind == "daily" else rows[-1][1]):
            raise ValueError(f"{kind} unordered or duplicate dates for {code}")
        rows.append(row)
    return {"method": "query_history_k_data_plus" if kind == "daily" else "query_adjust_factor",
            "error_code": "0", "error_msg": str(result.error_msg),
            "fields": list(fields), "data": rows,
            "query": {"code": code, "start_date": PRICE_START if kind == "daily" else FACTOR_START,
                      "end_date": END, **({"frequency": "d", "adjustflag": "3"} if kind == "daily" else {})}}


def save_response(directory: Path, code: str, kind: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    compressed = gzip.compress(body, mtime=0)
    name = f"{kind}-{code.replace('.', '-')}.json.gz"
    path = directory / name
    with path.open("xb") as stream:
        stream.write(compressed)
        stream.flush()
        os.fsync(stream.fileno())
    return {"code": code, "kind": kind, "path": str(path),
            "compressed_sha256": sha256(compressed), "payload_sha256": sha256(body),
            "rows": len(payload["data"]), "bytes": len(compressed)}


def coverage(responses: list[dict], raw_dir: Path, codes: list[str]) -> dict:
    by_date = {day: {"quotedCodes": 0, "validAmountCodes": 0, "zeroAmountCodes": 0,
                     "nonTradingCodes": 0} for day in DATES}
    daily_codes = set()
    factor_codes = set()
    factor_events = 0
    for ref in responses:
        if ref["kind"] == "factor":
            factor_codes.add(ref["code"])
            factor_events += ref["rows"]
            continue
        daily_codes.add(ref["code"])
        with gzip.open(raw_dir / Path(ref["path"]).name, "rt") as stream:
            payload = json.load(stream)
        for row in payload["data"]:
            day = row[0]
            if day not in by_date:
                continue
            item = by_date[day]
            item["quotedCodes"] += 1
            amount = row[SOURCE_FIELDS.index("amount")]
            status = row[SOURCE_FIELDS.index("tradestatus")]
            if status != "1":
                item["nonTradingCodes"] += 1
            try:
                numeric = float(amount)
            except (TypeError, ValueError):
                numeric = -1
            if math.isfinite(numeric) and numeric > 0 and status == "1":
                item["validAmountCodes"] += 1
            elif numeric == 0:
                item["zeroAmountCodes"] += 1
    for item in by_date.values():
        item["noQuoteRowAmongSuccessfulDailyCodes"] = len(daily_codes) - item["quotedCodes"]
    return {"dailyQuerySuccessCodes": len(daily_codes), "factorQuerySuccessCodes": len(factor_codes),
            "dailyQueryFailedCodes": sorted(set(codes) - daily_codes),
            "factorQueryFailedCodes": sorted(set(codes) - factor_codes),
            "factorEventRows": factor_events, "byDate": by_date}


def run() -> dict:
    import baostock as bs
    from baostock.common import context

    codes, manifest_sha = fixed_codes()
    plan = plan_output(ROOT, "focus-recent-20261102", MAX_RAW_BYTES, internal_bytes=5_000_000)
    run_dir = Path(plan["run_directory"])
    if run_dir.parent != EXTERNAL_PARENT or run_dir.exists() or STAGE.exists():
        raise ValueError("output is not a fresh authorized location")
    raw_dir = run_dir / "result" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=False)
    STAGE.mkdir(parents=True, exist_ok=False)
    ledger = {"startedAt": datetime.now(timezone.utc).isoformat(), "storagePlan": plan,
              "fixedManifestSha256": manifest_sha, "fixedCodes": 300,
              "previousContinuationRuns": 4, "previousLoginFailures": 2,
              "newLoginAttempts": [], "queries": [], "responses": []}
    responses = ledger["responses"]
    attempts = ledger["newLoginAttempts"]
    try:
        for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
            try:
                with hard_socket_timeout():
                    login = bs.login()
                entry = {"attempt": attempt, "errorCode": str(login.error_code),
                         "errorMessage": str(login.error_msg)}
                attempts.append(entry)
                if entry["errorCode"] == "0":
                    break
            except Exception as exc:
                attempts.append({"attempt": attempt, "errorType": type(exc).__name__,
                                 "errorMessage": str(exc)[:160]})
            if hasattr(context, "default_socket") and context.default_socket is not None:
                context.default_socket.close()
                context.default_socket = None
        else:
            return finish(ledger, raw_dir, codes, "login_failed_twice")

        consecutive_errors = 0
        for code in codes:
            for kind in ("daily", "factor"):
                if len(ledger["queries"]) >= MAX_QUERY_REQUESTS:
                    return finish(ledger, raw_dir, codes, "request_limit_reached")
                query = {"code": code, "kind": kind}
                ledger["queries"].append(query)
                try:
                    with hard_socket_timeout():
                        if kind == "daily":
                            result = bs.query_history_k_data_plus(code, ",".join(SOURCE_FIELDS),
                                                                  start_date=PRICE_START, end_date=END,
                                                                  frequency="d", adjustflag="3")
                        else:
                            result = bs.query_adjust_factor(code, start_date=FACTOR_START, end_date=END)
                        payload = collect_response(result, code,
                                                   SOURCE_FIELDS if kind == "daily" else ADJUSTMENT_FIELDS,
                                                   kind)
                    ref = save_response(raw_dir, code, kind, payload)
                    responses.append(ref)
                    query.update({"status": "ok", "rows": ref["rows"],
                                  "compressedSha256": ref["compressed_sha256"]})
                    consecutive_errors = 0
                except Exception as exc:
                    query.update({"status": "error", "errorType": type(exc).__name__,
                                  "errorMessage": str(exc)[:160]})
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        return finish(ledger, raw_dir, codes, "three_consecutive_query_errors")
                if sum(ref["bytes"] for ref in responses) > MAX_RAW_BYTES:
                    return finish(ledger, raw_dir, codes, "raw_size_limit_reached")
        return finish(ledger, raw_dir, codes, "queries_finished")
    finally:
        try:
            bs.logout()
        except Exception:
            pass


def finish(ledger: dict, raw_dir: Path, codes: list[str], reason: str) -> dict:
    ledger["finishedAt"] = datetime.now(timezone.utc).isoformat()
    ledger["stopReason"] = reason
    result = {"status": "qualified_raw_available" if reason == "queries_finished" and
              len(ledger["responses"]) == MAX_QUERY_REQUESTS else "incomplete_source_gap",
              "stopReason": reason, "asOfRequested": END, "lastQualifiedContinuationDate": "2026-10-23",
              "missingSessionsBeforeFetch": list(DATES), "manifestSha256": ledger["fixedManifestSha256"],
              "dailyFields": list(SOURCE_FIELDS), "factorFields": list(ADJUSTMENT_FIELDS),
              "dailyRange": [PRICE_START, END], "factorRange": [FACTOR_START, END],
              "adjustment": "BaoStock adjustflag=3 is unadjusted; factor events are separate",
              "amount": "BaoStock daily amount field, reported CNY yuan; source string retained",
              "storageUuid": ledger["storagePlan"]["external_uuid"],
              "externalRawDirectory": str(raw_dir), "queryRequests": len(ledger["queries"]),
              "rawCompressedBytes": sum(ref["bytes"] for ref in ledger["responses"]),
              "loginAttemptsThisRun": len(ledger["newLoginAttempts"]),
              "coverage": coverage(ledger["responses"], raw_dir, codes),
              "unresolvedSessions": [] if reason == "queries_finished" and
              len(ledger["responses"]) == MAX_QUERY_REQUESTS else list(DATES),
              "sourceArrivalAndRevisionTime": "unknown; acquisition timestamps in ledger",
              "integration": "not done; controller must independently read back and run original fixed-300 continuation"}
    result_dir = raw_dir.parent
    ledger_path = result_dir / "acquisition-ledger.json"
    ledger_bytes = json.dumps(ledger, ensure_ascii=False, indent=2, allow_nan=False).encode()
    ledger_path.write_bytes(ledger_bytes)
    result["acquisitionLedger"] = {"path": str(ledger_path), "sha256": sha256(ledger_bytes)}
    stage_result = STAGE / "data-result.json"
    stage_result.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    (STAGE / "report.md").write_text(
        f"# 固定300股近期缺口原始源核查\n\n结论：{reason}；新增成功原响应 "
        f"{len(ledger['responses'])}/600 份，供应商新登录 {len(ledger['newLoginAttempts'])}/2 次。"
        f"截至 {END} 的六个交易日不能因请求或索引存在就称为已续接；主控需逐原件核验并接续原计算。\n\n"
        f"原始响应只在已核设备 {result['storageUuid']} 的新目录，路径与逐件 SHA 见外盘 acquisition-ledger.json。"
        f"旧历史截至 2026-10-23，旧包与此前四次续接、两次登录失败记录均未改动。\n"
    )
    return result


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = run()
    print(json.dumps({"status": result["status"], "stopReason": result["stopReason"],
                      "queryRequests": result["queryRequests"],
                      "coverage": result["coverage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
