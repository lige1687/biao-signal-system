from pathlib import Path
from datetime import date
import csv,json,math,statistics
HERE=Path(__file__).resolve().parent; NEW=HERE/'attempt-01'; OLD=HERE.parent.parent/'research-broad-etf-technical-2026-09-08/execution/account-results'
def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def one(aid,folder,method,sym,fee):
 daily=list(csv.DictReader((folder/'daily.csv').open()));trades=list(csv.DictReader((folder/'trades.csv').open()));ps=read(folder/'roundtrips.json');events=read(folder/'events.json')
 entries={p['entry_date']:p for p in ps};accrued={p['position_id']:0. for p in ps};divs={}
 for e in events:
  if e['kind']=='dividend_receivable' and e.get('position_id'):divs.setdefault(e['date'],[]).append(e)
 base=nav=peak=1.;draw=0.;active=None;holding=0;stats=[];annual=[];ys={};ye={};last=1.
 for row in daily:
  d=row['date'];y=d[:4];ys.setdefault(y,last)
  for e in divs.get(d,[]):accrued[e['position_id']]+=float(e['amount'])
  if d in entries:active=entries[d];active['_peak']=1.;active['_draw']=0.;active['_days']=0
  if active:
   p=active;capital=p['entry_notional']+p['buy_fee'];val=(p['exit_notional']-p['sell_fee'] if p['closed'] and d==p['exit_date'] else float(row['assets']))+accrued[p['position_id']];factor=val/capital;nav=base*factor;p['_peak']=max(p['_peak'],factor);p['_draw']=max(p['_draw'],1-factor/p['_peak'])
   if not(p['closed'] and d==p['exit_date']):holding+=1;p['_days']+=1
   if p['closed'] and d==p['exit_date']:base=nav;active=None
  else:nav=base
  peak=max(peak,nav);draw=max(draw,1-nav/peak);ye[y]=nav;last=nav
 span=(date.fromisoformat(daily[-1]['date'])-date.fromisoformat(daily[0]['date'])).days;closed=[p for p in ps if p['closed']]
 for p in ps:stats.append({'account_id':aid,'position_id':p['position_id'],'candidate_id':p['candidate_id'],'entry_date':p['entry_date'],'exit_date':p['exit_date'],'exit_reason':next((t['reason'] for t in trades if t['side']=='sell' and t['position_id']==p['position_id']),None),'closed':p['closed'],'net_return':p['net_return'],'holding_calendar_days':p['_days'],'maximum_daily_decline_within_trade':p['_draw'],'net_pnl':p['net_pnl']})
 for y in ys:annual.append({'account_id':aid,'year':y,'unit_return':ye[y]/ys[y]-1})
 rs=[p['net_return'] for p in closed];loss_streak=cur=0
 for x in rs:cur=cur+1 if x<0 else 0;loss_streak=max(loss_streak,cur)
 profile={'account_id':aid,'symbol':sym,'method':method,'fee_per_side':fee,'unit_final':nav,'calendar_annualized_unit_return':nav**(365.25/span)-1,'maximum_unit_curve_decline':draw,'completed_trades':len(closed),'open_trades':len(ps)-len(closed),'trade_count':len(ps),'closed_mean':statistics.mean(rs) if rs else None,'closed_median':statistics.median(rs) if rs else None,'closed_win_fraction':sum(x>0 for x in rs)/len(rs) if rs else None,'longest_losing_streak':loss_streak,'holding_calendar_days':holding,'worst_single_trade_daily_decline':max((p['_draw'] for p in ps),default=None)}
 return profile,stats,annual
def main():
 profiles=[];trades=[];annual=[];accounts=[];account_annual=[];periods=[]
 for sym in ('sh510300','sz159915'):
  for fee,tag in ((.001,'10'),(.002,'20')):
   for method,folder,aid in [('R1',OLD/f'{sym}-R1-fee{tag}bp',f'{sym}-R1-fee{tag}bp'),('R1-structure-only',NEW/f'{sym}-R1-structure-only-fee{tag}bp',f'{sym}-R1-structure-only-fee{tag}bp')]:
    p,t,a=one(aid,folder,method,sym,fee);profiles.append(p);trades+=t;annual+=a
    rows=list(csv.DictReader((folder/'daily.csv').open()));start=100000.;groups={}
    for row in rows:groups.setdefault(row['date'][:4],[]).append(row)
    prior=start
    for y,g in groups.items():end=float(g[-1]['equity']);account_annual.append({'account_id':aid,'year':y,'return':end/prior-1});prior=end
    for label,lo,hi in [('2015-2019','2015-01-01','2019-12-31'),('2020-2026H1','2020-01-01','2026-06-30')]:
     g=[r for r in rows if lo<=r['date']<=hi];before=start if lo.startswith('2015') else float([r for r in rows if r['date']<lo][-1]['equity']);periods.append({'account_id':aid,'period':label,'return':float(g[-1]['equity'])/before-1})
    summary=next((x for x in read(NEW/'summary.json') if x['account_id']==aid),None) if method!='R1' else next(x for x in read(OLD/'summary.json') if x['account_id']==aid)
    final=rows[-1];accounts.append({'account_id':aid,'symbol':sym,'method':method,'fee_per_side':fee,'final_equity':float(final['equity']),'cash':float(final['cash']),'receivable':float(final['receivable']),'assets':float(final['assets']),'average_invested_fraction':sum(float(r['assets'])/float(r['equity']) for r in rows)/len(rows),'max_drawdown':summary['max_drawdown'],'buys':summary['buys'],'sells':summary['sells'],'fees':summary['fees']})
 save(HERE/'invested-results.json',profiles);save(HERE/'invested-trades.json',trades);save(HERE/'invested-annual.json',annual)
 save(HERE/'account-comparison.json',accounts);save(HERE/'account-annual.json',account_annual);save(HERE/'fixed-periods.json',periods)
if __name__=='__main__':main()
