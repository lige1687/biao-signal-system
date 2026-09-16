"""Independent holding-difference accounting review; no controller imports."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[4]; B=HERE.parent
OLD=ROOT/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09'; COMP=B/'comparison'
PAIR_FRAME=pd.read_csv(COMP/'holding-difference-attribution.csv')[['candidate','benchmark']].drop_duplicates()
PAIRS=PAIR_FRAME[PAIR_FRAME.benchmark.str.contains('-P50-')].itertuples(index=False,name=None)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def locate(a):
 fee=a.rsplit('-',1)[1];return (B/'execution/results' if '-P50-' in a else OLD/'results')/f'fee-{fee}'
def account(a):
 base=locate(a);d=pd.read_parquet(base/f'{a}-daily.parquet');d.date=pd.to_datetime(d.date);d=d.set_index('date');t=pd.read_csv(base/f'{a}-trades.csv');t.date=pd.to_datetime(t.date)
 sym=a[:6];pre='sh' if sym.startswith('5') else 'sz';bars=pd.read_csv(ROOT/f'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/bars/{pre}{sym}-nominal.csv');bars.date=pd.to_datetime(bars.date);bars=bars.set_index('date')
 signed=t.qty*np.where(t.side.eq('buy'),1,-1);qty=pd.Series(signed.values,index=t.date).groupby(level=0).sum().reindex(d.index,fill_value=0);fees=pd.Series(t.fee.values,index=t.date).groupby(level=0).sum().reindex(d.index,fill_value=0)
 pre_units=d.units-qty;prev_units=d.units.shift(1,fill_value=0);prev_mark=d.mark.shift(1,fill_value=0);op=bars.open.reindex(d.index);quote=d.is_quote_day.astype(bool)
 overnight=(pre_units*op-prev_units*prev_mark).where(quote,0.);intraday=(d.units*(d.mark-op)).where(quote,d.units*d.mark-prev_units*prev_mark)
 dividends=d.receivable.diff().fillna(d.receivable.iloc[0])+d.dividends_received.diff().fillna(d.dividends_received.iloc[0]);delta=d.equity.diff().fillna(d.equity.iloc[0]-1e6)
 z=pd.DataFrame({'overnight':overnight,'intraday':intraday,'dividends':dividends,'fees':-fees,'pre_units':pre_units,'post_units':d.units,'delta':delta})
 return d,z,float((z.overnight+z.intraday+z.dividends+z.fees-z.delta).abs().max())

def intervals(s):
 peak=1.;peakday=s.index[0]-pd.Timedelta(days=1);active=None;done=[]
 for day,v in s.items():
  if v>=peak:
   if active is not None:active.update(recovery=str(day.date()),days=(day-active['peak_ts']).days,unrecovered=False);done.append(active);active=None
   peak=v;peakday=day
  else:
   dd=v/peak-1
   if active is None:active={'peak_ts':peakday,'peak_date':str(peakday.date()),'worst_relative_drawdown':dd,'trough':str(day.date())}
   elif dd<active['worst_relative_drawdown']:active.update(worst_relative_drawdown=dd,trough=str(day.date()))
 if active is not None:active.update(recovery=None,days=(s.index[-1]-active['peak_ts']).days,unrecovered=True);done.append(active)
 return done

def main():
 reported=pd.read_parquet(COMP/'holding-difference-daily.parquet');reported.date=pd.to_datetime(reported.date);ph=pd.read_csv(COMP/'holding-difference-phases.csv');attr=pd.read_csv(COMP/'holding-difference-attribution.csv');rd=pd.read_csv(COMP/'relative-daily.csv');rd.date=pd.to_datetime(rd.date);rs=pd.read_csv(COMP/'relative-summary.csv')
 files=[COMP/'holding-difference-daily.parquet',COMP/'holding-difference-phases.csv',COMP/'holding-difference-attribution.csv',COMP/'relative-daily.csv',COMP/'relative-summary.csv',B/'controller/relative_and_attribution.py',B/'protocol.md',ROOT/'docs/research/experiment-backtest-principles.md',ROOT/'docs/research/definition-standard.md'];before={str(p):sha(p) for p in files}
 failures=[];checks=[];phase_check=[];relative_checks=[]
 for cand,bench in PAIRS:
  da,a,ea=account(cand);db,b,eb=account(bench);assert da.index.equals(db.index)
  calc=[]
  for component,unitcol in [('overnight','pre_units'),('intraday','post_units')]:
   groups=np.select([(a[unitcol]>0)&(b[unitcol]>0),(a[unitcol]>0)&(b[unitcol]==0),(a[unitcol]==0)&(b[unitcol]>0)],['both_hold','only_width','only_price'],default='both_cash')
   calc.append(pd.DataFrame({'date':a.index,'component':component,'holding_group':groups,'candidate_pnl':a[component].values,'benchmark_pnl':b[component].values,'difference':(a[component]-b[component]).values}))
  for c in ('dividends','fees'):calc.append(pd.DataFrame({'date':a.index,'component':c,'holding_group':'separate','candidate_pnl':a[c].values,'benchmark_pnl':b[c].values,'difference':(a[c]-b[c]).values}))
  calc=pd.concat(calc,ignore_index=True);calc['candidate']=cand;calc['benchmark']=bench
  rr=reported[(reported.candidate==cand)&(reported.benchmark==bench)];m=calc.merge(rr,on=['date','candidate','benchmark','component','holding_group'],suffixes=('_calc','_reported'))
  md=max((m[c+'_calc']-m[c+'_reported']).abs().max() for c in ('candidate_pnl','benchmark_pnl','difference'))
  total=calc.difference.sum();expected=da.equity.iloc[-1]-db.equity.iloc[-1];recon=total-expected
  if len(m)!=len(calc) or len(m)!=len(rr) or md>1e-9 or abs(recon)>1e-6 or ea>1e-6 or eb>1e-6:failures.append({'candidate':cand,'benchmark':bench,'daily_diff':md,'recon':recon,'candidate_identity':ea,'benchmark_identity':eb})
  checks.append({'candidate':cand,'benchmark':bench,'rows':len(calc),'max_reported_difference':md,'candidate_daily_identity':ea,'benchmark_daily_identity':eb,'pair_reconciliation':recon})
  rel=da.equity/db.equity;peak=rel.cummax().clip(lower=1);dd=rel/peak-1;ints=intervals(rel);longest=max(ints,key=lambda x:x['days']) if ints else {'days':0,'unrecovered':False};end=ints[-1]['days'] if ints and ints[-1]['unrecovered'] else 0
  qr=rd[(rd.candidate==cand)&(rd.benchmark==bench)].sort_values('date');sr=rs[(rs.candidate==cand)&(rs.benchmark==bench)]
  rdiff=max((qr.relative_nav.to_numpy()-rel.to_numpy()).__abs__().max(),(qr.relative_drawdown.to_numpy()-dd.to_numpy()).__abs__().max()) if len(qr)==len(rel) else float('inf')
  expected=[rel.iloc[-1],dd.min(),longest['days'],longest['unrecovered'],end,da.equity.iloc[-1]-db.equity.iloc[-1]]
  got=[] if len(sr)!=1 else [sr.iloc[0][c] for c in ['end_relative_nav','worst_relative_drawdown','longest_relative_recovery_days','longest_unrecovered','end_unrecovered_days','end_absolute_profit_difference']]
  if len(got)!=6 or any(abs(float(a)-float(b))>1e-9 for a,b in zip(expected,got)) or rdiff>1e-12:failures.append({'type':'relative','candidate':cand,'benchmark':bench,'daily_diff':rdiff})
  relative_checks.append({'candidate':cand,'benchmark':bench,'daily_rows':len(qr),'max_daily_diff':rdiff,'end_relative_nav':rel.iloc[-1],'worst_relative_drawdown':dd.min(),'longest_recovery_days':longest['days'],'end_unrecovered_days':end})
  for label,lo,hi in [('full','2018-07-05','2026-06-30'),('2025-2026H1','2025-01-01','2026-06-30')]:
   q=calc[(calc.date>=lo)&(calc.date<=hi)];rp=ph[(ph.candidate==cand)&(ph.benchmark==bench)&(ph.period==(label if label!='full' else '__none__'))]
   phase_check.append({'candidate':cand,'benchmark':bench,'period':label,'candidate_pnl':q.candidate_pnl.sum(),'benchmark_pnl':q.benchmark_pnl.sum(),'difference':q.difference.sum(),'reported_phase_component_sum':rp.difference.sum() if label=='2025-2026H1' else None})
   if label=='2025-2026H1' and abs(rp.difference.sum()-q.difference.sum())>1e-6:failures.append({'type':'phase','candidate':cand,'benchmark':bench})
  # Full grouped totals must match the reported attribution table.
  cg=calc.groupby(['component','holding_group'])[['candidate_pnl','benchmark_pnl','difference']].sum().reset_index();ra=attr[(attr.candidate==cand)&(attr.benchmark==bench)];z=cg.merge(ra,on=['component','holding_group'],suffixes=('_calc','_reported'))
  if len(z)!=len(cg) or max((z[c+'_calc']-z[c+'_reported']).abs().max() for c in ('candidate_pnl','benchmark_pnl','difference'))>1e-8:failures.append({'type':'attribution','candidate':cand,'benchmark':bench})
  # On days with dividend/account-action entries the daily identity must still hold, preventing price-gap + dividend double count.
  action_days=a.index[(a.dividends!=0)] .union(b.index[(b.dividends!=0)])
  if len(action_days):
   if max((a.loc[action_days].overnight+a.loc[action_days].intraday+a.loc[action_days].dividends+a.loc[action_days].fees-a.loc[action_days].delta).abs().max(),(b.loc[action_days].overnight+b.loc[action_days].intraday+b.loc[action_days].dividends+b.loc[action_days].fees-b.loc[action_days].delta).abs().max())>1e-6:failures.append({'type':'action_day','candidate':cand,'benchmark':bench})
 pd.DataFrame(checks).to_csv(HERE/'attribution-checks.csv',index=False);pd.DataFrame(phase_check).to_csv(HERE/'attribution-phase-checks.csv',index=False);pd.DataFrame(relative_checks).to_csv(HERE/'relative-checks.csv',index=False)
 after={str(p):sha(p) for p in files};assert before==after
 result={'passed':not failures,'principles_version':'v1.0','definition_standard_version':'v1.0.0','pairs':len(checks),'failures':failures,'source_hashes':before};(HERE/'attribution-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['passed'],len(checks),len(failures))

if __name__=='__main__':main()
