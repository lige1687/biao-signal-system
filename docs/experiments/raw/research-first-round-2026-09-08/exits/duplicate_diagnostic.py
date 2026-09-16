"""Post-review diagnostic of duplicate append; real archived event, not a strategy test.

Selection fixed before loading prices: first CSV row with holding>=15, not tail,
and archived peak_r_at_15<=0. Compare reported-mean vs uncertainty-vector loops.
No parameter change or source edits.
"""
from pathlib import Path
import json, hashlib
import pandas as pd
ROOT=Path('/Users/yongbiaoli/lei-signal-sync')
OUT=Path(__file__).resolve().parent
cp=ROOT/'docs/experiments/raw/time_stop_tail_aware_full_pool/events_per_trade.csv'
df=pd.read_csv(cp)
r=df[(df.holding_bars>=15)&(~df.is_tail)&(df.peak_r_at_15<=0)].iloc[0].to_dict()
pp=ROOT/'docs/experiments/raw/pool-snapshot-2026-08-25'/f"{r['symbol']}.bars.parquet"
bars=pd.read_parquet(pp)
if 'date' in bars: bars=bars.set_index(pd.to_datetime(bars.date))
pos=bars.index.get_loc(pd.Timestamp(r['entry_date'])); xp=pos+15
while xp+1<len(bars) and bars.open.iloc[xp]<=bars.close.iloc[xp-1]*.905: xp+=1
price=float(bars.open.iloc[xp]); entry=float(r['entry_price']);risk=entry-float(r['stop_price'])
new=((price/entry-1)-2*max(.0005,.005/entry))*entry/risk
# Exact control-flow consequence of source lines 598-603 vs 641-643:
mean_vector=[new,float(r['r_net'])]
uncertainty_vector=[new]
out={'scope':'post-review concrete control-flow counterexample, not full strategy rerun','selected_actual_event':r,'price_source':str(pp),'exit_price_at_N15':price,'reported_mean_loop_values':mean_vector,'uncertainty_loop_values':uncertainty_vector,'same_one_opportunity':True,'reported_mean_count':len(mean_vector),'uncertainty_count':len(uncertainty_vector),'mean_delta_from_old':sum(mean_vector)/len(mean_vector)-r['r_net'],'paired_vector_delta_from_old':new-r['r_net'],'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [cp,pp,ROOT/'scripts/run_time_stop_tail_aware_full_pool.py',Path(__file__)]}}
(OUT/'duplicate_diagnostic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2,default=str))
