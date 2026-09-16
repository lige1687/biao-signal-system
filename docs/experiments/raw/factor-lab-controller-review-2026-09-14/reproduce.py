"""Controller-only synthetic counterexamples; no formal CLI or market runs."""
import json
import runpy
import pandas as pd
from pathlib import Path

from lei_signal.research.factor_lab.diagnostics import evaluate_predictive
from lei_signal.research.factor_lab.validation import audit_validation
from lei_signal.research.factor_lab.runner import _compare_expectations

ROOT = Path(__file__).resolve().parents[4]
d = runpy.run_path(str(ROOT / 'tests/unit/test_factor_lab_diagnostics.py'))
v = runpy.run_path(str(ROOT / 'tests/unit/test_factor_lab_validation.py'))
a = runpy.run_path(str(ROOT / 'tests/unit/test_factor_lab_attribution.py'))
values = d['values_frame']([(0, e, x, None) for e, x in [('a', 1), ('b', 2), ('c', 3)]])
targets = d['targets_frame']([(0, e, x) for e, x in [('a', 1), ('b', 2), ('c', 3)]])
targets['label_available_at'] = pd.NaT
unknown = evaluate_predictive(d['make_batch'](values), targets, protocol=d['make_protocol']())
crossing = audit_validation(v['pairs_frame']([('2024-01-09', 'a', 1, 1)]),
                            [v['trial']()], protocol=v['make_protocol']())
future = audit_validation(v['pairs_frame']([('2024-01-23', 'a', 1, 20)]),
                          [v['trial']()], protocol=v['make_protocol'](
                              evaluation_cutoff='2024-01-25T15:00:00+08:00'))
base, variant = a['base_account'](), a['variant_account']()
base['pool'], variant['pool'] = ['100001', 'A'], ['100001', 'B']
from lei_signal.research.factor_lab.attribution import explain_strategy
comparison = explain_strategy({'accounts': {'base': base, 'variant': variant}},
                              model_card=None, protocol=a['make_protocol'](
                                  comparison={'base': 'base', 'variant': 'variant',
                                              'declared_action': 'exit'}))
print(json.dumps({'unknown_available': unknown, 'crossing': crossing,
                  'future': future, 'comparison': comparison,
                  'empty_expectations': _compare_expectations({}, {})},
                 ensure_ascii=False, indent=2, default=str))
