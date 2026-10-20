"""Two preregistered diagnostic references; original candidates remain unedited."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import json, gzip, hashlib, importlib.util, io, copy
from datetime import datetime, timezone
import pandas as pd
P=Path(__file__).resolve().parent
E=P.parent/'research-eighth-2026-09-08'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def load_inputs():
 settings=read(E/'product-qualification/execution-parameters.json')
 prices={}
 for s in settings['symbols']:
  rows=pd.read_csv(Path(settings['prices_directory'])/f'{s}-nominal.csv').to_dict('records')
  prices[s]={r['date']:{k:r[k] for k in ('open','high','low','close','volume')} for r in rows}
 actions=[]
 for a in read(Path(settings['actions_file'])):
  e=dict(a,ex_date=a['effective_date'])
  if a['type']=='cash_dividend':e['cash_per_share']=float(a['cash'])
  else:e['ratio']=float(a['ratio'])
  actions.append(e)
 with gzip.open(E/'candidate-study/candidates.json.gz','rt') as f:candidates=json.load(f)
 with gzip.open(E/'candidate-study/exit-observations.json.gz','rt') as f:obs=json.load(f)
 return settings,prices,actions,candidates,obs

def main():
 out=P/'account-results';assert not out.exists(),'Preserve previous run'
 assert sha(P/'protocol.md')==read(P/'protocol-lock.json')['sha256']
 out.mkdir()
 settings,prices,actions,candidates,obs=load_inputs()
 files=[Path(__file__),P/'reference-engine/engine.py',P/'protocol.md',E/'spark-metrics/metrics.py',E/'product-qualification/execution-parameters.json',Path(settings['actions_file']),E/'candidate-study/candidates.json.gz',E/'candidate-study/exit-observations.json.gz']
 files+=list(Path(settings['prices_directory']).glob('*.csv'))
 for f,h in read(E/'account-results/run-lock.json')['files'].items():assert sha(Path(f))==h,('original changed',f)
 lock=dict(started_at_utc=datetime.now(timezone.utc).isoformat(),configs=['R0','R1'],files={str(f):sha(f) for f in files},settings=settings,start='2015-01-01',end='2026-06-30',weekly_per_symbol=250,fee_per_side=.001,cash_interest=0,diagnostic_reference_only=True)
 save(out/'run-lock.json',lock)
 engine=module('diagnostic_engine',P/'reference-engine/engine.py')
 metrics=module('frozen_eighth_metrics',E/'spark-metrics/metrics.py')
 def simulate(cfg,cs):return engine.simulate(prices,actions,cs,obs,start=lock['start'],end=lock['end'],weekly_per_symbol=250,fee=.001,config_id=cfg,limits=settings['limits'],limit_changes=settings['limit_changes'],blocked_dates=settings['blocked_dates'])
 # Compare serialization exactly, not only endpoint summaries. No sealed files written.
 regression=[]
 for cfg in ['P0','P5','P6']:
  r=simulate(cfg,[c for c in candidates if c['config_id']==cfg])
  for name in ['daily','trades','orders','events','roundtrips']:
   if name in ('daily','trades'):
    actual=pd.DataFrame(r[name]).to_csv(index=False);expected=(E/'account-results'/cfg/(name+'.csv')).read_text()
    matched=actual==expected
   else:matched=r[name]==read(E/'account-results'/cfg/(name+'.json'))
   regression.append(dict(config_id=cfg,table=name,exact_match=matched));assert matched,(cfg,name,'old regression')
 save(out/'original-regression.json',regression)
 allcs=[];summaries=[];annual=[];products=[]
 for cfg,source in [('R0','P0'),('R1','P5')]:
  cs=[]
  for original in candidates:
   if original['config_id']!=source:continue
   c=copy.deepcopy(original);c.update(config_id=cfg,source_config_id=source,source_candidate_id=original['candidate_id'],candidate_id=cfg+original['candidate_id'][len(source):],diagnostic_reference_only=True)
   cs.append(c)
  allcs+=cs
  r=simulate(cfg,cs);folder=out/cfg;folder.mkdir()
  for name in ['daily','trades']:pd.DataFrame(r[name]).to_csv(folder/(name+'.csv'),index=False)
  for name in ['orders','events','roundtrips']:save(folder/(name+'.json'),r[name])
  m=metrics.summarize(r);m.update(config_id=cfg,source_config_id=source,raw_candidates=len(cs),originally_accepted=sum(c['signal_accepted'] for c in cs),diagnostic_reference_only=True);summaries.append(m)
  df=pd.DataFrame(r['daily']);df['pnl']=df.equity.diff().fillna(df.equity.iloc[0])-df.deposit
  assert abs(df.pnl.sum()-m['net_gain'])<1e-6
  for year,g in df.groupby(df.date.str[:4]):annual.append(dict(config_id=cfg,year=year,investment_pnl=float(g.pnl.sum()),ending_equity=float(g.equity.iloc[-1]),trade_count=sum(t['date'].startswith(year) for t in r['trades'])))
  for s in settings['symbols']:
   final=r['daily'][-1];products.append(dict(config_id=cfg,symbol=s,ending_equity=final['equity_'+s],funding=final['funding_'+s],net_gain=final['equity_'+s]-final['funding_'+s],fees=final['fees_'+s],buy_count=sum(t['side']=='buy' and t['symbol']==s for t in r['trades']),open_shares=final['units_'+s]))
  assert all(sha(Path(f))==h for f,h in lock['files'].items())
  print(cfg,'complete',m['last_equity'],m['max_drawdown'],m['buys'],flush=True)
 save(out/'candidates.json',allcs)
 pd.DataFrame(allcs).to_csv(out/'candidates.csv',index=False)
 save(out/'summary.json',summaries)
 pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
 pd.DataFrame(annual).to_csv(out/'annual-contributions.csv',index=False)
 pd.DataFrame(products).to_csv(out/'product-contributions.csv',index=False)
 old={x['config_id']:x for x in read(E/'account-results/summary.json')}
 save(out/'paired-comparisons.json',[dict(diagnostic=x['config_id'],original=x['source_config_id'],**{k:x[k]-old[x['source_config_id']][k] for k in ['last_equity','net_gain','max_drawdown','buys','fees','mean_exposure']}) for x in summaries])
 save(out/'completion.json',dict(finished_at_utc=datetime.now(timezone.utc).isoformat(),configs_completed=['R0','R1'],original_tables_exact_match=len(regression),all_input_hashes_unchanged=True))
if __name__=='__main__':main()
