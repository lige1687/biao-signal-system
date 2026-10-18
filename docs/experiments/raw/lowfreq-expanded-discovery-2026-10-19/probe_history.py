"""Six bounded anonymous BaoStock history and membership probes."""
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
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted

PLAN = json.loads((HERE / 'storage-plan.json').read_text())
PROBE = Path(PLAN['output']) / 'probe'


def verify_storage() -> dict:
    plan = recheck_saved_plan(ROOT, PLAN, PLAN['task_id'], PLAN['estimated_bytes'], PLAN['internal_metadata_bytes'])
    mount = Path(plan['external_mount'])
    external_base = mount / 'LeiSignal-新实验结果' / plan['task_id']
    parent = Path(plan['run_directory'])
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    checks = {
        'mounted': os.path.ismount(mount),
        'mount_point': info.get('MountPoint') == str(mount),
        'uuid': info.get('VolumeUUID') == plan['external_uuid'],
        'device': mount.stat().st_dev == plan['external_device'],
        'external': info.get('Internal') is False,
        'writable': info.get('Writable') is True,
        'target_parent_device': external_base.parent.stat().st_dev == plan['external_device'],
        'run_absent': not parent.exists(),
        'external_capacity': shutil.disk_usage(mount).free >= plan['external_reserve_bytes'] + plan['estimated_bytes'],
        'internal_capacity': shutil.disk_usage(ROOT).free >= plan['internal_reserve_bytes'] + plan['internal_metadata_bytes'],
        'target_absent': not PROBE.exists(),
    }
    if not _still_mounted(plan) or not all(checks.values()):
        raise RuntimeError(f'storage guard failed: {checks}')
    external_base.mkdir(exist_ok=True)
    if not _still_mounted(plan) or external_base.stat().st_dev != plan['external_device']:
        raise RuntimeError('created task directory does not match the bound external device')
    parent.mkdir(parents=False, exist_ok=False)
    (parent / 'storage-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    (Path(plan['output'])).mkdir(parents=False, exist_ok=False)
    PROBE.mkdir(parents=False, exist_ok=False)
    return checks


def write_json_exclusive(path: Path, obj: object) -> bytes:
    payload = json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode()
    with path.open('xb') as f:
        f.write(payload)
    return payload


def main() -> int:
    checks = verify_storage()
    attempts_path = PROBE / 'attempts.jsonl'
    summary_path = PROBE / 'summary.json'
    attempts: list[dict] = []
    max_requests = 6
    requests_used = 0
    consecutive_failures = 0
    socket.setdefaulttimeout(40)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('BaoStock request exceeded 40 seconds')))
    import baostock as bs

    login_start = time.monotonic()
    signal.alarm(40)
    login = bs.login()
    signal.alarm(0)
    login_row = {'kind': 'login', 'source': 'BaoStock anonymous', 'at': dt.datetime.now().astimezone().isoformat(), 'error_code': login.error_code, 'error_msg': login.error_msg, 'elapsed_seconds': time.monotonic() - login_start}
    with attempts_path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(login_row, ensure_ascii=False) + '\n')
    attempts.append(login_row)
    if login.error_code != '0':
        write_json_exclusive(summary_path, {'status': 'login_failed', 'data_requests_used': 0, 'max_data_requests': max_requests, 'storage_checks': checks, 'attempts': attempts})
        return 1

    specs = [
        ('stock_basic', bs.query_stock_basic, {}),
        ('all_stock_2014_12_31', bs.query_all_stock, {'day': '2014-12-31'}),
        ('all_stock_2013_12_31', bs.query_all_stock, {'day': '2013-12-31'}),
        ('trade_dates', bs.query_trade_dates, {'start_date': '2013-01-01', 'end_date': '2026-01-15'}),
        ('maotai_daily', bs.query_history_k_data_plus, {'code': 'sh.600519', 'fields': 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,tradestatus,pctChg,isST', 'start_date': '2013-01-01', 'end_date': '2026-01-15', 'frequency': 'd', 'adjustflag': '2'}),
        ('maotai_adjust_factor', bs.query_adjust_factor, {'code': 'sh.600519', 'start_date': '2013-01-01', 'end_date': '2026-01-15'}),
    ]
    try:
        for key, method, kwargs in specs:
            if requests_used >= max_requests or consecutive_failures >= 2:
                break
            time.sleep(1)
            row = {'kind': 'data_request', 'key': key, 'source': 'BaoStock anonymous', 'kwargs': kwargs, 'at': dt.datetime.now().astimezone().isoformat()}
            requests_used += 1
            try:
                start = time.monotonic()
                signal.alarm(40)
                result = method(**kwargs)
                data = []
                while result.error_code == '0' and result.next():
                    data.append(result.get_row_data())
                signal.alarm(0)
                body = {'fields': result.fields, 'data': data, 'error_code': result.error_code, 'error_msg': result.error_msg}
                raw = json.dumps(body, ensure_ascii=False, indent=2).encode()
                raw_path = PROBE / f'{key}.json'
                with raw_path.open('xb') as f:
                    f.write(raw)
                row.update(status='ok' if result.error_code == '0' else 'source_failed', fields=result.fields, rows=len(data), error_code=result.error_code, error_msg=result.error_msg, raw_path=str(raw_path), raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(), elapsed_seconds=time.monotonic() - start)
                consecutive_failures = 0 if result.error_code == '0' else consecutive_failures + 1
                error_text = str(result.error_msg).lower()
                if '429' in error_text or 'too many requests' in error_text:
                    row['status'] = 'rate_limited_stop'
                    consecutive_failures = 2
            except Exception as exc:
                signal.alarm(0)
                row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                consecutive_failures += 1
            with attempts_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            attempts.append(row)
    finally:
        signal.alarm(0)
        try:
            logout = bs.logout()
            attempts.append({'kind': 'logout', 'source': 'BaoStock anonymous', 'at': dt.datetime.now().astimezone().isoformat(), 'error_code': logout.error_code, 'error_msg': logout.error_msg})
            with attempts_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(attempts[-1], ensure_ascii=False) + '\n')
        except Exception as exc:
            attempts.append({'kind': 'logout', 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
    status = 'complete' if requests_used == 6 and all(x.get('status') == 'ok' for x in attempts if x.get('kind') == 'data_request') else 'partial'
    summary = {'status': status, 'source': 'BaoStock anonymous only', 'data_requests_used': requests_used, 'max_data_requests': max_requests, 'storage_checks': checks, 'requests': [x for x in attempts if x.get('kind') == 'data_request'], 'notes': ['Metadata current listing/status is descriptive only and was not used to exclude names from historical dates.', 'No factor performance, returns, or trading signals were computed.']}
    write_json_exclusive(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if status == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
