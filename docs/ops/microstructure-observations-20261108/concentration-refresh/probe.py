"""Bounded, source-preserving probe for daily equity amount availability."""
import datetime as dt
import hashlib
import json
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-refresh-20261108')
LEDGER = HERE / 'probe-ledger.json'
RESULT = HERE / 'probe-result.json'
MAX_REQUESTS = 28
MAX_BYTES = 28 * 1024 * 1024
entries = []
started = time.monotonic()


def save():
    LEDGER.write_text(json.dumps({'startedUtc': dt.datetime.now(dt.timezone.utc).isoformat(),
                                  'requests': len(entries), 'responseBytes': sum(x.get('bytes', 0) for x in entries),
                                  'entries': entries}, ensure_ascii=False, indent=2) + '\n')


def record(name, provider, url, status, body, error=None):
    if len(entries) >= MAX_REQUESTS or sum(x.get('bytes', 0) for x in entries) + len(body) > MAX_BYTES:
        raise RuntimeError('probe budget reached')
    path = RAW / (name + '.json')
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(body)
    row = {'name': name, 'provider': provider, 'urlOrParameters': url, 'status': status,
           'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'path': str(path),
           'error': error, 'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    entries.append(row)
    save()
    return row


def eastmoney(code, beg, end):
    market = '1' if code.startswith('sh') else '0'
    symbol = code[2:]
    params = {'secid': market + '.' + symbol, 'fields1': 'f1,f2,f3,f4,f5,f6',
              'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
              'klt': '101', 'fqt': '0', 'beg': beg.replace('-', ''), 'end': end.replace('-', '')}
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get?' + urllib.parse.urlencode(params)
    name = 'eastmoney-' + code + '-' + beg + '-' + end
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'})
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(MAX_BYTES + 1)
            status = response.status
        record(name, 'Eastmoney stock kline', url, status, raw)
    except Exception as exc:
        record(name, 'Eastmoney stock kline', url, 'error', json.dumps({'error': repr(exc)}).encode(), repr(exc))


def bao():
    try:
        import baostock as bs
        socket.setdefaulttimeout(12)
        login = bs.login()
        record('baostock-login', 'BaoStock', 'bs.login()', login.error_code,
               json.dumps({'errorCode': login.error_code, 'errorMsg': login.error_msg}).encode())
        if login.error_code != '0':
            return
        for code, beg, end in [('sz.000016', '2026-10-19', '2026-11-06'),
                               ('sh.601326', '2026-10-19', '2026-11-06'),
                               ('sh.600696', '2023-01-01', '2023-01-31')]:
            fields = 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,tradestatus,pctChg,isST'
            args = {'code': code, 'fields': fields, 'start_date': beg, 'end_date': end, 'frequency': 'd', 'adjustflag': '3'}
            name = 'baostock-' + code.replace('.', '') + '-' + beg + '-' + end
            try:
                rs = bs.query_history_k_data_plus(code, fields, start_date=beg, end_date=end, frequency='d', adjustflag='3')
                data = []
                while rs.error_code == '0' and rs.next():
                    data.append(rs.get_row_data())
                raw = json.dumps({'parameters': args, 'errorCode': rs.error_code, 'errorMsg': rs.error_msg,
                                  'fields': rs.fields, 'rows': data}, ensure_ascii=False).encode()
                record(name, 'BaoStock query_history_k_data_plus', args, rs.error_code, raw)
            except Exception as exc:
                record(name, 'BaoStock query_history_k_data_plus', args, 'error', json.dumps({'error': repr(exc)}).encode(), repr(exc))
        try:
            logout = bs.logout()
            record('baostock-logout', 'BaoStock', 'bs.logout()', logout.error_code,
                   json.dumps({'errorCode': logout.error_code, 'errorMsg': logout.error_msg}).encode())
        except Exception as exc:
            record('baostock-logout', 'BaoStock', 'bs.logout()', 'error', json.dumps({'error': repr(exc)}).encode(), repr(exc))
    except Exception as exc:
        record('baostock-import-or-session', 'BaoStock', 'session', 'error', json.dumps({'error': repr(exc)}).encode(), repr(exc))


def main():
    if LEDGER.exists() or RESULT.exists() or RAW.exists():
        raise FileExistsError('probe output already exists')
    RAW.mkdir(parents=True)
    bao()
    for code, beg, end in [('sz000016', '2026-10-19', '2026-11-06'),
                           ('sh601326', '2026-10-19', '2026-11-06'),
                           ('sh600696', '2023-01-01', '2023-01-31'),
                           ('sh600519', '2026-10-19', '2026-11-06'),
                           ('sh601059', '2026-10-16', '2026-10-23'),
                           ('sh601198', '2026-10-16', '2026-10-23')]:
        if len(entries) >= MAX_REQUESTS or time.monotonic() - started > 270:
            break
        eastmoney(code, beg, end)
    RESULT.write_text(json.dumps({'requests': len(entries), 'responseBytes': sum(x['bytes'] for x in entries),
                                  'elapsedSeconds': round(time.monotonic() - started, 3),
                                  'samples': entries}, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
