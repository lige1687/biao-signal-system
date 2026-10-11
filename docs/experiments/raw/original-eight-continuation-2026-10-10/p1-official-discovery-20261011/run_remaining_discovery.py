"""Three disclosed P1 archive requests, appended to the existing frozen request ledger."""

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
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MAX_BODY = 1_048_576
TIMEOUT = 8


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, data):
    with Path(path).open("x", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n")
        out.flush(); os.fsync(out.fileno())


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AuditedTransport:
    def __init__(self, root, module, ledger_path, *, fake=False):
        self.root, self.module, self.ledger_path, self.fake = root, module, ledger_path, fake
        self.action = None
        self.calls = []
        self.opener = build_opener(NoRedirect())

    def request_once(self, url):
        action = self.action
        if action is None or url != action["url"] or urlsplit(url).hostname != action["host"]:
            raise ValueError("transport action/host mismatch")
        if urlsplit(url).path.lower().endswith(".pdf"):
            raise ValueError("PDF request prohibited")
        rows = [json.loads(x) for x in self.ledger_path.read_text().splitlines()]
        latest = rows[-1]
        if (latest["record_type"] != "reservation" or latest["target_id"] != action["target_id"]
                or latest["query_id"] != action["query_id"] or latest["requested_url"] != url):
            raise ValueError("latest reservation does not bind method request")
        method = action["method"]
        body = urlencode(action.get("form_fields", {})).encode("ascii") if method == "POST" else None
        index = len(self.calls) + 1
        evidence = {"attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                    "target_id": action["target_id"], "query_id": action["query_id"],
                    "url": url, "method": method, "body_form_encoded": body.decode("ascii") if body else None,
                    "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
                    "content_type": "application/x-www-form-urlencoded" if body else None,
                    "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        method_path = self.root / f"method-hop-{index:03d}.json"
        save_new(method_path, evidence)
        if self.fake:
            status, headers, response_body = 200, {"Content-Type": "text/html"}, b"fake-only"
        else:
            req = Request(url, data=body, method=method,
                          headers={"User-Agent": "LeiSignal-research-source-discovery/1",
                                   **({"Content-Type": "application/x-www-form-urlencoded"} if body else {})})
            try:
                response = self.opener.open(req, timeout=TIMEOUT)
            except HTTPError as exc:
                response = exc
            with response:
                status = response.status
                headers = dict(response.headers.items())
                content_type = headers.get("Content-Type", headers.get("content-type", ""))
                response_body = b"" if "pdf" in content_type.lower() else response.read(MAX_BODY + 1)
        blocked = None
        if len(response_body) > MAX_BODY:
            blocked = "body exceeds 1 MiB"; response_body = response_body[:MAX_BODY]
        if "pdf" in (headers.get("Content-Type") or headers.get("content-type") or "").lower():
            blocked = "PDF response not collected"
        if method == "POST" and status in {301, 302, 303, 307, 308}:
            blocked = "POST redirect stopped without a second transport hop"
            headers = {k: v for k, v in headers.items() if k.lower() != "location"}
        raw_path = self.root / f"response-hop-{index:03d}.bin"
        with raw_path.open("xb") as out:
            out.write(response_body); out.flush(); os.fsync(out.fileno())
        record = {"index": index, "target_id": action["target_id"], "attempt_id": latest["attempt_id"],
                  "method_evidence_path": str(method_path), "method_evidence_sha256": digest(method_path),
                  "response_path": str(raw_path), "response_sha256": digest(raw_path),
                  "response_bytes": len(response_body), "status": status, "headers": headers,
                  "blocked": blocked}
        save_new(self.root / f"response-hop-{index:03d}-headers.json", record)
        self.calls.append(record)
        if blocked and not (method == "POST" and status in {301, 302, 303, 307, 308}):
            raise ValueError(blocked)
        return self.module.TransportResponse(status=status, headers=headers, body=response_body)


def load_adapter():
    p = Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py")
    spec = importlib.util.spec_from_file_location("remaining_frozen_adapter", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    contract = json.loads((HERE / "remaining-source-contract.json").read_text())
    for path, expected in contract["input_sha256"].items():
        if digest(path) != expected: raise ValueError(f"frozen input changed: {path}")
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
    stage = root / "remaining"
    existing = {p.name for p in stage.iterdir() if not p.name.startswith("._")}
    nonlog = {name for name in existing if not (name.startswith("stdout") or name.startswith("stderr") or name == "fake")}
    if stage.stat().st_dev != plan["external_device"] or nonlog:
        raise ValueError("remaining directory wrong device or nonempty")
    log_path = root / "access-ledger.jsonl"
    accepted = json.loads((HERE / "stage1-controller-review.json").read_text())
    old_bytes = log_path.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != accepted["sha256"] or old_bytes != Path(accepted["immutable_stage1_ledger_snapshot"]).read_bytes():
        raise ValueError("six-stage ledger snapshot mismatch")
    old_rows = [json.loads(x) for x in old_bytes.splitlines()]
    if (sum(x["record_type"] == "reservation" for x in old_rows) != 6
            or sum(x["record_type"] == "outcome" for x in old_rows) != 6
            or any(x["target_id"].startswith("E1-") for x in old_rows)):
        raise ValueError("stage1 reservation/outcome history mismatch")
    adapter = load_adapter()
    payload = json.loads((HERE / "amended-targets.json").read_text())
    targets = {x["target_id"]: x for x in payload["targets"]}
    actions = json.loads((HERE / "remaining-request-map.json").read_text())["requests"]
    if len(actions) != 3 or [x["target_id"] for x in actions] != ["P1-518850-2022", "P1-588000-2023", "P1-515130-2023"]:
        raise ValueError("three frozen actions mismatch")
    disclosures = [(root / "initial/responses/hop-004.bin", "name='pageIndex' value='3'"),
                   (root / "initial/responses/hop-005.bin", "name='pageIndex' value='3'"),
                   (root / "initial/responses/hop-001.bin", 'action="/column/infoList.json"')]
    for source, needle in disclosures:
        if needle not in source.read_text(errors="replace"):
            raise ValueError(f"disclosed action absent: {source}")
    bosera = (root / "initial/responses/hop-001.bin").read_text()
    for needle in ('method="post"', 'name="pageNo" value="1"', 'name="classid" value="0002000200030005"', 'name="fundCode" value="515130"'):
        if needle not in bosera: raise ValueError(f"exact official POST form field absent: {needle}")
    for action in actions:
        action["host"] = targets[action["target_id"]]["exact_official_host"]
        if urlsplit(action["url"]).hostname != action["host"]: raise ValueError("host mismatch")
    # One offline fake: identical ledger path adapter, exact POST method/body audit,
    # and second query refused before the fake transport is reached.
    fake_root = stage / ("fake-corrected" if (stage / "fake").exists() else "fake")
    fake_root.mkdir()
    fake_log = fake_root / "ledger.jsonl"
    fake_transport = AuditedTransport(fake_root, adapter.module, fake_log, fake=True)
    fake_ledger = adapter.make_ledger(payload, fake_log, fake_transport)
    post = actions[2]
    fake_transport.action = {**post, "query_id": "offline-post-method-check"}
    fake_result = fake_ledger.run(post["target_id"], "search", post["url"],
                                  targets[post["target_id"]]["official_source_family"],
                                  "official_archive_discovery", query_id="offline-post-method-check")
    fake_evidence = json.loads((fake_root / "method-hop-001.json").read_text())
    assert fake_evidence["method"] == "POST" and fake_evidence["url"] == post["url"]
    assert fake_evidence["body_form_encoded"] == urlencode(post["form_fields"])
    assert fake_evidence["attempt_id"] == fake_ledger._rows[0]["attempt_id"]
    before = len(fake_transport.calls)
    refusal = None
    try:
        fake_ledger.run(post["target_id"], "search", post["url"],
                        targets[post["target_id"]]["official_source_family"],
                        "official_archive_discovery", query_id="offline-second-query-refused")
    except adapter.module.BudgetExceeded as exc:
        refusal = str(exc)
    assert refusal and len(fake_transport.calls) == before == 1
    save_new(stage / "fake-check.json", {"network_calls": 0, "fake_transport_calls": before,
              "fake_request_id": fake_result.request_id, "method_evidence": fake_evidence,
              "refusal_before_transport": refusal, "fake_ledger_sha256": digest(fake_log)})
    transport = AuditedTransport(stage, adapter.module, log_path)
    ledger = adapter.make_ledger(payload, log_path, transport)
    if ledger.attempt_totals()["groups"]["P1"] != 6 or ledger.unresolved_attempt_ids():
        raise ValueError("six-stage cumulative counts mismatch")
    started = datetime.now(timezone.utc).isoformat()
    results = []
    fatal = None
    for action in actions:
        transport.action = action
        before = len(transport.calls)
        try:
            response = ledger.run(action["target_id"], "search", action["url"],
                                  targets[action["target_id"]]["official_source_family"],
                                  "official_archive_discovery", query_id=action["query_id"])
            related = [x for x in ledger._rows if x["record_type"] == "outcome" and x["request_id"] == response.request_id]
            status = "saved" if related and all(x["error"] is None and x["http_status"] == 200 for x in related) else "non_200_or_error"
            error = [x["error"] for x in related if x["error"]]
        except (adapter.LedgerValidationError, adapter.module.BudgetExceeded) as exc:
            response = None; status = "ledger_refused"; error = [f"{type(exc).__name__}: {exc}"]
        except Exception as exc:
            response = None; status = "control_error"; error = [f"{type(exc).__name__}: {exc}"]
            fatal = error[0]
        results.append({"target_id": action["target_id"], "query_id": action["query_id"],
                        "method": action["method"], "request_id": response.request_id if response else None,
                        "status": status, "errors": error, "transport_calls": transport.calls[before:],
                        "counts_after": ledger.counts()[action["target_id"]]})
        if fatal or ledger.unresolved_attempt_ids():
            fatal = fatal or "unresolved reservation"; break
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(), "command": [sys.executable, str(Path(__file__)), "--exact-three"],
               "contract_sha256": digest(HERE / "remaining-source-contract.json"),
               "stage1_ledger_sha256": accepted["sha256"], "stage1_prefix_preserved": log_path.read_bytes().startswith(old_bytes),
               "fake_check_path": str(stage / "fake-check.json"), "fake_check_sha256": digest(stage / "fake-check.json"),
               "ledger_path": str(log_path), "ledger_sha256": digest(log_path),
               "results": results, "transport_calls": transport.calls, "fatal": fatal,
               "counts": ledger.counts(), "totals": ledger.attempt_totals(),
               "unresolved_reservations": ledger.unresolved_attempt_ids(), "E1_requests": 0}
    save_new(stage / "real-receipt.json", receipt)
    print(json.dumps({"receipt": str(stage / "real-receipt.json"), "fatal": fatal,
                      "total_hops": receipt["totals"], "real_transport_calls": len(transport.calls)}, ensure_ascii=False))
    if fatal: raise SystemExit(2)


if __name__ == "__main__":
    main()
