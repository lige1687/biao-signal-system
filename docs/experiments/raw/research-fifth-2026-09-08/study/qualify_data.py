from pathlib import Path
from datetime import date,timedelta,datetime,timezone
import csv,json,hashlib,re
from pypdf import PdfReader
P=Path(__file__).resolve().parent;ROOT=P.parent;OLD=ROOT.parent/'research-fourth-2026-09-08';THIRD=ROOT.parent/'research-third-2026-09-08'
START='2013-07-30';END='2026-06-30'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def norm(s):return re.sub(r'\s+','',s)
coverage=[];sources=[];pdf_checks=[]
for symbol,file,key,filekey,pagekey,quotekey in [
 ('159915','coverage.json','cash_dividend_coverage','source_file','pdf_page_1_based','original_quote_whitespace_normalized'),
 ('518880','cash-coverage.json','zero_cash_periods','source_file','pdf_page_1based','exact_statement'),
 ('513100','events-and-coverage.json','cash_zero_coverage','report','pdf_page_1_based','quote_whitespace_normalized')]:
 folder=ROOT/'sources'/symbol;src=folder/file;x=json.loads(src.read_text());rows=x[key];intervals=[]
 source_by_file={s['file']:s for s in json.loads((folder/'sources.json').read_text()) if 'file' in s}
 for row in rows:
  p=folder/row[filekey];expected=source_by_file[p.name]['sha256'];assert sha(p)==expected
  page=PdfReader(p).pages[row[pagekey]-1].extract_text();assert norm(row[quotekey]) in norm(page),(symbol,p.name,row[pagekey])
  intervals.append((row['start'],row['end']))
  pdf_checks.append(dict(symbol=symbol,path=str(p.resolve()),sha256=expected,page=row[pagekey],zero_distribution_quote_found=True))
 through=date.fromisoformat(START)-timedelta(days=1)
 for a,b in sorted(intervals):
  if b<START:continue
  assert date.fromisoformat(a)<=through+timedelta(days=1),('coverage gap',symbol,through,a)
  through=max(through,date.fromisoformat(b))
 assert through>=date.fromisoformat(END)
 coverage.append(dict(symbol=symbol,continuous_cash_coverage=[START,END],formal_share_change_coverage_complete=False))
 sources.append(dict(path=str(src.resolve()),sha256=sha(src)))
prices={};pricechecks=[]
events=json.loads((OLD/'events/510300/events.json').read_text())['events']
for symbol in ['sh510300','sz159915','sh518880','sh513100']:
 p=OLD/'prices'/f'{symbol}-nominal.csv';r=read(p);qpath=THIRD/'06'/f'{symbol}-qfq.csv';q={x['date']:x for x in read(qpath)}
 window=[x for x in r if START<=x['date']<=END]
 assert len(window)>3000 and any(x['date']<START for x in r)
 assert window[-1]['date']==END
 maxerr=0
 for x in window:
  o,c,h,l=[float(x[k]) for k in ['open','close','high','low']];assert 0<l<=min(o,c)<=max(o,c)<=h
  if symbol=='sh510300':expected=c-sum(e['cash_per_share'] for e in events if e['ex_date']>x['date'])
  elif symbol=='sh513100' and x['date']<'2022-01-13':expected=c/5
  else:expected=c
  err=abs(expected-float(q[x['date']]['close']));maxerr=max(maxerr,err)
  assert err<=.00051,(symbol,x['date'],err)
 prices[symbol]={x['date']:x for x in window}
 pricechecks.append(dict(symbol=symbol,rows=len(window),first=window[0]['date'],last=window[-1]['date'],known_actions_explain_qfq_max_error=maxerr))
 sources.extend([dict(path=str(p.resolve()),sha256=sha(p)),dict(path=str(qpath.resolve()),sha256=sha(qpath))])
ref=set(prices['sh510300']);missing={s:sorted(ref-set(x)) for s,x in prices.items()}
assert missing['sz159915']==['2021-02-08'] and missing['sh513100']==['2022-01-13']
assert not missing['sh518880']
for e in events:assert sha(OLD/'events/510300'/e['source_file'])==e['source_sha256']
sources.append(dict(path=str((OLD/'events/510300/events.json').resolve()),sha256=sha(OLD/'events/510300/events.json')))
result=dict(at=datetime.now(timezone.utc).isoformat(),window=[START,END],cash_coverage=coverage,pdf_checks=pdf_checks,price_checks=pricechecks,missing_vs_510300_reference=missing,price_reference_is_complete_exchange_calendar=False,full_share_event_coverage=False,qualified_for_bounded_research=True,qualification_basis='正式现金分配资料连续覆盖，已知份额变化与价格调整结构一致；仍是带日线执行假设的有限研究，不是完整市场事件服务。',sources=sources)
(P/'qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'window':result['window'],'primary_document_pages_checked':len(pdf_checks),'price_checks':pricechecks,'missing':missing},ensure_ascii=False,indent=2))
