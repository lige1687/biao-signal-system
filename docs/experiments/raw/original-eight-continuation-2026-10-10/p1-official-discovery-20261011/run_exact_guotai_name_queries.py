"""At most three frozen Guotai annual-title POSTs on the shared request ledger."""

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
ENDPOINT = "https://e.gtfund.com/Etrade/Public/cochin/fts.search_report"
PROXY = "http://127.0.0.1:7890"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def save_bytes(path, data):
    with Path(path).open("xb") as out:
        out.write(data); out.flush(); os.fsync(out.fileno())


def save_json(path, obj):
    save_bytes(path, (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BoundCurl:
    def __init__(self, adapter, output, log):
        self.adapter, self.output, self.log = adapter, output, log
        self.bound = None
        self.calls = []

    def request_once(self, url):
        item = self.bound
        if item is None or url != ENDPOINT or url != item["url"]:
            raise ValueError("request outside frozen annual-title action")
        if any(c["year"] == item["year"] for c in self.calls):
            raise ValueError("same annual title cannot be sent twice")
        latest = json.loads(self.log.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != TARGET
                or latest["query_id"] != item["query_id"] or latest["requested_url"] != url
                or latest["is_retry"] or latest["retry_of_attempt_id"] is not None):
            raise ValueError("latest fsynced ledger reservation does not match title")
        index = len(self.calls) + 1
        body = item["body_json_compact"].encode("utf-8")
        if sha_bytes(body) != item["body_sha256"]:
            raise ValueError("frozen body digest changed")
        payload = self.output / f"request-{index:03d}.bin"
        save_bytes(payload, body)
        method = {"attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                  "query_id": item["query_id"], "year": item["year"], "method": "POST",
                  "url": url, "body_sha256": sha(payload), "content_type": item["content_type"],
                  "proxy": PROXY, "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        save_json(self.output / f"method-{index:03d}.json", method)
        header_path = self.output / f"headers-{index:03d}.bin"
        response_path = self.output / f"response-{index:03d}.bin"
        stdout_path = self.output / f"curl-stdout-{index:03d}.bin"
        stderr_path = self.output / f"curl-stderr-{index:03d}.bin"
        command = ["/usr/bin/curl", "--disable", "--silent", "--show-error", "--retry", "0",
                   "--max-redirs", "0", "--max-time", "15", "--proto", "=https", "--noproxy", "",
                   "--proxy", PROXY, "--request", "POST", "--header", "Content-Type: " + item["content_type"],
                   "--data-binary", "@" + str(payload), "--dump-header", str(header_path),
                   "--output", str(response_path), "--write-out", "%{http_code}", url]
        save_json(self.output / f"command-{index:03d}.json", {"argv": command, "shell": False,
                   "default_certificate_verification": True, "redirect_following": False, "automatic_retries": 0})
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=self.output)
            call = {"year": item["year"], "query_id": item["query_id"], "pid": process.pid,
                    "attempt_id": latest["attempt_id"], "command_path": str(self.output / f"command-{index:03d}.json")}
            self.calls.append(call)
            exit_code = process.wait()
            stdout.flush(); os.fsync(stdout.fileno()); stderr.flush(); os.fsync(stderr.fileno())
        raw_headers = header_path.read_bytes() if header_path.exists() else b""
        response_body = response_path.read_bytes() if response_path.exists() else b""
        http_code = stdout_path.read_text(errors="replace").strip()
        stderr_text = stderr_path.read_text(errors="replace")
        call.update({"exit_code": exit_code, "http_code_text": http_code,
                     "headers_path": str(header_path) if header_path.exists() else None,
                     "headers_sha256": sha_bytes(raw_headers),
                     "body_path": str(response_path) if response_path.exists() else None,
                     "body_sha256": sha_bytes(response_body), "body_bytes": len(response_body),
                     "stderr_path": str(stderr_path), "stderr_sha256": sha(stderr_path)})
        if exit_code != 0:
            raise RuntimeError(f"curl exit {exit_code}: {stderr_text.strip()}")
        if not http_code.isdigit() or int(http_code) == 0:
            raise RuntimeError(f"curl returned no HTTP status: {http_code!r}")
        sections = [s for s in raw_headers.replace(b"\r\n", b"\n").split(b"\n\n") if s.strip()]
        final = sections[-1] if sections else b""
        headers = {}
        for line in final.splitlines()[1:]:
            if b":" in line:
                key, value = line.split(b":", 1)
                headers[key.decode("latin1")] = value.strip().decode("latin1")
        ledger_headers = {k: v for k, v in headers.items() if k.lower() != "location"}
        return self.adapter.module.TransportResponse(status=int(http_code), headers=ledger_headers, body=response_body)


def summarize(path):
    raw = path.read_bytes()
    try:
        obj = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"schema": "invalid_json", "body_bytes": len(raw)}, False
    if (not isinstance(obj, dict) or not isinstance(obj.get("total"), int)
            or not isinstance(obj.get("pages"), int) or not isinstance(obj.get("hits"), list)):
        return {"schema": "unexpected", "top_level_type": type(obj).__name__,
                "top_level_keys": list(obj) if isinstance(obj, dict) else None}, False
    hits = obj["hits"]
    parsed = []
    for hit in hits:
        if isinstance(hit, dict):
            parsed.append({"keys": list(hit),
                           "titles": {k: v for k, v in hit.items() if k.lower() in {"title", "name", "reporttitle", "reportname"} and isinstance(v, str)},
                           "urls": {k: v for k, v in hit.items() if k.lower() in {"url", "link", "pdfurl", "fileurl"} and isinstance(v, str)},
                           "years": {k: v for k, v in hit.items() if k.lower() in {"year", "reportyear"} and isinstance(v, (str, int))}})
        else:
            parsed.append({"type": type(hit).__name__})
    return {"schema": "report_search_json", "top_level_keys": list(obj), "total": obj["total"],
            "pages": obj["pages"], "hits_count": len(hits), "hits": parsed,
            "catalog_complete": False}, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-annual-titles", action="store_true", required=True)
    parser.parse_args()
    contract_path = HERE / "guotai-name-query-contract.json"
    contract = json.loads(contract_path.read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(path) != expected:
            raise ValueError(f"frozen input changed: {path}")
    preparation = json.loads((HERE / "guotai-name-query-preparation.json").read_text())
    items = preparation["proposed_requests"]
    if [x["year"] for x in items] != [2022, 2023, 2024] or len({x["query_id"] for x in items}) != 3:
        raise ValueError("frozen three-year sequence changed")
    for item in items:
        if (item["target_id"] != TARGET or item["url"] != ENDPOINT or item["method"] != "POST"
                or item["content_type"] != "application/json; charset=utf-8"
                or sha_bytes(item["body_json_compact"].encode()) != item["body_sha256"]):
            raise ValueError("frozen title request changed")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("external identity mismatch")
    for path, reserve, addition in ((mount, plan["external_reserve_bytes"], contract["expected_additional_ordinary_bytes"]),
                                     (Path.cwd(), plan["internal_reserve_bytes"], contract["expected_internal_small_record_bytes"])):
        stat = os.statvfs(path)
        if stat.f_bavail * stat.f_frsize <= reserve + addition:
            raise ValueError("storage reserve failed")
    root = Path(contract["external_run_directory"])
    if root.stat().st_dev != plan["external_device"]:
        raise ValueError("run directory is on wrong device")
    log = Path(contract["external_ledger_path"])
    prefix = log.read_bytes()
    if sha_bytes(prefix) != contract["external_ledger_before_sha256"]:
        raise ValueError("old35 ledger prefix changed")
    rows = [json.loads(line) for line in prefix.splitlines()]
    if (sum(x["record_type"] == "reservation" for x in rows),
            sum(x["record_type"] == "outcome" for x in rows)) != (35, 35):
        raise ValueError("old35 ledger count changed")
    output = Path(contract["external_write_paths"][0])
    output.mkdir(mode=0o755, exist_ok=False)
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("output directory is on wrong device")
    adapter = import_file("guotai_names_adapter", Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py"))
    targets = json.loads((HERE / "guotai-name-query-targets.json").read_text())
    caps = adapter.batch1_caps(targets)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    transport = BoundCurl(adapter, output, log)
    ledger = adapter.RequestLedger(log, caps, transport,
        allowed_hosts={x["exact_official_host"] for x in targets["targets"] if x["exact_official_host"]},
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if (ledger.attempt_totals()["groups"]["P1"] != 35 or ledger.unresolved_attempt_ids()
            or ledger.counts()[TARGET] != {"search_queries": 2, "candidate_resources": 1, "evidence_attempts": 3}):
        raise ValueError("ledger replay or target state differs")
    started = datetime.now(timezone.utc).isoformat()
    results = []
    for item in items:
        transport.bound = item
        result = ledger.run(TARGET, "search", ENDPOINT, "Guotai Fund official product-and-announcement conduit",
                            "official_annual_title_search", query_id=item["query_id"],
                            document_identity=f"Guotai-516220-annual-title-{item['year']}")
        outcome = next(x for x in reversed(ledger._rows) if x["record_type"] == "outcome" and x["request_id"] == result.request_id)
        call = transport.calls[-1] if transport.calls else None
        body_path = Path(call["body_path"]) if call and call["body_path"] else None
        summary, valid = summarize(body_path) if body_path and body_path.exists() else (None, False)
        stopped = outcome["error"] is not None or outcome["http_status"] != 200 or not valid
        if body_path and body_path.exists() and any(token in body_path.read_bytes().lower() for token in (b"hashcash_challenge", b"captcha")):
            stopped = True
        results.append({"year": item["year"], "query_id": item["query_id"], "request_id": result.request_id,
                        "outcome": outcome, "call": call, "summary": summary, "stop_source": stopped})
        if stopped:
            break
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(), "contract_sha256": sha(contract_path),
               "old35_sha256": sha_bytes(prefix), "old35_prefix_preserved": log.read_bytes().startswith(prefix),
               "results": results, "transport_call_count": len(transport.calls),
               "target_counts": ledger.counts()[TARGET], "cumulative_totals": ledger.attempt_totals(),
               "unresolved_reservations": ledger.unresolved_attempt_ids(), "ledger_path": str(log),
               "ledger_sha256": sha(log), "R2_science_runs": 0}
    save_json(output / "raw-receipt.json", receipt)
    print(json.dumps({"raw_receipt": str(output / "raw-receipt.json"),
                      "years_attempted": [x["year"] for x in results],
                      "http_statuses": [x["outcome"]["http_status"] for x in results],
                      "stopped": bool(results[-1]["stop_source"]) if results else True}, ensure_ascii=False))
    if not receipt["old35_prefix_preserved"] or receipt["unresolved_reservations"] or len(transport.calls) != len(results):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
