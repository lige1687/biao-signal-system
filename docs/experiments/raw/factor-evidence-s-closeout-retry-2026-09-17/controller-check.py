"""Controller-only verification: hashes and synthetic interface/math checks."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from lei_signal.research.factor_evidence import runner, stability
from lei_signal.research.factor_evidence.contract import FIXED_PARAMS

HERE = Path(__file__).resolve().parent
RAW = ROOT/'docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    return json.loads(p.read_text())
checks=[]
def ck(name, ok):
    checks.append({'name':name,'ok':bool(ok)})
for e in read(HERE/'closeout-manifest.json')['files']:
    ck('snapshot:'+e['path'], sha(ROOT/e['path']) == sha(HERE/e['snapshot_file']) == e['new_sha256_repaired'])
for e in read(RAW/'baseline/freeze-baseline.json')['files']:
    ck('protected:'+e['path'], sha(ROOT/e['path']) == e['sha256'])
protocol=read(RAW/'protocol-v1.0.0.json')
ck('old_protocol', sha(RAW/'protocol-v1.0.0.json') == '769a350160ef9f3da896df9c048b4b4ff664d64a4b1ab88cdf7dfb54adb88db1')
frozen={sha(p) for p in (RAW/'freeze/1.0.0/code-snapshot').rglob('*') if p.is_file()}
for rel,h in protocol['code_identity'].items():
    ck('old_frozen:'+rel,h in frozen)
sup=read(RAW/'supplement/supplement-manifest.json')
for rel,info in sup['files'].items():
    ck('supplement:'+rel,sha(RAW/'supplement'/rel)==info['sha256'])
m=read(RAW/'run-01/manifest.json')
ck('run01_keyset', {str(p.relative_to(RAW/'run-01')) for p in (RAW/'run-01').rglob('*') if p.is_file()} == set(m['files']) | {'manifest.json'})
for rel,info in m['files'].items():
    ck('run01:'+rel,sha(RAW/'run-01'/rel)==info['sha256'])

# Synthetic direct public entry must reject even matching symbol/fake provenance.
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'out'
    try:
        runner.run_analysis(pd.DataFrame({'symbol':['510300']}),pd.DataFrame(),FIXED_PARAMS,
                            out_dir=p,source_meta={'mode':'real','input_identity':{'base_dir':'fake','observations_csv_sha256':'fake'}})
    except ValueError:
        ck('fake_real_rejected_before_directory',not p.exists())
    else:
        ck('fake_real_rejected_before_directory',False)

# Independent simple arithmetic: two yearly true-minus-false differences +.1,-.2.
f=pd.DataFrame([{'session':d,'state':s,'main':v,'aux':None,'legal':True}
 for d,s,v in [('2020-01-02',True,.1),('2020-01-03',False,0),('2021-01-04',True,-.2),('2021-01-05',False,0)]])
y=stability.year_stability(f)
ck('hand_full_delta',abs(stability.state_summary(f)['delta']-(-.05))<1e-12)
ck('hand_leave_out_2021',abs(y['leave_one_year_out']['2021']['delta']-.1)<1e-12)
ck('hand_leave_out_2020',abs(y['leave_one_year_out']['2020']['delta']-(-.2))<1e-12)
src=(ROOT/'src/lei_signal/research/factor_evidence/runner.py').read_text()
ck('unconditional_claim_removed','只说明单个年份不使差值反号' not in src and '无预测有效性证据；逐年方向不一致' not in src)
print(json.dumps({'checks':len(checks),'failures':[x for x in checks if not x['ok']],
 'scope':'Frozen files read-only; no market calculation or formal analysis rerun.'},ensure_ascii=False))
assert all(x['ok'] for x in checks)
