import requests,re,pandas as pd,json,hashlib,datetime
from io import StringIO
from pathlib import Path
root=Path('docs/experiments/raw/research-mixed-pool-audit-2026-09-09/pool-sources/actual-holdings')
(root/'sources').mkdir(parents=True,exist_ok=True)
H={'Referer':'https://fundf10.eastmoney.com/','User-Agent':'Mozilla/5.0'}
codes=['510300','515130','515050','515880','512400','159652']
meta={}
for c in codes:
 u=f'https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={c}&topline=1000&year=2025&month=12'
 b=requests.get(u,headers=H,timeout=30).content
 p=root/'sources'/f'eastmoney-{c}-2025q4.txt'; p.write_bytes(b)
 t=b.decode('utf-8'); m=re.search(r'content:"(.*)",arryear:',t,re.S)
 if not m: raise RuntimeError(c)
 h=m.group(1).replace('\\"','"')
 df=pd.read_html(StringIO(h))[0]
 out=pd.DataFrame({'symbol':c,'stock_code':df['股票代码'].map(lambda x:str(int(x)).zfill(6)),'stock_name':df['股票名称'].astype(str),'nav_weight_pct':df['占净值 比例'].str.rstrip('%').astype(float),'shares_10k':df['持股数 （万股）'].astype(float),'market_value_10k_cny':df['持仓市值 （万元）'].astype(float)})
 out.to_csv(root/f'holdings-{c}.csv',index=False)
 meta[c]={'rows':len(out),'weight_sum_pct':round(out.nav_weight_pct.sum(),6),'raw_url':u,'raw_sha256':hashlib.sha256(b).hexdigest(),'csv_sha256':hashlib.sha256((root/f'holdings-{c}.csv').read_bytes()).hexdigest()}
# official docs known/attempted
urls={
'515050':'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-31/515050_20260331_44AV.pdf',
'515130':'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-31/515130_20260331_MAH8.pdf',
'512400':'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-31/512400_20260331_XKFK.pdf',
'159652':'https://www.99fund.com/announcement/zx/upload/2026/20260330/561e983b5abf448384420032ab36bfbf.pdf',
'515880':'https://st.gtfund.com/report_root/2026/03/%E5%9B%BD%E6%B3%B0%E4%B8%AD%E8%AF%81%E5%85%A8%E6%8C%87%E9%80%9A%E4%BF%A1%E8%AE%BE%E5%A4%87%E4%BA%A4%E6%98%93%E5%9E%8B%E5%BC%80%E6%94%BE%E5%BC%8F%E6%8C%87%E6%95%B0%E8%AF%81%E5%88%B8%E6%8A%95%E8%B5%84%E5%9F%BA%E9%87%912025%E5%B9%B4%E5%B9%B4%E5%BA%A6%E6%8A%A5%E5%91%8A.pdf'}
for c,u in urls.items():
 try:
  b=requests.get(u,headers={'User-Agent':'Mozilla/5.0'},timeout=30).content
  ok=b.startswith(b'%PDF')
  if ok:
   p=root/'sources'/f'official-{c}-2025-annual.pdf';p.write_bytes(b)
   meta[c]['official']={'url':u,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
  else: meta[c]['official_download_error']=f'not PDF; {len(b)} bytes'
 except Exception as e: meta[c]['official_download_error']=repr(e)
# pair metrics
pairs=[('510300','515130'),('515050','515880'),('512400','159652')]
res=[]
for a,b in pairs:
 A=pd.read_csv(root/f'holdings-{a}.csv',dtype={'stock_code':str}).set_index('stock_code')
 B=pd.read_csv(root/f'holdings-{b}.csv',dtype={'stock_code':str}).set_index('stock_code')
 common=sorted(set(A.index)&set(B.index))
 rows=[]
 for x in common:
  rows.append({'stock_code':x,'stock_name_a':A.loc[x,'stock_name'],'stock_name_b':B.loc[x,'stock_name'],'weight_a_pct':float(A.loc[x,'nav_weight_pct']),'weight_b_pct':float(B.loc[x,'nav_weight_pct']),'min_weight_pct':min(float(A.loc[x,'nav_weight_pct']),float(B.loc[x,'nav_weight_pct']))})
 pd.DataFrame(rows).to_csv(root/f'overlap-{a}-{b}.csv',index=False)
 res.append({'fund_a':a,'fund_b':b,'stock_count_a':len(A),'stock_count_b':len(B),'common_stock_count':len(common),'overlap_nav_weight_pct':round(sum(x['min_weight_pct'] for x in rows),6),'definition':'sum over common stock codes of min(each fund NAV weight %); stock rows only'})
(root/'results.json').write_text(json.dumps({'as_of':'2025-12-31','pairs':res,'funds':meta},ensure_ascii=False,indent=2)+'\n')
# manifest
files=[]
for p in sorted(root.rglob('*')):
 if p.is_file(): files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'manifest.json').write_text(json.dumps({'generated_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'files':files},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps({c:meta[c].get('official_download_error','ok' if 'official' in meta[c] else 'missing') for c in codes},ensure_ascii=False))
