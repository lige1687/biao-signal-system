"""Read actual report API fields and hashes, refreshing only owned report entries."""
from pathlib import Path
import hashlib,json,re,urllib.request
ROOT=Path(__file__).resolve().parents[4];RAW=Path(__file__).parent
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
rp=ROOT/'docs/experiments/registry.json';before=rp.read_text();body=before;old=json.loads(before)
registrations=[json.loads((RAW/(x+'-registration-entry.json')).read_text()) for x in ('zero-sale','complete-account')]
for r in registrations:
    assert hashlib.sha256((ROOT/r['report']).read_bytes()).hexdigest()==r['entry']['report_sha256']
    match=re.search(r'(?m)^ *'+re.escape(json.dumps(r['report']))+r' *: *',body);assert match
    _,end=json.JSONDecoder().raw_decode(body[match.end():])
    body=body[:match.end()]+json.dumps(r['entry'],ensure_ascii=False,indent=2)+body[match.end()+end:]
parsed=json.loads(body);names={x['report'] for x in registrations}
assert all(v==parsed['entries'][k] for k,v in old['entries'].items() if k not in names)
assert set(old['entries'])==set(parsed['entries'])
rp.write_text(body)
checks=[]
for r in registrations:
    with op.open('http://127.0.0.1:8000/api/experiments/'+r['report'],timeout=30) as f:d=json.load(f)
    h=hashlib.sha256(d['markdown'].encode()).hexdigest()
    assert h==r['entry']['report_sha256']
    assert d['category']==r['entry']['category'] and d['verdict']==r['entry']['verdict']
    checks.append({'report':r['report'],'served_markdown_sha256':h,'category':d['category'],'verdict':d['verdict'],'oneLiner':d['oneLiner']})
with op.open('http://127.0.0.1:8000/api/experiments',timeout=45) as f:d=json.load(f)
for x in checks:
    row=next(t for t in d['items'] if t['name']==x['report'])
    assert row['pending'] is False and row['category']==x['category'] and row['verdict']==x['verdict']
    assert row['oneLiner']==x['oneLiner']
    x['list_pending']=row['pending']
q=RAW/'complete-account-report-api-readback-20261011.json'
q.write_text(json.dumps({'checks':checks,'registry_other_entries_preserved':True,'actual_single_fulltext_and_list_fields_readback':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'reports_checked':len(checks),'actual_sha_and_classification_match':True,'list_pending_false':True},ensure_ascii=False))
