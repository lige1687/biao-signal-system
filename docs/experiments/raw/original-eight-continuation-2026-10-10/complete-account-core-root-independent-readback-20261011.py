"""Independently replay recorded money flows and verify complete-account metrics.

This reads delivered account events; it does not execute a policy or select a
different parameter/window. Original source closes are used only for acceptance.
"""
from pathlib import Path
from fractions import Fraction as F
import csv,hashlib,json,math
from collections import defaultdict
from datetime import date,timedelta

ROOT=Path(__file__).resolve().parents[4];RAW=Path(__file__).parent
HERE=ROOT/'docs/experiments/raw/weekly-two-etf-complete-account-2026-10-11'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((RAW/'complete-account-core-output-plan-20261011.json').read_text())
p=Path(plan['output'])/'paired-core-account.json'
raw=json.loads(p.read_text())
assert p.stat().st_dev==plan['external_device']
loc=json.loads((HERE/'core-result-location.json').read_text())
assert str(p)==loc['result'] and p.stat().st_size==loc['result_bytes']
assert sha(p)==loc['result_sha256']
source=ROOT/'docs/experiments/raw/research-eighth-2026-09-08/product-qualification'
closes={}
for s in ('sh510300','sz159915'):
    with (source/(s+'-nominal.csv')).open() as fp:
        closes[s]={r['session_date']:F(r['close']) for r in csv.DictReader(fp)}
actions={r['event_id']:r for r in json.loads((source/'actions.json').read_text())}
tol=F(1,10**16)
accepted={}
for policy in ('P0','P1'):
    delivered=raw['results'][policy];a=delivered['account'];m=delivered['metrics']
    cash=F(0);fees=F(0);contributions=F(0);units=F(0);restricted={};receivable={}
    shares={s:F(0) for s in closes};lots={s:[] for s in closes}
    entitlements={};realized=F(0);dividend=F(0);previous_nav=F(1)
    events=a['events'];i=0;buycount=0;sellcount=0;deposits=[];lastmarks={}
    for s,byday in closes.items():
        lastmarks[s]=byday[max(d for d in byday if d<'2015-01-01')]
    for dayrow in a['daily']:
        day=dayrow['day']
        while i<len(events) and events[i]['day']<=day:
            e=events[i];i+=1;k=e['kind']
            if k=='deposit':
                assert F(e['nav_used'])>0 and abs(F(e['nav_used'])-previous_nav)<tol
                assert date.fromisoformat(e['day']).weekday()==0 and e['day'] not in {d for d,v in deposits}
                amount=F(e['amount']);assert amount==250
                cash+=amount;contributions+=amount;units+=amount/F(e['nav_used'])
                deposits.append((e['day'],amount))
            elif k in ('buy','sell'):
                s=e['symbol'];q=F(e['qty']);price=F(e['price'])
                assert q>0 and q%100==0
                nf=q*price;charge=max(nf*F('.001'),F(5))+nf*F('.001')
                assert charge==F(e['fee']);fees+=charge
                if k=='buy':
                    buycount+=1;cash-=nf+charge;shares[s]+=q;lots[s].append([q,price])
                else:
                    sellcount+=1;assert shares[s]>=q;shares[s]-=q
                    remaining=q;basis=F(0)
                    for lot in lots[s]:
                        take=min(remaining,lot[0]);basis+=take*lot[1];lot[0]-=take;remaining-=take
                        if not remaining:break
                    assert remaining==0;lots[s]=[x for x in lots[s] if x[0]]
                    realized+=nf-basis
                    net=nf-charge;assert net==F(e['net_restricted'])
                    assert e['order_id'] not in restricted;restricted[e['order_id']]=net
            elif k=='release_sale_cash':
                amount=restricted.pop(e['sale_id'])
                assert amount==F(e['amount']);cash+=amount
            elif k=='record':
                assert F(e['eligible_shares'])==shares[actions[e['action']]['symbol']]
                assert e['action'] not in entitlements;entitlements[e['action']]=F(e['eligible_shares'])
            elif k=='ex':
                action=actions[e['action']]
                amount=entitlements[e['action']]*F(action['cash'])
                assert amount==F(e['receivable']) and e['action'] not in receivable
                receivable[e['action']]=amount;dividend+=amount
                assert F(e['reference_before'])-F(action['cash'])==F(e['reference_after'])
                lastmarks[action['symbol']]-=F(action['cash'])
            elif k=='pay':
                amount=receivable.pop(e['action']);assert amount==F(e['amount'])
                assert e['day']>actions[e['action']]['pay_date'];cash+=amount
            else:raise AssertionError(('unrecognized money event',k))
            assert cash>=0
        got=dayrow['account']
        assert F(got['free_cash'])==cash and F(got['restricted_cash'])==sum(restricted.values(),F(0))
        assert F(got['receivable'])==sum(receivable.values(),F(0))
        for s in shares:
            assert F(got['shares'][s])==shares[s]
            if day in closes[s]:lastmarks[s]=closes[s][day]
            else:assert (s,day)==('sz159915','2021-02-08')
            assert F(got['marks'][s])==lastmarks[s]
        wealth=cash+sum(restricted.values(),F(0))+sum(receivable.values(),F(0))+sum(shares[s]*lastmarks[s] for s in shares)
        assert F(got['equity'])==wealth
        assert abs(F(got['units'])-units)<tol
        assert abs(F(dayrow['unit_nav'])-wealth/F(got['units']))<tol
        previous_nav=F(dayrow['unit_nav'])
    assert i==len(events) and len(deposits)==600 and contributions==150000
    terminal=a['terminal'];wealth=F(terminal['equity'])
    unrealized=sum(shares[s]*F(terminal['marks'][s])-sum(q*price for q,price in lots[s]) for s in shares)
    assert realized+unrealized+dividend-fees==wealth-contributions
    assert F(str(m['contributions']))==contributions and abs(F(str(m['terminal_equity']))-wealth)<F(1,10**7)
    assert F(str(m['fees']))==fees and m['buy_orders']==buycount and m['sell_orders']==sellcount
    navs=[float(x['unit_nav']) for x in a['daily']]
    returns=[navs[j]/navs[j-1]-1 for j in range(1,len(navs))]
    mean=sum(returns)/len(returns)
    vol=math.sqrt(sum((x-mean)**2 for x in returns)/len(returns)*252)
    assert abs(vol-m['annual_volatility'])<1e-12
    peak=1.0;maxdrop=0.0
    for v in navs:peak=max(peak,v);maxdrop=max(maxdrop,1-v/peak)
    assert abs(maxdrop-m['max_drawdown'])<1e-12
    rate=m['cashflow_weighted_annualized_return']
    grown=sum(float(v)*(1+rate)**((date.fromisoformat(a['end'])-date.fromisoformat(d)).days/365.25) for d,v in deposits)
    assert abs(grown-float(wealth))<1e-5
    yearprofit=sum(F(str(x['profit_after_contributions'])) for x in m['years'].values())
    assert abs(yearprofit-(wealth-contributions))<F(1,10**7)
    operations={e['day'] for e in events if e['kind'] in ('buy','sell')}
    assert len(operations)==m['operation_dates']
    mean_cash_share=sum(float(F(x['account']['free_cash'])/F(x['account']['equity'])) for x in a['daily'])/len(a['daily'])
    accepted[policy]={'account_days_checked':len(a['daily']),'money_events_checked':len(events),
       'contributions_CNY':str(contributions),'terminal_equity_CNY':str(wealth),
       'price_gain_realized_CNY':str(realized),'price_gain_unrealized_CNY':str(unrealized),
       'dividend_entitlement_CNY':str(dividend),'fees_CNY':str(fees),
       'profit_CNY':str(wealth-contributions),'attribution_equal_profit':True,
       'annual_volatility_independent':vol,'max_drawdown_independent':maxdrop,
       'cashflow_annualized_rate_residual_CNY':grown-float(wealth),
       'operation_dates':len(operations),'buy_orders':buycount,'sell_orders':sellcount,
       'mean_daily_freecash_asset_share':mean_cash_share}
out={'status':'accepted_recorded_money_and_metrics_under_frozen_conditional_method',
'result':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'device':p.stat().st_dev,
'policies':accepted,'author_policy_program_rerun':False,'additional_historical_policy_paths':0,
'independent_reconstruction':'Fraction cash and FIFO price basis from actual delivered events; original closes only for after-run acceptance',
'limitations':['Original conditional daily-price fill/clock/settlement assumptions remain','One realized history; no stable additional return or actual execution proof','Strict historical source qualification unchanged false']}
q=RAW/'complete-account-core-root-independent-readback-20261011.json';q.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
