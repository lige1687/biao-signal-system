from pathlib import Path
import pandas as pd, csv, json, hashlib
ROOT=Path(__file__).resolve().parents[5]
OLD=ROOT/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09'
BARS=ROOT/'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/bars'
OUT=Path(__file__).resolve().parent
start,end=pd.Timestamp('2018-07-05'),pd.Timestamp('2026-06-30')
rows=[]
def add(group,metric,value,detail=''):rows.append({'group':group,'metric':metric,'value':value,'detail':detail})
widths={n:pd.read_parquet(OLD/f'prepared/breadth_{n}.parquet') for n in ['all_a','csi300']}
for n,d in widths.items():
 add(n,'stored_rows',len(d));add(n,'unique_dates',d.index.nunique());add(n,'first_date',d.index.min().date());add(n,'last_date',d.index.max().date())
 q=d.loc[start:end];add(n,'main_rows',len(q));add(n,'main_valid',int(q.valid.sum()));add(n,'main_invalid',int((~q.valid).sum()));add(n,'main_2021_rows',len(q.loc['2021']));add(n,'main_2021_invalid',int((~q.loc['2021'].valid).sum()))
 pre=d.loc[:start-pd.Timedelta(days=1)];add(n,'controller_pre_main_rows',len(pre));add(n,'controller_pre_main_valid',int(pre.valid.sum()));add(n,'controller_pre_main_invalid',int((~pre.valid).sum()),'stored pre-main segment, 2014-12-01 through 2018-07-04')
 add(n,'minimum_coverage_main',float(q.coverage.min()));add(n,'median_coverage_main',float(q.coverage.median()))
for sym,prefix in [('510300','sh'),('159915','sz')]:
 d=pd.read_csv(BARS/f'{prefix}{sym}-nominal.csv',parse_dates=['date']);q=d[d.date.between(start,end)]
 add(sym,'main_quote_rows',len(q));add(sym,'main_unique_quote_dates',q.date.nunique());add(sym,'main_first_quote',q.date.min().date());add(sym,'main_last_quote',q.date.max().date())
# data_quality's 2790 scope
for n,d in widths.items():add(n,'legacy_quality_rows_2015_on',len(d.loc['2015-01-01':'2026-06-30']),'this is the 2790 scope, not the frozen main window')
# archived signals, waits and invalid-date trades
invalid_all=set(widths['all_a'].index[~widths['all_a'].valid])
events=[]
for fee in ['10bp','20bp']:
 folder=OLD/'results'/f'fee-{fee}'
 for sym in ['510300','159915']:
  for w in ['W0','W1','W2','W3']:
   stem=f'{sym}-all_a-{w}-{fee}'
   sig=pd.read_csv(folder/f'{stem}-signals.csv',parse_dates=['date'])
   trades=pd.read_csv(folder/f'{stem}-trades.csv',parse_dates=['date'])
   waits_path=folder/f'{stem}-waits.csv'
   try: waits=pd.read_csv(waits_path)
   except pd.errors.EmptyDataError: waits=pd.DataFrame()
   add(stem,'invalid_width_week_signals',int((sig.kind=='invalid_width_week').sum()))
   add(stem,'trades_on_52_invalid_all_a_dates',int(trades.date.isin(invalid_all).sum()))
   if w=='W3':
    q=trades[(trades.side=='buy') & (trades.reason=='confirmed_waiting_buy') & trades.date.isin(invalid_all)]
    add(stem,'W3_confirmed_buys_on_invalid_width_date',len(q))
   if len(waits):
    vc=waits.status.value_counts()
    add(stem,'waits_total',len(waits));add(stem,'waits_cancelled_invalid_width_week',int(vc.get('cancelled_invalid_width_week',0)))
 for sym in ['510300','159915']:
  for b in ['B0','B1','B2']:
   stem=f'{sym}-baseline-{b}-{fee}'
   try: sig=pd.read_csv(folder/f'{stem}-signals.csv')
   except pd.errors.EmptyDataError: sig=pd.DataFrame(columns=['kind'])
   add(stem,'invalid_width_signals',int(sig.kind.astype(str).str.contains('width').sum()) if len(sig) else 0,'baseline simulate branch receives width=None')
# invalid day events and weekly signal dates
q=widths['all_a'].loc[start:end];
for day,row in q[~q.valid].iterrows():events.append({'event_type':'invalid_all_a_day','date':str(day.date()),'symbol_or_account':'all_a','detail':f"pool_total={int(row.pool_total)} eligible={int(row.eligible)} coverage={row.coverage:.6f}"})
folder=OLD/'results/fee-10bp'
s=pd.read_csv(folder/'510300-all_a-W0-10bp-signals.csv',parse_dates=['date'])
for day in s.loc[s.kind=='invalid_width_week','date']:events.append({'event_type':'invalid_width_week','date':str(day.date()),'symbol_or_account':'all_a','detail':'same weekly calendar for both symbols, all W variants and both fee levels'})
pd.DataFrame(rows).to_csv(OUT/'counts.csv',index=False)
pd.DataFrame(events).to_csv(OUT/'events.csv',index=False)
failures=[
 {'id':'all_a_universe_proxy','severity':'material_definition_limit','status':'open','detail':'Denominator is cached-panel columns between each column first/last valid quote, not the official point-in-time universe of all then-listed A shares.'},
 {'id':'current_list_backfill_survivorship','severity':'material_source_limit','status':'open','detail':'prepare_data.py explicitly labels the panel current-list backfill; stocks gone before snapshot can be absent.'},
 {'id':'legacy_arrival_times','severity':'historical_availability_limit','status':'open','detail':'Frozen source arrival times are not proven; definition-standard v1.0.0 says old data remain legacy and are not retroactively migrated.'},
 {'id':'chinext_2017_chain','severity':'scope_limit','status':'open','detail':'Own-index ChiNext branch failed at 2017-10-09 and was paused; it does not affect the all-A account arithmetic but prevents own-index comparison.'},
 {'id':'2790_vs_1884_scope','severity':'documentation_mismatch','status':'explained','detail':'data_quality computes both 2790 rows and 1884 valid rows on 2015-01-01..2026-06-30, so that legacy ratio is calculable; it is mislabeled if presented as the frozen 2018-07-05 main comparison window, whose ratio is 1884/1936.'},
 {'id':'invalid_day_behavior','severity':'behavior_check','status':'explained','detail':'52 invalid all-A dates produced 11 invalid weeks and no archived W0-W3 trades on those dates; no archived waiting order was cancelled specifically by invalid week.'},
 {'id':'w3_daily_invalid_confirmation_latent','severity':'semantic_limit','status':'not_observed','detail':'W3 daily confirmation does not re-check same-day width validity when the week has another valid row; archived paths have zero such buys on the 52 invalid dates.'},
 {'id':'159915_missing_quote_2021_02_08','severity':'calendar_difference','status':'explained','detail':'159915 has no quote on 2021-02-08 while 510300 does; archived accounts mark it non-quote, carry the 2021-02-05 mark, and do not trade.'},
]
pd.DataFrame(failures).to_csv(OUT/'failures.csv',index=False)
