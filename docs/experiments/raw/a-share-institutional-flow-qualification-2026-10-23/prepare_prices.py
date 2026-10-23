"""Prepare full formation universe and endpoint availability; never compute returns."""
import json,csv,hashlib,datetime
from pathlib import Path
from decimal import Decimal as D
import pandas as pd
import pyarrow.parquet as pq
R=Path(__file__).resolve().parent
out=Path(json.loads((R/'storage-plan.json').read_text())['output'])/'price-qualification';assert not out.exists()
h=json.loads((R/'huaxia-history/history-series.json').read_text());j=json.loads((R/'jiashi-history/qualification.json').read_text());x=json.loads((R/'history-comparison.json').read_text());H={v['key']:v for v in h['reports']};J={v['period']:v for v in j['reports']}
with open(j['holdings_csv']) as f:jr=list(csv.DictReader(f))
def holdings(key):
 a={v['stock_code']:v for v in jr if v['period_end']==J[key]['period_end']}
 with open(H[key]['holdings_csv']) as f:b={v['stock_code']:v for v in csv.DictReader(f)}
 return a,b
calp=Path('docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json');calendar=json.loads(calp.read_text())['days'];days=pd.DatetimeIndex([k for k,v in calendar.items() if v['is_trading_day']]).sort_values()
source=Path('/Users/yongbiaoli/.lei_signal_lab/cache/a_share_klines_full.parquet');price_sha=hashlib.sha256(source.read_bytes()).hexdigest();assert price_sha=='5ad045c518d0bb4394d8c8cb946d207ad9b5b1454e5a776b1a3766c62b475b04'
cols=set(pq.read_schema(source).names);records=[];periods=[]
for row in x['periods']:
 if not row['start_holdings_available']:continue
 key=row['start_holdings_period'];a,b=holdings(key);pub=max(row['necessary_reports_public_date'],J[key]['official_pub_date'],H[key]['announcement_date']);start=days[days>pd.Timestamp(pub)][0];target=start+pd.DateOffset(months=6);end=days[days>=target][0] if len(days[days>=target]) else pd.NaT
 for code in sorted(set(a)|set(b)):
  va=D(a.get(code,{}).get('fair_value_cny','0'));vb=D(b.get(code,{}).get('fair_value_cny','0'));af=float(va/(va+vb));p1=float(row['jiashi_amount_pressure']);p2=float(row['huaxia_amount_pressure'])
  records.append({'period':row['period'],'code':code,'name_a':a.get(code,{}).get('stock_name'),'name_b':b.get(code,{}).get('stock_name'),'entry':start,'exit':end,'a':af,'pressure':p2+(p1-p2)*af,'direction':row['amount_direction'],'held_value_cny':float(va+vb),'column_present':code in cols})
 periods.append({'period':row['period'],'public_date':pub,'entry':str(start.date()),'exit':None if pd.isna(end) else str(end.date()),'requested_exit_on_or_after':str(target.date()),'direction':row['amount_direction']})
f=pd.DataFrame(records);c=sorted(set(f['code'])&cols);prices=pd.read_parquet(source,columns=['date']+c);prices=prices.set_index('date') if 'date' in prices.columns else prices;assert prices.index.name=='date';prices.index=pd.to_datetime(prices.index)
# Availability only, no arithmetic between endpoint prices or future magnitude inspection.
f['entry_price_available']=[v.code in cols and v.entry in prices.index and pd.notna(prices.loc[v.entry,v.code]) and prices.loc[v.entry,v.code]>0 for v in f.itertuples()]
f['exit_price_available']=[v.code in cols and v.exit in prices.index and pd.notna(prices.loc[v.exit,v.code]) and prices.loc[v.exit,v.code]>0 for v in f.itertuples()]
f['source_covers_exit']=f['exit']<=prices.index.max()
for v in periods:
 t=f[f.period==v['period']];v.update(universe=len(t),entry_available=int(t.entry_price_available.sum()),both_available=int((t.entry_price_available&t.exit_price_available).sum()),missing_codes=t.loc[~t.column_present,'code'].tolist(),unknown_endpoint_codes=t.loc[~(t.entry_price_available&t.exit_price_available),'code'].tolist(),source_covers_exit=bool(t.source_covers_exit.iloc[0]))
out.mkdir(parents=True);f.to_parquet(out/'formations.parquet',index=False)
res={'at':datetime.datetime.now().astimezone().isoformat(),'price_source':str(source),'price_sha256':price_sha,'calendar_source':str(calp),'calendar_sha256':hashlib.sha256(calp.read_bytes()).hexdigest(),'formations_path':str(out/'formations.parquet'),'formations_sha256':hashlib.sha256((out/'formations.parquet').read_bytes()).hexdigest(),'formations':len(f),'unique_codes':int(f.code.nunique()),'periods':periods,'returns_computed':False,'limitation':'Endpoint observation only; no historical trading status, liquidation or dividends verified; price-change association only may be considered'}
(R/'price-qualification.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n');print(json.dumps(res,ensure_ascii=False))
