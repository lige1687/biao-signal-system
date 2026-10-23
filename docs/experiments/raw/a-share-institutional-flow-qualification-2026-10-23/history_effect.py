"""Frozen descriptive price-change test; no training, tuning, execution or net-return claim."""
import json,hashlib,sys,math,datetime
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
R=Path(__file__).resolve().parent

def top_weights(scores, fraction=.3):
 s=np.asarray(scores,float);n=len(s);w=np.zeros(n);left=n*fraction
 for v in sorted(set(s),reverse=True):
  ix=np.flatnonzero(s==v);take=min(left,len(ix));w[ix]=take/len(ix);left-=take
  if left<1e-12:break
 assert abs(w.sum()-n*fraction)<1e-9
 return w

def selfcheck():
 s=np.array([1,1,1,0,0,0,0]);w=top_weights(s);assert np.allclose(w[:3],.7) and not w[3:].any()
 order=np.array([3,1,6,2,0,4,5]);assert np.allclose(top_weights(s[order]),w[order])
 a=np.array([0.,.1,.5,1,1]);assert np.allclose(top_weights(.2-.1*a),top_weights(-a))
 print(json.dumps({'tie_boundary_shared_equal':True,'permutation_invariant':True,'affine_direction_identity':True}))
if '--selfcheck' in sys.argv:selfcheck();raise SystemExit
assert '--execute' in sys.argv
contract=json.loads((R/'history-effect-freeze.json').read_text())
for p,h in contract['bindings'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
p=json.loads((R/'price-qualification.json').read_text());a=json.loads((R/'adjusted-history-comparison.json').read_text());directions={v['period']:(v['adjusted_direction'],v['raw_direction']) for v in a['periods']}
plan=json.loads((R/'storage-plan.json').read_text());sys.path.insert(0,str(R.parents[3]/'src'));from lei_signal.research.output_storage import plan_output
fresh=plan_output(R.parents[3],plan['task_id'],plan['estimated_bytes'],internal_bytes=plan['internal_metadata_bytes']);assert fresh['external_uuid']==plan['external_uuid'] and fresh['external_device']==plan['external_device'];assert Path(plan['output']).stat().st_dev==plan['external_device']
forms=pd.read_parquet(p['formations_path']);codes=sorted(set(forms.loc[forms.column_present,'code']));prices=pd.read_parquet(p['price_source'],columns=['date']+codes);prices=prices.set_index('date') if 'date' in prices.columns else prices;prices.index=pd.to_datetime(prices.index)
forms['future_price_change']=np.nan
for i,row in forms.iterrows():
 if row['entry_price_available'] and row['exit_price_available']:
  forms.loc[i,'future_price_change']=prices.loc[row['exit'],row['code']]/prices.loc[row['entry'],row['code']]-1
per=[];choices=[]
for period,t in forms.groupby('period',sort=True):
 direction,raw_direction=directions[period];y=t.future_price_change.to_numpy();valid=np.isfinite(y);whole=float(np.mean(y[valid])) if valid.any() else None
 for name,scores in [('fixed_jiashi',t.a.to_numpy()),('fixed_huaxia',-t.a.to_numpy()),('report_redemption',raw_direction*t.a.to_numpy()),('adjusted_redemption',direction*t.a.to_numpy())]:
  active=not((name=='adjusted_redemption' and direction==0) or (name=='report_redemption' and raw_direction==0))
  ic=float(spearmanr(scores[valid],y[valid]).statistic) if active and valid.sum()>1 and len(set(scores[valid]))>1 else None
  ic=ic if ic is not None and math.isfinite(ic) else None
  w=top_weights(scores) if active else np.zeros(len(t));obs=w[valid].sum();high=float(np.dot(w[valid],y[valid])/obs) if obs>0 else None
  per.append({'period':period,'method':name,'direction':direction,'active':active,'universe':len(t),'known':int(valid.sum()),'unknown':int((~valid).sum()),'ic':ic,'high_price_change_known':high,'whole_price_change_known':whole,'high_minus_whole_known':high-whole if high is not None and whole is not None else None,'selected_weight':float(w.sum()),'unknown_selected_weight':float(w[~valid].sum()),'unknown_selected_fraction':float(w[~valid].sum()/w.sum()) if w.sum() else None,'entry':str(t.entry.iloc[0].date()),'exit':str(t.exit.iloc[0].date()) if pd.notna(t.exit.iloc[0]) else None})
  for row,weight in zip(t.to_dict('records'),w):choices.append({'period':period,'method':name,'code':row['code'],'selected_weight':float(weight),'future_known':bool(np.isfinite(row['future_price_change']))})
frame=pd.DataFrame(per);common=sorted(frame.loc[(frame.method=='adjusted_redemption')&frame.ic.notna(),'period']);res={}
raw_periods=sorted(frame.loc[(frame.method=='report_redemption')&frame.ic.notna(),'period']);adjusted_periods=list(common);both_periods=sorted(set(common)&set(raw_periods));common=both_periods
def finite_mean(values):
 return float(values.mean()) if values.notna().any() else None
for method in ['fixed_jiashi','fixed_huaxia','report_redemption','adjusted_redemption']:
 q=frame[(frame.method==method)&frame.period.isin(common)];res[method]={'periods':len(q),'mean_ic':finite_mean(q.ic),'mean_high_price_change_known':finite_mean(q.high_price_change_known),'mean_whole_price_change_known':finite_mean(q.whole_price_change_known),'mean_high_minus_whole_known':finite_mean(q.high_minus_whole_known),'max_unknown_selected_fraction':float(q.unknown_selected_fraction.max())}
q=frame[frame.period.isin(common)].pivot(index='period',columns='method',values=['ic','high_price_change_known']);inc={}
for opp in ['fixed_jiashi','fixed_huaxia']:
 delta=q['high_price_change_known']['adjusted_redemption']-q['high_price_change_known'][opp];di=q['ic']['adjusted_redemption']-q['ic'][opp]
 inc[opp]={'mean_ic_difference':float(di.mean()),'mean_high_price_change_difference':float(delta.mean()),'positive_periods':int((delta>1e-12).sum()),'negative_periods':int((delta< -1e-12).sum()),'identical_periods':int((abs(delta)<=1e-12).sum()),'leave_one_out_mean_high_difference_range':[float(delta.drop(i).mean()) for i in delta.index] if len(delta)>1 else []}
plan=json.loads((R/'storage-plan.json').read_text());sys.path.insert(0,str(R.parents[3]/'src'));from lei_signal.research.output_storage import plan_output
fresh=plan_output(R.parents[3],plan['task_id'],plan['estimated_bytes'],internal_bytes=plan['internal_metadata_bytes']);assert fresh['external_uuid']==plan['external_uuid'] and fresh['external_device']==plan['external_device'];base=Path(plan['output']);assert base.is_dir() and base.stat().st_dev==plan['external_device']
out=base/'history-effect';assert not out.exists();out.mkdir()
forms.to_parquet(out/'formation-outcomes.parquet',index=False);frame.to_csv(out/'per-period.csv',index=False);pd.DataFrame(choices).to_csv(out/'selection-weights.csv',index=False)
summary={'at':datetime.datetime.now().astimezone().isoformat(),'common_periods':common,'adjusted_finite_periods':adjusted_periods,'raw_finite_periods':raw_periods,'both_definition_common_periods':both_periods,'performance':res,'increment':inc,'per_period':per,'formations':len(forms),'known':int(forms.future_price_change.notna().sum()),'unknown':int(forms.future_price_change.isna().sum()),'price_change_not_total_or_net_return':True,'new_fits':0,'parameter_searches':0,'effect_runs':1,'no_trading_status_or_terminal_value_verification':True,'out':str(out)}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n');(R/'history-effect-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'common_periods':common,'adjusted_finite_periods':adjusted_periods,'raw_finite_periods':raw_periods,'both_definition_common_periods':both_periods,'performance':res,'increment':inc},ensure_ascii=False,allow_nan=False))
