from pathlib import Path
import json,hashlib,re,datetime
import pandas as pd
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
inputs=[]
for name in ['input-manifest.json','supplement-manifest.json']:
 inputs+=json.loads((P/name).read_text())['files']
inputs+=json.loads((P/'07/replay-inputs.json').read_text())
for x in inputs:assert sha(Path(x['snapshot']))==x['sha256'],x['snapshot']
prior=json.loads((P.parent/'research-05-08-next-2026-09-08/final-manifest.json').read_text())
for name,digest in prior['files'].items():assert sha(ROOT/name)==digest,name
fetch=json.loads((P/'06/fetch-manifest.json').read_text());assert len(fetch)==28
for x in fetch:assert not x['error'] and x['field']=='qfqday' and sha(P/'06'/x['file'])==x['sha256']
coverage=json.loads((P/'06/long-coverage.json').read_text());assert coverage['common_dates']==3187 and all(not x['conflicting_overlap_dates'] for x in coverage['products'])
data=pd.read_csv(P/'07/legacy-observations.csv');summary=json.loads((P/'07/replay-summary.json').read_text())['results'];assert len(data)==252 and not data.duplicated(['event','code','date']).any()
for x in summary:
 d=data[data.event==x['event']];assert len(d)==x['observations'] and abs(d.price_change.mean()*100-x['mean_percent'])<1e-10 and x['matches_old_rounded']
assert abs((data.end_price/data.start_price-1-data.price_change)).max()<1e-12
ledger=pd.read_csv(P/'06/dividend-daily-ledger.csv');assert abs(ledger.units*ledger.nominal_close+ledger.cash+ledger.dividend_receivable-ledger.equity).max()<1e-12
assert ledger.loc[(ledger.date>='2025-06-18')&(ledger.date<'2025-06-27'),'cash'].eq(0).all()
assert abs(ledger.loc[ledger.date=='2025-06-27','cash'].iloc[0]-.088)<1e-12
r=json.loads((P/'06/dividend-results.json').read_text());assert all(r['synthetic_checks'].values()) and abs(r['nominal_plus_cash_return']-((3.982+.088)/3.972-1))<1e-12
cases=json.loads((P/'08/explanation-cases.json').read_text())['cases'];assert len(cases)==len({x['case_id'] for x in cases})==8
for c in cases:
 assert c['score'] is None and c['A1_model_response'] is None and c['user_comprehension'] is None
 for ref in c['references']:assert sha(Path(ref['path']))==ref['sha256']
cards=json.loads((P/'evidence-cards.json').read_text());assert len(cards)==4
for c in cards:
 ref=c['evidence_ref'];assert ref['schema_version']=='provenance/1.2' and ref['compatibility']=='unknown'
 for path,digest in zip(ref['source_path'],ref['source_hash']):assert sha(Path(path))==digest
reports=['dca-long-data-cash-boundary-2026-09-08.md','icepoint-legacy-replay-2026-09-08.md','ai-explanation-exercise-pack-2026-09-08.md','research-third-progress-2026-09-08.md'];reg=json.loads((ROOT/'docs/experiments/registry.json').read_text());links=0
for name in reports:
 f=ROOT/'docs/experiments'/name;t=f.read_text();assert '## 一句话结论（大白话）' in t and '## ARCHIVE' in t;assert reg['entries']['docs/experiments/'+name]['category'] in reg['categories']
 for target in re.findall(r'\]\(([^)]+)\)',t):
  if target.startswith(('http:','https:')):continue
  assert (f.parent/target.split('#')[0]).exists(),(name,target);links+=1
out=dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),frozen_inputs_unchanged=len(inputs),previous_sealed_files_unchanged=len(prior['files']),public_history_responses_checked=28,legacy_observations_checked=252,dividend_accounting_identity=True,practice_materials_unscored=8,provenance_cards=4,reports_registered=4,local_links_checked=links,claim='Bounded data and evidence verification; full portfolio and AI efficacy not established')
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
files={str(f.relative_to(ROOT)):sha(f) for f in P.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.name!='final-manifest.json'}
for name in reports:
 f=ROOT/'docs/experiments'/name;files[str(f.relative_to(ROOT))]=sha(f)
(P/'final-manifest.json').write_text(json.dumps(dict(sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files),ensure_ascii=False,indent=2))
for name,digest in files.items():assert sha(ROOT/name)==digest
print(json.dumps(out,ensure_ascii=False));print('Sealed files',len(files))
