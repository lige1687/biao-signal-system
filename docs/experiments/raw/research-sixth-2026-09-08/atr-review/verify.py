"""Independent raw-input, scalar-path and conservation review. No root functions imported."""
from pathlib import Path
import json,hashlib,math,itertools
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent;R=P.parent;S=P/'root-snapshot';S.mkdir(exist_ok=True)
roots=['atr-protocol.md','atr-protocol-lock.json','atr_opportunity_study.py','atr-opportunity-inventory.csv','atr-opportunity-ledger.csv','atr-results.json','atr-preflight.json']
reviewinputs=[]
for name in roots:
 f=R/name;b=f.read_bytes();target=S/name
 if target.exists():assert target.read_bytes()==b,'Root artifact changed; preserve prior review snapshot'
 else:target.write_bytes(b)
 reviewinputs.append(dict(file=name,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
M=json.loads((R/'full-baseline-review/input-manifest.json').read_text());lookup={Path(x['source']).name:R/'full-baseline-review'/x['copy'] for x in M['files']};assert all(hashlib.sha256((R/'full-baseline-review'/x['copy']).read_bytes()).hexdigest()==x['sha256'] for x in M['files'])
D=pd.read_csv(S/'atr-opportunity-ledger.csv');V=pd.read_csv(S/'atr-opportunity-inventory.csv').set_index('key');out=json.loads((S/'atr-results.json').read_text());raw={};cache={};facts=[];paths=[];mismatches=[]
for mod,file in [('A','20260831-231254-88cb12.json'),('B','20260831-231715-1bb6f2.json'),('C','20260831-231944-b87a6b.json')]:
 for i,e in enumerate(json.loads(lookup[file].read_text())['trades']):raw[f'{mod}:{i}:{e["symbol"]}:{e["signal_date"]}']=dict(e,module=mod)
assert len(raw)==2309 and set(D.key)==set(raw)==set(V.index)
expected=set(itertools.product(['base','buffer','base_rr3','buffer_rr3'],['legacy','amount_5bp','amount_10bp'],['same_budget','same_planned_risk']))
for key,df in D.groupby('key'):assert set(zip(df.arm,df.fee,df.sizing))==expected and len(df)==24
for sym in {e['symbol'] for e in raw.values()}:
 b=pd.read_parquet(lookup[sym+'.bars.parquet']);b.index=pd.to_datetime(b.index);assert b.index.is_monotonic_increasing and not b.index.duplicated().any();cache[sym]=b
thin=D[(D.fee=='amount_5bp')&(D.sizing=='same_budget')];B=thin[thin.arm=='base'].set_index('key');C=thin[thin.arm=='buffer'].set_index('key');changed={k for k in raw if (str(B.loc[k].exit_date)!=str(C.loc[k].exit_date) or str(B.loc[k].exit_reason)!=str(C.loc[k].exit_reason))};checkpaths=changed|{k for k,e in raw.items() if e['symbol']=='MSFT' and B.loc[k].entered and not B.loc[k].closed};ema={}
for key,e in raw.items():
 b=cache[e['symbol']];s=b.index.get_loc(pd.Timestamp(e['signal_date']));j=s+1;ref=float(b.close.iloc[s]);stop=float(e['stop_price']);tr=[]
 for z in range(s-19,s+1):
  if z<1:tr.append(float('nan'));continue
  hi=float(b.high.iloc[z]);lo=float(b.low.iloc[z]);pc=float(b.close.iloc[z-1]);tr.append(max(hi-lo,abs(hi-pc),abs(lo-pc)))
 atr=math.fsum(tr)/20 if all(math.isfinite(x) for x in tr) else float('nan');assert abs(atr-V.loc[key].atr20)<1e-9
 ep=float(b.open.iloc[j]) if j<len(b) else None;cn=e['symbol'].endswith(('.SZ','.SS')) and not e['symbol'].startswith('TH');inv='signal_at_end_not_entered' if ep is None else 'missing_entry_price' if not math.isfinite(ep) else 'skipped_limit_up_at_entry' if cn and ep>=ref*1.095 else 'invalid_nonpositive_risk' if ep<=stop else None
 valid=math.isfinite(atr) and atr>0 and stop-.5*atr>0;ns=stop-.5*atr if valid else stop;rr=(float(e['target_price'])-ref)/(ref-stop) if e.get('target_price') is not None and ref>stop else None;nrr=(float(e['target_price'])-ref)/(ref-ns) if e.get('target_price') is not None and ref>ns else None
 assert str(inv) == ('None' if pd.isna(V.loc[key].invalid) else str(V.loc[key].invalid));assert valid==V.loc[key].atr_buffer_applicable
 for arm,ast,ratio in [('base',stop,rr),('buffer',ns,nrr),('base_rr3',stop,rr),('buffer_rr3',ns,nrr)]:
  r=thin[(thin.key==key)&(thin.arm==arm)].iloc[0];accept=(inv is None and (not arm.endswith('rr3') or (ratio is not None and ratio>=3)) and (arm!='buffer_rr3' or valid));assert bool(r.entered)==accept
  if accept:assert abs(r.stop_price-ast)<1e-9
  if ratio is not None:
   vi=V.loc[key].buffered_rr if arm.startswith('buffer') else V.loc[key].reference_rr;assert abs(ratio-vi)<1e-8
 facts.append(dict(key=key,atr20=atr,invalid=inv,rr=rr,buffer_rr=nrr,base_entered=bool(B.loc[key].entered),buffer_entered=bool(C.loc[key].entered)))
 if key not in checkpaths:continue
 sym=e['symbol']
 if sym not in ema:
  a=[float(x) for x in b.close];line=[float('nan')]*len(a);line[19]=sum(a[:20])/20
  for z in range(20,len(a)):line[z]=(2*a[z]+19*line[z-1])/21
  ema[sym]=line
 for arm,threshold in [('base',stop),('buffer',ns)]:
  found=None;cause='open_at_end';confirm=None;skips=[]
  for z in range(j,len(b)):
   price=float(b.close.iloc[z])
   if not math.isfinite(price):cause='missing_close_no_execution';break
   trend=(price<ema[sym][z] and z>=20 and price<float(b.close.iloc[z-20]))
   why='structure_stop_C' if price<threshold else 'exit_a6_1_costbasis' if trend else None
   if why is None:continue
   confirm=z;cause=why+'(数据末尾未执行)'
   for q in range(z+1,len(b)):
    op=float(b.open.iloc[q]);previous=float(b.close.iloc[q-1])
    if not math.isfinite(op) or not math.isfinite(previous):cause='missing_next_open_no_execution';break
    if cn and previous>0 and op<=previous*.905:skips.append(str(b.index[q].date()));continue
    found=q;cause=why;break
   break
  r=B.loc[key] if arm=='base' else C.loc[key];isclosed=found is not None
  last=found if isclosed else max(z for z,x in enumerate(b.close) if math.isfinite(x));terminal=float(b.open.iloc[last] if isclosed else b.close.iloc[last]);xd=str(b.index[last].date()) if isclosed else None;match=(isclosed==bool(r.closed) and (str(xd)==('None' if pd.isna(r.exit_date) else str(r.exit_date))) and cause==r.exit_reason and abs(terminal-r.terminal_price)<1e-9 and str(b.index[last].date())==r.valuation_date)
  if not match:mismatches.append(dict(key=key,arm=arm,cause=cause,exit=xd,terminal=terminal,root=r.to_dict()))
  paths.append(dict(key=key,arm=arm,stop=threshold,signal_atr=atr,closed=isclosed,reason=cause,signal_exit_date=str(b.index[confirm].date()) if confirm is not None else None,exit_date=xd,valuation_date=str(b.index[last].date()),terminal=terminal,skipped_dates=skips,matches=match))
assert not mismatches,mismatches[:2]
# Independent accounting from published fills, not account() or copied arithmetic implementation.
entered=D[D.entered].copy();rejected=D[~D.entered].copy();ep=entered.entry_price.to_numpy();st=entered.stop_price.to_numpy();px=entered.terminal_price.to_numpy();closed=entered.closed.to_numpy();rate=np.where(entered.fee=='legacy',np.maximum(.0005,.005/ep),np.where(entered.fee=='amount_5bp',.0005,.001));riskunits=.01/(ep-st);fullunits=1/(ep*(1+rate));units=np.where(entered.sizing=='same_budget',fullunits,np.minimum(fullunits,riskunits));buy=units*ep*rate;sell=np.where(closed,np.where(entered.fee=='legacy',units*ep*rate,units*px*rate),0.);remaining=1-units*ep-buy;wealth=remaining+units*px-sell
errors={field:float(np.max(abs(calc-entered[field].to_numpy()))) for field,calc in [('quantity_proxy',units),('cash_after_entry',remaining),('position_fraction',units*ep),('planned_loss_fraction',units*(ep-st)),('fees_fraction',buy+sell),('budget_return',wealth-1)]};assert max(errors.values())<1e-9;assert remaining.min()>-1e-12;assert np.max(abs(remaining+units*ep+buy-1))<1e-12
assert (rejected.cash_after_entry==1).all() and (rejected.budget_return==0).all() and (rejected.position_fraction==0).all() and (rejected.fees_fraction==0).all();assert (entered.loc[entered.sizing=='same_planned_risk','planned_loss_fraction']<=.01+1e-12).all()
# Rebuild each minimum from raw closes to the already independently checked or baseline-audited fill.
mins={}
for r in thin[thin.entered].itertuples():
 b=cache[r.symbol];j=b.index.get_loc(pd.Timestamp(r.entry_date));k=b.index.get_loc(pd.Timestamp(r.valuation_date));sl=b.close.iloc[j:k if r.closed else k+1].to_list();assert all(math.isfinite(x) for x in sl);mins[r.key,r.arm]=min([r.entry_price,r.terminal_price]+sl)
computed_low=[]
for row,u,cash,end in zip(entered.itertuples(),units,remaining,wealth):computed_low.append(min(0.,cash+u*mins[row.key,row.arm]-1,end-1))
errors['minimum_budget_return']=float(np.max(abs(np.array(computed_low)-entered.minimum_budget_return.to_numpy())));assert errors['minimum_budget_return']<1e-9
# Conditional arms must be either cash or exactly the corresponding admitted full path.
for arm,parent in [('base_rr3','base'),('buffer_rr3','buffer')]:
 x=D[(D.arm==arm)&D.entered].set_index(['key','fee','sizing']);y=D[D.arm==parent].set_index(['key','fee','sizing']).loc[x.index]
 for f in ['budget_return','terminal_price','fees_fraction','cash_after_entry','minimum_budget_return']:assert np.max(abs(x[f]-y[f]))<1e-9
sets={arm:set(thin[(thin.arm==arm)&thin.entered].key) for arm in ['base','buffer','base_rr3','buffer_rr3']};assert sets['base']==sets['buffer'];assert sets['buffer_rr3']<=sets['base_rr3']<=sets['base']
# Check numerical group summaries independently from ledger rows, with total budgets including cash.
stats_errors=[]
for stt in out['stats']:
 g=D[(D.arm==stt['arm'])&(D.fee==stt['fee'])&(D.sizing==stt['sizing'])&(D.module==stt['module'])]
 for k,c in [('opportunities',len(g)),('entered',int(g.entered.sum())),('closed',int(g.closed.sum())),('mean_budget_return',float(g.budget_return.mean())),('worst_budget_return',float(g.budget_return.min())),('median_budget_return',float(g.budget_return.median())),('p05_budget_return',float(g.budget_return.quantile(.05))),('mean_minimum_budget_return',float(g.minimum_budget_return.mean())),('worst_minimum_budget_return',float(g.minimum_budget_return.min())),('mean_holding_bars',float(g.holding_bars.mean())),('mean_position_fraction',float(g.position_fraction.mean())),('mean_fees_fraction',float(g.fees_fraction.mean()))]:
  if abs(stt[k]-c)>1e-9:stats_errors.append(dict(cell=stt,key=k,independent=c))
assert not stats_errors
pd.DataFrame(paths).to_csv(P/'changed-paths.csv',index=False,float_format='%.17g');pd.DataFrame(facts).to_csv(P/'opportunity-checks.csv',index=False,float_format='%.17g');(P/'reviewed-inputs.json').write_text(json.dumps(reviewinputs,indent=2))
report=dict(opportunities=len(raw),all_views=len(D),views_per_opportunity=24,all_identifiers_retained=True,independent_atr_all_opportunities=True,changed_paths_opportunities=len(changed),independently_rebuilt_path_count=len(paths),all_changed_paths_match=True,admitted_counts={k:len(v) for k,v in sets.items()},accounting_max_errors=errors,cash_minimum=float(remaining.min()),no_unexecuted_sell_fee=True,all_admitted_filtered_paths_equal_unfiltered=True,buffer_filter_subset_of_base_filter=True,group_summaries_match=True,buffer_flag_on_rejected_rows=int((D.applied_buffer&~D.entered).sum()),msft_pending_rows=thin[(thin.symbol=='MSFT')&thin.entered&~thin.closed].to_dict('records'),source_inputs_still_unchanged=all(hashlib.sha256((R/'full-baseline-review'/x['copy']).read_bytes()).hexdigest()==x['sha256'] for x in M['files']))
def json_safe(x):
 if isinstance(x,float) and not math.isfinite(x):return None
 if isinstance(x,dict):return {k:json_safe(v) for k,v in x.items()}
 if isinstance(x,list):return [json_safe(v) for v in x]
 return x
report=json_safe(report)
(P/'independent-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str,allow_nan=False));print(json.dumps(report,ensure_ascii=False,default=str,allow_nan=False))
