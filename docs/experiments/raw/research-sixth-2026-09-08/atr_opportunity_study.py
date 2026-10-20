"""Fixed 0.5 ATR mechanism comparison on frozen opportunities, never a portfolio."""
from pathlib import Path
import hashlib, json, math, socket, sys
import numpy as np
import pandas as pd

P=Path(__file__).resolve().parent
I=P/'full-baseline-review/inputs'
RUNS=[('A','20260831-231254-88cb12.json'),('B','20260831-231715-1bb6f2.json'),('C','20260831-231944-b87a6b.json')]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def offline(*a,**kw): raise RuntimeError('Offline research')
socket.create_connection=offline; socket.socket.connect=offline
sys.dont_write_bytecode=True

def prepare(b):
    b=b.copy(); b.index=pd.to_datetime(b.index)
    assert b.index.is_monotonic_increasing and not b.index.duplicated().any()
    a=b.close.to_numpy(float); ema=np.full(len(a),np.nan)
    if len(a)>=20:
        ema[19]=np.mean(a[:20])
        for i in range(20,len(a)): ema[i]=a[i]*2/21+ema[i-1]*19/21
    prev=b.close.shift(1)
    tr=pd.concat([b.high-b.low,(b.high-prev).abs(),(b.low-prev).abs()],axis=1).max(axis=1)
    tr.iloc[0]=np.nan
    b['atr20']=tr.rolling(20,min_periods=20).mean(); b['ema20']=ema
    b['trend_exit']=(b.close<b.ema20)&(b.close<b.close.shift(20))
    return b

def exit_path(b, entry_pos, stop, cn):
    for j in range(entry_pos,len(b)):
        close=float(b.close.iloc[j])
        if not math.isfinite(close):
            return {'closed':False,'exit_pos':None,'reason':'missing_close_no_execution'}
        reason='structure_stop_C' if close<stop else 'exit_a6_1_costbasis' if b.trend_exit.iloc[j] else None
        if reason:
            k=j+1
            while k<len(b):
                xp=float(b.open.iloc[k]); prev=float(b.close.iloc[k-1])
                if not math.isfinite(xp) or not math.isfinite(prev):
                    return {'closed':False,'exit_pos':None,'reason':'missing_next_open_no_execution'}
                if cn and prev>0 and xp<=prev*.905: k+=1
                else: return {'closed':True,'exit_pos':k,'reason':reason}
            return {'closed':False,'exit_pos':None,'reason':reason+'(数据末尾未执行)'}
    return {'closed':False,'exit_pos':None,'reason':'open_at_end'}

def account(ep, stop, price, minimum_close, closed, fee, sizing):
    buy_rate=max(.0005,.005/ep) if fee=='legacy' else .0005 if fee=='amount_5bp' else .001
    qmax=1/(ep*(1+buy_rate))
    q=qmax if sizing=='same_budget' else min(qmax,.01/(ep-stop))
    cash=1-q*ep*(1+buy_rate)
    sell_cost=(q*ep*buy_rate if fee=='legacy' else q*price*buy_rate) if closed else 0
    end=cash+q*price-sell_cost
    return {'budget_return':end-1,'quantity_proxy':q,'cash_after_entry':cash,'position_fraction':q*ep,'planned_loss_fraction':q*(ep-stop),'fees_fraction':q*ep*buy_rate+sell_cost,'minimum_budget_return':min(cash+q*minimum_close-1,end-1,0.)}

def main():
    lock=json.loads((P/'atr-protocol-lock.json').read_text()); assert sha(P/'atr-protocol.md')==lock['sha256']
    manifest=json.loads((P/'full-baseline-review/input-manifest.json').read_text())
    # Input names are resolved from the frozen source manifest, never live prices.
    mapping={}
    for x in manifest['files']:
        source=x.get('source_path',x.get('source'))
        frozen=x.get('snapshot_path',x.get('frozen_path',x.get('copy_path')))
        if frozen is None and 'copy' in x: frozen=str(P/'full-baseline-review'/x['copy'])
        if frozen is None: frozen=str(I/x.get('relative_path',x.get('relative','')))
        fp=Path(frozen)
        assert fp.is_file(), x
        assert sha(fp)==x['sha256'], x
        mapping[source]=fp
    def find(suffix):
        found=[v for k,v in mapping.items() if k.endswith(suffix)]
        assert len(found)==1,(suffix,found)
        return found[0]
    raw=[]
    for mod,name in RUNS:
        d=json.loads(find('/'+name).read_text())
        raw += [dict(t,module=mod,source_row=i) for i,t in enumerate(d['trades'])]
    assert len(raw)==2309
    bcache={s:prepare(pd.read_parquet(find('/'+s+'.bars.parquet'))) for s in sorted({r['symbol'] for r in raw})}
    # Preflight all completed trades before evaluating any candidate path.
    verified_closed=0; preflight_errors=[]
    for e in raw:
        if e.get('r_net') is None or e['exit_reason']=='invalid_nonpositive_risk': continue
        b=bcache[e['symbol']]; p=int(b.index.get_loc(pd.Timestamp(e['signal_date'])))+1
        ep=float(b.open.iloc[p]); stop=float(e['stop_price'])
        cn=e['symbol'].endswith(('.SS','.SZ')) and not e['symbol'].startswith('TH')
        v=exit_path(b,p,stop,cn)
        xp=float(b.open.iloc[v['exit_pos']]) if v['closed'] else None
        rn=(xp-ep-2*max(.0005,.005/ep)*ep)/(ep-stop) if xp is not None else None
        good=v['closed'] and str(b.index[v['exit_pos']].date())==e['exit_date'] and v['reason']==e['exit_reason'] and math.isclose(rn,e['r_net'],abs_tol=1e-8)
        if good: verified_closed+=1
        else: preflight_errors.append({'module':e['module'],'symbol':e['symbol'],'signal_date':e['signal_date'],'new':v,'new_r':rn})
    (P/'atr-preflight.json').write_text(json.dumps({'verified_closed':verified_closed,'errors':preflight_errors,'independent_audit':'full-baseline-review/summary.json; MSFT tail missing explicitly retained'},indent=2)+'\n')
    assert verified_closed==2245 and not preflight_errors,'Baseline preflight failed before candidate evaluation'
    details=[]; opportunities=[]; base_mismatches=[]
    for e in raw:
        b=bcache[e['symbol']]; s=int(b.index.get_loc(pd.Timestamp(e['signal_date']))); p=s+1
        key=f"{e['module']}:{e['source_row']}:{e['symbol']}:{e['signal_date']}"
        cn=e['symbol'].endswith(('.SS','.SZ')) and not e['symbol'].startswith('TH')
        stop=float(e['stop_price']); ref=float(b.close.iloc[s]); atr=float(b.atr20.iloc[s])
        ep=float(b.open.iloc[p]) if p<len(b) else None
        invalid='signal_at_end_not_entered' if ep is None else 'missing_entry_price' if not math.isfinite(ep) else 'skipped_limit_up_at_entry' if cn and ep>=ref*1.095 else 'invalid_nonpositive_risk' if ep<=stop else None
        rr=(float(e['target_price'])-ref)/(ref-stop) if e.get('target_price') is not None and ref>stop else None
        valid_atr=math.isfinite(atr) and atr>0 and stop-.5*atr>0
        ns=stop-.5*atr if valid_atr else stop
        nrr=(float(e['target_price'])-ref)/(ref-ns) if e.get('target_price') is not None and ref>ns else None
        base=exit_path(b,p,stop,cn) if invalid is None else None
        buffered=exit_path(b,p,ns,cn) if invalid is None and valid_atr else base
        if base and e.get('r_net') is not None:
            xp=float(b.open.iloc[base['exit_pos']]) if base['closed'] else None
            rn=(xp-ep-2*max(.0005,.005/ep)*ep)/(ep-stop) if xp is not None else None
            good=base['closed'] and str(b.index[base['exit_pos']].date())==e['exit_date'] and base['reason']==e['exit_reason'] and math.isclose(rn,e['r_net'],abs_tol=1e-8)
            if not good: base_mismatches.append({'key':key,'old':e,'new':base,'recalculated_r':rn})
        opportunities.append({'key':key,'module':e['module'],'symbol':e['symbol'],'signal_date':e['signal_date'],'invalid':invalid,'atr20':atr if math.isfinite(atr) else None,'atr_buffer_applicable':valid_atr,'reference_rr':rr,'buffered_rr':nrr,'base_admitted_rr3':rr is not None and rr>=3,'buffer_admitted_rr3':valid_atr and nrr is not None and nrr>=3})
        last=int(np.where(np.isfinite(b.close.to_numpy(float)))[0][-1])
        for arm in ('base','buffer','base_rr3','buffer_rr3'):
            isbuffer=arm.startswith('buffer'); discipline=arm.endswith('rr3')
            astop=ns if isbuffer else stop; ar=nrr if isbuffer else rr
            rejection=invalid or ('atr_missing_or_nonpositive_stop' if discipline and isbuffer and not valid_atr else None) or ('rr_below3_or_no_target' if discipline and (ar is None or ar<3) else None)
            path=buffered if isbuffer else base
            common={'key':key,'module':e['module'],'symbol':e['symbol'],'signal_date':e['signal_date'],'arm':arm,'rejection':rejection,'applied_buffer':isbuffer and valid_atr and not rejection,'structure_distance_atr_group':'below_1' if valid_atr and (ref-stop)/atr<1 else 'at_least_1' if valid_atr else 'unavailable'}
            if rejection:
                for fee in ('legacy','amount_5bp','amount_10bp'):
                    for sizing in ('same_budget','same_planned_risk'):
                        details.append(dict(common,fee=fee,sizing=sizing,entered=False,closed=False,holding_bars=0,budget_return=0.,minimum_budget_return=0.,position_fraction=0.,planned_loss_fraction=0.,cash_after_entry=1.,fees_fraction=0.))
                continue
            k=path['exit_pos'] if path['closed'] else last
            assert k>=p and ep>0 and astop>0,(key,ep,astop)
            terminal=float(b.open.iloc[k]) if path['closed'] else float(b.close.iloc[k])
            prices=b.close.iloc[p:k if path['closed'] else k+1].to_numpy(float)
            assert np.isfinite(prices).all(),key
            low=min(ep,terminal,float(prices.min()) if len(prices) else ep)
            for fee in ('legacy','amount_5bp','amount_10bp'):
                for sizing in ('same_budget','same_planned_risk'):
                    a=account(ep,astop,terminal,low,path['closed'],fee,sizing)
                    details.append(dict(common,fee=fee,sizing=sizing,entered=True,closed=path['closed'],entry_date=str(b.index[p].date()),entry_price=ep,stop_price=astop,exit_date=str(b.index[k].date()) if path['closed'] else None,valuation_date=str(b.index[k].date()),terminal_price=terminal,exit_reason=path['reason'],holding_bars=k-p,**a))
    (P/'atr-baseline-check.json').write_text(json.dumps({'n':len(raw),'mismatches':base_mismatches},ensure_ascii=False,indent=2,default=str)+'\n')
    if base_mismatches: raise RuntimeError('Baseline mismatch, do not publish candidate results')
    d=pd.DataFrame(details); assert len(d)==2309*24
    assert not d.duplicated(['key','arm','fee','sizing']).any()
    d.to_csv(P/'atr-opportunity-ledger.csv',index=False)
    pd.DataFrame(opportunities).to_csv(P/'atr-opportunity-inventory.csv',index=False)
    stats=[]
    for (arm,fee,sizing,mod),g in d.groupby(['arm','fee','sizing','module']):
        stats.append({'arm':arm,'fee':fee,'sizing':sizing,'module':mod,'opportunities':len(g),'entered':int(g.entered.sum()),'closed':int(g.closed.sum()),'mean_budget_return':float(g.budget_return.mean()),'median_budget_return':float(g.budget_return.median()),'worst_budget_return':float(g.budget_return.min()),'p05_budget_return':float(g.budget_return.quantile(.05)),'mean_minimum_budget_return':float(g.minimum_budget_return.mean()),'worst_minimum_budget_return':float(g.minimum_budget_return.min()),'mean_holding_bars':float(g.holding_bars.mean()),'mean_position_fraction':float(g.position_fraction.mean()),'mean_fees_fraction':float(g.fees_fraction.mean())})
    result={'opportunities':len(raw),'ledger_rows':len(d),'views':24,'baseline_closed_all_match':True,'stats':stats,'protocol_sha256':sha(P/'atr-protocol.md'),'code_sha256':sha(Path(__file__)),'ledger_sha256':sha(P/'atr-opportunity-ledger.csv'),'limitations':['independent opportunity budgets, not a shared portfolio','historically selected universe and opportunity list','adjusted-price proxies, legacy execution restrictions','no newly untouched history, no evidence of future advantage']}
    (P/'atr-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='stats'},indent=2))

if __name__=='__main__': main()
