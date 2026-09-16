from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,sys
import pandas as pd
sys.dont_write_bytecode=True
H=Path(__file__).parent;ROOT=H.parent;I=H/'inputs'
def read(p):return json.load(open(p))
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadmod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def main():
 out=H/'account-results';assert not out.exists(),'preserve prior attempt';out.mkdir()
 pl=read(ROOT/'protocol-lock.json');assert sha(ROOT/'protocol.md')==pl['sha256']
 lock=read(H/'source-lock.json');assert all(sha(p)==v for p,v in lock['files'].items())
 cfg=read(H/'execution-config.json');allc=read(I/'diagnostic-candidates.json');cs=[c for c in allc if c['config_id']=='R1' and c['symbol'] in cfg['symbols']];assert len(cs)==313
 save(out/'candidates.json',cs);save(out/'run-lock.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),'source_lock_sha256':sha(H/'source-lock.json'),'files':lock['files'],'accounts':4,'config':cfg})
 prices={}
 for s in cfg['symbols']:
  rows=pd.read_csv(I/f'bars/{s}-nominal.csv').to_dict('records');prices[s]={r['date']:{k:r[k] for k in ('open','high','low','close','volume')} for r in rows}
 actions=[]
 for a in read(I/'actions.json'):
  if a['symbol'] not in cfg['symbols']:continue
  x=dict(a,ex_date=a['effective_date']);x['cash_per_share' if a['type']=='cash_dividend' else 'ratio']=float(a['cash' if a['type']=='cash_dividend' else 'ratio']);actions.append(x)
 with gzip.open(I/'exit-observations.json.gz','rt') as f:obs=json.load(f)
 engine=loadmod('risk_engine',H/'engine.py');metrics=loadmod('risk_metrics',H/'metrics.py');summaries=[];annual=[]
 for s in cfg['symbols']:
  subset=[c for c in cs if c['symbol']==s]
  for fee in cfg['fees_per_side']:
   tag=str(int(fee*10000));aid=f'{s}-R1-risk1-fee{tag}bp';folder=out/aid;folder.mkdir()
   r=engine.simulate({s:prices[s]},[a for a in actions if a['symbol']==s],subset,{s:obs[s]},start=cfg['start'],end=cfg['end'],initial_per_symbol=100000,weekly_per_symbol=0,fee=fee,config_id='R1',limits={s:cfg['limits'][s]},limit_changes={s:cfg['limit_changes'][s]},blocked_dates={s:cfg['blocked_dates'][s]},risk_sized_config_set={'R1'})
   pd.DataFrame(r['daily']).to_csv(folder/'daily.csv',index=False);pd.DataFrame(r['trades']).to_csv(folder/'trades.csv',index=False)
   for n in ('orders','events','roundtrips'):save(folder/(n+'.json'),r[n])
   m=metrics.summarize(r);m.update(account_id=aid,symbol=s,config_id='R1',method='R1-risk1',fee_per_side=fee,raw_candidates=len(subset),signal_accepted=sum(bool(c['signal_accepted']) for c in subset),sizing_policy='one_percent_prior_equity',exit_policy='ema20_and_cost20_or_structure');summaries.append(m)
   d=pd.DataFrame(r['daily']);d['pnl']=d.equity.diff().fillna(d.equity.iloc[0]-100000)-d.deposit;assert abs(d.pnl.sum()-m['net_gain'])<1e-5
   for y,g in d.groupby(d.date.str[:4]):annual.append({'account_id':aid,'symbol':s,'method':'R1-risk1','fee_per_side':fee,'year':y,'investment_pnl':float(g.pnl.sum()),'ending_equity':float(g.equity.iloc[-1]),'trade_count':sum(t['date'].startswith(y) for t in r['trades'])})
   assert all(sha(p)==v for p,v in lock['files'].items());print(aid,m['last_equity'],m['max_drawdown'],m['buys'],flush=True)
 save(out/'summary.json',summaries);pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False)
 assert all(sha(p)==v for p,v in lock['files'].items());save(out/'completion.json',{'finished_at_utc':datetime.now(timezone.utc).isoformat(),'accounts_completed':4,'all_input_hashes_unchanged':True,'source_lock_sha256_after':sha(H/'source-lock.json')})
if __name__=='__main__':main()
