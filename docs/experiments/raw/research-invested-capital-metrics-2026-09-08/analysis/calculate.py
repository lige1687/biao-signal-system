from pathlib import Path
from datetime import date,datetime,timezone
import csv,json,math,hashlib,statistics
B=Path(__file__).resolve().parents[1];R=B.parents[3];H=Path(__file__).resolve().parent
SOURCES=[('R1',R/'docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/account-results'),('R1-risk1',R/'docs/experiments/raw/research-broad-etf-risk-sizing-2026-09-08/execution/account-results')]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 assert not (H/'results.json').exists(),'preserve prior calculation'
 paths=[B/'protocol.md',Path(__file__).resolve()]
 for m,root in SOURCES:
  for s in ['sh510300','sz159915']:
   for tag in ['10','20']:paths.extend(root/f'{s}-{m}-fee{tag}bp'/n for n in ['daily.csv','trades.csv','roundtrips.json','events.json'])
 lock={str(p):sha(p) for p in paths};save(H/'input-code-lock.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'files':lock})
 output=[];annual=[];trade_stats=[];curves={}
 for m,root in SOURCES:
  for s in ['sh510300','sz159915']:
   for tag in ['10','20']:
    aid=f'{s}-{m}-fee{tag}bp';folder=root/aid
    with (folder/'daily.csv').open() as f:daily=list(csv.DictReader(f))
    with (folder/'trades.csv').open() as f:trades=list(csv.DictReader(f))
    ps=read(folder/'roundtrips.json');events=read(folder/'events.json');buys={t['position_id']:t for t in trades if t['side']=='buy'}
    entries={p['entry_date']:p for p in ps};assert len(entries)==len(ps)
    accrued={p['position_id']:0. for p in ps};divs={}
    for e in events:
     if e['kind']=='dividend_receivable' and e.get('position_id'):divs.setdefault(e['date'],[]).append(e)
    curve=[];base=1.;nav=1.;peak=1.;draw=0.;active=None;holding_days=0;factor_checks=[];pertrade={};year_starts={};year_ends={};last=1.
    for row in daily:
     d=row['date'];y=d[:4];year_starts.setdefault(y,last)
     for e in divs.get(d,[]):accrued[e['position_id']]+=float(e['amount'])
     if d in entries:
      assert active is None;active=entries[d];pertrade[active['position_id']]={'peak':1.,'draw':0.,'days':0}
     posid=active['position_id'] if active else None;factor=None
     if active:
      p=active;pid=p['position_id'];capital=p['entry_notional']+p['buy_fee'];assert capital>0
      if p['closed'] and d==p['exit_date']:
       val=p['exit_notional']-p['sell_fee']+accrued[pid]
      else:
       assert float(row['assets'])>0
       val=float(row['assets'])+accrued[pid];holding_days+=1;pertrade[pid]['days']+=1
      factor=val/capital;assert factor>0
      pertrade[pid]['peak']=max(pertrade[pid]['peak'],factor);pertrade[pid]['draw']=max(pertrade[pid]['draw'],1-factor/pertrade[pid]['peak'])
      nav=base*factor
      if (p['closed'] and d==p['exit_date']) or (not p['closed'] and d==daily[-1]['date']):
       assert abs(factor-(1+p['net_return']))<1e-10,(aid,pid,factor,p['net_return'])
       factor_checks.append((pid,factor))
      if p['closed'] and d==p['exit_date']:base=nav;active=None
     else:nav=base;assert float(row['assets'])==0
     peak=max(peak,nav);draw=max(draw,1-nav/peak);curve.append({'date':d,'unit_value':nav,'decline_from_peak':1-nav/peak,'position_id':posid,'position_factor':factor});year_ends[y]=nav;last=nav
    assert len(factor_checks)==len(ps)
    product=math.prod(1+p['net_return'] for p in ps);assert abs(nav-product)<1e-9
    assert holding_days==sum(float(r['assets'])>0 for r in daily)
    span=(date.fromisoformat(daily[-1]['date'])-date.fromisoformat(daily[0]['date'])).days
    closed=[p for p in ps if p['closed']]
    for p in ps:
     t=buys[p['position_id']];q=pertrade[p['position_id']]
     trade_stats.append({'account_id':aid,'symbol':s,'method':m,'fee_per_side':int(tag)/10000,'candidate_id':p['candidate_id'],'entry_date':p['entry_date'],'exit_date':p['exit_date'],'closed':p['closed'],'entry_price':float(t['price']),'entry_capital':p['entry_notional']+p['buy_fee'],'net_return_on_entry_capital':p['net_return'],'maximum_daily_decline_within_trade':q['draw'],'holding_calendar_days':q['days']})
    out={'account_id':aid,'symbol':s,'method':m,'fee_per_side':int(tag)/10000,'unit_final':nav,'calendar_span_days':span,'holding_calendar_days':holding_days,'calendar_annualized_unit_return':nav**(365.25/span)-1,'holding_time_annualized_speed':nav**(365.25/holding_days)-1 if holding_days>=365.25 else None,'maximum_unit_curve_decline':draw,'worst_single_trade_daily_decline':max(q['draw'] for q in pertrade.values()),'completed_trades':len(closed),'open_trades':len(ps)-len(closed),'closed_net_return_mean':statistics.mean(p['net_return'] for p in closed),'closed_net_return_median':statistics.median(p['net_return'] for p in closed),'closed_win_fraction':sum(p['net_return']>0 for p in closed)/len(closed),'all_position_return_factors_match':True}
    output.append(out);curves[aid]=curve;save(H/(aid+'-curve.json'),curve)
    for y in year_starts:annual.append({'account_id':aid,'year':y,'unit_return':year_ends[y]/year_starts[y]-1})
 pairs=[]
 for s in ['sh510300','sz159915']:
  for tag in ['10','20']:
   a=f'{s}-R1-fee{tag}bp';b=f'{s}-R1-risk1-fee{tag}bp';pa=[p for p in trade_stats if p['account_id']==a];pb=[p for p in trade_stats if p['account_id']==b]
   assert len(pa)==len(pb)
   for x,y in zip(pa,pb):
    assert all(x[k]==y[k] for k in ['candidate_id','entry_date','exit_date','entry_price','closed','holding_calendar_days'])
   err=max(abs(x['net_return_on_entry_capital']-y['net_return_on_entry_capital']) for x,y in zip(pa,pb));cerr=max(abs(x['unit_value']-y['unit_value']) for x,y in zip(curves[a],curves[b]));assert err<1e-10 and cerr<1e-9
   pairs.append({'symbol':s,'fee_per_side':int(tag)/10000,'paired_positions':len(pa),'max_per_trade_return_difference':err,'max_daily_unit_curve_difference':cerr,'same_unit_capital_performance':True})
 assert all(sha(Path(p))==h for p,h in lock.items())
 save(H/'results.json',{'profiles':output,'paired_checks':pairs,'new_strategy_backtests':0,'inputs_unchanged':True});save(H/'trades.json',trade_stats);save(H/'annual.json',annual)
 print(json.dumps({'profiles':output,'paired_checks':pairs},ensure_ascii=False))
if __name__=='__main__':main()
