from __future__ import annotations

import hashlib, json, math, sys
from collections import defaultdict
from pathlib import Path
import pandas as pd
import numpy as np

sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent; BASE=HERE.parent; DATA=BASE/'full-pool-preparation'
FULL=['510300','512400','515050','515130','515300','518850','588000','515170','516220','159652','512890','515880','513870','562590']
INDUSTRY=['512400','515050','515170','516220','159652','515880','562590']
SYMS=FULL; START='2020-12-01'; END='2026-06-30'; INITIAL=1_000_000.; LOT=100
CONFIGS=['equal','momentum_top3','equal_sma200','momentum_top3_sma200']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def action_fields(a):
    typ=a.get('type') or a.get('action_type')
    sym=str(a['symbol']).split('.')[0].replace('sh','').replace('sz','')
    return dict(a,symbol=sym,type=typ,event_id=a.get('event_id',f"{sym}:{typ}:{a.get('effective_date') or a.get('ex_date')}"),
      effective_date=a.get('effective_date') or a.get('ex_date'), record_date=a.get('record_date'), pay_date=a.get('pay_date'),
      cash=float(a.get('cash',a.get('cash_per_share',a.get('cash_per_unit',0))) or 0), ratio=float(a.get('ratio',a.get('split_ratio',1)) or 1))

def load():
    p=pd.read_csv(DATA/'prices.csv',dtype={'symbol':str,'date':str}); p.symbol=p.symbol.str.split('.').str[0].str.zfill(6)
    assert set(p.symbol)==set(SYMS) and not p.duplicated(['date','symbol']).any()
    for c in ['open','high','low','close','volume']: p[c]=pd.to_numeric(p[c],errors='coerce')
    raw=json.loads((DATA/'action-sources/normalized-actions.json').read_text()); acts=[action_fields(a) for a in raw['events']]
    return p.sort_values(['date','symbol']),acts

def economic_indices(p,acts):
    out=[]
    for s in SYMS:
        q=p[(p.symbol==s)&p.close.notna()& (p.close>0)].sort_values('date').copy(); prev=None
        sa=[a for a in acts if a['symbol']==s]
        vals=[]; level=1.; prevdate=None
        for _,r in q.iterrows():
            if prev is None: factor=1.
            else:
                between=sorted([a for a in sa if a['effective_date'] and prevdate<a['effective_date']<=r.date],key=lambda a:(a['effective_date'],a['event_id']))
                mult=1.; cash=0.
                for a in reversed(between):
                    if a['type']=='split': mult*=a['ratio']; cash*=a['ratio']
                    elif a['type']=='cash_dividend': cash+=a['cash']
                factor=(float(r.close)*mult+cash)/prev
            level*=factor; vals.append(level); prev=float(r.close); prevdate=r.date
        q['economic_index']=vals; q['sma200']=q.economic_index.rolling(200,min_periods=200).mean()
        q['momentum']=q.economic_index.shift(21)/q.economic_index.shift(252)-1
        rv=q.economic_index.pct_change().rolling(20).std(ddof=1)*np.sqrt(252)
        q['rv_rank']=rv.rolling(756,min_periods=252).rank(method='average',pct=True)
        q['valid_count']=np.arange(1,len(q)+1)
        out.append(q[['date','symbol','economic_index','sma200','momentum','rv_rank','valid_count']])
    return pd.concat(out,ignore_index=True)

def decisions(idx):
    piv=idx.pivot(index='date',columns='symbol'); dates=sorted(idx.date.unique()); months={}
    for d in dates:
        if d<'2020-11-01' or d>END: continue
        months[d[:7]]=d
    rows=[]
    for d in months.values():
        mom={s:piv.loc[d,('momentum',s)] if d in piv.index and ('momentum',s) in piv else np.nan for s in SYMS}
        eligible=[]
        for s in SYMS:
            if d in piv.index and ('valid_count',s) in piv and pd.notna(piv.loc[d,('valid_count',s)]) and piv.loc[d,('valid_count',s)]>=273:
                eligible.append(s)
        ranked_all=sorted([s for s in eligible if pd.notna(mom[s])],key=lambda s:(-mom[s],s))
        ranked=[s for s in ranked_all if pd.isna(piv.loc[d,('rv_rank',s)]) or piv.loc[d,('rv_rank',s)]<0.8]
        top=ranked[:3]
        for cfg in CONFIGS:
            selected=eligible if cfg.startswith('equal') else top
            weights={s:0. for s in SYMS}; reasons={}
            n=len(selected)
            for s in selected:
                if n: weights[s]=1/n
                reasons[s]='included_monthly_without_entry_sma_filter'
            rows.append(dict(config=cfg,decision_date=d,selected='|'.join(selected),ranked='|'.join(ranked),
              lookback_start='shift252',lookback_end='shift21',scores=json.dumps({s:(None if pd.isna(v) else float(v)) for s,v in mom.items()}),
              weights=json.dumps(weights),trend_states=json.dumps(reasons)))
    return rows

def blocked(bar, side, restriction=None):
    if restriction and restriction.get(f'blocks_open_{side}',False): return 'known_open_restriction'
    if bar is None: return 'missing_quote'
    get=lambda k: getattr(bar,k) if hasattr(bar,k) else bar[k]
    if not np.isfinite(get('open')) or get('open')<=0: return 'invalid_open'
    if not np.isfinite(get('volume')) or get('volume')<=0: return 'zero_volume_or_halt'
    if np.isfinite(get('high')) and np.isfinite(get('low')) and abs(get('high')-get('low'))<1e-12:
        return 'locked_one_price_limit'
    return None

def apply_split_to_account(symbol, ratio, units, last_close):
    units[symbol] *= ratio
    if symbol in last_close:
        last_close[symbol] /= ratio

def simulate(pool,cfg,fee,p,acts,idx,decs):
    aid=f'{pool}-{cfg}-fee{fee:.3f}'; bars={(r.date,r.symbol):r for r in p.itertuples(index=False)}
    quote_dates=sorted(d for d in p.date.unique() if START<=d<=END); all_dates=pd.date_range(START,END,freq='D').strftime('%Y-%m-%d').tolist()
    last_close={}; units={s:0. for s in SYMS}; cash=INITIAL; rec=0.; ent={}; dues={}; pending={}; trades=[]; orders=[]; daily=[]; events=[]; signals=[]; fees=0.
    ds={r['decision_date']:r for r in decs if r['config']==cfg}; nextq={d:next((x for x in quote_dates if x>d),None) for d in ds}
    decision_by_eligible=defaultdict(list)
    for d,r in ds.items():
        e=nextq[d]
        if e: decision_by_eligible[e].append(r)
    aeff=defaultdict(list); apay=defaultdict(list); arec=defaultdict(list); restrictions={}
    for a in acts:
        if a['effective_date']: aeff[a['effective_date']].append(a)
        if a['pay_date']: apay[a['pay_date']].append(a)
        if a['record_date']: arec[a['record_date']].append(a)
        if a['type'] in ('trading_halt','delayed_open_restriction') and a.get('halt'):
            restrictions[(a['effective_date'],a['symbol'])]=a['halt']
    idxmap={(r.date,r.symbol):r for r in idx.itertuples(index=False)}
    stop_due=defaultdict(list)
    for day in all_dates:
        # record-date entitlement is locked at close; processed after trading below
        for a in sorted(aeff[day],key=lambda x:x['event_id']):
            if a['type']=='split':
                apply_split_to_account(a['symbol'],a['ratio'],units,last_close)
                events.append(dict(account_id=aid,date=day,event_id=a['event_id'],event='split',amount=a['ratio']))
            elif a['type']=='cash_dividend':
                qty=ent.get(a['event_id'],units[a['symbol']]); amt=qty*a['cash']; dues[a['event_id']]=amt; rec+=amt
                events.append(dict(account_id=aid,date=day,event_id=a['event_id'],event='receivable',amount=amt))
        for a in apay[day]:
            amt=dues.pop(a['event_id'],0.); rec-=amt; cash+=amt; events.append(dict(account_id=aid,date=day,event_id=a['event_id'],event='cash_paid',amount=amt))
        for item in stop_due[day]:
            s=item['symbol']; pending[s]=dict(kind='stop',target_value=0.,signal_date=item['signal_date'],eligible_date=day)
        for dec in decision_by_eligible[day]:
            weights=json.loads(dec['weights']);
            for s in SYMS:
                if s in pending: orders.append(dict(account_id=aid,date=day,symbol=s,status='replaced_by_monthly',**pending[s]))
            # opening mark; missing opens use last close strictly for valuation
            eqopen=cash+rec+sum(units[s]*(getattr(bars.get((day,s)),'open',last_close.get(s,0.)) if bars.get((day,s)) else last_close.get(s,0.)) for s in SYMS)
            pending={s:dict(kind='monthly',target_value=eqopen*weights[s],signal_date=dec['decision_date'],eligible_date=day) for s in SYMS}
            signals.append(dict(account_id=aid,eligible_date=day,opening_equity=eqopen,**dec))
        # execute all sells first
        for side in ('sell','buy'):
            buy_needs=[]
            for s,o in list(pending.items()):
                b=bars.get((day,s)); reason=blocked(b,side,restrictions.get((day,s)))
                price=float(b.open) if b and reason is None else None
                current=units[s]*price if price else None
                wants_sell=price is not None and current>o['target_value']+1e-8
                wants_buy=price is not None and current<o['target_value']-price*LOT
                if reason:
                    orders.append(dict(account_id=aid,date=day,symbol=s,side=side,status='delayed',reason=reason,**o)); continue
                if side=='sell' and wants_sell:
                    target_qty=math.floor(o['target_value']/price/LOT)*LOT
                    qty=units[s]-target_qty
                    if o['target_value']==0: qty=units[s]
                    if qty>0:
                        val=qty*price; f=val*fee; cash+=val-f; units[s]-=qty; fees+=f
                        trades.append(dict(account_id=aid,date=day,symbol=s,side='sell',qty=qty,price=price,notional=val,fee=f,reason=o['kind'],signal_date=o['signal_date']))
                if side=='buy' and wants_buy: buy_needs.append((s,o,price))
            if side=='buy' and buy_needs:
                desired=[]
                for s,o,price in buy_needs:
                    qty=math.floor(max(0,o['target_value']-units[s]*price)/(price*(1+fee))/LOT)*LOT
                    desired.append((s,o,price,qty))
                need=sum(q*p0*(1+fee) for _,_,p0,q in desired); scale=min(1.,cash/need) if need else 0.
                for s,o,price,q in desired:
                    q=math.floor(q*scale/LOT)*LOT
                    if q>0:
                        val=q*price; f=val*fee; cash-=val+f; units[s]+=q; fees+=f
                        trades.append(dict(account_id=aid,date=day,symbol=s,side='buy',qty=q,price=price,notional=val,fee=f,reason=o['kind'],signal_date=o['signal_date']))
            # remove satisfied orders after both phases later
        for s,o in list(pending.items()):
            b=bars.get((day,s))
            if b and blocked(b,'buy',restrictions.get((day,s))) is None:
                # A valid execution opportunity consumes the fixed instruction.
                # Lot/cash residuals are not silently retraded every later day.
                orders.append(dict(account_id=aid,date=day,symbol=s,side='target',status='completed_or_residual',reason='',**o))
                pending.pop(s)
        for a in arec[day]: ent[a['event_id']]=units[a['symbol']]; events.append(dict(account_id=aid,date=day,event_id=a['event_id'],event='entitlement',amount=ent[a['event_id']]))
        for s in SYMS:
            b=bars.get((day,s))
            if b and np.isfinite(b.close) and b.close>0: last_close[s]=float(b.close)
        equity=cash+rec+sum(units[s]*last_close.get(s,0.) for s in SYMS); exposure=sum(units[s]*last_close.get(s,0.) for s in SYMS)/equity if equity else 0
        daily.append(dict(account_id=aid,date=day,equity=equity,cash=cash,receivable=rec,market_value=equity-cash-rec,exposure=exposure,fees=fees,**{f'units_{s}':units[s] for s in SYMS}))
        # close signal -> next valid quote per symbol, not calendar tomorrow
        if cfg.endswith('sma200'):
            for s in SYMS:
                z=idxmap.get((day,s))
                if units[s]>0 and z and pd.notna(z.sma200) and z.economic_index<z.sma200:
                    nd=next((x for x in quote_dates if x>day),None)
                    already=any(x['symbol']==s for x in stop_due.get(nd,[]))
                    if nd and not already: stop_due[nd].append({'symbol':s,'signal_date':day}); signals.append(dict(account_id=aid,config=cfg,decision_date=day,eligible_date=nd,selected=s,ranked='',lookback_start='',lookback_end='',scores='',weights='{"'+s+'":0}',trend_states='daily_below_sma200'))
    dd=min([r['equity']/max([INITIAL]+[x['equity'] for x in daily[:i+1]])-1 for i,r in enumerate(daily)])
    years=(pd.Timestamp(END)-pd.Timestamp(START)).days/365.2425; final=daily[-1]['equity']; cagr=(final/INITIAL)**(1/years)-1
    ann=[]; prev=INITIAL
    for yr,g in pd.DataFrame(daily).groupby(pd.to_datetime(pd.DataFrame(daily).date).dt.year):
        endeq=float(g.iloc[-1].equity); ann.append(dict(account_id=aid,year=int(yr),return_=endeq/prev-1,partial=(g.iloc[0].date>f'{yr}-01-01' or g.iloc[-1].date<f'{yr}-12-31'))); prev=endeq
    summary=dict(account_id=aid,config=cfg,fee=fee,initial=INITIAL,final=final,cagr=cagr,max_drawdown=dd,average_exposure=float(pd.DataFrame(daily).exposure.mean()),fees=fees,trades=len(trades),pending_end=len(pending))
    attrib=[]
    for s in SYMS:
        ts=[t for t in trades if t['symbol']==s]; ev=[e for e in events if e.get('event_id','').startswith(s)]
        buys=sum(t['notional']+t['fee'] for t in ts if t['side']=='buy'); sells=sum(t['notional']-t['fee'] for t in ts if t['side']=='sell')
        divs=sum(e['amount'] for e in ev if e['event']=='cash_paid'); endmv=units[s]*last_close.get(s,0.)
        attrib.append(dict(account_id=aid,symbol=s,buy_cash_out=buys,sell_cash_in=sells,dividend_cash=divs,end_market_value=endmv,net_pnl=sells+divs+endmv-buys,end_units=units[s]))
    return summary,daily,trades,orders,signals,events,ann,attrib

def main():
    global SYMS
    p,acts=load()
    inputs=[DATA/'prices.csv',DATA/'action-sources/normalized-actions.json',DATA/'candidate-pool.json',BASE/'full-protocol.json',BASE/'full-protocol.md',BASE/'full-protocol.sha256',Path(__file__)]
    lock={'created_before_returns':pd.Timestamp.utcnow().isoformat(),'files':{str(x):sha(x) for x in inputs}}
    lock_name='run-lock-attempt-02.json' if (HERE/'run-lock.json').exists() else 'run-lock.json'
    dump(HERE/lock_name,lock)
    alls=[]; tables=defaultdict(list)
    for pool,syms,feeset in [('full14',FULL,(.001,.002)),('industry7',INDUSTRY,(.001,))]:
      SYMS=syms; pp=p[p.symbol.isin(syms)].copy(); aa=[a for a in acts if a['symbol'] in syms]
      idx=economic_indices(pp,aa); decs=decisions(idx)
      for fee in feeset:
       for cfg in CONFIGS:
        s,*parts=simulate(pool,cfg,fee,pp,aa,idx,decs); alls.append(s)
        for k,v in zip(['equity','trades','orders','signals','actions','annual','per_symbol'],parts): tables[k]+=v
    for k,v in tables.items(): pd.DataFrame(v).to_csv(HERE/f'{k}.csv',index=False)
    pd.DataFrame(alls).to_csv(HERE/'accounts.csv',index=False)
    dump(HERE/'summary.json',{'protocol':'rotation-reconstructed-full-v1','accounts':alls})
    assert all(sha(Path(f))==h for f,h in lock['files'].items())
    dump(HERE/'post-run-verification.json',{'all_locked_files_unchanged':True,'files':lock['files']})

if __name__=='__main__': main()
