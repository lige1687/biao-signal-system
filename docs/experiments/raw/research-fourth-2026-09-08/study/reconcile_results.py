"""Rebuild balances from transactions, independently of simulation state updates."""
from pathlib import Path
import json,csv,math
from collections import defaultdict
from datetime import date
P=Path(__file__).resolve().parent

def read(p):
    with p.open() as f:return list(csv.DictReader(f))

def close(a,b,label):
    if abs(a-b)>max(1e-7,abs(b)*1e-10):raise AssertionError((label,a,b))

out=[];contributions={};attributions=[]
ev=[e for e in json.loads((P.parent/'events/510300/events.json').read_text())['events'] if '2023-01-01'<=e['record_date']<='2025-12-31']
for summary in json.loads((P/'summary.json').read_text()):
    path=P/'results'/f"{summary['scenario']}-{summary['arm']}"
    ds=read(path/'daily.csv');ts=read(path/'trades.csv');fs=read(path/'flows.csv');el=json.loads((path/'events.json').read_text())
    tx=defaultdict(list)
    for t in ts:tx[t['date']].append(t)
    flow={f['date']:float(f['amount']) for f in fs}
    contribution_signature=tuple((f['date'],f['amount']) for f in fs)
    scenario=summary['scenario']
    if scenario in contributions:assert contribution_signature==contributions[scenario]
    else:contributions[scenario]=contribution_signature
    syms=[k[6:] for k in ds[0] if k.startswith('units_')]
    positions={s:0 for s in syms};cash=0;receivable=0;rights={};fundunits=0;priornav=1;divtot=0
    paid_by_symbol=defaultdict(float)
    for row in ds:
        d=row['date'];cash+=flow.get(d,0)
        fundunits+=flow.get(d,0)/priornav
        for e in ev if 'sh510300' in syms else []:
            if d==e['ex_date']:receivable+=rights[e['event_id']]*e['cash_per_share']
            if d==e['pay_date']:
                paid=rights[e['event_id']]*e['cash_per_share'];cash+=paid;receivable-=paid;divtot+=paid;paid_by_symbol['sh510300']+=paid
        sides=defaultdict(set)
        for t in tx[d]:
            s=t['symbol'];qty=int(t['shares']);px=float(t['price']);cost=float(t['fee']);side=t['side'];sides[s].add(side)
            assert qty>0 and qty%100==0
            close(cost,qty*px*summary['fee'],'transaction fee')
            if side=='buy':positions[s]+=qty;cash-=qty*px+cost
            else:positions[s]-=qty;cash+=qty*px-cost
            assert positions[s]>=0 and cash>=-1e-7
        assert all(len(v)==1 for v in sides.values()),('same-day round trip',d)
        close(float(row['interest']),cash*((1+summary['cash_rate'])**(1/365)-1),'interest')
        cash*=(1+summary['cash_rate'])**(1/365)
        for s in syms:close(positions[s],float(row['units_'+s]),'share balance')
        for e in ev if 'sh510300' in syms else []:
            if d==e['record_date']:rights[e['event_id']]=positions['sh510300']
        close(cash,float(row['cash']),'cash')
        close(receivable,float(row['receivable']),'receivable')
        wealth=cash+receivable+sum(positions[s]*float(row['mark_'+s]) for s in syms)
        close(wealth,float(row['equity']),'wealth')
        nav=wealth/fundunits if fundunits else 1
        close(nav,float(row['nav']),'unitized NAV');priornav=nav
    close(divtot,summary['dividends_received'],'dividend total')
    close(cash+receivable+sum(positions[s]*float(ds[-1]['mark_'+s]) for s in syms),summary['final_equity'],'final wealth')
    pnl_sum=0
    for s in syms:
        st=[t for t in ts if t['symbol']==s]
        buy=sum(float(t['notional']) for t in st if t['side']=='buy')
        sell=sum(float(t['notional']) for t in st if t['side']=='sell')
        fees=sum(float(t['fee']) for t in st)
        endholding=positions[s]*float(ds[-1]['mark_'+s]);pnl=endholding+sell-buy-fees+paid_by_symbol[s]
        pnl_sum+=pnl
        attributions.append(dict(scenario=scenario,arm=summary['arm'],symbol=s,bought=buy,sold=sell,fees=fees,cash_dividends=paid_by_symbol[s],ending_holdings=endholding,net_investment_profit=pnl))
    close(pnl_sum+summary['cash_interest'],summary['profit'],'profit attribution')
    out.append(dict(scenario=scenario,arm=summary['arm'],days=len(ds),transactions=len(ts),cash_shares_dividends_nav_reconciled=True,same_day_roundtrips=0))
(P/'reconciliation.json').write_text(json.dumps(out,indent=2))
(P/'fund-attribution.json').write_text(json.dumps(attributions,indent=2))
print(json.dumps({'runs_checked':len(out),'daily_accounts':sum(x['days'] for x in out),'transactions_checked':sum(x['transactions'] for x in out),'all_reconciled':True},indent=2))
