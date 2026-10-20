"""Bounded public read: four fixed ETFs, seven two-year ranges; no cache writes."""
from pathlib import Path
import urllib.request,urllib.parse,json,hashlib,datetime
from concurrent.futures import ThreadPoolExecutor
P=Path(__file__).resolve().parent
def fetch(job):
 sym,year=job;start=f'{year-1}-12-15' if year>2013 else '2013-01-01';end=f'{year+1}-12-31' if year<2025 else '2026-09-07'
 url='https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'+urllib.parse.urlencode({'param':f'{sym},day,{start},{end},640,'})
 rec=dict(symbol=sym,start=start,end=end,url=url,retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  with urllib.request.urlopen(url,timeout=25) as r:raw=r.read()
  f=P/f'{sym}-{year}.json';f.write_bytes(raw);obj=json.loads(raw);data=obj.get('data');d=data.get(sym,{}) if isinstance(data,dict) else {};field='qfqday' if d.get('qfqday') else 'day';rows=d.get(field,[])
  rec.update(file=f.name,sha256=hashlib.sha256(raw).hexdigest(),field=field,rows=len(rows),first=rows[0][0] if rows else None,last=rows[-1][0] if rows else None,error=obj.get('msg') or None)
 except Exception as e:rec['error']=str(e)
 return rec
jobs=[(s,y) for s in ['sh510300','sz159915','sh518880','sh513100'] for y in range(2013,2027,2)]
(P/'download-plan.json').write_text(json.dumps(dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),jobs=jobs,max_requests=28,purpose='nominal data coverage only; no strategy outcomes'),indent=2))
with ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(fetch,jobs))
(P/'fetch-manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
