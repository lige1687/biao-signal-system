"""Build an explicit, unapplied research correction; never rewrite vendor payloads."""
from pathlib import Path
from decimal import Decimal as D
import hashlib,json,sys,datetime,shutil,os
HERE=Path(__file__).resolve().parent
ROOT=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
sys.path.insert(0,str(ROOT/'src'))
from lei_signal.research.output_storage import _still_mounted

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def table(j):return {r[0]:dict(zip(j['fields'],r,strict=True)) for r in j.get('rows',j.get('data',[]))}
def main():
 c=load(HERE/'overlay-contract.json')
 for b in c['bindings']:assert digest(b['path'])==b['sha256'],b['path']
 plan=load(HERE/'storage-plan.json');out=Path(plan['output']);assert _still_mounted(plan) and out.stat().st_dev==plan['external_device']
 assert shutil.disk_usage(out).free>=plan['external_reserve_bytes']+plan['estimated_bytes']
 assert shutil.disk_usage(ROOT).free>=plan['internal_reserve_bytes']+plan['internal_metadata_bytes']
 bridge=load(HERE/'frozen-source-bridge-check.json');review=load(HERE/'source-review.json');five=load(HERE/'five-price-field-review.json')
 assert bridge['all_common_fields_equal'] and five['exact_all_five_fields'] and five['rows']==1560
 frozen=bridge['frozen_source'];assert digest(frozen['path'])==frozen['sha256'];old=table(load(frozen['path']));legacy=table(load(out/'request-01.json'))
 factor=D(review['good_adjusted_overlap']['constant_ratio']);assert factor==D('0.91352') and review['good_adjusted_overlap']['ratio_min']==review['good_adjusted_overlap']['ratio_max']
 fields=['open','high','low','close','preclose'];changes=[]
 for date,row in sorted(old.items()):
  if row['adjustflag']=='2':continue
  assert row['adjustflag']=='3' and '2013-01-04'<=date<='2019-06-05'
  a=legacy[date];assert a['code']=='sz.000043' and a['adjustflag']=='2'
  changes.append({'date':date,'canonical_code':'sz.001914','source_adjustflag':row['adjustflag'],'source_price_values':{k:row[k] for k in fields},'legacy_code':'sz.000043','legacy_adjusted_values':{k:a[k] for k in fields},'derived_adjusted_values':{k:str(D(a[k])*factor) for k in fields},'formula':'legacy_adjusted_value * 0.91352'})
 assert len(changes)==1560 and len({r['date'] for r in changes})==1560
 target=out/'price-correction-overlay.json'
 body={'schema':'research.price-correction-overlay/1','created_at':datetime.datetime.now().astimezone().isoformat(),'status':'source_consistency_checked_not_applied','vendor_original':False,'source':frozen,'canonical_identity':'000043 -> 001914 effective2019-12-16','derived_price_basis':'forward-adjusted quotation normalized to the saved current-code source; not nominal execution prices','normalization':str(factor),'allowed_fields':fields,'original_source_adjustflag_preserved':True,'other_dates_and_fields':'read from unchanged frozen source; overlay supplies no replacements','evidence':c['bindings'],'changes':changes,'limits':['One-vendor consistency, not independent exchange certification or cash wealth.','First103 legacy dates observed constant0.889508; no independent pre-first-event factor record.','This envelope is not a vendor daily response or an accepted factor input. Adapter and complete600 input checks remain required.','No strategy effects, execution prices, original results or production rules changed.']}
 raw=(json.dumps(body,ensure_ascii=False,indent=2)+'\n').encode();assert _still_mounted(plan)
 with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 again=load(target);assert again['changes']==changes
 for b in c['bindings']:assert digest(b['path'])==b['sha256'],b['path']
 receipt={'at':datetime.datetime.now().astimezone().isoformat(),'contract_sha256':digest(HERE/'overlay-contract.json'),'output':{'path':str(target),'sha256':digest(target),'bytes':len(raw)},'rows':len(changes),'price_cells':len(changes)*5,'outside_rows_changed':0,'nonprice_fields_replaced':0,'all_bound_sources_unchanged':True,'applied_to_any_experiment':False,'new_market_outcomes':0}
 with (HERE/'overlay-receipt.json').open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
