"""Bounded, source-only valuation probes; never compute future factor effects."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time

MAIN = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
sys.path.insert(0, str(MAIN / 'src'))
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contract', required=True)
    ap.add_argument('--check-only', action='store_true')
    args = ap.parse_args()
    cpath = Path(args.contract)
    contract = json.loads(cpath.read_text())
    assert contract['schema'] == 'value-source-execution/1'
    assert contract['market_effects_allowed'] is False
    assert contract['runner']['sha256'] == digest(__file__)
    assert Path(contract['runner']['path']).resolve() == Path(__file__).resolve()
    pb = contract['plan']
    assert digest(pb['path']) == pb['sha256']
    spec = json.loads(Path(pb['path']).read_text())
    assert spec['schema'] == 'value-source-probe/1'
    assert spec['market_effects_allowed'] is False and spec['retries'] == 0
    assert len(spec['requests']) == spec['max_data_operations'] == 4
    sb = spec['storage_plan']
    assert digest(sb['path']) == sb['sha256']
    plan = json.loads(Path(sb['path']).read_text())
    recheck_saved_plan(MAIN, plan, plan['task_id'], plan['estimated_bytes'], plan['internal_metadata_bytes'])
    assert _still_mounted(plan)
    out = Path(plan['output'])
    run = Path(plan['run_directory'])
    assert not run.exists(), 'Existing attempt cannot be silently restarted'
    assert out == run / 'result'
    assert run.parent.parent.stat().st_dev == plan['external_device']
    if args.check_only:
        print(json.dumps({'checked': True, 'network': False, 'output_created': False, 'operations': 4}))
        return 0
    run.parent.mkdir(exist_ok=True)
    assert _still_mounted(plan) and run.parent.stat().st_dev == plan['external_device']
    run.mkdir(exist_ok=False)
    out.mkdir(exist_ok=False)
    write_new(run / 'storage-plan.json', plan)
    write_new(run / 'contract.json', contract)
    log = (out / 'attempts.jsonl').open('x', encoding='utf-8')
    events = []
    def record(event):
        event['at'] = dt.datetime.now().astimezone().isoformat()
        events.append(event)
        log.write(json.dumps(event, ensure_ascii=False) + '\n')
        log.flush()
        os.fsync(log.fileno())
    timeout = int(spec['timeout_seconds'])
    socket.setdefaulttimeout(timeout)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('bounded BaoStock operation timeout')))
    import baostock as bs
    from baostock import cons
    cons.BAOSTOCK_PER_PAGE_COUNT = 4000
    login_ok = False
    used = failures = completed = 0
    stop_reason = None
    try:
        signal.alarm(timeout)
        login = bs.login()
        signal.alarm(0)
        login_ok = login.error_code == '0'
        record({'kind': 'login', 'error_code': login.error_code, 'error_msg': login.error_msg})
        if not login_ok:
            raise RuntimeError('anonymous login failed')
        for ix, request in enumerate(spec['requests'], 1):
            assert _still_mounted(plan) and out.stat().st_dev == plan['external_device']
            if failures >= 2:
                stop_reason = 'two consecutive source failures'
                break
            if used:
                time.sleep(spec['delay_seconds'])
            used += 1
            record({'kind': 'request_started', 'operation': ix, 'request': request})
            try:
                signal.alarm(timeout)
                response = getattr(bs, request['method'])(**request['kwargs'])
                rows = []
                while response.error_code == '0' and response.next():
                    rows.append(response.get_row_data())
                    if len(rows) > 4000:
                        raise ValueError('source probe row limit exceeded')
                signal.alarm(0)
                body = {'fields': response.fields, 'rows': rows, 'error_code': response.error_code, 'error_msg': response.error_msg}
                path = out / f'{ix:02d}-{request["method"]}-{request["kwargs"]["code"]}.json'
                assert _still_mounted(plan)
                write_new(path, body)
                ok = response.error_code == '0'
                record({'kind': 'request_finished', 'operation': ix, 'status': 'ok' if ok else 'failed', 'rows': len(rows), 'path': str(path), 'sha256': digest(path), 'error_code': response.error_code, 'error_msg': response.error_msg})
                failures = 0 if ok else failures + 1
                if '429' in str(response.error_msg) or 'too many' in str(response.error_msg).lower():
                    stop_reason = 'rate limit'
                    break
            except Exception as exc:
                signal.alarm(0)
                record({'kind': 'request_failed', 'operation': ix, 'error': f'{type(exc).__name__}: {exc}'})
                failures += 1
    except Exception as exc:
        signal.alarm(0)
        stop_reason = f'{type(exc).__name__}: {exc}'
        if _still_mounted(plan):
            record({'kind': 'execution_failed', 'error': stop_reason})
    finally:
        signal.alarm(0)
        if login_ok:
            try:
                signal.alarm(timeout)
                bs.logout()
            except Exception:
                pass
            finally:
                signal.alarm(0)
        if _still_mounted(plan):
            completed = sum(e.get('kind') == 'request_finished' and e.get('status') == 'ok' for e in events)
            manifest = {'schema': 'value-source-probe-result/1', 'contract': str(cpath), 'contract_sha256': digest(cpath), 'runner_sha256': digest(__file__), 'data_operations_used': used, 'successful_operations': completed, 'maximum_operations': 4, 'retries': 0, 'status': 'complete' if completed == 4 else 'partial', 'stop_reason': stop_reason, 'market_effects_run': False, 'source_time_qualification': 'pending independent original-document comparison', 'events': events}
            write_new(out / 'manifest.json', manifest)
            print(json.dumps({'status': manifest['status'], 'manifest': str(out / 'manifest.json'), 'sha256': digest(out / 'manifest.json'), 'used': used, 'success': completed}, ensure_ascii=False))
        log.close()
    return 0 if completed == 4 else 1


if __name__ == '__main__':
    raise SystemExit(main())
