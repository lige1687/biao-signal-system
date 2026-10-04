"""Secondary comparisons on the saved outputs only; never fit or choose parameters."""
import json,math,csv
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
cal=read(HERE/'workflow-input.local.json')['calendar'];axis=[d for d in cal if '2025-01-01'<=d<='2026-06-30'];di={d:i for i,d in enumerate(axis)}
def interval(s):
 a=np.full(len(axis),np.nan)
 for d,v in s.items():a[di[d]]=v
 rng=np.random.default_rng(20261004);vals=[]
 for _ in range(1000):
  starts=rng.integers(0,len(a)-60+1,size=math.ceil(len(a)/60));ix=np.concatenate([np.arange(j,j+60) for j in starts])[:len(a)];x=a[ix];x=x[np.isfinite(x)]
  if len(x):vals.append(float(x.mean()))
 return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if vals else None
rows=pd.read_csv(HERE/'same-day-ranking-rows.csv');fields=['green_share20','switch_frequency20','distance_to_ema20','ret20','ema20_up_share20'];rank=[]
for group in ['all','broad','sector']:
 pool=rows if group=='all' else rows[rows.asset.str.startswith('512')==(group=='sector')]
 for name in fields:
  for date,f in pool.groupby('date'):
   # Recompute fixed average-tie ranks for each descriptive universe, not conditioned on future return.
   x=f[name];rk=(x.rank(method='average')-1)/(len(f)-1) if len(f)>1 else x*float('nan')
   lo=f[rk<.5];hi=f[rk>.5]
   if len(lo) and len(hi):rank.append({'group':group,'factor':name,'date':date,'n':len(f),'high_n':len(hi),'low_n':len(lo),'pool':float(f.ret.mean()),'high':float(hi.ret.mean()),'low':float(lo.ret.mean()),'gap':float(hi.ret.mean()-lo.ret.mean()),'high_mae':float(hi.mae.mean()),'low_mae':float(lo.mae.mean())})
r=pd.DataFrame(rank);out={}
for (g,n),f in r.groupby(['group','factor']):
 out[g+'/'+n]={'dates':len(f),'rows':int(f.n.sum()),'high':float(f.high.mean()),'low':float(f.low.mean()),'pool':float(f.pool.mean()),'gap':float(f.gap.mean()),'gap60':interval(dict(zip(f.date,f.gap))),'high_mae':float(f.high_mae.mean()),'low_mae':float(f.low_mae.mean()),'period_gap':{y:float(z.gap.mean()) for y,z in f.groupby(f.date.str[:4])}}
r.to_csv(HERE/'universe-ranking.csv',index=False)
models={};errors=[]
for target in ['forward_return','mae']:
 for method in ['ridge','lightgbm']:
  name=method+'-'+target;f=pd.read_csv(HERE/('continuous-'+name+'-saved.csv'),dtype={'fold':str});v={}
  for group in ['all','broad','sector']:
   z=f if group=='all' else f[f.asset.str.startswith('512')==(group=='sector')]
   w=1/z.asset.map(z.asset.value_counts()).to_numpy(float);w/=w.sum()
   loss=(z.y-z.B1)**2-(z.y-z.B2)**2
   bydate=z.assign(delta=loss).groupby('date').delta.mean()
   v[group]={'rows':len(z),'dates':z.date.nunique(),'mse_improvement':float(w@loss),'date_mean_improvement':float(bydate.mean()),'date60':interval(bydate.to_dict()),'positive_rows':int((loss>0).sum()),'negative_rows':int((loss<0).sum()),'rmse':{c:float(np.sqrt(w@((z.y-z[c])**2))) for c in ['ETF_mean','B1','B2']}}
  models[name]=v
  # independent standard-library equal-ETF headline recalculation
  with (HERE/('continuous-'+name+'-saved.csv')).open() as h:rs=list(csv.DictReader(h))
  aset=sorted({v['asset'] for v in rs});m={c:math.sqrt(sum(sum((float(v['y'])-float(v[c]))**2 for v in rs if v['asset']==a)/sum(v['asset']==a for v in rs) for a in aset)/len(aset)) for c in ['ETF_mean','B1','B2']}
  error=max(abs(m[c]-models[name]['all']['rmse'][c]) for c in m);assert error<1e-10;errors.append({'branch':name,'rows':len(rs),'independent_rmse_error':error})
# State descriptions are associations, not an independent effect of black controlling for trend.
f=pd.read_csv(HERE/'continuous-ridge-forward_return-saved.csv');risk=pd.read_csv(HERE/'continuous-ridge-mae-saved.csv');assert f.id.tolist()==risk.id.tolist();f['mae']=risk.y;state={}
for (g,s),z in f.assign(group=np.where(f.asset.str.startswith('512'),'sector','broad')).groupby(['group','state']):
 state[g+'/'+s]={'rows':len(z),'dates':z.date.nunique(),'assets':z.asset.nunique(),'return':float(z.y.mean()),'up_probability':float((z.y>0).mean()),'mae':float(z.mae.mean()),'loss_over5_probability':float((z.mae>5).mean()),'meaning':'descriptive state grouping, not independent increment; different dates and holdings'}
paired={}
for target in ['forward_return','mae']:
 for method in ['ridge','lightgbm']:
  a=pd.read_csv(HERE/('model-ranking-'+method+'-'+target+'-B1.csv'));b=pd.read_csv(HERE/('model-ranking-'+method+'-'+target+'-B2.csv'));z=a.merge(b,on='date',suffixes=('_b','_x')).dropna(subset=['high_minus_low_b','high_minus_low_x']);delta=z.high_minus_low_x-z.high_minus_low_b
  paired[method+'-'+target]={'dates':len(z),'rank_gap_improvement':float(delta.mean()),'date60':interval(dict(zip(z.date,delta))),'period':{y:float(delta[z.date.str.startswith(y)].mean()) for y in ['2025','2026']}}
put(HERE/'diagnostics.json',{'paired_model_ranking':paired,'ranking_by_pool':out,'model_increment_by_pool':models,'state_description':state,'independent_headline_checks':errors,'new_fits':0,'subpool_ranking_limitation':'available saved common outcome rows; actual evaluation must confirm all X-qualified ranks have complete outcomes before describing selection'})
print(json.dumps({'independent_checks':errors,'models':models},ensure_ascii=False))
