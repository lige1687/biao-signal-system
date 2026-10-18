"""Acquire the frozen 600-code A-share sample with bounded BaoStock requests."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).parent
BULK_PATH = HERE / 'bulk-v1.json'
PLAN_PATH = HERE / 'storage-plan.json'
BULK = json.loads(BULK_PATH.read_text())
PLAN = json.loads(PLAN_PATH.read_text())
RUN = Path(PLAN['run_directory'])
OUT = Path(PLAN['output'])
DEST = OUT / BULK['query_budget'].get('output_subdirectory', 'acquisition')
if DEST.name != 'acquisition':
    DEST = OUT / 'acquisition'
MAX_REQUESTS = int(BULK['query_budget']['total_data_max'])
TIMEOUT = int(BULK['query_budget']['timeout_seconds'])
FAIL_STOP = int(BULK['query_budget']['two_consecutive_errors_stop'])
FIELDS = BULK['fields']
START, END = BULK['price_window']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def guard() -> None:
    mount = Path(PLAN['external_mount'])
    if not os.path.ismount(mount) or mount.stat().st_dev != PLAN['external_device']:
        raise RuntimeError('registered external disk lost or device changed')
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    if info.get('VolumeUUID') != PLAN['external_uuid'] or info.get('Writable') is not True:
        raise RuntimeError('external UUID or writable state changed')
    if shutil.disk_usage(mount).free < PLAN['external_reserve_bytes']:
        raise RuntimeError('external reserve no longer available')


def verify_inputs() -> None:
    checks = [
        (Path(BULK['study_design']['path']), BULK['study_design']['sha256']),
        (Path(BULK['cohort']['path']), BULK['cohort']['sha256']),
        (Path(BULK['calendar']['path']), BULK['calendar']['sha256']),
        (PLAN_PATH, BULK['storage_plan']['sha256']),
    ]
    for path, expected in checks:
        if sha(path) != expected:
            raise RuntimeError(f'frozen input hash mismatch: {path}')
    if len(BULK['selected_codes']) != 600 or len(set(BULK['selected_codes'])) != 600:
        raise RuntimeError('frozen selected_codes must contain exactly 600 unique entries')
    if RUN.name != PLAN['run_id'] or not (OUT / 'probe' / 'summary.json').is_file():
        raise RuntimeError('bound probe run is missing or inconsistent')
    if DEST.exists():
        raise RuntimeError(f'refuse existing acquisition directory: {DEST}')
    guard()
    external_base = Path(PLAN['external_mount']) / 'LeiSignal-新实验结果' / PLAN['task_id']
    if external_base.stat().st_dev != PLAN['external_device'] or RUN.parent != external_base:
        raise RuntimeError('run path is outside the bound external task directory')


def exclusive_json(path: Path, obj: object) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode()
    with path.open('xb') as f:
        f.write(raw)
    return raw


def main() -> int:
    verify_inputs()
    DEST.mkdir(exist_ok=False)
    guard()
    data_requests = 0
    consecutive_errors = 0
    attempts: list[dict] = []
    manifest: list[dict] = []
    partial = False
    stop_reason = None
    socket.setdefaulttimeout(TIMEOUT)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(f'BaoStock request exceeded {TIMEOUT}s')))
    import baostock as bs

    signal.alarm(TIMEOUT)
    login = bs.login()
    signal.alarm(0)
    login_receipt = {'kind': 'login', 'source': BULK['source'], 'at': dt.datetime.now().astimezone().isoformat(), 'error_code': login.error_code, 'error_msg': login.error_msg}
    with (DEST / 'attempts.jsonl').open('x', encoding='utf-8') as f:
        f.write(json.dumps(login_receipt, ensure_ascii=False) + '\n')
    attempts.append(login_receipt)
    if login.error_code != '0':
        exclusive_json(DEST / 'manifest.json', {'status': 'partial', 'stop_reason': 'anonymous login failed', 'data_requests_used': 0, 'max_data_requests': MAX_REQUESTS, 'files': manifest})
        return 1

    spot = set(BULK['spot_check_codes'])
    queue = [(code, 'daily', {'code': code, 'fields': FIELDS, 'start_date': START, 'end_date': END, 'frequency': 'd', 'adjustflag': BULK['adjustflag']}) for code in BULK['selected_codes']]
    for code in BULK['spot_check_codes']:
        queue.append((code, 'raw_daily', {'code': code, 'fields': FIELDS, 'start_date': START, 'end_date': END, 'frequency': 'd', 'adjustflag': '3'}))
        queue.append((code, 'adjust_factor', {'code': code, 'start_date': START, 'end_date': END}))
    if len(queue) != MAX_REQUESTS or len(spot) != 5:
        raise RuntimeError(f'fixed request queue mismatch: {len(queue)}')
    write_queue = [{'code': c, 'kind': k, 'kwargs': a} for c, k, a in queue]
    exclusive_json(DEST / 'request-queue.json', {'source': BULK['source'], 'count': len(write_queue), 'requests': write_queue})

    try:
        for code, kind, kwargs in queue:
            if data_requests >= MAX_REQUESTS:
                partial, stop_reason = True, 'request ceiling reached'
                break
            guard()
            time.sleep(float(BULK['query_budget']['spacing_seconds']))
            row = {'kind': 'data_request', 'code': code, 'request_type': kind, 'source': BULK['source'], 'kwargs': kwargs, 'at': dt.datetime.now().astimezone().isoformat()}
            data_requests += 1
            try:
                start = time.monotonic()
                signal.alarm(TIMEOUT)
                if kind in ('daily', 'raw_daily'):
                    result = bs.query_history_k_data_plus(code, kwargs['fields'], start_date=START, end_date=END, frequency='d', adjustflag=kwargs['adjustflag'])
                else:
                    result = bs.query_adjust_factor(code, start_date=START, end_date=END)
                rows = []
                while result.error_code == '0' and result.next():
                    rows.append(result.get_row_data())
                signal.alarm(0)
                body = {'fields': result.fields, 'data': rows, 'error_code': result.error_code, 'error_msg': result.error_msg}
                filename = f'{code}-{kind}.json'
                raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
                raw_path = DEST / filename
                with raw_path.open('xb') as f:
                    f.write(raw)
                empty = len(rows) == 0
                source_error = result.error_code != '0'
                row.update(status='ok' if not empty and not source_error else ('empty_response' if empty and not source_error else 'source_error'), fields=result.fields, rows=len(rows), error_code=result.error_code, error_msg=result.error_msg, raw_path=str(raw_path), raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(), elapsed_seconds=time.monotonic() - start, empty_response=empty)
                if row['status'] == 'ok':
                    consecutive_errors = 0
                    manifest.append({'code': code, 'kind': kind, 'path': filename, 'rows': len(rows), 'fields': result.fields, 'bytes': len(raw), 'sha256': row['raw_sha256']})
                else:
                    consecutive_errors += 1
                err = str(result.error_msg).lower()
                if '429' in err or 'too many requests' in err:
                    row['status'] = 'rate_limited_stop'
                    consecutive_errors = FAIL_STOP
            except Exception as exc:
                signal.alarm(0)
                row.update(status='request_failed', error=f'{type(exc).__name__}: {exc}')
                consecutive_errors += 1
            with (DEST / 'attempts.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            attempts.append(row)
            if data_requests % 50 == 0:
                print(json.dumps({'completed_requests': data_requests, 'successful_files': len(manifest), 'failures': sum(x.get('status') != 'ok' for x in attempts if x.get('kind') == 'data_request'), 'at': dt.datetime.now().astimezone().isoformat()}), flush=True)
            if consecutive_errors >= FAIL_STOP:
                partial, stop_reason = True, 'two consecutive source errors or rate limit'
                break
    except Exception as exc:
        partial, stop_reason = True, f'guard or execution failure: {type(exc).__name__}: {exc}'
    finally:
        signal.alarm(0)
        try:
            logout = bs.logout()
            lr = {'kind': 'logout', 'source': BULK['source'], 'at': dt.datetime.now().astimezone().isoformat(), 'error_code': logout.error_code, 'error_msg': logout.error_msg}
            with (DEST / 'attempts.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(lr, ensure_ascii=False) + '\n')
            attempts.append(lr)
        except Exception as exc:
            attempts.append({'kind': 'logout', 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})

    status = 'complete' if not partial and data_requests == MAX_REQUESTS and len(manifest) == MAX_REQUESTS else 'partial'
    final = {'schema': 'lei-history-acquisition-manifest/1.0', 'status': status, 'source': BULK['source'], 'bulk_version': BULK['version'], 'bulk_sha256': sha(HERE / 'bulk-v1.json'), 'design_sha256': BULK['study_design']['sha256'], 'cohort_sha256': BULK['cohort']['sha256'], 'calendar_sha256': BULK['calendar']['sha256'], 'storage_run_id': PLAN['run_id'], 'data_requests_used': data_requests, 'max_data_requests': MAX_REQUESTS, 'successful_files': len(manifest), 'failed_requests': [x for x in attempts if x.get('kind') == 'data_request' and x.get('status') != 'ok'], 'stop_reason': stop_reason, 'files': manifest, 'limits': {'retries': 0, 'spacing_seconds': BULK['query_budget']['spacing_seconds'], 'timeout_seconds': TIMEOUT, 'two_consecutive_errors_stop': FAIL_STOP}, 'not_computed': ['factor performance', 'returns', 'signals']}
    exclusive_json(DEST / 'manifest.json', final)
    print(json.dumps({'status': status, 'data_requests_used': data_requests, 'successful_files': len(manifest), 'failed_requests': len(final['failed_requests']), 'stop_reason': stop_reason}, ensure_ascii=False), flush=True)
    return 0 if status == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
