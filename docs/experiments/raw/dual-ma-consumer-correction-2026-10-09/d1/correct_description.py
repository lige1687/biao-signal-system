"""Propagate two proven D1 state changes without rerunning indicators or old fits.

Reads frozen saved tables. The already corrected all-period Q20 primary result
and every nonoverlap effect are reused, not re-estimated. One missing fixed-window
peak drawdown is explicitly counted, while its saved return is reused.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

sys.dont_write_bytecode = True
MAIN = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OWN = BASE.parents[3]
D1 = MAIN / 'docs/experiments/raw/dual-ma-resonance-d1-2026-09-23'
R1 = MAIN / 'docs/experiments/raw/dual-ma-resonance-s0-r1-2026-09-23/resonance.py'
STORAGE_HELPER = OWN / 'docs/experiments/raw/daily-weekly-opportunity-2026-10-09/guarded_runner.py'
CONDITIONS = ('Q20','Q60','Q120','Q20_Q60','Q20_Q120','Q60_Q120','Q20_Q60_Q120')
CELLS = ('000','100','010','001','110','101','011','111')
TARGETS = {'510300.SS': ('2025-05-29','Q20'), '159915.SZ': ('2023-01-09','Q60')}
CONTRACT_SHA = '00ccc8185d98e8037bf15d42e5db374223aa3b88362fecc785692d23aef3579b'
SOURCE_LOCK_SHA = '55fe12164c07234a0704831674551a7422e739a64d9c2e85b3c067730a5a0169'


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def csv_rows(p):
    integers = {'raw_row','rows','calendar_days'}
    floats = {'close','Y','start_drawdown','peak_drawdown','wait_change','fixed_Y'}
    with Path(p).open(newline='') as f:
        result = []
        for raw in csv.DictReader(f):
            row = {}
            for k,v in raw.items():
                if v == '': value = None
                elif v in ('True','False'): value = v == 'True'
                elif k in integers or '_delay_' in k: value = int(v)
                elif k in floats or k.startswith(('ema','sma')): value = float(v)
                else: value = v
                row[k] = value
            result.append(row)
    return result


def classify(row):
    q = {k:row[k] for k in ('Q20','Q60','Q120')}
    if any(v is not None and type(v) is not bool for v in q.values()):
        raise ValueError('nonboolean state')
    for k in CONDITIONS[3:]:
        vs = [q[c] for c in k.split('_')]
        q[k] = None if any(v is None for v in vs) else all(vs)
    q['H'] = q['Q60_Q120']
    q['cell'] = None if any(q[k] is None for k in ('Q20','Q60','Q120')) else ''.join('1' if q[k] else '0' for k in ('Q20','Q60','Q120'))
    return q


def patch_days(symbol, rows):
    new = copy.deepcopy(rows)
    date,col = TARGETS[symbol]
    hits = [i for i,r in enumerate(rows) if r['date'] == date]
    if len(hits) != 1: raise ValueError('target date not unique')
    i = hits[0]
    if rows[i][col] is not True or rows[i]['calendar_gap'] or rows[i+1]['calendar_gap']:
        raise ValueError('target state or gap drift')
    new[i][col] = False
    new[i].update(classify(new[i]))
    for j in (i,i+1):
        for k in CONDITIONS:
            prior,current = new[j-1][k],new[j][k]
            known = prior is not None and current is not None
            new[j]['start_'+k] = prior is False and current is True if known else None
            new[j]['exit_'+k] = prior is True and current is False if known else None
            new[j]['first_'+k] = prior is None and current is True if current is not None else None
    if any(a['G'] != b['G'] or a['H'] != b['H'] for a,b in zip(rows,new)):
        raise ValueError('unexpected G/H change')
    return new


def ordered_ids(events):
    out=[];last=None
    for r in sorted((r for r in events if r['condition']=='Q20' and r['effect_eligible']),key=lambda r:r['date']):
        if last is None or r['e']>last:
            out.append((r['date'],r['e'],r['x'],r['H']));last=r['x']
    return out


def stats(values):
    return {'n':len(values),'mean':statistics.fmean(values) if values else None,
            'median':statistics.median(values) if values else None,'minimum':min(values) if values else None}


def quantile(values,p):
    if not values:return None
    a=sorted(values);pos=(len(a)-1)*p;lo=math.floor(pos);hi=math.ceil(pos)
    return a[lo]+(a[hi]-a[lo])*(pos-lo)


def summaries(symbol, days, events, episodes, old, accepted_primary):
    """Recompute affected descriptive consumers; reuse accepted primary and sparse."""
    updated=copy.deepcopy(old)
    years=('2025','all') if symbol=='510300.SS' else ('2023','all')
    for yr in years:
        part=updated['periods'][yr]
        ds=[r for r in days if yr=='all' or r['period']==yr]
        es=[r for r in events if yr=='all' or r['period']==yr]
        eps=[r for r in episodes if yr=='all' or r['period']==yr]
        cells=Counter(r['cell'] or 'unknown' for r in ds)
        part['eight_cells']={k:cells[k] for k in CELLS}|{'unknown':cells['unknown']}
        keys=('Q20',) if symbol=='510300.SS' else ('Q60','Q20_Q60')
        for k in keys:
            chosen=[r for r in es if r['condition']==k]
            eligible=[r for r in chosen if r['effect_eligible']]
            complete=[r['rows'] for r in eps if r['condition']==k and r['complete']]
            known=[r for r in ds if r[k] is not None]
            part['seven_conditions'][k]={
                'known_days':len(known),'unknown_days':len(ds)-len(known),
                'true_days':sum(r[k] is True for r in known),'start_raw':len(chosen),
                'start_gap_excluded':sum(r['calendar_gap'] for r in chosen),
                'exit_raw':sum(r['exit_'+k] is True for r in ds),
                'first_observable_true':sum(r['first_'+k] is True for r in ds),
                'price':stats([r['Y'] for r in eligible]),
                'price_exclusions':dict(Counter(r['exclusion'] for r in chosen if r['exclusion'])),
                'complete_episodes':len(complete),
                'censored_episodes':sum(r['condition']==k and not r['complete'] for r in eps),
                'duration_rows':{'median':statistics.median(complete) if complete else None,'p25':quantile(complete,.25),'p75':quantile(complete,.75)}}
        transitions=Counter();gap=unknown=0
        for a,b in zip(ds,ds[1:]):
            if b['calendar_gap']:gap+=1
            elif a['cell'] is None or b['cell'] is None:unknown+=1
            else:transitions[a['cell']+'->'+b['cell']]+=1
        part['transitions']={'matrix':{a:{b:transitions[a+'->'+b] for b in CELLS} for a in CELLS},'skipped_gap':gap,'skipped_unknown':unknown}
        part['G_cross']=dict(Counter('unknown' if r['G'] is None or r['cell'] is None else f"G{int(r['G'])}_111{int(r['cell']=='111')}" for r in ds))
        if symbol=='510300.SS':
            qe=[r for r in es if r['condition']=='Q20']; eligible=[r for r in qe if r['effect_eligible']]
            ordered=sorted(eligible,key=lambda r:r['date'])
            part['event_flow']={'Q20_raw_starts':len(qe),'Q20_exclusions':dict(Counter(r['exclusion'] for r in qe if r['exclusion'])),'Q20_eligible':len(eligible),'overlapping_adjacent_eligible':sum(ordered[i]['e']<=ordered[i-1]['x'] for i in range(1,len(ordered)))}
            part['G_event_cross']=dict(Counter('unknown' if r['G'] is None or r['H'] is None else f"G{int(r['G'])}_H{int(r['H'])}" for r in qe))
            qp=[r for r in eps if r['condition']=='Q20']
            part['waiting']={k:dict(Counter(r[k+'_join_status'] for r in qp)) for k in ('Q60','Q120','H')}
            part['waiting']['H_wait_change']=stats([r['wait_change'] for r in qp if r['wait_change'] is not None])
            part['waiting']['H_wait_missing']=dict(Counter(r['wait_missing_reason'] for r in qp if r['wait_missing_reason']))
            # Remaining annual/risk consumers must propagate the deleted event.
            # Reuse, rather than re-estimate, already accepted all-period means.
            for name,flag in [('A',True),('B',False)]:
                group=[r for r in eligible if r['H'] is flag]
                if yr=='all':
                    ref='joint' if flag else 'control'
                    vals=[r['Y'] for r in group]
                    target={'n':accepted_primary[ref+'_dates'],'mean':accepted_primary[ref+'_mean_pct']/100,
                            'median':statistics.median(vals) if vals else None,'minimum':min(vals) if vals else None}
                    if target['n'] != len(group):raise ValueError('accepted primary count drift')
                else:target=stats([r['Y'] for r in group])
                part['main_H'][name]={'target':target,'path_complete':sum(not r['path_incomplete'] for r in group),
                                     'start_drawdown':stats([r['start_drawdown'] for r in group if r['start_drawdown'] is not None]),
                                     'peak_drawdown':stats([r['peak_drawdown'] for r in group if r['peak_drawdown'] is not None])}
            enough=all(part['main_H'][k]['target']['n']>=10 for k in ('A','B'))
            part['main_H']['minimum_count_met']=enough
            part['main_H']['delta']=accepted_primary['difference_pp']/100 if yr=='all' else (part['main_H']['A']['target']['mean']-part['main_H']['B']['target']['mean'] if enough else None)
        # Every nonoverlap effect is inherited exactly, no recomputation.
        assert part['nonoverlap']==old['periods'][yr]['nonoverlap']
    return updated


def compute(root, r1):
    days=csv_rows(D1/'formal/daily_states.csv');events=csv_rows(D1/'formal/events.csv');episodes=csv_rows(D1/'formal/episodes.csv')
    cal=read(MAIN/'docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json')
    calendar=sorted(d for d,m in cal['days'].items() if m['is_trading_day'])
    old_summary=read(D1/'formal/summary.json')
    primary=next(r['corrected'] for r in read(MAIN/'docs/experiments/raw/dual-ma-correction-2026-09-28/event-impact.json')['results'] if r['symbol']=='510300.SS')
    labels=[r for r in read(MAIN/'docs/experiments/raw/dual-ma-information-2026-09-28/observations.json') if r['symbol']=='159915.SZ' and r['date']=='2023-01-10']
    if len(labels)!=1:raise ValueError('saved label must be unique')
    label=labels[0]
    if label['label_start']!='2023-01-11' or label['label_end']!='2023-02-16' or label['label_status']!='mature':raise ValueError('saved label target changed')
    price_rows=csv_rows(MAIN/'docs/experiments/raw/factor-six-etf-economic-momentum-2026-09-23/formal/159915.SZ.csv')
    if [r['date'] for r in price_rows]!=sorted(set(r['date'] for r in price_rows)):raise ValueError('price dates not unique and ordered')
    prices={r['date']:float(r['economic_index']) for r in price_rows}
    if any(not math.isfinite(v) or v<=0 for v in prices.values()):raise ValueError('price must be finite and positive')
    if any(type(label[k]) not in (int,float) or not math.isfinite(label[k]) for k in ('return_pct','mae_pct')):raise ValueError('invalid saved label number')
    window=calendar[calendar.index('2023-01-11'):calendar.index('2023-02-16')+1]
    if len(window)!=22 or any(d not in prices for d in window):raise ValueError('fixed risk window missing')
    peak=prices[window[0]];risk=0.0
    for day in window:
        peak=max(peak,prices[day]);risk=max(risk,1-prices[day]/peak)
    new_days=[];new_events=[];new_episodes=[];results={};nonoverlap={}
    import pandas as pd
    for sym in TARGETS:
        before=[r for r in days if r['symbol']==sym];after=patch_days(sym,before)
        es=[r for r in events if r['symbol']==sym];ep=[r for r in episodes if r['symbol']==sym]
        if sym=='510300.SS':
            en=[r for r in es if not(r['date']=='2025-05-29' and r['condition']=='Q20')]
            pn=[r for r in ep if not(r['start']=='2025-05-29' and r['condition']=='Q20')]
            if len(es)-len(en)!=1 or len(ep)-len(pn)!=1:raise ValueError('Q20 identity drift')
        else:
            day=next(r for r in after if r['date']=='2023-01-10')
            en=copy.deepcopy(es)
            for k in ('Q60','Q20_Q60'):
                if not day['start_'+k] or any(r['date']==day['date'] and r['condition']==k for r in es):raise ValueError('new start identity drift')
                en.append({k2:day[k2] for k2 in ('symbol','date','period','raw_row','calendar_gap','H','G','cell')}|
                          {'condition':k,'e':label['label_start'],'x':label['label_end'],'Y':label['return_pct']/100,
                           'path_incomplete':False,'start_drawdown':-label['mae_pct']/100,'peak_drawdown':risk,'exclusion':None,'effect_eligible':True})
            en.sort(key=lambda r:(r['date'],CONDITIONS.index(r['condition'])))
            pn=[r for r in ep if r['condition'] not in ('Q60','Q20_Q60')]
            for k in ('Q60','Q20_Q60'):
                frame=pd.DataFrame(after).set_index('date');frame['Q20']=frame[k];frame['start_Q20']=frame['start_'+k]
                for e in r1.build_episodes(frame,calendar):
                    # These auxiliary episodes never contain Q20 waiting labels.
                    template={key:None for key in ep[0]}
                    template.update(symbol=sym,period=e['start'][:4] if not e['start'].startswith('2026') else '2026H1',condition=k,
                                    **{key:e[key] for key in ('start','end','rows','calendar_days','complete','left_truncated','censor_reason')})
                    pn.append(template)
            pn.sort(key=lambda r:(CONDITIONS.index(r['condition']),r['start']))
        for yr in ('2022','2023','2024','2025','2026H1','all'):
            old_ids=ordered_ids([r for r in es if yr=='all' or r['period']==yr]);new_ids=ordered_ids([r for r in en if yr=='all' or r['period']==yr])
            if old_ids!=new_ids:raise ValueError('nonoverlap sequence changed')
            nonoverlap[sym+'|'+yr]={'same':True,'retained':len(old_ids)}
        results[sym]=summaries(sym,after,en,pn,old_summary['symbols'][sym],primary)
        new_days+=after;new_events+=en;new_episodes+=pn
    return {'corrected_days':new_days,'corrected_events':new_events,'corrected_episodes':new_episodes,
            'corrected_symbol_summaries':results,'nonoverlap_identity_checks':nonoverlap,
            'new_return_labels':0,'added_auxiliary_risk_windows':1,'auxiliary_risk':{'asset':'159915.SZ','start':window[0],'end':window[-1],'closes':22,'peak_drawdown':risk,'shared_by':['Q60','Q20_Q60']},
            'old_primary_reference':primary,'old_seven_comparisons_rerun':False,'old_accounts_run':0}


def run():
    release=read(BASE/'d1-release.json');contract=BASE/'contract.json';plan_path=BASE/'d1-output-plan.json'
    if digest(contract)!=CONTRACT_SHA:raise ValueError('fixed correction contract changed')
    if release.get('authorized') is not True or release.get('contract_sha256')!=CONTRACT_SHA or release.get('plan_sha256')!=digest(plan_path):raise ValueError('not released')
    source_lock=HERE/'source-lock.json'
    if digest(source_lock)!=SOURCE_LOCK_SHA:raise ValueError('fixed input closure changed')
    locked=read(source_lock)
    required={str(Path(__file__).resolve()),str(contract),str(plan_path),str(R1),str(STORAGE_HELPER),str(source_lock)}|set(locked['files'])
    bindings=release.get('bindings',{})
    if not required.issubset(bindings):raise ValueError('incomplete code closure')
    for path,expected in bindings.items():
        if digest(path)!=expected:raise ValueError('source drift: '+path)
    for path,expected in locked['files'].items():
        if bindings[path]!=expected:raise ValueError('release disagrees with frozen source: '+path)
    if sys.version.split()[0]!=locked['python']:raise ValueError('Python version changed')
    import importlib.metadata
    for name,version in locked['packages'].items():
        if importlib.metadata.version(name)!=version:raise ValueError('package version changed: '+name)
    plan=read(plan_path)
    if plan['task_id']!=read(contract)['task_id']+'-d1':raise ValueError('task mismatch')
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(MAIN,plan,plan['task_id'],plan['estimated_bytes'],plan['internal_metadata_bytes'])
    marker=BASE/'d1-started.json'
    with marker.open('x') as f:
        json.dump({'started_at':datetime.now(timezone.utc).isoformat(),'contract_sha256':digest(contract),'release_sha256':digest(BASE/'d1-release.json'),'state':'running'},f);f.flush();os.fsync(f.fileno())
    try:
        r1=load(R1,'fixed_r1_for_episode_metadata')
        helper=load(STORAGE_HELPER,'accepted_external_writer')
        result=compute(MAIN,r1)
        fds,fd=helper.open_external_output(plan)
        try: receipt=helper.durable_json(fd,'d1-correction.json',result,plan)
        finally:
            for item in reversed(fds):os.close(item)
    except BaseException as error:
        with marker.open('r+') as f:
            state=json.load(f);state.update(state='failed',error=repr(error),failed_at=datetime.now(timezone.utc).isoformat());f.seek(0);json.dump(state,f,indent=2);f.truncate()
        raise
    with marker.open('r+') as f:
        state=json.load(f);state.update(state='completed',output=str(Path(plan['output'])/'d1-correction.json'),receipt=receipt,finished_at=datetime.now(timezone.utc).isoformat());f.seek(0);json.dump(state,f,indent=2);f.truncate()
    print(json.dumps(state))


if __name__=='__main__':run()
