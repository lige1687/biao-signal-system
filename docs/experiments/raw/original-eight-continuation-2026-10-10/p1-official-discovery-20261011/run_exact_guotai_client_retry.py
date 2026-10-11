"""One explicitly counted Guotai POST via verified system curl and fixed proxy."""

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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TARGET = "P1-516220-2023"
QUERY = "GUOTAI-CLIENT-RETRY-Q01"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def write_new(path, data):
    with Path(path).open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path, obj):
    write_new(path, (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExactCurl:
    def __init__(self, adapter, output, ledger_path, request):
        self.adapter, self.output, self.ledger_path, self.request = adapter, output, ledger_path, request
        self.calls = []

    def request_once(self, url):
        bound = self.request
        if self.calls or url != bound["initial_report_request_url"]:
            raise ValueError("only one exact source request is allowed")
        latest = json.loads(self.ledger_path.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != TARGET
                or latest["query_id"] != QUERY or latest["requested_url"] != url
                or latest["retry_of_attempt_id"] != bound["retry_of_attempt_id"] or not latest["is_retry"]):
            raise ValueError("latest fsynced reservation does not bind explicit retry")
        payload = bound["body_json_compact"].encode("utf-8")
        if sha_bytes(payload) != bound["body_sha256"]:
            raise ValueError("source-bound request bytes changed")
        payload_path = self.output / "request-001.bin"
        write_new(payload_path, payload)
        method = {"attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                  "retry_of_attempt_id": latest["retry_of_attempt_id"], "query_id": QUERY,
                  "method": "POST", "url": url, "body_sha256": sha_file(payload_path),
                  "payload_path": str(payload_path), "content_type": bound["content_type"],
                  "proxy": bound["proxy"], "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        write_json(self.output / "method-001.json", method)
        headers_path = self.output / "headers-001.bin"
        body_path = self.output / "response-001.bin"
        stdout_path = self.output / "curl-stdout-001.bin"
        stderr_path = self.output / "curl-stderr-001.bin"
        command = ["/usr/bin/curl", "--disable", "--silent", "--show-error", "--retry", "0",
                   "--max-redirs", "0", "--max-time", "15", "--proto", "=https", "--noproxy", "",
                   "--proxy", bound["proxy"], "--request", "POST", "--header", "Content-Type: " + bound["content_type"],
                   "--data-binary", "@" + str(payload_path), "--dump-header", str(headers_path),
                   "--output", str(body_path), "--write-out", "%{http_code}", url]
        write_json(self.output / "command-001.json", {"argv": command, "shell": False,
                    "default_certificate_verification": True, "redirect_following": False,
                    "automatic_retries": 0, "curl_config_disabled": True})
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=self.output)
            self.calls.append({"pid": proc.pid, "attempt_id": latest["attempt_id"],
                               "command_path": str(self.output / "command-001.json")})
            exit_code = proc.wait()
            stdout.flush(); os.fsync(stdout.fileno())
            stderr.flush(); os.fsync(stderr.fileno())
        raw_headers = headers_path.read_bytes() if headers_path.exists() else b""
        response_body = body_path.read_bytes() if body_path.exists() else b""
        http_code = stdout_path.read_text(errors="replace").strip()
        stderr_text = stderr_path.read_text(errors="replace")
        self.calls[0].update({"exit_code": exit_code, "http_code_text": http_code,
                              "headers_path": str(headers_path) if headers_path.exists() else None,
                              "body_path": str(body_path) if body_path.exists() else None,
                              "headers_sha256": sha_bytes(raw_headers), "body_sha256": sha_bytes(response_body),
                              "body_bytes": len(response_body), "stderr_path": str(stderr_path),
                              "stderr_sha256": sha_file(stderr_path)})
        if exit_code != 0:
            raise RuntimeError(f"curl exit {exit_code}: {stderr_text.strip()}")
        if not http_code.isdigit() or int(http_code) == 0:
            raise RuntimeError(f"curl returned no HTTP status: {http_code!r}")
        status = int(http_code)
        # Curl may write an HTTP CONNECT preamble; use the final header section.
        sections = [part for part in raw_headers.replace(b"\r\n", b"\n").split(b"\n\n") if part.strip()]
        final = sections[-1] if sections else b""
        parsed = {}
        for line in final.splitlines()[1:]:
            if b":" in line:
                key, value = line.split(b":", 1)
                parsed[key.decode("latin1")] = value.strip().decode("latin1")
        # Preserve raw headers; omit Location in the ledger view to prevent the
        # frozen ledger's redirect loop from issuing another network request.
        ledger_headers = {k: v for k, v in parsed.items() if k.lower() != "location"}
        return self.adapter.module.TransportResponse(status=status, headers=ledger_headers, body=response_body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-client-retry", action="store_true", required=True)
    parser.parse_args()
    contract_path = HERE / "guotai-client-retry-contract.json"
    contract = json.loads(contract_path.read_text())
    for path, digest in contract["input_sha256"].items():
        if sha_file(path) != digest:
            raise ValueError(f"frozen input changed: {path}")
    bound = json.loads((HERE / "guotai-client-retry-request.json").read_text())
    if (bound["target_id"], bound["query_id"], bound["initial_report_request_url"],
            bound["initial_report_request_method"], bound["proxy"], bound["retry_of_attempt_id"]) != (
            TARGET, QUERY, "https://e.gtfund.com/Etrade/Public/cochin/fts.search_report", "POST",
            "http://127.0.0.1:7890", "attempt-7c909f40-a17f-4734-b2d0-62fa5b42204c"):
        raise ValueError("exact retry binding changed")
    if bound["initial_custom_headers"] or bound["automatic_retries"] or bound["redirects_permitted"] or not bound["verify_tls"]:
        raise ValueError("retry request violated source boundary")
    if sha_bytes(bound["body_json_compact"].encode()) != bound["body_sha256"]:
        raise ValueError("body SHA mismatch")
    original = json.loads((HERE / "guotai-bound-report-delivery.json").read_text())
    if (original["attempt_id"] != bound["retry_of_attempt_id"] or original["http_status"] is not None
            or original["body_sha256"] != bound["body_sha256"]):
        raise ValueError("original failure does not match retry contract")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("external device identity mismatch")
    for path, reserve, addition in ((mount, plan["external_reserve_bytes"], contract["expected_additional_ordinary_bytes"]),
                                     (Path.cwd(), plan["internal_reserve_bytes"], contract["expected_internal_small_record_bytes"])):
        stat = os.statvfs(path)
        if stat.f_bavail * stat.f_frsize <= reserve + addition:
            raise ValueError("storage reserve failed")
    root = Path(contract["external_run_directory"])
    if root.stat().st_dev != plan["external_device"]:
        raise ValueError("external run directory is on wrong device")
    log = Path(contract["external_ledger_path"])
    prefix = log.read_bytes()
    if sha_bytes(prefix) != contract["external_ledger_before_sha256"]:
        raise ValueError("cumulative34 ledger prefix changed")
    rows = [json.loads(line) for line in prefix.splitlines()]
    if (sum(r["record_type"] == "reservation" for r in rows),
            sum(r["record_type"] == "outcome" for r in rows)) != (34, 34):
        raise ValueError("cumulative34 ledger count changed")
    adapter = import_file("guotai_retry_frozen_adapter", Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py"))
    payload = json.loads((HERE / "guotai-client-retry-targets.json").read_text())
    targets = {x["target_id"]: x for x in payload["targets"]}
    output = Path(contract["external_write_paths"][0])
    output.mkdir(mode=0o755, exist_ok=False)
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("output directory on wrong device")
    transport = ExactCurl(adapter, output, log, bound)
    caps = adapter.batch1_caps(payload)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    ledger = adapter.RequestLedger(log, caps, transport,
        allowed_hosts={x["exact_official_host"] for x in payload["targets"] if x["exact_official_host"]},
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if (ledger.attempt_totals()["groups"]["P1"] != 34 or ledger.unresolved_attempt_ids()
            or ledger.counts()[TARGET] != {"search_queries": 1, "candidate_resources": 1, "evidence_attempts": 2}):
        raise ValueError("ledger replay/count mismatch")
    started = datetime.now(timezone.utc).isoformat()
    result = ledger.run(TARGET, "search", bound["initial_report_request_url"],
        targets[TARGET]["official_source_family"], "official_report_search_client_repair",
        query_id=QUERY, retry_of_attempt_id=bound["retry_of_attempt_id"],
        document_identity="Guotai-516220-report-catalog-page1")
    outcomes = [r for r in ledger._rows if r["record_type"] == "outcome" and r["request_id"] == result.request_id]
    outcome = outcomes[-1] if outcomes else None
    raw_body = output / "response-001.bin"
    summary = None
    if raw_body.exists() and outcome and outcome["error"] is None:
        previous = import_file("guotai_previous_parser", HERE / "run_exact_guotai_report_query.py")
        summary = previous.summarize_response(raw_body.read_bytes(), outcome["content_type"])
    status = "transport_failed" if not outcome or outcome["error"] else "response_saved"
    if outcome and outcome["http_status"] in {401, 403}:
        status = "auth_or_forbidden_stop"
    if outcome and outcome["http_status"] in {301, 302, 303, 307, 308}:
        status = "redirect_stop"
    if raw_body.exists() and any(term in raw_body.read_bytes().lower() for term in (b"hashcash_challenge", b"captcha")):
        status = "challenge_stop"
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
        "ended_utc": datetime.now(timezone.utc).isoformat(), "status": status,
        "contract_sha256": sha_file(contract_path), "request_sha256": sha_file(HERE / "guotai-client-retry-request.json"),
        "old34_prefix_preserved": log.read_bytes().startswith(prefix), "old34_sha256": sha_bytes(prefix),
        "target_id": TARGET, "query_id": QUERY, "request_id": result.request_id,
        "retry_of_attempt_id": bound["retry_of_attempt_id"], "transport_calls": transport.calls,
        "outcome": outcome, "response_summary": summary, "target_counts": ledger.counts()[TARGET],
        "cumulative_totals": ledger.attempt_totals(), "unresolved_reservations": ledger.unresolved_attempt_ids(),
        "ledger_path": str(log), "ledger_sha256": sha_file(log),
        "raw_body_path": str(raw_body) if raw_body.exists() else None,
        "raw_body_sha256": sha_file(raw_body) if raw_body.exists() else None,
        "R2_science_runs": 0}
    write_json(output / "raw-receipt.json", receipt)
    print(json.dumps({"raw_receipt": str(output / "raw-receipt.json"), "status": status,
                      "http_status": outcome["http_status"] if outcome else None,
                      "curl_pid": transport.calls[0]["pid"] if transport.calls else None,
                      "curl_exit": transport.calls[0].get("exit_code") if transport.calls else None}, ensure_ascii=False))
    if not receipt["old34_prefix_preserved"] or receipt["unresolved_reservations"] or len(transport.calls) != 1:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
