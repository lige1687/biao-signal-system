from pathlib import Path
import json, csv, hashlib, datetime, math
from cash_engine import simulate
ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent
SYMS=['sh510300','sz159915','sh518880','sh513100']
START='2023-01-01';END='2025-12-31'

def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
def csvout(p,rows):
    if not rows:return
    with p.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def drawdown(values,dates):
    peak=values[0];peakday=dates[0];worst=0;worst_peak=peakday;trough=peakday
    for v,d in zip(values,dates):
        if v>=peak:peak=v;peakday=d
        dd=1-v/peak if peak else 0
        if dd>worst:worst=dd;worst_peak=peakday;trough=d
    peakvalue=values[dates.index(worst_peak)]
    recover=next((d for v,d in zip(values,dates) if d>trough and v>=peakvalue),None) if worst else worst_peak
    until=recover or dates[-1]
    return dict(max_drawdown=worst,peak_date=worst_peak,trough_date=trough,recovery_date=recover,days_peak_to_recovery_or_end=(datetime.date.fromisoformat(until)-datetime.date.fromisoformat(worst_peak)).days)

def summarize(r,fee):
    daily=[d for d in r['daily'] if d['total_funding']>0]
    last=daily[-1];tr=r['trades'];nav=[1]+[d['nav'] for d in daily];dates=[START]+[d['date'] for d in daily]
    out=dict(contributed=last['total_funding'],final_equity=last['equity'],profit=last['equity']-last['total_funding'],final_cash=last['cash'],final_receivable=last['receivable'],final_holdings_value=last['assets'],hypothetical_net_liquidation=last['equity']-last['assets']*fee,fees=sum(t['fee'] for t in tr),turnover=sum(t['notional'] for t in tr),buy_count=sum(t['side']=='buy' for t in tr),sell_count=sum(t['side']=='sell' for t in tr),contribution_count=len(r['flows']),dividends_received=sum(e['amount'] for e in r['events'] if e['kind']=='dividend_paid'),cash_interest=sum(d['interest'] for d in daily),worst_loss_vs_contributions=max(0,max(1-d['equity']/d['total_funding'] for d in daily)),mean_cash_fraction=sum(d['cash']/d['equity'] for d in daily)/len(daily),nav_total_return=last['nav']-1,rebalance_count=sum(e['kind']=='rebalance' for e in r['events']),limit_deferrals=sum(e.get('reason')=='at_open_limit_conservative' for e in r['events']))
    out.update(drawdown(nav,dates));return out

def main():
    protocol=json.loads((ROOT/'protocol-lock.json').read_text())
    assert hashlib.sha256((ROOT/'protocol.md').read_bytes()).hexdigest()==protocol['protocol_sha256']
    prices={};checks=[];sources=[]
    for s in SYMS:
        path=RAW/'prices'/f'{s}-nominal.csv'
        with path.open() as f: rows=list(csv.DictReader(f))
        assert len({r['date'] for r in rows})==len(rows)
        for r in rows:
            if not START<=r['date']<=END:continue
            o,c,h,l=[float(r[k]) for k in ('open','close','high','low')]
            assert 0<l<=min(o,c)<=max(o,c)<=h
        prices[s]={r['date']:{k:float(r[k]) for k in ('open','close')} for r in rows if r['date']<=END}
        qpath=RAW.parent/'research-third-2026-09-08'/'06'/f'{s}-qfq.csv'
        with qpath.open() as f:qrows={r['date']:r for r in csv.DictReader(f)}
        window=[r for r in rows if START<=r['date']<=END]
        assert len(window)>700
        diffs=[float(r['close'])-float(qrows[r['date']]['close']) for r in window]
        if s!='sh510300':assert max(abs(x) for x in diffs)<1e-12
        checks.append(dict(symbol=s,rows=len(window),first=window[0]['date'],last=window[-1]['date'],nominal_minus_qfq_range=[min(diffs),max(diffs)],one_price_dates=[r['date'] for r in window if r['high']==r['low']]))
        sources.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    eventpath=RAW/'events/510300/events.json'
    ev=[dict(e,symbol='sh510300') for e in json.loads(eventpath.read_text())['events'] if START<=e['record_date']<=END]
    assert len(ev)==3
    for e in ev:
        assert e['announcement_date']<e['record_date']<e['ex_date']<=e['pay_date']
        path=eventpath.parent/e['source_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==e['source_sha256']
    sources.append(dict(path=str(eventpath),sha256=hashlib.sha256(eventpath.read_bytes()).hexdigest()))
    sources.append(dict(path=str(RAW/'events/other/events-and-coverage.json'),sha256=hashlib.sha256((RAW/'events/other/events-and-coverage.json').read_bytes()).hexdigest()))
    dump(ROOT/'data-checks.json',checks)
    dump(ROOT/'run-lock.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,engine_sha256=hashlib.sha256((ROOT/'cash_engine.py').read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),protocol=protocol,window=[START,END],planned_runs=12))
    configs=[('base',1000,.001,0),('budget10000',10000,.001,0),('fee1',1000,.0001,0),('cash2',1000,.001,.02)]
    summary=[]
    for cfg,weekly,fee,cash_rate in configs:
        flows=None
        for arm in ('quarterly','hold','single'):
            subset={s:p for s,p in prices.items() if arm!='single' or s=='sh510300'}
            r=simulate(subset,ev,start=START,end=END,weekly=weekly,fee=fee,cash_rate=cash_rate,rebalance=arm=='quarterly',limits={s:.2 if s=='sz159915' else .1 for s in subset})
            if flows is None:flows=r['flows']
            else:assert flows==r['flows']
            folder=ROOT/'results'/f'{cfg}-{arm}';folder.mkdir(parents=True,exist_ok=True)
            for key in ('daily','trades','flows'):csvout(folder/f'{key}.csv',r[key])
            dump(folder/'events.json',r['events'])
            row=dict(scenario=cfg,arm=arm,weekly=weekly,fee=fee,cash_rate=cash_rate,**summarize(r,fee));summary.append(row)
    dump(ROOT/'summary.json',summary);csvout(ROOT/'summary.csv',summary)
    print(json.dumps(summary[:3],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
