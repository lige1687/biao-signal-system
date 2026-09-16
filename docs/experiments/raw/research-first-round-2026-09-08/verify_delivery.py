from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,datetime,re
p=Path(__file__).resolve().parent;repo=p.parents[3]
def read(url):
 with urllib.request.urlopen(url) as f:return json.load(f)
checks={};reports=['research-first-round-ARCHIVE-2026-09-08.md','research-first-experiment-protocol-2026-09-08.md'];reg=json.loads((repo/'docs/experiments/registry.json').read_text());api=read('http://localhost:8000/api/experiments')
for name in reports:
 rel='docs/experiments/'+name;f=repo/rel;t=f.read_text();assert '## 一句话结论（大白话）' in t and '## ARCHIVE' in t;assert reg['entries'][rel]['category'] in reg['categories'];a=next(x for x in api['items'] if x.get('path')==rel or x.get('name')==rel or x.get('id')==rel);assert not a['pending'];d=read('http://localhost:8000/api/experiments/'+urllib.parse.quote(rel,safe='/'));assert t in d.values();checks[name]={'registered':True,'api_readback':True,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'metadata':a}
freeze=json.loads((p/'next-experiment-freeze.json').read_text());assert hashlib.sha256((repo/'docs/experiments/research-first-experiment-protocol-2026-09-08.md').read_bytes()).hexdigest()==freeze['sha256'];assert (p/'E01-frozen-v1.md').read_bytes()==(repo/'docs/experiments/research-first-experiment-protocol-2026-09-08.md').read_bytes();checks['protocol_frozen']=True
z=json.loads((p/'literature/zotero-after.json').read_text());assert len(z)==18 and all(a['notes']==1 and 'EN7QZYKX' in a['collections'] for a in z);checks['zotero']={'papers':18,'notes':18}
x=read('http://localhost:8000/api/upgrades');root=next(a for a in x['items'] if a['id']=='okr-9236b2cd4622');assert root['status']=='review' and root['progress']=={'done':5,'total':5};checks['okr']={'status':root['status'],'progress':root['progress']}
for key in ['okr-a2eff5db5b52','okr-2e99d9d04832']:
 a=next(q for q in x['items'] if q['id']==key);assert a['status']=='awaiting_approval';checks[key]={'status':a['status']}
for sub,file in [('exits','reproduction_results.json'),('dca','results.json'),('evidence','cross-review-dca-results.json'),('evidence','evidence_card.json')]:json.loads((p/sub/file).read_text())
a=json.loads((p/'exits/reproduction_results.json').read_text());assert a['summary']['opportunities']==16 and a['summary']['independent_mismatch_trades']==0 and a['summary']['historical_mismatch_trades']==3
b=json.loads((p/'dca/results.json').read_text());assert b['round13']['archive_matches']==21 and b['round13']['changed_exits']==10
assert abs(b['round18']['cases']['W5']['accounting_check']['deposit_adjusted_mdd']+.2338042403132382)<1e-12
checks['reported_numbers_match_raw']=True
required=['exits/findings.md','exits/manifest.json','dca/findings.md','dca/amendment.md','evidence/findings.md','evidence/cross-review-dca.md','literature/source-files.json','okr-after.json']
assert all((p/f).exists() for f in required);checks['all_deliverables_present']=True
out={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks};(p/'delivery-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:({'registered':True,'api_readback':True} if k in reports else v) for k,v in checks.items()},ensure_ascii=False,indent=2))
