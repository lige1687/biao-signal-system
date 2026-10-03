"""Zero-fit audit and preplanned diagnostics of sealed workflow predictions."""
from pathlib import Path
import copy, hashlib, json, math
import numpy as np
from lei_signal.research.workflow_evaluation import summarize_predictions
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent

def read(p): return json.loads(p.read_text())
def weights(rows):
    counts={a:sum(r['asset']==a for r in rows) for a in {r['asset'] for r in rows}}
    return np.array([1/counts[r['asset']]/len(counts) for r in rows])
def metrics(rows, cols=('B0','B1','B2')):
    w=weights(rows); y=np.array([r['y'] for r in rows])
    mse={c:float(w@((np.array([r[c] for r in rows])-y)**2)) for c in cols}
    return {'mse':mse,'rmse':{c:math.sqrt(v) for c,v in mse.items()},'rows':len(rows),'dates':len({r['date'] for r in rows}),'assets':len({r['asset'] for r in rows})}
def audit_fit(result, proof, c):
    obs=[r for r in proof['observations'] if r['eligible']]
    audits=[]
    for detail in result['execution']['fit_details']:
        f=c['split']['folds'][int(detail['fold'])]
        tr=[r for r in obs if r['date']<=f['train_end'] and r['label_end']<f['eval_start']]
        ev=[r for r in result['predictions'] if r['fold']==detail['fold']]
        lookup={r['id']:r for r in obs}; cols=detail['features']; w=weights(tr)
        x=np.array([[r['features'][k] for k in cols] for r in tr]); y=np.array([r['y'] for r in tr])
        mean=w@x; sd=np.sqrt(w@((x-mean)**2)); zero=sd<1e-12; sd[zero]=1
        z=(x-mean)/sd; z[:,zero]=0
        intercept=float(w@y); coef=np.array(detail['coef'])
        residual=np.max(np.abs(((z.T*w)@z+np.eye(len(cols)))@coef-(z.T*w)@(y-intercept)))
        xe=np.array([[lookup[r['id']]['features'][k] for k in cols] for r in ev]); ze=(xe-mean)/sd; ze[:,zero]=0
        prediction=intercept+ze@coef
        maxerr=float(np.max(np.abs(prediction-np.array([r[detail['model']] for r in ev]))))
        assert np.allclose(mean,detail['mean'],atol=1e-10,rtol=1e-10)
        assert np.allclose(sd,detail['std'],atol=1e-10,rtol=1e-10)
        assert abs(intercept-detail['intercept'])<1e-10
        assert residual<1e-9 and maxerr<1e-9
        assert all(r['date']<f['eval_start'] and r['label_end']<f['eval_start'] for r in tr)
        assert all(r['label_end']<=f['eval_end'] for r in ev)
        assert not any(r['asset']=='510300.SS' for r in tr+ev)
        audits.append({'fold':detail['fold'],'model':detail['model'],'training_rows':len(tr),'evaluation_rows':len(ev),'normal_equation_residual':float(residual),'prediction_max_error':maxerr,'training_max_label_end':max(r['label_end'] for r in tr),'negative_prediction_rows':int(np.sum(prediction<0))})
    return audits

def main():
    output={}; fingerprints={}; support=None
    names=list(read(HERE/'brief.json')['candidate_definitions'])
    for name in names:
        runs={(x['candidate'],x['mode']):ROOT/x['run_path'] for x in read(HERE/'trial-plan.json')['planned_experiments']}
        mainpath=runs[(name,'main')]; solopath=runs[(name,'solo')]
        c=read(mainpath/'contract.json'); proof=read(mainpath/'preflight.json'); result=read(mainpath/'result.json'); solo=read(solopath/'result.json')
        rows=result['predictions']; expected={r['id'] for r in rows}
        assert expected=={r['id'] for r in solo['predictions']}
        if support is None: support=expected
        assert support==expected
        headline=metrics(rows)
        for item in result['performance']:
            assert abs(headline[item['metric'].lower()][item['model']]-item['value'])<1e-10
        audits=audit_fit(result,proof,c)+audit_fit(solo,read(solopath/'preflight.json'),read(solopath/'contract.json'))
        obs=[r for r in proof['observations'] if r['eligible']]
        simple=[]
        for p in rows:
            fold=c['split']['folds'][int(p['fold'])]
            tr=[r for r in obs if r['asset']==p['asset'] and r['date']<=fold['train_end'] and r['label_end']<fold['eval_start']]
            histmean=float(np.mean([r['y'] for r in tr]))
            days=[d for d in c['calendar'] if d<p['date']][-120:]
            rolling=[r['y'] for r in obs if r['asset']==p['asset'] and r['label_end'] in days]
            assert rolling
            simple.append({**p,'asset_mean':histmean,'rolling_mature120':float(np.mean(rolling))})
        sm=metrics(simple,('B0','asset_mean','rolling_mature120','B1','B2'))
        simple_increment={}
        for baseline in ['asset_mean','rolling_mature120']:
            rr=[{**r,'B1':r[baseline]} for r in simple]
            simple_increment[baseline]=summarize_predictions(rr,c,proof['observations'])['increments'][0]
        periods={yr:metrics([r for r in rows if r['date'][:4]==yr]) for yr in sorted({r['date'][:4] for r in rows})}
        assets={a:metrics([r for r in rows if r['asset']==a]) for a in sorted({r['asset'] for r in rows})}
        leaveout={a:metrics([r for r in rows if r['asset']!=a]) for a in assets}
        cc=copy.deepcopy(c); cc['dependence']['block_length']=120
        sens=summarize_predictions(rows,cc,proof['observations'])['increments'][0]
        dates=sorted({r['date'] for r in rows}); w=weights(rows)
        daily={d:float(sum(w[i]*((r['B1']-r['y'])**2-(r['B2']-r['y'])**2) for i,r in enumerate(rows) if r['date']==d)) for d in dates}
        absolute=sum(abs(v) for v in daily.values()); extreme=sorted(daily.items(),key=lambda x:abs(x[1]),reverse=True)[:10]
        output[name]={'core':headline,'solo':metrics(solo['predictions']),'increment':result['increments'][0],'simple_baselines':sm,'vs_simple_increment':simple_increment,'periods':periods,'assets':assets,'leave_one_asset_out':leaveout,'block120_increment':sens,'fit_boundary_audit':audits,'top10_abs_daily_share':sum(abs(v) for _,v in extreme)/absolute if absolute else 0,'top10_date_contributions':extreme,'common_support_asserted':True,'new_fits':0}
        for run in [mainpath,solopath]:
            for fn in ['contract.json','preflight.json','result.json','receipt.json']:
                pp=run/fn; fingerprints[str(pp.relative_to(ROOT))]=hashlib.sha256(pp.read_bytes()).hexdigest()
    target=HERE/'diagnostics.json'
    assert not target.exists()
    target.write_text(json.dumps({'candidates':output,'fingerprints':fingerprints,'execution':{'new_fits':0,'real_fits_verified':24,'analysis':'preplanned auxiliary calculations of sealed predictions'},'uncertainty_limit':'95 percent intervals conditional on seen history/model; three tests exploratory, no multiple-test promotion; 120-day blocks offer few segments'},ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({n:{'rmse':v['core']['rmse'],'solo_rmse':v['solo']['rmse'],'increment':v['increment'],'simple':v['simple_baselines']['rmse'],'periods':v['periods']} for n,v in output.items()},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
