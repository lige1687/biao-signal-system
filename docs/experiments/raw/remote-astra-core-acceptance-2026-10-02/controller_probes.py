"""Bounded acceptance checks; no production edits or new return experiment."""
from pathlib import Path
import csv, json, sys, tempfile, subprocess, copy
from decimal import Decimal, ROUND_HALF_UP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
C = ROOT / '.biao/remote-astra-acceptance-20261002/checkout'
sys.dont_write_bytecode = True
sys.path.insert(0, str(C/'docs/experiments/raw/remote-astra-T9-2026-09-30'))
import observation_ledger as t9
sys.path.insert(0, str(C/'docs/experiments/raw/remote-astra-T10-2026-09-30'))
import handoff_check as t10

ledger, _ = t9.case_matured()
before = t9.validate(ledger)
next(r for r in ledger if r['kind']=='outcome')['payload']['values']['ret20'] = 0.9
for i,r in enumerate(ledger):
    r['prev_hash'] = ledger[i-1]['hash'] if i else None
    r['hash'] = t9._digest(r)
out = {'t9_rehashed_edit': {'before_errors':before, 'after_errors':t9.validate(ledger),
                          'changed_mean':t9.review(t9.derive(ledger),t9.OBJ)['first_mean']}}
temp_root = ROOT/'.biao/remote-astra-acceptance-20261002/tmp/controller'
temp_root.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=temp_root) as tmp:
    package,code,manifest = t10.build_synthetic(Path(tmp))
    manifest['missing'].append({'item':'frozen dependency lock required for replay', 'reason':'not transferred'})
    out['t10_declared_required_missing'] = t10.check(package,manifest,code)

def git(*args):
    return subprocess.check_output(['git',*args],cwd=C).decode()
base='639ad8d'
changes=[line.split('\t') for line in git('diff',base,'HEAD','--name-status').splitlines()]
allowed_dirs = ['docs/research/proposals/remote-astra-2026-09-30/']
allowed_dirs += [f'docs/experiments/raw/remote-astra-T{i}-2026-09-30/' for i in (2,3,4,5,6,7,9,10)]
allowed_dirs += ['docs/experiments/raw/remote-astra-T2-audit-2026-10-02/']
reports = ['docs/experiments/remote-astra-core-review-2026-09-30.md','docs/experiments/module-a-population-audit-2026-10-02.md']
allowed_modified=['docs/experiments/INDEX.md','docs/experiments/registry.json']
scope_bad=[(s,p) for s,p in changes if not (s=='A' and (p in reports or any(p.startswith(d) for d in allowed_dirs)) or s=='M' and p in allowed_modified)]
old=json.loads(git('show',base+':docs/experiments/registry.json'))
new=json.loads(git('show','HEAD:docs/experiments/registry.json'))
out['delivery_boundary']={'files':len(changes),'stat':git('diff',base,'HEAD','--shortstat').strip(),
    'unexpected_paths':scope_bad,'modified_existing':[p for s,p in changes if s!='A'],
    'all_old_registry_entries_preserved':all(new['entries'].get(k)==v for k,v in old['entries'].items()),
    'registry_metadata_preserved':all(new.get(k)==v for k,v in old.items() if k!='entries'),
    'new_registry_entries':[k for k in new['entries'] if k not in old['entries']],
    'index_deletions':int(git('diff',base,'HEAD','--numstat','--','docs/experiments/INDEX.md').split()[1])}
out['oct8_prices']={}
for symbol, pct in [('sh510300','0.1'),('sz159915','0.2')]:
    p=C/f'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/bars/{symbol}-nominal.csv'
    rows=list(csv.DictReader(p.open()))
    i=next(i for i,r in enumerate(rows) if r['date']=='2024-10-08')
    prev, day, nex = rows[i-1], rows[i], rows[i+1]
    limit=(Decimal(prev['close'])*(1+Decimal(pct))).quantize(Decimal('0.001'),rounding=ROUND_HALF_UP)
    out['oct8_prices'][symbol]={'previous_date':prev['date'],'previous_close':prev['close'],
        'open':day['open'],'close':day['close'],'limit_under_frozen_rate':str(limit),
        'open_equals_limit':Decimal(day['open'])==limit,'next_date':nex['date'],'next_open':nex['open']}
(HERE/'controller-probes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
