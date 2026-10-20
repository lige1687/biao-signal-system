from pathlib import Path
import json
import pandas as pd
P=Path(__file__).resolve().parent;frames={};out=[]
for s in ['sh510300','sz159915','sh518880','sh513100']:
 rows=[]
 for y in range(2013,2027,2):
  obj=json.loads((P/f'{s}-{y}.json').read_text());rows.extend([x[:6] for x in obj['data'][s]['qfqday']])
 d=pd.DataFrame(rows,columns=['date','open','close','high','low','volume']);num=d.columns[1:];d[num]=d[num].astype(float);conf=d.groupby('date')[list(num)].nunique().max(axis=1);bad=conf[conf>1]
 assert bad.empty,(s,bad.index.tolist())
 d=d.drop_duplicates('date').set_index('date').sort_index();assert (d[['open','close','high','low']]>0).all().all();d.to_csv(P/f'{s}-qfq.csv');frames[s]=d
 out.append(dict(symbol=s,rows=len(d),first=d.index.min(),last=d.index.max(),conflicting_overlap_dates=bad.index.tolist(),max_daily_jump=float(d.close.pct_change(fill_method=None).abs().max()),min_price=float(d[list(num[:4])].min().min())))
common=frames['sh510300'].index
for d in frames.values():common=common.intersection(d.index)
(P/'long-coverage.json').write_text(json.dumps(dict(products=out,common_dates=len(common),first=common.min(),last=common.max()),indent=2))
reference=frames['sh510300'].loc['2013-07-29':].index
(P/'missing-quote-dates.json').write_text(json.dumps({s:list(reference.difference(d.index)) for s,d in frames.items()},indent=2))
print('No conflicting overlap; common',len(common),'dates;',common.min(),common.max())
