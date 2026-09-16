"""Bounded diagnostic of the original simulate function; no historical rerun.

Only the original function AST is loaded. The old module's imports/main/output
paths are never executed. Constants are explicitly supplied fixture assumptions.
"""
from pathlib import Path
import ast
import hashlib
import json

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / 'scripts/run_portfolio_split.py'
source = SOURCE.read_text()
tree = ast.parse(source)
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'simulate')
namespace = {'np': np, 'pd': pd, 'BAND': .05, 'COST': .001}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), 'exec'), namespace)


def check(name, prices, expected):
    frame = pd.DataFrame(prices, index=pd.date_range('2024-01-01', periods=3))
    exposure = pd.DataFrame(1.0, index=frame.index, columns=frame.columns)
    result = namespace['simulate'](frame, exposure)
    actual = float(result['eq'].iloc[-1])
    # All cases return to starting prices, and drift is below the 5pp band.
    # Equal shares purchased once with total budget net of entry cost = .999.
    shares = .999 / len(frame.columns) / frame.iloc[0]
    shares_value = frame.mul(shares, axis=1).sum(axis=1)
    drift = frame.mul(shares, axis=1).div(shares_value, axis=0) - 1 / len(frame.columns)
    assert float(drift.abs().max().max()) < .05
    assert abs(float(shares_value.iloc[-1]) - expected) < 1e-12
    return {'name': name, 'prices': prices, 'original_curve': result['eq'].tolist(),
            'constant_shares_curve': shares_value.tolist(), 'original_end': actual,
            'constant_shares_end': expected, 'difference': actual-expected,
            'max_abs_weight_drift': float(drift.abs().max().max()),
            'same': abs(actual-expected) < 1e-12}


cases = [check('two_assets_roundtrip', {'a':[100.,104.,100.], 'b':[100.,96.,100.]}, .999),
         check('one_asset_roundtrip', {'a':[100.,104.,100.]}, .999),
         check('two_assets_flat', {'a':[100.,100.,100.], 'b':[100.,100.,100.]}, .999)]
assert not cases[0]['same'] and cases[1]['same'] and cases[2]['same']
payload = {'source': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
           'loaded_function': 'simulate', 'method': 'original AST function vs directly held constant shares',
           'fixture_constants': {'COST': .001, 'BAND': .05}, 'cases': cases,
           'finding': 'original stored weights do not drift with relative asset prices; below-band no-order path differs from constant shares',
           'scope': 'synthetic accounting diagnostic only; not a historical return correction or proof all old relative conclusions fail'}
(HERE/'weight-drift-check.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'cases':cases,'scope':payload['scope']}, ensure_ascii=False))
