"""Controller repair review: hashes and synthetic counterexamples only."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from lei_signal.research.factor_evidence import runner, stability
from lei_signal.research.factor_evidence.contract import FIXED_PARAMS
from lei_signal.research.factor_evidence.resampling import paired_block_deltas

RAW = ROOT / 'docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

checks = []
def check(name, value):
    checks.append({'name': name, 'ok': bool(value)})

for e in json.loads((RAW/'baseline/freeze-baseline.json').read_text())['files']:
    check('protected:'+e['path'], sha(ROOT/e['path']) == e['sha256'])
sup = json.loads((RAW/'supplement/supplement-manifest.json').read_text())
check('supplement keyset', {str(p.relative_to(RAW/'supplement')) for p in
      (RAW/'supplement').rglob('*') if p.is_file()} == set(sup['files']) | {'supplement-manifest.json'})
for rel, m in sup['files'].items():
    check('supplement:'+rel, sha(RAW/'supplement'/rel) == m['sha256'])
repair = json.loads((RAW/'repair-r1-r4/repair-manifest.json').read_text())
for e in repair['code_snapshot']:
    matches = [p for p in (RAW/'repair-r1-r4/code-snapshot').rglob('*')
               if p.is_file() and sha(p) == e['new_sha256_repaired']]
    check('repair:'+e['path'], sha(ROOT/e['path']) == e['new_sha256_repaired'] and bool(matches))
old = json.loads((RAW/'protocol-v1.0.0.json').read_text())
check('old protocol', sha(RAW/'protocol-v1.0.0.json') == '769a350160ef9f3da896df9c048b4b4ff664d64a4b1ab88cdf7dfb54adb88db1')
manifest=json.loads((RAW/'run-01/manifest.json').read_text())
for rel,m in manifest['files'].items():
    check('run01:'+rel, sha(RAW/'run-01'/rel) == m['sha256'])

# No true-market computation. Four synthetic observations across two years.
f = pd.DataFrame([
    {'symbol':'SYN','session':d,'state':s,'main':v,'aux':None,'legal':True}
    for d,s,v in [('2020-01-02',True,.1),('2020-01-03',False,0),
                  ('2021-01-04',True,-.2),('2021-01-05',False,0)]])
y=stability.year_stability(f)
check('hand loo signs', y['leave_one_year_out']['2020']['delta'] == -.2 and
      y['leave_one_year_out']['2021']['delta'] == .1)
ov={'sparse':{'anchor':'2020-01-02','step':23,'expected_points':1,
    'auditable_points':1,'reasons':{},'adjacent_shared_max':None},
    'rows_audited':4,'illegal_rows_excluded':0,'legal_missing_endpoints':0,
    'per_label_intervals':21,'total_interval_refs':84,'unique_intervals':42,
    'reuse_ratio':2,'adjacent_shared_mean':20}
report=runner._report_md(stability.state_summary(f),y['years'],
    y['leave_one_year_out'],y['equal_weight_year_delta'],y['sign_counts'],ov,{},
    FIXED_PARAMS,{'synthetic':True,'object_ref':'synthetic:test@0','symbol':'SYN'})
empty=paired_block_deltas(f.iloc[:0],2,4,1)
check('empty pure result', empty['not_estimable_reason'] is not None)
# Direct helper claims validated real provenance without actually checking it.
fake=runner._resolve_identity(f.assign(symbol='510300'),FIXED_PARAMS,
    {'mode':'real','input_identity':{'base_dir':'does-not-exist',
                                   'observations_csv_sha256':'fake'}})
out={'checks':checks,'failures':[x for x in checks if not x['ok']],
     'synthetic_findings':{
        'loo':y['leave_one_year_out'],
        'contradictory_unconditional_sentence': '只说明单个年份不使差值反号' in report,
        'direct_helper_accepts_fake_identity':fake},
     'scope':'No real analysis rerun. Direct helper is not the validated CLI.'}
print(json.dumps(out,ensure_ascii=False,indent=2))
