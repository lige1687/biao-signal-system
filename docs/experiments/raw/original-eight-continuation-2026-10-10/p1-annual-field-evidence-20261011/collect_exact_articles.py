"""Read eight frozen ChinaAMC annual article pages through the cumulative ledger."""

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
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MAX_BODY = 2_097_152


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, obj):
    with Path(path).open("x", encoding="utf-8") as out:
        json.dump(obj, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())


def import_adapter():
    p = Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py")
    spec = importlib.util.spec_from_file_location("article_frozen_adapter", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class NarrowArticleTransport:
    def __init__(self, output, module, ledger_path):
        self.output, self.module, self.ledger_path = output, module, ledger_path
        self.current = None
        self.calls = []
        self.opener = build_opener(NoRedirect())

    def request_once(self, url):
        entry = self.current
        if entry is None:
            raise ValueError("no bound article target")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "www.chinaamc.com" or not parsed.path.startswith("/c/") or parsed.path.lower().endswith(".pdf"):
            raise ValueError("article hop outside exact official /c/ HTML family")
        latest = json.loads(self.ledger_path.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != entry["target_id"]
                or latest["resource_id"] != entry["resource_id"] or latest["requested_url"] != url):
            raise ValueError("latest reservation does not bind article hop")
        # A redirected hop must stay inside the same article family. Both initial and
        # redirected URL are preserved in the cumulative ledger and method audit.
        index = len(self.calls) + 1
        audit = {"index": index, "attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                 "target_id": entry["target_id"], "resource_id": entry["resource_id"],
                 "url": url, "method": "GET", "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        ap = self.output / f"method-{index:03d}.json"
        write_new(ap, audit)
        request = Request(url, method="GET", headers={"User-Agent": "LeiSignal-research-source-evidence/1"})
        try:
            response = self.opener.open(request, timeout=8)
        except HTTPError as exc:
            response = exc
        with response:
            status, headers = response.status, dict(response.headers.items())
            ctype = headers.get("Content-Type", headers.get("content-type", ""))
            body = b"" if "pdf" in ctype.lower() else response.read(MAX_BODY + 1)
        blocked = None
        if len(body) > MAX_BODY:
            blocked = "article response exceeds 2 MiB"; body = body[:MAX_BODY]
        if "pdf" in (headers.get("Content-Type") or headers.get("content-type") or "").lower():
            blocked = "PDF response refused in article-only stage"
        if status in {301, 302, 303, 307, 308}:
            location = headers.get("Location") or headers.get("location")
            if not location:
                blocked = "redirect lacks Location"
            else:
                from urllib.parse import urljoin
                next_url = urljoin(url, location)
                next_parsed = urlsplit(next_url)
                if (next_parsed.scheme != "https" or next_parsed.hostname != "www.chinaamc.com"
                        or not next_parsed.path.startswith("/c/") or next_parsed.path.lower().endswith(".pdf")):
                    blocked = "redirect leaves official article HTML family"
                elif sum(x["target_id"] == entry["target_id"] for x in self.calls) + 1 >= entry["remaining_hops"]:
                    blocked = "redirect would consume reserved PDF hop"
        raw = self.output / f"article-hop-{index:03d}.bin"
        with raw.open("xb") as out:
            out.write(body); out.flush(); os.fsync(out.fileno())
        receipt = {"index": index, "target_id": entry["target_id"], "attempt_id": latest["attempt_id"],
                   "status": status, "headers": headers, "body_path": str(raw), "body_bytes": len(body),
                   "body_sha256": sha(raw), "method_path": str(ap), "method_sha256": sha(ap),
                   "blocked": blocked}
        hp = self.output / f"headers-{index:03d}.json"
        write_new(hp, receipt)
        self.calls.append({"headers_path": str(hp), **receipt})
        if blocked:
            raise ValueError(blocked)
        return self.module.TransportResponse(status=status, headers=headers, body=body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-articles", action="store_true", required=True)
    parser.parse_args()
    contract = json.loads((HERE / "article-contract.json").read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(path) != expected: raise ValueError(f"frozen input changed: {path}")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("fixed external disk identity mismatch")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free <= plan["external_reserve_bytes"] + plan["estimated_bytes"]:
        raise ValueError("external capacity insufficient")
    output = Path(plan["run_directory"])
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("external result on wrong device")
    if any(p.name not in {"stdout.log", "stderr.log"} and not p.name.startswith("._") for p in output.iterdir()):
        raise ValueError("article result directory not pristine")
    entries = json.loads((HERE / "annual-article-map.json").read_text())["entries"]
    if len(entries) != 8 or len({e["target_id"] for e in entries}) != 8:
        raise ValueError("eight exact annual targets required")
    for e in entries:
        if sha(e["raw_discovery"]["raw_response_path"]) != e["raw_discovery"]["raw_response_sha256"]:
            raise ValueError("discovery evidence changed")
        if e["url"] != e["raw_discovery"]["article_url"] or e["method"] != "GET" or e["role"] != "evidence":
            raise ValueError("article request differs from frozen discovery")
    log = Path(contract["external_ledger_path"])
    old_bytes = log.read_bytes()
    expected = json.loads((HERE / "annual-article-map.json").read_text())["source_cumulative_ledger_sha256"]
    if hashlib.sha256(old_bytes).hexdigest() != expected:
        raise ValueError("accepted cumulative16 ledger SHA mismatch")
    old_rows = [json.loads(x) for x in old_bytes.splitlines()]
    if sum(x["record_type"] == "reservation" for x in old_rows) != 16 or sum(x["record_type"] == "outcome" for x in old_rows) != 16:
        raise ValueError("accepted16 ledger reservation/outcome mismatch")
    snapshot = output / "accepted16-ledger-snapshot.jsonl"
    with snapshot.open("xb") as out:
        out.write(old_bytes); out.flush(); os.fsync(out.fileno())
    adapter = import_adapter()
    payload = json.loads((HERE / "annual-field-targets.json").read_text())
    targets = {x["target_id"]: x for x in payload["targets"]}
    caps = adapter.batch1_caps(payload)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    transport = NarrowArticleTransport(output, adapter.module, log)
    ledger = adapter.RequestLedger(log, caps, adapter.PathCheckedTransport(transport),
        allowed_hosts={x["exact_official_host"] for x in payload["targets"] if x["exact_official_host"]},
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if ledger.attempt_totals()["groups"]["P1"] != 16 or ledger.unresolved_attempt_ids():
        raise ValueError("cumulative ledger replay failed")
    before_counts = ledger.counts()
    started = datetime.now(timezone.utc).isoformat()
    results = []
    fatal = None
    for entry in entries:
        target = entry["target_id"]
        if target not in targets or targets[target]["exact_official_host"] != "www.chinaamc.com":
            fatal = "unbound article target/host"; break
        prior_target_hops = before_counts[target]["evidence_attempts"]
        remaining_hops = 3 - (ledger.counts()[target]["evidence_attempts"] - prior_target_hops)
        transport.current = {**entry, "remaining_hops": remaining_hops}
        call_start = len(transport.calls)
        try:
            result = ledger.run(target, "evidence", entry["url"],
                                targets[target]["official_source_family"], "annual_article_source_text",
                                resource_id=entry["resource_id"], document_identity=target + "-official-annual-article")
            outcomes = [x for x in ledger._rows if x["record_type"] == "outcome" and x["request_id"] == result.request_id]
            good = bool(outcomes) and all(x["error"] is None for x in outcomes) and outcomes[-1]["http_status"] == 200
            status = "saved_200" if good else "source_failed"
            errors = [x["error"] or f"HTTP {x['http_status']}" for x in outcomes if x["error"] or x["http_status"] not in {200,301,302,303,307,308}]
        except (adapter.LedgerValidationError, adapter.module.BudgetExceeded) as exc:
            result = None; status = "ledger_refused"; errors = [f"{type(exc).__name__}: {exc}"]
        except Exception as exc:
            result = None; status = "control_error"; errors = [f"{type(exc).__name__}: {exc}"]
            fatal = errors[0]
        calls = transport.calls[call_start:]
        results.append({"target_id": target, "url": entry["url"], "resource_id": entry["resource_id"],
                        "request_id": result.request_id if result else None, "status": status,
                        "errors": errors, "hops": calls, "counts_after": ledger.counts()[target]})
        if ledger.unresolved_attempt_ids(): fatal = "unresolved ledger reservation"
        if fatal: break
    stage_resources = sum(ledger.counts()[tid]["candidate_resources"] - before_counts[tid]["candidate_resources"] for tid in before_counts if tid.startswith("P1-"))
    stage_queries = sum(ledger.counts()[tid]["search_queries"] - before_counts[tid]["search_queries"] for tid in before_counts if tid.startswith("P1-"))
    stage_hops = ledger.attempt_totals()["groups"]["P1"] - 16
    if stage_resources > 8 or stage_queries != 0 or stage_hops > 24:
        fatal = "article substage budget breached"
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(),
               "command": [sys.executable, str(Path(__file__)), "--exact-articles"],
               "contract_sha256": sha(HERE / "article-contract.json"),
               "prior16_sha256": sha(snapshot), "prior16_prefix_preserved": log.read_bytes().startswith(old_bytes),
               "snapshot_path": str(snapshot), "results": results,
               "stage_counts": {"queries": stage_queries, "resources": stage_resources, "hops": stage_hops},
               "cumulative_counts": ledger.counts(), "cumulative_totals": ledger.attempt_totals(),
               "ledger_path": str(log), "ledger_sha256": sha(log),
               "unresolved_reservations": ledger.unresolved_attempt_ids(), "fatal": fatal,
               "PDF_downloads": 0, "E1_requests": 0}
    write_new(output / "article-raw-receipt.json", receipt)
    print(json.dumps({"receipt": str(output / "article-raw-receipt.json"),
                      "stage_counts": receipt["stage_counts"], "fatal": fatal}, ensure_ascii=False))
    if fatal: raise SystemExit(2)


if __name__ == "__main__":
    main()
