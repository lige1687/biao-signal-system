from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd, baostock as bs, json, hashlib

ROOT=Path(__file__).resolve().parents[5]; OUT=Path(__file__).resolve().parent; RAW=OUT/'raw-responses'; RAW.mkdir(parents=True,exist_ok=True)
OLD=ROOT/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09'
BARS=ROOT/'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/bars/sh510300-nominal.csv'
plan=json.loads((OUT/'query-plan.json').read_text())
dates=pd.read_csv(BARS,parse_dates=['date']).date
requests=[]
for ev in plan['events']:
    left,right=pd.Timestamp(ev['left_probe']),pd.Timestamp(ev['right_probe'])
    q=list(dates[(dates>left)&(dates<=right)])
    assert len(q)==20,(ev,len(q)); requests += [(ev['selected_week_date'],d) for d in q]
assert len(requests)==40
frozen=pd.read_parquet(OLD/'prepared/csi300_membership_daily.parquet');frozen.date=pd.to_datetime(frozen.date)
login=bs.login(); records=[]; diffs=[]
if login.error_code!='0':
    records.append({'date':'','event':'','acquired_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'status':'login_failed','error_code':login.error_code,'error_msg':login.error_msg,'returned_count':0})
else:
    try:
        for event,d in requests:
            at=datetime.now(timezone(timedelta(hours=8))).isoformat()
            rs=bs.query_hs300_stocks(d.strftime('%Y-%m-%d'))
            frame=rs.get_data()
            path=RAW/f'{d:%Y-%m-%d}.csv';frame.to_csv(path,index=False)
            got=set(frame.code.astype(str).str.split('.').str[-1].str.zfill(6)) if 'code' in frame else set()
            old=set(frozen.loc[frozen.date==d,'symbol'].astype(str).str.zfill(6))
            status='ok' if rs.error_code=='0' and len(got)==300 else 'failed_or_non300'
            records.append({'date':d.date().isoformat(),'event':event,'acquired_at':at,'status':status,'error_code':rs.error_code,'error_msg':rs.error_msg,'returned_count':len(got),'raw_path':str(path.relative_to(ROOT))})
            diffs.append({'date':d.date().isoformat(),'event':event,'provider_count':len(got),'frozen_count':len(old),'added_vs_frozen':'|'.join(sorted(got-old)),'removed_vs_frozen':'|'.join(sorted(old-got)),'sets_equal':got==old})
    finally: bs.logout()
pd.DataFrame(records).to_csv(OUT/'request-log.csv',index=False)
pd.DataFrame(diffs).to_csv(OUT/'daily-set-differences.csv',index=False)
print(pd.DataFrame(records).status.value_counts().to_string())
if diffs: print(pd.DataFrame(diffs).sets_equal.value_counts().to_string())
