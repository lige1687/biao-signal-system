"""One offline, stub-only completion check for B4's specific untested access guards."""

import copy
import hashlib
import importlib.util
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
OLD = Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20")
B1 = OLD / "source-evidence-recovery-batch1" / "access_log.py"
B2 = OLD / "source-evidence-recovery-batch2"
SOURCES = [B1, B2 / "gate0b_request_ledger_adapter.py", B2 / "targets.json",
           B2 / "CONTROLLER-GATE0B-REVIEW-2026-09-20.md",
           B2 / "test_gate0b_request_ledger_adapter.py"]
RESULT = HERE / "missing-access-guard-result.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_adapter():
    spec = importlib.util.spec_from_file_location("b4_guard_adapter", B2 / "gate0b_request_ledger_adapter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, status=200, location=None):
        self.status = status
        self.headers = {"Location": location} if location else {"Content-Type": "text/plain"}
        self.body = b"offline-stub-only"


class Stub:
    def __init__(self):
        self.pending = []
        self.urls = []

    def queue(self, url, hops):
        self.pending.extend([Response(301, url) for _ in range(hops - 1)] + [Response()])

    def request_once(self, url):
        self.urls.append(url)
        if not self.pending:
            raise AssertionError("unexpected stub transport call")
        return self.pending.pop(0)


def target_url(item):
    # E1 has no proved host: this synthetic global-allowlist URL proves counts only.
    host = item["exact_official_host"] or "www.bosera.com"
    path = "/Etrade/Search/offline" if host == "e.gtfund.com" else "/offline-only"
    return f"https://{host}{path}"


def fill(ledger, stub, targets, counts):
    for item in targets:
        target = item["target_id"]
        hops = counts[target]
        url = target_url(item)
        stub.queue(url, hops)
        ledger.run(target, "evidence", url, "offline_fixture", "budget_only",
                   resource_id=f"one-resource-{target}", document_identity=f"offline-{target}")
        if stub.pending:
            raise AssertionError("stub plan was not fully consumed")


def expect_exception(call, expected):
    try:
        call()
    except expected as exc:
        return f"{type(exc).__name__}: {exc}"
    raise AssertionError(f"expected {expected.__name__} before stub transport")


def case_mixed(adapter, payload, guard):
    fixture = copy.deepcopy(payload)
    item = next(t for t in fixture["targets"] if t["target_id"] == "P1-515130-2021")
    item["budget"]["http_hops"] = 4  # isolated fixture; original is 3
    stub = Stub()
    ledger = adapter.make_ledger(fixture, guard / "mixed.jsonl", stub)
    url = target_url(item)
    stub.queue(url, 2)
    ledger.run(item["target_id"], "search", url, "offline_fixture", "search", query_id="query-one")
    stub.queue(url, 1)
    ledger.run(item["target_id"], "evidence", url, "offline_fixture", "resource",
               resource_id="resource-one", document_identity="same-document")
    attempt = next(r["attempt_id"] for r in ledger._rows if r["record_type"] == "reservation" and r["resource_id"] == "resource-one")
    stub.queue(url, 1)
    ledger.run(item["target_id"], "evidence", url, "offline_fixture", "retry",
               resource_id="resource-one", retry_of_attempt_id=attempt,
               document_identity="same-document")
    count = ledger.counts()[item["target_id"]]
    assert count == {"search_queries": 1, "candidate_resources": 1, "evidence_attempts": 4}
    assert len(stub.urls) == 4 and ledger.unresolved_attempt_ids() == 0
    return {"fixture_only_target_hop_cap": 4, "original_target_hop_cap": 3,
            "search_301_then_200": "one query, two HTTP hops", "resource_and_valid_retry": "one resource, two further HTTP hops",
            "counts": count, "stub_calls": len(stub.urls), "ledger": str(ledger.log_path)}


def case_target_ten(adapter, payload, guard):
    fixture = copy.deepcopy(payload)
    item = next(t for t in fixture["targets"] if t["target_id"] == "P1-518850-2021")
    original = item["budget"]["http_hops"]
    item["budget"]["http_hops"] = 10
    stub = Stub(); ledger = adapter.make_ledger(fixture, guard / "target-ten.jsonl", stub)
    url = target_url(item)
    first_attempt = None
    for index in range(10):
        stub.queue(url, 1)
        ledger.run(item["target_id"], "evidence", url, "offline_fixture", "ten-hop-isolation",
                   resource_id="single-resource", document_identity="same-document",
                   retry_of_attempt_id=first_attempt)
        if first_attempt is None:
            first_attempt = next(r["attempt_id"] for r in ledger._rows if r["record_type"] == "reservation")
    before = len(stub.urls)
    refusal = expect_exception(lambda: ledger.run(item["target_id"], "evidence", url,
                                "offline_fixture", "eleventh-hop", resource_id="single-resource",
                                document_identity="same-document", retry_of_attempt_id=first_attempt), adapter.module.BudgetExceeded)
    assert before == len(stub.urls) == 10 and ledger.counts()[item["target_id"]]["evidence_attempts"] == 10
    return {"fixture_only_target_hop_cap": 10, "original_target_hop_cap": original,
            "attempted_next_hop": 11, "refusal": refusal, "stub_calls_before_after": [before, len(stub.urls)],
            "ledger": str(ledger.log_path)}


def case_group_45(adapter, payload, guard):
    fixture = copy.deepcopy(payload)
    p1 = [t for t in fixture["targets"] if t["target_id"].startswith("P1-")]
    first = p1[0]; first["budget"]["http_hops"] += 1  # leave one per-target slot after original44
    stub = Stub(); ledger = adapter.make_ledger(fixture, guard / "p1-fortyfive.jsonl", stub)
    original_counts = {t["target_id"]: next(o for o in payload["targets"] if o["target_id"] == t["target_id"])["budget"]["http_hops"] for t in p1}
    fill(ledger, stub, p1, original_counts)
    assert ledger.attempt_totals()["groups"]["P1"] == 44
    url = target_url(first);before=len(stub.urls)
    refusal = expect_exception(lambda: ledger.run(first["target_id"], "search", url,
                                "offline_fixture", "forty-fifth", query_id="fresh-query"), adapter.module.BudgetExceeded)
    assert len(stub.urls) == before == 44
    return {"original_P1_sum": 44, "fixture_only_first_target_cap": first["budget"]["http_hops"],
            "original_first_target_cap": first["budget"]["http_hops"] - 1,
            "attempted_next_hop": 45, "refusal": refusal, "stub_calls_before_after": [before, len(stub.urls)],
            "ledger": str(ledger.log_path)}


def case_batch_53(adapter, payload, guard):
    fixture = copy.deepcopy(payload)
    e1 = next(t for t in fixture["targets"] if t["target_id"].startswith("E1-"))
    e1["budget"]["http_hops"] = 9
    stub = Stub(); ledger = adapter.make_ledger(fixture, guard / "batch-fiftythree.jsonl", stub)
    ledger.group_attempt_caps["E1"] = 9  # fixture only: isolate 52 batch cap from 8 group cap
    counts = {t["target_id"]: t["budget"]["http_hops"] for t in payload["targets"]}
    fill(ledger, stub, fixture["targets"], counts)
    assert ledger.attempt_totals() == {"groups": {"E1": 8, "P1": 44}, "batch": 52}
    url=target_url(e1);before=len(stub.urls)
    refusal = expect_exception(lambda: ledger.run(e1["target_id"], "search", url,
                                "offline_fixture", "fifty-third", query_id="fresh-query"), adapter.module.BudgetExceeded)
    assert len(stub.urls) == before == 52
    return {"original_E1_group_cap": 8, "fixture_only_E1_target_and_group_cap": 9,
            "original_batch_cap": 52, "attempted_next_hop": 53, "refusal": refusal,
            "stub_calls_before_after": [before, len(stub.urls)], "ledger": str(ledger.log_path),
            "E1_URL_note": "Synthetic Bosera allowlist URL solely exercises budget counting; E1 official discovery remains unproved."}


def case_full_original_replay(adapter, payload, guard):
    stub = Stub(); log = guard / "all-original-targets.jsonl"
    ledger = adapter.make_ledger(payload, log, stub)
    counts = {t["target_id"]: t["budget"]["http_hops"] for t in payload["targets"]}
    fill(ledger, stub, payload["targets"], counts)
    reopened = adapter.make_ledger(payload, log, Stub())
    assert reopened.counts() == ledger.counts()
    assert reopened.attempt_totals() == {"groups": {"E1": 8, "P1": 44}, "batch": 52}
    assert reopened.unresolved_attempt_ids() == 0
    assert set(reopened.counts()) == {t["target_id"] for t in payload["targets"]}
    assert len(stub.urls) == 52
    return {"original_target_count": len(payload["targets"]), "original_caps_unchanged": True,
            "all_target_counts": reopened.counts(), "totals": reopened.attempt_totals(),
            "unresolved_reservations": reopened.unresolved_attempt_ids(), "stub_calls": len(stub.urls),
            "ledger": str(log), "E1_URL_note": "Synthetic Bosera allowlist URL solely exercises replay; no E1 official source claimed."}


def case_paths(adapter, payload, guard):
    item = next(t for t in payload["targets"] if t["exact_official_host"] == "e.gtfund.com")
    target=item["target_id"]; results=[]
    for label,url in [("initial_sibling", "https://e.gtfund.com/Etrade/SearchEvil"),
                      ("initial_other", "https://e.gtfund.com/Etrade/User/login"),
                      ("initial_credential", "https://e.gtfund.com/Etrade/Search?token=bad")]:
        stub=Stub();ledger=adapter.make_ledger(payload,guard/f"{label}.jsonl",stub)
        call=lambda:ledger.run(target,"evidence",url,"offline_fixture",label,resource_id=label)
        if label=="initial_credential":
            error=expect_exception(call,adapter.LedgerValidationError)
        else:
            response=call()
            assert response.body is None
            error=ledger._rows[-1]["error"]
            assert error and error.startswith("LedgerValidationError:")
        assert len(stub.urls)==0
        results.append({"case":label,"error":error,"stub_calls":0,"ledger":str(ledger.log_path)})
    for label,location in [("redirect_sibling","https://e.gtfund.com/Etrade/JijinTrade"),
                           ("redirect_host","https://example.org/Etrade/Search/x")]:
        stub=Stub();ledger=adapter.make_ledger(payload,guard/f"{label}.jsonl",stub)
        initial="https://e.gtfund.com/Etrade/Search/offline"
        stub.pending.append(Response(301,location))
        call=lambda:ledger.run(target,"evidence",initial,"offline_fixture",label,resource_id=label)
        if label=="redirect_host":
            error=expect_exception(call,adapter.LedgerValidationError)
        else:
            response=call()
            assert response.body is None
            error=ledger._rows[-1]["error"]
            assert error and error.startswith("LedgerValidationError:")
        assert len(stub.urls)==1
        results.append({"case":label,"error":error,"stub_calls":1,"ledger":str(ledger.log_path)})
    return results


def main():
    plan=json.loads((HERE/"storage-plan.json").read_text())
    contract=json.loads((HERE/"guard-contract.json").read_text())
    guard=Path(contract["external_write_paths"][0])
    assert guard == Path(plan["run_directory"])/"guard"
    mount=Path(plan["external_mount"])
    info=plistlib.loads(subprocess.check_output(["diskutil","info","-plist",str(mount)]))
    assert mount.stat().st_dev==plan["external_device"] and info["VolumeUUID"]==plan["external_uuid"]
    assert info.get("Internal")==0 and info.get("WritableVolume")==1
    assert os.statvfs(mount).f_bavail*os.statvfs(mount).f_frsize > plan["external_reserve_bytes"]+plan["estimated_bytes"]
    original={str(p):sha(p) for p in SOURCES}
    payload=json.loads((B2/"targets.json").read_text())
    assert len(payload["targets"])==16
    assert [sum(t["budget"][k] for t in payload["targets"] if t["target_id"].startswith("E1-")) for k in ("search_queries","candidate_resources","http_hops")] == [2,4,8]
    assert [sum(t["budget"][k] for t in payload["targets"] if t["target_id"].startswith("P1-")) for k in ("search_queries","candidate_resources","http_hops")] == [10,26,44]
    allowed_logs={"checker-stdout.log", "checker-stderr.log",
                  "checker-stdout-repair.log", "checker-stderr-repair.log"}
    assert guard.is_dir() and {p.name for p in guard.iterdir() if not p.name.startswith("._")} <= allowed_logs
    assert not RESULT.exists()
    assert guard.stat().st_dev==plan["external_device"]
    adapter=load_adapter()
    result={"schema_version":1,"status":"failed","pid":os.getpid(),"network_requests":0,
            "scientific_runs":0,"old_suite_reruns":0,"original_source_sha256":original,
            "original_payload_caps":{"E1":[2,4,8],"P1":[10,26,44],"batch_hops":52},
            "external_guard":str(guard),"external_device":guard.stat().st_dev,"cases":{}}
    try:
        for name,func in [("mixed_counters",case_mixed),("target_ten",case_target_ten),
                          ("P1_next_after_44",case_group_45),("batch_next_after_52",case_batch_53),
                          ("all_original_targets_replay",case_full_original_replay),("path_and_redirect",case_paths)]:
            result["cases"][name]=func(adapter,payload,guard)
        assert {str(p):sha(p) for p in SOURCES}==original
        assert sha(B2/"targets.json")==original[str(B2/"targets.json")]
        result["status"]="passed_offline_local_guards_only"
        result["original_sources_unchanged"]=True
        result["stub_transport_calls_total"]=4+10+44+52+52+2
        result["limits"]="Synthetic E1 URL and cap-expanded fixtures prove mechanics only; original targets/budgets are unchanged. The frozen ledger records path-wrapper validation errors as failed outcomes with body=None after reservation, while credential/host validation raises; every invalid path is stopped before the inner stub. Discovery coverage incomplete, Gate1B/R2 still blocked."
    except Exception as exc:
        result["failure"]={"type":type(exc).__name__,"message":str(exc)}
        raise
    finally:
        with RESULT.open("x") as file:
            json.dump(result,file,ensure_ascii=False,indent=2,sort_keys=True)
            file.write("\n")
    print(json.dumps({"status":result["status"],"cases":list(result["cases"]),
                      "result":str(RESULT)},ensure_ascii=False))


if __name__=="__main__":
    main()
