from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,math,sys
import pandas as pd
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;IN=HERE/'inputs';OUT=HERE/'attempt-01'
def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def exit_rule(kind):
 def rule(position,obs,close):
  target=position.get('target')
  if finite(target) and close>=target:return 'known_target_reached'
  if kind=='E1':
   ema,cost=obs.get('ema20'),obs.get('cost20')
   if not finite(ema) or not finite(cost):raise ValueError('missing black-state fields')
   if close<ema and close<cost:return 'black_after_entry'
  return None
 return rule
def load_conditions():
 raw=read(HERE/'conditions.json');rows=raw.get('rows',raw.get('candidates',raw)) if isinstance(raw,dict) else raw
 if isinstance(rows,dict):rows=[dict(v,candidate_id=k) for k,v in rows.items()]
 return {x['candidate_id']:x for x in rows}
def load():
 cfg=read(IN/'execution-config.json');prices={}
 for sym in ('sh510300','sz159915'):
  rows=pd.read_csv(IN/f'bars/{sym}-nominal.csv').to_dict('records');prices[sym]={r['date']:{k:r[k] for k in ('open','high','low','close','volume')} for r in rows}
 actions=[]
 for a in read(IN/'actions.json'):
  if a['symbol'] not in prices:continue
  x=dict(a,ex_date=a['effective_date']);x['cash_per_share' if a['type']=='cash_dividend' else 'ratio']=float(a['cash'] if a['type']=='cash_dividend' else a['ratio']);actions.append(x)
 with gzip.open(IN/'exit-observations.json.gz','rt') as f:obs=json.load(f)
 with gzip.open(IN/'source-candidates/precision-candidates.json.gz','rt') as f:allc=json.load(f)
 c=[x for x in allc if x['config_id']=='C1' and x['symbol'] in prices];assert len(c)==84
 cond=load_conditions();assert set(x['candidate_id'] for x in c)==set(cond)
 for x in c:
  row=cond[x['candidate_id']];p=row.get('position_p',row.get('P'));q=row.get('direction_q',row.get('Q'))
  assert p in (True,False,None,'unknown') and q in (True,False,None,'unknown'),x['candidate_id']
  x.update(condition_P=None if p=='unknown' else p,condition_Q=None if q=='unknown' else q,condition_detail=row)
 return cfg,prices,actions,obs,c
def selected(c,group):
 if group=='G0':return True
 if group=='GP':return c['condition_P'] is True
 if group=='GQ':return c['condition_Q'] is True
 return c['condition_P'] is True and c['condition_Q'] is True
def prepare(c,config):
 out=[]
 for x in c:
  y=dict(x);y['source_config_id']='C1';y['config_id']=config;out.append(y)
 return out
def write_result(folder,r):
 folder.mkdir(parents=True)
 for n in ('daily','trades'):pd.DataFrame(r[n]).to_csv(folder/f'{n}.csv',index=False)
 for n in ('orders','events','roundtrips'):save(folder/f'{n}.json',r[n])
def simulate(engine,cfg,prices,actions,obs,sym,cands,fee,config,exit_kind):
 return engine.simulate({sym:prices[sym]},[a for a in actions if a['symbol']==sym],prepare(cands,config),{sym:obs[sym]},start='2015-01-01',end='2026-06-30',initial_per_symbol=100000,weekly_per_symbol=0,fee=fee,config_id=config,limits={sym:cfg['limits'][sym]},limit_changes={sym:cfg['limit_changes'][sym]},blocked_dates={sym:cfg['blocked_dates'][sym]},exit_rule=exit_rule(exit_kind),explicit_config_set={config})
def main():
 assert not OUT.exists(),'preserve first results';OUT.mkdir()
 locks=read(HERE/'source-lock.json');
 for p,h in locks['files'].items():assert sha(HERE/p)==h,p
 code=read(HERE/'code-lock.json');assert sha(HERE/'run.py')==code['run'];assert sha(HERE/'test_runner.py')==code['test']
 cfg,prices,actions,obs,candidates=load();engine=module('semantic_engine',HERE/'engine.py');metrics=module('semantic_metrics',HERE/'metrics.py')
 save(OUT/'run-lock.json',{'at':datetime.now(timezone.utc).isoformat(),'source_lock':sha(HERE/'source-lock.json'),'code_lock':sha(HERE/'code-lock.json'),'c1':84})
 summaries=[];membership=[]
 for group in ('G0','GP','GQ','GPQ'):
  for exit_kind in ('E0','E1'):
   config=f'SC-{group}-{exit_kind}'
   for sym in ('sh510300','sz159915'):
    cs=[x for x in candidates if x['symbol']==sym and selected(x,group)]
    membership.append({'group':group,'exit':exit_kind,'symbol':sym,'candidates':len(cs),'accepted':sum(x['signal_accepted'] for x in cs)})
    for fee in (.001,.002):
     r=simulate(engine,cfg,prices,actions,obs,sym,cs,fee,config,exit_kind);aid=f'{sym}-{group}-{exit_kind}-fee{int(fee*10000):02d}bp';write_result(OUT/'accounts'/aid,r)
     m=metrics.summarize(r);m.update(account_id=aid,group=group,exit=exit_kind,symbol=sym,fee=fee,candidates=len(cs),accepted=sum(x['signal_accepted'] for x in cs));summaries.append(m)
 save(OUT/'summary.json',summaries);save(OUT/'membership.json',membership);pd.DataFrame(summaries).to_csv(OUT/'summary.csv',index=False)
 qualified=[x for x in candidates if x['signal_accepted']]
 fixed=[]
 for c in qualified:
  for exit_kind in ('E0','E1'):
   for fee in (.001,.002):
    config=f'FX-{exit_kind}';r=simulate(engine,cfg,prices,actions,obs,c['symbol'],[c],fee,config,exit_kind);pid=f"{c['candidate_id'].replace(':','_')}-{exit_kind}-fee{int(fee*10000):02d}bp";write_result(OUT/'fixed-opportunities'/pid,r);rt=r['roundtrips'][0] if r['roundtrips'] else None
    fixed.append({'path_id':pid,'candidate_id':c['candidate_id'],'symbol':c['symbol'],'groups':[g for g in ('G0','GP','GQ','GPQ') if selected(c,g)],'exit_variant':exit_kind,'fee':fee,'signal_date':c['signal_date'],'entered':bool(rt),'entry_date':rt.get('entry_date') if rt else None,'exit_date':rt.get('exit_date') if rt else None,'net_return':rt.get('net_return') if rt else None,'trades':len(r['trades']),'positions':len(r['roundtrips']),'final_equity':r['daily'][-1]['equity'],'condition_detail':c['condition_detail'],'target':c.get('target'),'target_source':c.get('target_source'),'target_confirmed_at':c.get('target_confirmed_at')})
 save(OUT/'fixed-summary.json',fixed)
 for p,h in locks['files'].items():assert sha(HERE/p)==h,p
 assert sha(HERE/'run.py')==code['run'] and sha(HERE/'test_runner.py')==code['test']
 save(OUT/'completion.json',{'accounts':32,'qualified_candidates':len(qualified),'fixed_paths':len(fixed),'finished_at':datetime.now(timezone.utc).isoformat(),'locks_unchanged':True})
if __name__=='__main__':main()
