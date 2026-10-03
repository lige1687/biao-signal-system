"""One bounded saved-prediction audit; shared evaluator handles uncertainty, no new fits."""
from pathlib import Path
import copy, hashlib, json, math, time
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
    started=time.monotonic()
    mainpath=HERE/'run-main'; solopath=HERE/'run-solo'
    c=read(mainpath/'contract.json'); proof=read(mainpath/'preflight.json'); result=read(mainpath/'result.json'); solo=read(solopath/'result.json')
    rows=result['predictions']; expected={r['id'] for r in rows}
    assert expected=={r['id'] for r in solo['predictions']} and len(rows)==951
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
    # All 21 pre-fixed phases of the original calendar; no selected best phase.
    index={d:i for i,d in enumerate(c['calendar'])}
    phases=[]
    for phase in range(21):
        selected=[r for r in rows if index[r['date']]%21==phase]
        dates=sorted({r['date'] for r in selected})
        assert all(index[b]-index[a]>=21 for a,b in zip(dates,dates[1:]))
        m=metrics(selected); phases.append({'phase':phase,**m,'improvement':m['mse']['B1']-m['mse']['B2']})
    assert sum(x['rows'] for x in phases)==951
    assert abs(sum(x['improvement']*x['rows']/951 for x in phases)-result['increments'][0]['absolute_error_improvement'])<1e-10
    # Frozen diagnostic only: one quoted day's maximum volume share in past20.
    # Classification uses only current/past volumes; no refitting or best cutoff.
    panel=read(ROOT/c['data']['path']); bykey={(r['asset'],r['date']):r for r in panel['bars']}
    shares={}
    for r in rows:
        end=index[r['date']]; vv=[bykey[(r['asset'],d)]['volume'] for d in c['calendar'][end-19:end+1]]
        shares[r['id']]=max(vv)/sum(vv)
    flags={k:v>=0.20 for k,v in shares.items()}
    action_groups={str(flag):metrics([r for r in rows if flags[r['id']]==flag]) for flag in [False,True] if any(flags[r['id']]==flag for r in rows)}
    action_weights={str(flag):float(sum(weights(rows)[i] for i,r in enumerate(rows) if flags[r['id']]==flag)) for flag in [False,True]}
    w=weights(rows)
    action_contributions={str(flag):float(sum(w[i]*((r['y']-r['B1'])**2-(r['y']-r['B2'])**2) for i,r in enumerate(rows) if flags[r['id']]==flag)) for flag in [False,True]}
    assert abs(sum(action_contributions.values())-result['increments'][0]['absolute_error_improvement'])<1e-10
    dates=sorted({r['date'] for r in rows}); daily={d:float(sum(w[i]*((r['B1']-r['y'])**2-(r['B2']-r['y'])**2) for i,r in enumerate(rows) if r['date']==d)) for d in dates}
    extreme=sorted(daily.items(),key=lambda x:abs(x[1]),reverse=True)[:10]
    sign_counts={'better':sum((r['y']-r['B1'])**2>(r['y']-r['B2'])**2 for r in rows),'worse':sum((r['y']-r['B1'])**2<(r['y']-r['B2'])**2 for r in rows),'same':sum(r['B1']==r['B2'] for r in rows)}
    fingerprints={str((path/f).relative_to(ROOT)):hashlib.sha256((path/f).read_bytes()).hexdigest() for path in [mainpath,solopath] for f in ['contract.json','preflight.json','result.json','receipt.json']}
    result={'core':headline,'solo':metrics(solo['predictions']),'increment':result['increments'][0],'simple_baselines':sm,'vs_simple_increment':simple_increment,'periods':periods,'assets':assets,'leave_one_asset_out':leaveout,'block120_increment':sens,'fit_boundary_audit':audits,'phases21':phases,'volume_concentration_sensitivity':{'definition':'max past20 volume share >=0.20 vs <0.20; predetermined before effects; same saved predictions no fit','groups':action_groups,'original_weights':action_weights,'original_weight_contributions':action_contributions,'share_range':[min(shares.values()),max(shares.values())]},'top10_date_contributions':extreme,'top10_remaining_original_weight_improvement':sum(daily.values())-sum(v for _,v in extreme),'sign_counts':sign_counts,'common_support_asserted':True,'fingerprints':fingerprints,'execution':{'new_fits':0,'real_fits_verified':8,'seconds':time.monotonic()-started},'limits':'All history seen; dates/ETFs related; 60/120 draws conditional and few blocks; phase alternatives correlated. Baseline review adapter absent locally, reused prior experiment arithmetic under this raw only, no platform created.'}
    target=HERE/'diagnostics.json'; assert not target.exists()
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (HERE/'simple-reference-predictions.json').write_text(json.dumps(simple,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['core','solo','simple_baselines','vs_simple_increment','periods','assets','volume_concentration_sensitivity','execution','sign_counts']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
