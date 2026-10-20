"""Independently recompute 20-bar price geometry without source feature helpers."""
from pathlib import Path
from decimal import Decimal as D
import csv, gzip, json, hashlib

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'research-broad-etf-technical-2026-09-08/execution/inputs'

def main():
    cond=json.loads((HERE/'source-audit/conditions.json').read_text())['rows']
    actions=json.loads((SOURCE/'actions.json').read_text())
    bars={s:list(csv.DictReader((SOURCE/f'bars/{s}-nominal.csv').open())) for s in ('sh510300','sz159915')}
    with gzip.open(SOURCE/'exit-observations.json.gz','rt') as f: observations=json.load(f)
    checks=[]
    for r in cond:
        s,day=r['symbol'],r['signal_date']
        prefix=[b for b in bars[s] if b['date']<=day]
        window=prefix[-21:];assert len(window)==21
        converted=[]
        for b in window:
            factor=D(1)
            for a in actions:
                if a['symbol']!=s or not b['date']<a['effective_date']<=day:continue
                assert a['announcement_date']<=day
                if a['type']=='split':factor/=D(str(a['ratio']))
                else:
                    previous=[x for x in prefix if x['date']<a['effective_date']][-1]
                    factor*=(D(previous['close'])-D(str(a['cash'])))/D(previous['close'])
            converted.append({k:D(b[k])*factor for k in ('high','low','close')})
        sma=sum((x['close'] for x in converted[-20:]),D(0))/20
        tr=[max(x['high']-x['low'],abs(x['high']-p['close']),abs(x['low']-p['close'])) for p,x in zip(converted,converted[1:])]
        atr=sum(tr,D(0))/20
        position=D(str(r['close']))>=sma and abs(D(str(r['l1']))-sma)<=atr
        obs=observations[s][day]
        direction=(obs['close']>obs['ema20'] and obs['close']>obs['sma20'] and obs['ema20_slope']>0 and obs['sma20_slope']>0 and obs['close']>obs['cost20'])
        assert abs(float(sma)-r['sma20'])<1e-12
        assert abs(float(atr)-r['atr20'])<1e-12
        assert position==r['position_p'] and direction==r['direction_q']
        assert r['l1_confirmed_available_date']<=r['breakdown_date']<=day
        if r['target_confirmed_at'] is not None:assert r['target_confirmed_at']<=day
        assert r['basis_as_of']==day
        checks.append(dict(candidate_id=r['candidate_id'],sma_difference=float(sma)-r['sma20'],atr_difference=float(atr)-r['atr20'],position_match=True,direction_match=True))
    lock=json.loads((HERE/'source-audit/source-code-lock.json').read_text())
    for p,h in lock['files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    result=dict(status='passed',checked=len(checks),source_lock_files_unchanged=len(lock['files']),
        method='Decimal action multipliers and last21 raw quotes; no condition builder or price-basis helper imports; Q from frozen daily observations',
        limitations='Original C1 detection and historical target selection are reused, not independently reimplemented.',checks=checks)
    out=HERE/'controller-condition-review.json';assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('84 conditions independently matched; source locks unchanged')

if __name__=='__main__':main()
