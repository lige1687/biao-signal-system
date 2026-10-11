"""One budgeted, source-bound Guotai report POST; never retry or follow redirects."""

import argparse
import hashlib
import importlib.util
import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MAX_BODY = 4_194_304
TARGET = "P1-516220-2023"
QUERY = "GUOTAI-BOUND-Q01"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def write_new(path, data):
    with Path(path).open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path, value):
    write_new(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())


def import_adapter(path):
    spec = importlib.util.spec_from_file_location("guotai_query_frozen_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ExactPost:
    def __init__(self, adapter, output, ledger_path, request):
        self.adapter, self.output, self.ledger_path, self.request = adapter, output, ledger_path, request
        self.opener = build_opener(NoRedirect())
        self.calls = []

    def request_once(self, url):
        bound = self.request
        if url != bound["initial_report_request_url"] or bound["initial_report_request_method"] != "POST":
            raise ValueError("request is outside exact source binding")
        if self.calls:
            raise ValueError("second transport call prohibited")
        latest = json.loads(self.ledger_path.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != TARGET
                or latest["query_id"] != QUERY or latest["requested_url"] != url):
            raise ValueError("latest fsynced reservation does not match POST")
        body = bound["body_json_compact"].encode("utf-8")
        if sha_bytes(body) != bound["body_sha256"]:
            raise ValueError("POST body SHA mismatch")
        method = {"attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                  "method": "POST", "url": url, "body_sha256": sha_bytes(body),
                  "content_type": bound["content_type"], "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        write_json(self.output / "method-001.json", method)
        self.calls.append({"attempt_id": latest["attempt_id"], "method_path": str(self.output / "method-001.json")})
        req = Request(url, data=body, method="POST", headers={"Content-Type": bound["content_type"]})
        try:
            try:
                response = self.opener.open(req, timeout=12)
            except HTTPError as exc:
                response = exc
            with response:
                status = response.status
                headers = dict(response.headers.items())
                raw_header = response.headers.as_bytes()
                response_body = response.read(MAX_BODY + 1)
        except Exception as exc:
            write_json(self.output / "transport-error-001.json", {"type": type(exc).__name__, "message": str(exc)})
            raise
        write_new(self.output / "headers-001.bin", raw_header)
        write_new(self.output / "response-001.bin", response_body)
        self.calls[0].update({"status": status, "raw_headers_path": str(self.output / "headers-001.bin"),
                              "body_path": str(self.output / "response-001.bin"),
                              "body_bytes": len(response_body), "body_sha256": sha_bytes(response_body),
                              "response_headers": headers})
        if len(response_body) > MAX_BODY:
            raise ValueError("response exceeds the 4 MiB read cap; saved prefix only")
        # Keep the wire headers above; omit Location in the ledger view so the frozen
        # ledger cannot schedule a second hop. The 3xx status is still recorded.
        ledger_headers = {k: v for k, v in headers.items() if k.lower() != "location"}
        return self.adapter.module.TransportResponse(status=status, headers=ledger_headers, body=response_body)


def summarize_response(body, content_type):
    summary = {"content_type": content_type, "json_parse": "not_json", "catalog_complete": False,
               "titles": [], "years": [], "urls": [], "pagination": None}
    try:
        obj = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return summary
    summary["json_parse"] = "valid_json"
    summary["top_level_type"] = type(obj).__name__
    if isinstance(obj, dict):
        summary["top_level_keys"] = list(obj)
        for key in ("data", "result", "results", "list", "records", "rows", "page", "pagination", "paginator", "total", "totalCount"):
            if key in obj:
                value = obj[key]
                summary.setdefault("observed_fields", {})[key] = value if isinstance(value, (str, int, float, bool, type(None))) else type(value).__name__
    # Preserve the full server response on disk. This small receipt only reports
    # fields actually present; no schema or completeness is inferred from HTTP 200.
    def visit(value, depth=0):
        if depth > 5:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                kl = k.lower()
                if isinstance(v, str) and kl in {"title", "name", "reportname", "reporttitle"}:
                    summary["titles"].append(v)
                if isinstance(v, str) and kl in {"url", "link", "pdfurl", "fileurl"}:
                    summary["urls"].append(v)
                if kl in {"year", "reportyear"} and isinstance(v, (str, int)):
                    summary["years"].append(v)
                if kl in {"pagination", "paginator"} and isinstance(v, dict):
                    summary["pagination"] = v
                visit(v, depth + 1)
        elif isinstance(value, list):
            for v in value[:100]:
                visit(v, depth + 1)
    visit(obj)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-report-post", action="store_true", required=True)
    parser.parse_args()
    contract_path = HERE / "guotai-bound-report-contract.json"
    contract = json.loads(contract_path.read_text())
    for path, digest in contract["input_sha256"].items():
        if sha_file(path) != digest:
            raise ValueError(f"frozen input changed: {path}")
    bound = json.loads((HERE / "guotai-bound-report-request.json").read_text())
    if (bound["target_id"], bound["query_id"], bound["initial_report_request_url"]) != (
            TARGET, QUERY, "https://e.gtfund.com/Etrade/Public/cochin/fts.search_report"):
        raise ValueError("source-bound target/query/path changed")
    if bound["initial_custom_headers"] or bound["automatic_retries"] or bound["redirects_permitted"]:
        raise ValueError("request has forbidden headers/retries/redirects")
    if sha_bytes(bound["body_json_compact"].encode()) != bound["body_sha256"]:
        raise ValueError("bound body bytes changed")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("external device identity mismatch")
    external_free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    internal_free = os.statvfs(Path.cwd()).f_bavail * os.statvfs(Path.cwd()).f_frsize
    if (external_free <= plan["external_reserve_bytes"] + contract["expected_additional_ordinary_bytes"]
            or internal_free <= plan["internal_reserve_bytes"] + contract["expected_internal_small_record_bytes"]):
        raise ValueError("storage reserve failed")
    root = Path(contract["external_run_directory"])
    if root.stat().st_dev != plan["external_device"]:
        raise ValueError("run directory is on another device")
    log = Path(contract["external_ledger_path"])
    prefix = log.read_bytes()
    if sha_bytes(prefix) != contract["external_ledger_before_sha256"]:
        raise ValueError("cumulative33 ledger prefix changed")
    rows = [json.loads(line) for line in prefix.splitlines()]
    if (sum(x["record_type"] == "reservation" for x in rows),
            sum(x["record_type"] == "outcome" for x in rows)) != (33, 33):
        raise ValueError("cumulative33 ledger records changed")
    output = Path(contract["external_write_paths"][0])
    output.mkdir(mode=0o755, exist_ok=False)
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("result directory is on another device")
    adapter = import_adapter(Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py"))
    payload = json.loads((HERE / "guotai-bound-query-targets.json").read_text())
    targets = {x["target_id"]: x for x in payload["targets"]}
    caps = adapter.batch1_caps(payload)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    transport = ExactPost(adapter, output, log, bound)
    ledger = adapter.RequestLedger(log, caps, transport,
        allowed_hosts={x["exact_official_host"] for x in payload["targets"] if x["exact_official_host"]},
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if (ledger.attempt_totals()["groups"]["P1"] != 33 or ledger.unresolved_attempt_ids()
            or ledger.counts()[TARGET] != {"search_queries": 0, "candidate_resources": 1, "evidence_attempts": 1}):
        raise ValueError("ledger count or target budget differs from frozen state")
    started = datetime.now(timezone.utc).isoformat()
    result = ledger.run(TARGET, "search", bound["initial_report_request_url"],
                        targets[TARGET]["official_source_family"], "official_report_search",
                        query_id=QUERY, document_identity="Guotai-516220-report-catalog-page1")
    outcomes = [row for row in ledger._rows if row["record_type"] == "outcome" and row["request_id"] == result.request_id]
    outcome = outcomes[-1] if outcomes else None
    saved = output / "response-001.bin"
    summary = summarize_response(saved.read_bytes(), outcome["content_type"]) if saved.exists() and outcome else None
    status = "response_saved" if outcome and outcome["error"] is None else "transport_failed"
    if outcome and outcome["http_status"] in {401, 403}:
        status = "auth_or_forbidden_stop"
    if outcome and outcome["http_status"] in {301, 302, 303, 307, 308}:
        status = "redirect_stop"
    if saved.exists() and any(term in saved.read_bytes().lower() for term in (b"hashcash_challenge", b"captcha")):
        status = "challenge_stop"
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(), "status": status,
               "contract_sha256": sha_file(contract_path), "request_sha256": sha_file(HERE / "guotai-bound-report-request.json"),
               "old33_prefix_preserved": log.read_bytes().startswith(prefix), "old33_sha256": sha_bytes(prefix),
               "target_id": TARGET, "query_id": QUERY, "request_id": result.request_id,
               "transport_calls": transport.calls, "outcome": outcome,
               "target_counts": ledger.counts()[TARGET], "cumulative_totals": ledger.attempt_totals(),
               "unresolved_reservations": ledger.unresolved_attempt_ids(),
               "ledger_path": str(log), "ledger_sha256": sha_file(log), "response_summary": summary,
               "raw_response_path": str(saved) if saved.exists() else None,
               "raw_response_sha256": sha_file(saved) if saved.exists() else None,
               "report_queries_this_run": 1, "resources_this_run": 0, "R2_science_runs": 0}
    write_json(output / "raw-receipt.json", receipt)
    print(json.dumps({"raw_receipt": str(output / "raw-receipt.json"), "status": status,
                      "request_id": result.request_id, "http_status": outcome["http_status"] if outcome else None}, ensure_ascii=False))
    if not receipt["old33_prefix_preserved"] or receipt["unresolved_reservations"] or len(transport.calls) != 1:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
