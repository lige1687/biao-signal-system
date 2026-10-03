"""Inventory and verify this study's existing artifacts; no market calculation."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[4]
GUIDE = ROOT/'docs/research/methods/factor-validation-guide.md'
MAIN = ROOT/'docs/experiments/risk-shape-information-2026-10-03.md'
SUPPLEMENT = ROOT/'docs/experiments/risk-shape-multimethod-2026-10-03.md'
CASE = ROOT/'docs/research/methods/research-method-cases/cases/rmc-2026-10-03-risk-shape-multimethod.json'

def read(p): return json.loads(p.read_text())
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def relative(p): return str(p.relative_to(ROOT))
def record(p): return {'path': relative(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}
def dump(p, value):
    assert not p.exists(), str(p)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def raw_files():
    return sorted(p for p in BASE.rglob('*') if p.is_file() and HERE not in p.parents and '__pycache__' not in p.parts)

def build():
    plan = read(BASE/'trial-plan.json'); defs = read(ROOT/'docs/research/definitions.v1.json')['objects']
    factors = []
    for name in ['vol_instability20','beta_asymmetry60','negative_cluster60']:
        card = next(x for x in defs if x['id'] == f'research.risk.{name}' and x['version'] == '1.0.0')
        canonical = json.dumps(card,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        rr = [x for x in plan['planned_experiments'] if x['candidate'] == name]
        factors.append({'definition_ref':f'{card["id"]}@{card["version"]}', 'definition_registry':'docs/research/definitions.v1.json', 'definition_card_canonical_sha256':hashlib.sha256(canonical).hexdigest(),
            'original_runs':{x['mode']:x['run_path'] for x in rr},
            'published_receipt':relative(BASE/f'accepted-{name}-main/receipt.json'),
            'numeric_report':f'docs/experiments/risk-shape-{name}-main-2026-10-03.md',
            'diagnostic_key':name, 'diagnostics':relative(BASE/'diagnostics.json'),
            'supplement_key':name,'supplement_results':relative(BASE/'multimethod-01/methods.json')})
    index = {'kind':'local_study_navigation_and_integrity_snapshot_not_new_registry','created_at':datetime.now(timezone.utc).isoformat(),
        'authorization':'用户要求沉淀因子验证方法、研究相关全部留痕；继续。',
        'scope':'Original three risk-shape factors and their actual existing records; documentation and artifact integrity only.',
        'new_experiments':0,'new_fits':0,'new_market_requests':0,'files_moved_or_deleted':0,
        'factors':factors,'raw_root':relative(BASE),'raw_inventory':[record(p) for p in raw_files()],
        'documentation_snapshot':[record(p) for p in [GUIDE,MAIN,SUPPLEMENT,CASE,HERE/'check_trace.py']]+[record(ROOT/x['numeric_report']) for x in factors],
        'live_navigation_only':['docs/research/research-workflow-usage.md','docs/research/methods/research-method-cases/README.md','docs/ops/work-progress/risk-shape-information.md','docs/experiments/registry.json','docs/experiments/INDEX.md'],
        'failure_and_correction_paths':[relative(BASE/p) for p in ['controller-coverage-correction.json','delegation-preflight-failure.json','execution-metadata-repair.json','execution-path-correction.json','run-vol_instability20-solo/failure.json','multimethod-01/joint-B1-fold0.json','multimethod-01/joint-B1-fold1.json','multimethod-01/completion.json']],
        'historical_state_snapshot':relative(BASE/'multimethod-01/previous-state.json'),
        'authority':'Original definitions, frozen contracts, workflow family log and report registry remain authoritative; no production adoption or new universal method approval.',
        'storage':'Local shared workspace only; no commit, push or remote backup performed; large original material is not staged.',
        'exclusions':'This index/verification outputs excluded to avoid recursive hashing; generated __pycache__ excluded; live shared navigation is resolved but not frozen.'}
    dump(HERE/'evidence-index.json',index)

def verify():
    index=read(HERE/'evidence-index.json'); checks={}; counted=0
    for item in index['raw_inventory']+index['documentation_snapshot']:
        p=ROOT/item['path']; assert p.is_file(),p
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],p
        counted+=1
    assert set(x['path'] for x in index['raw_inventory'])==set(relative(p) for p in raw_files())
    checks['complete_current_raw_inventory']=len(index['raw_inventory'])
    defs=read(ROOT/'docs/research/definitions.v1.json')['objects'];registry=read(ROOT/'docs/experiments/registry.json')['entries']
    fits=0; receipts=0
    for factor in index['factors']:
        name,version=factor['definition_ref'].rsplit('@',1)
        card=next(x for x in defs if x['id']==name and x['version']==version)
        canonical=json.dumps(card,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        assert hashlib.sha256(canonical).hexdigest()==factor['definition_card_canonical_sha256']
        for run in factor['original_runs'].values():
            directory=ROOT/run;result=read(directory/'result.json');receipt=read(directory/'receipt.json')
            assert sha(directory/'contract.json')==receipt['contract_sha256']
            for fn,h in receipt['outputs'].items():assert sha(directory/fn)==h
            fits+=len(result['execution']['fit_details']);receipts+=1
        publication=ROOT/factor['published_receipt'];directory=publication.parent;receipt=read(publication)
        assert sha(directory/'contract.json')==receipt['contract_sha256']
        for fn,h in receipt['outputs'].items():assert sha(directory/fn)==h
        report=ROOT/factor['numeric_report'];assert report.exists() and report.read_bytes()==(directory/'report.md').read_bytes()
        entry=registry[factor['numeric_report']];assert (ROOT/entry['workflow_receipt']).resolve()==publication.resolve()
        receipts+=1
    assert fits==24 and len(index['factors'])==3
    checks.update(original_successful_runs=6,actual_fit_records_preserved=fits,receipts_hash_verified=receipts,formal_reports_registered=5)
    for p in [MAIN,SUPPLEMENT]:assert relative(p) in registry and '## 一句话结论（大白话）' in p.read_text()
    assert read(CASE)['status']=='observed' and read(CASE)['rule_changed'] is False and read(CASE)['evaluator_changed'] is False
    for path in index['failure_and_correction_paths']:assert (ROOT/path).is_file()
    assert read(BASE/'run-vol_instability20-solo/failure.json')
    for f in [0,1]:assert read(BASE/f'multimethod-01/joint-B1-fold{f}.json')['status']=='not_applicable'
    changed=[];restored=[]
    for line in (BASE/'SHA256SUMS').read_text().splitlines():
        expected,path=line.split('  ',1);p=BASE/path
        if sha(p)!=expected:
            changed.append(path)
            assert path=='research-state.json'
            assert sha(BASE/'multimethod-01/previous-state.json')==expected
            restored.append(relative(BASE/'multimethod-01/previous-state.json'))
    checks.update(historical_raw_manifest_changed_files=changed,original_state_fingerprint_recovered_at=restored)
    for path,h in read(BASE/'multimethod-01/plan.json')['inputs'].items():
        p=BASE/'multimethod-01/previous-state.json' if path.endswith('/research-state.json') else ROOT/path
        assert sha(p)==h,path
    links=0
    for p in [GUIDE,MAIN,SUPPLEMENT,ROOT/'docs/research/research-workflow-usage.md']:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            file=target.split('#',1)[0].strip('<>');assert (p.parent/file).exists(),(p,target)
            links+=1
    assert read(BASE/'research-state.json')['execution']=='completed'
    checks.update(local_markdown_links_resolved=links,fingerprinted_files_checked=counted,core_scientific_inputs_unchanged=True,new_experiments=0,new_fits=0)
    return {'status':'passed','checks':checks,'scope':'Artifact integrity and traceability; not another test of scientific efficacy or historical availability.','new_market_requests':0}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if args.build:build()
    answer=verify()
    if args.build:dump(HERE/'verification.json',answer)
    print(json.dumps(answer,ensure_ascii=False,indent=2))
