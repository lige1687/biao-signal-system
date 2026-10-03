"""Different linear algebra and direct CSV arithmetic; no executor import."""
import csv
import json
import math
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parent
obs = list(csv.DictReader((R/'run-01/all-observations.csv').open()))
pred = list(csv.DictReader((R/'run-01/predictions.csv').open()))
results = json.loads((R/'run-01/results.json').read_text())
oracle = json.loads((R/'independent-label-review/independent-labels.json').read_text())
models = {'I': [], 'B': ['r20'], 'X': ['b20'], 'BX': ['r20','b20'], 'BXD': ['r20','b20','delta20']}
train = [r for r in obs if r['partition'] == 'train']
evaluation = [r for r in obs if r['partition'] == 'eval']
retained = [r for r in train if not (r['target_start'] <= '2025-04-30' and r['target_end'] >= '2025-04-01')]
assert (len(obs),len(train),len(pred),len(retained)) == (343,175,147,149)
assert [r['date'] for r in pred] == [r['date'] for r in evaluation]
scales = {f: (np.mean([float(r[f]) for r in train]), np.std([float(r[f]) for r in train]) or 1.)
          for f in ['r20','b20','delta20']}
max_gap = 0.
refits = []
for variant, rows in [('core', train),('without_April', retained)]:
    y = np.array([float(r['y']) for r in rows])
    for name, features in models.items():
        z = np.array([[1.]+[(float(r[f])-scales[f][0])/scales[f][1] for f in features] for r in rows])
        penalty = np.diag([0.] + [math.sqrt(len(rows)*.001)]*len(features))
        coefficient = np.linalg.lstsq(np.vstack([z,penalty]), np.r_[y,np.zeros(len(features)+1)],rcond=None)[0]
        e = np.array([[1.]+[(float(r[f])-scales[f][0])/scales[f][1] for f in features] for r in evaluation])
        p = e @ coefficient
        expected = np.array([float(r[variant+'_'+name]) for r in pred])
        gap = float(np.max(np.abs(p-expected))); max_gap=max(max_gap,gap)
        assert gap<1e-10
        error = [float(r['y'])-float(r[variant+'_'+name]) for r in pred]
        mse = math.fsum(a*a for a in error)/len(error)
        mae = math.fsum(abs(a) for a in error)/len(error)
        assert math.isclose(mse,results['performance'][variant][name]['mse_pp2'],abs_tol=1e-10)
        assert math.isclose(mae,results['performance'][variant][name]['mae_pp'],abs_tol=1e-10)
        refits.append({'variant':variant,'model':name,'prediction_max_gap':gap,'mse_pp2':mse})
for variant in ['core','without_April']:
    p=results['performance'][variant]
    for key,a,b in [('B_to_BX','B','BX'),('BX_to_BXD','BX','BXD')]:
        improvement=100*(1-p[b]['mse_pp2']/p[a]['mse_pp2'])
        assert math.isclose(improvement,results['increment'][variant][key]['relative_gain_percent'],abs_tol=1e-10)
total = results['performance']['core']['B']['mse_pp2']-results['performance']['core']['BX']['mse_pp2']
quarter_sum = sum(results['strata'][q]['increment']['B_to_BX']['absolute_gain_pp2'] *
                  results['strata'][q]['performance']['B']['n'] for q in ['2026Q1','2026Q2','2026Q3_partial'])/147
assert math.isclose(total,quarter_sum,abs_tol=1e-12)
check={'passed':True,'independent_refits':10,'fit_method':'augmented least squares, unlike normal equations',
       'maximum_prediction_gap':max_gap,'manual_metrics_refits':refits,'quarter_reconciled':True,
       'oracle_input_counts_match':oracle['common_mature_dates']==343}
(R/'independent-reconciliation.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'independent_refits':10,'max_gap':max_gap}))
