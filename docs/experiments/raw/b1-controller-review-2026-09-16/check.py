"""Read-only B1 archive/summary review; never calls real calculation entry."""
import copy
import csv
import hashlib
import json
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'src'))
from lei_signal.research.factor_unit.b1_contract import validate_b1_protocol

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

raw = ROOT/'docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16'
pack = raw/'run-02'
m = json.loads((pack/'manifest.json').read_text())
actual = {str(p.relative_to(pack)) for p in pack.rglob('*') if p.is_file() and p != pack/'manifest.json'}
listed = m['file_hashes']
bad = [p for p,h in listed.items() if sha(pack/p) != h]
assert not bad
protocol = json.loads((pack/'protocol.source.json').read_text())
assert sha(pack/'protocol.source.json') == m['protocol_sha256']
assert (pack/'protocol.source.json').read_bytes() == (raw/'protocol-v1.0.1.json').read_bytes()
code_bad = [p for p,h in protocol['code_identity'].items() if sha(pack/'source-snapshot'/p) != h or sha(ROOT/p) != h]
assert not code_bad
with (pack/'observations.csv').open() as f:
    obs = list(csv.DictReader(f))
assert len({r['session'] for r in obs}) == len(obs)
s = json.loads((pack/'summary.json').read_text())['symbols']['510300']
groups = {}
for state in ['true','false']:
    rows = [r for r in obs if r['state']==state and r['in_comparison']=='True']
    vals = [float(r['main']) for r in rows]
    aux = [float(r['aux']) for r in rows if r['aux']]
    got = {'n':len(vals),'mean':statistics.mean(vals),'median':statistics.median(vals),
           'up_ratio':sum(x>0 for x in vals)/len(vals),'aux_n':len(aux),
           'aux_mean':statistics.mean(aux),'aux_worst':min(aux)}
    assert all(abs(v-s[state+'_group'][k])<=1e-12 for k,v in got.items())
    groups[state]=got
years = {}
for year in sorted({r['session'][:4] for r in obs}):
    means = {}
    for state in ['true','false']:
        vals=[float(r['main']) for r in obs if r['session'].startswith(year) and r['state']==state and r['in_comparison']=='True']
        means[state] = statistics.mean(vals)
        assert abs(means[state]-s['by_year'][year][state]['mean'])<=1e-12
    years[year] = (means['true']-means['false'])*100
with (pack/'states.csv').open() as f:
    dates=[r['date'] for r in csv.DictReader(f)]
anchor=dates.index('2019-10-08')
slots=set(dates[anchor::23])
sparse={}
for state in ['true','false']:
    vals=[float(r['main']) for r in obs if r['session'] in slots and r['state']==state and r['in_comparison']=='True']
    sparse[state]={'n':len(vals),'up':sum(v>0 for v in vals),'down':sum(v<0 for v in vals),'zero':sum(v==0 for v in vals)}
    assert sparse[state]==s['sparse_view']['groups'][state]
probes={}
with tempfile.TemporaryDirectory(prefix='lei-b1-controller-') as td:
    for name, changes in [('no_standards',{'standards':[]}),('wrong_tolerance',{'tolerance':{'float':1}})]:
        v=copy.deepcopy(protocol);v.update(changes)
        path=Path(td)/(name+'.json');path.write_text(json.dumps(v))
        try:
            validate_b1_protocol(path,ROOT)
            probes[name]='accepted'
        except ValueError as exc:
            probes[name]=str(exc)
old=json.loads((raw/'protocol-v1.0.0.json').read_text())
unrecoverable=[p for p,h in old['code_identity'].items() if sha(raw/'freeze/code-snapshot'/p)!=h]
out={'groups':groups,'year_mean_differences_percentage_points':years,'sparse':sparse,
     'listed_file_count':len(listed),'all_nonroot_manifest_files':len(actual),
     'unlisted_files':sorted(actual-set(listed)), 'code_hash_errors':code_bad,
     'protocol_probes':probes,'v100_keys_not_matching_current_freeze':unrecoverable,
     'scope':'existing observations reaggregated only; no state/target recalculation'}
text=json.dumps(out,ensure_ascii=False,indent=2);print(text)
if len(sys.argv)>1:
    with Path(sys.argv[1]).open('x') as f:f.write(text+'\n')
