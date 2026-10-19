"""Bounded CNINFO original-filing probe; no financial extraction or market effects.

Run only with the frozen probe plan and its saved external storage plan. Every
HTTP attempt, including an index lookup, page, and PDF, uses one shared budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

PLAN_SHA256 = "70c16afe1a60c9d2c9f94d07868121f44ba2ffeee5c2aabfe74ef9aae0157de7"
STORAGE_PLAN_SHA256 = "2bb0d1f1a89e7b0e70e0f78a68e22e0a9802639706c869b1519da0a07796437c"
CATEGORIES = {"年报": "category_ndbg_szsh", "补充更正": "category_bcgz_szsh"}
EXCLUDE_FULL = ("摘要", "英文", "审计", "意见")
REVISION_WORDS = ("修订", "更正", "补充", "更新", "重述", "追溯")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)


def _check_storage(storage, out: Path, expected_out: str):
    mount = Path(storage["external_mount"])
    parent = Path(storage["output"])
    if (str(out) != expected_out or out.parent != parent or not parent.is_dir()
            or out.exists() or not os.path.ismount(mount)):
        raise ValueError("bound external result parent is not ready or output already exists")
    device = storage["external_device"]
    if mount.stat().st_dev != device or parent.stat().st_dev != device or Path(__file__).stat().st_dev == device:
        raise ValueError("external device identity mismatch")
    result = subprocess.run(["diskutil", "info", "-plist", str(mount)],
                            capture_output=True, check=True, timeout=10)
    info = plistlib.loads(result.stdout)
    if info.get("VolumeUUID") != storage["external_uuid"]:
        raise ValueError("external volume UUID mismatch")
    if shutil.disk_usage(mount).free < storage["external_reserve_bytes"] + storage["estimated_bytes"]:
        raise ValueError("external capacity below saved estimate and reserve")


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


class Budget:
    def __init__(self, plan, out: Path):
        self.limit = plan["max_total_data_operations"]
        self.delay = plan["request_delay_seconds"]
        self.timeout = plan["timeout_seconds"]
        self.json_cap = plan["max_bytes_json"]
        self.pdf_cap = plan["max_bytes_pdf_each"]
        self.attempts = []
        self.last_request = None
        self.consecutive_failures = 0
        self.stopped_reason = None
        self.out = out

    def request(self, kind: str, method: str, url: str, *, params=None, data=None):
        if self.stopped_reason or len(self.attempts) >= self.limit:
            self.stopped_reason = self.stopped_reason or "18_operation_budget_exhausted"
            return None
        if self.last_request is not None:
            wait = self.delay - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
        attempt_id = len(self.attempts) + 1
        attempt = {"id": attempt_id, "kind": kind, "method": method, "url": url,
                   "params": params, "data": data, "started_utc": _timestamp(),
                   "status": None, "bytes": 0, "sha256": None, "body_path": None,
                   "error": None, "completed_utc": None}
        self.attempts.append(attempt)
        self.last_request = time.monotonic()
        cap = self.pdf_cap if kind == "pdf" else self.json_cap
        body = bytearray()
        try:
            with requests.request(method, url, params=params, data=data, stream=True,
                                  allow_redirects=False, timeout=self.timeout,
                                  headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"}) as response:
                attempt["status"] = response.status_code
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    if len(body) + len(chunk) > cap:
                        body.extend(chunk[:cap - len(body)])
                        attempt["error"] = "body_exceeds_plan_byte_cap; capped prefix saved"
                        break
                    body.extend(chunk)
        except requests.RequestException as exc:
            attempt["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            self.last_request = time.monotonic()
            body_path = self.out / f"attempt-{attempt_id:02d}-{kind}.body"
            with body_path.open("xb") as handle:
                handle.write(body)
            attempt["body_path"] = str(body_path)
            attempt["bytes"] = len(body)
            attempt["sha256"] = hashlib.sha256(body).hexdigest()
            attempt["completed_utc"] = _timestamp()
            _write_json(self.out / f"attempt-{attempt_id:02d}.json", attempt)
        if attempt["status"] == 429:
            self.stopped_reason = "http_429"
        failed = attempt["error"] is not None or attempt["status"] is None or not (200 <= attempt["status"] < 300)
        self.consecutive_failures = self.consecutive_failures + 1 if failed else 0
        if self.consecutive_failures >= 2:
            self.stopped_reason = self.stopped_reason or "two_consecutive_http_or_network_failures"
        return bytes(body) if not failed else None


def _response_json(budget, kind, method, url, *, params=None, data=None):
    body = budget.request(kind, method, url, params=params, data=data)
    if body is None:
        return None
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        budget.attempts[-1]["error"] = f"invalid_json: {exc}"
        with (budget.out / f"attempt-{budget.attempts[-1]['id']:02d}.json").open("w", encoding="utf-8") as handle:
            json.dump(budget.attempts[-1], handle, ensure_ascii=False, indent=2)
        budget.consecutive_failures += 1
        if budget.consecutive_failures >= 2:
            budget.stopped_reason = "two_consecutive_http_or_network_failures"
        return None


def _payload(case, org_id):
    code = case["code"]
    return {"pageNum": "1", "pageSize": "30", "column": "szse", "tabName": "fulltext",
            "plate": "", "stock": f"{code},{org_id}" if org_id else "",
            "searchkey": "" if org_id else code, "secid": "",
            "category": CATEGORIES[case["category"]], "trade": "",
            "seDate": case["seDate"], "sortName": "", "sortType": "", "isHLtitle": "true"}


def _query_pages(budget, endpoint, case, org_id, page2_slots):
    payload = _payload(case, org_id)
    first = _response_json(budget, "announcement", "POST", endpoint, data=payload)
    if first is None:
        return [], {"reason": "first_page_failed", "total": None, "pages_read": 0}, page2_slots
    total = first.get("totalAnnouncement")
    items = first.get("announcements")
    if not isinstance(items, list) or not isinstance(total, (str, int)) or not str(total).isdigit():
        return [], {"reason": "unexpected_response_schema", "total": total, "pages_read": 1}, page2_slots
    total = int(total)
    pages_read = 1
    reason = None
    if total > 30 and page2_slots > 0 and not budget.stopped_reason:
        page2_slots -= 1
        page2 = _response_json(budget, "announcement", "POST", endpoint,
                               data={**payload, "pageNum": "2"})
        if isinstance(page2, dict) and isinstance(page2.get("announcements"), list):
            items.extend(page2["announcements"])
            pages_read = 2
        else:
            reason = "page2_failed"
    if total > pages_read * 30:
        reason = reason or "more_pages_not_read_within_frozen_budget"
    exact = [item for item in items if str(item.get("secCode", "")) == case["code"]]
    return exact, {"reason": reason, "total": total, "pages_read": pages_read,
                   "returned": len(items), "exact_code": len(exact), "org_id_from_index": org_id,
                   "fallback_searchkey_without_stock": org_id is None}, page2_slots


def _year_in_title(title, year):
    return bool(re.search(rf"(?<!\d){year}\s*年?", title))


def _is_full_annual(title, year):
    return (_year_in_title(title, year) and ("年度报告" in title or "年报" in title)
            and not any(word in title for word in EXCLUDE_FULL))


def _published(item):
    value = item.get("announcementTime")
    return value if isinstance(value, (int, float)) else float("inf")


def _select(items, plan):
    cases = {(case["code"], year) for case in plan["query_cases"] for year in case["report_years"]}
    selected, findings = [], []
    for code, year in sorted(cases):
        matching = [item for item in items if item["secCode"] == code
                    and _is_full_annual(str(item.get("announcementTitle", "")), year)]
        originals = sorted((item for item in matching if not any(w in str(item.get("announcementTitle", ""))
                                                                 for w in REVISION_WORDS)), key=_published)
        revisions = sorted((item for item in matching if any(w in str(item.get("announcementTitle", ""))
                                                                for w in REVISION_WORDS)), key=_published)
        original = originals[0] if originals else None
        revision = revisions[0] if revisions else None
        for role, item in (("earliest_original", original), ("explicit_revision", revision)):
            if item is not None:
                selected.append({"code": code, "report_year": year, "role": role,
                                 "announcement": item})
        findings.append({"code": code, "report_year": year,
                         "original_candidates": len(originals), "revision_candidates": len(revisions),
                         "original_found": original is not None, "revision_found": revision is not None,
                         "missing_reason": None if original is not None else "no_matching_full_original_in_read_pages"})
    # Keep correction notices visible even if their title does not identify a full revised report.
    known = [item for item in items if item.get("secCode") == "600518"
             and any(w in str(item.get("announcementTitle", "")) for w in REVISION_WORDS)]
    linked = {str(x["announcement"].get("announcementId")) for x in selected}
    for year in (2016, 2017):
        candidates = [item for item in known
                      if _year_in_title(str(item.get("announcementTitle", "")), year)
                      and str(item.get("announcementId")) not in linked]
        if candidates:
            item = min(candidates, key=_published)
            title = str(item.get("announcementTitle", ""))
            selected.append({"code": "600518", "report_year": year,
                             "linked_report_years": [y for y in (2016, 2017) if _year_in_title(title, y)],
                             "role": "dated_correction_notice", "announcement": item})
            linked.add(str(item.get("announcementId")))
    if not any(x["code"] == "600518" and "correction" in x["role"] for x in selected):
        unlinked = [item for item in known if "会计差错" in str(item.get("announcementTitle", ""))
                    and str(item.get("announcementId")) not in linked]
        if unlinked:
            item = min(unlinked, key=_published)
            selected.append({"code": "600518", "report_year": None, "linked_report_years": [],
                             "role": "accounting_correction_notice_year_unverified", "announcement": item})
    return selected[:8], findings, known


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


def run(plan_path: Path, storage_path: Path, out: Path):
    plan_path, storage_path, out = Path(plan_path).resolve(), Path(storage_path).resolve(), Path(out).resolve()
    if _sha(plan_path) != PLAN_SHA256 or _sha(storage_path) != STORAGE_PLAN_SHA256:
        raise ValueError("frozen probe or storage plan changed")
    plan, storage = _json(plan_path), _json(storage_path)
    if (plan["max_total_data_operations"] != 18 or plan["request_delay_seconds"] != 1
            or plan["timeout_seconds"] != 40 or plan["retries"] != 0
            or len(plan["query_cases"]) != 6):
        raise ValueError("unexpected probe scope or budget")
    _check_storage(storage, out, plan["out"])
    out.mkdir(parents=False, exist_ok=False)
    budget = Budget(plan, out)
    index = _response_json(budget, "stock_index", "GET", plan["stock_index"])
    mapping = {}
    if isinstance(index, dict) and isinstance(index.get("stockList"), list):
        mapping = {str(item["code"]): str(item["orgId"]) for item in index["stockList"]
                   if isinstance(item, dict) and "code" in item and "orgId" in item}
    all_items, query_log, page2_slots = [], [], 3
    if not budget.stopped_reason:
        for case in plan["query_cases"]:
            if budget.stopped_reason:
                break
            org_id = mapping.get(case["code"])
            items, detail, page2_slots = _query_pages(
                budget, plan["announcement_endpoint"], case, org_id, page2_slots)
            query_log.append({"case": case, **detail})
            all_items.extend(items)
    unique = {}
    for item in all_items:
        key = (str(item.get("secCode")), str(item.get("announcementId")))
        unique[key] = item
    selected, findings, known_corrections = _select(list(unique.values()), plan)
    pdfs = []
    for target in selected:
        item = target["announcement"]
        locator = _pdf_url(item)
        record = {"code": target["code"], "report_year": target["report_year"],
                  "linked_report_years": target.get("linked_report_years", []),
                  "role": target["role"], "announcement_id": item.get("announcementId"),
                  "org_id": item.get("orgId"), "sec_code": item.get("secCode"),
                  "announcement_title": item.get("announcementTitle"),
                  "announcement_time_ms": item.get("announcementTime"),
                  "adjunct_url_as_returned": item.get("adjunctUrl"), "pdf_url": locator,
                  "attempt_id": None, "pdf_valid": False, "missing_reason": None}
        if budget.stopped_reason or len(budget.attempts) >= budget.limit:
            record["missing_reason"] = "budget_or_stop_before_pdf"
        elif not locator or not record["announcement_id"]:
            record["missing_reason"] = "actual_pdf_locator_or_announcement_id_missing"
        else:
            body = budget.request("pdf", "GET", locator)
            record["attempt_id"] = budget.attempts[-1]["id"] if budget.attempts else None
            record["pdf_valid"] = body is not None and body.startswith(b"%PDF-")
            if not record["pdf_valid"]:
                record["missing_reason"] = "download_failed_or_non_pdf_body"
        pdfs.append(record)
    manifest = {"schema": "original-filings-probe/1", "plan_path": str(plan_path),
                "plan_sha256": _sha(plan_path), "storage_plan_path": str(storage_path),
                "storage_plan_sha256": _sha(storage_path), "script_sha256": _sha(Path(__file__)),
                "out": str(out), "started_and_finished_utc": _timestamp(),
                "max_total_data_operations": budget.limit, "operations_used": len(budget.attempts),
                "stopped_reason": budget.stopped_reason,
                "attempts": budget.attempts, "queries": query_log,
                "findings": findings, "known_600518_correction_announcements": known_corrections,
                "selected_pdf_objects": pdfs,
                "all_exact_code_announcements": list(unique.values()),
                "qualification": "announcement inventory and raw PDF only; no financial numbers extracted",
                "coverage_limit": "unread pages, missing orgId, missing adjunctUrl and corrections remain explicit"}
    _write_json(out / "manifest.json", manifest)
    return {"out": str(out), "manifest_sha256": _sha(out / "manifest.json"),
            "operations_used": len(budget.attempts), "stopped_reason": budget.stopped_reason}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--storage-plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.storage_plan, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
