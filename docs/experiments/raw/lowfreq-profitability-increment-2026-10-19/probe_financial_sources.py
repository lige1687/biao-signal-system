"""Run the eight fixed financial-source qualification requests in the bound contract."""
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
import urllib.error
import urllib.request
import zipfile
from io import BytesIO

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted

PLAN = json.loads((HERE / 'storage-plan.json').read_text())
SPEC = json.loads((HERE / 'source-probe-plan.json').read_text())
PROBE = Path(SPEC['external_output']) / 'probe'
TIMEOUT = int(SPEC['timeout_seconds'])
UA = 'LeiSignalResearch/1.0 (read-only public filing source qualification; contact: yongbiaoli)'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_exclusive(path: Path, obj: object) -> bytes:
    data = json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode('utf-8')
    with path.open('xb') as f:
        f.write(data)
    return data


def write_raw(path: Path, data: bytes) -> dict:
    with path.open('xb') as f:
        f.write(data)
    return {'raw_path': str(path), 'raw_bytes': len(data), 'raw_sha256': sha(data)}


def verify_storage() -> dict:
    plan = recheck_saved_plan(ROOT, PLAN, PLAN['task_id'], PLAN['estimated_bytes'], PLAN['internal_metadata_bytes'])
    mount = Path(plan['external_mount'])
    base = mount / 'LeiSignal-新实验结果'
    task_parent = base / plan['task_id']
    run = Path(plan['run_directory'])
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    checks = {
        'mounted': os.path.ismount(mount),
        'mount_point': info.get('MountPoint') == str(mount),
        'uuid': info.get('VolumeUUID') == plan['external_uuid'],
        'device': mount.stat().st_dev == plan['external_device'],
        'external': info.get('Internal') is False,
        'writable': info.get('Writable') is True,
        'managed_base_exists': base.is_dir(),
        'managed_base_device': base.stat().st_dev == plan['external_device'],
        'task_parent_absent': not task_parent.exists(),
        'run_absent': not run.exists(),
        'probe_absent': not PROBE.exists(),
        'external_capacity': shutil.disk_usage(mount).free >= plan['external_reserve_bytes'] + plan['estimated_bytes'],
        'internal_capacity': shutil.disk_usage(ROOT).free >= plan['internal_reserve_bytes'] + plan['internal_metadata_bytes'],
    }
    if not _still_mounted(plan) or not all(checks.values()):
        raise RuntimeError(f'storage guard failed: {checks}')
    task_parent.mkdir(exist_ok=False)
    if not _still_mounted(plan) or task_parent.stat().st_dev != plan['external_device']:
        raise RuntimeError('created task directory does not match bound external device')
    run.mkdir(exist_ok=False)
    write_json_exclusive(run / 'storage-plan.json', plan)
    Path(plan['output']).mkdir(exist_ok=False)
    PROBE.mkdir(exist_ok=False)
    return checks


def sec_read(url: str, max_bytes: int, raw_path: Path) -> tuple[dict, bytes | None, bool]:
    request = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
    started = time.monotonic()
    row = {'kind': 'http', 'url': url, 'user_agent': UA, 'started_at': dt.datetime.now().astimezone().isoformat(), 'max_bytes': max_bytes}
    body = bytearray()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            row.update(http_status=response.status, final_url=response.geturl(), headers={k.lower(): response.headers.get(k) for k in ['Content-Type', 'Content-Length', 'Date', 'Last-Modified', 'ETag']})
            while True:
                if time.monotonic() - started > TIMEOUT:
                    raise TimeoutError(f'HTTP operation exceeded {TIMEOUT}s')
                chunk = response.read(min(1024 * 1024, max_bytes + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > max_bytes:
                    raw = bytes(body[:max_bytes])
                    meta = write_raw(raw_path.with_suffix(raw_path.suffix + '.partial'), raw)
                    row.update(status='oversize_partial', **meta, error=f'response exceeded {max_bytes} bytes')
                    return row, raw, False
        raw = bytes(body)
        meta = write_raw(raw_path, raw)
        row.update(status='ok', **meta)
        return row, raw, True
    except urllib.error.HTTPError as exc:
        row.update(http_status=exc.code, final_url=exc.geturl(), error=f'HTTPError: {exc.reason}')
        try:
            errbody = exc.read(1024 * 1024)
            if errbody:
                row.update(error_body=write_raw(raw_path.with_suffix(raw_path.suffix + '.error-body'), errbody))
        except Exception as read_exc:
            row['error_body_read_error'] = f'{type(read_exc).__name__}: {read_exc}'
        row['status'] = 'rate_limited_stop' if exc.code == 429 else 'http_failed'
        return row, None, False
    except Exception as exc:
        row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        return row, None, False
    finally:
        row.setdefault('elapsed_seconds', round(time.monotonic() - started, 3))
        row.setdefault('finished_at', dt.datetime.now().astimezone().isoformat())


def inspect_facts(raw: bytes) -> dict:
    obj = json.loads(raw)
    fact_names = ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'OperatingIncomeLoss', 'NetIncomeLoss', 'Assets', 'StockholdersEquity']
    taxonomy = obj.get('facts', {}).get('us-gaap', {})
    found = {}
    for name in fact_names:
        fact = taxonomy.get(name)
        if not fact:
            continue
        rows = []
        for unit, values in fact.get('units', {}).items():
            ends = [x.get('end') for x in values if x.get('end')]
            filed = [x.get('filed') for x in values if x.get('filed')]
            rows.append({'unit': unit, 'count': len(values), 'min_end': min(ends) if ends else None, 'max_end': max(ends) if ends else None, 'min_filed': min(filed) if filed else None, 'max_filed': max(filed) if filed else None, 'sample': values[:2]})
        found[name] = rows
    return {'cik': obj.get('cik'), 'entityName': obj.get('entityName'), 'taxonomy_names': list(obj.get('facts', {}).keys()), 'tag_metadata': found}


def inspect_zip(raw: bytes) -> dict:
    result = {}
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        names = zf.namelist()
        result['members'] = [{'name': i.filename, 'size': i.file_size, 'compressed_size': i.compress_size} for i in zf.infolist()]
        for candidate in names:
            low = candidate.lower().rsplit('/', 1)[-1]
            if low == 'readme' or low in {'sub.txt', 'num.txt'}:
                with zf.open(candidate) as f:
                    lines = []
                    for _ in range(8 if low == 'readme' else 5):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line.decode('utf-8', 'replace').rstrip('\r\n'))
                result[low] = lines
    return result


def main() -> int:
    storage_checks = verify_storage()
    attempts_path = PROBE / 'attempts.jsonl'
    log = attempts_path.open('x', encoding='utf-8')
    attempts: list[dict] = []
    consecutive = 0
    stopped = False
    def record(row: dict) -> None:
        attempts.append(row)
        log.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
        log.flush()

    socket.setdefaulttimeout(TIMEOUT)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(f'BaoStock request exceeded {TIMEOUT}s')))
    import baostock as bs
    from baostock import cons
    cons.BAOSTOCK_PER_PAGE_COUNT = 4000
    login_started = time.monotonic()
    signal.alarm(TIMEOUT)
    try:
        login = bs.login()
    finally:
        signal.alarm(0)
    login_ok = getattr(login, 'error_code', None) == '0'
    record({'kind': 'login', 'source': 'BaoStock anonymous', 'started_at': dt.datetime.now().astimezone().isoformat(), 'status': 'ok' if login_ok else 'failed', 'error_code': getattr(login, 'error_code', None), 'error_msg': getattr(login, 'error_msg', None), 'elapsed_seconds': round(time.monotonic() - login_started, 3)})

    sdk_specs = SPEC['requests'][:6]
    http_specs = SPEC['requests'][6:]
    sdk_finished = 0
    if login_ok:
        for ix, spec in enumerate(sdk_specs):
            if consecutive >= 2 or stopped:
                break
            if sdk_finished:
                time.sleep(float(SPEC['delay_seconds']))
            key = f"sdk-{ix+1}-{spec['sdk']}"
            started = time.monotonic()
            row = {'kind': 'sdk', 'operation': ix + 1, 'method': spec['sdk'], 'kwargs': spec['kwargs'], 'started_at': dt.datetime.now().astimezone().isoformat(), 'requested_page_size': cons.BAOSTOCK_PER_PAGE_COUNT}
            try:
                signal.alarm(TIMEOUT)
                result = getattr(bs, spec['sdk'])(**spec['kwargs'])
                data, page_counts, page_sizes = [], {}, {}
                while result.error_code == '0' and result.next():
                    data.append(result.get_row_data())
                    psize = getattr(result, 'per_page_count', None)
                    page_size = int(psize) if psize not in (None, '') else cons.BAOSTOCK_PER_PAGE_COUNT
                    page = str(getattr(result, 'cur_page_num', 'unknown'))
                    page_counts[page] = page_counts.get(page, 0) + 1
                    page_sizes[page] = page_size
                    cons.BAOSTOCK_PER_PAGE_COUNT = page_size
                signal.alarm(0)
                body = {'fields': result.fields, 'rows': data, 'error_code': result.error_code, 'error_msg': result.error_msg}
                raw = json.dumps(body, ensure_ascii=False, indent=2).encode('utf-8')
                meta = write_raw(PROBE / f'{key}.json', raw)
                ok = result.error_code == '0'
                row.update(status='ok' if ok else 'source_failed', fields=result.fields, row_count=len(data), page_count=len(page_counts), rows_by_page=page_counts, returned_page_sizes=page_sizes, error_code=result.error_code, error_msg=result.error_msg, **meta)
                consecutive = 0 if ok else consecutive + 1
                if '429' in str(result.error_msg) or 'too many requests' in str(result.error_msg).lower():
                    row['status'] = 'rate_limited_stop'; stopped = True
            except Exception as exc:
                signal.alarm(0)
                row.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                consecutive += 1
            row['elapsed_seconds'] = round(time.monotonic() - started, 3)
            row['finished_at'] = dt.datetime.now().astimezone().isoformat()
            record(row); sdk_finished += 1
    else:
        for ix, spec in enumerate(sdk_specs):
            record({'kind': 'sdk', 'operation': ix + 1, 'method': spec['sdk'], 'kwargs': spec['kwargs'], 'status': 'not_run_login_failed'})

    if login_ok:
        try:
            logout = bs.logout()
            record({'kind': 'logout', 'source': 'BaoStock anonymous', 'status': 'ok' if logout.error_code == '0' else 'failed', 'error_code': logout.error_code, 'error_msg': logout.error_msg})
        except Exception as exc:
            record({'kind': 'logout', 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})

    time.sleep(float(SPEC['delay_seconds']))
    http_finished = 0
    for ix, spec in enumerate(http_specs):
        if stopped or consecutive >= 2:
            break
        started = time.monotonic()
        label = 'companyfacts' if ix == 0 else 'sec-financial-statement-2014q4'
        row, raw, ok = sec_read(spec['http'], int(spec['max_bytes']), PROBE / f'{label}.raw')
        row.update(operation=7 + ix, label=label)
        if ok and raw is not None:
            try:
                extra = inspect_facts(raw) if ix == 0 else inspect_zip(raw)
                extra_bytes = json.dumps(extra, ensure_ascii=False, indent=2).encode('utf-8')
                row['inspection'] = json.loads(extra_bytes)
                if ix == 1:
                    row['archive_inspection_only_no_extraction'] = True
            except Exception as exc:
                row['inspection_error'] = f'{type(exc).__name__}: {exc}'
                ok = False
        if row.get('status') == 'rate_limited_stop':
            stopped = True
        consecutive = 0 if ok else consecutive + 1
        row['elapsed_seconds'] = round(time.monotonic() - started, 3)
        row['finished_at'] = dt.datetime.now().astimezone().isoformat()
        record(row); http_finished += 1
        if ix == 0:
            time.sleep(float(SPEC['delay_seconds']))
    log.close()
    data_rows = [x for x in attempts if x.get('kind') in {'sdk', 'http'}]
    manifest = {
        'contract_path': str(HERE / 'luna-source-probe-contract.json'),
        'contract_sha256': sha((HERE / 'luna-source-probe-contract.json').read_bytes()),
        'plan_path': str(HERE / 'source-probe-plan.json'),
        'plan_sha256': sha((HERE / 'source-probe-plan.json').read_bytes()),
        'storage_plan_path': str(HERE / 'storage-plan.json'),
        'storage_plan_sha256': sha((HERE / 'storage-plan.json').read_bytes()),
        'script_path': str(HERE / 'probe_financial_sources.py'),
        'script_sha256': sha(Path(__file__).read_bytes()),
        'scope': 'source qualification only; no effects, returns, or signals',
        'status': 'complete' if len(data_rows) == 8 and all(x.get('status') == 'ok' for x in data_rows) else 'partial',
        'data_operations_attempted': sum(1 for x in data_rows if x.get('status') != 'not_run_login_failed'),
        'fixed_data_operations': 8,
        'sdk_operations_attempted': sum(1 for x in attempts if x.get('kind') == 'sdk' and x.get('status') != 'not_run_login_failed'),
        'http_operations_attempted': http_finished,
        'storage_checks': storage_checks,
        'attempts': attempts,
        'raw_files': [{'path': x.get('raw_path'), 'bytes': x.get('raw_bytes'), 'sha256': x.get('raw_sha256')} for x in data_rows if x.get('raw_path')],
        'notes': ['BaoStock page size was set at runtime to 4000 and synchronized to returned per_page_count for pagination.', 'SEC ZIP was preserved as ZIP and only README plus small leading excerpts of sub.txt and num.txt were read in memory.', 'No historical value was replaced or treated as known earlier than its actual disclosure/version fields.'],
    }
    manifest_path = PROBE / 'manifest.json'
    write_json_exclusive(manifest_path, manifest)
    print(json.dumps({'status': manifest['status'], 'attempted': manifest['data_operations_attempted'], 'success': sum(x.get('status') == 'ok' for x in data_rows), 'manifest': str(manifest_path), 'sha256': sha(manifest_path.read_bytes())}, ensure_ascii=False))
    return 0 if manifest['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
