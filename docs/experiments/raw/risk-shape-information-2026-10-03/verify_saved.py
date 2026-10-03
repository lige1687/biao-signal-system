"""Independent direct arithmetic of saved labels/features, no fitting."""
from pathlib import Path
import json, hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent

def main():
    run=HERE/'run-vol_instability20-main'
    c=json.loads((run/'contract.json').read_text());proof=json.loads((run/'preflight.json').read_text())
    data=json.loads((ROOT/c['data']['path']).read_text());cal=data['calendar'];idx={d:i for i,d in enumerate(cal)}
    arrays={a:np.array([next(r['close'] for r in data['bars'] if r['asset']==a and r['date']==d) for d in cal]) for a in c['universe']['assets']}
    max_label_error=0.; max_feature_error=0.;labels=0;features=0
    for row in proof['observations']:
        if row['asset']=='510300.SS':
            assert not row['eligible'] and row['y'] is None
            continue
        i=idx[row['date']];price=arrays[row['asset']];marketprice=arrays['510300.SS']
        if i+21<len(cal):
            expected=max(0.,float(100*(1-np.min(price[i+1:i+22])/price[i+1])))
            error=abs(expected-row['y']);max_label_error=max(error,max_label_error);assert error<1e-10
            assert row['label_end']==cal[i+21];labels+=1
        else: assert row['y'] is None and row['target_label_reason']=='immature_label'
        if row['feature_reason'] is not None: continue
        r=100*(price[i-59:i+1]/price[i-60:i]-1);m=100*(marketprice[i-59:i+1]/marketprice[i-60:i]-1)
        v=np.array([np.std(r[j-4:j+1],ddof=1) for j in range(40,60)])
        down=m<0;up=m>0
        slope=lambda mask:np.cov(m[mask],r[mask],ddof=1)[0,1]/np.var(m[mask],ddof=1)
        negative=r<0;old=negative[:-1];now=negative[1:]
        expected_features={'vol_instability20':float(np.std(v,ddof=1)/np.mean(v)),'beta_asymmetry60':float(slope(down)-slope(up)),'negative_cluster60':float(np.mean(now[old])-np.mean(now[~old]))}
        for name,expected in expected_features.items():
            error=abs(expected-row['features'][name]);max_feature_error=max(error,max_feature_error);assert error<1e-9;features+=1
    assert len(proof['observations'])==4340 and labels==3192 and features==9765
    assert proof['coverage']['per_asset']['510300.SS']['anchor_excluded']==1085
    receipt_checks=[]
    for candidate in ['vol_instability20','beta_asymmetry60','negative_cluster60']:
        for mode in ['main','solo']:
            runs={(x['candidate'],x['mode']):ROOT/x['run_path'] for x in json.loads((HERE/'trial-plan.json').read_text())['planned_experiments']}
            folder=runs[(candidate,mode)];receipt=json.loads((folder/'receipt.json').read_text())
            for fn,sha in receipt['outputs'].items():assert hashlib.sha256((folder/fn).read_bytes()).hexdigest()==sha
            assert hashlib.sha256((folder/'contract.json').read_bytes()).hexdigest()==receipt['contract_sha256']
            receipt_checks.append(str(folder.relative_to(ROOT)))
    out={'status':'passed','new_fits':0,'label_checks':labels,'candidate_value_checks':features,'max_label_error':max_label_error,'max_feature_error':max_feature_error,'anchor_exclusions':1085,'receipt_hash_checks':receipt_checks,'method':'Direct numpy arithmetic over frozen economic prices; not shared label/feature functions','known_scope':'No gap in actual qualified period; gap boundary checked independently in synthetic test'}
    target=HERE/'independent-verification.json';assert not target.exists();target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
