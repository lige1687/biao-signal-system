from pathlib import Path
from datetime import date,timedelta,datetime,timezone
from pypdf import PdfReader
import re,json,hashlib
P=Path(__file__).resolve().parent
sources=json.loads((P/'sources-new.json').read_text())+json.loads((P/'sources-reused.json').read_text())
cash=[];splits=[]
intervals={'2013':('2011-09-20','2013-12-31'),'2016':('2014-01-01','2016-12-31'),'2018':('2016-01-01','2018-12-31'),'2020':('2018-01-01','2020-12-31'),'2022':('2020-01-01','2022-12-31'),'2025':('2023-01-01','2025-12-31'),'2026h':('2026-01-01','2026-06-30')}
for meta in sources:
    y=meta['year'];f=P/meta['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256']
    pages=[p.extract_text() or '' for p in PdfReader(f).pages]
    assert '联接' not in pages[0] and '易方达创业板' in pages[0]
    assert any(re.search(r'基金主代码\s+159915',p) for p in pages[:7])
    for i,s in enumerate(pages):
        compact=re.sub(r'\s+','',s)
        if y=='2013':
            quote='本基金自基金合同生效日（2011年9月20日）至本报告期末未发生利润分配。'
            found=quote in compact
        elif y=='2026h':
            quote='本基金本报告期内未发生利润分配。'
            found='6.4.11利润分配情况'+quote in compact
        else:
            quote='本基金过去三年未发生利润分配。'
            found='3.3过去三年基金的利润分配情况'+quote in compact
        if found:
            cash.append(dict(symbol='159915',type='cash_dividend_coverage',start=intervals[y][0],end=intervals[y][1],cash_dividend_count=0,source_file=f.name,source_url=meta['url'],source_sha256=meta['sha256'],pdf_page_1_based=i+1,printed_page=str(i) if y=='2013' else str(i+1),section='6.4.11' if y=='2026h' else '3.3',original_quote_whitespace_normalized=quote,interpretation='Explicit reporting-period statement; annual past-three-year clause includes report year and preceding two years.'))
        needle='本报告期基金拆分变动份额'
        if needle in s:
            j=s.index(needle);excerpt=s[max(0,j-260):j+230].strip()
            assert re.search(re.escape(needle)+r'\s*-',s)
            splits.append(dict(symbol='159915',type='share_split_period_coverage',start=y[:4]+'-01-01',end=y[:4]+('-06-30' if y=='2026h' else '-12-31'),reported_split_change='-',source_file=f.name,source_url=meta['url'],source_sha256=meta['sha256'],pdf_page_1_based=i+1,printed_page=str(i) if y=='2013' else str(i+1),section='10' if y!='2026h' else '9',original_excerpt=excerpt,interpretation='Only this report period has zero reported share-split change; subscription/redemption share changes are separate and do not change an existing investor holding.'))
assert len(cash)==len(splits)==7
def missing(records,start='2013-07-29',end='2026-06-30'):
    d=date.fromisoformat(start);finish=date.fromisoformat(end);gaps=[];cur=None
    while d<=finish:
        found=any(x['start']<=d.isoformat()<=x['end'] for x in records)
        if not found and cur is None:cur=d
        if found and cur is not None:gaps.append([cur.isoformat(),(d-timedelta(days=1)).isoformat()]);cur=None
        d+=timedelta(days=1)
    if cur is not None:gaps.append([cur.isoformat(),end])
    return gaps
out=dict(symbol='159915',requested_window=['2013-07-29','2026-06-30'],new_pdf_count=5,reused_pdf_count=2,actual_cash_events=[],cash_dividend_coverage=cash,cash_uncovered_intervals=missing(cash),share_split_coverage=splits,share_split_uncovered_intervals=missing(splits),notes=['2019 annual report was not retrieved; overlapping 2018 and 2020 annual past-three-year statements close its cash-dividend coverage gap.','Zero cash distributions do not prove zero share split over the entire requested interval.','After 2026-06-30 is outside requested coverage; no claim for July to September 2026.'],generated_at_utc=datetime.now(timezone.utc).isoformat())
assert not out['cash_uncovered_intervals']
(P/'coverage.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(P/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'cash_intervals':[(r['source_file'],r['start'],r['end'],r['pdf_page_1_based']) for r in cash],'cash_gaps':out['cash_uncovered_intervals'],'split_gaps':out['share_split_uncovered_intervals']},ensure_ascii=False,indent=2))
