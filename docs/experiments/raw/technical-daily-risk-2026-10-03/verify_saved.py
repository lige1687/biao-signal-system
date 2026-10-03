"""Independent arithmetic, fixed block sensitivity and optional source-label audit.
No feature generation, fitting, network or writes to sealed results.
"""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np

BASE=Path(__file__).resolve().parent
MODELS=('B0','B1','B2')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def score(rows):
    assets=sorted({r['asset'] for r in rows})
    mse={m:sum(sum((r[m]-r['y'])**2 for r in rows if r['asset']==a)/sum(r['asset']==a for r in rows) for a in assets)/len(assets) for m in MODELS}
    values={m:math.sqrt(mse[m]) for m in MODELS}
    return {'rows':len(rows),'dates':len({r['date'] for r in rows}),'assets':assets,'rmse':values,'mse':mse,'rmse_improvement':values['B1']-values['B2'],'mean_actual_risk':sum(sum(r['y'] for r in rows if r['asset']==a)/sum(r['asset']==a for r in rows) for a in assets)/len(assets)}
def blocks(rows,axis,length):
    assets=sorted({r['asset'] for r in rows}); loc={d:i for i,d in enumerate(axis)}
    # date x asset x model sufficient sums retain same-day assets.
    sums=np.zeros((len(axis),len(assets),3));counts=np.zeros((len(axis),len(assets)))
    for r in rows:
        i,j=loc[r['date']],assets.index(r['asset']);counts[i,j]+=1
        for k,m in enumerate(MODELS):sums[i,j,k]+=(r[m]-r['y'])**2
    rng=np.random.default_rng(20261003);mse_deltas=[];rmse_deltas=[]
    for _ in range(1000):
        starts=rng.integers(0,len(axis),math.ceil(len(axis)/length)); chosen=((starts[:,None]+np.arange(length))%len(axis)).ravel()[:len(axis)]
        mult=np.bincount(chosen,minlength=len(axis));den=mult@counts
        if (den==0).any():continue
        mse=(np.einsum('d,dam->am',mult,sums)/den[:,None]).mean(axis=0)
        mse_deltas.append(mse[1]-mse[2]);rmse_deltas.append(np.sqrt(mse[1])-np.sqrt(mse[2]))
    return {'block_length':length,'draws':1000,'valid':len(mse_deltas),'seed':20261003,'mse_improvement_range':np.quantile(mse_deltas,[.025,.975]).tolist(),'rmse_improvement_range':np.quantile(rmse_deltas,[.025,.975]).tolist(),'axis_dates':len(axis)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--source-audit',action='store_true');args=ap.parse_args();out=Path(args.output)
    if out.exists():raise RuntimeError('new output required')
    all_results={}
    for name in ('slope','age'):
        cpath=BASE/name/'freeze-01/contract.json';rpath=BASE/name/'core-01/result.json'
        c=json.loads(cpath.read_text());result=json.loads(rpath.read_text());rows=result['predictions'];s=score(rows)
        for r in result['performance']:
            if r['metric']=='RMSE':assert abs(s['rmse'][r['model']]-r['value'])<1e-10
        axis=json.loads((BASE/'evaluation-axis.json').read_text())
        ci={str(n):blocks(rows,axis,n) for n in (20,60)}
        inc=next(x for x in result['increments'] if x['old_model']=='B1')
        assert max(abs(ci['20']['mse_improvement_range'][i]-inc[k]) for i,k in enumerate(('lo','hi')))<1e-10
        assets=s['assets'];periods=sorted({r['date'][:4] for r in rows}); audited=0;err=0.;train_audit=[]
        for r in rows:
            f=c['split']['folds'][int(r['fold'])];assert f['eval_start']<=r['date']<=r['label_end']<=f['eval_end']
        if args.source_audit:
            repo=BASE.parents[3];panel=json.loads((repo/c['data']['path']).read_text());assert sha(repo/c['data']['path'])==c['data']['sha256'];cal=panel['calendar'];ix={d:i for i,d in enumerate(cal)};bars={(b['asset'],b['date']):b for b in panel['bars']}
            for r in rows:
                i=ix[r['date']];path=[bars[(r['asset'],d)]['close'] for d in cal[i+1:i+22]];value=100*max(0,1-min(path)/path[0]);err=max(err,abs(value-r['y']));audited+=1;assert len(path)==21 and cal[i+21]==r['label_end']
            assert err<1e-10
            proof=json.loads((BASE/name/'core-01/preflight.json').read_text())
            for j,f in enumerate(c['split']['folds']):
                train=[r for r in proof['observations'] if r['eligible'] and r['date']<=f['train_end'] and r['label_end']<=f['train_end']]
                assert all(r['label_end']<f['eval_start'] for r in train)
                mean=score([dict(r,B0=0,B1=0,B2=0) for r in train])['mean_actual_risk']
                values=[r['B0'] for r in rows if r['fold']==str(j)];assert max(abs(v-mean) for v in values)<1e-10
                train_audit.append({'fold':j,'rows':len(train),'mean_risk':mean,'labels_mature_before_evaluation':True})
        all_results[name]={'all':s,'by_period':{y:score([r for r in rows if r['date'].startswith(y)]) for y in periods},'by_asset':{a:score([r for r in rows if r['asset']==a]) for a in assets},'leave_one_asset_out':{a:score([r for r in rows if r['asset']!=a]) for a in assets},'uncertainty':ci,'negative_prediction_counts':{m:sum(r[m]<0 for r in rows) for m in MODELS},'source_label_checks':audited,'max_label_difference':err if audited else None,'train_audit':train_audit,'inputs':{'contract_sha256':sha(cpath),'result_sha256':sha(rpath)},'fits':0}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(all_results,ensure_ascii=False,indent=2)+'\n');print(json.dumps({n:{'rmse':d['all']['rmse'],'delta':d['all']['rmse_improvement'],'ranges':d['uncertainty'],'source_labels':d['source_label_checks'],'by_period':d['by_period']} for n,d in all_results.items()},ensure_ascii=False))
if __name__=='__main__':main()
