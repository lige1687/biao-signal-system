"""Fixed synthetic boundary tests; no real assets or historic opportunity generation."""
import argparse,dataclasses,hashlib,importlib,json,sys,traceback
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(P/'research-package/src'))
import pandas as pd
from lei_signal.features.indicators import compute_features
from lei_signal.rules import dense_breakout as db
from lei_signal.backtest import engine as eng
from lei_signal.rules.clock_classifier import clock_series
parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);args=parser.parse_args();OUT=P/args.attempt;OUT.mkdir(exist_ok=False)
def save(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save('before.json',{'time_utc':datetime.now(timezone.utc).isoformat(),'test_sha256':sha(Path(__file__)),'package':{str(p.relative_to(P)):sha(p) for p in (P/'research-package').rglob('*') if p.is_file()}})
results=[]
def check(label,fn):
 try:
  ok,details=fn();results.append({'id':'E%02d'%(len(results)+1),'label':label,'status':'pass' if ok else 'fail','details':details})
 except Exception:results.append({'id':'E%02d'%(len(results)+1),'label':label,'status':'fixture_error','traceback':traceback.format_exc()})
 save('results.json',results)
def age_probe(flags,expected):
 actual=db._state_age_series(pd.Series(flags),exit_bars=20).tolist();return actual==expected,{'actual':actual,'expected':expected}
check('initial False never counts toward consolidation',lambda:age_probe([False]*45+[True,True],[0]*45+[1,2]))
check('20-bar interruption retains existing age',lambda:age_probe([True,True]+[False]*20+[True],list(range(1,24))))
check('21st absent bar resets; no new age until true',lambda:age_probe([True]*3+[False]*24+[True,True],list(range(1,24))+[0]*4+[1,2]))
def full_age():
 ix=pd.bdate_range('2020-01-01',periods=306);b=pd.DataFrame({'open':100.,'high':101.,'low':99.,'close':100.,'volume':1000.},index=ix);f=compute_features(b)
 events=db.detect_dense_breakout_events(f,'SYNTH.SZ');watch=next(e for e in events if e.evidence.get('sub_rule')==db.SUB_RULE_WATCH);pos=ix.get_loc(pd.Timestamp(watch.available_date));c=clock_series(f);n=int((c.iloc[:pos+1]==3).sum());return n==126,{'effective_sideways_bars_at_watch':n,'watch_position':int(pos)}
check('full OHLC first watch requires126 valid sideways bars',full_age)
def frame():
 ix=pd.bdate_range('2020-01-01',periods=306);f=pd.DataFrame({'open':10.,'high':10.2,'low':9.8,'close':10.,'sma20':10.2,'sma60':10.,'close_lag20':9.5},index=ix);return f
def specification(f,target=14.,stop=9.,variant='breakout'):
 return eng.EntrySpec(symbol='SYNTH',signal_date=f.index[300].date(),signal_position=300,entry_ref_price=10.,stop_price=stop,target_price=target,target_source='fixed-synthetic',reward_risk=4.,entry_variant=variant,is_first_touch=False,ma_period=0,clock_type=3,weekly_bull_env=False,event_id='fixed',breakout_reference=10.)
def trade(open_price=10.,target=14.,stop=9.):
 f=frame();f.loc[f.index[301],'open']=open_price;s=specification(f,target,stop)
 t=eng.simulate_trade(f,s,exit_variant=eng.EXIT_STRUCTURE_STOP,fee=eng.FeeModel('none',0.,0.),prepared={'costbasis_cond':pd.Series(False,index=f.index),'top_dates':[]},limit_guard=False)
 return t
for label,op,target,stop,expected in [
 ('exact3 accepted',10.,13.,9.,'open_at_end'),
 ('below3 rejected',10.,12.999,9.,'skipped_actual_reward_risk_below_3'),
 ('missing target rejected',10.,None,9.,'skipped_target_unavailable_at_entry'),
 ('open equal stop rejected as unentered',9.,14.,9.,'skipped_open_at_or_below_stop'),
 ('open below stop rejected as unentered',8.9,14.,9.,'skipped_open_at_or_below_stop'),
 ('NaN open rejected',float('nan'),14.,9.,'skipped_invalid_entry_price'),
 ('infinite target rejected',10.,float('inf'),9.,'skipped_invalid_target_price'),
 ('NaN stop rejected',10.,14.,float('nan'),'skipped_invalid_stop_price'),
 ('target equal open rejected',10.,10.,9.,'skipped_target_not_above_entry'),
]:
 def fn(op=op,target=target,stop=stop,expected=expected):
  t=trade(op,target,stop);ok=t.exit_reason==expected
  if expected.startswith('skipped_'):ok=ok and t.exit_date is None and t.r_net is None
  return ok,{'open':op,'target':target,'stop':stop,'expected':expected,'actual_reason':t.exit_reason,'exit_date':t.exit_date,'r_net':t.r_net,'meta':t.meta}
 check(label,fn)
def helper_matrix():
 try:m=importlib.import_module('lei_signal.backtest.entry_qualification')
 except ModuleNotFoundError:return False,{'expected':'public entry qualification helper','observed':'module missing in original package'}
 out=[]
 for op,target,stop in [(10.,13.,9.),(10.9,14.,9.),(9.,14.,9.),(10.,None,9.),(10.,float('nan'),9.)]:
  q=m.qualify_entry_at_open(open_price=op,target_price=target,stop_price=stop);t=trade(op,target,stop)
  out.append({'helper':dataclasses.asdict(q),'engine':t.exit_reason,'accepted_matches':q.accepted==(t.exit_reason=='open_at_end'),'reason_matches':q.accepted or q.reason==t.exit_reason})
 return all(x['accepted_matches'] and x['reason_matches'] for x in out),out
check('public entry helper and engine reject consistently',helper_matrix)
def b3_matrix():
 fn=getattr(eng,'b3_exit_triggered',None)
 if fn is None:return False,{'expected':'public B3 pure helper','observed':'missing in original package'}
 cases=[('breakout',102.,100.,100.1,100.,101.,False),('ambush',102.,100.,100.1,100.,101.,True),('breakout',99.,100.,98.,100.,101.,True),('breakout',99.,100.,98.,98.,101.,False)]
 out=[]
 for variant,close,s20,s60,lag,ref,expected in cases:
  actual=fn(close=close,sma20=s20,sma60=s60,close_lag20=lag,breakout_reference=ref,entry_variant=variant);out.append({'variant':variant,'actual':actual,'expected':expected})
 return all(x['actual']==x['expected'] for x in out),out
check('public B3 helper preserves dual actions and limits alignment to ambush',b3_matrix)
def at_end():
 f=frame();s=dataclasses.replace(specification(f),signal_position=len(f)-1,signal_date=f.index[-1].date());t=eng.simulate_trade(f,s,exit_variant=eng.EXIT_STRUCTURE_STOP,fee=eng.FeeModel('none',0.,0.),prepared={'costbasis_cond':pd.Series(False,index=f.index),'top_dates':[]});return t.exit_reason=='signal_at_end_not_entered' and t.exit_date is None,{'actual_reason':t.exit_reason}
check('no next bar remains unentered',at_end)
save('after.json',{'time_utc':datetime.now(timezone.utc).isoformat(),'status_counts':{s:sum(r['status']==s for r in results) for s in ['pass','fail','fixture_error']},'cases':len(results)})
print((OUT/'after.json').read_text())
