from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd, re, json
ROOT=Path(__file__).resolve().parent
sources={
 '515050':('official_pdf_text',ROOT/'sources/official-515050-2025-annual.txt'),
 '515130':('official_pdf_text',ROOT/'sources/official-515130-2025-annual.txt'),
 '512400':('official_pdf_text',ROOT/'sources/official-512400-2025-annual.txt'),
 '159652':('official_pdf_text',ROOT/'sources/official-159652-2025-annual.txt'),
 '510300':('third_party_full_report_mirror',ROOT/'sources/report-mirror-510300-2025-annual.html'),
 '515880':('official_pdf_text',ROOT/'sources/official-515880-2025-annual.txt'),
}
out={}
for code,(kind,path) in sources.items():
 raw=path.read_text(errors='replace')
 if path.suffix=='.html': raw=BeautifulSoup(raw,'html.parser').get_text('\n')
 last_detail=max(raw.rfind('所有股票投资明细'),raw.rfind('股票投资明细'))
 idx831=raw.rfind('8.3.1',0,last_detail+1)
 start=idx831 if idx831>=0 else last_detail
 ends=[x for x in [raw.find('8.4报告期内',start),raw.find('8.4 报告期内',start)] if x>=0]
 end=min(ends) if ends else len(raw)
 section=re.sub(r'\s+',' ',raw[start:end]).replace(',','')
 df=pd.read_csv(ROOT/f'holdings-{code}.csv',dtype={'stock_code':str})
 # Locate each reported holding code in report order, then restrict numeric comparison
 # to that code's own block ending immediately before the next holding code.
 positions=[]; cursor=0; missing_codes=[]
 for c in df.stock_code:
  p=section.find(c,cursor)
  if p<0 and c.startswith('0'): p=section.find(str(int(c)),cursor)
  if p<0: missing_codes.append(c); positions.append(None)
  else: positions.append(p); cursor=p+len(c)
 mismatches=[]
 for i,row in df.iterrows():
  p=positions[i]
  if p is None: continue
  nextp=next((q for q in positions[i+1:] if q is not None),len(section))
  block=section[p:nextp]
  if '8.3.2' in block: block=block.split('8.3.2',1)[0]
  decimals=re.findall(r'(?<!\d)(\d+\.\d+)(?!\d)',block)
  observed=decimals[-1] if decimals else None
  expected=f"{float(row.nav_weight_pct):.2f}"
  if observed != expected:
   mismatches.append({'stock_code':row.stock_code,'expected_weight_pct':expected,'observed_last_decimal_in_own_block':observed,'block_tail':block[-100:]})
 # Codes parsed from the bounded table section (may include page/report dates, so the ordered
 # holding-code pass above is authoritative for completeness).
 out[code]={'source_kind':kind,'source_file':str(path.relative_to(ROOT)),'csv_rows':len(df),'ordered_codes_found':len(df)-len(missing_codes),'missing_codes':missing_codes,'exact_own_block_weight_matches':len(df)-len(missing_codes)-len(mismatches),'weight_mismatches':mismatches,'method':'codes located sequentially in bounded 8.3-to-8.4 table; weight is last decimal token before next holding code'}
(ROOT/'report-row-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{'codes':v['ordered_codes_found'],'rows':v['csv_rows'],'weights':v['exact_own_block_weight_matches'],'mismatch':len(v['weight_mismatches'])} for k,v in out.items()},ensure_ascii=False,indent=2))
