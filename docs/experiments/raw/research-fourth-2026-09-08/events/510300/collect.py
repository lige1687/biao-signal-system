"""Bounded public primary dividend source collection; no trading/source cache writes.
Serves trading-spec §3 data consistency, not signal rules.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, io, json, re
import requests
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
ROWS=[
('2014-01-15','2014-01-20','2014-01-21','2014-01-27','0.48','https://static.cninfo.com.cn/finalpage/2014-01-15/63486698.PDF'),
('2015-01-14','2015-01-19','2015-01-20','2015-01-23','0.35','https://static.cninfo.com.cn/finalpage/2015-01-14/1200543748.PDF'),
('2016-01-14','2016-01-19','2016-01-20','2016-01-25','0.51','https://static.cninfo.com.cn/finalpage/2016-01-14/1201911082.PDF'),
('2017-01-17','2017-01-20','2017-01-23','2017-01-26','0.55','https://static.cninfo.com.cn/finalpage/2017-01-17/1203020541.PDF'),
('2018-01-17','2018-01-22','2018-01-23','2018-01-26','0.46','https://static.cninfo.com.cn/finalpage/2018-01-17/1204337711.PDF'),
('2019-01-10','2019-01-15','2019-01-16','2019-01-21','0.59','https://static.cninfo.com.cn/finalpage/2019-01-10/1205719943.PDF'),
('2019-12-05','2019-12-10','2019-12-11','2019-12-16','0.62','https://static.cninfo.com.cn/finalpage/2019-12-05/1207139807.PDF'),
('2021-01-11','2021-01-15','2021-01-18','2021-01-21','0.72','https://www.sse.com.cn/disclosure/fund/announcement/c/2021-01-11/510300_20210111_1.pdf'),
('2022-01-12','2022-01-18','2022-01-19','2022-01-24','0.7500','https://static.cninfo.com.cn/finalpage/2022-01-12/1212149093.PDF'),
('2023-01-09','2023-01-13','2023-01-16','2023-01-19','0.6400','https://static.cninfo.com.cn/finalpage/2023-01-09/1215552905.PDF'),
('2024-01-11','2024-01-17','2024-01-18','2024-01-23','0.6900','https://static.cninfo.com.cn/finalpage/2024-01-11/1218850806.PDF'),
('2025-06-11','2025-06-17','2025-06-18','2025-06-27','0.880','https://static.cninfo.com.cn/finalpage/2025-06-11/1223837903.PDF'),
('2026-01-12','2026-01-16','2026-01-19','2026-01-27','1.2300','https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-12/510300_20260112_VTCZ.pdf'),
]

def get(row):
    announced,record,ex,pay,amount,url=row
    stamp=datetime.now(timezone.utc).isoformat()
    r=requests.get(url, timeout=25);r.raise_for_status()
    assert r.content.startswith(b'%PDF'),(url,r.headers.get('Content-Type'))
    p=ROOT/f'{announced}.pdf';p.write_bytes(r.content)
    reader=PdfReader(io.BytesIO(r.content))
    pages=[p.extract_text() or '' for p in reader.pages]
    text='\n\n'.join(f'PAGE {i+1}\n{s}' for i,s in enumerate(pages))
    (ROOT/f'{announced}.txt').write_text(text)
    compact=re.sub(r'\s+','',text)
    checks={}
    for label,value in [('权益登记日',record),('除息日',ex),('现金红利发放日',pay)]:
        y,m,d=map(int,value.split('-'));needle=f'{y}年{m}月{d}日'
        match=re.search(re.escape(label)+r'.{0,30}'+re.escape(needle),compact)
        checks[label]=bool(match)
    checks['fund_code']='510300' in compact
    checks['amount_per_10']=bool(re.search(r'本次分红方案.{0,30}'+re.escape(amount.rstrip('0').rstrip('.') if '.' in amount else amount),compact))
    return dict(event_id=f'510300-cash-{ex}',symbol='510300',type='cash_dividend',currency='CNY',announcement_date=announced,record_date=record,ex_date=ex,pay_date=pay,cash_per_share=float(Decimal(amount)/10),cash_per_share_decimal=str(Decimal(amount)/10),announced_cash_per_10_shares=amount,source_url=url,source_file=p.name,source_sha256=hashlib.sha256(r.content).hexdigest(),retrieved_at_utc=stamp,primary_source=True,pdf_pages=len(pages),field_checks=checks,verification_status='primary_pdf_fields_verified' if all(checks.values()) else 'needs_manual_pdf_check',unknown_fields=[])

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        events=list(pool.map(get,ROWS))
    result=dict(symbol='510300',window_start='2013-07-29',window_end='2026-09-07',event_count=len(events),events=events,completeness='All 13 events in the retrieved public distribution listings matched primary issuer announcement PDFs; not an exchange-certified corporate-action feed.',limitations=['No events invented for 2020 or January 2025. Annual attribution in announcement may refer to prior year; execution follows actual dates.','Payment date is issuer-announced date for ordinary designated broker registration; actual investor settlement can differ.','This file records cash events only, no performance calculation.'])
    (ROOT/'events.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([dict(date=x['ex_date'],checks=x['field_checks'],status=x['verification_status']) for x in events],ensure_ascii=False,indent=2))
