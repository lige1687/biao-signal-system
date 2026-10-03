"""Read-only independent arithmetic and preregistered state descriptions.

--source-audit requires the original authorized panel; default saved-result
verification does not need market inputs and never fits a model.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np

R=Path(__file__).resolve().parent
ROOT=R.parents[3]
MODELS=('B0','B1','B2','ETF_mean')

def load(p): return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def score(rows):
    assets=sorted({r['asset'] for r in rows})
    if not rows:return {'rows':0,'dates':0,'assets':[]}
    mse={m:float(np.mean([np.mean([(r[m]-r['y'])**2 for r in rows if r['asset']==a]) for a in assets])) for m in MODELS}
    return {'rows':len(rows),'dates':len({r['date'] for r in rows}),'assets':assets,
            'mse':mse,'rmse':{m:math.sqrt(v) for m,v in mse.items()},
            'rmse_improvement':math.sqrt(mse['B1'])-math.sqrt(mse['B2']),
            'mse_improvement_percent':100*(1-mse['B2']/mse['B1'])}

def uncertainty(rows,axis,length):
    assets=sorted({r['asset'] for r in rows});loc={d:i for i,d in enumerate(axis)}
    sums=np.zeros((len(axis),len(assets),2));counts=np.zeros((len(axis),len(assets)))
    for r in rows:
        i,j=loc[r['date']],assets.index(r['asset']);counts[i,j]+=1
        sums[i,j]=[(r[m]-r['y'])**2 for m in ('B1','B2')]
    rng=np.random.default_rng(20261003);deltas=[]
    for _ in range(1000):
        starts=rng.integers(0,len(axis),math.ceil(len(axis)/length))
        ix=((starts[:,None]+np.arange(length))%len(axis)).ravel()[:len(axis)]
        mult=np.bincount(ix,minlength=len(axis));den=mult@counts
        if np.any(den==0):continue
        mse=(np.einsum('d,dam->am',mult,sums)/den[:,None]).mean(axis=0)
        deltas.append(math.sqrt(mse[0])-math.sqrt(mse[1]))
    return {'length':length,'draws':1000,'valid':len(deltas),'axis_dates':len(axis),
            'rmse_improvement_range':np.quantile(deltas,[.025,.975]).tolist()}

def describe(rows):
    if not rows:return {'rows':0,'dates':0,'assets':[],'metrics':None}
    assets=sorted({r['asset'] for r in rows})
    fields=('return','up','return_over5','mae','mfe','drawdown','mae_over5','mae_over10','mae_over15')
    return {'rows':len(rows),'dates':len({r['date'] for r in rows}),'assets':assets,
            'per_asset_rows':{a:sum(r['asset']==a for r in rows) for a in assets},
            'metrics':{k:float(np.mean([np.mean([r[k] for r in rows if r['asset']==a]) for a in assets])) for k in fields},
            'weighting':'each represented ETF has equal total weight; compare coverage before interpreting differences'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--source-audit',action='store_true')
    args=ap.parse_args();dest=Path(args.out)
    if dest.exists():raise RuntimeError('refuse overwrite')
    answer={};source=None;obs=None
    for name in ('return','risk'):
        core=R/name/'core-01';contract=load(core/'contract.json');result=load(core/'result.json')
        rows=[dict(r) for r in result['predictions']];folds=contract['split']['folds']
        means={};training={}
        if args.source_audit:
            original=load(core/'preflight.json')['observations']
            for j,f in enumerate(folds):
                train=[r for r in original if r['eligible'] and r['date']<=f['train_end'] and r['label_end']<f['eval_start']]
                training[str(j)]={}
                for a in contract['universe']['assets']:
                    ar=[r['y'] for r in train if r['asset']==a];means[(str(j),a)]=sum(ar)/len(ar)
                    training[str(j)][a]={'mean':means[(str(j),a)],'rows':len(ar)}
        else:
            saved=load(R/'audit-02.json')[name]
            assert saved['contract_sha256']==sha(core/'contract.json') and saved['result_sha256']==sha(core/'result.json')
            training=saved['training_means']
            means={(f,a):v['mean'] for f,assets in training.items() for a,v in assets.items()}
        for r in rows:
            r['ETF_mean']=means[(r['fold'],r['asset'])]
            f=folds[int(r['fold'])];assert f['eval_start']<=r['date']<r['label_end']<=f['eval_end']
        s=score(rows)
        for v in result['performance']:
            if v['metric']=='RMSE':assert abs(s['rmse'][v['model']]-v['value'])<1e-10
        axis=contract['calendar'];axis=[d for d in axis if folds[0]['eval_start']<=d<=folds[-1]['eval_end']]
        # Persist the exact calendar; portable verification must not reconstruct
        # it from only the dates with mature predictions.
        answer[name]={'all':s,'by_year':{y:score([r for r in rows if r['date'][:4]==y]) for y in ('2025','2026')},
                      'by_asset':{a:score([r for r in rows if r['asset']==a]) for a in s['assets']},
                      'leave_one_asset_out':{a:score([r for r in rows if r['asset']!=a]) for a in s['assets']},
                      'uncertainty':{str(n):uncertainty(rows,axis,n) for n in (60,120)},
                      'negative_predictions':{m:sum(r[m]<0 for r in rows) for m in MODELS},
                      'contract_sha256':sha(core/'contract.json'),'result_sha256':sha(core/'result.json'),
                      'training_means':training,'new_fits':0,'source_label_checks':0}
        if args.source_audit:
            if source is None:
                p=ROOT/contract['data']['path'];assert sha(p)==contract['data']['sha256'];source=load(p)
                cal=source['calendar'];loc={d:i for i,d in enumerate(cal)};bars={(b['asset'],b['date']):b for b in source['bars']}
            for r in rows:
                i=loc[r['date']];path=[bars[(r['asset'],d)]['close'] for d in cal[i+1:i+62]]
                assert len(path)==61 and cal[i+61]==r['label_end']
                y=100*(path[-1]/path[0]-1) if name=='return' else 100*max(0,1-min(path)/path[0])
                assert abs(y-r['y'])<1e-10
            for j,f in enumerate(folds):
                train=[r for r in original if r['eligible'] and r['date']<=f['train_end'] and r['label_end']<f['eval_start']]
                independent={a:[] for a in contract['universe']['assets']}
                for r in train:
                    i=loc[r['date']];path=[bars[(r['asset'],d)]['close'] for d in cal[i+1:i+62]]
                    assert len(path)==61 and cal[i+61]==r['label_end'] and r['label_end']<f['eval_start']
                    y=100*(path[-1]/path[0]-1) if name=='return' else 100*max(0,1-min(path)/path[0])
                    assert abs(y-r['y'])<1e-10;independent[r['asset']].append(y)
                for a,vals in independent.items():assert abs(sum(vals)/len(vals)-means[(str(j),a)])<1e-10
                weighted=sum(means[(str(j),a)] for a in independent)/len(independent)
                assert all(abs(r['B0']-weighted)<1e-10 for r in rows if r['fold']==str(j))
            answer[name]['source_label_checks']=len(rows)
            if name=='return':obs=original
    if args.source_audit:
        groups={}
        for h in (5,10,20,60,120):
            derived=[]
            for row in obs:
                if not row['ready_252']:continue
                i=loc[row['date']]
                if i+h+1>=len(cal):continue
                path=[bars[(row['asset'],d)]['close'] for d in cal[i+1:i+h+2]]
                peak=path[0];dd=0
                for p in path:peak=max(peak,p);dd=max(dd,100*(1-p/peak))
                ret=100*(path[-1]/path[0]-1);mae=100*max(0,1-min(path)/path[0])
                derived.append({'asset':row['asset'],'date':row['date'],'color20':row['color20'],'color60':row['color60'],
                    'first_color60':row['first_color60'],'return':ret,'up':100*int(ret>0),'return_over5':100*int(ret>5),
                    'mae':mae,'mfe':100*max(0,max(path)/path[0]-1),'drawdown':dd,
                    **{'mae_over'+str(n):100*int(mae>n) for n in (5,10,15)},'label_end':cal[i+h+1]})
            gs={'all':describe(derived),'color60':{c:describe([r for r in derived if r['color60']==c]) for c in ('green','black','gray')},
                'joint':{a+'/'+b:describe([r for r in derived if r['color20']==a and r['color60']==b]) for a in ('green','black','gray') for b in ('green','black','gray')},
                'by_year':{y:{c:describe([r for r in derived if r['date'][:4]==y and r['color60']==c]) for c in ('green','black','gray')} for y in ('2022','2023','2024','2025','2026')},
                'by_asset':{a:{c:describe([r for r in derived if r['asset']==a and r['color60']==c]) for c in ('green','black','gray')} for a in contract['universe']['assets']},
                'first_transition':{c:describe([r for r in derived if r['first_color60'] and r['color60']==c]) for c in ('green','black','gray')},
                'fixed_stride121':{c:describe([r for r in derived if (loc[r['date']]-loc['2022-01-04'])%121==0 and r['color60']==c]) for c in ('green','black','gray')}}
            # The SMA-only groups and confirmation describe representation,
            # not conditional causal effects. Use source features, never outcomes,
            # to define these categories.
            obmap={(r['asset'],r['date']):r for r in obs}
            def sma_direction(r):
                v=obmap[(r['asset'],r['date'])]['features']['ret60']
                return (v>0)-(v<0)
            gs['SMA60_direction']={str(s):describe([r for r in derived if sma_direction(r)==s]) for s in (-1,0,1)}
            groups[str(h)]=gs
        answer['descriptive']=groups
        answer['descriptive_limits']='all historical dates; different state dates; ETF equal weight within represented assets; year groups may have labels extending into next year; fixed stride tiny and calendar-phase dependent, not new independent data'
        # Direct production recurrence and deduction-price identity check; this
        # implementation never calls the research adapter or indicator module.
        checks=0;states={(r['asset'],r['date']):r for r in obs}
        for a in contract['universe']['assets']:
            closes=[bars[(a,d)]['close'] for d in cal]
            for n in (20,60):
                ema=sum(closes[:n])/n
                for i in range(n,len(closes)):
                    ema=closes[i]*2/(n+1)+ema*(1-2/(n+1))
                    if (a,cal[i]) not in states:continue
                    r=states[(a,cal[i])]
                    if not r['ready_252']:continue
                    color='green' if closes[i]>ema and closes[i]>closes[i-n] else 'black' if closes[i]<ema and closes[i]<closes[i-n] else 'gray'
                    assert color==r['color'+str(n)];checks+=1
        answer['independent_state_checks']=checks
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(answer,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({n:answer[n]['all'] for n in ('return','risk')},ensure_ascii=False))

if __name__=='__main__':main()
