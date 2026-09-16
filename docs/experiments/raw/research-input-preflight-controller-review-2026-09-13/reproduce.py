"""Read-only controller probes; generated fixtures are SYNTHETIC, never market evidence.

Run from repo root with --out pointing to a NEW directory. No existing files edited.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.input_preflight import inspect_input


def write_json(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    snap = out / 'synthetic-snapshot'
    snap.mkdir()
    # Constant nominal prices without actions imply a constant economic index of 1.
    # An actual input column is supplied; no object definition is invented or modified.
    csv = 'date,open,high,low,close,volume,economic_index\n2026-06-01,10,11,9,10,100,1\n2026-06-02,10,11,9,10,100,1\n'
    (snap / 'prices.csv').write_text(csv, encoding='utf-8')
    write_json(snap / 'snapshot.json', {
        'schema_version': 'research-data-snapshot/1.0',
        'transform_version': 'research-data-snapshot/1.0',
        'mode': 'import', 'fixture': 'SYNTHETIC ALGORITHM TEST ONLY',
        'semantics': {'fields': csv.splitlines()[0].split(','), 'currency': 'CNY',
                      'price_basis': 'nominal_close', 'trading_calendar': {'authority': 'none'}},
        'uses': ['description', 'diagnostic'], 'not_for': ['production_trade'],
        'market_data_refs': {},
        'instruments': [{'instrument_id': '510300.SS', 'rows': 2,
            'first_date': '2026-06-01', 'last_date': '2026-06-02',
            'normalized': {'path': 'prices.csv', 'sha256': hashlib.sha256(csv.encode()).hexdigest()},
            'raw_responses': []}],
    })
    registry_path = ROOT / 'docs/research/definitions.v1.json'
    registry = json.loads(registry_path.read_text())
    registry['sources']['mixed_code']['sha256'] = '0' * 64
    broken = out / 'synthetic-registry-wrong-source-hash.json'
    write_json(broken, registry)
    common = dict(snapshot_dir=snap, calendar_path=None, publication_path=None,
                  actions_path=None, registry_path=registry_path,
                  refs=('mixed.price.economic@1.0.0',), use='description',
                  evaluation_start='2026-06-01', evaluation_end='2026-06-02')
    results = {}
    for name, changes in [('source_control', {}),
                          ('source_hash_failed', {'registry_path': broken}),
                          ('reversed_no_calendar', {'evaluation_start': '2026-06-30', 'evaluation_end': '2026-06-01', 'refs': ()}),
                          ('invalid_no_calendar', {'evaluation_start': 'garbage', 'evaluation_end': 'garbage', 'refs': ()})]:
        report = inspect_input(**(common | changes))
        write_json(out / (name + '.json'), report)
        results[name] = {'request_satisfied': report['request_satisfied'],
            'sources_verified': report['registry'].get('sources_verified'),
            'errors': report['errors'], 'objects': report['objects']}

    script = ROOT / 'scripts/check_research_input.py'
    base = [sys.executable, str(script), '--snapshot', str(snap),
            '--start', '2026-06-01', '--end', '2026-06-02', '--use', 'description']
    for name, extra in [('cli_source_hash_failed', ['--registry', str(broken), '--refs', 'mixed.price.economic@1.0.0']),
                        ('cli_unknown_object', ['--registry', str(registry_path), '--refs', 'nosuch.object@1.0.0'])]:
        proc = subprocess.run(base + extra + ['--out', str(out / name)], capture_output=True, text=True, cwd=ROOT)
        (out / (name + '.stdout.txt')).write_text(proc.stdout)
        (out / (name + '.stderr.txt')).write_text(proc.stderr)
        results[name] = {'exit_code': proc.returncode}

    # Controlled write failure after the successful JSON was written. No source patch.
    spec = importlib.util.spec_from_file_location('preflight_cli_probe', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_write = Path.write_text
    failure_out = out / 'write_failure'

    def fail_markdown(path, *a, **kw):
        if path == failure_out / 'preflight.md':
            raise OSError('SYNTHETIC disk failure for controller probe')
        return original_write(path, *a, **kw)

    with patch.object(Path, 'write_text', fail_markdown):
        try:
            rc = module.main(base[2:] + ['--out', str(failure_out)])
            results['write_failure'] = {'returned_exit': rc}
        except OSError as exc:
            results['write_failure'] = {'uncaught': str(exc)}
    partial = json.loads((failure_out / 'preflight.json').read_text())
    results['write_failure'].update(partial_request_satisfied=partial['request_satisfied'],
                                    manifest_exists=(failure_out / 'manifest.json').exists())

    real = ROOT / 'docs/experiments/raw/research-input-preflight-2026-09-13'
    protocol = json.loads((real / 'protocol.json').read_text())
    inputs = protocol['fixed_inputs']
    real_base = [sys.executable, str(script), '--snapshot', inputs['snapshot_dir'],
        '--calendar', inputs['calendar'], '--publication', inputs['publication'],
        '--actions', inputs['actions'], '--registry', str(registry_path),
        '--start', inputs['evaluation_start'], '--end', inputs['evaluation_end']]
    for name, use, refs, prior in [
        ('real_description', 'description', [], 'attempt-01-03'),
        ('real_objects', 'description', protocol['first_refs'], 'attempt-02-02'),
        ('real_ranking', 'ranking', ['mixed.momentum.raw@1.0.0'], 'attempt-03-02')]:
        proc = subprocess.run(real_base + ['--use', use, '--refs', *refs, '--out', str(out / name)],
                              capture_output=True, text=True, cwd=ROOT)
        current = json.loads((out / name / 'preflight.json').read_text())
        old = json.loads((real / prior / 'preflight.json').read_text())
        stable = ['integrity', 'data_uses', 'objects', 'findings', 'request_satisfied', 'errors']
        results[name] = {'exit_code': proc.returncode,
                         'stable_fields_equal': all(current[k] == old[k] for k in stable),
                         'rows': current['integrity']['rows']}
    write_json(out / 'probe-summary.json', results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
