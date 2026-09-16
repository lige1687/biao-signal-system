"""Read-only synthetic controller checks; does not run formal cases."""
import copy
import hashlib
import json
from pathlib import Path
import runpy

from lei_signal.research.factor_lab import runner
from lei_signal.research.factor_lab.attribution import explain_strategy
from lei_signal.research.factor_lab.validation import audit_validation

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / 'docs/experiments/raw/factor-lab-concentrated-repair-2026-09-14'
a = runpy.run_path(str(ROOT / 'tests/unit/test_factor_lab_attribution.py'))
v = runpy.run_path(str(ROOT / 'tests/unit/test_factor_lab_validation.py'))
out = {}
contract = a['TestComparisonContractR3']().full_comparison()['comparison']
contract['input_identity'] = {'base': {'prices': 'A'}, 'variant': {'prices': 'B'}}
result = explain_strategy({'accounts': {'base': a['base_account'](),
                          'variant_exit_on_d3': a['variant_account']()}},
                          model_card=None, protocol=a['make_protocol'](comparison=contract))
out['different_input_identity'] = result['layer2_decision_increment']
pairs = v['pairs_frame']([('2024-01-02', 'a', 1, 1)])
pairs['exclusion_reason'] = 'feature_not_available_by_decision_time'
out['already_excluded'] = audit_validation(pairs, [v['trial']()],
    protocol=v['make_protocol']())['sample_counts']['dev']
inverted = v['pairs_frame']([('2024-01-02', 'a', 4, -2)])
out['inverted_direct_audit'] = audit_validation(inverted, [v['trial']()],
    protocol=v['make_protocol']())['sample_counts']['dev']
protocol = json.loads((RAW / 'protocol-1-numerical.json').read_text())
runner.verify_frozen_contract(protocol, ROOT, RAW)
reduced = copy.deepcopy(protocol)
keep = next(iter(reduced['expectations']))
reduced['required_checks'] = [keep]
reduced['expectations'] = {keep: reduced['expectations'][keep]}
runner.verify_frozen_contract(reduced, ROOT, RAW)
out['reduced_checks'] = {'original': len(protocol['expectations']), 'accepted': 1,
                         'kept': keep}
try:
    json.loads(runner._dump_json({'value': float('nan')}))
    out['json_nonfinite'] = 'parseable'
except json.JSONDecodeError as exc:
    out['json_nonfinite'] = str(exc)
baseline = json.loads((RAW / 'protection-baseline.json').read_text())
out['baseline_keys'] = {k: len(x) for k, x in baseline.items()
                        if k.startswith('protected')}
changes = []
for path, expected in baseline['protected_files_from_prev_baseline'].items():
    f = ROOT / path
    if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != expected:
        changes.append(path)
out['protected_file_changes'] = changes
raw_changes = []
raw_count = 0
for group in baseline['protected_raw_from_prev_baseline']:
    for path, expected in group['files'].items():
        raw_count += 1
        f = ROOT / path
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != expected:
            raw_changes.append(path)
out['protected_raw'] = {'count': raw_count, 'changes': raw_changes}
out['runs'] = {}
for f in sorted((RAW / 'runs').glob('*/manifest.json')):
    m = json.loads(f.read_text())
    out['runs'][f.parent.name] = {'outputs': len(m.get('outputs', {}))}
print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
