"""Read exactly one HTML-referenced Guotai common.js via the cumulative ledger."""

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
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXACT = "https://e.gtfund.com/Public/static/etrade/1/dist/js/common.js?v=hy187"
TARGET = "P1-516220-2023"
RESOURCE = "EXACT-HTML-REFERENCED-GUOTAI-COMMON-JS"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExactTransport:
    def __init__(self, inner):
        self.inner = inner

    def request_once(self, url):
        if url != EXACT:
            raise ValueError("only the single HTML-referenced common.js URL is allowed")
        return self.inner.request_once(url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-common", action="store_true", required=True)
    parser.parse_args()
    contract = json.loads((HERE / "guotai-common-contract.json").read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(path) != expected:
            raise ValueError(f"frozen input changed: {path}")
    saved = Path(contract["external_read_paths"][1]).read_text(errors="replace")
    if saved.count('src="/Public/static/etrade/1/dist/js/common.js?v=hy187"') != 1:
        raise ValueError("exact active script reference not present once")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("fixed external device identity mismatch")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free <= plan["external_reserve_bytes"] + contract["expected_additional_ordinary_bytes"]:
        raise ValueError("fixed external capacity insufficient")
    root = Path(contract["external_run_directory"]); output = root / "guotai-common-binding"
    if output.stat().st_dev != plan["external_device"]:
        raise ValueError("Guotai result on wrong device")
    if any(p.name not in {"stdout.log", "stderr.log"} and not p.name.startswith("._") for p in output.iterdir()):
        raise ValueError("result directory not pristine")
    log = Path(contract["external_ledger_path"])
    old_bytes = log.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != contract["external_ledger_before_sha256"]:
        raise ValueError("accepted cumulative32 ledger SHA mismatch")
    old_rows = [json.loads(x) for x in old_bytes.splitlines()]
    if sum(x["record_type"] == "reservation" for x in old_rows) != 32 or sum(x["record_type"] == "outcome" for x in old_rows) != 32:
        raise ValueError("accepted32 reservation/outcome mismatch")
    adapter = import_file("guotai_frozen_adapter", Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py"))
    previous = import_file("guotai_previous_transport", HERE / "run_additional_discovery.py")
    payload = json.loads((HERE / "additional-targets.json").read_text())
    targets = {x["target_id"]: x for x in payload["targets"]}
    if urlsplit(EXACT).hostname != targets[TARGET]["exact_official_host"]:
        raise ValueError("target host mismatch")
    caps = adapter.batch1_caps(payload)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    inner = previous.AuditedOneHop(output, adapter.module, log)
    ledger = adapter.RequestLedger(log, caps, ExactTransport(inner),
        allowed_hosts={x["exact_official_host"] for x in payload["targets"] if x["exact_official_host"]},
        group_for_target=groups, group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)
    if ledger.attempt_totals()["groups"]["P1"] != 32 or ledger.unresolved_attempt_ids():
        raise ValueError("ledger replay/count mismatch")
    before = ledger.counts()[TARGET]
    if before["candidate_resources"] != 0 or before["evidence_attempts"] != 0:
        raise ValueError("target original unused resource/hop already spent")
    action = {"target_id": TARGET, "query_id": None, "resource_id": RESOURCE,
              "url": EXACT, "host": "e.gtfund.com", "method": "GET", "role": "evidence"}
    inner.action = action
    started = datetime.now(timezone.utc).isoformat()
    fatal = None
    try:
        result = ledger.run(TARGET, "evidence", EXACT, targets[TARGET]["official_source_family"],
                            "exact_HTML_referenced_common_JS_source_text", resource_id=RESOURCE,
                            document_identity="Guotai-common-js-hy187")
        outcomes = [x for x in ledger._rows if x["record_type"] == "outcome" and x["request_id"] == result.request_id]
        good = len(outcomes) == 1 and outcomes[0]["http_status"] == 200 and outcomes[0]["error"] is None
        status = "saved_200" if good else "source_failed"
        errors = [x["error"] or f"HTTP {x['http_status']}" for x in outcomes if x["error"] or x["http_status"] != 200]
    except (adapter.LedgerValidationError, adapter.module.BudgetExceeded) as exc:
        result = None; status = "ledger_refused"; errors = [f"{type(exc).__name__}: {exc}"]
    except Exception as exc:
        result = None; status = "control_error"; errors = [f"{type(exc).__name__}: {exc}"]
        fatal = errors[0]
    if ledger.unresolved_attempt_ids():
        fatal = "unresolved ledger reservation"
    if ledger.counts()[TARGET]["candidate_resources"] - before["candidate_resources"] > 1 or ledger.counts()[TARGET]["evidence_attempts"] - before["evidence_attempts"] > 1:
        fatal = "single resource/hop budget exceeded"
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(),
               "command": [sys.executable, str(Path(__file__)), "--exact-common"],
               "contract_sha256": sha(HERE / "guotai-common-contract.json"),
               "old32_prefix_preserved": log.read_bytes().startswith(old_bytes),
               "old32_sha256": hashlib.sha256(old_bytes).hexdigest(),
               "target_id": TARGET, "resource_id": RESOURCE, "url": EXACT,
               "status": status, "errors": errors, "request_id": result.request_id if result else None,
               "transport_calls": inner.calls, "target_counts": ledger.counts()[TARGET],
               "cumulative_counts": ledger.counts(), "cumulative_totals": ledger.attempt_totals(),
               "ledger_path": str(log), "ledger_sha256": sha(log),
               "unresolved_reservations": ledger.unresolved_attempt_ids(), "fatal": fatal,
               "report_queries": 0, "E1_requests": 0, "R2_science_runs": 0}
    save_new(output / "raw-receipt.json", receipt)
    print(json.dumps({"receipt": str(output / "raw-receipt.json"),
                      "status": status, "cumulative": receipt["cumulative_totals"], "fatal": fatal}, ensure_ascii=False))
    if fatal: raise SystemExit(2)


if __name__ == "__main__":
    main()
