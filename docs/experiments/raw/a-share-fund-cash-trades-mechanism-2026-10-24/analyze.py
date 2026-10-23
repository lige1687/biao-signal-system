"""One frozen descriptive fund-half-year behavior matrix, no prices or fits."""
import json,hashlib,datetime,statistics,sys
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parent;ROOT=R.parents[3]
def read(path):return json.loads(Path(path).read_text())
def cell(rows):
 if not rows:return {'n':0,'net_selling_n':0,'net_buying_n':0,'zero_n':0,'net_selling_fraction':None,'median_net_sale_cny':None,'median_net_sale_over_nav':None,'D_over_nav_range':None,'periods':[]}
 n=len(rows);ys=[D(r['net_stock_sell_cny']) for r in rows];ratio=[D(r['net_stock_sell_cny'])/D(r['open_nav_cny']) for r in rows];ds=[D(r['D_cny'])/D(r['open_nav_cny']) for r in rows]
 return {'n':n,'net_selling_n':sum(y>0 for y in ys),'net_buying_n':sum(y<0 for y in ys),'zero_n':sum(y==0 for y in ys),'net_selling_fraction':sum(y>0 for y in ys)/n,'median_net_sale_cny':str(statistics.median(ys)),'median_net_sale_over_nav':str(statistics.median(ratio)),'D_over_nav_range':[str(min(ds)),str(max(ds))],'periods':[r['period'] for r in rows]}
def main():
 assert '--execute' in sys.argv
 freeze=read(R/'freeze.json')
 for p,h in freeze['bindings'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 inputs=read(R/'inputs.json');rows=inputs['half_years'];assert len(rows)==28;result=[];cases=[];years=[]
 for definition in ['report','adjusted_conditional']:
  q=[]
  for row in rows:
   x=dict(row);x['D_cny']=x['D_report_cny'] if definition=='report' else x['D_adjusted_cny'];x['definition']=definition;x['D_minus_C0_cny']=str(D(x['D_cny'])-D(x['C0_cny']));q.append(x);cases.append(x)
  for fund in ['070002','000001']:
   f=[x for x in q if x['fund_code']==fund];positive=[x for x in f if D(x['D_cny'])>0];other=[x for x in f if D(x['D_cny'])<=0];above=[x for x in positive if D(x['D_cny'])>D(x['C0_cny'])];below=[x for x in positive if D(x['D_cny'])<=D(x['C0_cny'])]
   stats={name:cell(x) for name,x in [('all',f),('net_redemption',positive),('non_net_redemption',other),('redemption_above_C0',above),('redemption_at_or_below_C0',below)]}
   ranges=[stats[k]['D_over_nav_range'] for k in ['redemption_above_C0','redemption_at_or_below_C0']]
   overlap=None if any(x is None for x in ranges) else max(D(x[0]) for x in ranges)<=min(D(x[1]) for x in ranges)
   unconditional=stats['net_redemption']['net_selling_fraction'];gap_fraction=stats['redemption_above_C0']['net_selling_fraction'];covered_fraction=stats['redemption_at_or_below_C0']['net_selling_fraction']
   result.append({'definition':definition,'fund_code':fund,'groups':stats,'cash_cells_redemption_size_ranges_overlap':overlap,'cash_extra_effect_identified':False,'cash_identification_note':'missing or nonoverlapping cells' if overlap is not True else 'range overlap does not control magnitude or time; descriptive only','gap_minus_all_net_redemption_selling_rate':None if gap_fraction is None or unconditional is None else gap_fraction-unconditional,'covered_minus_all_net_redemption_selling_rate':None if covered_fraction is None or unconditional is None else covered_fraction-unconditional,'counterexample_periods':[x['period'] for x in positive if D(x['net_stock_sell_cny'])<=0],'above_C0_counterexamples':[x['period'] for x in above if D(x['net_stock_sell_cny'])<=0]})
  for year in range(2019,2026):
   qs=[x for x in q if x['period'].startswith(str(year))];pos=[x for x in qs if D(x['D_cny'])>0];years.append({'definition':definition,'year':year,'fund_halves':len(qs),'redemption_cases':len(pos),'redemption_and_net_sell':sum(D(x['net_stock_sell_cny'])>0 for x in pos),'redemption_but_net_buy_or_zero':[x['fund_code']+' '+x['period'] for x in pos if D(x['net_stock_sell_cny'])<=0]})
 plan=read(R/'storage-plan.json');sys.path.insert(0,str(ROOT/'src'));from lei_signal.research.output_storage import plan_output
 live=plan_output(ROOT,plan['task_id'],plan['estimated_bytes'],internal_bytes=plan['internal_metadata_bytes']);assert live['external_uuid']==plan['external_uuid'] and live['external_device']==plan['external_device'];base=Path(plan['output']);base.mkdir(parents=True,exist_ok=True);assert base.stat().st_dev==plan['external_device'];out=base/'behavior';assert not out.exists();out.mkdir()
 summary={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'question':'contemporaneous reported net redemption and net stock transactions; no causal or trading claim','fund_half_years':28,'shared_half_years':14,'funds':2,'definition_versions':2,'matrix_runs':1,'fits':0,'new_price_or_return_runs':0,'results':result,'by_year':years,'source_and_code_freeze':str(R/'freeze.json'),'out':str(out)}
 (out/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n');(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(R/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'rows':len(rows),'results':result},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
