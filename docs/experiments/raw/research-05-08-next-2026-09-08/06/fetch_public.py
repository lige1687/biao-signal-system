"""Four products only. One retry uses the frozen provider's 1500-bar default."""
from pathlib import Path
import urllib.request,urllib.parse,json,hashlib,datetime
from concurrent.futures import ThreadPoolExecutor
P=Path(__file__).resolve().parent
def get(sym):
 url='https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'+urllib.parse.urlencode({'param':f'{sym},day,,,1500,qfq'})
 rec=dict(symbol=sym,url=url,retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
 try:
  with urllib.request.urlopen(url,timeout=25) as r:data=r.read()
  (P/f'{sym}-retry-response.json').write_bytes(data);obj=json.loads(data);payload=obj.get('data');d=payload.get(sym,{}) if isinstance(payload,dict) else {};field='qfqday' if d.get('qfqday') else 'day';bars=d.get(field,[])
  rec.update(sha256=hashlib.sha256(data).hexdigest(),selected_field=field,rows=len(bars),first=bars[0][0] if bars else None,last=bars[-1][0] if bars else None,response_keys=list(d),message=obj.get('msg'),historical_cache_provenance_inferred=False)
 except Exception as e:rec['error']=str(e)
 return rec
with ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(get,['sh510300','sz159915','sh518880','sh513100']))
(P/'public-retry-manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
