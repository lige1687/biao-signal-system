"""Independent candidate-source, summary and annual checks from reconciled ledgers."""
from verify_accounts import *
import gzip,statistics
def run():
 params=jload(INPUT/'execution-config.json');reported=jload(ACCOUNT/'summary.json');rmap={r['account_id']:r for r in reported};annual=readcsv(ACCOUNT/'annual.csv')
 precision=json.load(gzip.open(INPUT/'source-candidates/precision-candidates.json.gz','rt'));diagnostic=jload(INPUT/'source-candidates/diagnostic-candidates.json')
 expected=[c for c in precision if c['symbol'] in SYMS and c['config_id'] in ACD]+[c for c in diagnostic if c['symbol'] in SYMS and c['config_id'] in DIAG]
 actual=jload(ACCOUNT/'candidates.json');assert expected==actual and len(expected)==1134
 checks=[];annual_checks=[];tol=D('.00001')
 for aid,r in sorted(rmap.items()):
  daily=readcsv(REVIEW/'reconciliation'/aid/'daily-independent.csv');folder=ACCOUNT/aid;trades=readcsv(folder/'trades.csv');orders=jload(folder/'orders.json');trips=jload(folder/'roundtrips.json')
  last=daily[-1];closed=[p for p in trips if p['closed']];pnl=[num(p['net_pnl']) for p in closed];ret=[num(p['net_return']) for p in closed]
  calc={'last_equity':num(last['equity']),'total_funding':num(last['total_funding']),'net_gain':num(last['equity'])-D('100000'),'cash':num(last['cash']),'assets':num(last['assets']),'receivable':num(last['receivable']),'fees':num(last['fees']),
   'trade_count':D(len(trades)),'buys':D(sum(t['side']=='buy' for t in trades)),'sells':D(sum(t['side']=='sell' for t in trades)),'open_positions':D(sum(not p['closed'] for p in trips)),
   'completed_trades':D(len(closed)),'zero_exposure_days':D(sum(num(x['assets'])==0 for x in daily))}
  diffs={k:abs(num(r[k])-v) for k,v in calc.items()};checks.append({'account_id':aid,'passed':max(diffs.values(),default=ZERO)<tol,'max_difference':str(max(diffs.values(),default=ZERO)),'fields':len(diffs)})
  groups=defaultdict(list)
  for x in daily:groups[x['date'][:4]].append(x)
  prev=D('100000')
  for year,rows in sorted(groups.items()):
   ts=[t for t in trades if t['date'].startswith(year)];end=num(rows[-1]['equity']);pnl_year=end-prev;prev=end
   ex=next(x for x in annual if x['account_id']==aid and x['year']==year)
   ds=[abs(num(ex['investment_pnl'])-pnl_year),abs(num(ex['ending_equity'])-end),abs(num(ex['trade_count'])-len(ts))]
   annual_checks.append({'account_id':aid,'year':year,'passed':max(ds)<tol,'max_difference':str(max(ds))})
 save(REVIEW/'summary-checks.json',checks);save(REVIEW/'annual-checks.json',annual_checks)
 result={'status':'passed' if all(x['passed'] for x in checks+annual_checks) else 'failed','accounts':len(checks),'annual_rows':len(annual_checks),'candidate_rows':len(actual),'precision_acd_rows':sum(c['config_id'] in ACD for c in actual),'diagnostic_rows':sum(c['config_id'] in DIAG for c in actual),'candidate_all_fields_ordered_match':expected==actual,'failures':sum(not x['passed'] for x in checks+annual_checks)}
 save(REVIEW/'summary-results.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':run()
