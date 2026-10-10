"""Update only the owned startup report registration and read actual served report."""
from pathlib import Path
import hashlib,json,re,urllib.request
ROOT=Path(__file__).resolve().parents[4]
RAW=Path(__file__).parent
reg=json.loads((RAW/'zero-sale-registration-entry.json').read_text())
rp=ROOT/reg['report']
assert hashlib.sha256(rp.read_bytes()).hexdigest()==reg['entry']['report_sha256']
p=ROOT/'docs/experiments/registry.json'
before=p.read_text()
old=json.loads(before)
match=re.search(r'(?m)^[ \\t]*'+re.escape(json.dumps(reg['report']))+r'[ \\t]*:[ \\t]*',before)
assert match
_,end=json.JSONDecoder().raw_decode(before[match.end():])
after=before[:match.end()]+json.dumps(reg['entry'],ensure_ascii=False,indent=2)+before[match.end()+end:]
new=json.loads(after)
assert set(old['entries'])==set(new['entries'])
assert all(old['entries'][k]==new['entries'][k] for k in old['entries'] if k!=reg['report'])
p.write_text(after)
ins=json.loads((RAW/'shared-document-insertions.json').read_text())
p=ROOT/'docs/experiments/INDEX.md'
text=p.read_text()
prev=ins['previous_own_lines']['zero_sale_index_line']
assert text.count(prev)==1 or ins['zero_sale_index_line'] in text
if prev in text:text=text.replace(prev,ins['zero_sale_index_line'],1)
p.write_text(text)
p=ROOT/'docs/experiments/research-evidence-catalog-2026-10-07.md'
text=p.read_text()
header='## 2026-10-10 当前接续：D条件描述已结案，历史成员单事件复用已有原件\n'
assert text.startswith(header)
marker='\n---\n\n'
tail=text[text.index(marker)+len(marker):]
p.write_text(ins['catalog_prefix']+tail)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
url='http://127.0.0.1:8000/api/experiments/'+reg['report']
with opener.open(url,timeout=20) as r:served=json.load(r)
(RAW/'startup-approved-served-report-20261011.json').write_text(json.dumps(served,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'report_sha256':reg['entry']['report_sha256'],'registry_unrelated_entries_unchanged':True,'served_keys':list(served)},ensure_ascii=False))
