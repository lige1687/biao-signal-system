"""Rebuild every eligible event using explicit trailing windows and calendar month ends."""
from pathlib import Path
import json,calendar,datetime
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;P=R.parent;b=pd.read_parquet(P/'inputs/cache/breadth_cn_all.parquet');frozen=json.loads((P/'frozen-events.json').read_text());results=[];cache={}
for group in frozen:
 s=group['symbol'];k=group['kind']
 if s not in cache:
  d=pd.read_parquet(P/'inputs/cache'/f'{s}.parquet');d=d.loc[:min(d.index.max(),b.b200.last_valid_index())];bw=b.b200.reindex(d.index).to_numpy();c=d.close.to_numpy();g=[];dd=[]
  for i in range(len(d)):
   window=c[max(0,i-199):i+1];long=c[max(0,i-499):i+1]
   g.append(c[i]/window.mean()-1 if len(window)==200 and np.isfinite(window).all() else np.nan)
   dd.append(c[i]/long.max()-1 if len(long)>=100 and np.isfinite(long).all() else np.nan)
  g=np.array(g);dd=np.array(dd);start=int(np.flatnonzero(np.isfinite(g)&np.isfinite(dd)&np.isfinite(bw))[0]);cache[s]=(d,g,dd,bw,start)
 d,g,dd,bw,start=cache[s];seen=[];last=-10**9
 if k=='base':
  year,month=d.index[start].year,d.index[start].month
  while (year,month)<=(d.index[-1].year,d.index[-1].month):
   day=calendar.monthrange(year,month)[1];ts=pd.Timestamp(datetime.datetime(year,month,day,23,59))
   if ts<=d.index[-1]+pd.Timedelta(hours=16):
    e=int(d.index.searchsorted(ts,side='right')-1)
    if e>=start and e-last>=126:seen.append({'e':e,'decision_at':str(ts)});last=e
   year,month=(year+1,1) if month==12 else (year,month+1)
 else:
  if k=='deep20':valid=np.isfinite(g);flag=g<=-.2
  elif k=='bottom':valid=np.isfinite(g)&np.isfinite(dd)&np.isfinite(bw);flag=(bw<43.3)&(dd<=-.15)&(g<0)
  else:valid=np.isfinite(bw);flag=bw<43.3
  for i in range(max(start,1),len(d)):
   if valid[i-1] and valid[i] and not flag[i-1] and flag[i] and i-last>=126:seen.append({'e':i,'decision_at':str(d.index[i]+pd.Timedelta(hours=16))});last=i
 results.append({'symbol':s,'kind':k,'start':str(d.index[start].date()),'events':len(seen),'matches_frozen':seen==group['events']})
out={'all_match':all(x['matches_frozen'] for x in results),'total_unique_method_events':sum(x['events'] for x in results),'scope':'Condition arithmetic uses only prices/breadth through the evaluated date. This does not prove historical public availability of the underlying breadth data.','groups':results}
(R/'events-check-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='groups'},ensure_ascii=False))
