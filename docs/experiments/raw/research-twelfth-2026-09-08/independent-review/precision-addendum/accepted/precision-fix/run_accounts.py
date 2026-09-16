"""Twelve predeclared daily-proxy accounts; source provenance and empty groups retained."""
from pathlib import Path
import sys,importlib.util,json,gzip,hashlib
from datetime import datetime,timezone
import pandas as pd
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent.parent;E=P.parent/'research-eighth-2026-09-08'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def structure_only(position,observations,close):
 # Engine checks close < action-adjusted initial stop first. No added exit.
 return None

def main():
 out=P/'precision-account-results';assert not out.exists(),'preserve every prior attempt';out.mkdir()
 assert sha(P/'protocol.md')==read(P/'initial-lock.json')['protocol_sha256']
 settings=read(E/'product-qualification/execution-parameters.json');configurations=read(P/'configurations.json')
 prices={}
 for s in settings['symbols']:
  rows=pd.read_csv(Path(settings['prices_directory'])/f'{s}-nominal.csv').to_dict('records')
  prices[s]={r['date']:{k:r[k] for k in ('open','high','low','close','volume')} for r in rows}
 actions=[]
 for a in read(Path(settings['actions_file'])):
  item=dict(a,ex_date=a['effective_date'])
  if a['type']=='cash_dividend':item['cash_per_share']=float(a['cash'])
  else:item['ratio']=float(a['ratio'])
  actions.append(item)
 with gzip.open(P/'precision-fix/candidates.json.gz','rt') as f:candidates=json.load(f)
 assert len({c['candidate_id'] for c in candidates})==len(candidates)
 assert set(c['config_id'] for c in candidates)<=set(c['id'] for c in configurations)
 files=[Path(__file__),P/'protocol.md',P/'configurations.json',P/'initial-lock.json',P/'precision-fix/engine.py',P/'precision-fix/candidates.json.gz',P/'adapter/run-lock.json',P/'adapter/completion.json',E/'spark-metrics/metrics.py',E/'product-qualification/execution-parameters.json',Path(settings['actions_file'])]+list(Path(settings['prices_directory']).glob('*.csv'))
 files += [P/'precision-fix/protocol.md',P/'precision-fix/correct_candidates.py',P/'precision-fix/candidate-lock.json',P/'precision-fix/candidate-completion.json',P/'precision-fix/candidate-differences.json',P/'adapter/candidate-review-summary.json',P/'adapter/candidate-review-lock.json',P/'adapter/candidate-review-completion.json',P/'cash-engine/root-new-config-tests.txt',P/'cash-engine/root-old-tests.txt',P/'cash-engine/root-old-real-tables.txt']
 assert read(P/'adapter/candidate-review-summary.json')['all_fields_matched']==891
 for p,h in read(P/'precision-fix/candidate-lock.json')['files'].items():assert sha(Path(p))==h,p
 for p,h in read(P/'adapter/run-lock.json')['files'].items():assert sha(Path(p))==h,p
 for p,h in read(P/'adapter/candidate-review-lock.json')['files'].items():assert sha(Path(p))==h,p
 lock=dict(started_at_utc=datetime.now(timezone.utc).isoformat(),files={str(f.resolve()):sha(f) for f in files},settings=settings,configs=[c['id'] for c in configurations],start='2015-01-01',end='2026-06-30',weekly_per_symbol=250,fee_per_side=.001,risk_fraction_of_prior_product_equity=.01,exit_policy='initial_structure_stop_only',full_strategy_qualified=False)
 save(out/'run-lock.json',lock);save(out/'candidates.json',candidates)
 engine=module('phase12_cash_engine',P/'precision-fix/engine.py');metrics=module('phase12_frozen_metrics',E/'spark-metrics/metrics.py')
 summaries=[];products=[];annual=[];outcomes=[];firstsplit=[]
 for config in configurations:
  cfg=config['id'];cs=[c for c in candidates if c['config_id']==cfg]
  r=engine.simulate(prices,actions,cs,{},start=lock['start'],end=lock['end'],weekly_per_symbol=250,fee=.001,config_id=cfg,limits=settings['limits'],limit_changes=settings['limit_changes'],blocked_dates=settings['blocked_dates'],exit_rule=structure_only,explicit_config_set={c['id'] for c in configurations})
  folder=out/cfg;folder.mkdir()
  for name in ['daily','trades']:
   if r[name]:pd.DataFrame(r[name]).to_csv(folder/(name+'.csv'),index=False)
   else:pd.DataFrame(columns=['date','config_id','symbol','side','shares','price','notional','fee','reason','order_id','position_id','candidate_id']).to_csv(folder/(name+'.csv'),index=False)
  for name in ['orders','events','roundtrips']:save(folder/(name+'.json'),r[name])
  m=metrics.summarize(r);m.update(config_id=cfg,module=config['module'],raw_candidates=len(cs),signal_accepted=sum(c['signal_accepted'] for c in cs),full_strategy_qualified=False);summaries.append(m)
  df=pd.DataFrame(r['daily']);df['pnl']=df.equity.diff().fillna(df.equity.iloc[0])-df.deposit
  assert abs(float(df.pnl.sum())-m['net_gain'])<1e-6
  for yr,g in df.groupby(df.date.str[:4]):annual.append(dict(config_id=cfg,year=yr,investment_pnl=float(g.pnl.sum()),ending_equity=float(g.equity.iloc[-1]),trade_count=sum(t['date'].startswith(yr) for t in r['trades'])))
  for s in settings['symbols']:
   f=r['daily'][-1];products.append(dict(config_id=cfg,symbol=s,ending_equity=f['equity_'+s],funding=f['funding_'+s],net_gain=f['equity_'+s]-f['funding_'+s],fees=f['fees_'+s],buys=sum(t['side']=='buy' and t['symbol']==s for t in r['trades']),open_shares=f['units_'+s]))
  orders={o['candidate_id']:o for o in r['orders'] if o['side']=='buy'};assert len(orders)==len(cs)
  for c in cs:
   o=orders[c['candidate_id']];outcomes.append(dict(config_id=cfg,candidate_id=c['candidate_id'],symbol=c['symbol'],signal_date=c['signal_date'],signal_accepted=c['signal_accepted'],signal_reject_reason=c['signal_reject_reason'],status=o['status'],order_reason=o['reason'],position_id=o.get('position_id')))
  if config['module']=='A':
   cmap={c['candidate_id']:c for c in cs}
   for isfirst in [True,False]:
    subset=[c for c in cs if c.get('source_event',{}).get('evidence',{}).get('is_first_touch') is isfirst]
    ids={c['candidate_id'] for c in subset};trips=[t for t in r['roundtrips'] if t['candidate_id'] in ids]
    firstsplit.append(dict(config_id=cfg,is_first_touch=isfirst,candidates=len(subset),filled_positions=len(trips),closed=sum(t['closed'] for t in trips),open=sum(not t['closed'] for t in trips),position_pnl_sum=sum(t['net_pnl'] for t in trips),note='conditional decomposition within same evolving account; not a separate portfolio or causal effect'))
  for f,h in lock['files'].items():assert sha(Path(f))==h,f
  save(out/'progress.json',dict(completed=len(summaries),total=12,latest=cfg))
  print(cfg,'complete',m['last_equity'],m['max_drawdown'],m['buys'],flush=True)
 save(out/'summary.json',summaries);pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
 for name,rows in [('annual-contributions',annual),('product-contributions',products),('candidate-outcomes',outcomes),('a-first-touch-contributions',firstsplit)]:pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
 save(out/'completion.json',dict(finished_at_utc=datetime.now(timezone.utc).isoformat(),configs_completed=lock['configs'],all_input_hashes_unchanged=True,full_strategy_qualified=False))
if __name__=='__main__':main()
