"""Fetch exactly three bound Guotai annual PDFs and save page-level source text."""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from pypdf import PdfReader

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
NAME = "国泰中证细分化工产业主题交易型开放式指数证券投资基金"
PROXY = "http://127.0.0.1:7890"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def write(path, data):
    with Path(path).open("xb") as out:
        out.write(data); out.flush(); os.fsync(out.fileno())


def write_json(path, data):
    write(path, (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BoundPDFCurl:
    def __init__(self, adapter, output, ledger_path):
        self.adapter, self.output, self.ledger_path = adapter, output, ledger_path
        self.entry = None
        self.calls = []

    def request_once(self, url):
        entry = self.entry
        if (entry is None or url != entry["url"] or urlsplit(url).scheme != "https"
                or urlsplit(url).hostname != "st.gtfund.com" or len(self.calls) >= 3
                or any(x["year"] == entry["year"] for x in self.calls)):
            raise ValueError("PDF URL or request count differs from bound source")
        latest = json.loads(self.ledger_path.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != entry["target_id"]
                or latest["resource_id"] != entry["resource_id"] or latest["requested_url"] != url
                or latest["is_retry"] or latest["retry_of_attempt_id"] is not None):
            raise ValueError("fsynced ledger reservation does not bind PDF GET")
        index = len(self.calls) + 1
        method_path = self.output / f"method-{index:03d}.json"
        write_json(method_path, {"attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                  "target_id": entry["target_id"], "resource_id": entry["resource_id"],
                  "year": entry["year"], "method": "GET", "url": url,
                  "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()})
        header_path = self.output / f"headers-{index:03d}.bin"
        pdf_path = self.output / f"annual-{entry['year']}.pdf"
        stdout_path = self.output / f"curl-stdout-{index:03d}.bin"
        stderr_path = self.output / f"curl-stderr-{index:03d}.bin"
        command = ["/usr/bin/curl", "--disable", "--silent", "--show-error", "--retry", "0",
                   "--max-redirs", "0", "--max-time", "30", "--proto", "=https", "--noproxy", "",
                   "--proxy", PROXY, "--request", "GET", "--dump-header", str(header_path),
                   "--output", str(pdf_path), "--write-out", "%{http_code}", url]
        write_json(self.output / f"command-{index:03d}.json", {"argv": command, "shell": False,
                   "default_certificate_verification": True, "redirect_following": False, "automatic_retries": 0})
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=self.output)
            call = {"year": entry["year"], "pid": process.pid, "attempt_id": latest["attempt_id"],
                    "method_path": str(method_path), "command_path": str(self.output / f"command-{index:03d}.json")}
            self.calls.append(call)
            exit_code = process.wait()
            stdout.flush(); os.fsync(stdout.fileno()); stderr.flush(); os.fsync(stderr.fileno())
        raw_header = header_path.read_bytes() if header_path.exists() else b""
        body = pdf_path.read_bytes() if pdf_path.exists() else b""
        code = stdout_path.read_text(errors="replace").strip()
        stderr_text = stderr_path.read_text(errors="replace")
        call.update({"exit_code": exit_code, "http_code_text": code,
                     "headers_path": str(header_path) if header_path.exists() else None,
                     "headers_sha256": digest(raw_header), "pdf_path": str(pdf_path) if pdf_path.exists() else None,
                     "pdf_sha256": digest(body), "pdf_bytes": len(body),
                     "stderr_path": str(stderr_path), "stderr_sha256": sha(stderr_path)})
        if exit_code != 0:
            raise RuntimeError(f"curl exit {exit_code}: {stderr_text.strip()}")
        if not code.isdigit() or int(code) == 0:
            raise RuntimeError(f"curl returned no HTTP status: {code!r}")
        sections = [x for x in raw_header.replace(b"\r\n", b"\n").split(b"\n\n") if x.strip()]
        final = sections[-1] if sections else b""
        headers = {}
        for line in final.splitlines()[1:]:
            if b":" in line:
                key, value = line.split(b":", 1)
                headers[key.decode("latin1")] = value.strip().decode("latin1")
        ledger_headers = {k: v for k, v in headers.items() if k.lower() != "location"}
        return self.adapter.module.TransportResponse(status=int(code), headers=ledger_headers, body=body)


def extract(pdf_path, output, year):
    data = pdf_path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
        raise ValueError("PDF signature or terminal EOF missing")
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError("PDF encrypted")
    texts = []
    for number, page in enumerate(reader.pages, 1):
        value = page.extract_text() or ""
        path = output / f"annual-{year}-page-{number:04d}.txt"
        write(path, value.encode("utf-8"))
        texts.append({"page": number, "path": str(path), "sha256": sha(path), "characters": len(value)})
    if not texts:
        raise ValueError("PDF has no pages")
    first = Path(texts[0]["path"]).read_text()
    identity_page = Path(texts[4]["path"]).read_text() if len(texts) >= 5 else first
    if (NAME not in first or f"{year} 年年度报告" not in first
            or "基金主代码" not in identity_page or "516220" not in identity_page):
        raise ValueError("PDF fund, code, or annual year identity mismatch")
    return {"page_count": len(texts), "first_page_text": texts[0],
            "code_page_text": texts[4] if len(texts) >= 5 else texts[0], "pages": texts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-guotai-pdfs", action="store_true", required=True)
    parser.parse_args()
    contract_path = HERE / "guotai-pdf-contract.json"
    contract = json.loads(contract_path.read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(path) != expected:
            raise ValueError(f"frozen input changed: {path}")
    delivery = json.loads((HERE / "guotai-name-query-delivery.json").read_text())
    entries = []
    for year in (2022, 2023, 2024):
        link = delivery["exact_annual_links"][str(year)]
        url = link["pdf_url"]
        if (link["fund_code"] != ["516220"] or link["title"] != f"{NAME}{year}年年度报告"
                or urlsplit(url).hostname != "st.gtfund.com" or not urlsplit(url).path.endswith(".pdf")):
            raise ValueError("official PDF source binding differs")
        entries.append({"year": year, "target_id": f"P1-516220-{year}",
                        "resource_id": f"GUOTAI-ANNUAL-PDF-{year}", "url": url,
                        "published_at": link["published_at"], "report_id": link["report_id"]})
    plan = json.loads(Path(contract["storage_plan_path"]).read_text())
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
        raise ValueError("run directory is on wrong device")
    log = Path(contract["external_ledger_path"])
    prefix = log.read_bytes()
    if digest(prefix) != contract["external_ledger_before_sha256"]:
        raise ValueError("old38 ledger prefix changed")
    old_rows = [json.loads(x) for x in prefix.splitlines()]
    if (sum(x["record_type"] == "reservation" for x in old_rows),
            sum(x["record_type"] == "outcome" for x in old_rows)) != (38, 38):
        raise ValueError("old38 ledger row count changed")
    output = Path(contract["external_write_paths"][0])
    output.mkdir(mode=0o755, exist_ok=False)
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("PDF output on wrong device")
    adapter = import_file("guotai_pdf_adapter", Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py"))
    targets = json.loads((HERE / "guotai-pdf-targets.json").read_text())
    caps = adapter.batch1_caps(targets)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    hosts = {x["exact_official_host"] for x in targets["targets"] if x["exact_official_host"]} | {"st.gtfund.com"}
    transport = BoundPDFCurl(adapter, output, log)
    ledger = adapter.RequestLedger(log, caps, transport, allowed_hosts=hosts,
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if ledger.attempt_totals()["groups"]["P1"] != 38 or ledger.unresolved_attempt_ids():
        raise ValueError("ledger replay count differs")
    before = ledger.counts()
    results = []
    started = datetime.now(timezone.utc).isoformat()
    for entry in entries:
        transport.entry = entry
        result = ledger.run(entry["target_id"], "evidence", entry["url"],
                            "Guotai Fund official annual report", "exact_official_annual_PDF",
                            resource_id=entry["resource_id"], document_identity=f"Guotai-516220-{entry['year']}-annual-PDF")
        outcome = next(x for x in reversed(ledger._rows) if x["record_type"] == "outcome" and x["request_id"] == result.request_id)
        call = transport.calls[-1] if transport.calls else None
        identity = None
        status = "source_failed"
        if outcome["error"] is None and outcome["http_status"] == 200 and call and call["pdf_path"]:
            try:
                identity = extract(Path(call["pdf_path"]), output, entry["year"])
                status = "pdf_identity_verified"
            except Exception as exc:
                status = "pdf_identity_or_text_failure"
                identity = {"error": f"{type(exc).__name__}: {exc}"}
        results.append({"year": entry["year"], "target_id": entry["target_id"],
                        "resource_id": entry["resource_id"], "url": entry["url"],
                        "published_at": entry["published_at"], "report_id": entry["report_id"],
                        "request_id": result.request_id, "status": status, "outcome": outcome,
                        "call": call, "identity": identity, "counts_after": ledger.counts()[entry["target_id"]]})
        if ledger.unresolved_attempt_ids() or ledger.attempt_totals()["groups"]["P1"] > 44:
            break
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(), "contract_sha256": sha(contract_path),
               "old38_sha256": digest(prefix), "old38_prefix_preserved": log.read_bytes().startswith(prefix),
               "results": results, "transport_call_count": len(transport.calls),
               "stage_counts": {"queries": sum(ledger.counts()[k]["search_queries"] - before[k]["search_queries"] for k in before if k.startswith("P1-")),
                                "resources": sum(ledger.counts()[k]["candidate_resources"] - before[k]["candidate_resources"] for k in before if k.startswith("P1-")),
                                "hops": ledger.attempt_totals()["groups"]["P1"] - 38},
               "cumulative_totals": ledger.attempt_totals(), "unresolved_reservations": ledger.unresolved_attempt_ids(),
               "ledger_path": str(log), "ledger_sha256": sha(log), "R2_science_runs": 0}
    write_json(output / "raw-receipt.json", receipt)
    print(json.dumps({"raw_receipt": str(output / "raw-receipt.json"),
                      "statuses": [x["status"] for x in results],
                      "http_statuses": [x["outcome"]["http_status"] for x in results]}, ensure_ascii=False))
    if (not receipt["old38_prefix_preserved"] or receipt["unresolved_reservations"]
            or receipt["stage_counts"]["queries"] != 0 or receipt["stage_counts"]["resources"] > 3
            or receipt["stage_counts"]["hops"] > 3):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
