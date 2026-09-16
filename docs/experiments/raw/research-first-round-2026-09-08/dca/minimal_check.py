"""Isolated evidence audit. Runs only local files; never imports study module side effects.
External contributions enter at period-end day open, matching archived code order.
New checks are diagnostics, not a rerun or acceptance of the complete strategy.
"""
from pathlib import Path
import ast, csv, hashlib, json, platform, subprocess, sys, os
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
SOURCE_ROOT = Path('/Users/yongbiaoli/lei-signal-sync')
SRC = OUT/'snapshot/source'
CACHE = OUT/'snapshot/cache'
os.environ['LEI_TIMING_CACHE_DIR'] = str(CACHE)
sys.path.insert(0, str(SRC/'src'))
from lei_signal.timing_backtest.data import load_index_bars, load_breadth, align_index_breadth

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n')
def csvsave(name,rows):
    if rows:
        with (OUT/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def funcs(script,names,extra=None):
    tree=ast.parse(script.read_text())
    tree.body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    ns=dict(np=np,pd=pd,load_index_bars=load_index_bars,load_breadth=load_breadth,align_index_breadth=align_index_breadth)
    ns.update(extra or {})
    exec(compile(tree,str(script),'exec'),ns)
    return ns

def ledger_engine(opens,closes,w,reb,fee,ns):
    """Independent ledger preserving original holdings operations for accounting comparison."""
    idx=opens.index;n=len(idx);L=len(w);o=opens.to_numpy();c=closes.to_numpy();f=fee*1e-4
    ends=ns['period_ends'](idx,'weekly');inflow=np.zeros(n);inflow[ends]=1/len(ends)
    rdays=set(p+1 for p in ns['period_ends'](idx,reb) if p+1<n) if reb!='none' else set()
    units=np.zeros(L);cash=0.;cumulative=0.;paid=0.;rows=[];oldflows=[];flows=[];nav=1.;prev_eq=0.
    for i,d in enumerate(idx):
        open_before_deposit=float((units*o[i]).sum()+cash)
        cash+=inflow[i];cumulative+=inflow[i]
        if inflow[i]: flows.append((d,-inflow[i]))
        buy=0.;rebfee=0.
        if i and inflow[i-1]>0 and cash>0:
            buy=cash;units+=cash*w*(1-f)/o[i];paid+=cash*f;oldflows.append((d,-cash));cash=0.
        if i in rdays and L>1:
            vals=units*o[i];total=vals.sum()
            if total>0:
                rebfee=np.abs(vals-total*w).sum()*f;paid+=rebfee;units=(total-rebfee)*w/o[i]
        eq=float((units*c[i]).sum()+cash)
        # Exact unitization for archived operation order: overnight move, deposit,
        # then trades and intraday move. Contributions never become investment gain.
        if prev_eq>0: nav*=open_before_deposit/prev_eq
        if open_before_deposit+inflow[i]>0: nav*=eq/(open_before_deposit+inflow[i])
        rows.append(dict(date=str(d.date()),deposit=float(inflow[i]),cumulative_deposit=float(cumulative),buy=float(buy),rebalance_fee=float(rebfee),cash=float(cash),holdings_value=float((units*c[i]).sum()),equity=eq,unit_nav=float(nav),cumulative_fees=float(paid)))
        prev_eq=eq
    eqs=np.array([r['equity'] for r in rows]);navs=np.array([r['unit_nav'] for r in rows])
    positive=eqs>0;valid_eq=eqs[positive]
    result=dict(final=float(eqs[-1]),external_deposits=float(sum(-x[1] for x in flows)),old_recorded_debits=float(sum(-x[1] for x in oldflows)),ending_cash=float(cash),old_xirr=ns['xirr_signed'](oldflows,idx[-1],eqs[-1]),external_flow_xirr=ns['xirr_signed'](flows,idx[-1],eqs[-1]),raw_wealth_mdd=float(np.min(valid_eq/np.maximum.accumulate(valid_eq)-1)),deposit_adjusted_mdd=float(np.min(navs/np.maximum.accumulate(navs)-1)),account_identity_max_error=float(max(abs(r['equity']-r['cash']-r['holdings_value']) for r in rows)))
    return result,rows

def main():
    p13=SRC/'scripts/dca_complete_trades_study.py';p18=SRC/'scripts/dca_final_form_assembly_study.py'
    raw13=SRC/'docs/experiments/raw/dca-complete-trades-2026-09-07/dca_complete_trades_results.json'
    raw18=SRC/'docs/experiments/raw/dca-final-form-assembly-2026-09-08/final_form_assembly_results.json'
    r13=json.loads(raw13.read_text());r18=json.loads(raw18.read_text())
    summaries=[];overlaps=[]
    for key,by_sym in r13['trades'].items():
        ts=[t for xs in by_sym.values() for t in xs];rets=np.array([t['ret'] for t in ts]);olds=r13['summary'][key]
        new=dict(n=len(ts),median=float(np.median(rets)),mean=float(np.mean(rets)),win=float((rets>0).mean()),p10=float(np.percentile(rets,10)),p90=float(np.percentile(rets,90)),worst=float(min(rets)),avg_hold_months=float(np.mean([t['hold_months'] for t in ts])),forced_pct=float(np.mean([t['forced'] for t in ts])))
        summaries.append(dict(group=key,**new,max_abs_difference=max(abs(new[k]-olds[k]) for k in new)))
        for sym,ts in by_sym.items():
            ts=sorted(ts,key=lambda t:t['entry_date'])
            for a,b in zip(ts,ts[1:]):
                if b['entry_date']<=a['exit_date']:
                    overlaps.append(dict(group=key,symbol=sym,first_entry=a['entry_date'],first_exit=a['exit_date'],next_entry=b['entry_date'],next_exit=b['exit_date']))
    csvsave('round13_summary_recalculated.csv',summaries);csvsave('round13_overlapping_plans.csv',overlaps)
    ns13=funcs(p13,{'build_states','entry_events','run_trade'},dict(FEE=10.,ACCUM=252,MAX_HOLD=504,COOLDOWN=126))
    # Same function body with one causality repair only; retained as an audit comparator.
    tree=ast.parse(p13.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_trade')
    fn.name='causal_run_trade'
    class CloseLag(ast.NodeTransformer):
        def visit_Subscript(self,node):
            node=self.generic_visit(node)
            if isinstance(node.value,ast.Name) and node.value.id=='closes' and isinstance(node.slice,ast.Name) and node.slice.id=='j':
                node.slice=ast.BinOp(left=ast.Name(id='j',ctx=ast.Load()),op=ast.Sub(),right=ast.Constant(1))
            return node
    fn=CloseLag().visit(fn);mod=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));exec(compile(mod,'causal_diagnostic','exec'),ns13)
    df=ns13['build_states']('000300');pairs=[]
    for entry in ['deep20','bottom','lowtier','base']:
        for t in r13['trades'][entry+'|Xtarget'].get('000300',[]):
            e=df.index.get_loc(pd.Timestamp(t['entry_date']));old=ns13['run_trade'](df,e,'Xtarget');new=ns13['causal_run_trade'](df,e,'Xtarget');j=df.index.get_loc(pd.Timestamp(old['exit_date']))
            # Reconstruct the entire weekly accumulation cost for an explicit decision-time record.
            s=pd.Series(np.arange(len(df)),index=df.index);ends=sorted(int(v) for v in s.groupby([df.index.isocalendar().year,df.index.isocalendar().week]).max())
            buyjs=sorted(p+1 for p in ends if e<p+1<=e+252);units=sum((1/len(buyjs))*.999/df.open.iloc[k] for k in buyjs)
            pairs.append(dict(entry_type=entry,entry_date=t['entry_date'],archived_exit=t['exit_date'],rerun_exit=old['exit_date'],archived_ret=t['ret'],rerun_ret=old['ret'],matches_archive=abs(old['ret']-t['ret'])<1e-12 and old['exit_date']==t['exit_date'],old_signal_previous_close_return=float(units*df.close.iloc[j-1]-1),old_signal_same_day_close_return=float(units*df.close.iloc[j]-1),old_execution_open=float(df.open.iloc[j]),causal_exit=new['exit_date'],causal_ret=new['ret'],delta=new['ret']-old['ret'],old_forced=old['forced'],causal_forced=new['forced']))
    csvsave('round13_000300_target_paired.csv',pairs)
    assert all(p['matches_archive'] for p in pairs), 'Frozen-price baseline differs from archive; stop diagnostics'
    grids=[]
    for a,starts in r18['grid_fee10'].items():
        vals=np.array([v['xirr'] for v in starts.values()]);summary=r18['grid_summary_fee10'][a]['xirr']
        grids.append(dict(arm=a,n=len(vals),median=float(np.median(vals)),p10=float(np.quantile(vals,.1)),p90=float(np.quantile(vals,.9)),minimum=float(min(vals)),maximum=float(max(vals)),summary_max_abs_diff=float(max(abs(np.median(vals)-summary['median']),abs(np.quantile(vals,.1)-summary['p10']),abs(np.quantile(vals,.9)-summary['p90'])))))
    csvsave('round18_grid_summary_recalculated.csv',grids)
    ns18=funcs(p18,{'build_join','period_ends','xirr_signed','run_engine'})
    cases={}
    for name,start,expected in [('W5','2020-11-16',r18['reconcile_w5_fee10']),('long','2013-07-29',r18['long_window_single_path']['FQ'])]:
        o,c=ns18['build_join'](['000300','399006','518880','^IXIC'],start,'2026-08-27');orig=ns18['run_engine'](o,c,np.ones(4)/4,'quarterly',10.);new,rows=ledger_engine(o,c,np.ones(4)/4,'quarterly',10.,ns18)
        cases[name]=dict(start=str(o.index[0].date()),end=str(o.index[-1].date()),n_dates=len(o),archived=expected,original_rerun=orig,accounting_check=new,abs_rerun_final_vs_archive=abs(orig['final']-expected['final']),abs_independent_ledger_final_vs_original=abs(new['final']-orig['final']))
        assert abs(orig['final']-expected['final'])<1e-12, 'Archived baseline mismatch'
        assert abs(new['final']-orig['final'])<1e-12, 'Independent ledger changes holdings outcome'
        assert new['account_identity_max_error']<1e-10, 'Cash/asset identity mismatch'
        csvsave('round18_'+name+'_daily_ledger.csv',rows)
    ix=pd.bdate_range('2025-01-06',periods=260);flat=pd.DataFrame({'constant':np.ones(260)*100},index=ix)
    synth,rows=ledger_engine(flat,flat,np.array([1.]),'none',0.,ns18);synth['original_engine']=ns18['run_engine'](flat,flat,np.array([1.]),'none',0.)
    assert abs(synth['external_flow_xirr'])<1e-10 and abs(synth['final']-1)<1e-10
    # Deposit masks a 20% loss: E0=100, holdings fall to80, E1 includes new100.
    synth['deposit_mask_example']={'before':100.,'after_price_fall':80.,'new_deposit':100.,'reported_account_balance':180.,'raw_balance_return':.8,'investment_return_excluding_deposit':-.2}
    csvsave('flat_price_daily_ledger.csv',rows)
    result=dict(scope='摘要核算＋第13轮单标的成交时序复核＋第18轮两个单路径会计复核；不是整套回测复现',round13=dict(summary_groups=len(summaries),trade_rows=sum(x['n'] for x in summaries),unique_entries=len(set((sym,t['entry_date']) for b in r13['trades'].values() for sym,ts in b.items() for t in ts)),summary_max_abs_difference=max(x['max_abs_difference'] for x in summaries),overlap_pairs=len(overlaps),target_pairs=len(pairs),archive_matches=sum(x['matches_archive'] for x in pairs),nonforced_same_day_signals=sum(not x['old_forced'] for x in pairs),changed_exits=sum(x['causal_exit']!=x['rerun_exit'] for x in pairs),mean_paired_delta=float(np.mean([x['delta'] for x in pairs]))),round18=dict(grid=grids,cases=cases),synthetic=synth)
    save('results.json',result)
    paths=[p13,p18,raw13,raw18,OUT/'check_plan.json',OUT/'minimal_check.py',SRC/'configs/dca_evidence.json',SRC/'src/lei_signal/timing_backtest/data.py']
    paths += [SRC/'scripts'/f'dca_{s}_study.py' for s in ['entry_execution','adaptive_exits','per_target_exits','joint_policy']]
    paths += [SRC/'docs'/n for n in ['dca-master-handoff-2026-09-08.md','dca-research-handoff-2026-09-08.md']]
    paths += [CACHE/f'{s}.parquet' for s in ['000300','399006','518880','^IXIC','breadth_cn_all']]
    files=[]
    for p in paths:
        d=dict(path=str(p),sha256=sha(p),size=p.stat().st_size)
        if p.suffix=='.parquet':
            z=pd.read_parquet(p);d.update(rows=len(z),first=str(z.index.min()),last=str(z.index.max()),columns=list(z.columns))
        files.append(d)
    save('manifest.json',dict(source_repo=str(SOURCE_ROOT),snapshot_repo=str(SRC),source_commit=subprocess.check_output(['git','-C',str(SOURCE_ROOT),'rev-parse','HEAD'],text=True).strip(),source_worktree_note='关键脚本/证据账本为未跟踪文件，commit不是完整版本；逐文件sha256为本次依据。测试全部读取专属快照。',python=sys.version,numpy=np.__version__,pandas=pd.__version__,platform=platform.platform(),network_price_calls=0,files=files,outputs=[dict(path=p.name,sha256=sha(p)) for p in sorted(OUT.glob('*.csv'))]+[dict(path='results.json',sha256=sha(OUT/'results.json'))]))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
