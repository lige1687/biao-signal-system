"""Isolated technical research cash account. No production imports or I/O."""
from bisect import bisect_right
from copy import deepcopy
from datetime import date, timedelta
import math


def _finite(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)


def simulate(prices, actions, candidates, exit_observations, *, start, end,
             weekly_per_symbol=250, fee=.001, config_id, limits,
             limit_changes=None, blocked_dates=None, exit_rule=None):
    diagnostic_configs={'R0','R1'}
    is_diagnostic_config=config_id in diagnostic_configs
    if config_id not in ['P'+str(i) for i in range(8)] and not is_diagnostic_config:raise ValueError('Unknown configuration')
    if start>end or not _finite(fee) or fee<0 or fee>=1:raise ValueError('Invalid window or fee')
    if not _finite(weekly_per_symbol) or weekly_per_symbol<0:raise ValueError('Invalid funding')
    syms=sorted(prices);actions=deepcopy(actions);cs=deepcopy(candidates)
    if not syms:raise ValueError('No products')
    for s in syms:
        if s not in limits or not 0<float(limits[s])<=1:raise ValueError('Missing limit')
    limit_changes=limit_changes or {};blocked_dates=blocked_dates or {}
    bars={s:{} for s in syms}
    for s,rows in prices.items():
        for d,b in rows.items():
            if date.fromisoformat(d).isoformat()!=d:raise ValueError('Noncanonical quote date')
            vals=[b.get(k) for k in ('open','high','low','close')]
            missing=[v is None or (_finite(v)==False and isinstance(v,(int,float))) for v in vals]
            if all(missing):continue
            if any(not _finite(v) or v<=0 for v in vals):raise ValueError('Invalid partial/negative quote '+s+' '+d)
            op,hi,lo,cl=vals
            if not lo<=min(op,cl)<=max(op,cl)<=hi:raise ValueError('Invalid OHLC order')
            bars[s][d]=b
    schedule=sorted({d for rows in prices.values() for d in rows})
    ids=set();economic=set();action_days=set()
    for a in actions:
        if a['symbol'] not in syms:raise ValueError('Action on unknown product')
        if a['event_id'] in ids:raise ValueError('Duplicate action ID')
        ids.add(a['event_id']);key=tuple(a.get(k) for k in ('symbol','type','record_date','ex_date','pay_date','cash_per_share','ratio'))
        if key in economic:raise ValueError('Duplicate economic action')
        economic.add(key)
        if (a['symbol'],a['ex_date']) in action_days:raise ValueError('Same-day action order unspecified')
        action_days.add((a['symbol'],a['ex_date']))
        for k in ['announcement_date','ex_date']+(['record_date','pay_date'] if a['type']=='cash_dividend' else []):
            if date.fromisoformat(a[k]).isoformat()!=a[k]:raise ValueError('Noncanonical action date')
        if a['announcement_date']>=a['ex_date']:raise ValueError('Action not known before effective open')
        if a['type']=='cash_dividend':
            if not a['record_date']<a['ex_date']<=a['pay_date']:raise ValueError('Invalid dividend dates')
            if not _finite(a['cash_per_share']) or a['cash_per_share']<0:raise ValueError('Bad dividend')
        elif a['type']=='split':
            if not _finite(a['ratio']) or a['ratio']<=0:raise ValueError('Bad split')
        else:raise ValueError('Unknown action type')
    bysignal={};cids=set()
    for c in sorted(cs,key=lambda x:(x['signal_date'],x['symbol'],x['candidate_id'])):
        if c['candidate_id'] in cids:raise ValueError('Duplicate candidate ID')
        cids.add(c['candidate_id'])
        if c['symbol'] not in syms:raise ValueError('Unknown candidate product')
        if start<=c['signal_date']<=end:bysignal.setdefault(c['signal_date'],[]).append(c)
    cash={s:0. for s in syms};units={s:0. for s in syms};position={s:None for s in syms}
    last={};last_date={};previous_equity={s:0. for s in syms}
    for s in syms:
        past=sorted(d for d in bars[s] if d<start)
        if not past:raise ValueError('Need valid pre-window close '+s)
        last_date[s]=past[-1];last[s]=float(bars[s][past[-1]]['close'])
    orders=[];trades=[];logs=[];daily=[];roundtrips=[];rights={};receivables={};pending_sell={};pending_buy=[]
    fees={s:0. for s in syms};funding={s:0. for s in syms};account_units=0.;nav=1.;peak=1.

    def order(side,s,d,reason,**extra):
        o=dict(order_id=f'{config_id}-O{len(orders)+1}',config_id=config_id,side=side,symbol=s,
               signal_date=d,reason=reason,status='pending',attempts=[],diagnostic_reference_only=is_diagnostic_config,**extra);orders.append(o);return o

    def rejection(o,reason,d=None):
        o['status']='rejected';o['reason']=reason
        if d is not None:o['resolved_date']=d

    def account_receivable(s):
        return sum(v['amount'] for v in receivables.values() if v['symbol']==s)

    def update_roundtrip(p,d):
        market=0. if p['closed'] else units[p['symbol']]*last[p['symbol']]
        p['market_value']=market;p['valuation_date']=p['exit_date'] if p['closed'] else last_date[p['symbol']]
        p['accounting_updated_date']=d
        p['net_pnl']=p['exit_notional']+market+p['dividend_accrued']-p['entry_notional']-p['buy_fee']-p['sell_fee']
        p['net_return']=p['net_pnl']/(p['entry_notional']+p['buy_fee']) if p['entry_notional'] else None

    day=date.fromisoformat(start)
    while day<=date.fromisoformat(end):
        d=day.isoformat();reference=last.copy();sold_today=set();risk_reference=previous_equity.copy()
        # Corporate actions change old nominal marks, economic holdings, and technical levels separately.
        for a in sorted(actions,key=lambda x:(x['ex_date'],x['event_id'])):
            s=a['symbol'];eid=a['event_id']
            if a['ex_date']==d:
                if a['type']=='split':
                    factor=1/a['ratio'];old=units[s];units[s]*=a['ratio'];last[s]*=factor;reference[s]*=factor
                    if position[s]:position[s]['shares']=units[s]
                    logs.append(dict(date=d,kind='split',symbol=s,event_id=eid,old_shares=old,new_shares=units[s],factor=factor,amount=0.))
                else:
                    div=a['cash_per_share']
                    if reference[s]<=div:raise ValueError('Nonpositive ex-dividend reference')
                    factor=(reference[s]-div)/reference[s];last[s]-=div;reference[s]-=div
                    if a['record_date']>=start and eid not in rights:raise ValueError('Missing recorded entitlement')
                    right=rights.get(eid,{'shares':0.,'position':None});amount=right['shares']*div
                    receivables[eid]=dict(symbol=s,amount=amount,position=right['position'])
                    if right['position']:right['position']['dividend_accrued']+=amount
                    logs.append(dict(date=d,kind='dividend_receivable',symbol=s,event_id=eid,amount=amount,entitled_shares=right['shares'],position_id=right['position']['position_id'] if right['position'] else None))
                targets=([position[s]] if position[s] else [])+[o for o in pending_buy if o['symbol']==s and o['status']=='pending' and o['signal_date']<d]
                for obj in targets:
                    for level in ['stop','target','upper']:
                        if _finite(obj.get(level)):obj[level]*=factor
                    obj.setdefault('level_actions',[]).append(eid)
                if last[s]<=0:raise ValueError('Nonpositive transformed mark')
            if a['type']=='cash_dividend' and a['pay_date']==d:
                item=receivables.pop(eid,None)
                if item is None:
                    if a['ex_date']>=start:raise ValueError('Missing dividend receivable')
                    item={'amount':0.,'position':None}
                cash[s]+=item['amount']
                if item['position']:item['position']['dividend_paid']+=item['amount']
                logs.append(dict(date=d,kind='dividend_paid',symbol=s,event_id=eid,amount=item['amount']))
        flow=0.
        if day.weekday()==0:
            flow=weekly_per_symbol*len(syms)
            if flow and nav<=0:raise ValueError('Cannot unitize insolvent account')
            account_units+=flow/nav
            for s in syms:cash[s]+=weekly_per_symbol;funding[s]+=weekly_per_symbol
            logs.append(dict(date=d,kind='deposit',symbol='all',amount=flow))

        def unavailable(s):
            if d in blocked_dates.get(s,[]):return 'known_open_unavailable'
            if d not in bars[s]:return 'missing_quote'
            limit=limits[s];changes=limit_changes.get(s,[])
            for effective,value in sorted(changes.items() if isinstance(changes,dict) else changes):
                if effective<=d:limit=value
            if abs(bars[s][d]['open']-reference[s])>=reference[s]*limit-.00051:return 'at_open_limit_conservative'
            return None

        def fill_buy(s,o,qty,risk_budget):
            px=float(bars[s][d]['open']);notional=qty*px;cost=notional*fee
            assert qty>0 and qty%100==0 and cash[s]+1e-9>=notional+cost
            cash[s]-=notional+cost;units[s]+=qty;fees[s]+=cost
            p=position[s]
            if p is None:
                p=dict(position_id=f'{config_id}-{s}-T{len(roundtrips)+1}',config_id=config_id,symbol=s,candidate_id=o.get('candidate_id'),entry_date=d,entry_price=px,entry_notional=0.,buy_fee=0.,sell_fee=0.,exit_notional=0.,dividend_accrued=0.,dividend_paid=0.,closed=False,exit_date=None,stop=o.get('stop'),target=o.get('target'),upper=o.get('upper'),variant=o.get('variant','breakout'),initial_stop=o.get('stop'),initial_target=o.get('target'),initial_upper=o.get('upper'),level_actions=list(o.get('level_actions',[])),diagnostic_reference_only=is_diagnostic_config)
                position[s]=p;roundtrips.append(p)
            p['entry_notional']+=notional;p['buy_fee']+=cost;p['shares']=units[s]
            o.update(status='filled',resolved_date=d,shares=qty,price=px,position_id=p['position_id'])
            trade=dict(date=d,config_id=config_id,symbol=s,side='buy',shares=qty,price=px,notional=notional,fee=cost,reason=o['reason'],order_id=o['order_id'],position_id=p['position_id'],candidate_id=o.get('candidate_id'),risk_budget=risk_budget,previous_product_equity=risk_reference[s],stop=p['stop'],target=p['target'])
            if is_diagnostic_config:trade['diagnostic_reference_only']=True
            trades.append(trade)

        for s,o in list(pending_sell.items()):
            if d<=o['signal_date']:continue
            reason=unavailable(s)
            if position[s] is None:raise AssertionError('Sell without position')
            if d<=position[s]['entry_date']:reason='tplus_restriction'
            o['attempts'].append(dict(date=d,reason=reason or 'filled'))
            if reason:continue
            p=position[s];qty=units[s];px=float(bars[s][d]['open']);notional=qty*px;cost=notional*fee
            cash[s]+=notional-cost;units[s]=0.;fees[s]+=cost;p.update(closed=True,exit_date=d,exit_price=px,exit_notional=notional,sell_fee=cost,shares=0.)
            o.update(status='filled',resolved_date=d,shares=qty,price=px);sold_today.add(s)
            trade=dict(date=d,config_id=config_id,symbol=s,side='sell',shares=qty,price=px,notional=notional,fee=cost,reason=o['reason'],order_id=o['order_id'],position_id=p['position_id'])
            if is_diagnostic_config:trade['diagnostic_reference_only']=True
            trades.append(trade)
            position[s]=None;del pending_sell[s]
        if config_id=='P6':
            for s in syms:
                if unavailable(s) is None:
                    qty=math.floor(max(0.,cash[s])/(float(bars[s][d]['open'])*(1+fee))/100)*100
                    if qty:
                        o=order('buy',s,d,'passive_cash_available',planned_date=d);o['attempts'].append(dict(date=d,reason='filled'));fill_buy(s,o,qty,None)
        else:
            for o in pending_buy:
                if o['status']!='pending' or o['planned_date']!=d:continue
                s=o['symbol'];reason='same_day_sale' if s in sold_today else 'position_exists' if position[s] else unavailable(s)
                ep=float(bars[s][d]['open']) if d in bars[s] else None
                if not reason:
                    if not _finite(o.get('stop')) or o['stop']<=0 or o['stop']>=ep:reason='nonpositive_open_risk'
                    else:
                        if _finite(o.get('target')):
                            o['open_rr']=(o['target']-ep)/(ep-o['stop'])
                            if not is_diagnostic_config and o['open_rr']<3:reason='open_rr_below3'
                risk_budget=risk_reference[s]*.01 if config_id=='P7' else None
                qty=0
                if not reason:
                    qty=math.floor(max(0.,cash[s])/(ep*(1+fee))/100)*100
                    if config_id=='P7':qty=min(qty,math.floor(max(0.,risk_budget)/(ep-o['stop'])/100+1e-12)*100)
                    if qty<=0:reason='insufficient_cash_or_risk_lot'
                o['attempts'].append(dict(date=d,reason=reason or 'filled',open_price=ep,open_rr=o.get('open_rr'),risk_budget=risk_budget,previous_product_equity=risk_reference[s]))
                if reason:rejection(o,reason,d)
                else:fill_buy(s,o,qty,risk_budget)
        # Closing marks and closing signal decisions: never perform a same-day sell.
        for s in syms:
            if d in bars[s]:last[s]=float(bars[s][d]['close']);last_date[s]=d
            p=position[s]
            if not p or config_id=='P6' or s in pending_sell or d not in bars[s]:continue
            cl=last[s];reason=None
            if cl<p['stop']:reason='structure_stop'
            else:
                obs=exit_observations.get(s,{}).get(d,{})
                if exit_rule is not None:reason=exit_rule(deepcopy(p),deepcopy(obs),cl)
                elif config_id in ('P4','P7'):
                    for k in ['sma20','cost20']:
                        if not _finite(obs.get(k)):raise ValueError('Missing exit observation '+k+' '+s+' '+d)
                    if not _finite(p.get('upper')):raise ValueError('Missing breakout upper')
                    if cl<p['upper'] and cl<obs['sma20'] and cl<obs['cost20']:reason='b_breakout_two_actions'
                else:
                    for k in ['ema20','cost20']:
                        if not _finite(obs.get(k)):raise ValueError('Missing exit observation '+k+' '+s+' '+d)
                    if cl<obs['ema20'] and cl<obs['cost20']:reason='ema_cost_exit'
            if reason:pending_sell[s]=order('sell',s,d,reason,position_id=p['position_id'])
        for c in bysignal.get(d,[]):
            if config_id=='P6':continue
            s=c['symbol'];planned_index=bisect_right(schedule,d);planned=schedule[planned_index] if planned_index<len(schedule) else None
            candidate_metadata=deepcopy(c)
            exclude=('symbol','signal_date','config_id','side','reason','status','attempts','planned_date','order_id','candidate_metadata','resolved_date','position_id')
            candidate_fields={k:deepcopy(v) for k,v in c.items() if k not in exclude}
            if is_diagnostic_config:
                candidate_metadata['diagnostic_reference_only']=True
                candidate_metadata.setdefault('original_candidate_id',c.get('candidate_id'))
                candidate_metadata.setdefault('original_config_id','P0' if config_id=='R0' else 'P5')
                candidate_fields['original_candidate_id']=candidate_metadata['original_candidate_id']
                candidate_fields['original_config_id']=candidate_metadata['original_config_id']
            o=order('buy',s,d,'candidate_entry',planned_date=planned,candidate_metadata=candidate_metadata,**candidate_fields)
            reason=None
            if c.get('signal_accepted') is False:
                reason=c.get('signal_reject_reason') or 'signal_rejected'
                if is_diagnostic_config and reason in ('target_unavailable','signal_reward_risk_below_3'):reason=None
            elif d not in bars[s]:raise ValueError('Candidate without signal close')
            elif not _finite(c.get('stop')) or c['stop']<=0:reason='invalid_stop'
            elif is_diagnostic_config:
                ref=c.get('signal_ref',bars[s][d]['close'])
                if not _finite(ref) or ref<=c['stop']:reason='nonpositive_signal_risk'
            elif not _finite(c.get('target')) or c['target']<=0:reason='missing_or_invalid_target'
            elif not _finite(c.get('stop')) or c['stop']<=0:reason='invalid_stop'
            elif config_id in ('P4','P7') and c.get('variant','breakout')!='breakout':raise ValueError('Only breakout variant locked')
            elif 'signal_ref' in c:
                ref=c['signal_ref']
                if not _finite(ref) or ref<=c['stop']:reason='nonpositive_signal_risk'
                else:
                    o['signal_rr_recomputed']=(c['target']-ref)/(ref-c['stop'])
                    if o['signal_rr_recomputed']<3:reason='signal_rr_below3'
            if not reason and position[s]:reason='pending_exit' if s in pending_sell else 'position_exists'
            if reason:rejection(o,reason,d)
            else:pending_buy.append(o)
        for a in actions:
            if a['type']=='cash_dividend' and a['record_date']==d:
                s=a['symbol']
                if units[s]>0 and d not in bars[s]:raise ValueError('Held asset lacks record-day quote')
                rights[a['event_id']]={'shares':units[s],'position':position[s]}
                logs.append(dict(date=d,kind='dividend_recorded',symbol=s,event_id=a['event_id'],shares=units[s],position_id=position[s]['position_id'] if position[s] else None))
        assets=sum(units[s]*last[s] for s in syms);total_cash=sum(cash.values());rec=sum(v['amount'] for v in receivables.values());equity=assets+total_cash+rec
        if account_units:nav=equity/account_units
        peak=max(peak,nav)
        row=dict(date=d,config_id=config_id,equity=equity,assets=assets,cash=total_cash,receivable=rec,total_funding=sum(funding.values()),deposit=flow,account_units=account_units,nav=nav,drawdown=nav/peak-1,fees=sum(fees.values()),stale_symbols=','.join(s for s in syms if last_date[s]!=d),accounting_difference=equity-assets-total_cash-rec)
        if is_diagnostic_config:row['diagnostic_reference_only']=True
        for s in syms:
            if cash[s]<-1e-7 or units[s]<0:raise AssertionError('Negative account state')
            previous_equity[s]=cash[s]+units[s]*last[s]+account_receivable(s)
            row.update({f'units_{s}':units[s],f'cash_{s}':cash[s],f'mark_{s}':last[s],f'mark_date_{s}':last_date[s],f'receivable_{s}':account_receivable(s),f'equity_{s}':previous_equity[s],f'previous_equity_{s}':risk_reference[s],f'funding_{s}':funding[s],f'fees_{s}':fees[s]})
        daily.append(row)
        for p in roundtrips:update_roundtrip(p,d)
        day+=timedelta(days=1)
    for o in orders:
        if o['status']=='pending':o['status']='pending_at_end'
    return dict(daily=daily,trades=trades,orders=orders,events=logs,roundtrips=roundtrips)
