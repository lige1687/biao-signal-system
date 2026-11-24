"""Bounded official SSE/SZSE financing history fetch; raw files are append-only.

Run once with: python3 docs/ops/microstructure-observations-20261108/funding-history/fetch_history.py
The oldest day is fetched and parsed before concurrent bulk collection begins.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'src'))
from lei_signal.market_context import microstructure_funding as mf  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/funding')
CALENDAR_PLAN = REPO / 'docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json'
LEDGER = HERE / 'history-request-ledger.json'
DATES = HERE / 'history-session-dates.json'
MAX_REQUESTS, MAX_BYTES, MAX_SECONDS = 1500, 300 * 1024 * 1024, 12 * 60
MAX_OBJECT = 6 * 1024 * 1024
GUARD = threading.Lock()
STOP = threading.Event()
START = time.monotonic()
REQUESTS: list[dict] = []
DAY_RESULTS: dict[str, dict] = {}
TOTAL_BYTES = 0
REQUEST_COUNT = 0


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def save_ledger() -> None:
    with GUARD:
        snapshot = {'schemaVersion': 1, 'generatedAt': datetime.now(timezone.utc).isoformat(),
                    'requestCount': REQUEST_COUNT, 'newBytes': TOTAL_BYTES,
                    'maxRequests': MAX_REQUESTS, 'maxBytes': MAX_BYTES, 'maxSeconds': MAX_SECONDS,
                    'stopped': STOP.is_set(), 'requests': list(REQUESTS),
                    'days': dict(sorted(DAY_RESULTS.items()))}
    temp = LEDGER.with_suffix('.json.tmp')
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, LEDGER)


def dates() -> list[str]:
    plan = json.loads(CALENDAR_PLAN.read_text())
    ref = plan['baseline']['calendar']
    calendar = Path(ref['path'])
    if digest(calendar) != ref['sha256']:
        raise RuntimeError('official accepted A-share calendar SHA mismatch')
    with calendar.open() as f:
        old = [r['trade_date'] for r in csv.DictReader(f) if r['trade_date'] < mf.SESSION_DATES[0]]
    selected = old[-250:]
    if len(selected) != 250 or selected[-1] != '2026-09-30' or selected[0] != '2025-09-18':
        raise RuntimeError('250-session prior date boundary unexpected')
    all_days = selected + list(mf.SESSION_DATES)
    if len(all_days) != 271 or all_days[-1] != '2026-11-05':
        raise RuntimeError('271-session skeleton unexpected')
    DATES.write_text(json.dumps({'schemaVersion': 1, 'calendarPath': str(calendar), 'calendarSha256': ref['sha256'],
                                 'historyDates': selected, 'currentOwnerDates': list(mf.SESSION_DATES),
                                 'all271Dates': all_days}, ensure_ascii=False, indent=2) + '\n')
    return selected


def url_for_page(day: str, page: int) -> str:
    compact = day.replace('-', '')
    query = urllib.parse.urlencode({'isPagination': 'true', 'tabType': 'mxtype', 'detailsDate': compact,
                                   'pageHelp.pageSize': '5000', 'pageHelp.pageNo': str(page),
                                   'pageHelp.beginPage': str(page), 'pageHelp.cacheSize': '1',
                                   'pageHelp.endPage': str(page)})
    return f'{mf.SSE_DETAIL_URL}?{query}'


def record(day: str, name: str, url: str, headers: dict[str, str]) -> Path | None:
    global TOTAL_BYTES, REQUEST_COUNT
    path = RAW / name
    if day >= '2026-10-08':
        raise RuntimeError('history writer reached current owner date')
    if STOP.is_set() or time.monotonic() - START > MAX_SECONDS:
        STOP.set()
        return None
    if path.exists():
        with GUARD:
            REQUESTS.append({'date': day, 'path': str(path), 'url': url, 'status': 'existing_untouched',
                             'bytes': path.stat().st_size, 'sha256': digest(path)})
        return path
    with GUARD:
        if REQUEST_COUNT >= MAX_REQUESTS or TOTAL_BYTES >= MAX_BYTES:
            STOP.set()
            return None
        REQUEST_COUNT += 1
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=25) as response:
            status = response.status
            payload = response.read(MAX_OBJECT + 1)
        if status != 200 or len(payload) > MAX_OBJECT:
            raise RuntimeError(f'HTTP {status} or oversized object ({len(payload)} bytes)')
        with GUARD:
            if TOTAL_BYTES + len(payload) > MAX_BYTES:
                STOP.set()
                REQUESTS.append({'date': day, 'path': str(path), 'url': url, 'status': 'byte_cap', 'bytes': len(payload)})
                return None
            TOTAL_BYTES += len(payload)
        with path.open('xb') as f:
            f.write(payload)
        with GUARD:
            REQUESTS.append({'date': day, 'path': str(path), 'url': url, 'status': 200,
                             'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        return path
    except Exception as exc:
        status = getattr(exc, 'code', 'request_failed')
        if status in (401, 403, 429):
            STOP.set()
        with GUARD:
            REQUESTS.append({'date': day, 'path': str(path), 'url': url,
                             'status': status, 'error': f'{type(exc).__name__}: {exc}'})
        return None


def one_day(day: str) -> dict:
    if STOP.is_set():
        return {'complete': False, 'reason': 'stopped_before_day'}
    compact = day.replace('-', '')
    page_paths = []
    first = record(day, f'sse-margin-{compact}-page1.json', url_for_page(day, 1), mf.SSE_HEADERS)
    if first is None:
        return {'complete': False, 'reason': 'sse_page1_unavailable'}
    try:
        body = mf._parse_sse_json(first)
        help_data = body['pageHelp']
        pages = int(help_data['pageCount'])
        if body.get('detailsDate') != compact or int(help_data['pageNo']) != 1 or not 1 <= pages <= 10:
            raise ValueError('SSE page1 date/page metadata invalid')
        page_paths.append(first)
    except Exception as exc:
        return {'complete': False, 'reason': f'sse_page1_parse: {exc}'}
    for page in range(2, pages+1):
        path = record(day, f'sse-margin-{compact}-page{page}.json', url_for_page(day, page), mf.SSE_HEADERS)
        if path is None:
            return {'complete': False, 'reason': f'sse_page{page}_unavailable', 'ssePageCount': pages}
        page_paths.append(path)
    # The three remaining object URLs are constructed by the current owner code,
    # which already fixes the exact official date parameters and report IDs.
    others = mf._urls_for_day(day)[2:]
    paths = []
    for name, url, headers in others:
        path = record(day, name, url, headers)
        if path is None:
            return {'complete': False, 'reason': f'{name}_unavailable', 'ssePageCount': pages}
        paths.append(path)
    try:
        sh_margin = mf._sse_margin_amount(page_paths, day)
        sh_turnover = mf._sse_stock_turnover(paths[0], day)
        sz_margin = mf._szse_margin_amount(paths[1])
        sz_turnover = mf._szse_stock_turnover(paths[2])
        return {'complete': True, 'ssePageCount': pages, 'sseMarginRows': sh_margin[2],
                'sseStockCount': sh_turnover[1], 'szseMarginRows': sz_margin[2],
                'szseStockCount': sz_turnover[1]}
    except Exception as exc:
        return {'complete': False, 'reason': f'official_parse: {type(exc).__name__}: {exc}', 'ssePageCount': pages}


def main() -> None:
    global REQUEST_COUNT, TOTAL_BYTES
    RAW.mkdir(parents=True, exist_ok=True)
    if LEDGER.is_file():
        previous = json.loads(LEDGER.read_text())
        REQUEST_COUNT = int(previous['requestCount'])
        TOTAL_BYTES = int(previous['newBytes'])
        REQUESTS.extend(previous['requests'])
        DAY_RESULTS.update(previous['days'])
    selected = dates()
    specific = next((arg.split('=', 1)[1] for arg in sys.argv[1:] if arg.startswith('--date=')), None)
    if specific is not None:
        if specific not in selected:
            raise RuntimeError('requested retry date outside historical scope')
        result = one_day(specific)
        with GUARD:
            DAY_RESULTS[specific] = result
        save_ledger()
        print('single date', specific, result, flush=True)
        return
    oldest = selected[0]
    probe = one_day(oldest)
    with GUARD:
        DAY_RESULTS[oldest] = probe
    save_ledger()
    print('oldest probe', oldest, probe, flush=True)
    if not probe['complete'] or '--probe-only' in sys.argv:
        return
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = {executor.submit(one_day, day): day for day in selected[1:]}
        for completed in as_completed(tasks):
            day = tasks[completed]
            try:
                result = completed.result()
            except Exception as exc:
                result = {'complete': False, 'reason': f'worker: {type(exc).__name__}: {exc}'}
            with GUARD:
                DAY_RESULTS[day] = result
            save_ledger()
            if len(DAY_RESULTS) % 25 == 0:
                print('completed', len(DAY_RESULTS), 'requests', REQUEST_COUNT, 'bytes', TOTAL_BYTES, flush=True)
    save_ledger()
    print('final', len(DAY_RESULTS), sum(v['complete'] for v in DAY_RESULTS.values()),
          REQUEST_COUNT, TOTAL_BYTES, 'stopped', STOP.is_set(), flush=True)


if __name__ == '__main__':
    main()
