"""Compare four new source replies without factor/return selection."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import hashlib,json
HERE=Path(__file__).resolve().parent
receipt=json.loads((HERE/'probe-receipt.json').read_text())
bykey={}
for item in receipt['requests']:
    if item['kind']!='data_request' or item.get('status')!='ok': continue
    payload=Path(item['path']).read_bytes()
    assert hashlib.sha256(payload).hexdigest()==item['sha256']
    doc=json.loads(payload)
    assert doc['error_code']=='0'
    rows=[dict(zip(doc['fields'],r)) for r in doc['data']]
    bykey[item['key']]=rows
nominal,adjusted=bykey['001914-nominal'],bykey['001914-adjusted-repeat']
assert len(nominal)==len(adjusted)==3166
assert [r['date'] for r in nominal]==[r['date'] for r in adjusted]
assert len({r['date'] for r in nominal})==len(nominal)
checks=[]
for key in ('001914-nominal','001914-adjusted-repeat'):
 rows=bykey[key]
 problems=[]
 for i,r in enumerate(rows):
    if r['code']!='sz.001914':problems.append([i,'code'])
    if i and r['date']<=rows[i-1]['date']:problems.append([i,'date_order'])
    if r['tradestatus']=='1':
        prices=[Decimal(r[f]) for f in ['open','high','low','close']]
        if not all(v.is_finite() and v>0 for v in prices):problems.append([i,'bad_price'])
        o,h,l,c=prices
        if not l<=min(o,c)<=max(o,c)<=h:problems.append([i,'ohlc_order'])
 checks.append({'key':key,'rows':len(rows),'start':rows[0]['date'],'end':rows[-1]['date'],'flags':dict(Counter(r['adjustflag'] for r in rows)),'problems':problems})
contract=json.loads((HERE.parent/'lowfreq-expanded-discovery-2026-10-19/evaluation-input-contract-v2.json').read_text())
item=next(x for x in contract['sources'] if x['code']=='sz.001914')
payload=Path(item['path']).read_bytes()
assert hashlib.sha256(payload).hexdigest()==item['sha256']
old=json.loads(payload);oldrows=[dict(zip(old['fields'],r)) for r in old['data']]
oldby={r['date']:r for r in oldrows}
old_diff=sum(any(oldby[r['date']][f]!=r[f] for f in old['fields']) for r in adjusted)
flag3=[r for r in adjusted if r['adjustflag']=='3']
flag2=[r for r in adjusted if r['adjustflag']=='2']
nomby={r['date']:r for r in nominal}
unchanged_nominal=sum(all(Decimal(r[f])==Decimal(nomby[r['date']][f]) for f in ['open','high','low','close']) for r in flag3)
qfq_vs_nominal=sum(Decimal(a['close'])!=Decimal(n['close']) for a,n in zip(adjusted,nominal))
financial=bykey['600519-share-fields'][0]
assert financial['code']=='sh.600519' and financial['statDate']=='2014-12-31'
assert financial['pubDate']>financial['statDate']
summary={
 'checks':checks,'old_source_path':item['path'],'old_source_sha256':item['sha256'],
 'new_vs_old_common_fields_changed_rows':old_diff,
 'flag3_span':[flag3[0]['date'],flag3[-1]['date']],
 'flag2_span':[flag2[0]['date'],flag2[-1]['date']],
 'flag3_ohlc_equals_nominal_rows':unchanged_nominal,
 'adjusted_vs_nominal_close_different_rows':qfq_vs_nominal,
 'adjustment_factor_records':bykey['001914-adjust-factors'],
 'financial_sample':financial,
 'decisions':{
  '001914_old_and_repeat_adjusted':'blocked: mixed returned adjustment conventions confirmed twice; no automatic conversion',
  '001914_nominal':'bounded current-vendor historical nominal sample; not point-in-time revision proof or total return',
  '001914_adjustment_factors':'10 supplier events, earliest2019; cannot prove complete older corporate actions/identity history',
  '600519_share_fields':'one fiscal-period report, date-only publication2015-04-21; not admissible at2014-12-31, no verified arrival time/version/daily shares',
  'daily_size_filters':'still blocked pending historical dated share changes, field units and coverage qualification',
  'actual_price_limits_and_fills':'still not supplied by these four requests'
 },'performance_experiments':0,'source_attempts':receipt['total_source_attempts']}
with (HERE/'probe-qualification.json').open('x') as stream:json.dump(summary,stream,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in summary.items() if k not in ['adjustment_factor_records','checks']},ensure_ascii=False))
