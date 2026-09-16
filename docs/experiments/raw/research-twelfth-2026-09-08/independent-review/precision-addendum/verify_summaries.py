"""Check reported top-line summaries and year/product contributions from Decimal ledger."""
from verify_accounts import *

def run_summaries():
 snap=BASE/'accepted';summary={r['config_id']:r for r in jload(snap/'account-results/summary.json')}
 products=readcsv(snap/'account-results/product-contributions.csv');annual=readcsv(snap/'account-results/annual-contributions.csv')
 params=jload(snap/'product-qualification/execution-parameters.json');checks=[];maxerr=ZERO
 def check(cfg,key,actual,expected):
  nonlocal maxerr
  diff=abs(num(actual)-expected);maxerr=max(maxerr,diff);assert diff<TOL,(cfg,key,actual,expected)
  checks.append(dict(config=cfg,field=key,reported=actual,independent=expected,difference=diff))
 for cfg in CONFIGS:
  rows=readcsv(BASE/'reconciliation'/cfg/'daily-independent.csv');last=rows[-1];reported=summary[cfg]
  trades=readcsv(snap/'account-results'/cfg/'trades.csv');trips=jload(snap/'account-results'/cfg/'roundtrips.json')
  expected={key:num(last[source]) for key,source in {'last_equity':'equity','total_funding':'total_funding','cash':'cash','assets':'assets','receivable':'receivable','fees':'fees'}.items()}
  expected.update(net_gain=num(last['equity'])-num(last['total_funding']),max_drawdown=-min(num(r['drawdown']) for r in rows),mean_exposure=sum((num(r['assets'])/num(r['equity']) if num(r['equity']) else ZERO for r in rows),ZERO)/sum(num(r['equity'])>0 for r in rows),trade_count=num(len(trades)),buys=num(sum(t['side']=='buy' for t in trades)),sells=num(sum(t['side']=='sell' for t in trades)),completed_trades=num(sum(t['closed'] for t in trips)),open_positions=num(sum(not t['closed'] for t in trips)))
  for key,value in expected.items():check(cfg,key,reported[key],value)
  for s in params['symbols']:
   product=next(r for r in products if r['config_id']==cfg and r['symbol']==s)
   for key,value in dict(ending_equity=num(last['equity_'+s]),funding=num(last['funding_'+s]),net_gain=num(last['equity_'+s])-num(last['funding_'+s]),fees=num(last['fees_'+s]),open_shares=num(last['units_'+s])).items():check(cfg,'product_'+s+'_'+key,product[key],value)
  gains=defaultdict(lambda:ZERO);lastyear={};previous=ZERO
  for row in rows:
   y=row['date'][:4];wealth=num(row['equity']);gains[y]+=wealth-previous-num(row['deposit']);previous=wealth;lastyear[y]=wealth
  for y,gain in gains.items():
   ar=next(r for r in annual if r['config_id']==cfg and r['year']==y)
   check(cfg,'year_'+y+'_pnl',ar['investment_pnl'],gain);check(cfg,'year_'+y+'_wealth',ar['ending_equity'],lastyear[y]);check(cfg,'year_'+y+'_trades',ar['trade_count'],num(sum(t['date'].startswith(y) for t in trades)))
 writecsv(BASE/'summary-checks.csv',checks);save(BASE/'summary-results.json',dict(status='passed',numeric_fields=len(checks),maximum_numeric_difference=maxerr,scope='Top-line wealth, net contributions, cash/assets/receivables, fees, drawdown, mean exposure, trade/position counts, all 48 product and 144 yearly contributions; other descriptive trade summary fields not independently rederived.'))
 print('Summary checks passed:',len(checks),'fields, maximum difference',maxerr)

if __name__=='__main__':run_summaries()
