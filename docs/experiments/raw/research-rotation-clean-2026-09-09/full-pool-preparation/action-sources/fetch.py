from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,hashlib,json,io,re
import pandas as pd
B=Path(__file__).resolve().parent
SYMS=['510300','512400','515050','515130','515300','518850','588000','515170','516220','159652','512890','515880','513870','562590']
def fetch(s):
 u=f'https://fundf10.eastmoney.com/fhsp_{s}.html'
 try:
  raw=urllib.request.urlopen(u,timeout=25).read(); (B/f'{s}.html').write_bytes(raw)
  txt=raw.decode('utf-8');tables=pd.read_html(io.StringIO(txt)); tab=[]
  for i,t in enumerate(tables):
   t.to_csv(B/f'{s}-table{i}.csv',index=False);tab.append(t.fillna('').to_dict('records'))
  return {'symbol':s,'url':u,'sha256':hashlib.sha256(raw).hexdigest(),'title':re.search(r'<title>(.*?)</title>',txt).group(1),'tables':tab,'status':'ok','source_level':'secondary compilation; official material needed for final action assurance'}
 except Exception as e:return {'symbol':s,'url':u,'status':'failed','error':str(e)}
with ThreadPoolExecutor(max_workers=4) as ex: out=list(ex.map(fetch,SYMS))
(B/'index.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for r in out:print(r['symbol'],r['status'],r.get('title'),r.get('tables'))
