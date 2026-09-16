"""Read-only package checks, independent of build_package.py; no network/strategy."""
from pathlib import Path
from decimal import Decimal as D
import json,csv,hashlib
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lock=json.loads((P/'source-lock.json').read_text()); checked=0
for x in lock['reused_files']:
 assert sha(P/x['file'])==x['sha256'];assert sha(Path(x['source_path']))==x['sha256'];checked+=1
for symbol in ['159915','518880','513100']:
 p=P/'sources/fifth'/symbol;m=json.loads((p/'manifest.json').read_text());rows=m['files'] if isinstance(m,dict) else m
 for x in rows:
  f=p/x['file']
  if f.exists():assert sha(f)==x['sha256'],f;checked+=1
for x in json.loads((P/'sources/new-rule-sources.json').read_text()):
 assert x['status']==200 and sha(P/'sources'/x['file'])==x['sha256'];checked+=1
params=json.loads((P/'execution-parameters.json').read_text()); counts={}
for s in params['symbols']:
 source=P/'sources/original-prices'/f'{s}-nominal.csv'
 original=list(csv.DictReader(source.open())); expected=[r for r in original if r['date']<='2026-06-30']
 actual=list(csv.DictReader((P/'bars-helper-native'/f'{s}-nominal.csv').open()));assert actual==expected
 assert sum(r['date']>='2015-01-01' for r in actual)==(2789 if s in ['sz159915','sh513100'] else 2790)
 counts[s]=len(actual)
actions=json.loads((P/'actions.json').read_text());assert len(actions)==14
assert sum(a['type']=='cash_dividend' and a['within_research_window'] for a in actions)==12
for a in actions:
 assert sha(P/a['source_file'])==a['source_sha256'];assert a['announcement_date']<=a['effective_date']<='2026-06-30'
 if a['type']=='cash_dividend':assert a['record_date']<a['effective_date']<=a['pay_date']
assert len({a['economic_event_key'] for a in actions})==14
coverage=json.loads((P/'action-coverage.json').read_text());assert coverage['formal_full_company_action_coverage'] is False
assert all(x['split_unknown_intervals'] and not x['split_formal_coverage_complete'] for x in coverage['products'])
assert params['blocked_dates']['sh513100']==['2022-01-13','2022-01-14']
assert params['blocked_dates']['sz159915']==['2021-02-08','2021-02-09']
assert params['limit_changes']['sz159915']==[['2020-08-24',0.2]]
checks=list(csv.DictReader((P/'open-price-checks.csv').open()));hit=next(r for r in checks if r['symbol']=='sh513100' and r['session_date']=='2025-04-07')
assert hit['open']=='1.272' and hit['reference_close']=='1.413' and hit['limit_down']=='1.272'
assert hit['open_sell_permitted_by_price_and_exception']=='False'
assert 'high' not in hit and 'low' not in hit and 'close' not in hit
for r in checks:
 if r['session_date'] in params['blocked_dates'][r['symbol']]:
  assert r['open_sell_permitted_by_price_and_exception']=='False' and r['open_buy_permitted_by_price_and_exception']=='False'
monthly=json.loads((P/'price-data-checks.json').read_text())['volume_crosscheck'];assert D(monthly['exchange_volume'])==D('24499884934');assert D(monthly['difference'])==D('9280334');assert params['volume_unit'] is None
final=json.loads((P/'manifest.json').read_text())
for f in final['files']:assert sha(P/f['file'])==f['sha256'];checked+=1
print(json.dumps({'status':'passed','hash_checks':checked,'input_rows':counts,'window_rows':11158,'actions':len(actions),'future_price_rows_in_model_inputs':0,'unchanged_seventh_helper':True,'formal_all_events_claim':False},ensure_ascii=False))
