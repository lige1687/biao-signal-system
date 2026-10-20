"""Run only the ten anonymously authorized BaoStock requests in source-plan.json."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sys
import time
import traceback


ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
SOURCE_PLAN = HERE / "source-plan.json"
STORAGE_PLAN = HERE / "storage-plan.json"
PROTECTED_INPUTS = HERE / "protected-inputs.json"
EXECUTION_CONTRACT = HERE / "execution-contract.json"
RECEIPT = HERE / "execution-receipt.json"
ALLOWED_METHODS = {"query_history_k_data_plus", "query_adjust_factor", "query_dividend_data"}
TIMEOUT_SECONDS = 40
MAX_OPERATIONS = 10
PRIOR_PHASE_COUNTS = {"input_integrity": 6, "value_probe": 4, "identity": 6}


class StopRun(RuntimeError):
    """A frozen precondition failed; do not try a fallback."""


def stamp() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def digest(path: Path) -> dict:
    h, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return {"path": str(path), "sha256": h.hexdigest(), "bytes": size}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StopRun(message)


def verify_contract(contract: dict) -> list[dict]:
    require(contract.get("execution_authorized") is True, "execution contract is not authorized")
    bindings = contract.get("bindings")
    require(isinstance(bindings, list) and bindings, "execution contract has no bindings")
    expected = {str(Path(item["path"])): item["sha256"] for item in bindings}
    observed = []
    for path_text, expected_sha in expected.items():
        actual = digest(Path(path_text))
        require(actual["sha256"] == expected_sha, f"contract SHA mismatch: {path_text}")
        observed.append(actual)
    required = [SOURCE_PLAN, STORAGE_PLAN, PROTECTED_INPUTS, Path(__file__).resolve()]
    for path in required:
        require(str(path) in expected, f"contract does not bind {path}")
    return observed


def verify_protected(inputs: list[dict]) -> list[dict]:
    result = []
    for item in inputs:
        actual = digest(Path(item["path"]))
        require(actual["sha256"] == item["sha256"], f"protected input SHA mismatch: {item['path']}")
        result.append(actual)
    return result


def verify_source_plan(plan: dict, protected: list[dict]) -> None:
    require(plan.get("schema") == "source-repair-proposal/1", "unexpected source-plan schema")
    require(plan.get("status") == "authorized_bounded_source_extension", "source plan not authorized")
    require(plan.get("max_new_data_operations") == MAX_OPERATIONS, "request cap must be ten")
    require(plan.get("incremental_max") == MAX_OPERATIONS, "incremental cap must be ten")
    require(plan.get("retries") == 0, "retries must remain zero")
    require(plan.get("request_timeout_seconds") == TIMEOUT_SECONDS, "timeout must remain 40 seconds")
    require(plan.get("stop_after_consecutive_failures") == 2, "failure stop rule mismatch")
    require(plan.get("stop_on_rate_limit") is True, "rate-limit stop rule missing")
    requests = plan.get("requests")
    require(isinstance(requests, list) and len(requests) == MAX_OPERATIONS,
            "expected exactly ten frozen requests")
    for request in requests:
        require(set(request) == {"method", "kwargs"}, "request must contain only method and kwargs")
        require(request["method"] in ALLOWED_METHODS, "request method is not allowlisted")
        require(isinstance(request["kwargs"], dict), "request kwargs must be an object")
    protected_map = {str(item["path"]): item["sha256"] for item in protected}
    identity = plan.get("source_identity_evidence") or {}
    require(protected_map.get(identity.get("path")) == identity.get("sha256"),
            "source identity evidence is not protected")


def storage_check(plan: dict, run_dir: Path, out_dir: Path, extra_bytes: int = 0) -> None:
    from lei_signal.research.output_storage import _still_mounted

    require(_still_mounted(plan), "external disk identity/device changed; no internal fallback")
    device = plan["external_device"]
    require(run_dir.is_dir() and os.stat(run_dir).st_dev == device, "run directory is off bound disk")
    require(out_dir.is_dir() and os.stat(out_dir).st_dev == device, "result directory is off bound disk")
    needed = plan["external_reserve_bytes"] + max(plan["estimated_bytes"], extra_bytes)
    require(shutil.disk_usage(plan["external_mount"]).free >= needed,
            "external reserve plus output allowance is unavailable")
    internal_needed = plan["internal_reserve_bytes"] + plan["internal_metadata_bytes"]
    require(shutil.disk_usage(ROOT).free >= internal_needed, "internal reserve is below bound")


def journal(path: Path, storage: dict, run_dir: Path, out_dir: Path, event: dict) -> None:
    raw = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    storage_check(storage, run_dir, out_dir, len(raw.encode("utf-8")))
    with path.open("a", encoding="utf-8") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def save_json(path: Path, value: dict, storage: dict, run_dir: Path, out_dir: Path) -> dict:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    storage_check(storage, run_dir, out_dir, len(raw))
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


class CheckedLog:
    """Check the bound disk before every captured SDK log write."""

    def __init__(self, stream, storage: dict, run_dir: Path, out_dir: Path):
        self.stream, self.storage, self.run_dir, self.out_dir = stream, storage, run_dir, out_dir

    @property
    def encoding(self):
        return self.stream.encoding

    def write(self, text):
        storage_check(self.storage, self.run_dir, self.out_dir,
                      len(str(text).encode(self.encoding or "utf-8")))
        return self.stream.write(text)

    def flush(self):
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def isatty(self):
        return False


def rate_limited(message: str) -> bool:
    text = message.casefold()
    return any(token in text for token in ("429", "too many", "频繁", "请求频率", "请求过多"))


def timeout_handler(_signum, _frame):
    raise TimeoutError(f"request exceeded {TIMEOUT_SECONDS} seconds")


def timed_call(function, **kwargs):
    signal.signal(signal.SIGALRM, timeout_handler)
    socket.setdefaulttimeout(TIMEOUT_SECONDS)
    signal.alarm(TIMEOUT_SECONDS)
    try:
        return function(**kwargs)
    finally:
        signal.alarm(0)


def create_output_dirs(storage: dict):
    from lei_signal.research.output_storage import _still_mounted, recheck_saved_plan

    checked = recheck_saved_plan(ROOT, storage, storage["task_id"],
                                 storage["estimated_bytes"], storage["internal_metadata_bytes"])
    require(_still_mounted(checked), "external disk mismatch before directory creation")
    run_dir, out_dir = Path(checked["run_directory"]), Path(checked["output"])
    task_parent = run_dir.parent
    require(not run_dir.exists() and not out_dir.exists(), "run/result directory exists; refusing overwrite")
    require(task_parent.parent.is_dir() and os.stat(task_parent.parent).st_dev == checked["external_device"],
            "external task base missing or on wrong device")
    require(shutil.disk_usage(checked["external_mount"]).free >=
            checked["external_reserve_bytes"] + checked["estimated_bytes"], "external reserve check failed")
    require(shutil.disk_usage(ROOT).free >=
            checked["internal_reserve_bytes"] + checked["internal_metadata_bytes"], "internal reserve check failed")
    task_parent.mkdir(exist_ok=True)
    require(os.stat(task_parent).st_dev == checked["external_device"], "task parent is on wrong device")
    run_dir.mkdir(exist_ok=False)
    out_dir.mkdir(exist_ok=False)
    storage_check(checked, run_dir, out_dir)
    route = (json.dumps(checked, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    storage_check(checked, run_dir, out_dir, len(route))
    with (run_dir / "storage-plan.json").open("xb") as stream:
        stream.write(route)
        stream.flush()
        os.fsync(stream.fileno())
    return checked, run_dir, out_dir


def run_requests(source_plan: dict, storage: dict, run_dir: Path, out_dir: Path,
                 stdout_path: Path, stderr_path: Path) -> tuple[str, int, list, list]:
    requests_log, outputs = [], []
    used = consecutive_bad = 0
    rate_stop = login_failed = False
    journal_path = run_dir / "attempt-journal.jsonl"
    storage_check(storage, run_dir, out_dir)
    with stdout_path.open("x", encoding="utf-8") as stdout_file, stderr_path.open("x", encoding="utf-8") as stderr_file:
        stdout = CheckedLog(stdout_file, storage, run_dir, out_dir)
        stderr = CheckedLog(stderr_file, storage, run_dir, out_dir)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            storage_check(storage, run_dir, out_dir)
            import baostock as bs

            journal(journal_path, storage, run_dir, out_dir,
                    {"event": "login_start", "at": stamp(), "anonymous": True})
            started = time.monotonic()
            try:
                login = timed_call(bs.login)
                code, message = login.error_code, login.error_msg
                logged_in = str(code).strip() == "0"
                login_failed = not logged_in
                if login_failed:
                    used = 1
                login_event = {"event": "login_result", "at": stamp(),
                               "status": "ok" if logged_in else "failed", "error_code": code,
                               "error_msg": message, "seconds": round(time.monotonic() - started, 3)}
            except Exception as exc:
                logged_in = False
                login_failed = True
                used = 1
                login_event = {"event": "login_result", "at": stamp(), "status": "failed",
                               "exception": f"{type(exc).__name__}: {exc}",
                               "seconds": round(time.monotonic() - started, 3)}
            requests_log.append(login_event)
            journal(journal_path, storage, run_dir, out_dir, login_event)

            if logged_in:
                for number, request in enumerate(source_plan["requests"], 1):
                    storage_check(storage, run_dir, out_dir)
                    started = time.monotonic()
                    journal(journal_path, storage, run_dir, out_dir,
                            {"event": "request_start", "request_number": number, "at": stamp(),
                             "method": request["method"], "kwargs": request["kwargs"]})
                    used += 1
                    fields, rows, code, message, exception = None, [], None, None, None
                    try:
                        def collect_response():
                            nonlocal fields, code, message
                            response = getattr(bs, request["method"])(**request["kwargs"])
                            fields, code, message = response.fields, response.error_code, response.error_msg
                            if str(code).strip() == "0":
                                while response.next():
                                    rows.append(response.get_row_data())
                            code, message = response.error_code, response.error_msg

                        timed_call(collect_response)
                        status = "ok" if str(code).strip() == "0" and rows else "empty_or_error"
                    except Exception as exc:
                        status = "failed"
                        exception = f"{type(exc).__name__}: {exc}"
                    payload = {"method": request["method"], "kwargs": request["kwargs"],
                               "status": status, "fields": fields, "rows": rows,
                               "error_code": code, "error_msg": message, "exception": exception}
                    target = out_dir / f"request-{number:02d}.json"
                    saved = save_json(target, payload, storage, run_dir, out_dir)
                    outputs.append(saved)
                    result_event = {"event": "request_result", "request_number": number, "at": stamp(),
                                    "status": status, "rows": len(rows), "fields": fields,
                                    "error_code": code, "error_msg": message, "exception": exception,
                                    **saved, "seconds": round(time.monotonic() - started, 3)}
                    requests_log.append(result_event)
                    journal(journal_path, storage, run_dir, out_dir, result_event)
                    consecutive_bad = 0 if status == "ok" else consecutive_bad + 1
                    if rate_limited(" ".join(str(x or "") for x in (code, message, exception))):
                        rate_stop = True
                        break
                    if consecutive_bad >= source_plan["stop_after_consecutive_failures"]:
                        break
                    time.sleep(1)

            if logged_in:
                journal(journal_path, storage, run_dir, out_dir, {"event": "logout_start", "at": stamp()})
                try:
                    logout = timed_call(bs.logout)
                    logout_event = {"event": "logout_result", "at": stamp(), "error_code": logout.error_code}
                except Exception as exc:
                    logout_event = {"event": "logout_result", "at": stamp(),
                                    "exception": f"{type(exc).__name__}: {exc}"}
                requests_log.append(logout_event)
                journal(journal_path, storage, run_dir, out_dir, logout_event)

            nonempty_ok = [x for x in requests_log if x.get("event") == "request_result"]
            complete = used == MAX_OPERATIONS and len(nonempty_ok) == MAX_OPERATIONS and all(
                x["status"] == "ok" for x in nonempty_ok)
            status = "complete10" if complete else "source_unavailable"
            summary = {"schema": "old-code-source-repair-summary/1", "status": status, "at": stamp(),
                       "source_operations_used_this_run": used, "source_operations_max_this_run": MAX_OPERATIONS,
                       "prior_named_phase_counts": PRIOR_PHASE_COUNTS,
                       "named_phase_subtotal_with_this_run": sum(PRIOR_PHASE_COUNTS.values()) + used,
                       "not_a_global_historical_total": True, "login_failed": login_failed,
                       "rate_limit_stopped_run": rate_stop,
                       "consecutive_empty_or_error_stop_count": consecutive_bad,
                       "requests": requests_log, "raw_responses": outputs, "output": str(out_dir),
                       "financial_or_factor_readiness": False}
            outputs.append(save_json(out_dir / "summary.json", summary, storage, run_dir, out_dir))
            outputs.append(digest(journal_path))
            stdout.flush()
            stderr.flush()
    return status, used, requests_log, outputs


def main() -> int:
    receipt = {"schema": "old-code-source-repair-receipt/1", "started_at": stamp(),
               "source_operations_max_this_run": MAX_OPERATIONS, "source_operations_used_this_run": 0,
               "prior_named_phase_counts": PRIOR_PHASE_COUNTS,
               "named_phase_subtotal_is_not_global_historical_total": True,
               "financial_or_factor_readiness": False}
    try:
        require(not RECEIPT.exists(), "execution receipt already exists; refusing overwrite")
        contract = json.loads(EXECUTION_CONTRACT.read_text(encoding="utf-8"))
        receipt["contract_sha256"] = digest(EXECUTION_CONTRACT)["sha256"]
        receipt["bindings_before"] = verify_contract(contract)
        plan = json.loads(SOURCE_PLAN.read_text(encoding="utf-8"))
        storage_plan = json.loads(STORAGE_PLAN.read_text(encoding="utf-8"))
        protected = json.loads(PROTECTED_INPUTS.read_text(encoding="utf-8"))
        receipt["protected_inputs_before"] = verify_protected(protected)
        bound = {str(Path(item["path"])): item["sha256"] for item in contract["bindings"]}
        require(all(bound.get(str(Path(item["path"]))) == item["sha256"] for item in protected),
                "execution contract does not bind every protected input")
        verify_source_plan(plan, protected)
        checked, run_dir, out_dir = create_output_dirs(storage_plan)
        receipt["storage_plan_sha256"] = digest(STORAGE_PLAN)["sha256"]
        receipt["run_directory"] = str(run_dir)
        receipt["output_directory"] = str(out_dir)
        stdout_path, stderr_path = run_dir / "probe.stdout.log", run_dir / "probe.stderr.log"
        status, used, attempts, outputs = run_requests(plan, checked, run_dir, out_dir,
                                                       stdout_path, stderr_path)
        receipt.update(status=status, exit_code=0 if status == "complete10" else 2,
                       source_operations_used_this_run=used, requests=attempts, outputs=outputs,
                       stdout=digest(stdout_path), stderr=digest(stderr_path))
        receipt["bindings_after"] = verify_contract(contract)
        receipt["protected_inputs_after"] = verify_protected(protected)
    except Exception as exc:
        receipt.update(status="failed_closed", exit_code=3,
                       error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        # A failure after data requests must not reset their count to zero.
        if receipt.get("run_directory"):
            journal_path = Path(receipt["run_directory"]) / "attempt-journal.jsonl"
            if journal_path.is_file():
                events = [json.loads(line) for line in journal_path.read_text().splitlines()]
                starts = sum(row.get("event") == "request_start" for row in events)
                login_failed = any(row.get("event") == "login_result" and row.get("status") == "failed"
                                   for row in events)
                receipt["source_operations_used_this_run"] = starts or int(login_failed)
                receipt["requests"] = events
    receipt["ended_at"] = stamp()
    with RECEIPT.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return receipt["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
