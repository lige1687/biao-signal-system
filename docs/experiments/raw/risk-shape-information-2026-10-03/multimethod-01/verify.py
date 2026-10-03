"""Independent arithmetic checks; no fit or repeated inferential search."""
from pathlib import Path
import hashlib, json, math, statistics
import numpy as np
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
read = lambda p: json.loads(p.read_text())
out = read(HERE/'methods.json'); plan = read(HERE/'plan.json')
c = read(BASE/'run-vol_instability20-main/contract.json')
obs = [r for r in read(BASE/'run-vol_instability20-main/preflight.json')['observations'] if r['eligible']]
lookup = {r['id']: r for r in obs}
checks = []; maxima = {'rank': 0., 'group': 0., 'threshold': 0., 'loss': 0.}
def equal(kind, got, want):
    if got is None or want is None: assert got is want; return
    error = abs(got-want); maxima[kind] = max(maxima[kind], error); assert error < 1e-10, (kind, got, want)
def quantile(vals, q):
    vals = sorted(vals); at = (len(vals)-1)*q; lo = math.floor(at); hi = math.ceil(at)
    return vals[lo]+(vals[hi]-vals[lo])*(at-lo)
for n, v in out['candidates'].items():
    preds = read(BASE/f'run-{n}-main/result.json')['predictions']
    for f, fold in enumerate(c['split']['folds']):
        pp = [r for r in preds if int(r['fold']) == f]
        train = [r for r in obs if r['date'] <= fold['train_end'] and r['label_end'] < fold['eval_start']]
        for a, detail in v['details'][str(f)].items():
            tr = [r for r in train if r['asset'] == a]; ev = [lookup[r['id']] for r in pp if r['asset'] == a]
            assert len(tr) == detail['train_rows']
            assert max(r['label_end'] for r in tr) == detail['train_max_label_end'] < fold['eval_start']
            q = [quantile([r['features'][n] for r in tr], p) for p in [.3, .7]]
            for got, want in zip(detail['thresholds_train'], q): equal('threshold', got, want)
            for rr, tag in [(tr, 'train_rank'), (ev, 'eval_rank')]:
                equal('rank', detail[tag], float(spearmanr([r['features'][n] for r in rr], [r['y'] for r in rr]).statistic))
            means = {}
            for g in ['low', 'middle', 'high']:
                ys = [r['y'] for r in ev if ('low' if r['features'][n] <= q[0] else ('high' if r['features'][n] > q[1] else 'middle')) == g]
                assert len(ys) == detail['groups'][g]['n']
                means[g] = statistics.mean(ys) if ys else None
                equal('group', detail['groups'][g]['mean'], means[g])
                equal('group', detail['groups'][g]['median'], statistics.median(ys) if ys else None)
            equal('group', detail['groups']['high_minus_low'], means['high']-means['low'] if means['high'] is not None and means['low'] is not None else None)
            cond = v['conditional'][str(f)][a]; med = {k:statistics.median([r['features'][k] for r in tr]) for k in ['volatility20','return20']}
            supported = []
            for cc in cond['cells']:
                matches = lambda r: [int(r['features'][k] > med[k]) for k in ['volatility20','return20']] == cc['cell']
                tt = [r for r in tr if matches(r)]; ee = [r for r in ev if matches(r)]
                assert len(tt) == cc['train_rows'] and len(ee) == cc['eval_rows']
                if len(tt) >= 20:
                    qq = [quantile([r['features'][n] for r in tt], p) for p in [.3,.7]]
                    low = [r['y'] for r in ee if r['features'][n] <= qq[0]]; high = [r['y'] for r in ee if r['features'][n] > qq[1]]
                    assert cc['supported'] == (len(low) >= 5 and len(high) >= 5)
                    if cc['supported']: supported.append((len(ee), statistics.mean(high)-statistics.mean(low)))
            retained = sum(x[0] for x in supported); assert retained == cond['retained_rows']
            equal('group', cond['contrast'], sum(x[0]*x[1] for x in supported)/retained if retained else None)
        for baseline in ['B1-direct', 'simple']:
            packet = read(HERE/f'{baseline}-packet-fold{f}.json')
            assert packet['calendar'] == sorted({r['date'] for r in pp})
            actual_calendar = [d for d in c['calendar'] if packet['calendar'][0] <= d <= packet['calendar'][-1]]
            assert actual_calendar == packet['calendar']
            means = {a:statistics.mean([r['y'] for r in train if r['asset'] == a]) for a in ['510050.SS','510500.SS','588000.SS']}
            for row in packet['rows']:
                day = [r for r in pp if r['date'] == row['date']]
                assert sorted(r['asset'] for r in day) == sorted(means)
                b = statistics.mean([(r['B1']-r['y'])**2 if baseline == 'B1-direct' else (means[r['asset']]-r['y'])**2 for r in day])
                equal('loss', row['benchmark_loss'], b)
                equal('loss', row['models'][n], statistics.mean([(r['B2']-r['y'])**2 for r in day]))
            tool = read(HERE/f'joint-{baseline.replace("-direct", "-direct")}-fold{f}.json')
            delta = statistics.mean([r['benchmark_loss']-r['models'][n] for r in packet['rows']])
            equal('loss', tool['mean_improvements'][n], delta)
    assert sum(p['rows'] for p in v['nonoverlap_phases']) == len(preds)
    for col in ['B1','B2']:
        equal('loss', statistics.mean([(r[col]-r['y'])**2 for r in preds]), sum(p['rows']*p[f'{col.lower()}_mse'] for p in v['nonoverlap_phases'])/len(preds))
    for phase in v['nonoverlap_phases']:
        ds = [r['date'] for r in preds if c['calendar'].index(r['date']) % 21 == phase['phase']]
        positions = sorted({c['calendar'].index(d) for d in ds})
        assert all(b-a >= 21 for a,b in zip(positions,positions[1:]))
    checks.append(n)
result = {'status':'passed', 'candidate_checks':checks, 'max_absolute_errors':maxima,
          'threshold_source':'earlier matured training rows only', 'independent_rank_engine':'scipy.stats.spearmanr',
          'joint_packets':'all daily losses verified directly, contiguous original calendar and fixed 3 asset support',
          'phase_partition':'all rows exactly covered; 21 interval spacing; weighted phase errors recover original',
          'new_fits':0}
assert not (HERE/'verification.json').exists()
(HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
