"""Check an explicit price overlay while preserving original vendor flag failures."""
from pathlib import Path
from decimal import Decimal as D
from copy import deepcopy
import sys,json,hashlib,datetime
HERE=Path(__file__).resolve().parent
WT=HERE.parents[3]
sys.path.insert(0,str(WT/'src'))
from lei_signal.research.lowfreq_input_guard import inspect_contract
FIELDS=('open','high','low','close','preclose')
def load(p):return json.loads(Path(p).read_text())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table(j):return {r[0]:dict(zip(j['fields'],r,strict=True)) for r in j.get('data',j.get('rows',[]))}
def require(x,why):
 if not x:raise ValueError(why)
def check_overlay(overlay,original,legacy):
 require(overlay['schema']=='research.price-correction-overlay/1' and overlay['vendor_original'] is False,'not an explicit derived source')
 require(overlay['normalization']=='0.91352','unqualified normalization')
 changes=overlay['changes'];target={d for d,r in original.items() if r['adjustflag']=='3'}
 require(len(changes)==1560 and len({r['date'] for r in changes})==1560 and {r['date'] for r in changes}==target,'target date list differs')
 cells=0;unchanged=0
 for row in changes:
  require(set(row)=={'date','canonical_code','source_adjustflag','source_price_values','legacy_code','legacy_adjusted_values','derived_adjusted_values','formula'},'unexpected overlay field')
  day=row['date'];base=original[day];old=legacy[day]
  require(row['canonical_code']==base['code']=='sz.001914' and row['legacy_code']==old['code']=='sz.000043','security identity mismatch')
  require(row['source_adjustflag']==base['adjustflag']=='3' and old['adjustflag']=='2','source flag changed')
  require(row['formula']=='legacy_adjusted_value * 0.91352','formula differs')
  for key in ('source_price_values','legacy_adjusted_values','derived_adjusted_values'):require(set(row[key])==set(FIELDS),'nonprice or missing price field')
  projected=dict(base)
  for f in FIELDS:
   require(row['source_price_values'][f]==base[f],'original price mismatch')
   require(row['legacy_adjusted_values'][f]==old[f],'legacy source price mismatch')
   value=D(row['derived_adjusted_values'][f]);require(value.is_finite() and value==D(old[f])*D('0.91352'),'derived number differs')
   projected[f]=str(value);cells+=1
  require(all(projected[k]==v for k,v in base.items() if k not in FIELDS),'nonprice changed')
  unchanged+=sum(k not in FIELDS for k in base)
  prices={f:D(projected[f]) for f in FIELDS}
  if base['tradestatus']=='1':
   require(all(v>0 for v in prices.values()),'nonpositive traded price')
   require(prices['low']<=min(prices['open'],prices['close']) and prices['high']>=max(prices['open'],prices['close']) and prices['high']>=prices['low'],'derived OHLC ordering')
 return {'rows':len(changes),'price_cells':cells,'nonprice_cells_checked_unchanged_on_target_rows':unchanged,'untouched_dates':len(original)-len(changes),'source_flags_rewritten':0}
def main():
 c=load(HERE/'derived-input-contract.json')
 for b in c['bindings']:require(digest(b['path'])==b['sha256'],'bound source changed: '+b['path'])
 overlay=load(c['overlay']['path']);source=overlay['source'];require(digest(source['path'])==source['sha256'],'frozen original changed')
 original=table(load(source['path']));legacy=table(load(c['legacy_adjusted']['path']))
 mutation_tests=[]
 cases=[('source_flag',lambda x:x['changes'][0].update(source_adjustflag='2')),('outside_date',lambda x:x['changes'][0].update(date='2025-01-01')),('wrong_number',lambda x:x['changes'][0]['derived_adjusted_values'].update(close='123')),('change_activity',lambda x:x['changes'][0]['derived_adjusted_values'].update(volume='123')),('wrong_original',lambda x:x['changes'][0]['source_price_values'].update(close='123')),('wrong_scale',lambda x:x.update(normalization='1'))]
 for name,change in cases:
  altered=deepcopy(overlay);change(altered)
  try:check_overlay(altered,original,legacy)
  except (ValueError,KeyError):mutation_tests.append({'name':name,'rejected':True})
  else:raise ValueError('bad overlay accepted: '+name)
 overlay_check=check_overlay(overlay,original,legacy)
 # This call checks all600 original sources. Its original failure remains explicit.
 base=inspect_contract(c['base_contract']['path'])
 require(base['source_count']==600 and base['row_count']==1852185,'base source scope drift')
 require(set(base['blockers'])=={'returned_adjustflag'},'new unrelated blocker')
 b=base['blockers']['returned_adjustflag'];require(b['count']==1560 and b['by_code']=={'sz.001914':1560},'original failure differs')
 for binding in c['bindings']:require(digest(binding['path'])==binding['sha256'],'bound source changed after checks')
 result={'at':datetime.datetime.now().astimezone().isoformat(),'status':'derived_source_consistency_checked_evaluator_integration_required','contract_sha256':digest(HERE/'derived-input-contract.json'),'original_input_status':base['status'],'original_checks':base,'overlay_checks':overlay_check,'invalid_overlay_tests':mutation_tests,'market_statistics_calls':0,'old_evaluator_compatible':False,'restored_evaluation_months_claimed':0,'qualified_use':'Bounded historical adjusted-quotation diagnostic only, after explicit evaluator integration; not nominal execution, point-in-time fundamentals, ETF or account trading.','reason':'All original source checks executed; only the known flag issue persists in originals. Overlay addresses the price interpretation explicitly without converting vendor source flag3 to2. Old direct evaluator remains blocked.'}
 with (HERE/'derived-input-review.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ['status','original_input_status','overlay_checks','market_statistics_calls','old_evaluator_compatible']},ensure_ascii=False))
if __name__=='__main__':main()
