from pathlib import Path
import json,hashlib,datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def h(f):return hashlib.sha256(f.read_bytes()).hexdigest()
rows=[]
for f in sorted(P.rglob('*')):
 if not f.is_file() or '__pycache__' in f.parts or f.name=='final-manifest.json':continue
 rows.append({'path':str(f.relative_to(ROOT)),'sha256':h(f),'bytes':f.stat().st_size})
for n in json.loads((P/'report-list.json').read_text()):
 f=ROOT/'docs/experiments'/n;rows.append({'path':str(f.relative_to(ROOT)),'sha256':h(f),'bytes':f.stat().st_size})
out={'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_repository':'/Users/yongbiaoli/lei-signal-sync','output_repository':str(ROOT),'data_are_frozen_research_proxies':True,'production_acceptance':False,'new_paid_model_calls':0,'excludes':['this manifest','__pycache__','mutable shared registry and OKR database; see saved exports'], 'files':rows}
(P/'final-manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print({'files':len(rows),'bytes':sum(r['bytes'] for r in rows)})
# Verify the sealed output, not just the generated list.
assert all(h(ROOT/r['path'])==r['sha256'] for r in rows)
print('all sealed hashes verified')
