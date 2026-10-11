"""Append bounded official P1 archive discovery to the accepted nine-hop ledger."""

import argparse
import hashlib
import importlib.util
import json
import os
import plistlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
JS_URL = "https://e.gtfund.com/Public/static/etrade/1/dist/js/search_index.js?v=hy187"
MAX_BODY = 1_048_576
TIMEOUT = 8


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, obj):
    with Path(path).open("x", encoding="utf-8") as out:
        json.dump(obj, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())


def import_adapter():
    p = Path("docs/experiments/raw/factor-b4-price-basis-recovery-2026-09-20/source-evidence-recovery-batch2/gate0b_request_ledger_adapter.py")
    spec = importlib.util.spec_from_file_location("additional_frozen_adapter", p)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    return adapter


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ExactPathTransport:
    def __init__(self, inner, adapter):
        self.inner, self.adapter = inner, adapter

    def request_once(self, url):
        if url != JS_URL:
            self.adapter.check_path(url)
        return self.inner.request_once(url)


class AuditedOneHop:
    def __init__(self, directory, module, ledger_path, fake=False):
        self.directory, self.module, self.ledger_path, self.fake = directory, module, ledger_path, fake
        self.action = None
        self.calls = []
        self.opener = build_opener(NoRedirect())

    def request_once(self, url):
        action = self.action
        if action is None or url != action["url"] or urlsplit(url).hostname != action["host"]:
            raise ValueError("action URL or host differs from bound request")
        if urlsplit(url).path.lower().endswith(".pdf"):
            raise ValueError("report PDF request prohibited")
        latest = json.loads(self.ledger_path.read_text().splitlines()[-1])
        if (latest["record_type"] != "reservation" or latest["target_id"] != action["target_id"]
                or latest["requested_url"] != url or latest["query_id"] != action.get("query_id")
                or latest["resource_id"] != action.get("resource_id")):
            raise ValueError("latest reservation does not bind transport method")
        body = urlencode(action.get("form", {})).encode("ascii") if action["method"] == "POST" else None
        index = len(self.calls) + 1
        method = {"attempt_id": latest["attempt_id"], "request_id": latest["request_id"],
                  "target_id": action["target_id"], "query_id": action.get("query_id"),
                  "resource_id": action.get("resource_id"), "url": url,
                  "method": action["method"], "body_form_encoded": body.decode("ascii") if body else None,
                  "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
                  "recorded_before_transport_utc": datetime.now(timezone.utc).isoformat()}
        mp = self.directory / f"method-{index:03d}.json"
        write_new(mp, method)
        if self.fake:
            status, headers, response_body = 200, {"Content-Type": "text/plain"}, b"offline-fake"
        else:
            request = Request(url, data=body, method=action["method"], headers={
                "User-Agent": "LeiSignal-research-source-discovery/1",
                **({"Content-Type": "application/x-www-form-urlencoded"} if body else {})})
            try:
                response = self.opener.open(request, timeout=TIMEOUT)
            except HTTPError as exc:
                response = exc
            with response:
                status, headers = response.status, dict(response.headers.items())
                ctype = headers.get("Content-Type", headers.get("content-type", ""))
                response_body = b"" if "pdf" in ctype.lower() else response.read(MAX_BODY + 1)
        blocked = None
        if len(response_body) > MAX_BODY:
            blocked = "response >1MiB"; response_body = response_body[:MAX_BODY]
        if "pdf" in (headers.get("Content-Type") or headers.get("content-type") or "").lower():
            blocked = "PDF response suppressed"
        if status in {301, 302, 303, 307, 308}:
            blocked = "redirect stopped; no second hop or method change"
        rp = self.directory / f"response-{index:03d}.bin"
        with rp.open("xb") as out:
            out.write(response_body); out.flush(); os.fsync(out.fileno())
        hp = self.directory / f"headers-{index:03d}.json"
        record = {"index": index, "attempt_id": latest["attempt_id"], "target_id": action["target_id"],
                  "method_path": str(mp), "method_sha256": sha(mp), "response_path": str(rp),
                  "response_sha256": sha(rp), "status": status, "headers": headers,
                  "bytes_saved": len(response_body), "blocked": blocked}
        write_new(hp, record)
        self.calls.append({"record_path": str(hp), **record})
        if blocked:
            raise ValueError(blocked)
        return self.module.TransportResponse(status=status, headers=headers, body=response_body)


def ledger_for(adapter, targets, path, inner):
    caps = adapter.batch1_caps(targets)
    groups = {tid: ("E1" if tid.startswith("E1-") else "P1") for tid in caps}
    hosts = {x["exact_official_host"] for x in targets["targets"] if x["exact_official_host"]}
    return adapter.RequestLedger(path, caps, ExactPathTransport(inner, adapter),
                                 allowed_hosts=hosts, group_for_target=groups,
                                 group_attempt_caps={"E1": 8, "P1": 44}, batch_attempt_cap=52)


def offline_exact_js_check(stage, adapter, targets, base_action):
    directory = stage / "fake"
    directory.mkdir()
    log = directory / "ledger.jsonl"
    inner = AuditedOneHop(directory, adapter.module, log, fake=True)
    ledger = ledger_for(adapter, targets, log, inner)
    js = dict(base_action)
    js["query_id"] = None
    js["resource_id"] = "offline-js-allowed"
    inner.action = js
    ledger.run(js["target_id"], "evidence", JS_URL, "Guotai Fund",
               "exact_disclosed_JS_source_text", resource_id=js["resource_id"])
    assert len(inner.calls) == 1 and inner.calls[0]["status"] == 200
    # Rejection must occur before the fake transport, with an unrelated static path.
    bad = dict(js); bad["url"] = "https://e.gtfund.com/Public/static/etrade/1/dist/js/other.js"
    inner.action = bad
    response = ledger.run(js["target_id"], "search", bad["url"], "Guotai Fund",
                          "offline_denied_path", query_id="offline-bad-static")
    assert response.body is None and len(inner.calls) == 1
    outcomes = [x for x in ledger._rows if x["record_type"] == "outcome"]
    assert "LedgerValidationError" in (outcomes[-1]["error"] or "")
    write_new(stage / "fake-check.json", {"network_calls": 0, "allowed_exact_js": True,
              "other_static_rejected_before_fake_transport": True, "fake_calls": 1,
              "fake_ledger_sha256": sha(log)})


def bosera_links(path):
    data = json.loads(path.read_text())
    section = data["data"]
    if section.get("fundCode") != "515130": raise ValueError("Bosera JSON wrong fundCode")
    links = {}
    ids = []
    for item in section["resultList"]:
        ids.append(item["id"])
        title = item.get("title", "")
        match = re.fullmatch(r"博时沪深300交易型开放式指数证券投资基金(202[1-4])年年度报告(?:摘要)?", title)
        if match and not title.endswith("摘要"):
            url = urljoin("https://www.bosera.com", item.get("url", ""))
            if (urlsplit(url).hostname != "www.bosera.com" or "/column/infoDetail.do" != urlsplit(url).path
                    or "fundCode=515130" not in urlsplit(url).query):
                raise ValueError("Bosera annual item URL/code mismatch")
            links[f"P1-515130-{match.group(1)}"] = {"title": title, "article_url": url,
                            "raw_response_path": str(path), "raw_response_sha256": sha(path),
                            "official_item_id": item["id"], "announcement_date": item.get("originalTime")}
    return section["paginator"], ids, links


def foods_links(path):
    html = path.read_text(errors="replace")
    if not re.search(r'name="fundcode"\s+value="515170"', html):
        raise ValueError("ChinaAMC returned wrong fundcode")
    links = {}
    for href, title in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*年度报告)</a>', html):
        title = title.strip()
        match = re.search(r'华夏中证细分食品饮料产业主题交易型开放式指数证券投资基金(202[23])年年度报告$', title)
        if not match: continue
        url = urljoin("https://www.chinaamc.com/product/publishGgList.do", href)
        if urlsplit(url).hostname != "www.chinaamc.com" or not urlsplit(url).path.startswith("/c/"):
            raise ValueError("ChinaAMC annual article URL mismatch")
        links[f"P1-515170-{match.group(1)}"] = {"title": title, "article_url": url,
                       "raw_response_path": str(path), "raw_response_sha256": sha(path)}
    return html, links


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--exact-additional", action="store_true", required=True)
    parser.parse_args()
    contract = json.loads((HERE / "additional-source-contract.json").read_text())
    for path, expected in contract["input_sha256"].items():
        if sha(path) != expected: raise ValueError(f"frozen source changed: {path}")
    plan = json.loads((HERE / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (mount.stat().st_dev != plan["external_device"] or info.get("VolumeUUID") != plan["external_uuid"]
            or info.get("Internal") != 0 or info.get("WritableVolume") != 1):
        raise ValueError("external identity mismatch")
    free = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    if free <= plan["external_reserve_bytes"] + contract["expected_additional_ordinary_bytes"]:
        raise ValueError("external capacity insufficient")
    root = Path(contract["external_run_directory"]); stage = root / "additional"
    if stage.stat().st_dev != plan["external_device"] or any(p.name not in {"stdout.log", "stderr.log"} and not p.name.startswith("._") for p in stage.iterdir()):
        raise ValueError("additional directory not pristine or wrong device")
    log = root / "access-ledger.jsonl"
    old_bytes = log.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != "88630f88d8edd643914acfc468129f0e2991cc2476922ad2736d1f329385154a":
        raise ValueError("accepted nine-hop ledger hash mismatch")
    old_rows = [json.loads(x) for x in old_bytes.splitlines()]
    if (sum(x["record_type"] == "reservation" for x in old_rows) != 9
            or sum(x["record_type"] == "outcome" for x in old_rows) != 9):
        raise ValueError("accepted nine-hop reservations/outcomes mismatch")
    snapshot = root / "accepted-nine-ledger-snapshot.jsonl"
    with snapshot.open("xb") as out:
        out.write(old_bytes); out.flush(); os.fsync(out.fileno())
    adapter = import_adapter()
    payload = json.loads((HERE / "additional-targets.json").read_text())
    targets = {x["target_id"]: x for x in payload["targets"]}
    entries = json.loads((HERE / "additional-request-map.json").read_text())["entries"]
    if len(entries) != 19 or [e["id"] for e in entries[:15]] != [f"ADD-BOSE-PAGE-{n:02d}" for n in range(2, 17)]:
        raise ValueError("frozen additional request map mismatch")
    if [e["id"] for e in entries[15:]] != ["ADD-FOODS-PAGE-2", "ADD-FOODS-PAGE-3", "ADD-GUOTAI-JS", "ADD-GUOTAI-REPORT"]:
        raise ValueError("frozen later request map mismatch")
    for e in entries:
        if e["url"] is not None and urlsplit(e["url"]).hostname != targets[e["target_id"]]["exact_official_host"]:
            raise ValueError("request host mismatches target")
    offline_exact_js_check(stage, adapter, payload, {**entries[17], "host": targets[entries[17]["target_id"]]["exact_official_host"]})
    inner = AuditedOneHop(stage, adapter.module, log)
    ledger = ledger_for(adapter, payload, log, inner)
    if ledger.attempt_totals()["groups"]["P1"] != 9 or ledger.unresolved_attempt_ids():
        raise ValueError("ledger replay/count mismatch")
    old_counts = ledger.counts()
    started = datetime.now(timezone.utc).isoformat()
    performed = []
    found = {}
    stopped = {}
    fatal = None
    prior_bosera = root / "remaining/response-hop-003.bin"
    paginator, prev_ids, old_found = bosera_links(prior_bosera)
    assert paginator["page"] == 1 and paginator["total"] == 16
    found.update(old_found)

    def call(entry):
        nonlocal fatal
        before = len(inner.calls)
        e = {**entry, "host": targets[entry["target_id"]]["exact_official_host"]}
        e["query_id"] = e["id"] if e["role"] == "search" else None
        e["resource_id"] = e["id"] if e["role"] == "evidence" else None
        inner.action = e
        try:
            result = ledger.run(e["target_id"], e["role"], e["url"],
                                targets[e["target_id"]]["official_source_family"],
                                "bounded_official_archive_discovery", query_id=e["query_id"],
                                resource_id=e["resource_id"])
            outcomes = [x for x in ledger._rows if x["record_type"] == "outcome" and x["request_id"] == result.request_id]
            okay = len(outcomes) == 1 and outcomes[0]["error"] is None and outcomes[0]["http_status"] == 200
            status = "saved_200" if okay else "source_failed"
            errors = [x["error"] or f"HTTP {x['http_status']}" for x in outcomes if x["error"] or x["http_status"] != 200]
        except (adapter.LedgerValidationError, adapter.module.BudgetExceeded) as exc:
            result = None; status = "ledger_refused"; errors = [f"{type(exc).__name__}: {exc}"]
        except Exception as exc:
            result = None; status = "control_error"; errors = [f"{type(exc).__name__}: {exc}"]
            fatal = errors[0]
        calls = inner.calls[before:]
        performed.append({"id": e["id"], "target_id": e["target_id"], "role": e["role"],
                          "method": e["method"], "status": status, "errors": errors,
                          "request_id": result.request_id if result else None, "transport_calls": calls})
        if ledger.unresolved_attempt_ids(): fatal = "unresolved real reservation"
        return calls[0]["response_path"] if status == "saved_200" and len(calls) == 1 and not fatal else None

    for entry in entries[:15]:
        if len([k for k in found if k.startswith("P1-515130-")]) == 4:
            stopped["515130"] = "all four exact annual report links discovered"; break
        page = int(entry["form"]["pageNo"])
        if paginator["page"] != page - 1 or page > paginator["total"]:
            stopped["515130"] = "prior actual page does not disclose next sequential page"; break
        path = call(entry)
        if not path:
            stopped["515130"] = "request failed or non-200"; break
        try:
            p, ids, links = bosera_links(Path(path))
            if p["page"] != page or p["total"] < page or not ids or set(ids) & set(prev_ids):
                raise ValueError("Bosera wrong page/terminal/repeated list")
            for key, value in links.items():
                if key in found and found[key]["article_url"] != value["article_url"]:
                    raise ValueError("Bosera target-year annual link conflict")
            found.update(links); paginator, prev_ids = p, ids
        except Exception as exc:
            stopped["515130"] = f"response validation stopped product: {type(exc).__name__}: {exc}"; break
    if "515130" not in stopped:
        stopped["515130"] = "page16 reached or all exact annual report links discovered"
    foods_page = root / "continuation/responses/hop-001.bin"
    _, initial_foods = foods_links(foods_page)
    found.update(initial_foods)
    for entry in entries[15:17]:
        if len([k for k in found if k.startswith("P1-515170-")]) == 3:
            stopped["515170"] = "all three exact annual links already discovered"; break
        page = int(entry["form"]["pageIndex"])
        if page == 3 and not any(x["id"] == "ADD-FOODS-PAGE-2" and x["status"] == "saved_200" for x in performed):
            stopped["515170"] = "page2 not actually observed"; break
        path = call(entry)
        if not path:
            stopped["515170"] = "request failed or non-200"; break
        try:
            html, links = foods_links(Path(path))
            if not re.search(r'class="cur"\s+onclick="thisPage\(' + str(page) + r'\)"', html):
                raise ValueError("ChinaAMC wrong or repeated page")
            for key, value in links.items():
                if key in found and found[key]["article_url"] != value["article_url"]:
                    raise ValueError("ChinaAMC target-year annual link conflict")
            found.update(links)
        except Exception as exc:
            stopped["515170"] = f"response validation stopped product: {type(exc).__name__}: {exc}"; break
    if "515170" not in stopped:
        stopped["515170"] = "page3 reached or all exact annual links discovered"
    js = entries[17]
    js_path = call(js) if not fatal else None
    if js_path:
        raw = Path(js_path).read_bytes()
        js_text = raw.decode("utf-8", "replace")
        if any(word in js_text.lower() for word in ("password", "token", "authorization")):
            stopped["516220"] = "JS mentions credential-related fields; no report query"
        else:
            # An exact report request requires a complete literal URL/method/required-field
            # binding. The source is retained for controller review if any component is dynamic.
            stopped["516220"] = "JS source saved; no report query without fully literal method/path/fields binding"
    else:
        stopped["516220"] = "JS source request failed or unqualified"
    stage_queries = sum(ledger.counts()[tid]["search_queries"] - old_counts[tid]["search_queries"] for tid in old_counts if tid.startswith("P1-"))
    stage_resources = sum(ledger.counts()[tid]["candidate_resources"] - old_counts[tid]["candidate_resources"] for tid in old_counts if tid.startswith("P1-"))
    stage_hops = ledger.attempt_totals()["groups"]["P1"] - 9
    if stage_queries > 19 or stage_resources > 1 or stage_hops > 22:
        fatal = "additional stage cap exceeded"
    receipt = {"schema_version": 1, "pid": os.getpid(), "started_utc": started,
               "ended_utc": datetime.now(timezone.utc).isoformat(),
               "command": [sys.executable, str(Path(__file__)), "--exact-additional"],
               "contract_sha256": sha(HERE / "additional-source-contract.json"),
               "old_ledger_sha256": sha(snapshot), "old_prefix_preserved": log.read_bytes().startswith(old_bytes),
               "snapshot_path": str(snapshot), "fake_check_path": str(stage / "fake-check.json"),
               "fake_check_sha256": sha(stage / "fake-check.json"),
               "performed": performed, "found": found, "stopped": stopped,
               "stage_counts": {"queries": stage_queries, "resources": stage_resources, "hops": stage_hops},
               "cumulative_counts": ledger.counts(), "cumulative_totals": ledger.attempt_totals(),
               "ledger_path": str(log), "ledger_sha256": sha(log), "unresolved_reservations": ledger.unresolved_attempt_ids(),
               "fatal": fatal, "E1_requests": 0}
    write_new(stage / "real-receipt.json", receipt)
    print(json.dumps({"receipt": str(stage / "real-receipt.json"), "stage_counts": receipt["stage_counts"],
                      "found": len(found), "fatal": fatal}, ensure_ascii=False))
    if fatal: raise SystemExit(2)


if __name__ == "__main__":
    main()
