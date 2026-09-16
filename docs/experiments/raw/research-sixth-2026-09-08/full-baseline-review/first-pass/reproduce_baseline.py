#!/usr/bin/env python3
"""Independent audit of fixed historical rows, with no production imports/network."""
from pathlib import Path
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import socket
import sys

import pandas as pd

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
RAW = OUT / 'inputs/docs/experiments/raw'
RUNS = {'A': '20260831-231254-88cb12.json', 'B': '20260831-231715-1bb6f2.json', 'C': '20260831-231944-b87a6b.json'}
FIELDS = ['entry_date', 'entry_price', 'exit_date', 'exit_price', 'exit_reason', 'holding_bars', 'r_gross', 'r_net']


def prohibited(*args, **kwargs):
    raise RuntimeError('This audit is offline')


socket.create_connection = prohibited
socket.socket.connect = prohibited


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-9 + 1e-10*abs(b)
    return a == b


def ema20(values):
    # Read only the fixed historical rule: first-window arithmetic mean seed.
    result = [math.nan] * len(values)
    if len(values) < 20:
        return result
    result[19] = math.fsum(values[:20]) / 20
    for i in range(20, len(values)):
        result[i] = values[i] * (2/21) + result[i-1] * (19/21)
    return result


def fee_fraction(entry):
    return 2 * max(.0005, .005 / entry)


def accounting(entry, exit_price, stop):
    risk = entry-stop
    if risk <= 0 or entry <= 0:
        return None
    fee = fee_fraction(entry)
    return {'risk_per_share': risk, 'round_trip_fraction': fee,
            'fee_per_share': fee*entry, 'r_gross': (exit_price-entry)/risk,
            'r_net': (exit_price-entry-fee*entry)/risk}


def classification(reason):
    if reason in ('structure_stop_C', 'exit_a6_1_costbasis'):
        return 'closed'
    if reason == 'invalid_nonpositive_risk':
        return 'invalid_risk_not_valid_trade'
    if reason == 'skipped_limit_up_at_entry':
        return 'not_entered_limit'
    if reason == 'signal_at_end_not_entered':
        return 'not_entered_at_end'
    if reason == 'open_at_end' or '数据末尾未执行' in reason:
        return 'entered_not_closed'
    return 'unrecognized'


def replay(symbol, dates, opens, closes, averages, signal_position, stop):
    """Only fixed historical signal/stop supplied. No signal selection is performed."""
    n = len(dates)
    ent = signal_position+1
    result = {'entry_date': dates[signal_position], 'entry_price': closes[signal_position],
              'exit_date': None, 'exit_price': None, 'exit_reason': 'signal_at_end_not_entered',
              'holding_bars': 0, 'r_gross': None, 'r_net': None,
              'trigger_date': None, 'deferred_open_dates': [], 'both_exit_conditions': False}
    if ent == n:
        return result
    ep = opens[ent]
    result.update(entry_date=dates[ent], entry_price=ep)
    cn = symbol.endswith(('.SS', '.SZ')) and not symbol.startswith('TH')
    if cn and closes[ent-1] > 0 and ep >= closes[ent-1]*1.095:
        result['exit_reason'] = 'skipped_limit_up_at_entry'
        return result
    if ep-stop <= 0:
        result.update(exit_date=dates[ent], exit_price=ep, exit_reason='invalid_nonpositive_risk', r_gross=0., r_net=0.)
        return result
    for j in range(ent, n):
        structural = closes[j] < stop
        weakening = j >= 20 and closes[j] < averages[j] and closes[j] < closes[j-20]
        if not structural and not weakening:
            continue
        reason = 'structure_stop_C' if structural else 'exit_a6_1_costbasis'
        result.update(trigger_date=dates[j], both_exit_conditions=bool(structural and weakening))
        ex = j+1
        while ex < n and cn and closes[ex-1] > 0 and opens[ex] <= closes[ex-1]*.905:
            result['deferred_open_dates'].append(dates[ex])
            ex += 1
        if ex == n:
            result.update(exit_reason=reason+'(数据末尾未执行)', holding_bars=j-ent)
            return result
        a = accounting(ep, opens[ex], stop)
        result.update(exit_reason=reason, exit_date=dates[ex], exit_price=opens[ex],
                      holding_bars=ex-ent, r_gross=a['r_gross'], r_net=a['r_net'])
        return result
    result.update(exit_reason='open_at_end', holding_bars=n-1-ent)
    return result


def self_checks():
    dates = [f'2020-01-{i+1:02d}' for i in range(25)]
    closes = [10.]*21 + [8., 7., 9., 10.]
    opens = [10.]*22 + [7., 9., 10.]
    avgs = ema20(closes)
    r = replay('000001.SS', dates, opens, closes, avgs, 19, 9.)
    assert r['exit_reason'] == 'structure_stop_C' and r['both_exit_conditions']
    assert r['exit_date'] == dates[23] and r['deferred_open_dates'] == [dates[22]]
    u = replay('US', dates, opens, closes, avgs, 19, 9.)
    assert u['exit_date'] == dates[22]
    limited = opens.copy(); limited[20] = 11.
    assert replay('000001.SS', dates, limited, closes, avgs, 19, 9.)['exit_reason'] == 'skipped_limit_up_at_entry'
    assert replay('US', dates, limited, closes, avgs, 19, 9.)['exit_reason'] != 'skipped_limit_up_at_entry'
    assert replay('US', dates, opens, closes, avgs, 19, 11.)['exit_reason'] == 'invalid_nonpositive_risk'
    assert replay('US', dates, opens, closes, avgs, 24, 9.)['exit_reason'] == 'signal_at_end_not_entered'
    assert replay('US', dates[:22], opens[:22], closes[:22], avgs[:22], 19, 9.)['exit_reason'].endswith('(数据末尾未执行)')
    assert replay('US', dates[:21], opens[:21], closes[:21], avgs[:21], 19, 9.)['exit_reason'] == 'open_at_end'
    assert same(ema20(list(range(1, 22)))[20], 11.5)
    assert same(accounting(1., 1.2, .9)['r_net'], 1.9)
    assert same(accounting(100., 110., 90.)['r_net'], .99)
    return {'passed': True, 'checks': ['structure_priority_and_both_conditions', 'defer_cn_sale', 'no_us_sale_limit', 'cn_entry_limit', 'no_us_entry_limit', 'invalid_risk', 'last_bar_signal', 'last_bar_pending_exit', 'open_end', 'ema_seed_and_update', 'low_price_fee', 'high_price_fee']}


def main():
    manifest = json.loads((OUT/'input-manifest.json').read_text())
    present = [x for x in manifest['files'] if not x.get('missing')]
    assert all(sha(OUT/x['copy']) == x['sha256'] for x in present), 'Frozen input changed before audit'
    assert sha(OUT/'protocol.md') == manifest['protocol_sha256']
    write_json('execution-fingerprint.json', {'started_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'script_sha256': sha(Path(__file__)), 'protocol_sha256': sha(OUT/'protocol.md'),
               'input_manifest_sha256': sha(OUT/'input-manifest.json'), 'python': sys.version, 'pandas': pd.__version__})
    probes = self_checks()
    prices = {}; quality = []
    for symbol in manifest['symbols']:
        path = RAW/'pool-snapshot-2026-08-25'/f'{symbol}.bars.parquet'
        if not path.exists():
            quality.append({'symbol': symbol, 'missing': True}); continue
        b = pd.read_parquet(path)
        dates = [x.date().isoformat() for x in b.index]
        q = {'symbol': symbol, 'rows': len(b), 'start': min(dates), 'end': max(dates),
             'monotonic': bool(b.index.is_monotonic_increasing), 'duplicate_dates': len(dates)-len(set(dates)),
             'missing_ohlcv': int(b[['open','high','low','close','volume']].isna().sum().sum()),
             'nonfinite_ohlcv': sum(not math.isfinite(float(v)) for col in b.columns for v in b[col]),
             'nonpositive_ohlc': int((b[['open','high','low','close']] <= 0).sum().sum()),
             'high_below_low': int((b.high < b.low).sum()),
             'open_close_outside_range': int(((b.open < b.low-1e-9)|(b.open > b.high+1e-9)|(b.close < b.low-1e-9)|(b.close > b.high+1e-9)).sum())}
        meta = json.loads(path.with_name(f'{symbol}.bars.meta.json').read_text())
        q['metadata'] = meta
        quality.append(q)
        opens, closes = b.open.astype(float).tolist(), b.close.astype(float).tolist()
        prices[symbol] = {'dates': dates, 'pos': {d:i for i,d in enumerate(dates)}, 'opens': opens,
                          'closes': closes, 'averages': ema20(closes), 'quality': q}
    records = []; flat = []
    for module, filename in RUNS.items():
        source = json.loads((RAW/'backtest-runs-snapshot-2026-08-31'/filename).read_text())
        assert source['params']['exit_variant'] == 'a6_1_costbasis' and source['params']['limit_guard'] is True
        for row_number, old in enumerate(source['trades'], 1):
            key = f'{module}:{row_number:04d}:{old["symbol"]}:{old["signal_date"]}'
            status = classification(old['exit_reason']); closed = status == 'closed'
            entered = status in ('closed', 'entered_not_closed')
            rec = {'key': key, 'module': module, 'source_row_1based': row_number, 'status': status, 'historical': old}
            f = {'key': key, 'module': module, 'source_row_1based': row_number, 'symbol': old['symbol'],
                 'status': status, 'signal_date': old['signal_date'], **{'old_'+k:old[k] for k in FIELDS},
                 'stop_price': old['stop_price'], 'stored_risk_per_share': old['entry_price']-old['stop_price']}
            stored_calc = accounting(old['entry_price'], old['exit_price'], old['stop_price']) if closed else None
            rec['stored_price_accounting'] = stored_calc
            if stored_calc:
                for k,v in stored_calc.items(): f['stored_recalc_'+k] = v
                for k in ['r_gross','r_net']:
                    f['stored_'+k+'_match'] = same(stored_calc[k], old[k]); f['stored_'+k+'_difference'] = stored_calc[k]-old[k]
            p = prices.get(old['symbol'])
            if not p:
                rec['gap'] = 'price_file_missing'; records.append(rec); flat.append(f); continue
            for field in ['signal_date', 'entry_date', 'exit_date']:
                value = old[field]
                f[field+'_covered'] = value in p['pos'] if value else None
            f['price_start'], f['price_end'] = p['dates'][0], p['dates'][-1]
            signal_i = p['pos'].get(old['signal_date'])
            entry_i = p['pos'].get(old['entry_date'])
            exit_i = p['pos'].get(old['exit_date'])
            if entry_i is not None:
                f['entry_open'] = p['opens'][entry_i]
                f['entry_open_match'] = same(old['entry_price'],f['entry_open']) if status != 'not_entered_at_end' else None
                f['entry_open_difference'] = f['entry_open']-old['entry_price'] if status != 'not_entered_at_end' else None
                f['snapshot_risk_per_share'] = f['entry_open']-old['stop_price']
                if status == 'not_entered_at_end':
                    f['last_signal_close_placeholder_match'] = same(old['entry_price'],p['closes'][entry_i])
            if entered and entry_i is not None and signal_i is not None:
                f['entry_is_next_bar'] = entry_i == signal_i+1
            if exit_i is not None:
                f['exit_open'] = p['opens'][exit_i]
                f['exit_open_match'] = same(old['exit_price'], f['exit_open'])
                f['exit_open_difference'] = f['exit_open']-old['exit_price']
                if closed and entry_i is not None:
                    f['holding_bars_match'] = old['holding_bars'] == exit_i-entry_i
                    sc = accounting(p['opens'][entry_i],p['opens'][exit_i],old['stop_price'])
                    rec['snapshot_price_accounting'] = sc
                    if sc:
                        for k,v in sc.items(): f['snapshot_recalc_'+k] = v
                        f['snapshot_r_net_match'] = same(sc['r_net'],old['r_net'])
            # Ordering/date problems cannot be silently normalized into a replay.
            q = p['quality']
            if signal_i is None:
                rec['replay_gap'] = 'signal_date_missing'
            elif not q['monotonic'] or q['duplicate_dates'] or q['nonfinite_ohlcv']:
                rec['replay_gap'] = 'unusable_price_order_or_nonfinite'
            else:
                new = replay(old['symbol'],p['dates'],p['opens'],p['closes'],p['averages'],signal_i,old['stop_price'])
                rec['independent_replay'] = new
                diffs = {k:{'old':old[k],'replay':new[k]} for k in FIELDS if not same(old[k],new[k])}
                rec['replay_differences'] = diffs
                for k in FIELDS: f['replay_'+k] = new[k]; f['replay_'+k+'_match'] = same(old[k],new[k])
                f['replay_all_fields_match'] = not diffs
                f['replay_differing_fields'] = '|'.join(diffs)
                f['replay_trigger_date'] = new['trigger_date']
                f['replay_deferred_open_dates'] = '|'.join(new['deferred_open_dates'])
                f['replay_both_exit_conditions'] = new['both_exit_conditions']
            records.append(rec); flat.append(f)
    assert len(records) == 2309
    columns = list(dict.fromkeys(k for f in flat for k in f))
    with (OUT/'all-2309-rows.csv').open('w',newline='') as fp:
        writer = csv.DictWriter(fp,fieldnames=columns); writer.writeheader(); writer.writerows(flat)
    write_json('all-2309-rows.json',records)
    write_json('price-quality.json',quality)
    mismatches = [x for x in records if x.get('replay_differences') or x.get('replay_gap') or x.get('gap')]
    write_json('replay-differences.json',mismatches)
    def summarize(fs):
        out = {'rows':len(fs), 'status_counts':dict(collections.Counter(x['status'] for x in fs)),
               'old_exit_reason_counts':dict(collections.Counter(x['old_exit_reason'] for x in fs))}
        checks = ['signal_date_covered','entry_date_covered','exit_date_covered','entry_open_match','exit_open_match',
                  'entry_is_next_bar','holding_bars_match','stored_r_gross_match','stored_r_net_match','snapshot_r_net_match',
                  'last_signal_close_placeholder_match','replay_all_fields_match'] + ['replay_'+k+'_match' for k in FIELDS]
        for c in checks:
            out[c] = {'checked':sum(x.get(c) is not None for x in fs), 'matched':sum(x.get(c) is True for x in fs),
                      'different':sum(x.get(c) is False for x in fs)}
        out['replay_deferred_records'] = sum(bool(x.get('replay_deferred_open_dates')) for x in fs)
        out['both_exit_conditions_records'] = sum(bool(x.get('replay_both_exit_conditions')) for x in fs)
        for k in ['entry_open_difference','exit_open_difference','stored_r_gross_difference','stored_r_net_difference']:
            out['max_abs_'+k] = max((abs(x[k]) for x in fs if x.get(k) is not None),default=None)
        return out
    summary = {'scope':'independent old-rule replay of fixed historical records; not entry regeneration or investable performance',
               'total':summarize(flat),'by_module':{m:summarize([x for x in flat if x['module']==m]) for m in RUNS},
               'true_entered_only':summarize([x for x in flat if x['status'] in ('closed','entered_not_closed')]),
               'true_closed_only':summarize([x for x in flat if x['status']=='closed']),
               'symbols':len(quality),'data_end_distribution':dict(collections.Counter(x.get('end') for x in quality)),
               'problem_quality':[x for x in quality if x.get('missing') or any(x.get(k) for k in ['duplicate_dates','missing_ohlcv','nonfinite_ohlcv','nonpositive_ohlc','high_below_low','open_close_outside_range']) or not x['monotonic']],
               'replay_difference_rows':len(mismatches),'self_checks':probes,
               'frozen_inputs_unchanged':all(sha(OUT/x['copy'])==x['sha256'] for x in present),
               'original_inputs_unchanged':all(Path(x['source']).exists() and sha(Path(x['source']))==x['sha256'] for x in present),
               'finished_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write_json('summary.json',summary)
    print(json.dumps({'total':summary['total'],'replay_difference_rows':len(mismatches),'problem_quality_symbols':len(summary['problem_quality']),'hashes_unchanged':summary['frozen_inputs_unchanged'] and summary['original_inputs_unchanged']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
