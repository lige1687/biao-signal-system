"""抓东财两融全历史（沪深北合计，日频）。"""
import json, time, urllib.request
import pandas as pd

BASE = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_LSHJ"
        "&columns=DIM_DATE,RZYE,RZMRE,RQYE,RZJME&pageSize=500&pageNum={p}&sortColumns=dim_date&sortTypes=1")

def get(p):
    req = urllib.request.Request(BASE.format(p=p), headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

rows = []
p = 1
while True:
    d = get(p)
    data = (d.get("result") or {}).get("data") or []
    if not data:
        break
    rows.extend(data)
    pages = d["result"]["pages"]
    if p % 4 == 0: print(f"page {p}/{pages}", flush=True)
    if p >= pages: break
    p += 1
    time.sleep(0.5)

df = pd.DataFrame(rows)
df['date'] = pd.to_datetime(df['DIM_DATE']).dt.date
for c in ['RZYE','RZMRE','RQYE','RZJME']:
    df[c] = pd.to_numeric(df[c])
df = df[['date','RZYE','RZMRE','RQYE','RZJME']].dropna().sort_values('date')
df.to_csv('margin_history.csv', index=False)
print('rows:', len(df), '| range:', df.date.min(), '→', df.date.max())
