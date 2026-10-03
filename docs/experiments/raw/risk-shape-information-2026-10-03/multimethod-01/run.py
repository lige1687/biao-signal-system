"""Fixed, zero-fit supplementary views of sealed risk-shape predictions."""
from pathlib import Path
import hashlib, json, subprocess, sys, time
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[4]
NAMES = ['vol_instability20', 'beta_asymmetry60', 'negative_cluster60']
ASSETS = ['510050.SS', '510500.SS', '588000.SS']

def read(p): return json.loads(p.read_text())
def write(p, x):
    assert not p.exists(), str(p)
    p.write_text(json.dumps(x, ensure_ascii=False, allow_nan=False, indent=2)+'\n')
def correlation(x, y):
    # Average tied ranks, independent of scipy/pandas.
    def ranks(a):
        a = np.asarray(a); order = np.argsort(a, kind='stable'); out = np.empty(len(a))
        i = 0
        while i < len(a):
            j = i+1
            while j < len(a) and a[order[j]] == a[order[i]]: j += 1
            out[order[i:j]] = (i+j-1)/2+1; i = j
        return out
    a, b = ranks(x), ranks(y)
    return float(np.corrcoef(a, b)[0, 1]) if np.std(a) and np.std(b) else None
def group_data(rows, name, q):
    vals = {g: [] for g in ['low', 'middle', 'high']}
    for r in rows:
        x = r['features'][name]
        g = 'low' if x <= q[0] else ('high' if x > q[1] else 'middle')
        vals[g].append(r['y'])
    result = {g: {'n': len(v), 'mean': float(np.mean(v)) if v else None,
                  'median': float(np.median(v)) if v else None} for g, v in vals.items()}
    result['high_minus_low'] = result['high']['mean']-result['low']['mean'] if vals['high'] and vals['low'] else None
    return result
def bootstrap_group(cells, fold_weights, calendars):
    rng = np.random.default_rng(20261004); draws = []
    for _ in range(1000):
        value = 0.; valid = True
        for f, calendar in enumerate(calendars):
            length = len(calendar); starts = rng.integers(0, length, size=(length+59)//60)
            indices = np.concatenate([(s+np.arange(60)) % length for s in starts])[:length]
            mult = np.bincount(indices, minlength=length)
            parts = []
            for a in ASSETS:
                v = cells[(f, a)]; means = []
                for g in ['low', 'high']:
                    m = v['group'] == g; w = mult[v['position'][m]]
                    if w.sum() == 0: valid = False; break
                    means.append(float(w @ v['y'][m]/w.sum()))
                if not valid: break
                parts.append(means[1]-means[0])
            if not valid: break
            value += fold_weights[f]*float(np.mean(parts))
        if valid: draws.append(value)
    return {'interval95': np.quantile(draws, [.025, .975]).tolist() if draws else None,
            'valid_draws': len(draws), 'unestimable_draws': 1000-len(draws),
            'block': 60, 'seed': 20261004, 'requested_draws': 1000}

def main():
    start = time.monotonic(); plan = read(HERE/'plan.json')
    for path, sha in plan['inputs'].items():
        p = HERE/'previous-state.json' if path.endswith('/research-state.json') else ROOT/path
        assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, path
    results = {n: read(BASE/f'run-{n}-main/result.json') for n in NAMES}
    c = read(BASE/'run-vol_instability20-main/contract.json')
    obs = [r for r in read(BASE/'run-vol_instability20-main/preflight.json')['observations'] if r['eligible']]
    lookup = {r['id']: r for r in obs}; predictions = results[NAMES[0]]['predictions']
    signature = lambda rr: [(r['id'], r['date'], r['asset'], r['fold'], r['y'], r['label_end'], r['B1']) for r in rr]
    assert all(signature(results[n]['predictions']) == signature(predictions) for n in NAMES)
    evals = {f: [lookup[r['id']] for r in predictions if int(r['fold']) == f] for f in range(2)}
    trains = {f: [r for r in obs if r['date'] <= fold['train_end'] and r['label_end'] < fold['eval_start']] for f, fold in enumerate(c['split']['folds'])}
    calendars = [[d for d in c['calendar'] if fold['eval_start'] <= d <= fold['eval_end']] for fold in c['split']['folds']]
    scores = [len({r['date'] for r in evals[f]}) for f in range(2)]; weights = np.array(scores)/sum(scores)
    assert all(r['asset'] in ASSETS for r in obs)
    output = {'stage': plan['stage'], 'new_fits': 0, 'new_market_requests': 0,
              'fold_scored_dates': scores, 'fold_calendar_lengths': list(map(len, calendars)),
              'plan_sha256': hashlib.sha256((HERE/'plan.json').read_bytes()).hexdigest(), 'candidates': {}}
    if (HERE/'methods.json').exists(): output = read(HERE/'methods.json')
    for name in ([] if (HERE/'methods.json').exists() else NAMES):
        cells = {}; detail = {}; conditional = {}; ranks = []
        for f in range(2):
            detail[str(f)] = {}; conditional[str(f)] = {}; rank_fold = []
            for asset in ASSETS:
                tr = [r for r in trains[f] if r['asset'] == asset]; ev = [r for r in evals[f] if r['asset'] == asset]
                q = np.quantile([r['features'][name] for r in tr], [.3, .7]).tolist()
                train_rank = correlation([r['features'][name] for r in tr], [r['y'] for r in tr])
                eval_rank = correlation([r['features'][name] for r in ev], [r['y'] for r in ev]); rank_fold.append(eval_rank)
                group = group_data(ev, name, q)
                detail[str(f)][asset] = {'thresholds_train': q, 'train_rows': len(tr), 'train_max_label_end': max(r['label_end'] for r in tr), 'train_rank': train_rank, 'eval_rank': eval_rank, 'direction_consistent': train_rank*eval_rank > 0, 'groups': group}
                pos = {d: i for i, d in enumerate(calendars[f])}
                cells[(f, asset)] = {'position': np.array([pos[r['date']] for r in ev]), 'y': np.array([r['y'] for r in ev]), 'group': np.array(['low' if r['features'][name] <= q[0] else ('high' if r['features'][name] > q[1] else 'middle') for r in ev])}
                med = {k: float(np.median([r['features'][k] for r in tr])) for k in ['volatility20', 'return20']}
                cell = lambda r: tuple(int(r['features'][k] > med[k]) for k in ['volatility20', 'return20'])
                parts = []; supported = []
                for v in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                    tt = [r for r in tr if cell(r) == v]; ee = [r for r in ev if cell(r) == v]
                    record = {'cell': list(v), 'train_rows': len(tt), 'eval_rows': len(ee), 'supported': False}
                    if len(tt) >= 20:
                        qq = np.quantile([r['features'][name] for r in tt], [.3, .7]).tolist(); gg = group_data(ee, name, qq)
                        record.update(thresholds_train=qq, groups=gg)
                        if gg['low']['n'] >= 5 and gg['high']['n'] >= 5:
                            record['supported'] = True; supported.append((len(ee), gg['high_minus_low']))
                    parts.append(record)
                retained = sum(t[0] for t in supported)
                conditional[str(f)][asset] = {'medians_train': med, 'cells': parts, 'retained_rows': retained, 'total_rows': len(ev), 'contrast': sum(t[0]*t[1] for t in supported)/retained if retained else None}
            ranks.append(float(np.mean(rank_fold)))
        fold_contrasts = [float(np.mean([detail[str(f)][a]['groups']['high_minus_low'] for a in ASSETS])) if all(detail[str(f)][a]['groups']['high_minus_low'] is not None for a in ASSETS) else None for f in range(2)]
        cond_fold = [float(np.mean([conditional[str(f)][a]['contrast'] for a in ASSETS])) if all(conditional[str(f)][a]['contrast'] is not None for a in ASSETS) else None for f in range(2)]
        phase = []
        clock = {d: i for i, d in enumerate(c['calendar'])}
        for k in range(21):
            rr = [r for r in results[name]['predictions'] if clock[r['date']] % 21 == k]
            assert len(rr) % 3 == 0 and set(r['asset'] for r in rr) == set(ASSETS)
            b1 = float(np.mean([(r['B1']-r['y'])**2 for r in rr])); b2 = float(np.mean([(r['B2']-r['y'])**2 for r in rr]))
            phase.append({'phase': k, 'dates': len(rr)//3, 'rows': len(rr), 'b1_mse': b1, 'b2_mse': b2, 'improvement_percent': 100*(b1-b2)/b1})
        assert sum(r['rows'] for r in phase) == len(predictions)
        phase_values = [r['improvement_percent'] for r in phase]
        output['candidates'][name] = {'details': detail, 'rank_by_fold': ranks, 'rank_weighted': float(weights @ ranks), 'raw_group_contrast_by_fold': fold_contrasts, 'raw_group_contrast': float(weights @ fold_contrasts) if all(v is not None for v in fold_contrasts) else None, 'group_uncertainty': bootstrap_group(cells, weights, calendars), 'conditional': conditional, 'conditional_contrast_by_fold': cond_fold, 'conditional_contrast': float(weights @ cond_fold) if all(v is not None for v in cond_fold) else None, 'nonoverlap_phases': phase, 'phase_summary': {'positive': sum(v > 0 for v in phase_values), 'total': 21, 'min': min(phase_values), 'median': float(np.median(phase_values)), 'max': max(phase_values)}}
    if not (HERE/'methods.json').exists(): write(HERE/'methods.json', output)
    tool = ROOT/'.agents/skills/lei-quant-tools/scripts/multiple_comparison.py'
    joint = {}
    for f in range(2):
        ds = sorted({r['date'] for r in evals[f]}); joint[str(f)] = {}
        command = [sys.executable, str(tool), 'compare-workflows']+[str(BASE/f'run-{n}-main') for n in NAMES]+['--start', ds[0], '--end', ds[-1], '--baseline', 'B1', '--block-size', '60', '--reps', '1000', '--seed', '20261004']
        archived = HERE/f'joint-B1-fold{f}.json'
        if archived.exists(): answer = read(archived)
        else:
            proc = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            answer = json.loads(proc.stdout); write(archived, answer)
        if answer['status'] == 'computed': joint[str(f)]['B1'] = answer['upper_pvalue']
        else:
            # Source universe includes the permanently excluded market anchor.
            # Preserve bridge rejection; use the documented direct-loss interface,
            # after independently checking the true fixed three-asset support.
            assert answer['status'] == 'not_applicable'
            joint[str(f)]['bridge_rejection'] = answer['reasons']
        means = {a: float(np.mean([r['y'] for r in trains[f] if r['asset'] == a])) for a in ASSETS}
        saved = {n: {r['id']: r for r in results[n]['predictions']} for n in NAMES}
        rows = []
        for d in ds:
            pp = [r for r in predictions if r['date'] == d]; assert len(pp) == 3
            rows.append({'date': d, 'benchmark_loss': float(np.mean([(means[r['asset']]-r['y'])**2 for r in pp])), 'models': {n: float(np.mean([(saved[n][r['id']]['B2']-r['y'])**2 for r in pp])) for n in NAMES}})
        packet = {'schema_version': 'lei-multiple-losses/1.0', 'frequency': 'qualified_session', 'unit': 'percentage_point_squared', 'calendar': ds, 'benchmark_id': 'per_asset_mature_training_mean', 'candidate_ids': NAMES, 'block_size': 60, 'reps': 1000, 'seed': 20261004, 'rows': rows}
        if answer['status'] != 'computed':
            baseline_rows = []
            for d in ds:
                pp = [r for r in predictions if r['date'] == d]
                assert sorted(r['asset'] for r in pp) == ASSETS
                baseline_rows.append({'date': d, 'benchmark_loss': float(np.mean([(r['B1']-r['y'])**2 for r in pp])), 'models': next(r['models'] for r in rows if r['date'] == d)})
            direct = {**packet, 'benchmark_id': 'B1', 'rows': baseline_rows}
            write(HERE/f'B1-direct-packet-fold{f}.json', direct)
            proc = subprocess.run([sys.executable, str(tool), 'compare-losses', str(HERE/f'B1-direct-packet-fold{f}.json')], capture_output=True, text=True, cwd=ROOT)
            answer = json.loads(proc.stdout); write(HERE/f'joint-B1-direct-fold{f}.json', answer)
            assert proc.returncode == 0, proc.stderr or answer
            joint[str(f)]['B1'] = answer['upper_pvalue']
        write(HERE/f'simple-packet-fold{f}.json', packet)
        proc = subprocess.run([sys.executable, str(tool), 'compare-losses', str(HERE/f'simple-packet-fold{f}.json')], capture_output=True, text=True, cwd=ROOT)
        answer = json.loads(proc.stdout); write(HERE/f'joint-simple-fold{f}.json', answer)
        assert proc.returncode == 0, proc.stderr or answer
        joint[str(f)]['simple'] = answer['upper_pvalue']
    write(HERE/'execution.json', {'status': 'computed', 'seconds': time.monotonic()-start, 'new_fits': 0, 'joint': joint})
    print(json.dumps({'candidates': {n: {k: v[k] for k in ['rank_by_fold', 'rank_weighted', 'raw_group_contrast_by_fold', 'raw_group_contrast', 'group_uncertainty', 'conditional_contrast_by_fold', 'conditional_contrast', 'phase_summary']} for n, v in output['candidates'].items()}, 'joint': joint}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
