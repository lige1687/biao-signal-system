"""Read-only delivery checks except writing this batch's check receipt."""
from pathlib import Path
import hashlib
import json
import re
from datetime import datetime, timezone

P = Path(__file__).resolve().parent
ROOT = P.parents[3]
REPORT = ROOT / 'docs/experiments/paper-methods-applied-checks-2026-09-08.md'
LEARNING = ROOT / 'docs/literature-learning/paper-method-followup-2026-09-08.md'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

checks = {}
for batch in ['fourth', 'fifth', 'sixth']:
    p = P.parent / f'research-{batch}-2026-09-08/final-manifest.json'
    entries = read(p)['files']
    bad = [f for f, expected in entries.items() if sha(ROOT / f) != expected]
    assert not bad, (batch, bad)
    checks[f'{batch}_seal'] = {'files': len(entries), 'mismatches': bad, 'manifest_sha256': sha(p)}
for name in ['paper-methods', 'calendar-review', 'rules-qualification', 'price-basis-qualification']:
    folder = P / name
    entries = read(folder / 'manifest.json')['files']
    bad = [e['path'] for e in entries if sha(folder / e['path']) != e['sha256']]
    assert not bad, (name, bad)
    checks[name] = {'files': len(entries), 'mismatches': bad}

registry = read(ROOT / 'docs/experiments/registry.json')
entry = registry['entries'][str(REPORT.relative_to(ROOT))]
assert entry['category'] in registry['categories'] and entry['verdict'] == 'mixed'
assert '## 一句话结论（大白话）' in REPORT.read_text() and '## ARCHIVE' in REPORT.read_text()
assert REPORT.name in (ROOT / 'docs/experiments/INDEX.md').read_text()
local_links = []
for doc in [REPORT, LEARNING]:
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        p = doc.parent / target.split('#')[0]
        assert p.exists(), (doc, target)
        local_links.append(str(p.resolve()))
checks['report_registration_and_links'] = {'category': entry['category'], 'verdict': entry['verdict'], 'local_links_checked': len(local_links)}

supplement = read(LEARNING.with_suffix('.json'))
paper_ids = {v['id'] for v in read(ROOT / 'docs/literature-learning/learning-seed.json')['papers']}
assert len(supplement['entries']) == 4
assert len({e['id'] for e in supplement['entries']}) == 4
for e in supplement['entries']:
    assert e['paper_id'] in paper_ids
    assert e['id'] in LEARNING.read_text()
    assert e['body_markdown'] in LEARNING.read_text()
    assert e['method_acceptance']['automatic_adoption'] is False
    for path in e['evidence_paths']:
        assert (ROOT / path).is_file()
checks['learning'] = {'entries': 4, 'paper_ids': sorted({e['paper_id'] for e in supplement['entries']}), 'markdown_json_consistent': True}

cards = read(P / 'evidence-cards.json')
assert len(cards) == 3
for c in cards:
    e = c['evidence_ref']
    assert e['schema_version'] == 'provenance/1.2'
    assert len(e['source_path']) == len(e['source_hash'])
    for path, expected in zip(e['source_path'], e['source_hash']):
        assert sha(Path(path)) == expected
    for rule in c['rule_refs']:
        assert sha(Path(rule['config_path'])) == rule['config_hash']
    assert c['research']['production_adopted'] is False
checks['evidence_cards'] = {'cards': 3, 'all_references_match': True, 'production_adopted': False}

rules = read(P / 'rules-qualification/qualification.json')
assert rules['synthetic_cases'] == 16 and rules['status_counts'] == {'pass': 14, 'finding': 2, 'fixture_error': 0}
assert rules['complete_B_qualified'] is False
prices = read(P / 'price-basis-qualification/results.json')
assert prices['passed_groups'] == 11 and prices['failed_groups'] == 0 and prices['failures'] == []
checks['qualification_results'] = {'B': 'not_complete', 'synthetic_behavior_cases': 16, 'price_groups_passed': 11}
checks['scope'] = 'Delivery/reference verification; computational reruns are recorded in the sealed sub-reviews, not rerun or overwritten here.'
receipt = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks, 'status': 'passed'}
(P / 'delivery-checks.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False, indent=2))
