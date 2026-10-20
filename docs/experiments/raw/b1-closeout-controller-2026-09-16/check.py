"""Controller read-only archive checks and validation-only synthetic mutations."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from lei_signal.research.factor_unit import b1_contract as bc

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / 'docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16'
RUN = RAW / 'run-02'
SUP = RAW / 'supplement'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


out = {}
manifest = read(RUN / 'manifest.json')
for rel, h in manifest['file_hashes'].items():
    assert sha(RUN / rel) == h, rel
out['old_manifest_entries_verified'] = len(manifest['file_hashes'])
listing = read(SUP / 'full-file-listing.json')
actual = {str(p.relative_to(RUN)): sha(p) for p in RUN.rglob('*')
          if p.is_file() and p != RUN / 'manifest.json'}
assert actual == listing['files']
assert sha(RUN / 'manifest.json') == listing['bound_run_manifest_sha256']
out['full_run_inventory_bidirectional'] = len(actual)
sm = read(SUP / 'supplement-manifest.json')
for rel, h in sm['files'].items():
    assert sha(SUP / rel) == h, rel
actual_sup = {str(p.relative_to(SUP)) for p in SUP.rglob('*') if p.is_file()}
out['supplement_unlisted'] = sorted(actual_sup - set(sm['files']) - {'supplement-manifest.json'})
proto = read(RAW / 'protocol-v1.0.1.json')
assert (RUN / 'protocol.source.json').read_bytes() == (RAW / 'protocol-v1.0.1.json').read_bytes()
refs = proto['standards'] + [proto['candidate_card'], proto['task_book']]
assert {p.name for p in (SUP / 'standards').iterdir()} == {Path(r['path']).name for r in refs}
for ref in refs:
    assert sha(SUP / 'standards' / Path(ref['path']).name) == ref['sha256']
out['restored_standard_card_taskbook_count'] = len(refs)
for name in ('states.csv', 'observations.csv'):
    assert read(SUP / (name + '.meta.json'))['binds']['sha256'] == sha(RUN / name)
out['protocol_hashes'] = {p.name: sha(p) for p in RAW.glob('protocol-v*.json')}
out['current_code_hashes'] = {p: sha(ROOT / p) for p in bc.REQUIRED_CODE_KEYS}
positive = copy.deepcopy(proto)
positive['code_identity'] = out['current_code_hashes']
with tempfile.TemporaryDirectory(prefix='b1-controller-validation-') as tmp:
    path = Path(tmp) / 'protocol-v1.0.1.json'
    def validate(p):
        path.write_text(json.dumps(p))
        return bc.validate_b1_protocol(path, ROOT)
    validate(positive)
    out['current_positive_validation'] = True
    mutations = {}
    for key, value in [('standards', []), ('tolerance', {'float': 1, 'counts_keys_nulls': '严格一致'}),
                       ('output_fields', []), ('no_claims', [])]:
        bad = copy.deepcopy(positive)
        bad[key] = value
        try:
            validate(bad)
        except ValueError as exc:
            mutations[key] = str(exc)
        else:
            raise AssertionError(f'accepted {key}')
    out['independent_rejections'] = mutations
out['real_computations'] = 0
print(json.dumps(out, ensure_ascii=False, indent=2))
with Path(__file__).with_name('results.json').open('x') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
