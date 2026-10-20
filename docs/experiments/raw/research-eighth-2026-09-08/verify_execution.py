"""Independent entry/exit execution audit; does not import the account engine."""
from pathlib import Path
import json
import gzip
import math
from datetime import date
import pandas as pd

P=Path(__file__).resolve().parent
Q=P/'product-qualification'
params=json.loads((Q/'execution-parameters.json').read_text())
actions=json.loads((Q/'actions.json').read_text())
prices={s:pd.read_csv(Q/'bars-helper-native'/f'{s}-nominal.csv').set_index('date').to_dict('index') for s in params['symbols']}
with gzip.open(P/'candidate-study/candidates.json.gz','rt') as f: candidates={c['candidate_id']:c for c in json.load(f)}
with gzip.open(P/'candidate-study/exit-observations.json.gz','rt') as f: observations=json.load(f)
sessions=sorted({d for bars in prices.values() for d in bars})

def same(a,b):
    assert abs(a-b)<=1e-8*max(1,abs(a),abs(b)),(a,b)

def levels_at(s,levels,basis,d):
    values=dict(levels)
    for a in sorted(actions,key=lambda x:x['effective_date']):
        if a['symbol']!=s or not basis<a['effective_date']<=d:continue
        if a['type']=='split':factor=1/float(a['ratio'])
        else:
            previous=max(x for x in prices[s] if x<a['effective_date'])
            close=prices[s][previous]['close'];factor=(close-float(a['cash']))/close
        values={k:v*factor if v is not None else None for k,v in values.items()}
    return values

def unavailable(s,d):
    if d in params['blocked_dates'][s]:return True
    if d not in prices[s]:return True
    previous=max(x for x in prices[s] if x<d)
    reference=prices[s][previous]['close']
    for a in sorted(actions,key=lambda x:x['effective_date']):
        if a['symbol']==s and previous<a['effective_date']<=d:
            reference=reference/float(a['ratio']) if a['type']=='split' else reference-float(a['cash'])
    limit=params['limits'][s]
    for effective,value in params['limit_changes'].get(s,[]):
        if effective<=d:limit=value
    return abs(prices[s][d]['open']-reference)>=reference*limit-.00051

results=[]; total_trades=0; all_orders=0
for cfg in [f'P{i}' for i in range(8)]:
    R=P/'account-results'/cfg
    try: trades=pd.read_csv(R/'trades.csv').to_dict('records')
    except pd.errors.EmptyDataError:trades=[]
    daily=pd.read_csv(R/'daily.csv').set_index('date')
    orders=json.loads((R/'orders.json').read_text());roundtrips=json.loads((R/'roundtrips.json').read_text())
    order_map={o['order_id']:o for o in orders}
    for t in trades:
        s,d=t['symbol'],t['date']
        assert not unavailable(s,d),('unavailable_fill',cfg,s,d)
        same(t['price'],prices[s][d]['open']);same(t['notional'],t['shares']*t['price']);same(t['fee'],t['notional']*.001)
        assert order_map[t['order_id']]['status']=='filled'
        if t['side']=='buy':
            assert t['shares']%100==0
            if cfg!='P6':
                c=candidates[t['candidate_id']];assert c['signal_accepted'] is True
                expected_day=min(x for x in sessions if x>c['signal_date']);assert d==expected_day
                levels=levels_at(s,{k:c[k] for k in ['stop','target','upper']},c['signal_date'],d)
                rr=(levels['target']-t['price'])/(t['price']-levels['stop'])
                assert t['price']>levels['stop'] and rr>=3
                same(rr,order_map[t['order_id']]['open_rr'])
                same(levels['stop'],t['stop']);same(levels['target'],t['target'])
                if cfg=='P7':
                    previous=daily.index[daily.index<d][-1]
                    expected_risk=float(daily.loc[previous,'equity_'+s])*.01
                    same(expected_risk,t['risk_budget'])
                    assert t['shares']*(t['price']-t['stop'])<=expected_risk+1e-8
    if cfg!='P6':
        expected={c['candidate_id'] for c in candidates.values() if c['config_id']==cfg}
        actual={o['candidate_id'] for o in orders if o['side']=='buy'}
        assert expected==actual
        for o in orders:
            if o['side']=='buy' and not candidates[o['candidate_id']]['signal_accepted']:
                assert o['status']=='rejected'
        for rt in roundtrips:
            s=rt['symbol'];entry=rt['entry_date'];trigger=None;reason=None
            levels={k:rt['initial_'+k] for k in ['stop','target','upper']}
            for d in sorted(x for x in prices[s] if entry<=x<='2026-06-30'):
                rebased=levels_at(s,levels,entry,d);cl=prices[s][d]['close'];obs=observations[s][d]
                if cl<rebased['stop']:reason='structure_stop'
                elif cfg in ('P4','P7') and cl<rebased['upper'] and cl<obs['sma20'] and cl<obs['cost20']:reason='b_breakout_two_actions'
                elif cfg not in ('P4','P7') and cl<obs['ema20'] and cl<obs['cost20']:reason='ema_cost_exit'
                else:continue
                trigger=d;break
            possible=[d for d in sessions if trigger is not None and trigger<d<='2026-06-30' and not unavailable(s,d)]
            expected_exit=possible[0] if possible else None
            assert rt['exit_date']==expected_exit,('exit_date',cfg,rt['position_id'],trigger,expected_exit,rt['exit_date'])
            if expected_exit:
                sell=[t for t in trades if t['position_id']==rt['position_id'] and t['side']=='sell'];assert len(sell)==1
                assert sell[0]['reason']==reason
                assert entry<expected_exit
            results.append({'config_id':cfg,'position_id':rt['position_id'],'entry_date':entry,'first_exit_signal':trigger,'exit_date':expected_exit,'exit_reason':reason,'matched':True})
    total_trades+=len(trades);all_orders+=len(orders)
pd.DataFrame(results).to_csv(P/'execution-position-checks.csv',index=False)
(P/'execution-checks.json').write_text(json.dumps({'all_fills_checked':total_trades,'all_orders_count':all_orders,
   'technical_positions_independently_replayed':len(results),'technical_candidate_coverage':len(candidates),
   'status':'passed','scope':'all fills prices/costs/availability; technical buys and first exits independently recomputed; no account engine imports'},indent=2)+'\n')
print('passed',total_trades,'fills,',len(results),'technical lifecycles,',len(candidates),'candidate coverage')
