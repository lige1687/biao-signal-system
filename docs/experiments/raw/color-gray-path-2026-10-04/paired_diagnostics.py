from pathlib import Path
import json,math
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent
calendar=json.loads((H/'continuous/ridge-forward_return/core-01/contract.json').read_text())['calendar'];axis=[d for d in calendar if '2025-01-01'<=d<='2026-06-30']
def ci(series,other=None):
 x=np.array([series.get(d,np.nan) for d in axis]);y=None if other is None else np.array([other.get(d,np.nan) for d in axis]);result={}
 for block in [20,60]:
  rng=np.random.default_rng(20261004);vals=[]
  for _ in range(1000):
   starts=rng.integers(0,len(axis)-block+1,math.ceil(len(axis)/block));pick=np.concatenate([np.arange(s,s+block) for s in starts])[:len(axis)];a=x[pick];b=None if y is None else y[pick]
   if np.isfinite(a).any() and (b is None or np.isfinite(b).any()):vals.append(float(np.nanmean(a)-(np.nanmean(b) if b is not None else 0)))
  result[str(block)]={'lo':float(np.quantile(vals,.025)) if vals else None,'hi':float(np.quantile(vals,.975)) if vals else None,'valid_draws':len(vals)}
 return result
out={'model_rank_common_dates':{},'environment_differences':{},'rank_vs_simple':{}}
for target in ['forward_return','mae']:
 files={name:pd.read_csv(H/f'model-ranking-{m}-{target}-{b}.csv').set_index('date') for name,m,b in [('A','ridge','B1'),('B','ridge','B2'),('C','lightgbm','B1'),('D','lightgbm','B2')]}
 for old,new in [('A','B'),('C','D'),('A','C'),('B','D')]:
  z=pd.concat([files[old].high_minus_low,files[new].high_minus_low],axis=1,keys=['old','new']).dropna();delta=z.new-z.old
  out['model_rank_common_dates'][target+'/'+new+'-'+old]={'common_dates':len(z),'mean_gap_before':float(z.old.mean()),'mean_gap_after':float(z.new.mean()),'difference':float(delta.mean()),'date_block_uncertainty':ci(delta.to_dict())}
for group in ['core','continuous']:
 for method in ['ridge','lightgbm']:
  for target in ['forward_return','mae']:
   f=pd.read_csv(H/f'{group}-{method}-{target}-saved.csv');f['improvement']=(f.y-f.B1)**2-(f.y-f.B2)**2
   env={e:g.groupby('date').improvement.mean().to_dict() for e,g in f.groupby('env')};record={}
   for first,second in [('up','sideways'),('up','down'),('sideways','down')]:
    x,y=env.get(first,{}),env.get(second,{})
    record[first+'-'+second]={'first_dates':len(x),'second_dates':len(y),'equal_date_increment_difference':float(np.mean(list(x.values()))-np.mean(list(y.values()))) if x and y else None,'uncertainty':ci(x,y),'interpretation':'own-asset conditional groups, shared price source, not causal market regimes'}
   record['period_environment']={yr:{e:{'rows':len(g),'dates':g.date.nunique(),'segments':g.env_run.nunique(),'mean_squared_error_improvement_equal_date':float(g.groupby('date').improvement.mean().mean())} for e,g in f[f.date.str.startswith(yr)].groupby('env')} for yr in ['2025','2026']}
   out['environment_differences'][group+'/'+method+'-'+target]=record
r=pd.read_csv(H/'same-day-ranking-daily.csv')
for candidate in ['green_share20','switch_frequency20','distance_to_ema20']:
 for baseline in ['ret20','ema20_up_share20']:
  c=r[r.factor==candidate].set_index('date');b=r[r.factor==baseline].set_index('date');z=pd.concat([c.high_minus_low,b.high_minus_low],axis=1,keys=['c','b']).dropna();v=z.c-z.b
  out['rank_vs_simple'][candidate+'/'+baseline]={'common_dates':len(z),'gap_difference_pp':float(v.mean()),'uncertainty':ci(v.to_dict())}
(H/'paired-diagnostics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print('saved zero-fit common-date and environment diagnostics')
