"""Independent read-back of frozen results; does not import the runner or change results."""
from pathlib import Path
import json, math, hashlib, bisect
import numpy as np
import pandas as pd
from scipy.stats import rankdata
R=Path(__file__).resolve().parent
O=Path(json.loads((R/'storage-plan.json').read_text())['output'])
S=json.loads((O/'summary.json').read_text())
F=pd.read_csv(O/'features.csv'); W=pd.read_csv(O/'weights.csv'); Y=pd.read_csv(O/'outcomes.csv'); M=pd.read_csv(O/'monthly.csv'); A=pd.read_csv(O/'rank-association.csv')
axis=S['calendar_months']; errors=[]; counts={}
def close(a,b,label):
 if pd.isna(a) and pd.isna(b): return
 if not math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-10): errors.append(label)
def stats(v):
 x=np.array(v,dtype=float); n=int(np.isfinite(x).sum())
 if not n:return {'n':0,'mean':None,'ci_low':None,'ci_high':None}
 mean=float(np.nanmean(x)); z=np.nan_to_num(x-mean,nan=0); var=float(z@z)
 for k in range(1,min(6,len(x)-1)+1):var+=2*(1-k/7)*float(z[k:]@z[:-k])
 se=math.sqrt(max(var,0))/n
 return {'n':n,'mean':mean,'ci_low':mean-1.96*se,'ci_high':mean+1.96*se}
for (ex,mo,arm),g in W.groupby(['exchange','month','arm']):
 f=F[(F.exchange==ex)&(F.month==mo)&F.eligible]; n=len(f); k=math.ceil(n/10)
 expected=f if arm=='all' else f.sort_values(['vol60' if arm=='lowvol' else 'hot','code'],ascending=[arm!='winner',True]).head(k)
 assert set(expected.code)==set(g.code)
 close(g.weight.sum(),1,'weights_sum')
 assert np.allclose(g.weight,1/len(expected))
counts['selection_sets']=W.groupby(['exchange','month','arm']).ngroups
merged=W.merge(Y,on=['exchange','month','code'],validate='many_to_many')
for key,g in merged.groupby(['exchange','month','lag','arm']):
 row=M[(M.exchange==key[0])&(M.month==key[1])&(M.lag==key[2])&(M.arm==key[3])].iloc[0]
 unknown=g.loc[g['return'].isna(),'weight'].sum(); contribution=(g.weight*g['return']).sum()
 close(unknown,row.unknown_weight,'unknown_weight');close(contribution,row.known_weighted_contribution,'known_contribution')
 close(contribution if unknown<1e-12 else np.nan,row.complete_return,'complete_return')
 close(row.complete_return-row.cost_25bps_per_side,row.after_cost_25bps,'cost_subtraction')
counts['portfolio_months']=len(M)
for c in S['comparisons']:
 v=c['monthly_values']; z=stats(v)
 for k in z:close(z[k],c['gross']['all'][k],f'stats:{k}')
counts['comparison_full_stats']=len(S['comparisons'])

for c in S['comparisons']:
 g=M[M.exchange==c['exchange']]
 if isinstance(c['lag'],int):
  left,right=c['comparison'].split('_minus_');g=g[g.lag==c['lag']]
  for field,key in [('complete_return','monthly_values'),('after_cost_25bps','monthly_after_cost_values')]:
   tab=g.pivot(index='month',columns='arm',values=field).reindex(axis)
   for a,b in zip(tab[left]-tab[right],c[key]):close(a,np.nan if b is None else b,'paired_actual_monthly')
 else:
  tab=g.pivot(index='month',columns=['lag','arm'],values='complete_return').reindex(axis)
  z=(tab[(0,'loser')]-tab[(0,'winner')])-(tab[(1,'loser')]-tab[(1,'winner')])
  for a,b in zip(z,c['monthly_values']):close(a,np.nan if b is None else b,'decay_actual_monthly')
# Reconstruct trading amount from prior target positions drifted by prior period quotes.
for (ex,lag,arm),g in M.groupby(['exchange','lag','arm']):
 prior=None
 for mo in axis:
  current=W[(W.exchange==ex)&(W.month==mo)&(W.arm==arm)].set_index('code').weight
  row=g[g.month==mo].iloc[0]
  if prior is None: tv=1.0
  else:
   previous_weights,pm=prior
   ret=Y[(Y.exchange==ex)&(Y.month==pm)&(Y.lag==lag)].set_index('code')['return'].reindex(previous_weights.index)
   if ret.isna().any():tv=np.nan
   else:
    drift=previous_weights*(1+ret);drift=drift/drift.sum();tv=float((current.subtract(drift,fill_value=0)).abs().sum())
  close(tv,row.turnover_gross,'turnover_recomputed')
  prior=(current,mo)
counts['turnover_months_reconstructed']=len(M)

for key,g in Y[Y['return'].notna()].groupby(['exchange','month','lag']):
 f=g.merge(F[['code','month','hot','momentum','vol60']],on=['code','month'],validate='one_to_one')
 x=rankdata(-f.hot); y=rankdata(f['return']); controls=np.column_stack([np.ones(len(f)),rankdata(f.momentum),rankdata(f.vol60)])
 xr=x-controls@np.linalg.lstsq(controls,x,rcond=None)[0];yr=y-controls@np.linalg.lstsq(controls,y,rcond=None)[0]
 a=A[(A.exchange==key[0])&(A.month==key[1])&(A.lag==key[2])].iloc[0]
 close(np.corrcoef(x,y)[0,1],a.raw,'raw_rank');close(np.corrcoef(xr,yr)[0,1],a.partial_momentum_vol60,'partial_rank')
counts['rank_months']=len(A)
assert (Y.decision_date<Y.entry_date).all() and (Y.entry_date<Y.exit_date).all()
counts['time_order_rows']=len(Y)
# Independently reconstruct representative endpoints and monthly signal from original decimal strings.
design=json.loads((R/'design.json').read_text())
manifest=json.loads(Path(design['sources']['new_source_manifest']['path']).read_text())
anchors=[]
for code in sorted(Y.code.unique())[::24]:
 ref=manifest['asset_sources'][code]; raw=json.loads(Path(ref['daily']['path']).read_text()); acts=json.loads(Path(ref['adjustments']['path']).read_text())
 rows=[dict(zip(raw['fields'],v)) for v in raw['data']]; rows={v['date']:v for v in rows}
 acts=[dict(zip(acts['fields'],v)) for v in acts['data']]; dates=[v['dividOperateDate'] for v in acts]
 def price(day,field):return float(rows[day][field])*float(acts[bisect.bisect_right(dates,day)-1]['foreAdjustFactor'])
 sub=Y[(Y.code==code)&Y['return'].notna()]
 for i in [0,len(sub)//2,len(sub)-1]:
  t=sub.iloc[i]; calc=price(t.exit_date,'open')/price(t.entry_date,'open')-1;close(calc,t['return'],'original_quote')
  previous=str(pd.Period(t.month,freq='M')-1); prev=max(d for d in rows if d.startswith(previous));fv=F[(F.code==code)&(F.month==t.month)].iloc[0]
  close(price(t.decision_date,'close')/price(prev,'close')-1,fv.hot,'original_signal')
  anchors.append({'code':code,'month':t.month,'lag':int(t.lag),'entry':t.entry_date,'exit':t.exit_date,'return':calc})
counts['original_quote_and_signal_anchors']=len(anchors)
# Reporting views use same months for each comparison; no new selection or parameter fit.
summary=[]
for (ex,lag),g in M.groupby(['exchange','lag']):
 p=g.pivot(index='month',columns='arm',values='complete_return').reindex(axis)
 common=p.dropna()
 perf={'exchange':ex,'lag':int(lag),'all_four_complete_months':len(common),'all_four_means':common.mean().to_dict(),'arms':{}}
 for arm,h in g.groupby('arm'):
  perf['arms'][arm]={'selected_n_range':[int(h.selected_n.min()),int(h.selected_n.max())],'complete_months':int(h.complete_return.notna().sum()),'mean_unknown_weight':float(h.unknown_weight.mean()),'max_unknown_weight':float(h.unknown_weight.max()),'mean_turnover':float(h.turnover_gross.mean()),'turnover_months':int(h.turnover_gross.notna().sum())}
 for field in ['mean_adverse','known_top_decile_capture','known_20pct_winner_capture','sensitive_complete_return']:
  tab=g.pivot(index='month',columns='arm',values=field).reindex(axis)
  for base in ['all','lowvol']:
   diff=tab['loser']-tab[base]; perf[field+'_loser_minus_'+base]=stats(diff)
 if lag==0:
  both=M[M.exchange==ex].pivot(index='month',columns=['lag','arm'],values='complete_return').reindex(axis)
  ix=both[[(0,'loser'),(0,'winner'),(1,'loser'),(1,'winner')]].dropna().index
  perf['paired_lag_components']={'n':len(ix),'loser_lag0_minus_lag1':float((both.loc[ix,(0,'loser')]-both.loc[ix,(1,'loser')]).mean()),'winner_lag0_minus_lag1':float((both.loc[ix,(0,'winner')]-both.loc[ix,(1,'winner')]).mean())}
 summary.append(perf)
dec=pd.read_csv(O/'decomposition.csv'); decomp=[]
for (ex,lag,base),g in dec.groupby(['exchange','lag','baseline']):
 complete=g[g.complete_increment.notna()]; cols=['added_gain','added_loss','avoided_loss','foregone_gain','complete_increment'];decomp.append({'exchange':ex,'lag':int(lag),'baseline':base,'n':len(complete),**complete[cols].mean().to_dict()})
result={'status':'passed' if not errors else 'failed','checks':counts,'errors':errors,'original_anchors':anchors,'performance_views':summary,'four_contributions':decomp,'outcome_unknown_reasons':Y[Y['return'].isna()].reason.value_counts().to_dict(),'cautions':['Complete-month selection is nonrandom and omits many early months; sparse annual HAC intervals are not inferential evidence.','Net loser-minus-winner subtracts two long-only alternatives, not a tradable long-short strategy with both trading costs.','Partial rank association is descriptive; size industry and turnover not controlled.']}
(R/'controller-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:result[k] for k in ['status','checks','errors','outcome_unknown_reasons']},ensure_ascii=False))
assert not errors
