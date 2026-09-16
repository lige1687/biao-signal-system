"""Independent calendar audit, with no imports of root or Spark functions."""
from pathlib import Path
import hashlib,json,math
import numpy as np
import pandas as pd

P=Path(__file__).resolve().parent; R=P.parent; S=R.parent/'research-sixth-2026-09-08'
snap=P/'root-snapshot';snap.mkdir(exist_ok=True)
names=['calendar-protocol.md','calendar-lock.json','calendar_attribution.py','calendar-results.json','calendar-daily-opportunity-ledger.csv.gz','calendar-opportunity-reconciliation.csv','calendar-monthly.csv','calendar-yearly.csv','calendar-quarterly.csv','month-block-protocol.md','month-block-lock.json','month_block_diagnostic.py','month-block-results.json','spark/month_blocks.py']
names += [f'month-{kind}-L{n}.{ext}' for n in [6,12,24] for kind,ext in [('indices','npz'),('composition-draws','csv')]]
inputs=[]
for n in names:
 b=(R/n).read_bytes();dest=snap/n;dest.parent.mkdir(exist_ok=True)
 if dest.exists():assert dest.read_bytes()==b,'Changed root artifact: '+n
 else:dest.write_bytes(b)
 inputs.append({'file':n,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
for name in ['calendar-lock.json','month-block-lock.json']:
 lock=json.loads((snap/name).read_text());assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in lock['files'].items())
manifest=json.loads((S/'full-baseline-review/input-manifest.json').read_text());prices={}
for item in manifest['files']:
 f=S/'full-baseline-review'/item['copy'];assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
 if f.name.endswith('.bars.parquet'):prices[f.name.removesuffix('.bars.parquet')]=pd.read_parquet(f)
d=pd.read_csv(S/'atr-opportunity-ledger.csv');d=d[(d.fee=='amount_5bp')&d.arm.isin(['base','buffer'])]
assert len(d)==9236 and d.key.nunique()==2309 and (d.groupby('key').size()==4).all()
journal=pd.read_csv(snap/'calendar-daily-opportunity-ledger.csv.gz');assert not journal.duplicated(['key','arm','sizing','date']).any()
jgroups={k:g for k,g in journal.groupby(['key','arm','sizing'],sort=False)}
dates=pd.date_range(d[d.entered].entry_date.min(),d[d.entered].valuation_date.max(),freq='D');origin=dates[0]
arrs={k:np.zeros((len(dates),4)) for k in d.groupby(['module','sizing','arm']).groups}
max_value_error=0.;max_change_error=0.;checks=[];pending=[];exits=0;rebuilt_rows=0
counts={'A':1521,'B':563,'C':225}
for r in d.itertuples():
 key=(r.key,r.arm,r.sizing)
 if not r.entered:
  assert key not in jgroups and r.budget_return==0;checks.append({'key':r.key,'arm':r.arm,'sizing':r.sizing,'entered':False,'recomputed':0.,'difference':0.});continue
 b=prices[r.symbol];start=pd.Timestamp(r.entry_date);end=pd.Timestamp(r.valuation_date)
 q=r.quantity_proxy;ep=float(b.loc[start,'open']);assert abs(ep-r.entry_price)<1e-9
 buy=q*ep*.0005;sel=b.loc[start:end];assert len(sel)>0
 if r.closed:assert abs(float(b.loc[end,'open'])-r.terminal_price)<1e-9
 else:
  last=b.close[np.isfinite(b.close)].index[-1];assert last==end and abs(float(b.loc[end,'close'])-r.terminal_price)<1e-9
 raw_dates=list(sel.index);expected=[];wealth=1.;previous=ep;previous_mark=0.;previous_active=0
 a=arrs[(r.module,r.sizing,r.arm)];a[(start-origin).days,3]+=1
 for ix,t in enumerate(raw_dates):
  exited=bool(r.closed and t==end)
  mark=float(b.loc[t,'open'] if exited else b.loc[t,'close']);assert math.isfinite(mark)
  change=q*(mark-previous)-(buy if ix==0 else 0)-(q*mark*.0005 if exited else 0)
  wealth+=change;expected.append((str(t.date()),wealth,change,exited));a[(t-origin).days,0]+=change
  # Position at each calendar day's close. Market closures carry the last known mark
  # only while the original opportunity is known to be held; no execution fill is made.
  if not exited:
   nextt=raw_dates[ix+1] if ix+1<len(raw_dates) else end+pd.Timedelta(days=1)
   a[(t-origin).days:(nextt-origin).days,1]+=q*mark
   a[(t-origin).days:(nextt-origin).days,2]+=1
  previous=mark
 g=jgroups.pop(key);assert g.date.tolist()==[x[0] for x in expected]
 ev=np.array([x[1] for x in expected]);ec=np.array([x[2] for x in expected])
 max_value_error=max(max_value_error,float(np.max(abs(ev-g.budget_value))));max_change_error=max(max_change_error,float(np.max(abs(ec-g.change))))
 assert g.is_exit.tolist()==[x[3] for x in expected]
 err=wealth-1-r.budget_return;assert abs(err)<1e-10
 checks.append({'key':r.key,'arm':r.arm,'sizing':r.sizing,'entered':True,'recomputed':wealth-1,'difference':err});rebuilt_rows+=len(expected);exits+=int(r.closed)
 if not r.closed:pending.append({'key':r.key,'arm':r.arm,'sizing':r.sizing,'last_journal_date':g.date.iloc[-1],'value':wealth,'fee':buy,'journal_rows':len(g),'has_after_valuation_rows':False})
assert not jgroups and rebuilt_rows==len(journal)==164808
assert max_value_error<1e-10 and max_change_error<1e-10
recon=pd.read_csv(snap/'calendar-opportunity-reconciliation.csv').set_index(['key','arm','sizing'])
for x in checks:
 y=recon.loc[(x['key'],x['arm'],x['sizing'])];assert bool(y.entered)==x['entered'];assert abs(y.sum_daily_changes-x['recomputed'])<1e-10;assert abs(y.expected-(x['recomputed']-x['difference']))<1e-10;assert abs(y.difference-x['difference'])<1e-10
aggregate_errors={};recomputed={}
for period,kind in [('month','M'),('year','Y'),('quarter','Q')]:
 table=pd.read_csv(snap/f'calendar-{period}ly.csv').set_index(['module','sizing','arm',period]);rows=[]
 labels=dates.to_period(kind).astype(str)
 for (mod,sizing,arm),a in arrs.items():
  frame=pd.DataFrame(a,index=dates,columns=['changes','exposure','active','entries'])
  for label,g in frame.groupby(labels):
   label=int(label) if period=='year' else label;val={'budget_change_sum':g.changes.sum(),'per_opportunity_contribution':g.changes.sum()/counts[mod],'average_position_fraction':g.exposure.mean()/counts[mod],'average_active_opportunities':g.active.mean(),'entries':g.entries.sum(),'calendar_days':len(g)}
   root=table.loc[(mod,sizing,arm,label)]
   for k,v in val.items():
    error=abs(root[k]-v);aggregate_errors[k]=max(aggregate_errors.get(k,0.),float(error));assert error<1e-9,(period,k,error)
   rows.append(dict(module=mod,sizing=sizing,arm=arm,**{period:label},**val))
 assert len(rows)==len(table);recomputed[period]=pd.DataFrame(rows)
stats=json.loads((S/'atr-results.json').read_text())['stats'];year=recomputed['year'];calres=json.loads((snap/'calendar-results.json').read_text());totals=[]
for mod in counts:
 for sizing in ['same_budget','same_planned_risk']:
  z=year[(year.module==mod)&(year.sizing==sizing)].pivot(index='year',columns='arm',values='per_opportunity_contribution');delta=z.buffer-z.base
  for arm in ['base','buffer']:
   expected=next(x['mean_budget_return'] for x in stats if (x['module'],x['arm'],x['fee'],x['sizing'])==(mod,arm,'amount_5bp',sizing));assert abs(z[arm].sum()-expected)<1e-10;totals.append(dict(module=mod,sizing=sizing,arm=arm,total=float(z[arm].sum())))
  summary=next(x for x in calres['series'] if x['module']==mod and x['sizing']==sizing);total=float(delta.sum());assert abs(total-summary['all_years_delta'])<1e-10
  for k,calc in [('positive_years',int((delta>1e-12).sum())),('negative_years',int((delta< -1e-12).sum())),('zero_years',int((abs(delta)<=1e-12).sum()))]:assert calc==summary[k]
  for item in summary['leave_one_year_out']:
   remaining=total-delta.loc[item['omitted_year']];assert abs(remaining-item['remaining_contribution'])<1e-10;assert bool(total*remaining<0)==item['sign_reversed']
mon=recomputed['month'];months=sorted(set(mon.month));T=len(months);assert months==pd.period_range('1983-11','2026-08',freq='M').astype(str).tolist()
series=[];vectors=[]
for mod in ['A','B','C']:
 for sizing in ['same_budget','same_planned_risk']:
  g=mon[(mon.module==mod)&(mon.sizing==sizing)].pivot(index='month',columns='arm',values='per_opportunity_contribution').loc[months]
  series.append(mod+':'+sizing);vectors.append((g.buffer-g.base).values)
matrix=np.asarray(vectors).T;blockres=json.loads((snap/'month-block-results.json').read_text());block_checks=[]
for L in [6,12,24]:
 packed=np.load(snap/f'month-indices-L{L}.npz');idx=packed['indices'];assert idx.shape==(5000,T) and list(packed['months'])==months and list(packed['columns'])==series
 # Independent seed reconstruction as flat random starts plus broadcast offsets.
 rng=np.random.default_rng(20260908+L);starts=rng.integers(0,T-L+1,5000*math.ceil(T/L)).reshape(5000,-1)
 independent=(starts[:,:,None]+np.arange(L)[None,None,:]).reshape(5000,-1)[:,:T]
 assert np.array_equal(idx,independent)
 for k in range(0,T,L):
  assert (idx[:,k]<=T-L).all() and (idx[:,k]>=0).all()
  assert (np.diff(idx[:,k:min(k+L,T)],axis=1)==1).all()
 # Every draw sums actual selected months, avoiding the root's counts-matrix product.
 computed=np.empty((5000,6))
 for k in range(5000):computed[k]=np.sum(matrix[idx[k]],axis=0)
 published=pd.read_csv(snap/f'month-composition-draws-L{L}.csv');assert list(published)==series
 error=float(np.max(abs(computed-published.values)));assert error<1e-10
 for k,key in enumerate(series):
  row=next(x for x in blockres['series'] if x['series']==key and x['block_months']==L)
  assert row['draws']==5000 and row['months_per_draw']==T
  assert abs(row['original_total_delta']-matrix[:,k].sum())<1e-10
  for field,v in zip(['middle90_low','median','middle90_high'],np.percentile(computed[:,k],[5,50,95])):assert abs(row[field]-v)<1e-10
  assert row['shared_index_sha256']==hashlib.sha256((snap/f'month-indices-L{L}.npz').read_bytes()).hexdigest()
 freq=np.bincount(idx.ravel(),minlength=T)
 block_checks.append(dict(block_months=L,draws=5000,months_per_draw=T,all_indices_and_seed_match=True,all_six_views_share_indices=True,max_result_error=error,first_month_draws=int(freq[0]),last_month_draws=int(freq[-1]),middle_month_draws=int(freq[T//2]),zero_series_stays_zero=bool((np.zeros(T)[idx].sum(axis=1)==0).all())))
assert all(blockres[k] for k in ['not_confidence_intervals','not_future_probability','not_real_tradable_paths','not_whole_history_search_correction'])
report=dict(opportunities=2309,views=4,reconciled_rows=len(checks),independently_rebuilt_daily_rows=rebuilt_rows,completed_exit_rows=exits,max_daily_value_error=max_value_error,max_daily_change_error=max_change_error,max_aggregation_errors=aggregate_errors,all_twelve_s6_totals_match=True,all_leave_year_results_match=True,totals=totals,pending_views=len(pending),msft_pending=[x for x in pending if ':MSFT:' in x['key']],blocks=block_checks,root_files_unchanged=all(hashlib.sha256((R/x['file']).read_bytes()).hexdigest()==x['sha256'] for x in inputs))
assert report['root_files_unchanged']
pd.DataFrame(checks).to_csv(P/'independent-reconciliation.csv',index=False)
(P/'reviewed-inputs.json').write_text(json.dumps(inputs,indent=2))
(P/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
