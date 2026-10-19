"""Four predeclared anonymous requests; never replace frozen sources."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import signal
import socket
import sys
import time
ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted

def stamp():
    return dt.datetime.now().astimezone().isoformat()

def main():
    saved = json.loads((HERE / 'storage-plan.json').read_text())
    plan = recheck_saved_plan(ROOT, saved, saved['task_id'], saved['estimated_bytes'], saved['internal_metadata_bytes'])
    if not _still_mounted(plan):
        raise RuntimeError('external disk mismatch')
    parent, out = Path(plan['run_directory']), Path(plan['output'])
    parent.mkdir(exist_ok=False)
    out.mkdir(exist_ok=False)
    (parent / 'storage-plan.json').write_text(json.dumps(plan, indent=2))
    ledger = out / 'attempts.jsonl'
    attempts = []
    def record(row):
        attempts.append(row)
        with ledger.open('a') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
    def timeout(*_):
        raise TimeoutError('request exceeded 40 seconds')
    signal.signal(signal.SIGALRM, timeout)
    socket.setdefaulttimeout(40)
    import baostock as bs
    used, failures, logged_in = 0, 0, False
    try:
        start = time.monotonic()
        signal.alarm(40)
        login = bs.login()
        signal.alarm(0)
        logged_in = login.error_code == '0'
        record({'kind':'login','at':stamp(),'error_code':login.error_code,'error_msg':login.error_msg,'seconds':time.monotonic()-start})
        if not logged_in:
            used += 1
        else:
            fields = 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST'
            common = {'code':'sz.001914','start_date':'2013-01-01','end_date':'2026-01-15'}
            requests = [
                ('001914-nominal', bs.query_history_k_data_plus, {**common,'fields':fields,'frequency':'d','adjustflag':'3'}),
                ('001914-adjusted-repeat', bs.query_history_k_data_plus, {**common,'fields':fields,'frequency':'d','adjustflag':'2'}),
                ('001914-adjust-factors', bs.query_adjust_factor, common),
                ('600519-share-fields', bs.query_profit_data, {'code':'sh.600519','year':2014,'quarter':4}),
            ]
            for key, method, kwargs in requests:
                if failures >= 2:
                    break
                if not _still_mounted(plan):
                    raise RuntimeError('external disk disconnected; no internal fallback')
                used += 1
                entry = {'kind':'data_request','key':key,'at':stamp(),'method':method.__name__,'kwargs':kwargs}
                start = time.monotonic()
                try:
                    signal.alarm(40)
                    result = method(**kwargs)
                    data=[]
                    while result.error_code == '0' and result.next():
                        data.append(result.get_row_data())
                    signal.alarm(0)
                    body={'fields':result.fields,'data':data,'error_code':result.error_code,'error_msg':result.error_msg}
                    raw=json.dumps(body,ensure_ascii=False,indent=2).encode()
                    target=out / (key + '.json')
                    with target.open('xb') as stream:
                        stream.write(raw)
                    ok=result.error_code == '0' and bool(data)
                    entry.update(status='ok' if ok else 'source_failed_or_empty',rows=len(data),fields=result.fields,error_code=result.error_code,error_msg=result.error_msg,path=str(target),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
                    failures=0 if ok else failures+1
                except Exception as exc:
                    signal.alarm(0)
                    entry.update(status='failed',error=f'{type(exc).__name__}: {exc}')
                    failures+=1
                entry['seconds']=time.monotonic()-start
                record(entry)
                time.sleep(1)
    except Exception as exc:
        signal.alarm(0)
        if not logged_in and used == 0:
            used=1
        record({'kind':'fatal','at':stamp(),'error':f'{type(exc).__name__}: {exc}'})
    finally:
        if logged_in:
            try:
                signal.alarm(10)
                result=bs.logout()
                record({'kind':'logout','at':stamp(),'error_code':result.error_code})
            except Exception as exc:
                record({'kind':'logout','at':stamp(),'error':str(exc)})
            finally:
                signal.alarm(0)
    summary={'at':stamp(),'source_requests_before':2,'source_attempts_this_run':used,'total_source_attempts':2+used,'max_source_attempts':6,'no_new_returns':True,'requests':attempts,'output':str(out)}
    text=json.dumps(summary,ensure_ascii=False,indent=2)
    with (out/'probe-summary.json').open('x') as stream:
        stream.write(text)
    with (HERE/'probe-receipt.json').open('x') as stream:
        stream.write(text)
    print(json.dumps({'requests':[(r.get('key'),r.get('status'),r.get('rows')) for r in attempts if r['kind']=='data_request'],'used':2+used,'output':str(out)},ensure_ascii=False))
    return 0 if used == 4 and all(r.get('status')=='ok' for r in attempts if r['kind']=='data_request') else 2
if __name__=='__main__':
    raise SystemExit(main())
