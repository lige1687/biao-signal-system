"""Acquire the twelve fixed year-end BaoStock industry snapshots."""
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
HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / 'luna-industry-history-contract.json'
PLAN_PATH = HERE / 'industry-history-plan.json'
STORAGE_PATH = HERE / 'storage-plan.json'
COHORT_PATH = HERE / 'financial-cohort.json'
PRIOR_2015_PATH = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/lowfreq-profitability-increment-20261019/lowfreq-profitability-increment-20261019-20261019T102257-90b550e27121/result/probe/sdk-6-query_stock_industry.json')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_exclusive(path: Path, value: object) -> bytes:
    data = json.dumps(value, ensure_ascii=False, indent=2, default=str).encode('utf-8')
    with path.open('xb') as f:
        f.write(data)
    return data


def storage_guard(plan: dict) -> dict:
    mount = Path(plan['external_mount'])
    base = mount / 'LeiSignal-新实验结果'
    out = Path(json.loads(PLAN_PATH.read_text())['out'])
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    checks = {
        'mounted': os.path.ismount(mount),
        'mount_point': info.get('MountPoint') == str(mount),
        'uuid': info.get('VolumeUUID') == plan['external_uuid'],
        'device': mount.stat().st_dev == plan['external_device'],
        'external': info.get('Internal') is False,
        'writable': info.get('Writable') is True,
        'managed_base_exists': base.is_dir() and base.stat().st_dev == plan['external_device'],
        'output_parent_is_saved_result': out.parent == Path(plan['output']),
        'output_parent_exists_on_device': out.parent.is_dir() and out.parent.stat().st_dev == plan['external_device'],
        'output_absent': not out.exists(),
        'external_capacity': shutil.disk_usage(mount).free >= plan['external_reserve_bytes'] + plan['estimated_bytes'],
    }
    if not all(checks.values()):
        raise RuntimeError(f'external storage guard failed: {checks}')
    return checks


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text())
    plan = json.loads(PLAN_PATH.read_text())
    storage = json.loads(STORAGE_PATH.read_text())
    cohort = json.loads(COHORT_PATH.read_text())
    out = Path(plan['out'])
    old = json.loads(PRIOR_2015_PATH.read_text())
    fixed = cohort['fixed_codes']
    if len(fixed) != 600 or len(set(fixed)) != 600:
        raise RuntimeError('financial cohort must contain exactly 600 unique fixed codes')
    if (plan['queries'] != 12 or len(plan['dates']) != 12 or plan['retries'] != 0
            or plan['delay_seconds'] != 1 or plan['timeout_seconds'] != 40
            or plan['sdk'] != 'query_stock_industry'):
        raise RuntimeError('frozen query plan mismatch')
    if old.get('error_code') != '0' or len(old.get('rows', [])) != 2853:
        raise RuntimeError('previous 2015-06-30 cached probe does not match expected source')
    checks = storage_guard(storage)
    out.mkdir(parents=False, exist_ok=False)
    attempts_path = out / 'attempts.jsonl'
    log = attempts_path.open('x', encoding='utf-8')
    attempts: list[dict] = []

    def record(row: dict) -> None:
        attempts.append(row)
        log.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
        log.flush()

    socket.setdefaulttimeout(int(plan['timeout_seconds']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('BaoStock operation exceeded 40 seconds')))
    import baostock as bs
    from baostock import cons
    cons.BAOSTOCK_PER_PAGE_COUNT = 4000
    login_started = time.monotonic()
    signal.alarm(40)
    try:
        login = bs.login()
    finally:
        signal.alarm(0)
    logged_in = getattr(login, 'error_code', None) == '0'
    login_row = {'kind': 'login', 'status': 'ok' if logged_in else 'failed', 'error_code': getattr(login, 'error_code', None),
                 'error_msg': getattr(login, 'error_msg', None), 'elapsed_seconds': round(time.monotonic() - login_started, 3),
                 'timestamp': dt.datetime.now().astimezone().isoformat()}
    record(login_row)
    stopped = False
    consecutive_failures = 0
    requests_sent = 0
    snapshot_results: list[dict] = []
    if not logged_in:
        for date in plan['dates']:
            snapshot_results.append({'date': date, 'status': 'not_issued_login_failed', 'row_count': 0, 'rows': []})
    else:
        for date in plan['dates']:
            if stopped or consecutive_failures >= 2:
                snapshot_results.append({'date': date, 'status': 'not_issued_stop_condition', 'row_count': 0, 'rows': []})
                continue
            time.sleep(float(plan['delay_seconds']))
            started = time.monotonic()
            attempt = {'kind': 'data_request', 'date': date, 'method': plan['sdk'], 'kwargs': {'date': date},
                       'started_at': dt.datetime.now().astimezone().isoformat(), 'requested_page_size': cons.BAOSTOCK_PER_PAGE_COUNT}
            rows, page_counts, page_sizes, fields = [], {}, {}, []
            try:
                requests_sent += 1
                signal.alarm(int(plan['timeout_seconds']))
                result = bs.query_stock_industry(date=date)
                fields = list(result.fields)
                first_ok = result.error_code == '0'
                while result.error_code == '0' and result.next():
                    rows.append(result.get_row_data())
                    page = str(getattr(result, 'cur_page_num', 'unknown'))
                    size_val = getattr(result, 'per_page_count', None)
                    page_size = int(size_val) if size_val not in (None, '') else cons.BAOSTOCK_PER_PAGE_COUNT
                    page_counts[page] = page_counts.get(page, 0) + 1
                    page_sizes[page] = page_size
                    cons.BAOSTOCK_PER_PAGE_COUNT = page_size
                signal.alarm(0)
                success = first_ok and result.error_code == '0'
                body = {'request': {'method': plan['sdk'], 'kwargs': {'date': date}}, 'fields': fields, 'rows': rows,
                        'error_code': result.error_code, 'error_msg': result.error_msg,
                        'page_count': len(page_counts), 'rows_by_page': page_counts, 'returned_page_sizes': page_sizes}
                raw = json.dumps(body, ensure_ascii=False, indent=2).encode('utf-8')
                raw_path = out / f'industry-{date}.json'
                with raw_path.open('xb') as f:
                    f.write(raw)
                attempt.update(status='ok' if success else 'source_failed', fields=fields, row_count=len(rows), page_count=len(page_counts),
                               rows_by_page=page_counts, returned_page_sizes=page_sizes, error_code=result.error_code,
                               error_msg=result.error_msg, raw_path=str(raw_path), raw_bytes=len(raw), raw_sha256=digest(raw))
                consecutive_failures = 0 if success else consecutive_failures + 1
                msg = str(result.error_msg).lower()
                if '429' in msg or 'too many requests' in msg or 'rate limit' in msg:
                    attempt['status'] = 'rate_limited_stop'
                    stopped = True
                    consecutive_failures = 2
                snapshot_results.append({'date': date, 'status': attempt['status'], 'row_count': len(rows), 'rows': rows,
                                         'fields': fields, 'raw_path': str(raw_path), 'raw_bytes': len(raw), 'raw_sha256': digest(raw),
                                         'error_code': result.error_code, 'error_msg': result.error_msg,
                                         'page_count': len(page_counts), 'rows_by_page': page_counts, 'returned_page_sizes': page_sizes})
            except Exception as exc:
                signal.alarm(0)
                attempt.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                consecutive_failures += 1
                snapshot_results.append({'date': date, 'status': 'failed', 'row_count': len(rows), 'rows': rows, 'error': attempt['error']})
            attempt['elapsed_seconds'] = round(time.monotonic() - started, 3)
            attempt['finished_at'] = dt.datetime.now().astimezone().isoformat()
            record(attempt)
    if logged_in:
        try:
            logout = bs.logout()
            record({'kind': 'logout', 'status': 'ok' if logout.error_code == '0' else 'failed', 'error_code': logout.error_code, 'error_msg': logout.error_msg})
        except Exception as exc:
            record({'kind': 'logout', 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
    log.close()

    # Compare the 600 fixed codes with eligible rows only; later updateDate values remain raw but do not count.
    coverage = []
    eligible_by_date: dict[str, dict[str, dict]] = {}
    for snap in snapshot_results:
        date = snap['date']
        rowdict: dict[str, dict] = {}
        raw_codes = set()
        missing_industry = 0
        missing_classification = 0
        late = 0
        missing_update = 0
        updates = []
        field_names = snap.get('fields', [])
        field_index = {name: field_names.index(name) for name in ('updateDate', 'code', 'code_name', 'industry', 'industryClassification') if name in field_names}
        required_fields = {'updateDate', 'code', 'code_name', 'industry', 'industryClassification'}
        missing_fields = sorted(required_fields - set(field_index))
        for row in snap.get('rows', []):
            if missing_fields or any(field_index[name] >= len(row) for name in required_fields):
                continue
            update_date = row[field_index['updateDate']]
            code = row[field_index['code']]
            name = row[field_index['code_name']]
            industry = row[field_index['industry']]
            classification = row[field_index['industryClassification']]
            raw_codes.add(code)
            if not industry:
                missing_industry += 1
            if not classification:
                missing_classification += 1
            if update_date:
                updates.append(update_date)
            else:
                missing_update += 1
                continue
            if update_date > date:
                late += 1
                continue
            entry = {'updateDate': update_date, 'code_name': name, 'industry': industry,
                     'industryClassification': classification}
            if code in rowdict:
                rowdict[code] = {'ambiguous_duplicate_rows': [rowdict[code], entry]}
            else:
                rowdict[code] = entry
        eligible_by_date[date] = rowdict
        raw_covered = sorted(set(fixed) & raw_codes)
        eligible_covered = sorted(set(fixed) & set(rowdict))
        cohort_rows = [rowdict[code] for code in eligible_covered if 'ambiguous_duplicate_rows' not in rowdict[code]]
        coverage.append({'date': date, 'status': snap['status'], 'source_rows': snap['row_count'],
                         'raw_covered_count': len(raw_covered), 'raw_missing_codes': sorted(set(fixed) - set(raw_covered)),
                         'eligible_covered_count': len(eligible_covered), 'eligible_missing_codes': sorted(set(fixed) - set(eligible_covered)),
                         'updateDate_min': min(updates) if updates else None, 'updateDate_max': max(updates) if updates else None,
                         'updateDate_missing_rows': missing_update, 'updateDate_after_query_date_rows': late,
                         'source_rows_missing_industry': missing_industry, 'source_rows_missing_industryClassification': missing_classification,
                         'eligible_cohort_rows_missing_industry': sum(not x.get('industry') for x in cohort_rows),
                         'eligible_cohort_rows_missing_industryClassification': sum(not x.get('industryClassification') for x in cohort_rows),
                         'unique_codes': len(raw_codes), 'duplicate_codes': max(0, len(snap.get('rows', [])) - len(raw_codes)),
                         'missing_required_fields': missing_fields})
    changes = []
    for index in range(1, len(plan['dates'])):
        previous, current = plan['dates'][index - 1], plan['dates'][index]
        a, b = eligible_by_date.get(previous, {}), eligible_by_date.get(current, {})
        for code in fixed:
            if code not in a or code not in b:
                continue
            x, y = a[code], b[code]
            if 'ambiguous_duplicate_rows' in x or 'ambiguous_duplicate_rows' in y:
                continue
            if (x.get('industry'), x.get('industryClassification')) != (y.get('industry'), y.get('industryClassification')):
                changes.append({'code': code, 'from_date': previous, 'to_date': current,
                                'from_industry': x.get('industry'), 'to_industry': y.get('industry'),
                                'from_classification': x.get('industryClassification'),
                                'to_classification': y.get('industryClassification')})
    manifest = {
        'schema': 'historical-industry-snapshots/1',
        'contract_sha256': digest(CONTRACT_PATH.read_bytes()),
        'plan_sha256': digest(PLAN_PATH.read_bytes()),
        'storage_plan_sha256': digest(STORAGE_PATH.read_bytes()),
        'cohort_sha256': digest(COHORT_PATH.read_bytes()),
        'fixed_cohort_count': len(fixed), 'fixed_cohort_codes': fixed,
        'previous_probe_reused': {'path': str(PRIOR_2015_PATH), 'sha256': digest(PRIOR_2015_PATH.read_bytes()),
                                  'date': '2015-06-30', 'rows': len(old.get('rows', [])), 'requeried': False},
        'storage_checks': checks, 'output': str(out),
        'requests_planned': 12, 'requests_attempted': requests_sent,
        'request_successes': sum(1 for x in attempts if x.get('kind') == 'data_request' and x.get('status') == 'ok'),
        'unissued_dates': [x['date'] for x in snapshot_results if str(x.get('status', '')).startswith('not_issued')],
        'attempts': attempts, 'annual_snapshots': [{k: v for k, v in snap.items() if k != 'rows'} for snap in snapshot_results],
        'coverage_by_date': coverage,
        'adjacent_year_label_change_count': len(changes),
        'adjacent_year_label_changes': changes,
        'interpretation_limits': ['Only returned updateDate<=query-date rows are counted as eligible; updateDate is a provider field and its first public/vendor availability is not independently verified.',
                                  '2015-06-30 cached probe was reused descriptively and was not substituted for the 2015-12-31 query.',
                                  'No current industry label was used to fill a missing historical row.',
                                  'This is source coverage and label-change information only; no market effects were computed.']
    }
    mbytes = write_json_exclusive(out / 'manifest.json', manifest)
    print(json.dumps({'status': 'complete' if len([x for x in attempts if x.get('kind') == 'data_request']) == 12 and manifest['request_successes'] == 12 else 'partial',
                      'attempted': requests_sent, 'successes': manifest['request_successes'], 'unissued_dates': manifest['unissued_dates'],
                      'manifest': str(out / 'manifest.json'), 'manifest_sha256': digest(mbytes)}, ensure_ascii=False))
    return 0 if requests_sent == 12 and manifest['request_successes'] == 12 else 2


if __name__ == '__main__':
    raise SystemExit(main())
