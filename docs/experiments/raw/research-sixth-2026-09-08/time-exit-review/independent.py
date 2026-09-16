"""Independent scalar reconstruction. Never import root audit or original run_step2."""
from pathlib import Path
import json,math,hashlib
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent;R=P.parent;D=R/'inputs/docs/experiments/raw';E=pd.read_csv(D/'time_stop_tail_aware_full_pool/events_per_trade.csv');paired=pd.read_csv(R/'time-exit-paired-ledger.csv');claim=json.loads((R/'time-exit-audit.json').read_text());locks=json.loads((R/'input-lock.json').read_text())['files']
assert not E.duplicated(['module','symbol','signal_date']).any();cache={};bad=[];used=[];fee_inference=[]
for symbol in E.symbol.unique():
 b=pd.read_parquet(D/'pool-snapshot-2026-08-25'/f'{symbol}.bars.parquet')
 if 'date' in b:b=b.set_index(pd.to_datetime(b.date))
 assert b.index.is_monotonic_increasing and not b.index.duplicated().any();cache[symbol]=b
 mask=~np.isfinite(b[['open','high','low','close']].to_numpy()).all(axis=1)
 for day in b.index[mask]:bad.append({'symbol':symbol,'date':str(day.date()),'fields':[c for c in ['open','high','low','close'] if not math.isfinite(b.at[day,c])]})
for e in E.itertuples(index=False):
 b=cache[e.symbol];j=b.index.get_loc(pd.Timestamp(e.entry_date));q=b.index.get_loc(pd.Timestamp(e.exit_date));last=max(j+14,q);arr=b[['open','high','low','close']].iloc[j:last+1].to_numpy();assert np.isfinite(arr).all();risk=e.entry_price-e.stop_price;assert risk>0
 for k in [5,10,15]:assert abs((b.close.iloc[j+k-1]-e.entry_price)/risk-getattr(e,f'r_at_{k}'))<1e-9
 used.append(dict(symbol=e.symbol,signal_date=e.signal_date,first=str(b.index[j].date()),last=str(b.index[last].date())))
 # Diagnostic implied fee ONLY if baseline exited at frozen open; not a fee change.
 gross=(float(b.open.iloc[q])-e.entry_price);implied=(gross-e.r_net*risk)/(2*e.entry_price)*10000
 fee_inference.append(dict(symbol=e.symbol,module=e.module,signal_date=e.signal_date,implied_one_side_bps=implied,legacy_replacement_one_side_bps=max(5,50/e.entry_price)))
a=E[E.holding_bars>=10];assert len(a)==899;trace=[];groups=[]
for kind,N,threshold in [('plain',15,None),('plain',20,None),('conditional',15,0.),('conditional',20,0.),('conditional',15,.5),('conditional',20,.5)]:
 arm=f'plain_{N}' if kind=='plain' else f'conditional_{threshold}_{N}';rows=[];old_entries=[]
 for e in a.itertuples(index=False):
  b=cache[e.symbol];j=b.index.get_loc(pd.Timestamp(e.entry_date));ep=float(e.entry_price);risk=ep-float(e.stop_price);decision=None;xp=None;fillidx=None;side=None;candidate=False;read_positions=[];guard_future_close=False;skipped=0
  if e.holding_bars>=N:
   decision=j+N-1
   if kind=='plain':
    candidate=all(float(b.close.iloc[v])<=ep for v in range(j,j+N));read_positions.extend(range(j,j+N))
   else:
    candidate=(float(b.close.iloc[j+9])-ep)/risk<=threshold and (float(b.close.iloc[decision])-ep)/risk<=threshold;read_positions.extend([j+9,decision])
  if candidate:
   if e.symbol.endswith('.SS') or e.symbol.endswith('.SZ'):
    trial=j+N
    if trial<len(b):
     # Match original expression/order exactly; record its future-close dependency.
     while trial+1<len(b):
      read_positions.extend([trial,trial-1]);guard_future_close=True
      if float(b.close.iloc[trial])<=0:break
      if float(b.open.iloc[trial])>float(b.close.iloc[trial-1])*.905:break
      trial+=1;skipped+=1
     fillidx=trial;xp=float(b.open.iloc[trial]);side='open';read_positions.append(trial)
   else:
    fillidx=decision;xp=float(b.close.iloc[decision]);side='same_close';read_positions.append(decision)
  triggered=xp is not None
  if triggered:
   assert math.isfinite(xp);loss_cost=max(ep*.0005,.005)*2;value=(xp-ep-loss_cost)/risk;date=str(b.index[fillidx].date())
  else:value=float(e.r_net);date=e.exit_date
  duplicate=triggered and kind=='plain' and not e.is_tail
  old_entries.append(value)
  if duplicate:old_entries.append(float(e.r_net))
  for pos in read_positions:assert np.isfinite(b[['open','close']].iloc[pos].to_numpy()).all()
  row=dict(arm=arm,module=e.module,symbol=e.symbol,signal_date=e.signal_date,triggered=triggered,duplicate=duplicate,new_r=value,new_exit_date=date,base_r=float(e.r_net),same_close=side=='same_close',guard_reads_future_close=guard_future_close,skipped_opens=skipped,fill_after_baseline=triggered and date>e.exit_date,last_row_restricted=triggered and side=='open' and fillidx==len(b)-1 and xp<=float(b.close.iloc[fillidx-1])*.905)
  obs=paired[(paired.arm==arm)&(paired.module==e.module)&(paired.symbol==e.symbol)&(paired.signal_date==e.signal_date)];assert len(obs)==1;v=obs.iloc[0];row['matches_root']=bool(triggered==v.triggered and duplicate==v.old_duplicate_append and abs(value-v.new_r)<1e-9 and date==v.new_exit_date);rows.append(row);trace.append(row)
 baseline=float(a.r_net.mean());mean=math.fsum(x['new_r'] for x in rows)/len(rows);original=math.fsum(old_entries)/len(old_entries);c=next(x for x in claim['cells'] if x['arm']==arm)
 groups.append(dict(arm=arm,n=len(rows),triggers=sum(x['triggered'] for x in rows),duplicates=sum(x['duplicate'] for x in rows),old_length=len(old_entries),old_mean=original,corrected_mean=mean,corrected_delta=mean-baseline,root_mean_error=mean-c['corrected_mean_r'],all_rows_match_root=all(x['matches_root'] for x in rows),same_close_fills=sum(x['same_close'] for x in rows),guard_future_close_reads=sum(x['guard_reads_future_close'] for x in rows),skipped_opens=sum(x['skipped_opens'] for x in rows),fills_after_baseline=sum(x['fill_after_baseline'] for x in rows),last_row_restricted_fills=sum(x['last_row_restricted'] for x in rows)))
pd.DataFrame(trace).to_csv(P/'independent-ledger.csv',index=False,float_format='%.17g');pd.DataFrame(fee_inference).to_csv(P/'baseline-fee-diagnostic.csv',index=False,float_format='%.17g');fi=pd.DataFrame(fee_inference);fd=fi[abs(fi.implied_one_side_bps-fi.legacy_replacement_one_side_bps)>1e-7];bad_intersects=[dict(b,affected=[x for x in used if x['symbol']==b['symbol'] and x['first']<=b['date']<=x['last']]) for b in bad]
result=dict(events=len(E),alive=len(a),independently_compared_rows=len(trace),base_mean=float(a.r_net.mean()),cells=groups,nonfinite=bad_intersects,max_used_legacy_window=max(x['last'] for x in used),fee_diagnostic={'assumption':'Baseline exit price equals frozen open on its recorded exit day; inferred from r_net, not fetched broker fees.','events_mismatch_replacement_fee':len(fd),'events_total':len(fi),'implied_rounded_counts':{str(k):int(v) for k,v in fi.implied_one_side_bps.round(6).value_counts().head(10).items()},'max_abs_implied_bps_diff':float(abs(fi.implied_one_side_bps-fi.legacy_replacement_one_side_bps).max())},inputs_unchanged=all(hashlib.sha256(Path(x['snapshot_path']).read_bytes()).hexdigest()==x['sha256'] for x in locks))
(P/'independent-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
