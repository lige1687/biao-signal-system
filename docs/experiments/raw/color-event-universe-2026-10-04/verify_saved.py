"""Portable arithmetic/receipt check; no fitting and no market data required."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10):
        raise ValueError(f'arithmetic mismatch {a} != {b}')

def verify(base):
    index=load(base/'evidence-index.json'); summary=[]
    for name,rel in index['results'].items():
        p=base/rel; d=load(p); receipt=load(p.with_name('receipt.json'))
        assert sha(p)==receipt['outputs']['result.json'],name+' changed result bytes'
        assert sha(p.with_name('contract.json'))==receipt['contract_sha256'],name+' changed contract'
        c=load(p.with_name('contract.json')); rows=d['predictions']; n=collections.Counter(r['asset'] for r in rows)
        assert len({r['id'] for r in rows})==len(rows)
        values={}
        for model in ['B0','B1','B2']:
            values[model]=sum((r[model]-r['y'])**2/(len(n)*n[r['asset']]) for r in rows)
        for r in rows:
            fold=c['split']['folds'][int(r['fold'])]
            assert fold['eval_start']<=r['date']<=r['label_end']<=fold['eval_end']
            assert fold['train_end']<fold['eval_start']
        for pvalue in d['performance']:
            model=pvalue['model'];metric=pvalue['metric']
            if model in values:
                if metric=='RMSE':close(pvalue['value'],math.sqrt(values[model]))
                elif metric=='MSE':close(pvalue['value'],values[model])
                assert pvalue['rows']==len(rows)
        for r in d['increments']:
            close(r['old_value'],values[r['old_model']]);close(r['new_value'],values[r['new_model']])
            close(r['absolute_error_improvement'],values[r['old_model']]-values[r['new_model']])
        assert d['execution']['fits']==4
        summary.append({'branch':name,'rows':len(rows),'dates':len({r['date'] for r in rows}),
                        'baseline_rmse':math.sqrt(values['B1']),'candidate_rmse':math.sqrt(values['B2'])})
    assert len(summary)==4
    return {'saved_evidence_verified':True,'new_fits':0,'branches':summary,
            'not_verified':['original market provenance','future live validity','full trading strategy']}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=Path(__file__).parent)
    print(json.dumps(verify(ap.parse_args().directory),ensure_ascii=False,indent=2))
