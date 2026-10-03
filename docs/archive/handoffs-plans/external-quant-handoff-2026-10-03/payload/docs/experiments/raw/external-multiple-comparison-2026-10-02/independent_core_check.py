"""Independent NumPy reference for fixed unstudentized upper comparison.

Does not use arch's sampler, max-statistic or simulated-value implementation
to calculate the reference. Synthetic input only, no financial fits.
"""
from pathlib import Path
import ast
import hashlib
import json
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SCRIPTS = ROOT / '.agents/skills/lei-quant-tools/scripts'
sys.path.insert(0, str(SCRIPTS))
from lei_arch_bootstrap.bootstrap.multiple_comparison import SPA


def reference(benchmark, models, block, reps, seed):
    differences = benchmark[:, None] - models
    n = len(differences)
    means = differences.mean(0)
    observed = float(max(means))
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(reps):
        starts = rng.integers(0, n, size=(n + block - 1) // block)
        indices = np.array([(int(start) + offset) % n
                            for start in starts for offset in range(block)])[:n]
        draws.append(float(max(differences[indices].mean(0) - means)))
    return observed, np.array(draws), float(np.mean(np.array(draws) > observed))


def main():
    provenance = json.loads((SCRIPTS / 'lei_arch_bootstrap/provenance.json').read_text())
    wheel = next((ROOT / 'data_cache/external-arch-comparison').glob('*.whl'))
    source_checks = []
    with zipfile.ZipFile(wheel) as archive:
        for item in provenance['files']:
            original = archive.read(item['original'])
            local = (ROOT / item['local']).read_bytes()
            # Reverse the isolated package name only in actual import nodes.
            tree = ast.parse(local)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    node.module = node.module.replace('lei_arch_bootstrap.', 'arch.', 1)
            exact_ast = ast.dump(tree) == ast.dump(ast.parse(original))
            assert exact_ast
            assert hashlib.sha256(local).hexdigest() == item['local_sha256']
            assert hashlib.sha256(original).hexdigest() == item['original_sha256']
            source_checks.append({'module': item['original'], 'ast_equal_except_import_prefix': True})
        licenses = [name for name in archive.namelist() if name.endswith('LICENSE.md')]
        assert archive.read(licenses[0]) == (SCRIPTS / 'lei_arch_bootstrap/LICENSE.md').read_bytes()
    cases = []
    rng = np.random.default_rng(20261002)
    for name, offsets in [('mixed', [-0.5, 0.0, 0.5]),
                          ('all_worse', [-2.0, -1.0, -0.7]),
                          ('clear_improvement', [1.0, -1.0, -0.2])]:
        benchmark = 10.0 + rng.uniform(0, 1, 120)
        improvements = rng.normal(0, 0.1, (120, 3)) + offsets
        models = benchmark[:, None] - improvements
        observed, simulated, expected = reference(benchmark, models, 20, 1000, 20261002)
        core = SPA(benchmark, models, block_size=20, reps=1000,
                   bootstrap='circular', studentize=False, nested=False, seed=20261002)
        core.compute()
        actual = float(core.pvalues['upper'])
        raw_maxima = core._simulated_vals[:, :, 2].max(0)
        max_diff = float(np.max(np.abs(raw_maxima - simulated)))
        assert np.allclose(raw_maxima, simulated, atol=1e-12, rtol=0)
        assert actual == expected
        cases.append({'case': name, 'observed_max_mean_improvement': observed,
                      'library_upper_fraction': actual, 'independent_upper_fraction': expected,
                      'replications': 1000, 'max_replication_difference': max_diff})
    report = {'status': 'passed', 'batch': 2, 'source_ast_checks': source_checks,
              'license_bytes_equal': True, 'independent_cases': cases,
              'real_fits': 0, 'scope': 'Synthetic fixed core agreement; not finite-sample guarantees or financial efficacy'}
    (OUT / 'independent-core-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
