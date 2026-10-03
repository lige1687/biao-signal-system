"""Fixed counterexamples and independent arithmetic; no model fits or data fetch."""
from pathlib import Path
from statistics import mean,stdev
import hashlib,json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[4]; RAW=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from lei_signal.research.workflow_evaluation import _block_draws
from lei_signal.research.workflow import verify_receipt

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,value):
 with p.open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
def main():
 out=RAW/'run-01'; verify_receipt(out,ROOT)
 r=json.loads((out/'result.json').read_text()); c=json.loads((out/'contract.json').read_text()); proof=json.loads((out/'preflight.json').read_text())
 assert r['execution']['fits']==4
 obs=proof['observations']; by_id={v['id']:v for v in obs}; frame=pd.DataFrame(r['predictions'])
 assert len(frame)==1268 and frame.id.is_unique
 assert frame.groupby('date').asset.nunique().eq(4).all()
 per_fold=[]; am=[]; pv=[]
 for fidx,fold in enumerate(c['split']['folds']):
  train=[v for v in obs if v['eligible'] and v['date']<=fold['train_end'] and v['label_end']<fold['eval_start']]
  ev=frame[frame.fold.eq(str(fidx))]
  assert ev.label_end.le(fold['eval_end']).all()
  means={a:mean(v['y'] for v in train if v['asset']==a) for a in c['universe']['assets']}
  assert abs(mean(means.values())-float(ev.B0.iloc[0]))<1e-12
  per_fold.append({'fold':str(fidx),'training_rows':len(train),'evaluation_rows':len(ev),'asset_training_means':means,'train_latest_label':max(v['label_end'] for v in train),'evaluation_latest_label':ev.label_end.max()})
  for v in ev.to_dict('records'):
   am.append((v['id'],means[v['asset']]))
 for v in frame.to_dict('records'): pv.append((v['id'],by_id[v['id']]['features']['volatility20']))
 frame['asset_mean']=frame.id.map(dict(am)); frame['persistence']=frame.id.map(dict(pv))
 models=['B0','asset_mean','persistence','B1','B2']
 def metrics(f):
  d={}
  for k in models:
   mse=float(((f[k]-f.y)**2).groupby(f.asset).mean().mean())
   d[k]={'MSE':mse,'RMSE':float(np.sqrt(mse))}
  d['B2_vs_B1_reduction']=d['B1']['MSE']-d['B2']['MSE']
  d['B2_vs_asset_mean_reduction']=d['asset_mean']['MSE']-d['B2']['MSE']
  d['rows']=len(f);d['dates']=int(f.date.nunique()); return d
 overall=metrics(frame)
 for p in r['performance']: assert abs(overall[p['model']][p['metric']]-p['value'])<1e-12
 groups={'asset':{a:metrics(f) for a,f in frame.groupby('asset')},'year':{a:metrics(f) for a,f in frame.groupby(frame.date.str[:4])},'asset_year':{f'{a}|{y}':metrics(f) for (a,y),f in frame.groupby([frame.asset,frame.date.str[:4]])},'leave_one_asset_out_no_refit':{a:metrics(frame[frame.asset.ne(a)]) for a in c['universe']['assets']}}
 panel=json.loads((ROOT/c['data']['path']).read_text()); bar={ (x['asset'],x['date']):x for x in panel['bars'] }; index={d:i for i,d in enumerate(panel['calendar'])}; manual=[]
 for row in [frame.iloc[0],frame[frame.asset.eq('588000.SS')].iloc[0],frame[frame.fold.eq('1')].iloc[-1]]:
  j=index[row.date]; closes=[bar[(row.asset,panel['calendar'][n])]['close'] for n in range(j+1,j+22)]
  actual=100*stdev([b/a-1 for a,b in zip(closes,closes[1:])]); assert abs(actual-row.y)<1e-12
  past=[bar[(row.asset,panel['calendar'][n])]['close'] for n in range(j-20,j+1)]
  current=100*stdev([b/a-1 for a,b in zip(past,past[1:])]); expected=by_id[row.id]['features']['volatility20']; assert abs(current-expected)<1e-12
  manual.append({'id':row.id,'target_manual':actual,'target_saved':row.y,'feature_manual':current,'feature_saved':expected})
 axis=[d for d in c['calendar'] if any(f['eval_start']<=d<=f['eval_end'] for f in c['split']['folds'])]
 intervals={}
 for block in [60,120]:
  for old in ['B1','asset_mean','persistence']:
   difference=((frame[old]-frame.y)**2-(frame.B2-frame.y)**2).to_numpy()
   draws,bad=_block_draws(frame,difference,axis,'equal_asset',dict(c['dependence'],block_length=block))
   intervals[f'B2_vs_{old}_block{block}']={'lo':float(np.quantile(draws,.025)),'hi':float(np.quantile(draws,.975)),'unestimable_draws':bad,'seed':c['dependence']['seed'],'draws':len(draws),'evaluation_axis_dates':len(axis)}
 assert abs(intervals['B2_vs_B1_block60']['lo']-r['increments'][0]['lo'])<1e-12
 result={'scope':'saved predictions and mature train targets only; zero extra fits','overall':overall,'groups':groups,'intervals':intervals,'manual_arithmetic':manual,'folds':per_fold,'negative_predictions':{k:int((frame[k]<0).sum()) for k in models},'fingerprints':{str(out.relative_to(ROOT)/n):sha(out/n) for n in ['contract.json','preflight.json','result.json','receipt.json']},'real_fits':4,'extra_fits':0}
 dump(RAW/'saved-result-checks.json',result)
 print(json.dumps({'overall':overall,'intervals':intervals,'assets':groups['asset'],'leave_out':groups['leave_one_asset_out_no_refit']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
