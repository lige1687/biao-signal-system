def account(d,start,events,fee,case):
 diagnostics=[]
 idx=d.index;n=len(d);opens=d.open.to_numpy();closes=d.close.to_numpy();f=fee*1e-4
 # Civil schedules are known without reading subsequent prices. Missing exchange calendar is explicitly a proxy.
 weeks={}
 for sun in pd.date_range(idx[start].normalize()-pd.Timedelta(days=7),idx[-1],freq='W-SUN'):
  ts=sun+pd.Timedelta(hours=23,minutes=59);j=int(idx.searchsorted(ts,side='right'))
  if j<n:weeks.setdefault(j,[]).append(ts)
 incoming={};event_rows=[]
 for no,e in enumerate(events):
  e={**e,'event_id':f'{case}|event{no:04d}'};j=int(idx.searchsorted(e['decision_at'],side='right'));incoming.setdefault(j,[]).append(e)
 cash=1.;units=0.;active=None;paid=0.;realized=0.;daily=[];trades=[];actions=[];peak=1.;plan_no=0
 def close_plan(i,reason):
  nonlocal cash,units,paid,active,realized
  
  if units==0:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),status='cash_only_plan_expired',pending_reason=reason))
  val=units*opens[i];cost=val*f;cash+=val-cost;paid+=cost;realized+=val-cost-active['invested'];actions.append(dict(case=case,date=str(idx[i].date()),action='sell',amount=val,fee=cost,units=units,price=opens[i],plan=active['id'],reason=reason,available_at=str(active['pending_exit'][1])))
  trades.append(dict(case=case,plan=active['id'],trigger=str(active['decision_at']),e=active['e'],exit_date=str(idx[i].date()),reason=reason,budget=active['budget'],invested=active['invested'],buy_count=active['buys'],terminal_wealth=cash,plan_return=cash/active['budget']-1,holding_quote_days=i-active['e'],status='closed'))
  units=0.;active=None
 for i in range(start,n):
  # These decisions arrived before this open, while previous holdings were still held.
  for ev in incoming.get(i,[]):
   row=dict(case=case,event_id=ev['event_id'],decision_at=str(ev['decision_at']),quote_date=str(idx[ev['e']].date()),first_possible_open=str(idx[i].date()))
   if active is not None:row['status']='rejected_capital_occupied'
   elif cash<=1e-14:row['status']='rejected_no_capital'
   else:
    plan_no+=1;active=dict(id=plan_no,e=ev['e'],decision_at=ev['decision_at'],budget=cash,invested=0.,buys=0,pending_buys=[],pending_exit=None);row['status']='accepted'
   event_rows.append(row)
  sold=False
  if active and i>active['e']+252:
   
   for ts in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),scheduled_at=str(ts),status='cancelled_accumulation_ended'))
   active['pending_buys']=[]
   expired=i>=active['e']+756
   hit=active['invested']>0 and np.isfinite(closes[i-1]) and units*closes[i-1]/active['invested']-1>=.30
   if active['pending_exit'] is None and (expired or hit):
    active['pending_exit']=('deadline' if expired else 'target30',idx[i-1]+pd.Timedelta(hours=16))
   if active['pending_exit'] is not None and np.isfinite(opens[i]) and opens[i]>0:
    close_plan(i,active['pending_exit'][0]);sold=True
  if active and not sold and active['e']<i<=active['e']+252:
   active['pending_buys'].extend(ts for ts in weeks.get(i,[]) if ts>active['decision_at'])
   if active['buys']>=52:
    for pending in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),scheduled_at=str(pending),status='cancelled_buy_cap'))
    active['pending_buys']=[]
   due=list(active['pending_buys']) if np.isfinite(opens[i]) and opens[i]>0 else []
   for ts in due:
    if active['buys']>=52:
     for pending in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),scheduled_at=str(pending),status='cancelled_buy_cap'))
     active['pending_buys']=[]
     break
    active['pending_buys'].remove(ts)
    amt=min(active['budget']/52,cash);qty=amt*(1-f)/opens[i];units+=qty;cash-=amt;paid+=amt*f;active['invested']+=amt;active['buys']+=1
    actions.append(dict(case=case,date=str(idx[i].date()),action='buy',amount=amt,fee=amt*f,units=qty,price=opens[i],plan=active['id'],reason='weekly_schedule',available_at=str(ts)))
  value=units*closes[i];eq=cash+value;unrealized=value-(active['invested'] if active else 0.)
  assert cash>=-1e-12 and abs(eq-(1+realized+unrealized))<1e-10
  daily.append(dict(date=str(idx[i].date()),cash=cash,units=units,close=closes[i],holdings=value,equity=eq,external_inflow=1. if i==start else 0.,external_outflow=0.,cumulative_fees=paid,realized=realized,unrealized=unrealized,active_plan=active['id'] if active else 0))
 for ev in incoming.get(n,[]):event_rows.append(dict(case=case,event_id=ev['event_id'],decision_at=str(ev['decision_at']),quote_date=str(idx[ev['e']].date()),first_possible_open=None,status='unexecuted_no_next_quote'))
 if active:
  for ts in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[-1].date()),scheduled_at=str(ts),status='unexecuted_buy_at_cutoff'))
  if active['pending_exit'] is not None:diagnostics.append(dict(plan=active['id'],date=str(idx[-1].date()),status='unexecuted_exit_at_cutoff',reason=active['pending_exit'][0],available_at=str(active['pending_exit'][1])))
 if active:trades.append(dict(case=case,plan=active['id'],trigger=str(active['decision_at']),e=active['e'],exit_date=None,reason='open_at_cutoff',budget=active['budget'],invested=active['invested'],buy_count=active['buys'],terminal_wealth=daily[-1]['equity'],plan_return=daily[-1]['equity']/active['budget']-1,holding_quote_days=n-1-active['e'],status='open'))
 closed=[x for x in trades if x['status']=='closed'];rets=np.array([x['plan_return'] for x in closed]);eq=[x['equity'] for x in daily]
 summary=dict(case=case,fee_bps=fee,start=str(idx[start].date()),end=str(idx[-1].date()),events=len(events),accepted=sum(x['status']=='accepted' for x in event_rows),rejected_occupied=sum(x['status']=='rejected_capital_occupied' for x in event_rows),unexecuted_no_next_quote=sum(x['status']=='unexecuted_no_next_quote' for x in event_rows),closed_plans=len(closed),open_plans=sum(x['status']=='open' for x in trades),final_wealth=eq[-1],ending_cash=cash,ending_holdings=units*closes[-1],net_liquidation_estimate=cash+units*closes[-1]*(1-f),external_total=1.,total_fees=paid,mean_cash_fraction=float(np.mean([x['cash']/x['equity'] for x in daily])),mean_closed_return=float(rets.mean()) if len(rets) else None,median_closed_return=float(np.median(rets)) if len(rets) else None,min_closed_return=float(rets.min()) if len(rets) else None,closed_win_fraction=float((rets>0).mean()) if len(rets) else None,mean_closed_holding=float(np.mean([x['holding_quote_days'] for x in closed])) if closed else None,**risk_stats(eq,idx[start:]))
 return summary,daily,trades,event_rows,actions,diagnostics
