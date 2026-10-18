"""Serial single-session continuation for the frozen 600-stock history sample."""
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
BULK = json.loads((HERE / 'bulk-v1.json').read_text())
RESUME = json.loads((HERE / 'resume-single-v1.json').read_text())
PLAN_BYTES = (HERE / 'storage-plan.json').read_bytes()
PLAN = json.loads(PLAN_BYTES)
RUN = Path(PLAN['run_directory'])
OUT = Path(PLAN['output'])
OLD_SEQ = OUT / 'acquisition'
OLD_PAR = OUT / 'acquisition-parallel'
DEST = OUT / 'acquisition-single-resume'
START_DATE, END_DATE = BULK['price_window']
FIELDS = BULK['fields']
MAX_REQUESTS = int(RESUME['remaining_calls_max'])
TIMEOUT = int(BULK['query_budget']['timeout_seconds'])
SPACING = float(BULK['query_budget']['spacing_seconds'])
PER_PAGE = 4000
RETRY_CODES = {'sz.002353', 'sz.002619', 'sz.300175', 'sz.002367', 'sh.600690'}


def now() -> str:
    return dt.datetime.now().astimezone().isoformat()


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def storage_guard() -> None:
    mount = Path(PLAN['external_mount'])
    if not os.path.ismount(mount) or mount.stat().st_dev != PLAN['external_device']:
        raise RuntimeError('registered external disk lost or device changed')
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    if info.get('VolumeUUID') != PLAN['external_uuid'] or info.get('Writable') is not True:
        raise RuntimeError('external UUID or writable state changed')
    if shutil.disk_usage(mount).free < PLAN['external_reserve_bytes']:
        raise RuntimeError('external capacity reserve no longer available')


def exclusive_json(path: Path, value: object) -> bytes:
    raw = json.dumps(value, ensure_ascii=False, indent=2, default=str).encode()
    with path.open('xb') as f:
        f.write(raw)
    return raw


def source_record(path: Path, code: str, kind: str, request: dict, prior: bool = False) -> dict:
    raw = path.read_bytes()
    body = json.loads(raw)
    if not body.get('fields') or body.get('error_code') != '0' or not body.get('data'):
        raise RuntimeError(f'prior source is not a successful nonempty response: {path}')
    return {'code': code, 'kind': kind, 'path': str(path), 'rows': len(body['data']), 'fields': body['fields'], 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'status': 'ok', 'source': BULK['source'], 'request': request, 'origin': 'prior_verified' if prior else 'current_run'}


def request_queue() -> list[dict]:
    q = []
    for x in RESUME['queue']:
        code, kind, adjustflag = x['code'], x['kind'], x['adjustflag']
        if kind == 'daily':
            kwargs = {'code': code, 'fields': FIELDS, 'start_date': START_DATE, 'end_date': END_DATE, 'frequency': 'd', 'adjustflag': adjustflag}
        elif kind == 'raw_daily':
            kwargs = {'code': code, 'fields': FIELDS, 'start_date': START_DATE, 'end_date': END_DATE, 'frequency': 'd', 'adjustflag': adjustflag}
        elif kind == 'adjust_factor':
            # frequency/adjustflag stay in the receipt as scope labels; BaoStock's factor method accepts only code/date bounds.
            kwargs = {'code': code, 'start_date': START_DATE, 'end_date': END_DATE, 'frequency': 'd', 'adjustflag': None}
        else:
            raise RuntimeError(f'unknown frozen kind: {kind}')
        q.append({'code': code, 'kind': kind, 'adjustflag': adjustflag, 'kwargs': kwargs})
    if len(q) != MAX_REQUESTS:
        raise RuntimeError(f'resume queue length mismatch: {len(q)}')
    return q


def verified_prior_sources() -> dict[tuple[str, str], dict]:
    expected_manifest_hash = RESUME['old_manifest']['sha256']
    old_manifest_path = Path(RESUME['old_manifest']['path'])
    if hash_file(old_manifest_path) != expected_manifest_hash:
        raise RuntimeError('parallel predecessor manifest hash changed')
    parallel_manifest = json.loads(old_manifest_path.read_text())
    if parallel_manifest.get('successful_sources') != RESUME['already_successful']:
        raise RuntimeError('parallel predecessor successful-source count mismatch')
    prior: dict[tuple[str, str], dict] = {}
    for item in parallel_manifest['files']:
        if item['status'] != 'ok':
            continue
        path = Path(item['path'])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256'] or len(raw) != item['bytes']:
            raise RuntimeError(f'parallel successful source hash changed: {path}')
        body = json.loads(raw)
        if body['error_code'] != '0' or len(body['data']) != item['rows'] or body['fields'] != item['fields']:
            raise RuntimeError(f'parallel successful source schema changed: {path}')
        key = (item['code'], item['kind'])
        prior[key] = {'code': item['code'], 'kind': item['kind'], 'path': str(path), 'rows': item['rows'], 'fields': item['fields'], 'bytes': item['bytes'], 'sha256': item['sha256'], 'status': 'ok', 'source': item['source'], 'request': item['request'], 'origin': 'prior_verified'}
    for line in (OLD_SEQ / 'attempts.jsonl').read_text().splitlines():
        item = json.loads(line)
        if item.get('kind') != 'data_request' or item.get('status') != 'ok':
            continue
        path = Path(item['raw_path'])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['raw_sha256'] or len(raw) != item['raw_bytes']:
            raise RuntimeError(f'sequential successful source hash changed: {path}')
        body = json.loads(raw)
        if body['error_code'] != '0' or len(body['data']) != item['rows'] or body['fields'] != item['fields']:
            raise RuntimeError(f'sequential successful source schema changed: {path}')
        prior[(item['code'], item['request_type'])] = {'code': item['code'], 'kind': item['request_type'], 'path': str(path), 'rows': item['rows'], 'fields': item['fields'], 'bytes': item['raw_bytes'], 'sha256': item['raw_sha256'], 'status': 'ok', 'source': item['source'], 'request': item['kwargs'], 'origin': 'prior_verified'}
    if len(prior) != RESUME['already_successful']:
        raise RuntimeError(f'expected {RESUME["already_successful"]} unique prior successes, got {len(prior)}')
    return prior


def verify_contract() -> None:
    if hash_file(HERE / 'bulk-v1.json') != RESUME['original_bulk_sha256']:
        raise RuntimeError('original bulk-v1 hash changed')
    if hash_file(HERE / 'storage-plan.json') != BULK['storage_plan']['sha256']:
        raise RuntimeError('storage plan hash changed')
    if hash_file(Path(BULK['study_design']['path'])) != BULK['study_design']['sha256']:
        raise RuntimeError('design hash changed')
    if hash_file(Path(BULK['cohort']['path'])) != BULK['cohort']['sha256']:
        raise RuntimeError('cohort hash changed')
    if hash_file(Path(BULK['calendar']['path'])) != BULK['calendar']['sha256']:
        raise RuntimeError('calendar hash changed')
    if RUN.name != PLAN['run_id'] or not (OUT / 'probe' / 'summary.json').is_file():
        raise RuntimeError('bound run or probe missing')
    if DEST.exists():
        raise RuntimeError(f'refuse existing output directory: {DEST}')
    storage_guard()


def main() -> int:
    verify_contract()
    queue = request_queue()
    prior = verified_prior_sources()
    if len(prior) != 39:
        raise RuntimeError('expected 39 verified prior successes')
    # Confirm retry keys are precisely the five session-invalidated daily sources.
    failed = set()
    parallel_attempts = [json.loads(x) for x in (OLD_PAR / 'attempts.jsonl').read_text().splitlines() if x.strip()]
    for row in parallel_attempts:
        if row.get('kind') == 'data_request' and row.get('status') == 'source_error' and row.get('error_code') == '10001001':
            failed.add(row['code'])
    if failed != RETRY_CODES:
        raise RuntimeError(f'session-invalidated retry set mismatch: {sorted(failed)}')
    DEST.mkdir(exist_ok=False)
    storage_guard()
    started = now()
    queue_doc = {'version': RESUME['version'], 'source': BULK['source'], 'previous_successes_reused': len(prior), 'previous_starts': RESUME['already_started'], 'new_attempts_ceiling': MAX_REQUESTS, 'retry_codes_one_additional_attempt': sorted(RETRY_CODES), 'per_page_count': PER_PAGE, 'requests': queue}
    exclusive_json(DEST / 'request-queue.json', queue_doc)
    attempts_path = DEST / 'attempts.jsonl'
    attempts_file = attempts_path.open('x', encoding='utf-8')
    sources = dict(prior)
    failures: list[dict] = []
    started_requests = 0
    consecutive_errors = 0
    abort_reason = None
    previous_start = 0.0

    import baostock as bs
    import baostock.common.contants as cons
    cons.BAOSTOCK_PER_PAGE_COUNT = PER_PAGE
    socket.setdefaulttimeout(TIMEOUT)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(f'BaoStock request exceeded {TIMEOUT}s')))
    signal.alarm(TIMEOUT)
    login = bs.login()
    signal.alarm(0)
    attempts_file.write(json.dumps({'kind': 'login', 'at': now(), 'error_code': login.error_code, 'error_msg': login.error_msg, 'per_page_count': cons.BAOSTOCK_PER_PAGE_COUNT}, ensure_ascii=False) + '\n')
    attempts_file.flush()
    if login.error_code != '0':
        missing_daily = [code for code in BULK['selected_codes'] if (code, 'daily') not in sources]
        exclusive_json(DEST / 'manifest.json', {'status': 'partial', 'daily_cohort_complete': False, 'stop_reason': f'anonymous login failed: {login.error_code} {login.error_msg}', 'successful_sources': list(sources.values()), 'failures': failures, 'missing_daily_codes': missing_daily})
        attempts_file.close()
        return 1

    try:
        for i, task in enumerate(queue, 1):
            code, kind, kwargs = task['code'], task['kind'], task['kwargs']
            attempt_number = 2 if code in RETRY_CODES and kind == 'daily' else 1
            if attempt_number == 2:
                # Failed, invalid-session responses from the predecessor are preserved; this is the single authorized second attempt.
                prior_failure_count = sum(1 for r in parallel_attempts if r.get('kind') == 'data_request' and r.get('code') == code and r.get('status') == 'source_error')
                if prior_failure_count != 1:
                    raise RuntimeError(f'retry count mismatch for {code}')
            if previous_start:
                gap = SPACING - (time.monotonic() - previous_start)
                if gap > 0:
                    time.sleep(gap)
            storage_guard()
            started_requests += 1
            start_mono = time.monotonic()
            previous_start = start_mono
            row = {'kind': 'data_request', 'code': code, 'request_type': kind, 'source': BULK['source'], 'request': kwargs, 'attempt_number': attempt_number, 'started_at': now(), 'pid': os.getpid(), 'per_page_count_requested': PER_PAGE}
            attempts_file.write(json.dumps(row, ensure_ascii=False) + '\n')
            attempts_file.flush()
            try:
                signal.alarm(TIMEOUT)
                if kind in ('daily', 'raw_daily'):
                    result = bs.query_history_k_data_plus(code, kwargs['fields'], start_date=START_DATE, end_date=END_DATE, frequency=kwargs['frequency'], adjustflag=kwargs['adjustflag'])
                elif kind == 'adjust_factor':
                    result = bs.query_adjust_factor(code, start_date=START_DATE, end_date=END_DATE)
                else:
                    raise ValueError(kind)
                rows = []
                while result.error_code == '0' and result.next():
                    rows.append(result.get_row_data())
                signal.alarm(0)
                per_page_returned = int(getattr(result, 'per_page_count', 0) or 0)
                page_returned = int(getattr(result, 'cur_page_num', '0') or 0)
                body = {'fields': result.fields, 'data': rows, 'error_code': result.error_code, 'error_msg': result.error_msg, 'pages_returned': page_returned, 'per_page_count_requested': PER_PAGE, 'per_page_count_returned': per_page_returned}
                raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
                payload_path = DEST / f'{code}-{kind}-attempt{attempt_number}.json'
                with payload_path.open('xb') as f:
                    f.write(raw)
                empty = not rows
                source_error = result.error_code != '0'
                cap_suspected = kind in ('daily', 'raw_daily') and len(rows) == 2000 and per_page_returned == PER_PAGE and page_returned == 1
                status = 'ok' if not empty and not source_error and not cap_suspected else ('empty_response' if empty and not source_error else ('suspected_2000_row_cap' if cap_suspected else 'source_error'))
                row.update(status=status, finished_at=now(), fields=result.fields, rows=len(rows), pages_returned=page_returned, per_page_count_returned=per_page_returned, error_code=result.error_code, error_msg=result.error_msg, raw_path=str(payload_path), raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(), elapsed_seconds=time.monotonic() - start_mono)
                err_text = str(result.error_msg).lower()
                if '429' in err_text or 'too many requests' in err_text:
                    row['status'] = 'rate_limited_stop'
                success = row['status'] == 'ok'
                if success:
                    consecutive_errors = 0
                    sources[(code, kind)] = {'code': code, 'kind': kind, 'path': str(payload_path), 'rows': len(rows), 'fields': result.fields, 'bytes': len(raw), 'sha256': row['raw_sha256'], 'status': 'ok', 'source': BULK['source'], 'request': kwargs, 'attempt_number': attempt_number, 'origin': 'current_run', 'pages_returned': page_returned, 'per_page_count_requested': PER_PAGE, 'per_page_count_returned': per_page_returned}
                else:
                    consecutive_errors += 1
                    failures.append({'code': code, 'kind': kind, 'attempt_number': attempt_number, 'status': row['status'], 'error_code': result.error_code, 'error_msg': result.error_msg, 'path': str(payload_path), 'sha256': row['raw_sha256']})
                if row['status'] == 'rate_limited_stop':
                    abort_reason = '429 rate limit'; consecutive_errors = 2
                elif row['status'] == 'suspected_2000_row_cap':
                    abort_reason = f'possible 2000-row server cap for {code}; refusing possibly truncated daily source'
            except Exception as exc:
                signal.alarm(0)
                row.update(status='request_failed', finished_at=now(), error=f'{type(exc).__name__}: {exc}', elapsed_seconds=time.monotonic() - start_mono)
                failures.append({'code': code, 'kind': kind, 'attempt_number': attempt_number, 'status': row['status'], 'error': row['error']})
                consecutive_errors += 1
            attempts_file.write(json.dumps(row, ensure_ascii=False) + '\n')
            attempts_file.flush()
            if started_requests % 50 == 0:
                daily_ok = sum(1 for (c, k), s in sources.items() if k == 'daily' and s['status'] == 'ok')
                print(json.dumps({'new_requests': started_requests, 'cumulative_started': RESUME['already_started'] + started_requests, 'daily_codes_ok': daily_ok, 'failures': len(failures), 'last': f'{code}:{kind}:{row["status"]}'}, ensure_ascii=False), flush=True)
            if abort_reason is None and consecutive_errors >= 2:
                abort_reason = 'two consecutive source errors'
            if abort_reason:
                break
    finally:
        signal.alarm(0)
        try:
            logout = bs.logout()
            attempts_file.write(json.dumps({'kind': 'logout', 'at': now(), 'error_code': logout.error_code, 'error_msg': logout.error_msg}, ensure_ascii=False) + '\n')
            attempts_file.flush()
        finally:
            attempts_file.close()

    daily_codes = {c for (c, k), v in sources.items() if k == 'daily' and v['status'] == 'ok'}
    missing_daily = [c for c in BULK['selected_codes'] if c not in daily_codes]
    expected_keys = {(x['code'], x['kind']) for x in queue}
    missing_requests = [{'code': code, 'kind': kind} for code, kind in sorted(expected_keys - set(sources))]
    status = 'complete' if not missing_daily and not failures and not abort_reason else 'partial'
    previous_failures = [x for x in parallel_attempts if x.get('kind') == 'data_request' and x.get('status') == 'source_error']
    final = {'schema': 'lei-history-acquisition-manifest/2.0', 'status': status, 'daily_cohort_complete': len(missing_daily) == 0, 'source': BULK['source'], 'bulk_version': BULK['version'], 'bulk_sha256': hash_file(HERE / 'bulk-v1.json'), 'resume_contract': RESUME['version'], 'resume_queue_sha256': hash_file(HERE / 'resume-single-v1.json'), 'storage_run_id': PLAN['run_id'], 'prior_successes_reused': len(prior), 'prior_data_calls_started': RESUME['already_started'], 'new_data_calls_started': started_requests, 'cumulative_data_calls_started': RESUME['already_started'] + started_requests, 'new_successes': len(sources) - len(prior), 'successful_sources': len(sources), 'daily_codes_successful': len(daily_codes), 'daily_codes_expected': len(BULK['selected_codes']), 'missing_daily_codes': missing_daily, 'previous_parallel_failures': previous_failures, 'failures': failures, 'missing_requests': missing_requests, 'stop_reason': abort_reason, 'retry_policy': {'retry_codes': sorted(RETRY_CODES), 'max_attempt_number': 2, 'other_requests_retried': False}, 'pagination': {'runtime_per_page_count': PER_PAGE, 'truncation_rule': 'exactly 2000 daily rows in one 4000-sized page is marked suspected_2000_row_cap and excluded from success', 'per_request_recorded': True}, 'sources': [sources[k] for k in sorted(sources)], 'started_at': started, 'finished_at': now(), 'not_computed': ['factor performance', 'returns', 'signals']}
    exclusive_json(DEST / 'manifest.json', final)
    print(json.dumps({'status': status, 'new_requests': started_requests, 'cumulative_calls': final['cumulative_data_calls_started'], 'success_sources': len(sources), 'daily_codes': len(daily_codes), 'missing_daily': len(missing_daily), 'failures': len(failures), 'stop_reason': abort_reason}, ensure_ascii=False), flush=True)
    return 0 if status == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
