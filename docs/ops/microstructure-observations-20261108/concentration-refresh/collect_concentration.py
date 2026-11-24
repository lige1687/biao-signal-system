"""Bounded raw BaoStock acquisition for the concentration observation."""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-refresh-20261108')
RECENT = RAW / 'recent'
HISTORY = RAW / 'history'
REQUEST_LOG = RAW / 'collection-requests.jsonl'
LEDGER = HERE / 'collection-ledger.json'
SUMMARY = HERE / 'collection-summary.json'
PROBE = HERE / 'probe-ledger.json'
BASIC = RAW / 'baostock-stock-basic.json'
ALL = RAW / 'baostock-all-stock-20261106.json'
DEADLINE = dt.datetime.fromisoformat('2026-11-08T13:00:46.537129+00:00')
FIELDS = 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,tradestatus,pctChg,isST'
MAX_NEW_OPERATIONS = 5470  # tighter controller instruction than contract
MAX_OVERALL_BYTES = 50 * 1024 * 1024
MAX_OVERALL_OPERATIONS = 5600
ROOT_OPERATIONS = 4
ROOT_BYTES_RESERVED = 2 * 1024 * 1024
WORKERS = 4
_login = None


def now():
    return dt.datetime.now(dt.timezone.utc)


def _worker_init():
    global _login
    import baostock as bs
    import socket
    socket.setdefaulttimeout(15)
    try:
        result = bs.login()
        _login = {'pid': os.getpid(), 'errorCode': result.error_code, 'errorMsg': result.error_msg}
    except Exception as exc:
        _login = {'pid': os.getpid(), 'errorCode': 'exception', 'errorMsg': repr(exc)}


def _fetch(task):
    kind, code, start, end = task
    login = _login
    if login is None or login['errorCode'] != '0':
        return login, {'kind': kind, 'code': code, 'start': start, 'end': end,
                       'status': 'login_failed', 'error': login, 'queryAttempted': False}, b''
    import baostock as bs
    args = {'code': code, 'fields': FIELDS, 'start_date': start, 'end_date': end,
            'frequency': 'd', 'adjustflag': '3'}
    try:
        rs = bs.query_history_k_data_plus(code, FIELDS, start_date=start, end_date=end,
                                           frequency='d', adjustflag='3')
        rows = []
        while rs.error_code == '0' and rs.next():
            rows.append(rs.get_row_data())
        body = json.dumps({'source': 'BaoStock.query_history_k_data_plus', 'parameters': args,
                           'errorCode': rs.error_code, 'errorMsg': rs.error_msg,
                           'fields': rs.fields, 'data': rows}, ensure_ascii=False,
                          separators=(',', ':')).encode()
        status = rs.error_code
        first, last = (rows[0][0], rows[-1][0]) if rows else (None, None)
        error = None if status == '0' else rs.error_msg
    except Exception as exc:
        body = json.dumps({'source': 'BaoStock.query_history_k_data_plus', 'parameters': args,
                           'error': repr(exc)}, separators=(',', ':')).encode()
        status = 'exception'
        rows = []
        first = last = None
        error = repr(exc)
    record = {'kind': kind, 'code': code, 'start': start, 'end': end,
              'status': status, 'rows': len(rows), 'first': first, 'last': last,
              'error': error, 'queryAttempted': True}
    return login, record, body


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load_plan():
    basic = json.loads(BASIC.read_text())
    all_day = json.loads(ALL.read_text())
    rows = [r for r in basic['rows'] if r[4] == '1' and r[0].startswith(('sh.60', 'sh.68', 'sz.00', 'sz.30'))
            and r[2] and r[2] <= '2026-11-06' and (not r[3] or r[3] > '2026-10-08')]
    codes = sorted({r[0] for r in rows})
    current = {r[0] for r in rows if r[2] <= '2026-11-06' and (not r[3] or '2026-11-06' < r[3])}
    listed = {r[0] for r in all_day['rows'] if r[0].startswith(('sh.60', 'sh.68', 'sz.00', 'sz.30'))}
    if current != listed:
        raise RuntimeError(f'catalog mismatch: basic-only={sorted(current-listed)[:10]}, all-only={sorted(listed-current)[:10]}')
    return rows, codes, len(current)


def existing():
    if not REQUEST_LOG.exists():
        return {}, 0, 0, set()
    records = {}
    bytes_used = operations = 0
    pids = set()
    with REQUEST_LOG.open() as f:
        for line in f:
            x = json.loads(line)
            if x['event'] == 'login':
                if x['pid'] not in pids:
                    pids.add(x['pid'])
                    operations += 1
            elif x['event'] == 'logout':
                operations += 1
            elif x['event'] == 'query':
                records[(x['kind'], x['code'])] = x
                if x['queryAttempted']:
                    operations += 1
                    bytes_used += x['bytes']
    return records, bytes_used, operations, pids


def append(event):
    with REQUEST_LOG.open('a') as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
        f.flush()
        os.fsync(f.fileno())


def record_output(login, rec, body, logged_pids):
    if login is not None and login['pid'] not in logged_pids:
        append({'event': 'login', 'utc': now().isoformat(), **login})
        logged_pids.add(login['pid'])
    if rec['queryAttempted']:
        folder = RECENT if rec['kind'] == 'recent' else HISTORY
        filename = rec['code'].replace('.', '') + '-' + rec['start'] + '-' + rec['end'] + '.json'
        path = folder / filename
        if path.exists():
            raise FileExistsError(path)
        path.write_bytes(body)
        rec['path'] = str(path)
        rec['sha256'] = _sha(body)
        rec['bytes'] = len(body)
    else:
        rec['path'] = None
        rec['sha256'] = None
        rec['bytes'] = 0
    rec['event'] = 'query'
    rec['utc'] = now().isoformat()
    append(rec)


def summarize(plan_count, current_count, reason):
    records, response_bytes, operations, pids = existing()
    probe = json.loads(PROBE.read_text())
    recent = [x for (kind, _), x in records.items() if kind == 'recent']
    history = [x for (kind, _), x in records.items() if kind == 'history']
    status = {'state': reason, 'utc': now().isoformat(), 'deadlineUtc': DEADLINE.isoformat(),
              'plannedRecentStocks': plan_count, 'currentAsOfNov6': current_count,
              'recentAttempted': len(recent), 'recentSuccess': sum(x['status'] == '0' for x in recent),
              'recentEmpty': sum(x['status'] == '0' and x['rows'] == 0 for x in recent),
              'recentErrors': [x['code'] for x in recent if x['status'] != '0'],
              'historyAttempted': len(history), 'historySuccess': sum(x['status'] == '0' for x in history),
              'collectionOperations': operations, 'collectionResponseBytes': response_bytes,
              'totalKnownOperations': operations + probe['requests'] + ROOT_OPERATIONS,
              'totalKnownResponseBytesExcludingRoot': response_bytes + probe['responseBytes'],
              'rootBytesReserved': ROOT_BYTES_RESERVED,
              'rawRequestLog': str(REQUEST_LOG), 'rawRequestLogSha256': _sha(REQUEST_LOG.read_bytes()) if REQUEST_LOG.exists() else None,
              'rawRoot': str(RAW)}
    LEDGER.write_text(json.dumps({'schemaVersion': 1, 'requestLog': status['rawRequestLog'],
                                  'requestLogSha256': status['rawRequestLogSha256'],
                                  'collectionOperations': operations,
                                  'collectionResponseBytes': response_bytes,
                                  'probeOperations': probe['requests'], 'probeBytes': probe['responseBytes'],
                                  'rootOperationsKnown': ROOT_OPERATIONS,
                                  'rawRoot': str(RAW)}, ensure_ascii=False, separators=(',', ':')) + '\n')
    SUMMARY.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
    return status


def main():
    if now() >= DEADLINE:
        raise RuntimeError('deadline passed')
    rows, codes, current_count = load_plan()
    RECENT.mkdir(exist_ok=True)
    HISTORY.mkdir(exist_ok=True)
    records, old_bytes, old_ops, logged_pids = existing()
    mode = 'history' if '--history' in sys.argv else 'recent'
    if mode == 'recent':
        tasks = [('recent', code, '2026-10-08', '2026-11-06') for code in codes if ('recent', code) not in records]
    else:
        gap_path = HERE / 'monthly-gap-detail.json'
        gap = json.loads(gap_path.read_text())
        if (gap.get('qualification') != 'read-only full raw SHA/schema scan; original frozen result unchanged'
                or gap.get('affectedCodes') != 79 or gap.get('minimumSingleRangeRequests') != 79
                or len(gap.get('requests', [])) != 79):
            raise RuntimeError('monthly gap detail not qualified')
        tasks = [('history', x['code'], x['minimumSingleRange']['start'], x['minimumSingleRange']['end'])
                 for x in gap['requests'] if ('history', x['code']) not in records]
    stop = 'incomplete'
    same_errors = 0
    with cf.ProcessPoolExecutor(max_workers=WORKERS, initializer=_worker_init) as executor:
        for offset in range(0, len(tasks), 100):
            if now() >= DEADLINE - dt.timedelta(seconds=20):
                stop = 'deadline'; break
            records, used_bytes, used_ops, logged_pids = existing()
            if used_ops + 104 > MAX_NEW_OPERATIONS or used_bytes + 1024 * 1024 + json.loads(PROBE.read_text())['responseBytes'] + ROOT_BYTES_RESERVED > MAX_OVERALL_BYTES:
                stop = 'budget'; break
            batch = tasks[offset:offset+100]
            futures = {executor.submit(_fetch, task): task for task in batch}
            for future in cf.as_completed(futures):
                login, rec, body = future.result()
                record_output(login, rec, body, logged_pids)
                if rec['status'] not in ('0',):
                    same_errors += 1
                else:
                    same_errors = 0
            if same_errors >= 2:
                stop = 'two_repeated_errors'; break
            summary = summarize(len(codes), current_count, 'running')
            print(json.dumps({'mode': mode, 'recentAttempted': summary['recentAttempted'],
                              'recentSuccess': summary['recentSuccess'],
                              'historyAttempted': summary['historyAttempted'],
                              'historySuccess': summary['historySuccess'],
                              'collectionBytes': summary['collectionResponseBytes'],
                              'utc': summary['utc']}), flush=True)
        else:
            stop = mode + '_complete'
    summarize(len(codes), current_count, stop)


if __name__ == '__main__':
    main()
