"""Six frozen-event interval diagnostics; does not call any signal detector."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
P=Path(__file__).resolve().parent;E=P.parents[1]/'research-eighth-2026-09-08';sys.dont_write_bytecode=True;sys.path.insert(0,str(E/'b-research-fix/research-package/src'))
from lei_signal.features.indicators import compute_features
from lei_signal.rules.clock_classifier import clock_series
from lei_signal.rules.dense_breakout import _state_age_series
from lei_signal.domain.rules_config import get_rule
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str,allow_nan=False)+'\n')
m=json.loads((P/'input-manifest.json').read_text());assert all(sha(Path(x['source']))==x['sha256'] for x in m['files'])
write('run-before.json',{'time_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'protocol_sha256':sha(P/'protocol.md'),'clarification_sha256':sha(P/'protocol-clarification-01.md'),'all_inputs_match':True})
old=json.loads((E/'candidate-review/B-six-events.json').read_text());targets=json.loads((E/'candidate-review/selected-target-checks.json').read_text());assert len(old)==6
assert all(x['symbol']=='sh518880' for x in old)
actions=json.loads((E/'product-qualification/actions.json').read_text());assert not any(a['symbol']=='sh518880' for a in actions)
raw=pd.read_csv(E/'product-qualification/bars-helper-native/sh518880-nominal.csv',dtype={'date':str});raw=raw[raw.date<=max(x['date'] for x in old)].copy();raw['date']=pd.to_datetime(raw['date']);raw=raw.set_index('date');frame=compute_features(raw)
clock=clock_series(frame);exit_bars=int(get_rule('dense_breakout').param('zone_exit_bars',20));assert exit_bars==20
age=0;away=0;effective=0;start=None;states=[]
for i,typ in enumerate(clock):
 if int(typ)==3:
  if age==0:start=i;effective=0
  age+=1;away=0;effective+=1
 elif age>0:
  away+=1
  if away>exit_bars:age=away=effective=0;start=None
  else:age+=1
 states.append({'position':i,'date':frame.index[i].date().isoformat(),'clock_type':int(typ),'age':age,'effective_clock3_bars':effective,'temporarily_away_bars':away,'state_start_position':start,'state_start_date':None if start is None else frame.index[start].date().isoformat()})
assert [s['age'] for s in states]==_state_age_series(clock==3,exit_bars=exit_bars).tolist()
rows=[];source_rows=[]
for e in old:
 si=frame.index.get_loc(pd.Timestamp(e['date']));wi=frame.index.get_loc(pd.Timestamp(e['watch_date']));sw,ss=states[wi],states[si]
 assert sw['clock_type']==3 and sw['age']>=126 and sw['state_start_position'] is not None
 lines=frame.iloc[wi][['sma20','sma60','sma120','ema20','ema60','ema120']];assert lines.max()/lines.min()-1<.02
 begin=sw['state_start_position'];current=frame.iloc[wi:si];alt=frame.iloc[begin:si]
 upper,lower=float(current.high.max()),float(current.low.min());altupper,altlower=float(alt.high.max()),float(alt.low.min());close=float(frame.close.iloc[si]);target=next(c for c in targets if c['config_id']=='P3' and c['signal_date']==e['date'])
 assert abs(upper-e['manual_upper'])<1e-12 and abs(lower-e['manual_stop'])<1e-12
 r={'symbol':e['symbol'],'signal_date':e['date'],'event_id':e['event_id'],'qualifying_sideways_start':sw['state_start_date'],'watch_date':e['watch_date'],'watch_age_with_tolerated_absence':sw['age'],'watch_effective_clock3_bars':sw['effective_clock3_bars'],'signal_clock_type':ss['clock_type'],'signal_current_sideways_start':ss['state_start_date'],'signal_current_age_with_absence':ss['age'],'signal_current_effective_clock3_bars':ss['effective_clock3_bars'],'watch_to_yesterday_bars':len(current),'current_upper':upper,'current_lower':lower,'current_stop':lower,'signal_close':close,'current_price_risk':close-lower,'current_price_risk_pct':(close-lower)/close*100,'fixed_target':target['target'],'current_signal_reward_risk':target['signal_rr'],'current_signal_rr_ge3':target['signal_accepted'],'alternative_interval_start':sw['state_start_date'],'alternative_to_yesterday_bars':len(alt),'alternative_upper':altupper,'alternative_lower':altlower,'alternative_price_risk':close-altlower,'lower_difference':altlower-lower,'upper_difference':altupper-upper,'old_close_above_alternative_upper':close>altupper,'new_signals_generated':False}
 rows.append(r)
 needed=set(range(max(0,wi-3),min(si+1,wi+4)))|set(range(max(wi,si-2),si+1))
 for i in sorted(needed):source_rows.append({'event_date':e['date'],**states[i],**{k:float(frame[k].iloc[i]) for k in ['open','high','low','close','sma20','sma60','sma120','ema20','ema60','ema120']}})
write('six-events.json',rows);pd.DataFrame(rows).to_csv(P/'six-events.csv',index=False);write('state-observations.json',source_rows)
# The minimum counterexample is one existing event, with all original numbers intact.
example=next(x for x in rows if x['signal_date']=='2018-11-22')
write('minimal-existing-counterexample.json',{'example':example,'meaning':'已横盘足够久只负责watch资格；新watch当日独立初始化区间。此旧信号只突破新watch的1根上沿，不能解释为突破该资格横盘寿命段的整个箱体。','not_a_new_signal':True,'alternative_is_not_new_strategy_run':True})
sourcebad=[x['source'] for x in m['files'] if sha(Path(x['source']))!=x['sha256']]
summary={'time_utc':datetime.now(timezone.utc).isoformat(),'fixed_existing_events':6,'current_intervals_all_match_eighth':True,'age_trace_matches_frozen_research_helper':True,'one_bar_current_intervals':sum(r['watch_to_yesterday_bars']==1 for r in rows),'old_dates_still_above_single_alternative_upper':sum(r['old_close_above_alternative_upper'] for r in rows),'alternative_definitions':1,'new_signal_generation_runs':0,'return_runs':0,'source_changes':sourcebad}
write('summary.json',summary);print(json.dumps({'summary':summary,'rows':rows},ensure_ascii=False))
