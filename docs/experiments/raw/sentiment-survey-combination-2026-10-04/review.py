"""Independent date reconstruction and augmented least-squares verification."""
import json, hashlib, os
from pathlib import Path
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent; R=H.parents[3]
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
frozen=json.loads((H/'execution-freeze.json').read_text())
for p,h in frozen['bound_files'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
sources={x['name']:R/x['path'] for x in json.loads((H/'source-manifest.json').read_text())['files']}
p=pd.read_csv(sources['prices']);a=pd.read_csv(sources['aaii']);n=pd.read_csv(sources['naaim']);v=pd.read_csv(H/'run-01/predictions.csv');rows=[]
for z in n.to_dict('records'):
 i=next(i for i,d in enumerate(p.Date) if d>z['date']);date=p.Date.iloc[i]
 valid=a[(pd.to_datetime(a.date)+pd.Timedelta(days=7)<=pd.Timestamp(date))]
 q=valid.iloc[-1];assert (pd.Timestamp(date)-pd.Timestamp(q.date)).days<=14
 rows.append(dict(anchor_date=date,target_end=p.Date.iloc[i+21],r20=100*(p.Close.iloc[i]/p.Close.iloc[i-20]-1),aaii=100*(q.bullish-q.bearish),naaim=z['naaim'],y=100*(p.Close.iloc[i+21]/p.Close.iloc[i+1]-1)))
f=pd.DataFrame(rows);observed=pd.read_csv(H/'run-01/observations.csv')
assert f.anchor_date.tolist()==observed.anchor_date.tolist()
for c in ['r20','aaii','naaim','y']:assert np.allclose(f[c],observed[c],atol=1e-9,rtol=0)
s=json.loads((H/'state.json').read_text());assert s['independent_fits']==0;errors=[]
for year in [2025,2026]:
 tr=f[f.target_end<f'{year}-01-01'];te=f[f.anchor_date.str.startswith(str(year))]
 for model,cols in {'A':['aaii'],'BA':['r20','aaii'],'BAN':['r20','aaii','naaim'],'BANI':['r20','aaii','naaim']}.items():
  x=tr[cols].to_numpy();t=te[cols].to_numpy()
  if model=='BANI':
   b=tr[['aaii','naaim']].to_numpy();mu=b.mean(0);sd=b.std(0)
   x=np.column_stack([x,((b-mu)/sd).prod(1)]);t=np.column_stack([t,((te[['aaii','naaim']].to_numpy()-mu)/sd).prod(1)])
  mu=x.mean(0);sd=x.std(0);z=np.column_stack([np.ones(len(x)),(x-mu)/sd]);zt=np.column_stack([np.ones(len(t)),(t-mu)/sd])
  penalty=np.diag([0]+[np.sqrt(len(x)*.001)]*x.shape[1])
  s['independent_fits']+=1;dump(H/'state.json',s)
  with (H/'trial-ledger.jsonl').open('a') as out:out.write(json.dumps({'phase':'independent','year':year,'model':model,'fit':s['independent_fits']})+'\n')
  coef=np.linalg.lstsq(np.vstack([z,penalty]),np.r_[tr.y,np.zeros(z.shape[1])],rcond=None)[0]
  saved=v.set_index('anchor_date').loc[te.anchor_date,'pred_'+model].to_numpy();err=float(np.max(np.abs(zt@coef-saved)));assert err<1e-8;errors.append(err)
results=json.loads((H/'run-01/results.json').read_text())
for m,stats in results['overall'].items():assert abs(np.mean((v['pred_'+m]-v.y)**2)-stats['mse_pp2'])<1e-9
old=pd.read_csv(sources['old_predictions']).set_index('anchor_date');vv=v.set_index('anchor_date')
for new,prior in [('I','I'),('B','B'),('N','X'),('BN','BX')]:assert np.allclose(vv['pred_'+new],old.loc[vv.index,'pred_'+prior],atol=1e-12,rtol=0)
dump(H/'review.json',{'passed':True,'independent_fits':8,'max_prediction_difference_pp':max(errors),'reconstructed_rows':len(f),'same_evaluation_rows':len(v),'checks':['input hashes','separate date and outcome reconstruction','augmented least squares vs normal equations','all overall errors','old benchmark predictions unchanged']})
s['execution']='completed';dump(H/'state.json',s);print(json.dumps(json.loads((H/'review.json').read_text())))
