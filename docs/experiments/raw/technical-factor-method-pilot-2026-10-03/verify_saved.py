"""Independent saved-result arithmetic. No fitting, labels, or market requests.

Run from any cwd: python3 <this-file> --out NEW_JSON
Optional --strategy-root checks the two authorized local originals, without copying.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
from statistics import mean

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / 'docs/experiments/raw/green-black-state-information-2026-10-03'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--strategy-root')
    args = parser.parse_args()
    dest = Path(args.out)
    if dest.exists():
        raise ValueError('Refuse to overwrite evidence')
    audit = json.loads((SOURCE / 'audit-02.json').read_text())
    evidence = {'new_fits': 0, 'new_market_labels': 0, 'market_requests': 0,
                'source_files': {}, 'targets': {},
                'scope': 'saved arithmetic and contract date checks; original data qualification is inherited, not rerun'}
    inputs = [SOURCE / 'audit-02.json']
    paired = []
    for target in ('return', 'risk'):
        cp = SOURCE / target / 'core-01/contract.json'
        rp = SOURCE / target / 'core-01/result.json'
        inputs.extend((cp, rp))
        c, result = (json.loads(p.read_text()) for p in (cp, rp))
        assert sha(cp) == audit[target]['contract_sha256']
        assert sha(rp) == audit[target]['result_sha256']
        rows = result['predictions']
        keys = [(r['asset'], r['date'], r['fold'], r['label_end']) for r in rows]
        assert len(set(keys)) == len(keys)
        paired.append(set(keys))
        for r in rows:
            fold = c['split']['folds'][int(r['fold'])]
            assert fold['eval_start'] <= r['date'] < r['label_end'] <= fold['eval_end']
            r['ETF_mean'] = audit[target]['training_means'][r['fold']][r['asset']]['mean']
        assets = sorted({r['asset'] for r in rows})
        scores = {m: math.sqrt(mean(mean((r[m] - r['y']) ** 2 for r in rows if r['asset'] == a)
                                    for a in assets)) for m in ('B0', 'B1', 'B2', 'ETF_mean')}
        for model, value in scores.items():
            assert abs(value - audit[target]['all']['rmse'][model]) < 1e-10
        for item in result['performance']:
            if item['metric'] == 'RMSE':
                assert abs(scores[item['model']] - item['value']) < 1e-10
        delta = scores['B1'] - scores['B2']
        assert abs(delta - audit[target]['all']['rmse_improvement']) < 1e-10
        evidence['targets'][target] = {
            'rows': len(rows), 'dates': len({r['date'] for r in rows}), 'assets': assets,
            'rmse_percentage_points': scores, 'improvement_percentage_points': delta,
            'candidate_beats_existing': scores['B2'] < scores['B1'],
            'candidate_beats_simple_etf_mean': scores['B2'] < scores['ETF_mean'],
            'uncertainty_reused_not_reestimated': audit[target]['uncertainty'],
            'mean_baseline_source': 'fingerprinted previous audit training means; no new source-data validation',
        }
    assert paired[0] == paired[1]
    evidence['targets_paired'] = True
    for p in inputs:
        evidence['source_files'][str(p.relative_to(ROOT))] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
    evidence['strategy_originals'] = {'checked': False, 'reason': 'optional local input not supplied'}
    if args.strategy_root:
        expected = {'LEI 技术交易体系.md': 'df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20',
                    'LEI 技术实现.md': '85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903'}
        for filename, value in expected.items():
            assert sha(Path(args.strategy_root) / filename) == value
        evidence['strategy_originals'] = {'checked': True, 'sha256': expected, 'originals_copied': False}
    dest.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'verified': True, 'targets': evidence['targets'], 'new_fits': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
