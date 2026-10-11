"""Bounded P1 official archive discovery through the frozen per-hop request ledger."""

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "source-contract.json"
MAX_BODY = 1_048_576
TIMEOUT = 8


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CapturingOneHop:
    """One hop only. Ledger and adapter validate and reserve before this is called."""

    def __init__(self, root, module):
        self.root = root
        self.module = module
        self.opener = build_opener(NoRedirect())
        self.expected_host = None
        self.calls = []

    def request_once(self, url):
        index = len(self.calls) + 1
        host = urlsplit(url).hostname
        if host != self.expected_host or urlsplit(url).path.lower().endswith(".pdf"):
            raise ValueError("target host mismatch or report PDF path; no transport")
        start = time.monotonic()
        req = Request(url, method="GET", headers={"User-Agent": "LeiSignal-research-source-discovery/1"})
        try:
            response = self.opener.open(req, timeout=TIMEOUT)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            headers = dict(response.headers.items())
            content_type = headers.get("Content-Type", headers.get("content-type", ""))
            if "pdf" in content_type.lower():
                body = b""
                blocked = "PDF response not collected"
            else:
                body = response.read(MAX_BODY + 1)
                blocked = "response body exceeded 1 MiB cap" if len(body) > MAX_BODY else None
                if blocked:
                    body = body[:MAX_BODY]
        raw_path = self.root / "responses" / f"hop-{index:03d}.bin"
        header_path = self.root / "responses" / f"hop-{index:03d}-headers.json"
        with raw_path.open("xb") as stream:
            stream.write(body)
        receipt = {"index": index, "url": url, "status": status, "headers": headers,
                   "body_path": str(raw_path), "body_bytes_saved": len(body),
                   "body_sha256": hashlib.sha256(body).hexdigest(),
                   "elapsed_seconds": round(time.monotonic() - start, 3),
                   "blocked": blocked}
        save_new(header_path, receipt)
        self.calls.append({"receipt_path": str(header_path), **{k: v for k, v in receipt.items() if k != "headers"}})
        if blocked:
            raise ValueError(blocked)
        return self.module.TransportResponse(status=status, headers=headers, body=body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("initial", "continuation"), required=True)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    contract = json.loads(CONTRACT.read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(Path(path)) != expected:
            raise ValueError(f"frozen input changed: {path}")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("fixed external device identity mismatch")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free <= plan["external_reserve_bytes"] + plan["estimated_bytes"]:
        raise ValueError("fixed external capacity insufficient")
    root = Path(plan["run_directory"])
    if root.stat().st_dev != plan["external_device"]:
        raise ValueError("result directory on wrong device")
    output = root / args.phase
    if output.exists():
        raise ValueError(f"{args.phase} phase already exists; inspect before any continuation")
    if args.phase == "continuation":
        prior = json.loads((root / "initial" / "initial-receipt.json").read_text())
        if prior["fatal"] or prior["unresolved_reservations"]:
            raise ValueError("initial receipt is not closed")
        disclosed = (root / "initial" / "responses" / "hop-002.bin").read_bytes().decode("gb18030")
        exact_iframe = '<iframe src="/product/publishGgList.do?fundcode=515170"'
        if disclosed.count(exact_iframe) != 1:
            raise ValueError("expected official iframe continuation not disclosed exactly once")
    output.mkdir(exist_ok=False)
    (output / "responses").mkdir(exist_ok=False)
    adapter_path = Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("p1_frozen_adapter", adapter_path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    payload = json.loads((HERE / "amended-targets.json").read_text())
    old_payload = json.loads(Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/targets.json").read_text())
    if len(payload["targets"]) != 16 or len(old_payload["targets"]) != 16:
        raise ValueError("target count differs")
    targets = {item["target_id"]: item for item in payload["targets"]}
    initial = json.loads((HERE / "initial-request-map.json").read_text())["requests"]
    if len(initial) != 5 or len({r["query_id"] for r in initial}) != 5:
        raise ValueError("initial fixed slots differ")
    if args.phase == "continuation":
        initial = [{"target_id": "P1-515170-2024", "query_id": "p1-515170-2024-disclosed-iframe",
                    "url": "https://www.chinaamc.com/product/publishGgList.do?fundcode=515170",
                    "covered_periods": ["2024"], "disclosed_by": "initial/responses/hop-002.bin iframe src"}]
    transport = CapturingOneHop(output, adapter.module)
    log_path = root / "access-ledger.jsonl"
    ledger = adapter.make_ledger(payload, log_path, transport)
    findings = []
    fatal = None
    for item in initial:
        target = item["target_id"]
        if target not in targets or not target.startswith("P1-"):
            fatal = "unbound P1 target"; break
        host = targets[target]["exact_official_host"]
        if urlsplit(item["url"]).hostname != host:
            fatal = "initial URL not on target host"; break
        transport.expected_host = host
        before = len(transport.calls)
        try:
            result = ledger.run(target, "search", item["url"], targets[target]["official_source_family"],
                                "official_archive_discovery", query_id=item["query_id"])
            error = next((r.get("error") for r in reversed(ledger._rows)
                          if r.get("record_type") == "outcome" and r.get("request_id") == result.request_id), None)
            status = "transport_failed" if result.body is None or error else "response_saved"
        except (adapter.LedgerValidationError, adapter.module.BudgetExceeded) as exc:
            result = None; error = f"{type(exc).__name__}: {exc}"; status = "blocked_before_or_between_hops"
        except Exception as exc:
            fatal = f"unexpected ledger/control error: {type(exc).__name__}: {exc}"
            break
        findings.append({"target_id": target, "query_id": item["query_id"], "initial_url": item["url"],
                         "intended_periods_not_proved": item["covered_periods"], "status": status,
                         "error": error, "transport_calls": transport.calls[before:],
                         "request_id": result.request_id if result else None,
                         "ledger_counts_after": ledger.counts()[target]})
        if ledger.unresolved_attempt_ids():
            fatal = "unresolved ledger reservation"; break
    receipt = {"schema_version": 1, "phase": args.phase, "pid": os.getpid(),
               "started_at": started, "ended_at": datetime.now(timezone.utc).isoformat(),
               "command": [sys.executable, str(Path(__file__)), "--phase", args.phase],
               "contract_sha256": sha(CONTRACT), "adapter_sha256": sha(adapter_path),
               "ledger_source_sha256": sha(adapter.OLD), "amended_targets_sha256": sha(HERE / "amended-targets.json"),
               "initial_map_sha256": sha(HERE / "initial-request-map.json"),
               "storage_plan_sha256": sha(HERE / "storage-plan.json"),
               "ledger": str(log_path), "ledger_sha256": sha(log_path) if log_path.exists() else None,
               "fatal": fatal, "findings": findings, "transport_calls": transport.calls,
               "counts": ledger.counts(), "totals": ledger.attempt_totals(),
               "unresolved_reservations": ledger.unresolved_attempt_ids(),
               "network_outside_ledger": 0, "E1_requests": 0,
               "limits": "Saved response bytes are discovery observations only; no annual report PDF or complete year coverage inferred."}
    save_new(output / f"{args.phase}-receipt.json", receipt)
    print(json.dumps({"receipt": str(output / f"{args.phase}-receipt.json"),
                      "fatal": fatal, "transport_calls": len(transport.calls),
                      "totals": receipt["totals"]}, ensure_ascii=False))
    if fatal:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
