import json,math,statistics
from pathlib import Path
from collections import Counter
from lei_signal.research import focus_dynamic as f
from lei_signal.research.focus_recent import merge_rows
from lei_signal.research.fip import SOURCE_FIELDS
from lei_signal.research.high52_revalidation import ADJUSTMENT_FIELDS,adapt_back_adjusted
D=Path(__file__).parent
plan=json.loads(f.PLAN.read_text()); receipt=json.loads(f.RECEIPT.read_text()); supplement=json.loads(f.SUPPLEMENT.read_text())
out=Path(json.loads((D/'storage-plan.json').read_text())['output'])
rows=json.loads((out/'daily.json').read_text()); audit=json.loads((out/'audit.json').read_text())
assert audit['code_sha256']==f.sha(Path(f.__file__))
assert len(rows)==len({r['date'] for r in rows}) and [r['date'] for r in rows]==sorted(r['date'] for r in rows)
for r in rows:
 if r['signal_valid']:
  assert r['focus_count']==math.ceil(.05*r['qualified_count'])==len(set(r['focus_members']))
  assert all(math.isfinite(r[k]) for k in ['focus','pool_momentum','breadth','concentration'])
  assert 0<=r['breadth']<=1 and 0<r['concentration']<=1
 else: assert r['focus'] is None
selected=[next(r for r in rows if r['date']==d) for d in ['2015-01-05','2020-01-02','2025-12-31']]
codes={c for r in selected for c in r['focus_members']}
main={r['code']:r for r in f._indexed(receipt['v8_outputs']['all-equity-read-index-v8.jsonl'],'main') if r['code'] in codes}
old={r['code']:r['source_refs'] for r in f._indexed(plan['baseline']['price_union'],'old') if r['code'] in codes}
extras={}
for ref in supplement['sources']: extras.setdefault(ref['code'],[]).append(ref)
calendar=f._calendar(plan); calpos={d:i for i,d in enumerate(calendar)}; values={r['date']:{} for r in selected}; verified=[]
for code in sorted(codes):
 index=main[code]; refs=[*old.get(code,[]),*index.get('reused_raw_sources',[]),*index.get('new_price_sources',[]),*extras.get(code,[])]
 factors=[index['old_union_factor_source']] if code in old else [*index.get('reused_factor_sources',[]),*index.get('new_factor_sources',[])]
 counter=Counter(); raw=merge_rows(code,refs,SOURCE_FIELDS,f.START,f.END,counter,verified)
 actions=merge_rows(code,factors,ADJUSTMENT_FIELDS,'1900-01-01',f.END,counter,verified)
 rawmap={x[0]:dict(zip(SOURCE_FIELDS,x)) for x in raw}
 for row in selected:
  if code not in row['focus_members']: continue
  day=row['date']; i=calpos[day]; days=calendar[i-20:i+1]
  assert all(rawmap[d]['tradestatus']=='1' for d in days)
  assert rawmap[day]['isST']=='0'
  # Independent direct endpoint multiplication, without builder windows/adapter.
  closes=[]
  for d in [days[0],days[-1]]:
   events=[a for a in actions if a[1]<=d]
   assert events
   factor=float(events[-1][2]); closes.append(float(rawmap[d]['close'])*factor)
  amount=math.fsum(float(rawmap[d]['amount']) for d in days[1:])/20
  values[day][code]=(amount,closes[1]/closes[0]-1)
checks=[]
for row in selected:
 vals=values[row['date']]; ordered=sorted(vals,key=lambda c:(-vals[c][0],c)); assert ordered==row['focus_members']
 mean=math.fsum(v[1] for v in vals.values())/len(vals); assert abs(mean-row['focus'])<1e-10
 checks.append({'date':row['date'],'members':len(vals),'direct_mean':mean,'builder_mean':row['focus'],'absolute_difference':abs(mean-row['focus']),'amount_order_verified':True})
years={}
for year in sorted({r['date'][:4] for r in rows}):
 rs=[r for r in rows if r['date'].startswith(year)]; valid=[r for r in rs if r['signal_valid']]
 years[year]={'days':len(rs),'valid_days':len(valid),'qualified_min':min(r['qualified_count'] for r in valid),'qualified_median':statistics.median(r['qualified_count'] for r in valid),'qualified_max':max(r['qualified_count'] for r in valid)}
result={'status':'passed','source_manifest_code_bound':True,'structure_all_days_verified':len(rows),'spot_checks':checks,'distinct_selected_codes_reread':len(codes),'source_files_reverified':len(verified),'year_coverage':years,'excluded_codes_by_reason':dict(Counter(v['excluded'].split(':')[0] for v in audit['per_code'].values() if 'excluded' in v)),'limitation':'Direct audit confirms selected returns and ordering, not whole-universe ranking independently; heap ranking separately covered by synthetic tests.'}
(D/'input-spot-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
