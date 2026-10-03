"""Compute auditable candidate values without future returns or production imports."""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
SRC = Path('/Users/yongbiaoli/.lei_signal_lab/cache/sentiment_research_2026-09')
manifest = json.loads((OUT/'accepted-source-manifest.json').read_text())['files']
for f in manifest:
    assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest() == f['sha256'], f['path']

def coverage(v, date):
    ok = v.notna()
    return {'rows':int(len(v)), 'valid':int(ok.sum()), 'min':float(v.min()), 'max':float(v.max()),
            'start':str(date[ok].min().date()), 'end':str(date[ok].max().date())}

def extremes(d, value, lo, hi):
    counts = {}
    for name, flag in [('low',d[value]<=lo),('high',d[value]>=hi)]:
        breaks = d.date.diff().dt.days.gt(8)
        counts[name] = {'observations':int(flag.sum()), 'runs':int((flag & (~flag.shift(1,fill_value=False) | breaks)).sum())}
    return counts

a = pd.read_csv(SRC/'aaii_clean.csv',parse_dates=['reported']).rename(columns={'reported':'date'})
assert not a.date.duplicated().any()
assert a[['bullish','neutral','bearish']].apply(lambda s:s.between(0,1).all()).all()
a['spread_pp'] = 100*(a.bullish-a.bearish)
a['ma20_pp'] = a.spread_pp.rolling(20,min_periods=20).mean()
delta = (a.spread_pp - 100*a.bull_bear).abs().max()
assert delta < 1e-10
xls = pd.read_excel(SRC/'aaii_sentiment.xls',header=None)
raw = xls.iloc[:,[0,1,2,3]].copy()
raw.columns = ['date','bullish','neutral','bearish']
raw.date = pd.to_datetime(raw.date,errors='coerce')
for k in raw.columns[1:]: raw[k] = pd.to_numeric(raw[k],errors='coerce')
raw = raw.dropna().sort_values('date')
joined = a.merge(raw,on='date',suffixes=('_csv','_xls'),validate='one_to_one')
rawdiff = {k:float((joined[k+'_csv']-joined[k+'_xls']).abs().max()) for k in ['bullish','neutral','bearish']}
assert len(joined)==len(a) and max(rawdiff.values())<1e-10

n = pd.read_csv(SRC/'naaim_clean.csv',parse_dates=['date'])
assert not n.date.duplicated().any()
px = pd.read_csv(SRC/'apx_510300_SS.csv',parse_dates=['date']).set_index('date')
m = pd.read_csv(SRC/'margin_history.csv',parse_dates=['date']).set_index('date')
assert not px.index.duplicated().any() and not m.index.duplicated().any()
q = m.RZYE.reindex(px.index)
positive = q.gt(0) & q.notna()
window = positive.rolling(21,min_periods=21).sum().eq(21)
v = (q/q.shift(20)-1)*100
v = v.where(window)
mv = pd.DataFrame({'date':px.index,'rzye':q.to_numpy(),'change20_pct':v.to_numpy(),'valid_quote_window':window.to_numpy()})

start,end = pd.Timestamp('2014-01-01'),pd.Timestamp('2026-06-30')
ar = a[a.date.between(start,end)]
nr = n[n.date.between(start,end)]
mr = mv[mv.date.between(start,end)]
result = {'protocol_sha256':hashlib.sha256((OUT/'qualification-protocol.json').read_bytes()).hexdigest(),
    'aaii':{'all':coverage(a.spread_pp,a.date),'range':coverage(ar.spread_pp,ar.date),
            'extremes_all':extremes(a,'spread_pp',-25,25),'extremes_range':extremes(ar,'spread_pp',-25,25),
            'xls_rows_matched':len(joined),'xls_value_max_abs_difference':rawdiff,'spread_stored_max_abs_difference_pp':float(delta),
            'date_meaning':'Cached xls header is Reported Date; timestamp/revision vintage unknown'},
    'naaim':{'all':coverage(n.naaim,n.date),'range':coverage(nr.naaim,nr.date),
            'extremes_all':extremes(n,'naaim',40,100),'extremes_range':extremes(nr,'naaim',40,100),
            'range_above100':int((nr.naaim>100).sum()),'prediction_eligibility':'blocked: no proven timely source'},
    'margin':{'all_quote_axis':coverage(mv.change20_pct,mv.date),'range':coverage(mr.change20_pct,mr.date),
              'missing_balance_quote_dates':int(q.isna().sum()),'positive_window_count':int(window.sum()),
              'source_date_meaning':'date denotes balance observation; actual publication time and vintage unknown',
              'source_code_mismatch':'fetch_margin.py output has RQYE and no RZYEZB/LTSZ, current CSV has latter two; script is not proof of actual CSV provenance'},
    'limits':['Quote axis is not independently confirmed complete exchange calendar.','Episodes are consecutive survey runs, not independent investment opportunities.','Values and thresholds are computed; all effectiveness remains unevaluated here.']}
a.to_csv(OUT/'aaii-candidate-values.csv',index=False)
n.to_csv(OUT/'naaim-candidate-values.csv',index=False)
mv.to_csv(OUT/'margin-candidate-values.csv',index=False)
(OUT/'candidate-qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
bindings=[]
for p in [SRC/'aaii_sentiment.xls',SRC/'fetch_margin.py',SRC/'fetch_prices.py',SRC/'fetch_aetf.py',OUT/'qualification-protocol.json',Path(__file__)]:
    b=p.read_bytes();bindings.append({'path':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(OUT/'calculation-manifest.json').write_text(json.dumps({'files':bindings,'input_manifest':'accepted-source-manifest.json'},ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
