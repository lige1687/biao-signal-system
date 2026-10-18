"""Resume the frozen 610-call history acquisition with six bounded processes."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import plistlib
import queue
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).parent
BULK = json.loads((HERE / 'bulk-v1.json').read_text())
PLAN = json.loads((HERE / 'storage-plan.json').read_text())
RUN = Path(PLAN['run_directory'])
OUT = Path(PLAN['output'])
OLD = OUT / 'acquisition'
DEST = OUT / 'acquisition-parallel'
LOCK_PATH = HERE / 'bao-start.lock'
FIELDS = BULK['fields']
START, END = BULK['price_window']
TOTAL = int(BULK['query_budget']['total_data_max'])
MAX_WORKERS = 6
TIMEOUT = int(BULK['query_budget']['timeout_seconds'])
SPACING = float(BULK['query_budget']['spacing_seconds'])
STOP_ERRORS = 2


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def guard() -> None:
    mount = Path(PLAN['external_mount'])
    if not os.path.ismount(mount) or mount.stat().st_dev != PLAN['external_device']:
        raise RuntimeError('registered external disk lost or device changed')
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    if info.get('VolumeUUID') != PLAN['external_uuid'] or info.get('Writable') is not True:
        raise RuntimeError('external UUID or writable state changed')
    if shutil.disk_usage(mount).free < PLAN['external_reserve_bytes']:
        raise RuntimeError('external reserve no longer available')


def exclusive_json(path: Path, obj: object) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode()
    with path.open('xb') as f:
        f.write(raw)
    return raw


def build_queue() -> list[dict]:
    q = []
    for code in BULK['selected_codes']:
        q.append({'code': code, 'kind': 'daily', 'kwargs': {'code': code, 'fields': FIELDS, 'start_date': START, 'end_date': END, 'frequency': 'd', 'adjustflag': BULK['adjustflag']}})
    for code in BULK['spot_check_codes']:
        q.append({'code': code, 'kind': 'raw_daily', 'kwargs': {'code': code, 'fields': FIELDS, 'start_date': START, 'end_date': END, 'frequency': 'd', 'adjustflag': '3'}})
        q.append({'code': code, 'kind': 'adjust_factor', 'kwargs': {'code': code, 'start_date': START, 'end_date': END, 'frequency': 'd', 'adjustflag': BULK['adjustflag']}})
    if len(q) != TOTAL or len({(x['code'], x['kind']) for x in q}) != TOTAL:
        raise RuntimeError(f'frozen queue mismatch: {len(q)} unique={len({(x["code"], x["kind"]) for x in q})}')
    return q


def old_successes() -> tuple[dict[tuple[str, str], dict], int]:
    records = [json.loads(x) for x in (OLD / 'attempts.jsonl').read_text().splitlines() if x.strip()]
    successes = {}
    old_calls = 0
    for row in records:
        if row.get('kind') != 'data_request':
            continue
        old_calls += 1
        if row.get('status') == 'ok':
            key = (row['code'], row['request_type'])
            raw = Path(row['raw_path'])
            if not raw.is_file() or sha_path(raw) != row['raw_sha256']:
                raise RuntimeError(f'old successful source hash mismatch: {key}')
            body = json.loads(raw.read_text())
            if len(body.get('data', [])) != row.get('rows') or body.get('fields') != row.get('fields'):
                raise RuntimeError(f'old successful source schema mismatch: {key}')
            successes[key] = {'code': row['code'], 'kind': row['request_type'], 'path': str(raw), 'rows': row['rows'], 'fields': row['fields'], 'bytes': row['raw_bytes'], 'sha256': row['raw_sha256'], 'status': 'ok', 'source': row['source'], 'request': row['kwargs'], 'retrieved_at': row['at'], 'origin_attempts': 'acquisition/attempts.jsonl'}
    if old_calls != 36 or len(successes) != 36:
        raise RuntimeError(f'expected the reviewed 36 old calls/successes, got {old_calls}/{len(successes)}')
    return successes, old_calls


def validate_frozen() -> tuple[list[dict], dict[tuple[str, str], dict], int]:
    receipts = json.loads((HERE / 'acquisition-sequential-stop.json').read_text())
    checks = [
        (Path(BULK['study_design']['path']), BULK['study_design']['sha256']),
        (Path(BULK['cohort']['path']), BULK['cohort']['sha256']),
        (Path(BULK['calendar']['path']), BULK['calendar']['sha256']),
        (HERE / 'storage-plan.json', BULK['storage_plan']['sha256']),
    ]
    for path, expected in checks:
        if sha_path(path) != expected:
            raise RuntimeError(f'frozen input hash mismatch: {path}')
    if not receipts.get('all_success_hashes_verified') or receipts.get('requests') != 36:
        raise RuntimeError('sequential stop receipt does not attest 36 successful originals')
    if RUN.name != PLAN['run_id'] or not (OUT / 'probe' / 'summary.json').is_file():
        raise RuntimeError('bound run/probe missing')
    if DEST.exists():
        raise RuntimeError('refuse existing acquisition-parallel directory')
    guard()
    if RUN.parent.stat().st_dev != PLAN['external_device']:
        raise RuntimeError('bound run is on the wrong device')
    queue_items = build_queue()
    prior, old_calls = old_successes()
    pending_keys = {(x['code'], x['kind']) for x in queue_items} - set(prior)
    if old_calls + len(pending_keys) != TOTAL:
        raise RuntimeError(f'request budget mismatch: {old_calls}+{len(pending_keys)} != {TOTAL}')
    return queue_items, prior, old_calls


def call_source(task: dict, starts: list[float], start_lock: threading.Lock, abort_event: threading.Event) -> dict:
    import baostock as bs
    code, kind, kwargs = task['code'], task['kind'], task['kwargs']
    row = {'kind': 'data_request', 'code': code, 'request_type': kind, 'source': BULK['source'], 'kwargs': kwargs, 'pid': os.getpid(), 'login_at': dt.datetime.now().astimezone().isoformat()}
    login_start = time.monotonic()
    try:
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(f'BaoStock request exceeded {TIMEOUT}s')))
        socket.setdefaulttimeout(TIMEOUT)
        signal.alarm(TIMEOUT)
        login = bs.login()
        signal.alarm(0)
        row.update(login_error_code=login.error_code, login_error_msg=login.error_msg, login_elapsed=time.monotonic() - login_start)
        if login.error_code != '0':
            return {**row, 'status': 'login_failed', 'error': f'{login.error_code}: {login.error_msg}', 'finished_at': dt.datetime.now().astimezone().isoformat()}
        with start_lock:
            while starts and time.monotonic() - starts[-1] < SPACING:
                time.sleep(min(0.1, SPACING - (time.monotonic() - starts[-1])))
            if abort_event.is_set():
                return {**row, 'status': 'not_started_stopped', 'finished_at': dt.datetime.now().astimezone().isoformat()}
            starts.append(time.monotonic())
            row['started_at'] = dt.datetime.now().astimezone().isoformat()
        signal.alarm(TIMEOUT)
        if kind in ('daily', 'raw_daily'):
            result = bs.query_history_k_data_plus(code, kwargs['fields'], start_date=START, end_date=END, frequency=kwargs['frequency'], adjustflag=kwargs['adjustflag'])
        else:
            result = bs.query_adjust_factor(code, start_date=START, end_date=END)
        rows = []
        while result.error_code == '0' and result.next():
            rows.append(result.get_row_data())
        signal.alarm(0)
        body = {'fields': result.fields, 'data': rows, 'error_code': result.error_code, 'error_msg': result.error_msg}
        raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
        empty = len(rows) == 0
        status = 'ok' if result.error_code == '0' and not empty else ('empty_response' if result.error_code == '0' else 'source_error')
        row.update(status=status, fields=result.fields, rows=len(rows), error_code=result.error_code, error_msg=result.error_msg, raw=raw, raw_bytes=len(raw), raw_sha256=sha_bytes(raw), empty_response=empty)
        if '429' in str(result.error_msg).lower() or 'too many requests' in str(result.error_msg).lower():
            row['status'] = 'rate_limited_stop'
    except BaseException as exc:
        signal.alarm(0)
        row.update(status='request_failed', error=f'{type(exc).__name__}: {exc}')
    finally:
        row['finished_at'] = dt.datetime.now().astimezone().isoformat()
        try:
            logout = bs.logout()
            row.update(logout_error_code=logout.error_code, logout_error_msg=logout.error_msg)
        except Exception as exc:
            row['logout_error'] = f'{type(exc).__name__}: {exc}'
    return row


def main() -> int:
    queue_items, old, old_calls = validate_frozen()
    DEST.mkdir(exist_ok=False)
    guard()
    exclusive_json(DEST / 'storage-binding.json', {'run_id': PLAN['run_id'], 'run_directory': str(RUN), 'output': str(DEST), 'external_mount': PLAN['external_mount'], 'external_uuid': PLAN['external_uuid'], 'external_device': PLAN['external_device'], 'verified_at': dt.datetime.now().astimezone().isoformat()})
    pending = [t for t in queue_items if (t['code'], t['kind']) not in old]
    # Main process alone writes all files and ledgers.
    attempts_path = DEST / 'attempts.jsonl'
    attempts_file = attempts_path.open('x', encoding='utf-8')
    attempts_file.write(json.dumps({'kind': 'resume', 'at': dt.datetime.now().astimezone().isoformat(), 'old_successful_requests': old_calls, 'old_successful_hashes_reverified': len(old), 'new_requests_pending': len(pending), 'predecessor_stop': '36 successful calls; Ctrl-C before request 37 network call'}, ensure_ascii=False) + '\n')
    attempts_file.flush()
    exclusive_json(DEST / 'request-queue.json', {'source': BULK['source'], 'total_unique_requests': TOTAL, 'already_successful_not_reissued': old_calls, 'remaining': len(pending), 'max_workers': MAX_WORKERS, 'global_min_start_spacing_seconds': SPACING, 'requests': pending})

    manager = multiprocessing.Manager()
    abort_event = manager.Event()
    start_notifier = manager.Queue()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS)
    # Each subprocess records a completion marker in a pipe by its future; all target outputs stay RAM-only until parent receives them.
    def dispatch(task: dict):
        return executor.submit(_worker_entry, task, DEST, PLAN, SPACING, TIMEOUT, abort_event, start_notifier)

    futures: dict[concurrent.futures.Future, dict] = {}
    iterator = iter(pending)
    in_flight = 0
    completed_new = 0
    errors_in_completion_order = 0
    stop_reason = None
    manifest_map = dict(old)
    all_failed: list[dict] = []
    started_at = dt.datetime.now().astimezone().isoformat()
    try:
        while in_flight < MAX_WORKERS:
            task = next(iterator, None)
            if task is None:
                break
            futures[dispatch(task)] = task
            in_flight += 1
        while futures:
            guard()
            while not start_notifier.empty():
                started = start_notifier.get()
                attempts_file.write(json.dumps(started, ensure_ascii=False) + '\n')
                attempts_file.flush()
            finished, _ = concurrent.futures.wait(futures, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED)
            if not finished:
                continue
            for future in finished:
                task = futures.pop(future)
                in_flight -= 1
                try:
                    row = future.result()
                except BaseException as exc:
                    row = {'kind': 'data_request', 'code': task['code'], 'request_type': task['kind'], 'kwargs': task['kwargs'], 'source': BULK['source'], 'status': 'worker_failed', 'error': f'{type(exc).__name__}: {exc}', 'finished_at': dt.datetime.now().astimezone().isoformat()}
                raw = row.pop('raw', None)
                if raw is not None:
                    guard()
                    filename = f"{task['code']}-{task['kind']}.json"
                    path = DEST / filename
                    with path.open('xb') as f:
                        f.write(raw)
                    row.update(raw_path=str(path), raw_file=filename)
                    manifest_map[(task['code'], task['kind'])] = {'code': task['code'], 'kind': task['kind'], 'path': str(path), 'rows': row['rows'], 'fields': row['fields'], 'bytes': len(raw), 'sha256': row['raw_sha256'], 'status': row['status'], 'source': BULK['source'], 'request': task['kwargs'], 'retrieved_at': row.get('started_at'), 'pid': row.get('pid')}
                attempts_file.write(json.dumps(row, ensure_ascii=False) + '\n')
                attempts_file.flush()
                completed_new += 1
                status = row.get('status')
                if status == 'ok':
                    errors_in_completion_order = 0
                else:
                    errors_in_completion_order += 1
                    all_failed.append({'code': task['code'], 'kind': task['kind'], 'status': status, 'error': row.get('error', row.get('error_msg'))})
                if status == 'rate_limited_stop':
                    abort_event.set()
                    stop_reason = '429/rate limit; stop new dispatch'
                elif errors_in_completion_order >= STOP_ERRORS:
                    abort_event.set()
                    stop_reason = 'two consecutive completed source errors; stop new dispatch'
                if completed_new % 50 == 0:
                    print(json.dumps({'completed_new': completed_new, 'reused_old': old_calls, 'total_completed': old_calls + completed_new, 'ok': len(manifest_map), 'failed': len(all_failed), 'in_flight': in_flight}, ensure_ascii=False), flush=True)
                if not abort_event.is_set():
                    nxt = next(iterator, None)
                    if nxt is not None:
                        futures[dispatch(nxt)] = nxt
                        in_flight += 1
        executor.shutdown(wait=True, cancel_futures=True)
        manager.shutdown()
    except BaseException as exc:
        abort_event.set()
        stop_reason = f'guard or parent failure: {type(exc).__name__}: {exc}'
        for future in futures:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
        raise
    finally:
        attempts_file.close()

    missing = [t for t in queue_items if (t['code'], t['kind']) not in manifest_map]
    status = 'complete' if not missing and not all_failed and len(manifest_map) == TOTAL else 'partial'
    final = {'schema': 'lei-history-acquisition-manifest/1.1', 'status': status, 'source': BULK['source'], 'bulk_version': BULK['version'], 'bulk_sha256': sha_path(HERE / 'bulk-v1.json'), 'design_sha256': BULK['study_design']['sha256'], 'cohort_sha256': BULK['cohort']['sha256'], 'calendar_sha256': BULK['calendar']['sha256'], 'storage_run_id': PLAN['run_id'], 'total_unique_data_requests': TOTAL, 'old_successful_not_reissued': old_calls, 'new_requests_started': completed_new, 'successful_sources': len(manifest_map), 'failed_requests': all_failed, 'missing_requests': missing, 'stop_reason': stop_reason, 'workers': MAX_WORKERS, 'global_min_start_spacing_seconds': SPACING, 'retries': 0, 'files': [manifest_map[k] for k in sorted(manifest_map)], 'started_at': started_at, 'finished_at': dt.datetime.now().astimezone().isoformat(), 'not_computed': ['factor performance', 'returns', 'signals']}
    exclusive_json(DEST / 'manifest.json', final)
    print(json.dumps({'status': status, 'old_reused': old_calls, 'new_completed': completed_new, 'sources': len(manifest_map), 'failures': len(all_failed), 'missing': len(missing), 'stop_reason': stop_reason}, ensure_ascii=False), flush=True)
    return 0 if status == 'complete' else 2


def _worker_entry(task: dict, dest: Path, plan: dict, spacing: float, timeout: int, abort_event, start_notifier) -> dict:
    # Process-local module/global setup keeps BaoStock's connection state isolated.
    import baostock as bs
    import datetime as _dt
    import hashlib as _hashlib
    import json as _json
    import os as _os
    import signal as _signal
    import socket as _socket
    import time as _time
    code, kind, kwargs = task['code'], task['kind'], task['kwargs']
    row = {'kind': 'data_request', 'code': code, 'request_type': kind, 'source': BULK['source'], 'kwargs': kwargs, 'pid': _os.getpid(), 'login_at': _dt.datetime.now().astimezone().isoformat()}
    try:
        _socket.setdefaulttimeout(timeout)
        _signal.signal(_signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(f'BaoStock request exceeded {timeout}s')))
        _signal.alarm(timeout)
        login = bs.login()
        _signal.alarm(0)
        row.update(login_error_code=login.error_code, login_error_msg=login.error_msg)
        if login.error_code != '0':
            row.update(status='login_failed', error=f'{login.error_code}: {login.error_msg}', finished_at=_dt.datetime.now().astimezone().isoformat())
            return row
        lockfile = open(str(Path(dest).parent / '.bao-start.lock'), 'a+')
        _signal.alarm(timeout)
        with lockfile:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
            lockfile.seek(0)
            try:
                last = float(lockfile.read().strip() or '0')
            except ValueError:
                last = 0.0
            wait = spacing - (_time.monotonic() - last)
            if wait > 0:
                _time.sleep(wait)
            if abort_event.is_set():
                fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)
                _signal.alarm(0)
                row.update(status='not_started_stopped', finished_at=_dt.datetime.now().astimezone().isoformat())
                return row
            start = _time.monotonic()
            row['started_at'] = _dt.datetime.now().astimezone().isoformat()
            lockfile.seek(0)
            lockfile.truncate()
            lockfile.write(str(start))
            lockfile.flush()
            start_notifier.put({**row, 'status': 'started'})
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)
        _signal.alarm(timeout)
        if kind in ('daily', 'raw_daily'):
            result = bs.query_history_k_data_plus(code, kwargs['fields'], start_date=START, end_date=END, frequency=kwargs['frequency'], adjustflag=kwargs['adjustflag'])
        else:
            result = bs.query_adjust_factor(code, start_date=START, end_date=END)
        data = []
        while result.error_code == '0' and result.next():
            data.append(result.get_row_data())
        _signal.alarm(0)
        payload = {'fields': result.fields, 'data': data, 'error_code': result.error_code, 'error_msg': result.error_msg}
        raw = _json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
        empty = not data
        status = 'ok' if result.error_code == '0' and not empty else ('empty_response' if empty and result.error_code == '0' else 'source_error')
        row.update(status=status, fields=result.fields, rows=len(data), error_code=result.error_code, error_msg=result.error_msg, raw=raw, raw_bytes=len(raw), raw_sha256=_hashlib.sha256(raw).hexdigest(), empty_response=empty, elapsed_seconds=_time.monotonic() - start)
        if '429' in str(result.error_msg).lower() or 'too many requests' in str(result.error_msg).lower():
            row['status'] = 'rate_limited_stop'
    except BaseException as exc:
        _signal.alarm(0)
        row.update(status='request_failed', error=f'{type(exc).__name__}: {exc}')
    finally:
        row['finished_at'] = _dt.datetime.now().astimezone().isoformat()
        try:
            logout = bs.logout()
            row.update(logout_error_code=logout.error_code, logout_error_msg=logout.error_msg)
        except Exception as exc:
            row['logout_error'] = f'{type(exc).__name__}: {exc}'
    return row


if __name__ == '__main__':
    raise SystemExit(main())
