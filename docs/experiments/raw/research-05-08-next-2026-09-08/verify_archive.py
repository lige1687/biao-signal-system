"""Verify this batch and seal only its files; preserve previous batch inputs."""
from pathlib import Path
import json,hashlib,re,datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
checks=[]
for name in ['input-manifest.json','supplement-manifest.json']:
 for x in json.loads((P/name).read_text())['files']:
  f=Path(x['snapshot']);assert sha(f)==x['sha256'];checks.append(str(f))
prior=json.loads((P.parent/'research-unified-2026-09-08/e01/run-manifest.json').read_text())
for f,digest in prior['inputs'].items():assert sha(Path(f))==digest
reports=['ambush-pending-boundaries-2026-09-08.md','dca-split-data-audit-2026-09-08.md','sentiment-four-input-audit-2026-09-08.md','ai-future-validation-protocol-2026-09-08.md','research-05-08-progress-2026-09-08.md']
reg=json.loads((ROOT/'docs/experiments/registry.json').read_text());links=0
for name in reports:
 f=ROOT/'docs/experiments'/name;text=f.read_text();assert '## 一句话结论（大白话）' in text and '## ARCHIVE' in text
 assert reg['entries']['docs/experiments/'+name]['category'] in reg['categories']
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http:','https:','/upgrades')):continue
  assert (f.parent/target.split('#')[0]).exists(),(name,target);links+=1
r=json.loads((P/'05/results.json').read_text());assert len(r['synthetic_checks'])==8 and r['accounts_checked']==64 and r['all_original_outputs_identical'];assert r['status_counts']=={'cancelled_buy_cap':732}
q=json.loads((P/'07/condition-dates.json').read_text());assert len(q)==514
for code,n in [('BK1036',0),('BK0478',96)]:
 a=[x for x in q if x['code']==code];assert sum(x['complete'] for x in a)==n;assert not any(x['condition_state']=='true' for x in a)
x=json.loads((P/'06/split-audit.json').read_text());assert abs(x['share_adjusted_return']-(-0.02253466872110954))<1e-12
v=dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_frozen_inputs_unchanged=len(checks),prior_sealed_inputs_unchanged=len(prior['inputs']),registered_reports=len(reports),local_report_links_checked=links,e01_original_outputs_unchanged_accounts=64,synthetic_checks=8,independent_review_present=(P/'05/independent-review.md').exists(),claim_scope='Research reporting/data audit/protocol only; no new validated trading performance')
(P/'verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2))
files={str(f.relative_to(ROOT)):sha(f) for f in P.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.name!='final-manifest.json'}
for name in reports:
 f=ROOT/'docs/experiments'/name;files[str(f.relative_to(ROOT))]=sha(f)
(P/'final-manifest.json').write_text(json.dumps(dict(sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,prior_inputs=prior['inputs']),ensure_ascii=False,indent=2))
for name,digest in files.items():assert sha(ROOT/name)==digest
print(json.dumps(v,ensure_ascii=False));print('Sealed files',len(files))
