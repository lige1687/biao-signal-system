from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import requests,json,hashlib
from bs4 import BeautifulSoup
from pypdf import PdfReader
P=Path(__file__).resolve().parent/'sources'
urls={
 'szse-20200824-20pct.pdf':'https://docs.static.szse.cn/www/aboutus/trends/conference/W020200821767425488573.pdf',
 'sse-etf-faq.html':'https://www.sse.com.cn/assortment/fund/etf/question/',
 'sse-gold-guide.html':'https://www.sse.com.cn/assortment/fund/etf/rules/c/c_20150911_3985190.shtml',
 'sse-2013-limit.html':'https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20150912_3988628.shtml',
 'sse-20150119-t0.html':'https://english.sse.com.cn/news/newsrelease/c/4947611.shtml',
 'szse-2006-rules.html':'https://investor.szse.cn/disclosure/notice/t20060515_499577.html',
 'szse-fund-units.html':'https://investor.szse.cn/knowledge/fund/trade/t20171113_538865.html',
 'szse-2014-sell-lots.html':'https://www.szse.cn/lawrules/rule/trade/current/t20150914_565054.html',
 'szse-2025-march-stats.html':'https://docs.static.szse.cn/www/market/periodical/month/W020250402560972808549.html'}
def fetch(item):
 n,u=item;meta=dict(file=n,url=u,retrieved_at_utc=datetime.now(timezone.utc).isoformat())
 try:
  r=requests.get(u,timeout=25);meta.update(status=r.status_code,final_url=r.url,bytes=len(r.content));r.raise_for_status();(P/n).write_bytes(r.content);meta['sha256']=hashlib.sha256(r.content).hexdigest()
  if n.endswith('.pdf'):
   pdf=PdfReader(P/n); text='\n'.join(f'=== PDF PAGE {i+1} ===\n'+(p.extract_text() or '') for i,p in enumerate(pdf.pages));meta['pages']=len(pdf.pages)
  else:
   encoding='gb18030' if n=='szse-2025-march-stats.html' else 'utf-8'; text=BeautifulSoup(r.content.decode(encoding),'html.parser').get_text('\n',strip=True)
  (P/(n+'.txt')).write_text(text);meta['status_text']='fetched_primary_source'
 except Exception as e:meta['error']=repr(e)
 return meta
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=5) as pool: result=list(pool.map(fetch,urls.items()))
 (P/'new-rule-sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))
