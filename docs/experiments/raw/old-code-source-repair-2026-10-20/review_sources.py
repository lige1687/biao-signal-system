"""Compare acquired source versions only; does not calculate strategy outcomes."""
from pathlib import Path
from decimal import Decimal as D
from collections import Counter
import json,hashlib,datetime
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def table(p):
 j=load(p);rows=[dict(zip(j['fields'],r,strict=True)) for r in j.get('rows',j.get('data',[]))];return j,rows

def main():
 receipt=load(HERE/'execution-receipt.json')
 assert receipt['status']=='complete10' and receipt['source_operations_used_this_run']==10
 for b in receipt['bindings_before']+receipt['outputs']+[receipt['stdout'],receipt['stderr']]:assert sha(b['path'])==b['sha256'],b['path']
 out=Path(receipt['output_directory']);oldreceipt=load(HERE.parent/'lowfreq-data-integrity-enforcement-2026-10-20/probe-receipt.json')
 old={r['key']:r for r in oldreceipt['requests'] if r.get('kind')=='data_request'}
 for r in old.values():assert sha(r['path'])==r['sha256']
 sources={};rows={}
 for label,path in [('old_code_adjusted',out/'request-01.json'),('old_code_nominal',out/'request-02.json'),('current_code_nominal',Path(old['001914-nominal']['path'])),('current_code_adjusted',Path(old['001914-adjusted-repeat']['path']))]:
  j,t=table(path); assert len({r['date'] for r in t})==len(t);rows[label]={r['date']:r for r in t}
  sources[label]={'path':str(path),'sha256':sha(path),'n':len(t),'first':min(rows[label]),'last':max(rows[label]),'codes':dict(Counter(r['code'] for r in t)),'adjustflags':dict(Counter(r['adjustflag'] for r in t)),'nontrading_rows':sum(r['tradestatus']!='1' for r in t)}
 dates=sorted(set(rows['old_code_nominal'])&set(rows['current_code_nominal']))
 fields=['open','high','low','close','preclose','volume','amount','tradestatus','pctChg','isST']
 def same(a,b):
  if a=='' or b=='': return a==b
  return D(a)==D(b)
 mismatch={f:sum(not same(rows['old_code_nominal'][dt][f],rows['current_code_nominal'][dt][f]) for dt in dates) for f in fields}
 overlap=sorted(set(rows['old_code_adjusted'])&set(rows['current_code_adjusted']))
 good=[dt for dt in overlap if rows['current_code_adjusted'][dt]['adjustflag']=='2']
 bad=[dt for dt in overlap if rows['current_code_adjusted'][dt]['adjustflag']!='2']
 ratios=[D(rows['current_code_adjusted'][dt]['close'])/D(rows['old_code_adjusted'][dt]['close']) for dt in good]
 factor=ratios[0];offsets={f:max(abs(D(rows['current_code_adjusted'][dt][f])-D(rows['old_code_adjusted'][dt][f])*factor) for dt in good) for f in ['open','high','low','close','preclose']}
 _,action=table(out/'request-03.json');_,currentaction=table(old['001914-adjust-factors']['path'])
 div=[]
 for n in range(4,11):
  j,rr=table(out/f'request-{n:02d}.json')
  for r in rr:div.append({'request_year':j['kwargs']['year'],**r})
 raw=rows['old_code_nominal'];adj=rows['old_code_adjusted'];alldates=sorted(raw);events=[]
 for a in action:
  dt=a['dividOperateDate'];prior=max(t for t in alldates if t<dt)
  r_before=D(adj[prior]['close'])/D(raw[prior]['close']);r_after=D(adj[dt]['close'])/D(raw[dt]['close'])
  ds=[d for d in div if d['dividOperateDate']==dt]
  row={'date':dt,'prior_date':prior,'factor_from_prices_before':str(r_before),'factor_from_prices_after':str(r_after),'source_fore_factor':a['foreAdjustFactor'],'dividend_matches':len(ds)}
  if len(ds)==1:
   cash=D(ds[0]['dividCashPsBeforeTax']);prev=D(raw[prior]['close']);expected=prev/(prev-cash)
   row.update(cash_per_share=str(cash),stock_dividend=ds[0]['dividStocksPs'],reserve_to_stock=ds[0]['dividReserveToStockPs'],expected_factor_jump=str(expected),observed_factor_jump=str(r_after/r_before),relative_jump_error=str((r_after/r_before)/expected-1))
  events.append(row)
 beforefirst=[dt for dt in alldates if dt<min(a['dividOperateDate'] for a in action)]
 factor_errors=[]
 for dt in alldates:
  prior=[a for a in action if a['dividOperateDate']<=dt]
  if prior:factor_errors.append(abs(D(adj[dt]['close'])/D(raw[dt]['close'])-D(max(prior,key=lambda a:a['dividOperateDate'])['foreAdjustFactor'])))
 result={'at':datetime.datetime.now().astimezone().isoformat(),'kind':'source_only_no_strategy_outcomes','sources':sources,'common_nominal_dates':len(dates),'nominal_mismatches_by_field':mismatch,'new_nominal_dates_not_in_saved_current_code':len(set(raw)-set(rows['current_code_nominal'])),'good_adjusted_overlap':{'n':len(good),'first':min(good),'last':max(good),'ratio_min':str(min(ratios)),'ratio_max':str(max(ratios)),'constant_ratio':str(factor),'ohlc_preclose_max_abs_residual':{k:str(v) for k,v in offsets.items()}},'bad_current_code_overlap':{'n':len(bad),'first':min(bad),'last':max(bad)},'factor_events':events,'max_abs_price_ratio_vs_returned_fore_factor':str(max(factor_errors)),'pre_first_factor_period':{'n':len(beforefirst),'first':min(beforefirst),'last':max(beforefirst),'observed_ratio_unique':sorted({str(D(adj[dt]['close'])/D(raw[dt]['close'])) for dt in beforefirst})},'action_date_sets_match_dividend':{a['dividOperateDate'] for a in action}=={d['dividOperateDate'] for d in div},'current_code_overlap_factors':[a for a in currentaction if a['dividOperateDate']<=max(alldates)],'limits':['One vendor internal consistency only; not exchange-level independent proof or a cash account model.','No old source/panel/outcome replaced; old code retired2019-12-16 and source flag break2019-06-06 are different dates.','Returned dividend year convention may be implementation year despite yearType=report; actual date governs, not request year.','Any derived normalized series remains a new source version requiring separate input requalification and pre-registered correction before outcomes.','No600-stock value price/share panel supplied by this one issuer.']}
 target=HERE/'source-review.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['common_nominal_dates','nominal_mismatches_by_field','good_adjusted_overlap','bad_current_code_overlap','max_abs_price_ratio_vs_returned_fore_factor','action_date_sets_match_dividend']},ensure_ascii=False,indent=2));print('events',len(events),'max_relative_jump_error',max(abs(D(x['relative_jump_error'])) for x in events))
if __name__=='__main__':main()
