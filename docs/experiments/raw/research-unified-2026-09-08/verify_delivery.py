from pathlib import Path
import json,hashlib,sys,re,urllib.request
import pandas as pd
P=Path(__file__).resolve().parent;ROOT=P.parents[3];sys.path.insert(0,str(ROOT/'src'))
from lei_signal.api.experiment_reports import scan_reports,read_report,extract_meta
from lei_signal.api import upgrades_store as store

def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(n):return json.loads((P/n).read_text())
out={};reports=load('report-list.json');items={r['name']:r for r in scan_reports(ROOT)};out['reports']=[]
for n in reports:
 name='docs/experiments/'+n;d=read_report(name,ROOT);assert d and name in items;assert d['category']!='待分类' and d['verdict']=='mixed';assert '## ARCHIVE' in d['markdown'];assert '## 一句话结论（大白话）' in d['markdown'];assert extract_meta(d['markdown'],n)['oneLiner'];out['reports'].append({'name':name,'category':d['category'],'verdict':d['verdict'],'listed':True,'body_readable':True})
 # Check concrete Markdown references, excluding URLs and the not-yet-written final manifest.
 for target in re.findall(r'\]\(([^)]+)\)',d['markdown']):
  if '://' in target or target.startswith('#'):continue
  target=target.split('#')[0]
  if target.endswith('final-manifest.json'):continue
  assert (ROOT/'docs/experiments'/target).exists(),target
out['snapshot_checks']=[]
for group in [load('e01/input-manifest.json')['files'],load('other-lines/source-manifest.json')]:
 for x in group:
  assert h(x['snapshot'])==x['sha256'];out['snapshot_checks'].append(x['snapshot'])
for manifest in ['e02/run-manifest.json','ai-replay/run-manifest.json']:
 d=load(manifest)
 for f,v in d['inputs'].items():assert h(f)==v,(manifest,f)
# Final versions must still match the versions actually executed.
assert h(P/'e02/run_e02.py')==load('e02/run-manifest.json')['script_sha256']
assert h(P/'ai-replay/run.py')==load('ai-replay/run-manifest.json')['script_hash']
checks={}
for f in (P/'e01/inputs/cache').glob('*.parquet'):
 if f.stem=='breadth_cn_all':continue
 d=pd.read_parquet(f);checks[f.stem]={'nonpositive_ohlc':int((d[['open','high','low','close']]<=0).sum().sum()),'nonfinite_ohlc':int(d[['open','high','low','close']].isna().sum().sum())};assert checks[f.stem]['nonpositive_ohlc']==0
out['price_positive_check']=checks
assert all(load('e02/label-fix-verification.json').values())
# All serialized public references carry actual file fingerprints.
cards=load('evidence-cards.json');assert len(cards['cards'])==5
for c in cards['cards']:
 for e in c['evidence_refs']:
  assert e['schema_version']=='provenance/1.2' and e['compatibility']=='reference'
  assert all(h(f)==v for f,v in zip(e['source_path'],e['source_hash']))
 for r in c['rule_refs']:assert h(r['config_path'])==r['config_hash']
 for d in c['data_refs']:assert d['health']=='unknown'
out['evidence_cards']=5
current=store.list_goals('/Users/yongbiaoli/.lei_signal_lab/system_upgrades.db');idx={x['id']:x for x in current['items']};out['okr']=[]
for key,id in load('okr-ids.json').items():
 x=idx[id];want='approved' if key in ['06b','07b','08b'] else 'review';assert x['status']==want,(key,x['status']);assert x['authorization']['granted'];out['okr'].append({'key':key,'id':id,'status':x['status'],'progress':x['progress']})
assert idx['okr-9236b2cd4622']['status']=='review';out['prior_round_review_preserved']=True
for key in ['okr-2e99d9d04832','K-baseline','K-risk-attribution','K-data-boundary','K-trial-ledger','K-forward-protocol','okr-b9a424674e29']:assert idx[key]['authorization']['granted']
try:
 with urllib.request.urlopen('http://localhost:8000/api/upgrades',timeout=2) as r:out['http_service']={'available':True,'code':r.status}
except Exception as e:out['http_service']={'available':False,'reason':str(e),'fallback_checked':'same production report loader and upgrades store; no live UI verification'}
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'reports':len(out['reports']),'snapshots':len(out['snapshot_checks']),'evidence_cards':5,'okr':out['okr'],'http':out['http_service']},ensure_ascii=False))
