from pathlib import Path
import json,datetime,hashlib
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent;I=P/'inputs'
def save(path,obj):(P/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str,allow_nan=False))
a=pd.read_parquet(I/'timing/513100.parquet.quarantined');b=pd.read_parquet(I/'pool/513100.SS.bars.parquet')
dates=a.close.pct_change(fill_method=None).abs().nlargest(5).index
q=a.loc['2022-01-12','close'];r=a.loc['2022-01-14','close']
joined=a[['close']].join(b[['close']],lsuffix='_timing',rsuffix='_pool',how='inner');pre=joined.loc[:'2022-01-12'];post=joined.loc['2022-01-14':]
save('06/split-audit.json',dict(split_date='2022-01-13',resumption='2022-01-14',old_to_new=5,raw_return=r/q-1,share_adjusted_return=5*r/q-1,pool_return=b.close.loc['2022-01-14']/b.close.loc['2022-01-12']-1,pre_ratio_median=float((pre.close_timing/pre.close_pool).median()),post_ratio_median=float((post.close_timing/post.close_pool).median()),overlap=len(joined),suspension_has_quote='2022-01-13' in a.index,largest_jumps=[dict(date=str(t.date()),return_=float(a.close.pct_change(fill_method=None).loc[t])) for t in dates],limitation='Only this split is explained. No certification of all dividends, other actions, adjusted execution prices or current tradability.'))
rows=[]
for f in sorted((I/'timing').glob('*parquet*'))+sorted((I/'pool').glob('*.parquet')):
 d=pd.read_parquet(f);meta=f.with_suffix('.meta.json');rows.append(dict(file=str(f.relative_to(I)),rows=len(d),first=str(d.index.min()),last=str(d.index.max()),attrs=d.attrs,duplicate_dates=int(d.index.duplicated().sum()),nonpositive_close=int((d.close<=0).sum()) if 'close' in d else None,metadata=json.loads(meta.read_text()) if meta.exists() else None))
save('06/local-inventory.json',rows)
tx=json.loads((I/'cache/tx_sector_flow_pilot.json').read_text())['boards'];em=json.loads((I/'cache/sector_flow_history.json').read_text());calendar=pd.read_parquet(I/'timing/SH000001.parquet').index
coverage=[];joint={}
for code in sorted(set(tx)|set(em)):
 vals={};sources={};conflicts=[]
 for label,data in [('tencent',tx),('eastmoney',em)]:
  for x in data.get(code,[]):
   if x.get('small_yi') is None:continue
   day=pd.Timestamp(x['date'])
   if day in vals and vals[day]!=x['small_yi']:conflicts.append(str(day.date()))
   if day not in vals:vals[day]=x['small_yi'];sources[day]=label
 s=pd.Series(vals,dtype=float).sort_index();joint[code]=s
 if s.empty:continue
 cal=calendar[(calendar>=s.index.min())&(calendar<=s.index.max())];aligned=s.reindex(cal)
 run=best=0
 for good in aligned.notna():run=run+1 if good else 0;best=max(best,run)
 # Need 20 current observations AND previous 120 means: first candidate needs 140 daily inputs.
 count140=int(aligned.notna().astype(int).rolling(140,min_periods=140).sum().eq(140).sum())
 coverage.append(dict(code=code,points=len(s),first=str(s.index.min().date()),last=str(s.index.max().date()),quote_proxy_dates=len(cal),available_quote_dates=int(aligned.notna().sum()),missing_quote_dates=int(aligned.isna().sum()),longest_consecutive_quote_days=best,eligible_140_day_windows=count140,conflicting_source_dates=len(conflicts),conflict_examples=conflicts[:3]))
save('07/flow-coverage.json',coverage)
hist=json.loads((I/'cache/sector_trend_history.json').read_text());df=pd.DataFrame({r['date']:{c:v.get('close') for c,v in r['boards'].items()} for r in hist}).T.sort_index();df.index=pd.to_datetime(df.index)
margin=pd.read_csv(I/'supplement/sentiment_research_2026-09/margin_history.csv');journal=json.loads((I/'cache/sentiment_signal_journal.json').read_text())['records']
soxx=pd.read_parquet(I/'supplement/SOXX.bars.parquet');cn=pd.read_parquet(I/'timing/512480.parquet')
agg=pd.concat(joint,axis=1);counts=agg.notna().sum(axis=1)
target=[x for x in coverage if x['code'] in ['BK1036','BK0478']]
common={}
for code in ['BK1036','BK0478']:
 flow=joint[code].reindex(calendar);eligible=flow.notna().astype(int).rolling(140,min_periods=140).sum().eq(140)
 boarddates=[pd.Timestamp(r['date']) for r in hist if r['boards'].get(code,{}).get('b50') is not None and r['boards'].get(code,{}).get('close') is not None]
 common[code]=len(set(eligible[eligible].index)&set(boarddates))
save('07/summary.json',dict(boards=len(coverage),boards_with_140_consecutive_window=sum(x['eligible_140_day_windows']>0 for x in coverage),targets=target,targets_flow_and_board_candidate_dates=common,market_flow_daily_board_count_min=int(counts.min()),market_flow_daily_board_count_max=int(counts.max()),market_equal_board_price_history=dict(first=str(df.index.min().date()),last=str(df.index.max().date()),rows=len(df)),margin_history=dict(rows=len(margin),first=str(margin.date.min()),last=str(margin.date.max()),missing_balance=int(margin.RZYE.isna().sum())),journal=journal,industry_pair=dict(china='512480',us='SOXX',cn_first=str(cn.index.min().date()),cn_last=str(cn.index.max().date()),us_first=str(soxx.index.min().date()),us_last=str(soxx.index.max().date()),same_date_overlap=len(cn.index.intersection(soxx.index)),currency_alignment=False,available_at_alignment=False,price_adjustment_provenance_complete=False),claim='Coverage only. Missing rows are not zero flows. Quote dates are a proxy calendar. No complete four-condition backtest or pair return computed.'))
print((P/'06/split-audit.json').read_text());print((P/'07/summary.json').read_text())
