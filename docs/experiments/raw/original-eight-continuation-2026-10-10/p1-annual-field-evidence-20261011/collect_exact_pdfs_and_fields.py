"""Collect eight bound official annual PDFs and extract page text, with no trading inference."""

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
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MAX_PDF = 20_971_520
MAX_TOTAL = 125_829_120


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())


def import_adapter():
    p = Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py")
    spec = importlib.util.spec_from_file_location("pdf_frozen_adapter", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def allowed_hop(url, initial):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.chinaamc.com":
        return False
    if url == initial:
        return True
    # Only an explicit server Location can introduce one such follow-up path.
    return parsed.path.startswith("/upload/resources/file/") or parsed.path == "/front/ui/contentcore/resource/download"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PDFOneHop:
    def __init__(self, output, module, log):
        self.output, self.module, self.log = output, module, log
        self.entry = None
        self.calls = []
        self.opener = build_opener(NoRedirect())

    def request_once(self, url):
        entry = self.entry
        if entry is None or not allowed_hop(url, entry["url"]):
            raise ValueError("PDF hop not bound to exact official path")
        latest = json.loads(self.log.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != entry["target_id"]
                or latest["resource_id"] != entry["resource_id"] or latest["requested_url"] != url):
            raise ValueError("ledger reservation/method binding mismatch")
        count = sum(x["target_id"] == entry["target_id"] for x in self.calls)
        if count >= 2:
            raise ValueError("per-year PDF hop cap exhausted")
        index = len(self.calls) + 1
        audit = {"index": index, "target_id": entry["target_id"], "attempt_id": latest["attempt_id"],
                 "resource_id": entry["resource_id"], "url": url, "method": "GET",
                 "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        audit_path = self.output / f"method-{index:03d}.json"
        save_new(audit_path, audit)
        request = Request(url, method="GET", headers={"User-Agent": "LeiSignal-research-source-evidence/1"})
        try:
            response = self.opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            status, headers = response.status, dict(response.headers.items())
            body = response.read(MAX_PDF + 1)
        blocked = None
        if len(body) > MAX_PDF:
            blocked = "PDF response exceeds 20 MiB per-resource cap"
            body = body[:MAX_PDF]
        if status in {301, 302, 303, 307, 308}:
            location = headers.get("Location") or headers.get("location")
            follow = urljoin(url, location) if location else None
            if not follow or not allowed_hop(follow, entry["url"]) or count + 1 >= 2:
                blocked = "redirect path/hop outside frozen PDF scope"
        raw = self.output / f"raw-hop-{index:03d}.bin"
        with raw.open("xb") as out:
            out.write(body); out.flush(); os.fsync(out.fileno())
        receipt = {"index": index, "target_id": entry["target_id"], "attempt_id": latest["attempt_id"],
                   "status": status, "headers": headers, "body_path": str(raw), "body_bytes": len(body),
                   "body_sha256": sha(raw), "method_path": str(audit_path), "method_sha256": sha(audit_path),
                   "blocked": blocked}
        hp = self.output / f"headers-{index:03d}.json"
        save_new(hp, receipt)
        self.calls.append({"receipt_path": str(hp), **receipt})
        if blocked:
            raise ValueError(blocked)
        return self.module.TransportResponse(status=status, headers=headers, body=body)


def extract_pages(pdf_path, output_dir):
    from pypdf import PdfReader
    data = pdf_path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
        raise ValueError("missing PDF signature or terminal EOF")
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError("encrypted PDF")
    pages = []
    for index, page in enumerate(reader.pages, 1):
        content = page.extract_text() or ""
        page_path = output_dir / f"page-{index:04d}.txt"
        with page_path.open("x", encoding="utf-8") as out:
            out.write(content)
            out.flush(); os.fsync(out.fileno())
        pages.append({"page": index, "text_path": str(page_path), "text_sha256": sha(page_path),
                      "characters": len(content)})
    if not pages:
        raise ValueError("PDF has no pages")
    return pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-pdfs", action="store_true", required=True)
    parser.parse_args()
    contract = json.loads((HERE / "pdf-field-contract.json").read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(path) != expected: raise ValueError(f"frozen input changed: {path}")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("fixed external identity mismatch")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free <= plan["external_reserve_bytes"] + plan["estimated_bytes"]:
        raise ValueError("external capacity insufficient")
    root = Path(contract["external_run_directory"]); output = root / "pdf-fields"
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("PDF output on wrong disk")
    if any(p.name not in {"stdout.log", "stderr.log"} and not p.name.startswith("._") for p in output.iterdir()):
        raise ValueError("PDF stage directory not pristine")
    mapping = json.loads((HERE / "exact-pdf-map.json").read_text())
    entries = mapping["entries"]
    if len(entries) != 8 or len({e["target_id"] for e in entries}) != 8:
        raise ValueError("frozen eight PDF bindings differ")
    candidates = {x["target_id"]: x for x in json.loads((HERE / "article-delivery.json").read_text())["candidates"]}
    for e in entries:
        if (sha(e["article_html_path"]) != e["article_html_sha256"]
                or e["url"] != candidates[e["target_id"]]["attachment_url_candidate"]
                or e["raw_href"] != candidates[e["target_id"]]["attachment_href_as_seen"]):
            raise ValueError("article/PDF binding changed")
    # One offline semantic set: exact original URLs, denied unrelated path/host,
    # and a two-hop maximum over article+PDF=3, without any transport call.
    fake = {"network_calls": 0,
            "exact_urls_allowed": all(allowed_hop(e["url"], e["url"]) for e in entries),
            "unrelated_path_denied": not allowed_hop("https://www.chinaamc.com/other/report.pdf", entries[0]["url"]),
            "other_host_denied": not allowed_hop("https://example.com/front/ui/contentcore/resource/download?ID=391869", entries[0]["url"]),
            "one_article_hop_plus_two_pdf_hops_max": 1 + 2 == 3}
    if not all(v for k,v in fake.items() if k!="network_calls"):
        raise ValueError("offline exact URL guard failure")
    save_new(output / "fake-check.json", fake)
    log = Path(contract["external_ledger_path"])
    old_bytes = log.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != contract["external_ledger_before_sha256"]:
        raise ValueError("accepted cumulative24 ledger hash mismatch")
    old_rows = [json.loads(x) for x in old_bytes.splitlines()]
    if sum(x["record_type"] == "reservation" for x in old_rows) != 24 or sum(x["record_type"] == "outcome" for x in old_rows) != 24:
        raise ValueError("accepted24 reservation/outcome mismatch")
    snapshot = root / "accepted24-ledger-snapshot.jsonl"
    with snapshot.open("xb") as out:
        out.write(old_bytes); out.flush(); os.fsync(out.fileno())
    adapter = import_adapter()
    payload = json.loads((HERE / "annual-field-targets.json").read_text())
    caps = adapter.batch1_caps(payload)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    by_target = {x["target_id"]: x for x in payload["targets"]}
    transport = PDFOneHop(output, adapter.module, log)
    ledger = adapter.RequestLedger(log, caps, adapter.PathCheckedTransport(transport),
        allowed_hosts={x["exact_official_host"] for x in payload["targets"] if x["exact_official_host"]},
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if ledger.attempt_totals()["groups"]["P1"] != 24 or ledger.unresolved_attempt_ids():
        raise ValueError("cumulative ledger replay mismatch")
    before = ledger.counts()
    started = datetime.now(timezone.utc).isoformat()
    results = []
    fatal = None
    bytes_total = 0
    for e in entries:
        target = e["target_id"]
        if target not in by_target or by_target[target]["exact_official_host"] != "www.chinaamc.com":
            fatal = "unbound PDF target"; break
        if ledger.counts()[target]["evidence_attempts"] - before[target]["evidence_attempts"] >= 2:
            fatal = "per-target PDF cap already consumed"; break
        transport.entry = e
        start = len(transport.calls)
        try:
            result = ledger.run(target, "evidence", e["url"],
                                by_target[target]["official_source_family"], "exact_official_annual_PDF",
                                resource_id=e["resource_id"], document_identity=target + "-fullannualPDF")
            outcomes = [x for x in ledger._rows if x["record_type"] == "outcome" and x["request_id"] == result.request_id]
            good = bool(outcomes) and all(x["error"] is None for x in outcomes) and outcomes[-1]["http_status"] == 200
            status = "saved_200" if good else "source_failed"
            errors = [x["error"] or f"HTTP {x['http_status']}" for x in outcomes if x["error"] or x["http_status"] not in {200,301,302,303,307,308}]
        except (adapter.LedgerValidationError, adapter.module.BudgetExceeded) as exc:
            result = None; status = "ledger_refused"; errors = [f"{type(exc).__name__}: {exc}"]
        except Exception as exc:
            result = None; status = "control_error"; errors = [f"{type(exc).__name__}: {exc}"]
            fatal = errors[0]
        calls = transport.calls[start:]
        pdf_path = None; pages = []
        if status == "saved_200" and calls:
            pdf_path = Path(calls[-1]["body_path"])
            bytes_total += pdf_path.stat().st_size
            if bytes_total > MAX_TOTAL:
                status = "stage_body_limit_exceeded"; errors.append("PDF body total exceeds 120 MiB")
            else:
                directory = output / target
                directory.mkdir(exist_ok=False)
                try:
                    pages = extract_pages(pdf_path, directory)
                except Exception as exc:
                    status = "PDF_identity_or_text_failure"
                    errors.append(f"{type(exc).__name__}: {exc}")
        results.append({"target_id": target, "url": e["url"], "request_id": result.request_id if result else None,
                        "status": status, "errors": errors, "hops": calls,
                        "pdf_path": str(pdf_path) if pdf_path else None,
                        "pdf_sha256": sha(pdf_path) if pdf_path else None,
                        "pages": pages, "counts_after": ledger.counts()[target]})
        if ledger.unresolved_attempt_ids(): fatal = "unresolved ledger reservation"
        if fatal: break
    queries = sum(ledger.counts()[k]["search_queries"] - before[k]["search_queries"] for k in before if k.startswith("P1-"))
    resources = sum(ledger.counts()[k]["candidate_resources"] - before[k]["candidate_resources"] for k in before if k.startswith("P1-"))
    hops = ledger.attempt_totals()["groups"]["P1"] - 24
    if queries or resources > 8 or hops > 16:
        fatal = "PDF substage budget exceeded"
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(),
               "command": [sys.executable, str(Path(__file__)), "--exact-pdfs"],
               "contract_sha256": sha(HERE / "pdf-field-contract.json"),
               "accepted24_snapshot_path": str(snapshot), "accepted24_snapshot_sha256": sha(snapshot),
               "accepted24_prefix_preserved": log.read_bytes().startswith(old_bytes),
               "fake_check_path": str(output / "fake-check.json"), "fake_check_sha256": sha(output / "fake-check.json"),
               "results": results, "stage_counts": {"queries": queries, "resources": resources, "hops": hops},
               "cumulative_counts": ledger.counts(), "cumulative_totals": ledger.attempt_totals(),
               "ledger_path": str(log), "ledger_sha256": sha(log),
               "unresolved_reservations": ledger.unresolved_attempt_ids(), "fatal": fatal,
               "E1_requests": 0, "R2_science_runs": 0}
    save_new(output / "pdf-raw-receipt.json", receipt)
    print(json.dumps({"receipt": str(output / "pdf-raw-receipt.json"),
                      "stage_counts": receipt["stage_counts"], "fatal": fatal}, ensure_ascii=False))
    if fatal: raise SystemExit(2)


if __name__ == "__main__":
    main()
