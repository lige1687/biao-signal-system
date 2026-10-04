"""Reporting for the same fixed combinations; no new model or weight selection."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def contribution(base, new, y):
    d = [(b-t)**2-(n-t)**2 for b, n, t in zip(base, new, y)]
    pos = math.fsum(x for x in d if x > 0) / len(d)
    neg = math.fsum(x for x in d if x < 0) / len(d)
    return {'rows': len(d), 'improved_rows': sum(x > 0 for x in d),
            'worsened_rows': sum(x < 0 for x in d), 'unchanged_rows': sum(x == 0 for x in d),
            'positive_contribution': pos, 'negative_contribution': neg,
            'net_mse_improvement': math.fsum(d) / len(d),
            'reconciliation_error': abs(pos + neg - math.fsum(d) / len(d))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    assert not a.output.exists()
    raw = a.root / 'docs/experiments/raw'
    sources = {}

    def read(path):
        sources[str(path.relative_to(a.root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())

    runs = [read(raw / 'tsfresh-factor-validation-2026-10-02' / ('run-'+n) / 'result.json')['predictions']
            for n in ['joint', 'amplitude', 'serial']]
    idx = [{r['id']: r for r in rs} for rs in runs]
    keys = sorted(idx[0])
    y = [idx[0][k]['y'] for k in keys]
    pc = {n: [i[k]['B2'] for k in keys] for n, i in zip(['joint', 'amplitude', 'serial'], idx)}
    pc.update({n: [idx[0][k][n] for k in keys] for n in ['B0', 'B1']})
    equal = [math.fsum(i[k]['B2'] for i in idx)/3 for k in keys]
    half = [(v+b)/2 for v, b in zip(equal, pc['B0'])]
    detail = {'price': {name: {b: contribution(values, combo, y) for b, values in pc.items()}
                        for name, combo in [('equal3', equal), ('half_simple', half)]}}
    detail['price']['simple_component_help'] = contribution(equal, half, y)
    names = ['volume-direction-information-2026-10-04','session-composition-information-2026-10-04']
    refs = [read(raw / n / 'simple-reference-predictions.json') for n in names]
    accepted = [read(raw / n / 'accepted-main/result.json')['predictions'] for n in names]
    maps = [{r['id']: r for r in rs} for rs in refs]
    originals = [{r['id']: r for r in rs} for rs in accepted]
    assert set(maps[0]) == set(maps[1]) == set(originals[0]) == set(originals[1])
    keys = sorted(maps[0])
    for j in range(2):
        for k in keys:
            assert all(maps[j][k][f] == originals[j][k][f]
                       for f in ['id','asset','date','fold','y','label_end','B0','B1','B2'])
    y = [maps[0][k]['y'] for k in keys]
    combo = [(maps[0][k]['B2']+maps[1][k]['B2'])/2 for k in keys]
    refs_pred = {f'{n}.{c}': [i[k][c] for k in keys]
                 for n, i in zip(['volume','session'], maps) for c in ['B0','B1','B2','asset_mean']}
    detail['risk'] = {n: contribution(v, combo, y) for n, v in refs_pred.items()}
    detail['risk_strong_reference_rmse'] = {
        n: math.sqrt(math.fsum((v-t)**2 for v, t in zip(values,y))/len(y))
        for n, values in refs_pred.items() if n.endswith('asset_mean')}
    detail['sources'] = sources
    detail['scope'] = 'postprocessing same fixed comparisons; preserved earlier no-common-baseline audit; strong references added for completeness, no tuned weight'
    detail['new_fits'] = 0
    assert all(hashlib.sha256((a.root / n).read_bytes()).hexdigest() == h for n, h in sources.items())
    a.output.write_text(json.dumps(detail, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'risk_strong_reference_rmse': detail['risk_strong_reference_rmse'],
                      'risk_vs_volume_mean': detail['risk']['volume.asset_mean'],
                      'price_vs_B0': detail['price']['equal3']['B0']}))


if __name__ == '__main__':
    main()
