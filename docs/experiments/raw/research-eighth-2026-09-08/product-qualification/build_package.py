"""Bounded input qualification only. No signals, positions or strategy returns."""
from pathlib import Path
from decimal import Decimal as D, ROUND_HALF_UP
from datetime import date, timedelta,datetime,timezone
from bs4 import BeautifulSoup
import json,csv,hashlib,shutil,sys
P=Path(__file__).resolve().parent; RAW=P.parents[1]; F4=RAW/'research-fourth-2026-09-08'; F5=RAW/'research-fifth-2026-09-08'; F7=RAW/'research-seventh-2026-09-08/price-basis-qualification'
START='2015-01-01'; END='2026-06-30'; SYMBOLS=['sh510300','sz159915','sh518880','sh513100']; hashes=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,d): (P/n).parent.mkdir(parents=True,exist_ok=True);(P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=str)+'\n')
def freeze(src,rel):
 dst=P/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(dst)==sha(src)
 hashes.append(dict(source_path=str(src.resolve()),file=rel,sha256=sha(src),bytes=src.stat().st_size));return rel
# Copy accepted helper without any modification; its final lock and tests remain evidence.
for name in ['price_basis.py','code-lock.json','results.json','protocol.md','protocol-amendment-1.md']:
 freeze(F7/name,'price-helper/'+name)
sys.path.insert(0,str(P/'price-helper'));from price_basis import PriceBasis,MODES,FIELDS
helper_lock=json.loads((F7/'code-lock.json').read_text());assert sha(P/'price-helper/price_basis.py')==helper_lock['sha256']['price_basis.py']
coverage_raw={}; cash_intervals={}; split_intervals={}
for s,filename,cashkey,splitkey in [('159915','coverage.json','cash_dividend_coverage','share_split_coverage'),('518880','cash-coverage.json','zero_cash_periods','verified_no_share_split_periods'),('513100','events-and-coverage.json','cash_zero_coverage','split_zero_coverage')]:
 src=F5/'sources'/s;data=json.loads((src/filename).read_text());coverage_raw[s]=data;cash_intervals[s]=data[cashkey];split_intervals[s]=data[splitkey]
 for f in src.iterdir():
  if f.suffix in ('.pdf','.txt') or f.name in (filename,'sources.json','manifest.json'):
   freeze(f,'sources/fifth/'+s+'/'+f.name)
for name in ['events.json','verification.json','verification-note.md','listings.json']:
 freeze(F4/'events/510300'/name,'sources/fourth/510300/'+name)
for a in json.loads((F4/'events/510300/events.json').read_text())['events']:
 freeze(F4/'events/510300'/a['source_file'],'sources/fourth/510300/'+a['source_file'])
for f in ['159915-resume.pdf','159915-resume.txt','sources.json','events-and-coverage.json']:
 freeze(F4/'events/other'/f,'sources/fourth/other/'+f)
freeze(F4/'prices/fetch-manifest.json','sources/nominal-fetch-manifest.json')
freeze(F4/'prices/fetch_nominal.py','sources/original-fetch-script-not-run.py')
# Raw prices preserved through June; later data kept only in a source copy, never a model input.
bars={}; rawbars={}; qfq={}; checks=[]; anomalies=[]
for symbol in SYMBOLS:
 fp=F4/'prices'/f'{symbol}-nominal.csv';freeze(fp,'sources/original-prices/'+fp.name)
 qfp=RAW/'research-third-2026-09-08/06'/f'{symbol}-qfq.csv';freeze(qfp,'sources/original-prices/'+qfp.name)
 rawbars[symbol]=list(csv.DictReader(fp.open())); bars[symbol]=[b for b in rawbars[symbol] if b['date']<=END]
 qfq[symbol]={b['date']:b for b in csv.DictReader(qfp.open())}
 dates=[b['date'] for b in bars[symbol]];assert dates==sorted(set(dates))
 for b in bars[symbol]:
  vals={f:D(b[f]) for f in FIELDS}; assert all(v.is_finite() and v>0 for v in vals.values());assert vals['low']<=min(vals['open'],vals['close'])<=max(vals['open'],vals['close'])<=vals['high'];assert D(b['volume']).is_finite() and D(b['volume'])>0
  if len(set(vals.values()))==1 and START<=b['date']:
   anomalies.append(dict(symbol=symbol,date=b['date'],type='one_price_day',available_after='session close',use_for_open_decision=False,OHLC={f:b[f] for f in FIELDS}))
 rows=[dict(symbol=symbol,session_date=b['date'],**{k:v for k,v in b.items() if k!='date'},currency='CNY',price_unit='CNY per contemporaneous fund unit',volume_unit='unverified vendor raw unit',use_role='research_window' if b['date']>=START else 'warmup_only') for b in bars[symbol]]
 with (P/f'{symbol}-nominal.csv').open('w') as file:
  w=csv.DictWriter(file,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 checks.append(dict(symbol=symbol,warmup_rows=sum(b['date']<START for b in bars[symbol]),window_rows=sum(b['date']>=START for b in bars[symbol]),first=dates[0],window_first=next(b['date'] for b in bars[symbol] if b['date']>=START),last=dates[-1],currency='CNY',price_unit='CNY per contemporaneous fund unit',source_sha256=sha(fp),volume_unit=None,volume_allowed_usage='same-symbol ratios only; no absolute liquidity sizing or amount conversion'))
# Keep helper-native date schema also for direct reuse, clipped at END.
(P/'bars-helper-native').mkdir(exist_ok=True)
for s,rows in bars.items():
 with (P/'bars-helper-native'/f'{s}-nominal.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
normalized=json.loads((F7/'inputs/actions.json').read_text());actions=[]
for a in normalized:
 if a['effective_date']>END:continue
 a=dict(a);a['economic_event_key']='|'.join([a['symbol'],a['type'],a['effective_date']]);a['within_research_window']=a['effective_date']>=START;a['amount_basis']='per unit outstanding immediately before event'
 if a['symbol']=='sh510300':
  a['source_file']='sources/fourth/510300/'+Path(a['source_file']).name
 else:a['source_file']='sources/fifth/513100/513100-official-split.pdf';a['effective_event_confirmed_by']='sources/fifth/513100/513100-2022.pdf'
 assert sha(P/a['source_file'])==a['source_sha256'];actions.append(a)
assert len({a['economic_event_key'] for a in actions})==len(actions)
save('actions.json',actions)
engine=PriceBasis(bars,actions)
# Supportive vendor crosscheck: existing source qfq uses cash additive, NOT selected proportional helper.
price_cross=[]
for s,rows in bars.items():
 maximum=D(0);count=0
 for row in rows:
  if row['date'] not in qfq[s]:continue
  for field in FIELDS:
   expected=D(row[field])
   for a in sorted(actions,key=lambda x:x['effective_date']):
    if a['symbol']==s and row['date']<a['effective_date']:
     expected=expected-D(a['cash']) if a['type']=='cash_dividend' else expected/D(a['ratio'])
   err=abs(expected-D(qfq[s][row['date']][field]));maximum=max(maximum,err);count+=1
 assert maximum<=D('.0005'),(s,maximum)
 price_cross.append(dict(symbol=s,OHLC_cells=count,max_error=maximum,tolerance='.0005',status='known events explain vendor adjustment within published quote precision',independent_action_completeness_proof=False))
# Coverage gaps are literal unknown dates, never zero events.
def missing_intervals(intervals):
 gaps=[];d=date.fromisoformat(START);end=date.fromisoformat(END);begin=None
 while d<=end:
  covered=any(a['start']<=str(d)<=a['end'] for a in intervals)
  if not covered and begin is None:begin=str(d)
  if covered and begin is not None:gaps.append([begin,str(d-timedelta(days=1))]);begin=None
  d+=timedelta(days=1)
 if begin:gaps.append([begin,END])
 return gaps
coverage=[]
for symbol in SYMBOLS:
 s=symbol[2:]
 if s=='510300':
  coverage.append(dict(symbol=symbol,cash_status='12 in-window primary-announcement events; two public lists agree; not a continuous official no-event certification',cash_events_in_window=12,cash_absence_proof_for_unlisted_dates='list concordance and vendor adjustment crosscheck only',split_formal_coverage_complete=False,split_unknown_intervals=[[START,END]],known_split_events=[]))
 else:
  cashgap=missing_intervals(cash_intervals[s]);assert not cashgap
  parts=list(split_intervals[s])
  if s=='513100':parts.append(dict(start='2022-01-01',end='2022-12-31',status='annual report shows actual split, not zero'))
  coverage.append(dict(symbol=symbol,cash_status='continuous explicit-zero formal period reports',cash_events_in_window=0,cash_uncovered_intervals=cashgap,split_formal_coverage_complete=False,split_unknown_intervals=missing_intervals(parts),known_split_events=['513100-split-2022-01-13'] if s=='513100' else [],source_coverage_file='sources/fifth/'+s+'/'+({'159915':'coverage.json','518880':'cash-coverage.json','513100':'events-and-coverage.json'}[s])))
save('action-coverage.json',dict(window=[START,END],products=coverage,conditional_assumption='only documented known share actions are applied; vendor agreement supports but does not prove absence of undocumented events',formal_full_company_action_coverage=False))
# Known dated exceptions. First split resumption price limit reference unresolved => omit fills that day.
restrictions=[
 dict(symbol='sz159915',date='2021-02-08',reason='official suspension',open_buy_allowed=False,open_sell_allowed=False,close_mark_allowed=False,source='sources/fourth/other/159915-resume.pdf',pdf_page=2,known_notice_precision='final confirmation dated 2021-02-09; actual suspension is directly observable on 2021-02-08'),
 dict(symbol='sz159915',date='2021-02-09',reason='resumes at 10:30 Asia/Shanghai, no 09:30 fill',open_buy_allowed=False,open_sell_allowed=False,close_mark_allowed=True,source='sources/fourth/other/159915-resume.pdf',pdf_page=2),
 dict(symbol='sh513100',date='2022-01-13',reason='split day suspension; apply shares x5 and prior mark /5, no synthetic quote',open_buy_allowed=False,open_sell_allowed=False,close_mark_allowed=False,source='sources/fifth/513100/513100-official-split.pdf',pdf_page=2),
 dict(symbol='sh513100',date='2022-01-14',reason='first resumed quote exists; exchange price-limit reference not verified, conservatively omit all fills',open_buy_allowed=False,open_sell_allowed=False,close_mark_allowed=True,source='sources/fifth/513100/513100-2022.pdf',pdf_page=45,status='research restriction due to missing reference, NOT claimed exchange suspension')]
save('dated-restrictions.json',restrictions)
# Calendar is only an observation union; all missing sessions retained explicitly.
union=sorted({b['date'] for rows in bars.values() for b in rows if b['date']>=START});indexes={s:{b['date']:b for b in rows} for s,rows in bars.items()}
sessions=[]
for d in union:
 for s in SYMBOLS:
  found=d in indexes[s]; restriction=next((r for r in restrictions if r['symbol']==s and r['date']==d),None)
  sessions.append(dict(symbol=s,session_date=d,quote_present=found,open_allowed_by_static_exception=(found and restriction is None),restriction_reason=restriction['reason'] if restriction else ('' if found else 'missing quote; do not create fills'),close_mark_present=found,calendar_status='observed union; not certified exchange calendar'))
with (P/'observed-sessions.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(sessions[0]));w.writeheader();w.writerows(sessions)
regimes=[]
for s in SYMBOLS:
 for begin,end,fraction in ([('2015-01-01','2020-08-23','.10'),('2020-08-24',END,'.20')] if s=='sz159915' else [(START,END,'.10')]):
  regimes.append(dict(symbol=s,start=begin,end=end,price_limit_fraction=fraction,rounding='ROUND_HALF_UP to CNY 0.001',status='ordinary-session reference only; special exchange reference not universally covered',source='sources/szse-20200824-20pct.pdf' if fraction=='.20' else ('sources/szse-2006-rules.html' if s=='sz159915' else 'sources/sse-2013-limit.html')))
save('price-limit-regimes.json',regimes)
# Pure price diagnostic. Open constraints use only the observed open and prior/action-adjusted reference.
open_checks=[];outside=[]
for s,rows in bars.items():
 for i,b in enumerate(rows):
  if b['date']<START:continue
  assert i>0
  prev=rows[i-1];ref=engine.mapping(s,prev['date'],b['date'],'cash_proportional_v1','open').forward(prev['close'])
  lim=next(D(x['price_limit_fraction']) for x in regimes if x['symbol']==s and x['start']<=b['date']<=x['end'])
  lower=(ref*(1-lim)).quantize(D('.001'),rounding=ROUND_HALF_UP);upper=(ref*(1+lim)).quantize(D('.001'),rounding=ROUND_HALF_UP)
  unknown=s=='sh513100' and b['date']=='2022-01-14'
  buy=D(b['open'])<upper;sell=D(b['open'])>lower
  if unknown:buy=sell=False
  restriction=next((r for r in restrictions if r['symbol']==s and r['date']==b['date']),None)
  if restriction:buy=sell=False
  open_checks.append(dict(symbol=s,session_date=b['date'],prior_quote_date=prev['date'],reference_close=ref,reference_status='unverified_exchange_reference_skip_fills' if unknown else 'ordinary_session_research_reference',open=b['open'],limit_down=lower,limit_up=upper,open_buy_permitted_by_price_and_exception=buy,open_sell_permitted_by_price_and_exception=sell,known_at='current open observation; never current high low close'))
  if not unknown and (D(b['low'])<lower-D('.001') or D(b['high'])>upper+D('.001')):
   outside.append(dict(symbol=s,date=b['date'],low=b['low'],high=b['high'],lower=lower,upper=upper,available_after='close',status='reference or data issue; requires review before using any affected fill'))
with (P/'open-price-checks.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(open_checks[0]));w.writeheader();w.writerows(open_checks)
# Volume units: bounded independent exchange-month comparison, not enough to declare daily field units.
stats=P/'sources/szse-2025-march-stats.html';soup=BeautifulSoup(stats.read_bytes().decode('gb18030'),'html.parser');(P/'sources/szse-2025-march-stats.html.txt').write_text(soup.get_text('\n',strip=True))
row=next(tr for tr in soup.find_all('tr') if tr.find('td') and tr.find('td').get_text(strip=True)=='159915');cells=[td.get_text(strip=True) for td in row.find_all('td')]
nonblank=[c for c in cells if c]; assert nonblank[0]=='159915' and len(nonblank)==17
vol=D(nonblank[14]); assert vol>0; rawsum=sum(D(b['volume']) for b in bars['sz159915'] if b['date'].startswith('2025-03'))
volume=dict(symbol='sz159915',period='2025-03',exchange_volume=vol,vendor_sum=rawsum,exchange_over_vendor=vol/rawsum,vendor_x100=rawsum*100,difference=vol-rawsum*100,relative_difference=(vol-rawsum*100)/vol,exchange_row=cells,source='sources/szse-2025-march-stats.html',conclusion='roughly 100-fold units supported; exact mismatch and trade-scope difference unresolved; keep raw volume unit null for all products; same-series ratios only')
missing={s:[d for d in union if d not in indexes[s]] for s in SYMBOLS}
save('price-data-checks.json',dict(window=[START,END],products=checks,vendor_adjustment_crosscheck=price_cross,missing_vs_observed_union=missing,one_price_diagnostics=anomalies,OHLC_outside_ordinary_reference=outside,volume_crosscheck=volume,formal_exchange_calendar_complete=False,formal_intraday_suspension_coverage_complete=False))
save('source-lock.json',dict(created_at_utc=datetime.now(timezone.utc).isoformat(),reused_files=hashes,new_rule_source_manifest='sources/new-rule-sources.json',selected_price_helper='cash_proportional_v1',formal_strategy_changed=False))
print(json.dumps(dict(products=checks,missing=missing,outside=outside,one_price=anomalies,volume=volume,normalized_actions=len(actions),copied_sources=len(hashes)),ensure_ascii=False,default=str,indent=2))
