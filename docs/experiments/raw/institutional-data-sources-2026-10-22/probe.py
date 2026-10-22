"""Bounded public-source probes. No credentials, execution of remote code, or effects."""
import urllib.request, urllib.error, json, hashlib, datetime, concurrent.futures
from pathlib import Path
P=Path(__file__).parent
SOURCES=[
('hf-trader298','https://huggingface.co/api/datasets/trader298/sec-nport'),
('hf-ziplime','https://huggingface.co/api/datasets/ZipLime/fund-holdings-nport'),
('hf-ncen-search','https://huggingface.co/api/datasets?search=ncen&limit=30'),
('cn-070002-scale','https://fundf10.eastmoney.com/gmbd_070002.html'),
('akshare-fund-source','https://raw.githubusercontent.com/akfamily/akshare/main/akshare/fund/fund_em.py'),
('secapi-pricing','https://sec-api.io/pricing'),
('secapi-ncen-doc','https://sec-api.io/docs/form-ncen-api-annual-reports-investment-companies'),
('eodhd-pricing','https://eodhd.com/pricing'),
('stockfit-pricing','https://developer.stockfit.io/pricing'),
('tushare-permissions','https://tushare.pro/document/1?doc_id=108'),
]
def one(pair):
 name,url=pair; rec={'name':name,'url':url,'retrieved_at':datetime.datetime.now().astimezone().isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'LeiSignal-public-source-audit/1.0'})
  with urllib.request.urlopen(req,timeout=25) as r:
   rec.update(status=r.status,content_type=r.headers.get('Content-Type'),final_url=r.url); data=r.read(2_000_001)
  rec['truncated']=len(data)>2_000_000
  if rec['truncated']: data=data[:2_000_000]
  rec.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),file=name+'.txt'); (P/rec['file']).write_bytes(data)
 except Exception as e:
  rec.update(error=str(e),status=getattr(e,'code',None))
 return rec
if __name__=='__main__':
 out=P/'http-probes.json'; assert not out.exists(), 'Preserve prior probe receipts'
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: recs=list(ex.map(one,SOURCES))
 out.write_text(json.dumps(recs,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(recs,ensure_ascii=False,indent=2))
