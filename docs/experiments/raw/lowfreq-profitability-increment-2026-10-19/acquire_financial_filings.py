"""Acquire frozen-company original filings; preserve versions, never score effects.

HTTP is bounded across four workers by a durable append-only journal. An
explicit --resume may issue only operations absent from that journal; even a
failed or interrupted prior request is never retried automatically.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import fcntl
import hashlib
import json
import math
import os
import plistlib
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

PLAN_SHA256 = "bcb2d5b3a8a3efe9ef08d656fe92b60af80ab6a1e0f17b4b8cddcd662b091e07"
STORAGE_SHA256 = "99c1b2b77f24b4206b86f5efc611b223bbb8d24f1ac447147b9d25115c369979"
COHORT_SHA256 = "6f073e37809613469efe6cd2adb6b7ef1b4e77515e99e7149e1636d9e390cc16"
EXCLUDE_ANNUAL = ("摘要", "英文", "审计", "意见", "问询")
ANNUAL_RE = re.compile(r"(?<!\d)(20(?:1[3-9]|2[0-4]))\s*年?\s*(?:年度报告|年报)")
PDF_ID_RE = re.compile(r"\d+")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _create_json(path: Path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_progress(path: Path, data):
    temporary = path.with_name("progress.json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _check_storage(storage, out: Path, *, resume: bool):
    mount = Path(storage["external_mount"])
    run_directory = Path(storage["run_directory"])
    if (str(out) != storage["output"] or not os.path.ismount(mount)
            or mount.stat().st_dev != storage["external_device"]
            or Path(__file__).stat().st_dev == storage["external_device"]):
        raise ValueError("frozen external output identity mismatch")
    info = plistlib.loads(subprocess.run(["diskutil", "info", "-plist", str(mount)],
                                          capture_output=True, check=True, timeout=10).stdout)
    if info.get("VolumeUUID") != storage["external_uuid"]:
        raise ValueError("external volume UUID mismatch")
    task_parent = run_directory.parent
    base = task_parent.parent
    if (out.parent != run_directory or not base.is_dir()
            or base.stat().st_dev != storage["external_device"]
            or out.exists() != resume or run_directory.exists() != resume):
        raise ValueError("output must be create-only, or existing under explicit --resume")
    if task_parent.exists() and task_parent.stat().st_dev != storage["external_device"]:
        raise ValueError("task output parent changed devices")
    minimum = storage["external_reserve_bytes"] + (0 if resume else storage["estimated_bytes"])
    if shutil.disk_usage(mount).free < minimum:
        raise ValueError("external capacity below saved reserve and remaining estimate")


def _cohort_codes(cohort, source):
    if len(cohort["fixed_codes"]) != 600 or not cohort["no_replacements"]:
        raise ValueError("fixed historical cohort identity invalid")
    fields = source["fields"]
    if not {"code", "type", "ipoDate", "outDate"} <= set(fields):
        raise ValueError("source cohort identity fields missing")
    rows = [dict(zip(fields, row)) for row in source["data"]]
    asof = cohort["asof"]
    eligible = [row["code"] for row in rows
                if re.fullmatch(r"(?:sh\.60|sz\.00|sz\.30)\d{4}", row["code"])
                and str(row["type"]) == "1" and row["ipoDate"] <= asof
                and (not row["outDate"] or row["outDate"] > asof)]
    if len(eligible) != len(set(eligible)):
        raise ValueError("duplicate historical candidate code")
    ordered = sorted(eligible, key=lambda code: (
        hashlib.sha256(("lowfreq-20141231-v1|" + code).encode()).hexdigest(), code))[:600]
    quality_path = Path(cohort["price_quality_path"])
    if _sha(quality_path) != cohort["price_quality_sha256"]:
        raise ValueError("frozen core sample identity changed")
    saved = _json(quality_path)["sample_codes"]
    if len(ordered) != 600 or ordered != saved or ordered != cohort["fixed_codes"]:
        raise ValueError("reconstructed sample differs from frozen core 600")
    return [code.split(".")[-1] for code in ordered]


def _index_mapping(plan):
    entry = plan["stock_index_reuse"]
    path = Path(entry["path"])
    if _sha(path) != entry["sha256"]:
        raise ValueError("saved stock code-orgId index changed")
    doc = _json(path)
    if not isinstance(doc.get("stockList"), list):
        raise ValueError("saved stock index schema invalid")
    return {str(item["code"]): str(item["orgId"]) for item in doc["stockList"]
            if isinstance(item, dict) and item.get("code") and item.get("orgId")}


def _prior_pdfs(plan):
    records = {}
    for item in plan["prior_pdf_reuse"]:
        path = Path(item["path"])
        with path.open("rb") as handle:
            prefix = handle.read(5)
        if (_sha(path) != item["sha256"] or path.stat().st_size != item["bytes"]
                or prefix != b"%PDF-"):
            raise ValueError(f"old source PDF failed identity check: {item['code']}:{item['announcement_id']}")
        key = (item["code"], str(item["announcement_id"]))
        if key in records:
            raise ValueError("duplicate prior PDF identity")
        records[key] = item
    return records


def _pdf_url(item):
    locator = item.get("adjunctUrl")
    if not isinstance(locator, str) or not locator.strip():
        return None
    locator = locator.strip()
    parsed = urlparse(locator)
    if parsed.scheme in ("http", "https") and parsed.hostname and parsed.hostname.endswith(".cninfo.com.cn"):
        return locator
    if parsed.scheme or parsed.netloc or locator.startswith("//"):
        return None
    return urljoin("https://static.cninfo.com.cn/", locator.lstrip("/"))


def _annual_year(item, years):
    title = str(item.get("announcementTitle", ""))
    if any(word in title for word in EXCLUDE_ANNUAL):
        return None
    matched = ANNUAL_RE.search(title)
    if matched is None:
        return None
    year = int(matched.group(1))
    return year if year in years else None


def _payload(code, org_id, category, date_range, page):
    return {"pageNum": str(page), "pageSize": "30", "column": "szse", "tabName": "fulltext",
            "plate": "", "stock": f"{code},{org_id}" if org_id else "",
            "searchkey": "" if org_id else code, "secid": "", "category": category,
            "trade": "", "seDate": date_range, "sortName": "", "sortType": "", "isHLtitle": "true"}


class Controller:
    def __init__(self, plan, out: Path, codes, *, resume: bool):
        self.plan, self.out = plan, out
        self.journal = out / "journal.jsonl"
        self.raw = out / "raw"
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.last_start = None
        self.consecutive_failures = 0
        self.starts = {}
        self.finishes = {}
        self.reuses = {}
        self.counts = {"catalog": 0, "pdf": 0, "total": 0}
        self.states = {code: {"status": "pending", "catalogs": {}, "pdfs": [],
                              "missing_org_id": False} for code in codes}
        if resume:
            self._load_journal()

    def _load_journal(self):
        with self.journal.open(encoding="utf-8") as handle:
            for line in handle:
                entry = json.loads(line)
                op_id = entry["op_id"]
                if entry["event"] == "start":
                    if op_id in self.starts:
                        raise ValueError("duplicate durable request start")
                    self.starts[op_id] = entry
                    self.counts[entry["kind"]] += 1
                    self.counts["total"] += 1
                elif entry["event"] == "finish":
                    self.finishes[op_id] = entry
                elif entry["event"] == "reuse":
                    self.reuses[op_id] = entry
        if any(op_id not in self.starts for op_id in self.finishes):
            raise ValueError("finish without durable request start")
        if (self.counts["total"] > self.plan["max_total_http_operations"]
                or self.counts["catalog"] > self.plan["max_catalog_requests"]
                or self.counts["pdf"] > self.plan["max_pdf_requests"]):
            raise ValueError("saved journal exceeds frozen operation budget")

    def _append(self, entry):
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True, allow_nan=False)
        with self.journal.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _existing(self, op_id):
        if op_id not in self.starts:
            return None
        result = self.finishes.get(op_id)
        if result is None:
            return {"event": "interrupted_after_start", "op_id": op_id, "error": "no_finish; never_retry"}
        path = result.get("body_path")
        if path:
            body = Path(path)
            if not body.is_file() or _sha(body) != result["sha256"] or body.stat().st_size != result["bytes"]:
                return {**result, "successful": False,
                        "error": "saved_body_missing_or_changed; never_retry"}
        return result

    def _reserve(self, op_id, kind, method, url, params, data):
        with self.lock:
            existing = self._existing(op_id)
            if existing is not None:
                if existing.get("error") == "saved_body_missing_or_changed; never_retry":
                    self.stop.set()
                return existing
            limits = self.plan
            if (self.stop.is_set() or self.counts["total"] >= limits["max_total_http_operations"]
                    or self.counts[kind] >= limits["max_catalog_requests" if kind == "catalog" else "max_pdf_requests"]):
                self.stop.set()
                return {"event": "unissued", "op_id": op_id, "error": "global_stop_or_budget_exhausted"}
            if self.last_start is not None:
                delay = limits["global_min_start_interval_seconds"] - (time.monotonic() - self.last_start)
                if delay > 0:
                    time.sleep(delay)
            entry = {"event": "start", "op_id": op_id, "kind": kind, "method": method,
                     "url": url, "params": params, "data": data, "actual_started_utc": _utc(),
                     "sequence": self.counts["total"] + 1}
            self._append(entry)
            self.starts[op_id] = entry
            self.counts[kind] += 1
            self.counts["total"] += 1
            self.last_start = time.monotonic()
            return entry

    def request(self, op_id, kind, method, url, *, params=None, data=None):
        reserved = self._reserve(op_id, kind, method, url, params, data)
        if reserved["event"] != "start" or op_id in self.finishes:
            return reserved
        # The operation may have started before this process crashed. Never reissue it.
        if reserved is not self.starts[op_id]:
            raise AssertionError("request reservation identity lost")
        sequence = reserved["sequence"]
        body = bytearray()
        status = None
        error = None
        cap = self.plan["max_bytes_pdf_each" if kind == "pdf" else "max_bytes_json_each"]
        try:
            with requests.request(method, url, params=params, data=data, stream=True,
                                  allow_redirects=False, timeout=self.plan["per_operation_timeout_seconds"],
                                  headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}) as response:
                status = response.status_code
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    if len(body) + len(chunk) > cap:
                        body.extend(chunk[:cap - len(body)])
                        error = "body_above_saved_byte_cap; prefix_preserved"
                        break
                    body.extend(chunk)
        except requests.RequestException as exc:
            error = f"{type(exc).__name__}: {exc}"
        if status is None or not (200 <= status < 300):
            error = error or f"http_status_{status}"
        if not error and kind == "pdf" and not body.startswith(b"%PDF-"):
            error = "non_pdf_response"
        if not error and kind == "catalog":
            try:
                json.loads(body)
            except (ValueError, UnicodeDecodeError):
                error = "invalid_json_response"
        path = self.raw / f"{sequence:05d}-{kind}.body"
        with path.open("xb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        result = {"event": "finish", "op_id": op_id, "kind": kind, "status": status,
                  "completed_utc": _utc(), "bytes": len(body),
                  "sha256": hashlib.sha256(body).hexdigest(), "body_path": str(path),
                  "error": error, "successful": error is None}
        with self.lock:
            self._append(result)
            self.finishes[op_id] = result
            self.consecutive_failures = self.consecutive_failures + 1 if error else 0
            if status == 429 or self.consecutive_failures >= 2:
                self.stop.set()
        return result

    def reuse(self, op_id, item):
        with self.lock:
            if op_id in self.reuses:
                return self.reuses[op_id]
            entry = {"event": "reuse", "op_id": op_id, "kind": "pdf",
                     "source_path": item["path"], "bytes": item["bytes"],
                     "sha256": item["sha256"], "recorded_utc": _utc(), "successful": True}
            self._append(entry)
            self.reuses[op_id] = entry
            return entry

    def progress(self, code=None, state=None):
        with self.lock:
            if code is not None:
                self.states[code] = copy.deepcopy(state)
            payload = {"schema": "financial-filings-progress/1", "updated_utc": _utc(),
                       "operations": dict(self.counts), "global_stop": self.stop.is_set(),
                       "codes": self.states}
            _atomic_progress(self.out / "progress.json", payload)


def _catalog(controller, code, org_id, category_name):
    plan = controller.plan
    category = plan["categories"][category_name]
    items, pages = [], []
    total = None
    expected_pages = None
    issue = None
    for page in range(1, plan["max_pages_per_query"] + 1):
        if expected_pages is not None and page > expected_pages:
            break
        op_id = f"catalog:{code}:{category_name}:{page}"
        payload = _payload(code, org_id, category, plan["query_date_range"], page)
        record = controller.request(op_id, "catalog", "POST", plan["endpoint"], data=payload)
        if not record.get("successful"):
            issue = record.get("error") or "catalog_request_not_completed"
            break
        try:
            doc = _json(Path(record["body_path"]))
        except (ValueError, OSError):
            issue = "saved_catalog_json_unreadable"
            break
        count = doc.get("totalAnnouncement")
        returned = doc.get("announcements")
        if not str(count).isdigit():
            issue = "catalog_schema_missing_total_or_announcements"
            break
        count = int(count)
        if count == 0 and returned is None:
            returned = []
        if not isinstance(returned, list):
            issue = "catalog_schema_missing_total_or_announcements"
            break
        if count == 0 and returned:
            issue = "zero_total_with_nonempty_page"
            break
        if total is None:
            total = count
            expected_pages = max(1, math.ceil(total / plan["page_size"]))
        elif total != count:
            issue = "catalog_total_changed_between_pages"
            break
        exact = [item for item in returned if str(item.get("secCode", "")) == code]
        items.extend(exact)
        pages.append({"page": page, "raw_path": record["body_path"], "sha256": record["sha256"],
                      "returned": len(returned), "exact_code": len(exact),
                      "wrong_code": len(returned) - len(exact)})
        if page < expected_pages and not returned:
            issue = "empty_page_before_reported_total"
            break
    if issue is None and expected_pages is not None and len(pages) < expected_pages:
        issue = "unread_pages_max30_or_budget_stop"
    if issue is None and expected_pages is None:
        issue = "no_catalog_page_read"
    return {"status": "complete_empty" if issue is None and total == 0 else
            "complete" if issue is None else "incomplete",
            "reason": issue, "totalAnnouncement": total, "expected_pages": expected_pages,
            "pages_read": len(pages), "pages": pages, "exact_announcements": items,
            "missing_org_id": org_id is None}


def _targets(catalogs, years):
    targets = {}
    for category, catalog in catalogs.items():
        for item in catalog["exact_announcements"]:
            code = str(item.get("secCode", ""))
            ann_id = str(item.get("announcementId", ""))
            if not code or not PDF_ID_RE.fullmatch(ann_id):
                continue
            if category == "annual":
                year = _annual_year(item, years)
                if year is None:
                    continue
            else:
                year = None
            key = (code, ann_id)
            if key in targets:
                targets[key]["categories"].append(category)
                if year is not None:
                    targets[key]["report_year_from_title"] = year
                continue
            targets[key] = {"code": code, "announcement_id": ann_id, "categories": [category],
                            "report_year_from_title": year, "announcement_title": item.get("announcementTitle"),
                            "announcement_time_ms": item.get("announcementTime"),
                            "org_id_from_response": item.get("orgId"),
                            "adjunct_url_as_returned": item.get("adjunctUrl"),
                            "pdf_url": _pdf_url(item)}
    return list(targets.values())


def _code_worker(code, org_id, controller, prior):
    if controller.stop.is_set():
        return controller.states[code]
    state = {"status": "running", "catalogs": {}, "pdfs": [], "missing_org_id": org_id is None,
             "pdf_targets_expected": None, "pdfs_unissued_count": None,
             "pdfs_not_started_reason": None}
    controller.progress(code, state)
    for category in ("annual", "correction"):
        state["catalogs"][category] = _catalog(controller, code, org_id, category)
        controller.progress(code, state)
        if controller.stop.is_set():
            break
    if len(state["catalogs"]) == 2 and all(x["status"].startswith("complete") for x in state["catalogs"].values()):
        targets = _targets(state["catalogs"], set(controller.plan["annual_report_years"]))
        state["pdf_targets_expected"] = len(targets)
        for index, target in enumerate(targets, 1):
            op_id = f"pdf:{code}:{target['announcement_id']}"
            old = prior.get((code, target["announcement_id"]))
            if old:
                record = controller.reuse(op_id, old)
                target.update({"status": "reused", "source_path": record["source_path"],
                               "bytes": record["bytes"], "sha256": record["sha256"]})
            elif not target["pdf_url"]:
                target.update({"status": "missing", "reason": "actual_adjunct_url_missing_or_invalid"})
            else:
                record = controller.request(op_id, "pdf", "GET", target["pdf_url"])
                target.update({"status": "obtained" if record.get("successful") else "incomplete",
                               "reason": record.get("error"), "source_path": record.get("body_path"),
                               "bytes": record.get("bytes"), "sha256": record.get("sha256")})
            state["pdfs"].append(target)
            if index % 25 == 0:
                controller.progress(code, state)
            if controller.stop.is_set():
                break
        state["pdfs_unissued_count"] = len(targets) - len(state["pdfs"])
        if state["pdfs_unissued_count"]:
            state["pdfs_not_started_reason"] = "global_stop_or_budget_exhausted"
    else:
        state["pdfs_not_started_reason"] = "catalogs_incomplete; PDF selection not qualified"
    catalog_complete = len(state["catalogs"]) == 2 and all(
        x["status"].startswith("complete") for x in state["catalogs"].values())
    pdf_complete = catalog_complete and all(x["status"] in ("obtained", "reused") for x in state["pdfs"])
    if catalog_complete:
        expected = len(_targets(state["catalogs"], set(controller.plan["annual_report_years"])))
        pdf_complete = pdf_complete and len(state["pdfs"]) == expected
    state["status"] = "complete" if pdf_complete else "incomplete"
    controller.progress(code, state)
    return state


def _manifest(controller, plan_path, storage_path, cohort_path, codes):
    existing = sorted(controller.out.glob("manifest-*.json"))
    sequence = len(existing) + 1
    states = controller.states
    files = {entry["body_path"]: {"sha256": entry["sha256"], "bytes": entry["bytes"]}
             for entry in controller.finishes.values() if entry.get("body_path")}
    manifest = {"schema": "financial-filings-bulk-result/1", "created_utc": _utc(),
                "manifest_sequence": sequence, "plan_path": str(plan_path), "plan_sha256": _sha(plan_path),
                "storage_plan_path": str(storage_path), "storage_plan_sha256": _sha(storage_path),
                "cohort_path": str(cohort_path), "cohort_sha256": _sha(cohort_path),
                "script_sha256": _sha(Path(__file__)), "fixed_codes": codes,
                "actual_http_starts": dict(controller.counts),
                "successful_http": sum(x.get("successful", False) for x in controller.finishes.values()),
                "failed_or_interrupted_http": controller.counts["total"] - sum(
                    x.get("successful", False) for x in controller.finishes.values()),
                "prior_pdf_reuses": list(controller.reuses.values()),
                "raw_response_files": files, "journal_path": str(controller.journal),
                "journal_sha256_at_manifest": _sha(controller.journal),
                "code_status_counts": {key: sum(s["status"] == key for s in states.values())
                                       for key in ("complete", "incomplete", "pending", "running")},
                "codes": states, "global_stopped": controller.stop.is_set(),
                "all_600_complete": all(s["status"] == "complete" for s in states.values()),
                "market_effects_run": False}
    path = controller.out / f"manifest-{sequence:04d}.json"
    _create_json(path, manifest)
    return path


def run(plan_path: Path, storage_path: Path, *, resume: bool):
    plan_path, storage_path = Path(plan_path).resolve(), Path(storage_path).resolve()
    if _sha(plan_path) != PLAN_SHA256 or _sha(storage_path) != STORAGE_SHA256:
        raise ValueError("frozen bulk or storage plan changed")
    plan, storage = _json(plan_path), _json(storage_path)
    if (plan.get("schema") != "financial-filings-acquisition/1" or plan["max_total_http_operations"] != 14000
            or plan["max_catalog_requests"] != 6000 or plan["max_pdf_requests"] != 9000
            or plan["http_concurrency"] != 4 or plan["global_min_start_interval_seconds"] != .5
            or plan["per_operation_timeout_seconds"] != 40 or plan["retries"] != 0):
        raise ValueError("bulk scope or limits differ from frozen plan")
    out = Path(plan["output"])
    _check_storage(storage, out, resume=resume)
    cohort_path = Path(plan["cohort_path"])
    if (_sha(cohort_path) != plan["cohort_sha256"] or _sha(cohort_path) != COHORT_SHA256):
        raise ValueError("financial cohort binding changed")
    cohort = _json(cohort_path)
    source_path = Path(cohort["source_cohort"]["path"])
    if _sha(source_path) != cohort["source_cohort"]["sha256"]:
        raise ValueError("original historical cohort changed")
    codes = _cohort_codes(cohort, _json(source_path))
    mapping = _index_mapping(plan)
    prior = _prior_pdfs(plan)
    if not resume:
        out.parent.parent.mkdir(parents=False, exist_ok=True)
        if out.parent.parent.stat().st_dev != storage["external_device"]:
            raise ValueError("task output parent changed devices before creation")
        out.parent.mkdir(parents=False, exist_ok=False)
        out.mkdir(parents=False, exist_ok=False)
        (out / "raw").mkdir()
        _create_json(out / "run-meta.json", {"plan_sha256": PLAN_SHA256,
                    "storage_plan_sha256": STORAGE_SHA256, "cohort_sha256": COHORT_SHA256,
                    "script_sha256": _sha(Path(__file__)), "created_utc": _utc(), "codes": codes})
        (out / "journal.jsonl").open("x").close()
    else:
        meta = _json(out / "run-meta.json")
        if (meta["plan_sha256"] != PLAN_SHA256 or meta["storage_plan_sha256"] != STORAGE_SHA256
                or meta["cohort_sha256"] != COHORT_SHA256 or meta["script_sha256"] != _sha(Path(__file__))
                or meta["codes"] != codes or not (out / "raw").is_dir()):
            raise ValueError("resume must use same run, cohort and script")
    with (out / "journal.jsonl").open("a", encoding="utf-8") as run_lock:
        try:
            fcntl.flock(run_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("same frozen run is already active") from exc
        try:
            controller = Controller(plan, out, codes, resume=resume)
            controller.progress()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                future_to_code = {pool.submit(_code_worker, code, mapping.get(code), controller, prior): code for code in codes}
                for future in concurrent.futures.as_completed(future_to_code):
                    code = future_to_code[future]
                    try:
                        future.result()
                    except Exception as exc:
                        state = controller.states[code]
                        state["status"] = "incomplete"
                        state["error"] = f"worker_error:{type(exc).__name__}:{exc}"
                        controller.progress(code, state)
                        controller.stop.set()
            path = _manifest(controller, plan_path, storage_path, cohort_path, codes)
            return {"manifest": str(path), "manifest_sha256": _sha(path),
                    "actual_http_starts": dict(controller.counts),
                    "all_600_complete": all(s["status"] == "complete" for s in controller.states.values())}
        finally:
            fcntl.flock(run_lock.fileno(), fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--storage-plan", required=True, type=Path)
    parser.add_argument("--resume", action="store_true", help="same run, issue only never-started operations")
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.storage_plan, resume=args.resume), ensure_ascii=False))


if __name__ == "__main__":
    main()
