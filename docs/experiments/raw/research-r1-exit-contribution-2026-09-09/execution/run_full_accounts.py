from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,sys
import pandas as pd
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; INPUT=HERE/'inputs'; OLD=HERE.parent.parent/'research-broad-etf-technical-2026-09-08/execution'
def read(p): return json.loads(Path(p).read_text())
def save(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def structure_only(position,observations,close): return None
def load():
 cfg=read(INPUT/'execution-config.json'); prices={}
 for sym in cfg['symbols']:
  rows=pd.read_csv(INPUT/f'bars/{sym}-nominal.csv').to_dict('records');prices[sym]={r['date']:{k:r[k] for k in ('open','high','low','close','volume')} for r in rows}
 actions=[]
 for a in read(INPUT/'actions.json'):
  if a['symbol'] not in cfg['symbols']: continue
  x=dict(a,ex_date=a['effective_date']);x['cash_per_share' if a['type']=='cash_dividend' else 'ratio']=float(a['cash'] if a['type']=='cash_dividend' else a['ratio']);actions.append(x)
 with gzip.open(INPUT/'exit-observations.json.gz','rt') as f: obs=json.load(f)
 candidates=[c for c in read(INPUT/'source-candidates/diagnostic-candidates.json') if c['config_id']=='R1']
 return cfg,prices,actions,obs,candidates
def write_result(folder,r):
 folder.mkdir()
 for n in ('daily','trades'): pd.DataFrame(r[n]).to_csv(folder/f'{n}.csv',index=False)
 for n in ('orders','events','roundtrips'): save(folder/f'{n}.json',r[n])
def main():
 out=HERE/'attempt-01';assert not out.exists();out.mkdir()
 lock=read(HERE/'source-lock.json')
 for p,h in lock['files'].items(): assert sha(HERE/p)==h,p
 code=read(HERE/'code-lock.json');assert sha(HERE/'run_full_accounts.py')==code['runner'];assert sha(HERE/'config.json')==code['config']
 cfg,prices,actions,obs,candidates=load();engine=module('r1_engine',HERE/'engine.py');metrics=module('r1_metrics',HERE/'metrics.py')
 save(out/'run-lock.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'source_lock':sha(HERE/'source-lock.json'),'code_lock':sha(HERE/'code-lock.json')})
 summaries=[]
 for sym in cfg['symbols']:
  cs=[c for c in candidates if c['symbol']==sym]
  for fee in (.001,.002):
   r=engine.simulate({sym:prices[sym]},[a for a in actions if a['symbol']==sym],cs,{sym:obs[sym]},start=cfg['start'],end=cfg['end'],initial_per_symbol=100000,weekly_per_symbol=0,fee=fee,config_id='R1',limits={sym:cfg['limits'][sym]},limit_changes={sym:cfg['limit_changes'][sym]},blocked_dates={sym:cfg['blocked_dates'][sym]},exit_rule=structure_only)
   aid=f'{sym}-R1-structure-only-fee{int(fee*10000):02d}bp';write_result(out/aid,r);m=metrics.summarize(r);m.update(account_id=aid,symbol=sym,method='R1-structure-only',fee_per_side=fee);summaries.append(m)
 save(out/'summary.json',summaries);pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
 save(out/'completion.json',{'accounts':4,'finished_at_utc':datetime.now(timezone.utc).isoformat()})
 # Final-engine regression for the two old main-fee R1 accounts, all five files.
 reg=[]
 for sym in cfg['symbols']:
  cs=[c for c in candidates if c['symbol']==sym]
  r=engine.simulate({sym:prices[sym]},[a for a in actions if a['symbol']==sym],cs,{sym:obs[sym]},start=cfg['start'],end=cfg['end'],initial_per_symbol=100000,weekly_per_symbol=0,fee=.001,config_id='R1',limits={sym:cfg['limits'][sym]},limit_changes={sym:cfg['limit_changes'][sym]},blocked_dates={sym:cfg['blocked_dates'][sym]})
  tmp=out/f'_reg-{sym}';write_result(tmp,r);old=OLD/'account-results'/f'{sym}-R1-fee10bp'
  for n in ('daily.csv','trades.csv','orders.json','events.json','roundtrips.json'): reg.append({'symbol':sym,'file':n,'identical':(tmp/n).read_bytes()==(old/n).read_bytes()})
 assert all(x['identical'] for x in reg);save(out/'old-r1-regression.json',reg)
if __name__=='__main__':main()
