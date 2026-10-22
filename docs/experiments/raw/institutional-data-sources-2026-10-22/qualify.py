"""Reconcile saved source responses only; no factor or strategy calculations."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import json,re,hashlib,gzip
from bs4 import BeautifulSoup
P=Path(__file__).parent
receipts=[]
for file in sorted(P.glob('http-probes*.json')): receipts+=json.loads(file.read_text())
assert len(receipts)==28
for r in receipts:
 if 'file' in r:
  b=(P/r['file']).read_bytes();assert len(b)==r['bytes'];assert hashlib.sha256(b).hexdigest()==r['sha256'];assert not r['truncated']
alltables={}; summary={}
for r in receipts:
 if not (r['name'].startswith('cn-') and 'file' in r):continue
 s=(P/r['file']).read_text(errors='replace');m=re.search(r'content\s*:\s*("(?:\\.|[^"\\])*")',s)
 if not m:continue
 content=json.loads(m.group(1));soup=BeautifulSoup(content,'html.parser');tables=[]
 for t in soup.find_all('table'):
  rows=[[c.get_text(' ',strip=True) for c in tr.find_all(['td','th'])] for tr in t.find_all('tr')];title=t.find_previous('h4')
  tables.append({'title':title.get_text(' ',strip=True) if title else None,'headers':rows[0],'rows':rows[1:]})
 # Independent markup count from regex against DOM parser.
 assert len(tables)==len(re.findall(r'<table\b',content,re.I))
 assert sum(len(t['rows'])+1 for t in tables)==len(re.findall(r'<tr\b',content,re.I))
 alltables[r['name']]=tables
 summary[r['name']]=[{'title':t['title'],'rows':len(t['rows']),'headers':t['headers'],'first':t['rows'][0],'last':t['rows'][-1]} for t in tables]
flows={n:t[0]['rows'] for n,t in alltables.items() if 'flow' in n}
for n,rows in flows.items():assert len({r[0] for r in rows})==len(rows);assert rows==sorted(rows,reverse=True)
cn2023=[r for r in flows['cn-070002-flow-with-referer'] if r[0]=='2023-12-31'][0]
orig={'subscription':'2744551.62','redemption':'3746991.14','end_shares':'158693101.13'}
for i,(k,v) in enumerate(orig.items(),1):assert (Decimal(v)/Decimal('100000000')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)==Decimal(cn2023[i])
assert len(alltables['cn-070002-2021-top100'][0]['rows'])==100
assert len(alltables['cn-070002-2021-top1000'][0]['rows'])==10
assert 'QDII' in alltables['cn-110011-holdings-2025'][0]['title']
assert len(json.loads((P/'eodhd-split-demo.txt').read_text()))==4
hf=[]
for name in ['hf-trader298','hf-ziplime']:
 d=json.loads((P/(name+'.txt')).read_text());hf.append({'dataset':d['id'],'revision':d['sha'],'last_modified':d['lastModified'],'files':len(d['siblings'])})
report={'status':'passed_source_reconciliation_not_factor_validity','http_requests':len(receipts),'http_successes':sum(r.get('status')==200 for r in receipts),'http_failures':[{'name':r['name'],'status':r.get('status'),'error':r.get('error')} for r in receipts if r.get('status')!=200], 'response_hashes_verified':sum('file' in r for r in receipts),'hf':hf,'fund_flow_rows':{n:len(r) for n,r in flows.items()},'holdings_2025_rows_Q4_Q3_Q2_Q1':{n:[len(t['rows']) for t in ts] for n,ts in alltables.items() if 'holdings-2025' in n},'excluded_from_pure_A_share_sample':['110011: observed QDII fund title and HK positions; historic mandate not qualified'],'earlier_pdf_spotcheck':{'source':'docs/experiments/a-share-contrarian-positioning-research-2026-10-20.md','period':'2023-12-31','prior_original_values':orig,'rounded_web_values':cn2023[1:4],'matched':True,'independent_reopening_original_this_turn':False},'cap_check':{'fund':'070002','period':'2021-12-31','prior_original_report_rows':187,'topline100_rows':100,'topline1000_rows':10,'conclusion':'Default wrapper truncates known long portfolio; larger undocumented value falls back and does not solve it'},'missing_for_research':['Historical announcement time and revisions in Eastmoney samples','Historical fund universe including merged/liquidated funds','Consistent full holdings and exact shares/flows from original reports','N-CEN raw or parsed access still absent; paid docs do not equal receipt','Split demo validates only AAPL example, not portfolio-wide identifier history'],'new_effect_runs':0,'paid_spending':0}
(P/'sample-quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(P/'cn-coverage-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(P/'parsed-cn-samples.json').write_text(json.dumps(alltables,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
