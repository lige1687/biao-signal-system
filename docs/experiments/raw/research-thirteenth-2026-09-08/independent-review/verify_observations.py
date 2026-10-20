"""Independent streaming Decimal EMA/cost-price audit; no signal or account imports.
Only previously observed closes are adjusted on an announced effective action date.
"""
from pathlib import Path
from decimal import Decimal as D, getcontext
from collections import deque
import json,csv,gzip,hashlib,shutil
getcontext().prec=40
BASE=Path(__file__).resolve().parent
EIGHTH=BASE.parent.parent/'research-eighth-2026-09-08'
SNAP=BASE/'observation-inputs'
def save(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str)+'\n')
def csvout(p,rows):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['none']);w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 if not SNAP.exists():
  SNAP.mkdir()
  paths=[EIGHTH/'candidate-study/exit-observations.json.gz',EIGHTH/'product-qualification/actions.json',EIGHTH/'product-qualification/execution-parameters.json']+sorted((EIGHTH/'product-qualification/bars-helper-native').glob('*.csv'))
  manifest=[]
  for p in paths:
   q=SNAP/p.name;shutil.copyfile(p,q);manifest.append(dict(source=str(p.resolve()),file=p.name,sha256=sha(p)))
  save(BASE/'observation-inputs-lock.json',manifest)
 lock=json.loads((BASE/'observation-inputs-lock.json').read_text())
 assert all(sha(Path(x['source']))==sha(SNAP/x['file'])==x['sha256'] for x in lock)
 actions=json.loads((SNAP/'actions.json').read_text());params=json.loads((SNAP/'execution-parameters.json').read_text())
 obs=json.load(gzip.open(SNAP/'exit-observations.json.gz','rt'))
 rows=[];actionrows=[];diffs=[];coverage=[];computed={};tol=D('1e-11')
 for symbol in sorted(params['symbols']):
  bars=list(csv.DictReader((SNAP/f'{symbol}-nominal.csv').open()));history=deque(maxlen=20);ema=None;applied=set();lastclose=None;values={};maxema=D(0);maxcost=D(0)
  for ix,b in enumerate(bars):
   day=b['date'];close=D(b['close'])
   today=[a for a in actions if a['symbol']==symbol and a['event_id'] not in applied and a['effective_date']<=day]
   for a in today:
    assert a['announcement_date']<a['effective_date']
    factor=1/D(a['ratio']) if a['type']=='split' else (lastclose-D(a['cash']))/lastclose
    before=ema;beforecost=history[0] if len(history)==20 else None
    if ema is not None:ema*=factor
    history=deque((v*factor for v in history),maxlen=20);applied.add(a['event_id'])
    actionrows.append(dict(symbol=symbol,event_id=a['event_id'],date=a['effective_date'],next_quote_date=day,announcement_date=a['announcement_date'],type=a['type'],factor=factor,previous_nominal_close=lastclose,ema_before=before,ema_after_action_before_current_close=ema,cost20_before=beforecost,cost20_after_action=history[0] if len(history)==20 else None))
   cost=history[0] if len(history)==20 else None
   if ema is None and len(history)==19:ema=(sum(history)+close)/20
   elif ema is not None:ema+=D(2)/21*(close-ema)
   history.append(close);lastclose=close
   if not params['research_window'][0]<=day<=params['research_window'][1]:continue
   assert ema is not None and cost is not None
   values[day]=dict(ema20=str(ema),cost20=str(cost),close=str(close),road_exit=close<ema and close<cost)
   original=obs[symbol][day];de=abs(ema-D(str(original['ema20'])));dc=abs(cost-D(str(original['cost20'])));maxema=max(maxema,de);maxcost=max(maxcost,dc)
   underema=close<ema;undercost=close<cost;expected=underema and undercost
   mainunderema=original['close']<original['ema20'];mainundercost=original['close']<original['cost20'];main=mainunderema and mainundercost
   row=dict(symbol=symbol,date=day,quote_index=ix,close=close,ema20=ema,cost20=cost,reported_ema20=original['ema20'],reported_cost20=original['cost20'],ema_abs_difference=de,cost_abs_difference=dc,close_below_ema20=underema,close_below_cost20=undercost,road_exit=expected,reported_close_below_ema20=mainunderema,reported_close_below_cost20=mainundercost,reported_road_exit=main,action_today=bool(today))
   rows.append(row)
   if de>tol or dc>tol or D(str(original['close']))!=close or original['basis_as_of']!=day or expected!=main or underema!=mainunderema or undercost!=mainundercost:diffs.append(row)
  assert set(values)==set(obs[symbol]),(symbol,'observation date coverage')
  expectedactions={a['event_id'] for a in actions if a['symbol']==symbol}
  assert applied==expectedactions
  computed[symbol]=values;coverage.append(dict(symbol=symbol,all_source_bars=len(bars),first_source_date=bars[0]['date'],last_source_date=bars[-1]['date'],research_observations=len(values),road_exit_closes=sum(v['road_exit'] for v in values.values()),actions=len(applied),max_ema_absolute_difference=maxema,max_cost_absolute_difference=maxcost))
 csvout(BASE/'observation-checks.csv',rows);csvout(BASE/'action-unit-checks.csv',actionrows);csvout(BASE/'observation-differences.csv',diffs)
 with gzip.open(BASE/'observations-independent.json.gz','wt') as f:json.dump(computed,f)
 result=dict(status='passed' if not diffs else 'failed',observations=len(rows),numeric_values_compared=3*len(rows),boolean_components_compared=3*len(rows),action_events=len(actionrows),tolerance=tol,differences=len(diffs),coverage=coverage,method='40-digit Decimal streaming EMA seeded by first 20 mean, alpha 2/21; only past EMA and last20 closes transformed on each known action date; no imported signal/features/price helper/account engine; all research dates and every component boolean compared')
 save(BASE/'observation-results.json',result);print(json.dumps(result,default=str))
 assert not diffs
if __name__=='__main__':run()
