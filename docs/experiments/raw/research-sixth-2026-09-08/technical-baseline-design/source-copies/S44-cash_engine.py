"""Isolated civil-day cash ledger; no production imports or network calls."""
from datetime import date, timedelta
import math


def simulate(prices, events, *, start, end, weekly, fee, cash_rate, rebalance, limits, limit_changes=None, blocked_dates=None):
    syms = sorted(prices)
    limit_changes = limit_changes or {}
    blocked_dates = blocked_dates or {}
    for symbol, rows in prices.items():
        for quote_date, quote in rows.items():
            if quote_date <= end:
                if any(not math.isfinite(quote[k]) or quote[k] <= 0 for k in ('open', 'close')):
                    raise ValueError('Invalid price: '+symbol+' '+quote_date)
    ids = set()
    economic_events = set()
    for event in events:
        if event['event_id'] in ids:
            raise ValueError('Duplicate event: '+event['event_id'])
        ids.add(event['event_id'])
        for field in ('record_date', 'ex_date', 'pay_date', 'announcement_date'):
            if field in event and date.fromisoformat(event[field]).isoformat() != event[field]:
                raise ValueError('Noncanonical event date')
        economic_key = tuple(event.get(k) for k in ('symbol','type','record_date','ex_date','pay_date','cash_per_share','ratio'))
        if economic_key in economic_events:
            raise ValueError('Duplicate economic event')
        economic_events.add(economic_key)
        if event['type'] == 'cash_dividend':
            if not event['record_date'] < event['ex_date'] <= event['pay_date']:
                raise ValueError('Invalid dividend dates: '+event['event_id'])
            if not math.isfinite(event['cash_per_share']) or event['cash_per_share'] < 0:
                raise ValueError('Invalid dividend amount')
        elif event['type'] == 'split':
            if not math.isfinite(event['ratio']) or event['ratio'] <= 0:
                raise ValueError('Invalid split ratio')
        else:
            raise ValueError('Unsupported cash action')
    n = len(syms)
    cash = {s: 0.0 for s in syms}
    units = {s: 0 for s in syms}
    last = {}
    last_date = {}
    for s in syms:
        before = sorted(d for d in prices[s] if d < start)
        if not before:
            raise ValueError('Need a price before simulation: '+s)
        last[s] = float(prices[s][before[-1]]['close'])
        last_date[s] = before[-1]
    events = [e for e in events if e['symbol'] in syms]
    entitlement, receivable = {}, {}
    daily, trades, flows, logs = [], [], [], []
    account_units, nav, total_funding = 0.0, 1.0, 0.0
    pending_quarter = False
    dr = (1+cash_rate)**(1/365)-1
    day = date.fromisoformat(start)
    while day <= date.fromisoformat(end):
        d = day.isoformat()
        if day.month in (1,4,7,10) and day.day == 1:
            pending_quarter = bool(rebalance)
        reference = last.copy()
        for e in events:
            s = e['symbol']; eid = e['event_id']
            if e['type'] == 'split' and e['ex_date'] == d:
                old = units[s]; units[s] *= e['ratio']
                reference[s] /= e['ratio']; last[s] /= e['ratio']
                logs.append(dict(date=d,kind='split',symbol=s,event_id=eid,old_shares=old,new_shares=units[s],amount=0))
            if e['type'] == 'cash_dividend' and e['ex_date'] == d:
                if e['record_date'] >= start and eid not in entitlement:
                    raise ValueError('Unrecorded dividend entitlement: '+eid)
                amount = entitlement.get(eid, 0)*e['cash_per_share']
                receivable[eid] = amount
                reference[s] -= e['cash_per_share']; last[s] -= e['cash_per_share']
                logs.append(dict(date=d,kind='dividend_receivable',symbol=s,event_id=eid,amount=amount))
            if e['type'] == 'cash_dividend' and e['pay_date'] == d:
                amount = receivable.pop(eid, 0.0)
                cash[s] += amount
                logs.append(dict(date=d,kind='dividend_paid',symbol=s,event_id=eid,amount=amount))
        if day.weekday() == 0:
            account_units += weekly/nav
            total_funding += weekly
            for s in syms:cash[s] += weekly/n
            flows.append(dict(date=d,amount=weekly))
        tradable = {}
        for s in syms:
            q = prices[s].get(d)
            reason = None
            limit = limits[s]
            for effective, changed_limit in sorted(limit_changes.get(s, [])):
                if effective <= d:limit = changed_limit
            if d in blocked_dates.get(s, []):reason='known_open_unavailable'
            elif q is None:reason='missing_quote' 
            elif not math.isfinite(q['open']) or q['open']<=0:raise ValueError('Bad open')
            elif reference[s] <= 0:raise ValueError('Bad reference price')
            elif abs(q['open']-reference[s]) >= reference[s]*limit-.00051:
                reason='at_open_limit_conservative'
            tradable[s] = reason is None
            if reason and (cash[s]>0 or pending_quarter):
                logs.append(dict(date=d,kind='deferred',symbol=s,reason=reason,amount=0))

        def execute(s, qty, side, reason):
            if qty <= 0:return
            assert qty % 100 == 0 and tradable[s]
            px = prices[s][d]['open']; notional=qty*px; cost=notional*fee
            if side == 'buy':cash[s] -= notional+cost; units[s] += qty
            else:cash[s] += notional-cost; units[s] -= qty
            trades.append(dict(date=d,symbol=s,side=side,shares=qty,price=px,notional=notional,fee=cost,reason=reason))

        if pending_quarter and all(tradable.values()):
            budget=sum(cash.values())+sum(units[s]*reference[s] for s in syms)
            target={s:math.floor(max(0,budget*(1-2*fee)/n)/reference[s]/100)*100 for s in syms}
            # Common cash only during this scheduled redistribution.
            pool=sum(cash.values())
            for s in syms:cash[s]=0.0
            for s in syms:
                qty=max(0,units[s]-target[s])
                execute(s,qty,'sell','quarterly_previous_close_target')
                pool+=cash[s];cash[s]=0.0
            for s in syms:
                cash[s]=pool
                cap=math.floor(max(0,pool)/(prices[s][d]['open']*(1+fee))/100)*100
                qty=min(max(0,target[s]-units[s]),cap)
                execute(s,qty,'buy','quarterly_previous_close_target')
                pool=cash[s];cash[s]=0.0
            for s in syms:cash[s]=pool/n
            logs.append(dict(date=d,kind='rebalance',symbol='all',amount=budget,targets=target))
            pending_quarter=False
        else:
            for s in syms:
                if tradable[s]:
                    qty=math.floor(max(0,cash[s])/(prices[s][d]['open']*(1+fee))/100)*100
                    execute(s,qty,'buy','cash_available')
        interest=0.0
        for s in syms:
            if cash[s] < -1e-7 or units[s] < 0:raise AssertionError('Negative balance')
            c_interest=cash[s]*dr;cash[s]+=c_interest;interest+=c_interest
            if d in prices[s]:last[s]=float(prices[s][d]['close']);last_date[s]=d
        for e in events:
            if e['type']=='cash_dividend' and e['record_date']==d:
                s=e['symbol']
                if units[s]>0 and d not in prices[s]:raise ValueError('Held asset missing on record date')
                entitlement[e['event_id']]=units[s]
                logs.append(dict(date=d,kind='dividend_recorded',symbol=s,event_id=e['event_id'],shares=units[s],amount=0))
        assets=sum(units[s]*last[s] for s in syms)
        c=sum(cash.values());r=sum(receivable.values());equity=assets+c+r
        if account_units:nav=equity/account_units
        row=dict(date=d,equity=equity,assets=assets,cash=c,receivable=r,interest=interest,total_funding=total_funding,account_units=account_units,nav=nav,stale_symbols=','.join(s for s in syms if last_date[s]!=d))
        for s in syms:row['units_'+s]=units[s];row['cash_'+s]=cash[s];row['mark_'+s]=last[s]
        daily.append(row)
        day+=timedelta(days=1)
    return dict(daily=daily,trades=trades,flows=flows,events=logs)
