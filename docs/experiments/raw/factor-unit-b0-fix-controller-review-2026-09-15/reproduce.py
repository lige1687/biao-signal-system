"""Read-only market qualification + synthetic statistical controller probes.

Generated temporary evidence is deliberately false and never installed in the repo.
No real factor or forward-return values are calculated.
"""
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from lei_signal.research.factor_unit.study_contract import validate_study_contract
from lei_signal.research.factor_unit.close_state import compute_close_state
from lei_signal.research.factor_unit.state_description import describe_states
from lei_signal.research.trading_calendar import TradingCalendar

RAW = ROOT / 'docs/experiments/raw/factor-unit-b0-concentrated-fix-2026-09-15'
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):
    return {'path':str(p), 'sha256':sha(p)}
def check(c):
    c = copy.deepcopy(c)
    c['_repo_root'] = str(ROOT)
    try:
        r = validate_study_contract(c)
        return {'status':r['status'], 'markets':r['markets']}
    except Exception as exc:
        return {'error':type(exc).__name__, 'message':str(exc)}

out = {}
syn = json.loads((RAW / 'b0fix-synthetic-positive-contract.json').read_text())
out['updated_contract_positive_control'] = check(syn)
bad = copy.deepcopy(syn)
bad['data_identity']['510300']['price_basis_evidence'] = {'path':'/absent.json','sha256':'0'*64}
out['old_missing_evidence_on_new_contract'] = check(bad)
bad = copy.deepcopy(syn)
bad['code_identity'] = {k:v for k,v in bad['code_identity'].items() if k.endswith('__init__.py')}
out['old_deleted_keys_on_new_contract'] = check(bad)

real = json.loads((RAW / 'b0fix-real-qualification-contract.json').read_text())
out['real_control'] = check(real)
with tempfile.TemporaryDirectory(prefix='lei-controller-b0fix-') as td:
    t = Path(td)
    c = copy.deepcopy(real)
    c['universe']['members'] = ['510300']
    c['data_identity'] = {'510300':c['data_identity']['510300']}
    c['calendar_identity'] = {'CN':c['calendar_identity']['CN']}
    # No provider response exists. Mutate all superficial declarations consistently.
    for tier in ('snapshot_provenance_bound','price_basis_verified'):
        e = c['data_identity']['510300']
        e['price_basis_status'] = tier
        evidence = {'schema':'factor-unit-price-evidence/1', 'records':[{
            'symbol':'510300', 'input_sha256':e['sha256'], 'price_basis_status':tier,
            'data_mode':'real', 'vendor_traceable':True,
            'vendor_response_ref':'/definitely/nonexistent/provider.json'}]}
        ep = t / (tier+'.json'); ep.write_text(json.dumps(evidence)); e['price_basis_evidence']=ref(ep)
        sp = t / (tier+'.csv')
        with sp.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['symbol','sha256','provenance_tier','data_mode'])
            w.writeheader(); w.writerow({'symbol':'510300','sha256':e['sha256'],
                                         'provenance_tier':tier,'data_mode':'real'})
        c['source_decision']=ref(sp)
        out['forged_'+tier+'_total_return'] = check(c)

dates = pd.date_range('2020-01-01',periods=50,freq='D')
schedule = pd.DataFrame({'session':dates,'close_at':dates.tz_localize('Asia/Shanghai')+pd.Timedelta(hours=15)})
values = pd.DataFrame({'symbol':'SYN','session':dates,'state':[True]*50,'I':range(100,150)})
contract={'data_mode':'synthetic','object_ref':syn['object_ref'],'lookback':20,'e_offset':1,'x_offset':22,
          'evaluation_window':{'start':'2020-01-01','end':'2020-02-19'},
          'research_cutoff':'2019-01-01T15:00:00+08:00',
          'sparse_anchor_session':{'SYN':'2020-01-01'},'sparse_step':23}
r=describe_states(values,schedule,contract)['symbols']['SYN']
out['cutoff_sparse_leak']={'comparison_n':r['comparison']['n'],
                         'true_slots_up':r['sparse_view']['true_slots_up'],
                         'slots':r['sparse_view']['slots']}
v=values.copy(); v['state']='false'
try:
    describe_states(v,schedule,contract); out['string_false']='accepted'
except ValueError as exc: out['string_false']='rejected: '+str(exc)
contract['research_cutoff']='2030-01-01T15:00:00+08:00'
calc=compute_close_state(pd.Series([100.]*20+list(range(101,131)),index=dates))
v=values.copy(); v['state']=calc['state'].array
try:
    describe_states(v,schedule,contract); out['nullable_adapter_to_description']='accepted'
except Exception as exc: out['nullable_adapter_to_description']=type(exc).__name__+': '+str(exc)

# Freeze package closure and original source/contract identities.
packs={}
for name in ('final-synthetic-positive-01','final-real-qualification-01'):
    p=RAW/name; m=json.loads((p/'manifest.json').read_text())
    actual={str(f.relative_to(p)) for f in p.rglob('*') if f.is_file() and f.name!='manifest.json'}
    bad=[k for k,h in m['file_hashes'].items() if not (p/k).exists() or sha(p/k)!=h]
    c=json.loads((p/'contract.source.json').read_text())
    frozen=set(m['files'])
    ev={e['price_basis_evidence']['path'] for e in c['data_identity'].values()}
    packs[name]={'listed':len(m['file_hashes']),'key_difference':sorted(actual^set(m['file_hashes'])),
                 'hash_errors':bad,'contract_hash_equal':sha(p/'contract.source.json')==m['contract_sha256'],
                 'missing_price_evidence_refs_in_archive':sorted(x for x in ev if x not in frozen),
                 'exit_code':m['exit_code']}
out['packages']=packs
baseline=json.loads((RAW/'task-contract.json').read_text())
out['baseline_sections']={}
for section, mapping in baseline.items():
    if isinstance(mapping,dict) and mapping and all(isinstance(v,str) and len(v)==64 for v in mapping.values()):
        changes=[]
        for key, expected in mapping.items():
            p=(Path('/Users/yongbiaoli/.lei_signal_lab/cache/timing')/(key.split(':')[1]+'.parquet')
               if key.startswith('CARRIER:') else ROOT/key)
            if not p.exists() or sha(p)!=expected: changes.append(key)
        out['baseline_sections'][section]={'count':len(mapping),'changed':changes}
cal=TradingCalendar.from_file(ROOT/'docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json')
days=cal.trading_days('2019-09-01','2019-10-31')
tail=cal.trading_days('2026-01-01','2026-03-01')
out['calendar']={'day21':days[20],'target22_after_2025_12_31':tail[21]}
csvcheck={}
for ver,p in [('v1',ROOT/'docs/experiments/raw/factor-unit-close-adapter-2026-09-15/source-decision.csv'),('v2',RAW/'source-decision-v2.csv')]:
    with p.open(newline='') as f:
        rows=list(csv.reader(f))
    csvcheck[ver]={'row_lengths':[len(r) for r in rows],
                  'identities':[(r[0],r[1],r[2]) for r in rows[1:]]}
out['csv']=csvcheck
text=json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)
print(text)
if len(sys.argv)>1:
    with Path(sys.argv[1]).open('x') as f:f.write(text+'\n')
