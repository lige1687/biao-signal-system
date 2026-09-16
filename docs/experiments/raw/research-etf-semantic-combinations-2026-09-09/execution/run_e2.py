from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,sys
import pandas as pd
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;OUT=H/'attempt-e2'
def mod(n,p):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
base=mod('semantic_base',H/'run.py')
def e2_rule():
 seen_green={}
 def rule(position,obs,close):
  pid=position['position_id'];seen_green.setdefault(pid,False)
  target=position.get('target')
  if base.finite(target) and close>=target:return 'known_target_reached'
  ema,cost=obs.get('ema20'),obs.get('cost20')
  if not base.finite(ema) or not base.finite(cost):raise ValueError('missing color fields')
  if close>ema and close>cost:seen_green[pid]=True;return None
  if seen_green[pid] and close<ema and close<cost:return 'black_after_post_entry_green'
  return None
 return rule
def simulate(engine,cfg,prices,actions,obs,sym,cands,fee,config):
 return engine.simulate({sym:prices[sym]},[a for a in actions if a['symbol']==sym],base.prepare(cands,config),{sym:obs[sym]},start='2015-01-01',end='2026-06-30',initial_per_symbol=100000,weekly_per_symbol=0,fee=fee,config_id=config,limits={sym:cfg['limits'][sym]},limit_changes={sym:cfg['limit_changes'][sym]},blocked_dates={sym:cfg['blocked_dates'][sym]},exit_rule=e2_rule(),explicit_config_set={config})
def main():
 assert not OUT.exists();OUT.mkdir();lock=base.read(H/'e2-code-lock.json');assert base.sha(H/'run_e2.py')==lock['run'];assert base.sha(H/'test_e2.py')==lock['test']
 for p,d in base.read(H/'source-lock.json')['files'].items():assert base.sha(H/p)==d
 assert base.sha(H.parent/'exit-semantics-addendum.md')==lock['addendum']
 cfg,prices,actions,obs,candidates=base.load();engine=mod('e2_engine',H/'engine.py');metrics=mod('e2_metrics',H/'metrics.py');summ=[]
 for group in ('G0','GP','GQ','GPQ'):
  for sym in ('sh510300','sz159915'):
   cs=[x for x in candidates if x['symbol']==sym and base.selected(x,group)]
   for fee in (.001,.002):
    config=f'SC-{group}-E2';r=simulate(engine,cfg,prices,actions,obs,sym,cs,fee,config);aid=f'{sym}-{group}-E2-fee{int(fee*10000):02d}bp';base.write_result(OUT/'accounts'/aid,r);m=metrics.summarize(r);m.update(account_id=aid,group=group,exit='E2',symbol=sym,fee=fee,candidates=len(cs),accepted=sum(x['signal_accepted'] for x in cs));summ.append(m)
 base.save(OUT/'summary.json',summ);pd.DataFrame(summ).to_csv(OUT/'summary.csv',index=False);fixed=[]
 for c in [x for x in candidates if x['signal_accepted']]:
  for fee in (.001,.002):
   config='FX-E2';r=simulate(engine,cfg,prices,actions,obs,c['symbol'],[c],fee,config);pid=f"{c['candidate_id'].replace(':','_')}-E2-fee{int(fee*10000):02d}bp";base.write_result(OUT/'fixed-opportunities'/pid,r);rt=r['roundtrips'][0] if r['roundtrips'] else None;fixed.append({'path_id':pid,'candidate_id':c['candidate_id'],'symbol':c['symbol'],'groups':[g for g in ('G0','GP','GQ','GPQ') if base.selected(c,g)],'exit_variant':'E2','fee':fee,'signal_date':c['signal_date'],'entered':bool(rt),'entry_date':rt.get('entry_date') if rt else None,'exit_date':rt.get('exit_date') if rt else None,'net_return':rt.get('net_return') if rt else None})
 base.save(OUT/'fixed-summary.json',fixed);base.save(OUT/'completion.json',{'accounts':16,'fixed_paths':len(fixed),'finished_at':datetime.now(timezone.utc).isoformat(),'post_result_diagnostic':True})
if __name__=='__main__':main()
