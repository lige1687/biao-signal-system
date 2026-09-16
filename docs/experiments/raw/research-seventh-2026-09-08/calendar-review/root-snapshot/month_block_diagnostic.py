"""Composition sensitivity, explicitly not confidence intervals or Reality Check."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(P/'spark'))
from month_blocks import draw_indices
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

lock=json.loads((P/'month-block-lock.json').read_text())
assert all(sha(Path(k))==v for k,v in lock['files'].items())
d=pd.read_csv(P/'calendar-monthly.csv');months=sorted(set(d.month));T=len(months)
keys=[];vectors=[]
for mod in ['A','B','C']:
    for sizing in ['same_budget','same_planned_risk']:
        g=d[(d.module==mod)&(d.sizing==sizing)].pivot(index='month',columns='arm',values='per_opportunity_contribution').loc[months]
        assert len(g)==T and g.notna().all().all()
        keys.append(f'{mod}:{sizing}');vectors.append((g.buffer-g.base).to_numpy())
values=np.array(vectors).T
summaries=[]
for L in [6,12,24]:
    idx=draw_indices(T,L,5000,20260908+L)
    assert idx.shape==(5000,T) and idx.min()>=0 and idx.max()<T
    for start in range(0,T,L):
        if min(L,T-start)>1:assert (np.diff(idx[:,start:min(start+L,T)],axis=1)==1).all()
    counts=np.zeros((5000,T),dtype=np.int32)
    for r in range(5000):counts[r]=np.bincount(idx[r],minlength=T)
    assert (counts.sum(axis=1)==T).all()
    samples=counts@values
    assert np.allclose(samples[:3],values[idx[:3]].sum(axis=1),atol=1e-12)
    assert np.allclose(counts@np.zeros(T),0)
    np.savez_compressed(P/f'month-indices-L{L}.npz',indices=idx,months=np.array(months),columns=np.array(keys))
    pd.DataFrame(samples,columns=keys).to_csv(P/f'month-composition-draws-L{L}.csv',index=False)
    for col,key in enumerate(keys):
        lo,med,hi=np.quantile(samples[:,col],[.05,.5,.95])
        summaries.append({'series':key,'block_months':L,'draws':5000,'months_per_draw':T,'original_total_delta':float(values[:,col].sum()),'middle90_low':float(lo),'median':float(med),'middle90_high':float(hi),'shared_index_sha256':sha(P/f'month-indices-L{L}.npz')})
result={'status':'post_hoc_composition_sensitivity_only','not_confidence_intervals':True,'not_future_probability':True,'not_real_tradable_paths':True,'not_whole_history_search_correction':True,'calendar_window':[months[0],months[-1]],'series':summaries,'code_sha256':sha(Path(__file__)),'spark_helper_sha256':sha(P/'spark/month_blocks.py'),'protocol_sha256':sha(P/'month-block-protocol.md')}
(P/'month-block-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
