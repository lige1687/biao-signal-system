"""Offline reproduction of the old TWO-condition price observation; no trades."""
from pathlib import Path
import ast,json,io,contextlib
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent;I=P.parent/'inputs'
tree=ast.parse((I/'scripts/icepoint_multi_event_validation.py').read_text());events=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EVENTS' for t in n.targets));main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
zt=ast.parse((I/'scripts/retail_sentiment_ts_backtest.py').read_text());z=next(n for n in zt.body if isinstance(n,ast.FunctionDef) and n.name=='zscore_self');ns=dict(pd=pd,np=np,json=json,CACHE=I,EVENTS=events,BASE_WIN=120)
exec(compile(ast.Module(body=[z,main],type_ignores=[]),'frozen_pure_functions','exec'),ns)
buf=io.StringIO()
with contextlib.redirect_stdout(buf):ns['main']()
(P/'legacy-stdout.txt').write_text(buf.getvalue())
panel=pd.read_parquet(I/'tx_close_panel.parquet').apply(pd.to_numeric,errors='coerce');panel.index=pd.to_datetime(panel.index);flows=json.loads((I/'tx_sector_flow_pilot.json').read_text())['boards'];members=json.loads((I/'sector_members.json').read_text())['boards'];snap=json.loads((I/'sector_trend_snapshot.json').read_text());codes=sorted(b['code'] for b in snap['boards'] if (b.get('level') or 3)<=2)
rows=[]
for code in codes:
 mem=[s for s in members.get(code,{}).get('members',[]) if s in panel.columns]
 if len(mem)<5:continue
 c=panel[mem].mean(axis=1).dropna()
 if len(c)<150:continue
 v={pd.Timestamp(p['date']):p['small_yi'] for p in flows.get(code,[]) if pd.Timestamp(p['date']) in c.index and p.get('small_yi') is not None}
 if not v:continue
 flow=pd.Series(v).sort_index().reindex(c.index);m=flow.rolling(20,min_periods=20).mean();mu=m.rolling(120,min_periods=120).mean().shift(1);sd=m.rolling(120,min_periods=120).std().shift(1);z=(m-mu)/sd.replace(0,np.nan);ret60=c.pct_change(60,fill_method=None);sig=(z>=1.5)&(ret60<=-.1)
 for name,start,end in events:
  for day in c.index[(c.index>=start)&(c.index<=end)&sig]:
   i=c.index.get_loc(day)
   if i+15<len(c):rows.append(dict(event=name,code=code,date=str(day.date()),observation_end=str(c.index[i+15].date()),start_price=float(c.iloc[i]),end_price=float(c.iloc[i+15]),price_change=float(c.iloc[i+15]/c.iloc[i]-1),z=float(z.loc[day]),ret60=float(ret60.loc[day]),current_member_count=len(mem)))
d=pd.DataFrame(rows);d.to_csv(P/'legacy-observations.csv',index=False,float_format='%.17g');summary=[]
old=[(118,3.56),(32,.97),(14,.62),(88,12.90)]
for (name,start,end),(oldn,oldmean) in zip(events,old):
 x=d[d.event==name];v=x.price_change;summary.append(dict(event=name,observations=len(x),unique_dates=int(x.date.nunique()),unique_boards=int(x.code.nunique()),mean_percent=float(v.mean()*100) if len(v) else None,median_percent=float(v.median()*100) if len(v) else None,positive_fraction=float((v>0).mean()) if len(v) else None,old_report_count=oldn,old_report_mean_percent=oldmean,matches_old_rounded=bool(len(x)==oldn and abs(v.mean()*100-oldmean)<.005)))
(P/'replay-summary.json').write_text(json.dumps(dict(results=summary,scope='Old two-condition price observations only; no independent event count claim or complete four-condition test.'),ensure_ascii=False,indent=2));print(buf.getvalue());print(json.dumps(summary,ensure_ascii=False))
