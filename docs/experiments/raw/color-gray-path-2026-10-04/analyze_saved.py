"""Saved-model analysis and independent price arithmetic; zero fits."""
import json,hashlib,math
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from lei_signal.features.indicators import compute_features
from lei_signal.rules.clock_classifier import clock_series
from lei_signal.research.color_continuous_information import same_day_ranks
from lei_signal.research.workflow_evaluation import summarize_predictions
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
panel=read(ROOT/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json');cal=panel['calendar'];idx={d:i for i,d in enumerate(cal)}
assets=sorted({b['asset'] for b in panel['bars']});bars={a:{b['date']:b for b in panel['bars'] if b['asset']==a} for a in assets}
clock={};clockrun={}
for a in assets:
 f=pd.DataFrame([bars[a][d] for d in cal]); types=clock_series(compute_features(f)).tolist();prev=None;start=None
 for d,t in zip(cal,types):
  group='up' if t in [1,2] else 'down' if t in [4,5] else 'sideways' if t==3 else 'unknown'
  if group!=prev:start=d
  clock[a,d]=(int(t),group);clockrun[a,d]=a+'|'+start;prev=group
axis=[d for d in cal if '2025-01-01'<=d<='2026-06-30'];dayindex={d:i for i,d in enumerate(axis)}
def weights(f):
 w=1/f.asset.map(f.asset.value_counts()).to_numpy(float);return w/w.sum()
def metric(f,cols):
 if not len(f):return {'n':0,'dates':0,'assets':0}
 w=weights(f);return {'n':len(f),'dates':f.date.nunique(),'assets':f.asset.nunique(),'rmse':{c:float(np.sqrt(w@((f.y-f[c])**2))) for c in cols},'mean_y':float(w@f.y),'asset_regime_segments':f.env_run.nunique()}
def blocks(values,block):
 arr=np.full(len(axis),np.nan)
 for d,v in values.items():
  if d in dayindex:arr[dayindex[d]]=v
 rng=np.random.default_rng(20261004);out=[];n=len(axis)
 for _ in range(1000):
  starts=rng.integers(0,n-block+1,size=math.ceil(n/block));pick=np.concatenate([np.arange(s,s+block) for s in starts])[:n];v=arr[pick];v=v[np.isfinite(v)]
  if len(v):out.append(float(v.mean()))
 return {'lo':float(np.quantile(out,.025)) if out else None,'hi':float(np.quantile(out,.975)) if out else None,'valid_draws':len(out),'block':block}
summary={};frames={};verification=[];fits=0
for group in ['core','continuous']:
 for target in ['forward_return','mae']:
  for method in ['ridge','lightgbm']:
   p=HERE/group/(method+'-'+target)/'core-01';result=read(p/'result.json');proof=read(p/'preflight.json');c=read(p/'contract.json');obs={r['id']:r for r in proof['observations']};f=pd.DataFrame(result['predictions']);fits+=result['execution']['fits']
   f['env5']=[clock[a,d][0] for a,d in zip(f.asset,f.date)];f['env']=[clock[a,d][1] for a,d in zip(f.asset,f.date)];f['env_run']=[clockrun[a,d] for a,d in zip(f.asset,f.date)];f['state']=[obs[k]['state'] for k in f.id]
   max_label=0.;max_pred=0.;fallbacks=0
   for foldno,fold in enumerate(c['split']['folds']):
    train=[r for r in proof['observations'] if r['eligible'] and r['date']<=fold['train_end'] and r['label_end']<fold['eval_start']];means={a:np.mean([r['y'] for r in train if r['asset']==a]) for a in assets};groupmeans={(a,s):np.mean([r['y'] for r in train if r['asset']==a and r['state']==s]) for a in assets for s in {r['state'] for r in train} if any(r['asset']==a and r['state']==s for r in train)}
    for i,row in f[f.fold==str(foldno)].iterrows():
     f.loc[i,'ETF_mean']=means[row.asset];key=(row.asset,row.state);f.loc[i,'ETF_state_mean']=groupmeans.get(key,means[row.asset]);fallbacks+=int(key not in groupmeans)
   for _,r in f.iterrows():
    j=idx[r.date];path=[bars[r.asset][d]['close'] for d in cal[j+1:j+22]];y=100*(path[-1]/path[0]-1) if target=='forward_return' else max(0,100*(1-min(path)/path[0]));max_label=max(max_label,abs(y-r.y));assert cal[j+21]==r.label_end
   for detail in result['execution']['fit_details']:
    selected=f[f.fold==detail['fold']];x=np.array([[obs[k]['features'][col] for col in detail['features']] for k in selected.id])
    if method=='ridge':pred=detail['intercept']+((x-np.array(detail['mean']))/np.array(detail['std']))@np.array(detail['coef'])
    else:
     assert hashlib.sha256(detail['model_text'].encode()).hexdigest()==detail['model_sha256'];pred=lgb.Booster(model_str=detail['model_text']).predict(x,num_threads=1)
    max_pred=max(max_pred,float(np.max(np.abs(pred-selected[detail['model']].to_numpy()))))
   assert max_label<1e-9 and max_pred<1e-9
   cols=['B0','ETF_mean','ETF_state_mean','B1','B2'];key=group+'/'+method+'-'+target
   s={'overall':metric(f,cols),'by_period':{y:metric(f[f.date.str.startswith(y)],cols) for y in ['2025','2026']},'by_asset':{a:metric(f[f.asset==a],cols) for a in assets},'drop_one':{a:metric(f[f.asset!=a],cols) for a in assets},'own_asset_environment':{e:metric(f[f.env==e],cols) for e in ['up','sideways','down','unknown']},'own_asset_five':{str(e):metric(f[f.env5==e],cols) for e in range(6)},'by_state':{s:metric(f[f.state==s],cols) for s in f.state.unique()},'increment20':result['increments'],'fallback_ETF_state_mean':fallbacks}
   c60={**c,'dependence':{**c['dependence'],'block_length':60}};s['increment60']=summarize_predictions(result['predictions'],c60)['increments'];summary[key]=s;frames[key]=f;f.to_csv(HERE/(group+'-'+method+'-'+target+'-saved.csv'),index=False)
   verification.append({'branch':key,'rows':len(f),'label_max_error':max_label,'saved_model_replay_max_error':max_pred,'new_fits':0})
# Four cells on identical support, including comparisons between methods.
comparison={}
for group in ['core','continuous']:
 for target in ['forward_return','mae']:
  a=frames[group+'/ridge-'+target];t=frames[group+'/lightgbm-'+target];assert a.id.tolist()==t.id.tolist() and np.allclose(a.y,t.y)
  f=a.copy();f['A']=a.B1;f['B']=a.B2;f['C']=t.B1;f['D']=t.B2
  diffs={}
  for old,new in [('A','B'),('C','D'),('A','C'),('B','D')]:
   loss=(f.y-f[old])**2-(f.y-f[new])**2;tmp=f.assign(delta=loss);dated=tmp.groupby('date').delta.mean().to_dict()
   diffs[new+'-'+old]={'mse_improvement':float(weights(f)@loss),'date_weighted_improvement':float(np.mean(list(dated.values()))),'date_blocks20':blocks(dated,20),'date_blocks60':blocks(dated,60),'note':'positive error improvement; uncertainty here equal-date, primary model aggregate equal-asset'}
  comparison[group+'/'+target]={'performance':metric(f,['ETF_mean','ETF_state_mean','A','B','C','D']),'differences':diffs}
# Same-day ranking and fixed high/low groups on the same common eligible dates.
obs=read(HERE/'continuous/ridge-forward_return/core-01/preflight.json')['observations'];rankrows=[{**r,**r['features']} for r in obs if r['eligible']];fields=['green_share20','switch_frequency20','distance_to_ema20','ret20','ema20_up_share20']
for field in fields:rankrows=same_day_ranks(rankrows,field)
rf=pd.DataFrame(rankrows);ret=frames['continuous/ridge-forward_return'].set_index('id').y;mae=frames['continuous/ridge-mae'].set_index('id').y
rf=rf[rf.id.isin(ret.index)].copy();rf['ret']=rf.id.map(ret);rf['mae']=rf.id.map(mae);rf['env']=[clock[a,d][1] for a,d in zip(rf.asset,rf.date)];rf['env5']=[clock[a,d][0] for a,d in zip(rf.asset,rf.date)];rf['env_run']=[clockrun[a,d] for a,d in zip(rf.asset,rf.date)]
ranksummary={};daily=[]
for field in fields:
 for day,f in rf.groupby('date'):
  x=f[field];yr=f.ret.rank(method='average');xr=x.rank(method='average');ic=float(xr.corr(yr)) if x.nunique()>1 and f.ret.nunique()>1 and len(f)>=2 else None
  ranks=f[field+'_rank'];lo=f[ranks<.5];hi=f[ranks>.5];mid=f[ranks==.5]
  daily.append({'factor':field,'date':day,'n':len(f),'n_low':len(lo),'n_high':len(hi),'n_middle':len(mid),'ic':ic,'pool_return':float(f.ret.mean()),'low_return':float(lo.ret.mean()) if len(lo) else None,'high_return':float(hi.ret.mean()) if len(hi) else None,'high_minus_low':float(hi.ret.mean()-lo.ret.mean()) if len(hi) and len(lo) else None,'high_minus_pool':float(hi.ret.mean()-f.ret.mean()) if len(hi) else None,'low_mae':float(lo.mae.mean()) if len(lo) else None,'high_mae':float(hi.mae.mean()) if len(hi) else None})
 d=pd.DataFrame([r for r in daily if r['factor']==field]);valid=d.dropna(subset=['high_minus_low']);di=d.dropna(subset=['ic'])
 def describe(ds):
  return {'dates':len(ds),'valid_rank_dates':int(ds.ic.notna().sum()),'valid_group_dates':int(ds.high_minus_low.notna().sum()),'mean_rank_correlation':float(ds.ic.mean()) if ds.ic.notna().any() else None,'pool_return':float(ds.pool_return.mean()),'low_return':float(ds.low_return.mean()) if ds.low_return.notna().any() else None,'high_return':float(ds.high_return.mean()) if ds.high_return.notna().any() else None,'high_minus_low':float(ds.high_minus_low.mean()) if ds.high_minus_low.notna().any() else None,'high_mae':float(ds.high_mae.mean()) if ds.high_mae.notna().any() else None,'low_mae':float(ds.low_mae.mean()) if ds.low_mae.notna().any() else None,'unrankable_dates':int(ds.ic.isna().sum()),'empty_group_dates':int(ds.high_minus_low.isna().sum())}
 ranksummary[field]={'overall':describe(d),'by_period':{y:describe(d[d.date.str.startswith(y)]) for y in ['2025','2026']},'gap20':blocks(dict(zip(valid.date,valid.high_minus_low)),20),'gap60':blocks(dict(zip(valid.date,valid.high_minus_low)),60),'rank20':blocks(dict(zip(di.date,di.ic)),20),'rank60':blocks(dict(zip(di.date,di.ic)),60)}
 # Conditioning on own state retains ranks from original common same-day pool.
 ranksummary[field]['own_asset_environment']={}
 for env,f in rf.groupby('env'):
  lo=f[f[field+'_rank']<.5];hi=f[f[field+'_rank']>.5]
  ranksummary[field]['own_asset_environment'][env]={'rows':len(f),'dates':f.date.nunique(),'segments':f.env_run.nunique(),'low_rows':len(lo),'high_rows':len(hi),'high_minus_low_pp':float(hi.ret.mean()-lo.ret.mean()) if len(hi) and len(lo) else None,'note':'conditional observed difference, not randomized or whole-market environment'}
pd.DataFrame(daily).to_csv(HERE/'same-day-ranking-daily.csv',index=False);rf[['id','asset','date','ret','mae','env','env5','env_run']+fields+[k+'_rank' for k in fields]].to_csv(HERE/'same-day-ranking-rows.csv',index=False)
put(HERE/'analysis.json',{'models':summary,'four_cells':comparison,'ranking':ranksummary,'actual_real_fits':fits,'analysis_fits':0,'market_environment':'not evaluated: qualified index panel missing; own-asset proxy is separate','net_portfolio_return':'not evaluated: executable opening/limits/cost evidence missing','individual_stock_Top20_Top30':'pending new data-owner qualified historical membership manifest'})
put(HERE/'independent-verification.json',verification)
print(json.dumps({'actual_fits':fits,'verified_branches':len(verification),'four_cells':{k:v['performance'] for k,v in comparison.items()},'rank':{k:v['overall'] for k,v in ranksummary.items()}},ensure_ascii=False))
