"""Portable, standard-library-only summary check. Never refits or fetches."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--require-inputs',action='store_true');args=ap.parse_args()
    freeze=json.loads((ROOT/'execution-freeze.json').read_text())
    for name,digest in freeze['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    r=json.loads((ROOT/'run-01/results.json').read_text())
    state=json.loads((ROOT/'research-state.json').read_text())
    review=json.loads((ROOT/'independent-review.json').read_text())
    assert state['core_fits']==4 and state['review_fits']==4 and review['passed']
    assert state['source_operations']==state['pro_calls']==state['paid_actions']==0
    assert r['overall']['I']['n']==78 and sum(v['I']['n'] for v in r['years'].values())==78
    for model in ['I','B','X','BX','P','PX']:
        weighted=sum(v[model]['mse_pp2']*v[model]['n'] for v in r['years'].values())/78
        assert math.isclose(weighted,r['overall'][model]['mse_pp2'],rel_tol=1e-12)
        for table in [r['overall'],*r['years'].values()]:
            assert math.isclose(table[model]['rmse_pp']**2,table[model]['mse_pp2'],rel_tol=1e-12)
    for table in [r['overall'],*r['years'].values()]:
        for a,b in [('PX','P'),('PX','I'),('BX','B'),('P','B'),('PX','BX')]:
            assert math.isclose(table[f'{a}_vs_{b}_improvement_pct'],100*(1-table[a]['mse_pp2']/table[b]['mse_pp2']),rel_tol=1e-12)
    assert r['adjacent_targets']['overlapping_pairs']==77
    if args.require_inputs:
        missing=[]
        for row in json.loads((ROOT/'inputs.json').read_text())['files']:
            p=REPO/row['path']
            if not p.exists():missing.append(row['path']);continue
            assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
        if missing:
            print(json.dumps({'summary_passed':True,'full_market_recovery':'blocked','missing_inputs':missing},ensure_ascii=False));return 2
    print(json.dumps({'saved_summary_passed':True,'market_fits':0,'input_files_checked':args.require_inputs}));return 0


if __name__=='__main__':raise SystemExit(main())
