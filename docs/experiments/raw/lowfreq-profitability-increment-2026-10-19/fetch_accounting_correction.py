"""Fetch the single already-located CNINFO accounting-correction PDF."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time
from datetime import datetime, timezone

import requests

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
CONTRACT = HERE / 'luna-accounting-correction-contract.json'
PLAN_PATH = HERE / 'accounting-correction-plan.json'
STORAGE_PATH = HERE / 'storage-plan.json'
PARENT_MANIFEST = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/lowfreq-profitability-increment-20261019/lowfreq-profitability-increment-20261019-20261019T102257-90b550e27121/result/original-filings-probe-v1/manifest.json')
EXPECTED_CONTRACT_SHA = '607c49ddac60074b8a3dbf6d0e6bfeeb06ab7e02e587f9caf951a329c3292124'
EXPECTED_PLAN_SHA = '0b65a027121b9f039573359b1d04afb0c5cbcec45033f5b1256555aa0ba4ad61'
EXPECTED_STORAGE_SHA = '2bb0d1f1a89e7b0e70e0f78a68e22e0a9802639706c869b1519da0a07796437c'
MAX_BYTES = 30_000_000
TIMEOUT = 40


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> bytes:
    data = json.dumps(value, ensure_ascii=False, indent=2, default=str).encode('utf-8')
    with path.open('xb') as f:
        f.write(data)
    return data


def main() -> int:
    for path, expected in ((CONTRACT, EXPECTED_CONTRACT_SHA), (PLAN_PATH, EXPECTED_PLAN_SHA), (STORAGE_PATH, EXPECTED_STORAGE_SHA)):
        if sha(path.read_bytes()) != expected:
            raise RuntimeError(f'frozen input hash mismatch: {path.name}')
    contract = json.loads(CONTRACT.read_text())
    plan = json.loads(PLAN_PATH.read_text())
    storage = json.loads(STORAGE_PATH.read_text())
    parent = json.loads(PARENT_MANIFEST.read_text())
    source = plan['source_announcement']
    matches = [item for item in parent['all_exact_code_announcements']
               if str(item.get('announcementId')) == str(source['announcementId'])
               and item.get('secCode') == source['secCode']
               and item.get('adjunctUrl') == source['adjunctUrl']]
    if len(matches) != 1 or plan['url'] != 'https://static.cninfo.com.cn/' + source['adjunctUrl']:
        raise RuntimeError('source announcement locator does not match exactly one saved parent record')
    if (plan['new_operations_max'] != 1 or plan['used_before'] != 14 or plan['pdf_before'] != 7
            or plan['total_operations_after'] != 15 or plan['total_pdf_after'] != 8
            or plan['retries'] != 0 or plan['timeout_seconds'] != TIMEOUT
            or plan['max_bytes'] != MAX_BYTES):
        raise RuntimeError('one-request scope mismatch')
    mount = Path(storage['external_mount'])
    out = Path(plan['out'])
    if out.parent != Path(storage['output']) or out.exists() or not os.path.ismount(mount):
        raise RuntimeError('bound fresh output path is unavailable')
    if mount.stat().st_dev != storage['external_device'] or out.parent.stat().st_dev != storage['external_device']:
        raise RuntimeError('external device mismatch')
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)], timeout=10))
    if info.get('VolumeUUID') != storage['external_uuid'] or info.get('Writable') is not True:
        raise RuntimeError('external volume UUID or writable check failed')
    if shutil.disk_usage(mount).free < storage['external_reserve_bytes'] + storage['estimated_bytes']:
        raise RuntimeError('external capacity below saved estimate and reserve')
    out.mkdir(parents=False, exist_ok=False)
    run_log = (out / 'run.log').open('x', encoding='utf-8')
    run_log.write(json.dumps({'event': 'request_start', 'operation_number': 15,
                              'method': 'GET', 'url': plan['url'],
                              'started_utc': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False) + '\n')
    run_log.flush()

    started = time.monotonic()
    attempt = {'operation_number': 15, 'new_operations_in_this_run': 1,
               'method': 'GET', 'url': plan['url'], 'started_utc': datetime.now(timezone.utc).isoformat(),
               'status': None, 'bytes': 0, 'sha256': None, 'body_path': None,
               'pdf_magic_valid': False, 'error': None}
    body = bytearray()
    try:
        with requests.request('GET', plan['url'], stream=True, allow_redirects=False,
                              timeout=TIMEOUT,
                              headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.cninfo.com.cn/'}) as response:
            attempt['status'] = response.status_code
            attempt['final_url'] = response.url
            attempt['headers'] = {key.lower(): response.headers.get(key) for key in ('Content-Type', 'Content-Length', 'Date', 'Last-Modified', 'ETag')}
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                if len(body) + len(chunk) > MAX_BYTES:
                    body.extend(chunk[:MAX_BYTES - len(body)])
                    attempt['error'] = f'body_exceeded_{MAX_BYTES}_byte_cap; capped prefix preserved'
                    break
                body.extend(chunk)
    except requests.RequestException as exc:
        attempt['error'] = f'{type(exc).__name__}: {exc}'
    raw = bytes(body)
    raw_path = out / 'accounting-correction-response.body'
    with raw_path.open('xb') as f:
        f.write(raw)
    attempt.update(bytes=len(raw), sha256=sha(raw), body_path=str(raw_path),
                   pdf_magic_valid=raw.startswith(b'%PDF-'), elapsed_seconds=round(time.monotonic() - started, 3),
                   completed_utc=datetime.now(timezone.utc).isoformat())
    if attempt['status'] is not None and not (200 <= attempt['status'] < 300):
        attempt['error'] = attempt['error'] or f'HTTP status {attempt["status"]}'
    run_log.write(json.dumps({'event': 'request_complete', 'status': attempt['status'],
                              'bytes': attempt['bytes'], 'sha256': attempt['sha256'],
                              'pdf_magic_valid': attempt['pdf_magic_valid'],
                              'error': attempt['error'], 'completed_utc': attempt['completed_utc']}, ensure_ascii=False) + '\n')
    run_log.close()
    manifest = {
        'schema': 'accounting-correction-original-probe/1',
        'contract_sha256': EXPECTED_CONTRACT_SHA,
        'plan_sha256': EXPECTED_PLAN_SHA,
        'storage_plan_sha256': EXPECTED_STORAGE_SHA,
        'script_sha256': sha(Path(__file__).read_bytes()),
        'parent_manifest': str(PARENT_MANIFEST),
        'parent_manifest_sha256': sha(PARENT_MANIFEST.read_bytes()),
        'output_directory': str(out),
        'shared_budget_before': {'operations': 14, 'pdfs': 7, 'max_operations': 18, 'max_pdfs': 8},
        'shared_budget_after': {'operations': 15, 'pdfs': 8, 'unissued_operation_budget': 3},
        'source_announcement': source,
        'attempts': [attempt],
        'status': 'pdf_saved' if attempt['status'] and 200 <= attempt['status'] < 300 and attempt['pdf_magic_valid'] else 'request_failed_or_non_pdf',
        'scope': 'single original PDF retrieval only; no announcement queries and no document-body interpretation',
    }
    write_json(out / 'manifest.json', manifest)
    print(json.dumps({'status': manifest['status'], 'http_status': attempt['status'],
                      'bytes': attempt['bytes'], 'sha256': attempt['sha256'],
                      'pdf_magic_valid': attempt['pdf_magic_valid'], 'manifest': str(out / 'manifest.json')}, ensure_ascii=False))
    return 0 if manifest['status'] == 'pdf_saved' else 2


if __name__ == '__main__':
    raise SystemExit(main())
