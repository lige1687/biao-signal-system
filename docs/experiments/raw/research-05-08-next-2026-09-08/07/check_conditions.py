from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent;I=P.parent/'inputs'
cal=pd.read_parquet(I/'timing/SH000001.parquet').index
hist=json.loads((I/'cache/sector_trend_history.json').read_text());prices=pd.DataFrame({r['date']:{c:v.get('close') for c,v in r['boards'].items()} for r in hist}).T.sort_index();prices.index=pd.to_datetime(prices.index);prices=prices.reindex(cal)
tx=json.loads((I/'cache/tx_sector_flow_pilot.json').read_text())['boards'];em=json.loads((I/'cache/sector_flow_history.json').read_text());flows={}
for code in set(tx)|set(em):
 vals={}
 for src in [tx,em]:
  for x in src.get(code,[]):
   if x.get('small_yi') is not None:vals.setdefault(pd.Timestamp(x['date']),x['small_yi'])
 flows[code]=pd.Series(vals,dtype=float)
allflow=pd.concat(flows,axis=1).sum(axis=1,min_count=1).reindex(cal).rolling(20,min_periods=20).sum()
m=pd.read_csv(I/'supplement/sentiment_research_2026-09/margin_history.csv',parse_dates=['date']).set_index('date').RZYE.reindex(cal).pct_change(20,fill_method=None)
meanret=prices.pct_change(fill_method=None).mean(axis=1);index=(1+meanret.dropna()).cumprod();mom=index.reindex(cal).pct_change(20,fill_method=None)
votes=pd.concat([m,allflow,mom],axis=1);cold=(np.sign(votes).sum(axis=1)<0).where(votes.notna().all(axis=1))
out=[];summary=[]
for code in ['BK1036','BK0478']:
 close=prices[code];normalized=flows[code].reindex(cal)/close;mean=normalized.rolling(20,min_periods=20).mean();mu=mean.rolling(120,min_periods=120).mean().shift(1);sd=mean.rolling(120,min_periods=120).std().shift(1);z=(mean-mu)/sd.replace(0,np.nan)
 ret=close.pct_change(60,fill_method=None)*100;b50=pd.Series({pd.Timestamp(r['date']):r['boards'].get(code,{}).get('b50') for r in hist},dtype=float).reindex(cal)
 tab=pd.DataFrame(dict(z=z,r60=ret,b50=b50,cn_cold=cold)).loc['2025-08-07':]
 for date,row in tab.iterrows():
  conditions=[None if pd.isna(row.z) else bool(round(row.z,2)>=1.5),None if pd.isna(row.r60) else bool(row.r60<=-10),None if pd.isna(row.b50) else bool(row.b50<30),None if pd.isna(row.cn_cold) else bool(row.cn_cold)]
  complete=all(v is not None for v in conditions);logical='false' if False in conditions else 'unknown' if None in conditions else 'true'
  out.append(dict(code=code,date=str(date.date()),z=None if pd.isna(row.z) else float(row.z),r60=None if pd.isna(row.r60) else float(row.r60),b50=None if pd.isna(row.b50) else float(row.b50),cn_cold=None if pd.isna(row.cn_cold) else bool(row.cn_cold),complete=complete,condition_state=logical))
 sub=[x for x in out if x['code']==code];summary.append(dict(code=code,dates=len(sub),complete=sum(x['complete'] for x in sub),complete_true_dates=[x['date'] for x in sub if x['complete'] and x['condition_state']=='true'],complete_false=sum(x['complete'] and x['condition_state']=='false' for x in sub),incomplete=sum(not x['complete'] for x in sub),logical_unknown=sum(x['condition_state']=='unknown' for x in sub)))
(P/'condition-dates.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));(P/'condition-summary.json').write_text(json.dumps(dict(protocol_sha256=hashlib.sha256((P/'complete_condition_protocol.md').read_bytes()).hexdigest(),results=summary,decision='Retrospective input diagnosis only; no known-at-the-time claim and no return evaluation'),ensure_ascii=False,indent=2));print((P/'condition-summary.json').read_text())
