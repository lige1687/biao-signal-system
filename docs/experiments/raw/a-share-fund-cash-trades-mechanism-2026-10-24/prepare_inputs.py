"""Build the fixed two-fund historical disclosure comparison; no grouped statistics."""
import json,hashlib,datetime
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parent;OLD=R.parent/'a-share-institutional-flow-qualification-2026-10-23'
def read(p):return json.loads(p.read_text())
def main():
 contract=read(R/'contract.json')
 for p,h in contract['prior_inputs'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
 old=read(OLD/'history-comparison.json');adjusted={x['period']:x for x in read(OLD/'adjusted-history-comparison.json')['periods']};rows=[];checks=[];reclasses=[]
 for folder,fund in [('jiashi','070002'),('huaxia','000001')]:
  data=read(R/folder/'reports.json');assert len(data['reports'])==14;assert not data.get('failures',data.get('reports_failed',[]));by={x['period']:x for x in data['reports']};assert len(by)==14
  for report in by.values():
   assert hashlib.sha256(Path(report['pdf_path']).read_bytes()).hexdigest()==report['pdf_sha256']
   assert D(report['bank_current_cny'])+D(report['settlement_current_cny'])==D(report['combined_current_cny'])
  for year in range(2019,2026):
   h,f=by[f'{year}H1'],by[f'{year}FY']
   for field in ['bank_prior_year_end_cny','settlement_prior_year_end_cny']:assert D(h[field])==D(f[field]),(fund,year,field)
   if year>2019:
    prev=by[f'{year-1}FY']
    for part in ['bank','settlement']:
     delta=D(h[part+'_prior_year_end_cny'])-D(prev[part+'_current_cny']);checks.append({'fund_code':fund,'year':year,'component':part,'cross_year_residual_cny':str(delta)})
     if delta:reclasses.append(checks[-1])
   for half in [1,2]:
    period=f'{year}H{half}';report=h if half==1 else f;flow=old['funds'][fund][period];adj=adjusted[period]['funds'][fund]
    buy=D(h['buy_total_cny']) if half==1 else D(f['buy_total_cny'])-D(h['buy_total_cny']);sell=D(h['sell_total_cny']) if half==1 else D(f['sell_total_cny'])-D(h['sell_total_cny']);assert buy>=0 and sell>=0
    b=D(h['bank_prior_year_end_cny']) if half==1 else D(h['bank_current_cny']);s=D(h['settlement_prior_year_end_cny']) if half==1 else D(h['settlement_current_cny']);nav=D(flow['open_nav']);assert nav>0 and b>=0 and s>=0
    raw=D(flow['red_amount'])-D(flow['sub_amount']);adjust=raw+D(adj['reinvest_cny']);assert adjust/nav==D(adj['unclipped_adjusted_fraction'])
    pub=report.get('actual_publication_date',report.get('announcement_date'));assert pub==flow['pub']
    rows.append({'fund_code':fund,'period':period,'period_start':f'{year}-01-01' if half==1 else f'{year}-07-01','period_end':f'{year}-06-30' if half==1 else f'{year}-12-31','available_report_date':pub,'stock_buy_gross_cny':str(buy),'stock_sell_gross_cny':str(sell),'net_stock_sell_cny':str(sell-buy),'open_nav_cny':str(nav),'bank_open_cny':str(b),'settlement_open_cny':str(s),'C0_cny':str(b+s),'D_report_cny':str(raw),'reinvestment_cny':adj['reinvest_cny'],'cash_distribution_cny':adj['cash_distribution_cny'],'D_adjusted_cny':str(adjust),'cash_source_report':h['period'],'cash_source_column':'prior-year-end' if half==1 else 'current-end','trade_source_reports':[h['period']] if half==1 else [f['period'],h['period']],'source_current_pdf_sha256':report['pdf_sha256'],'source_h1_pdf_sha256':h['pdf_sha256'],'retrospective_only':True})
 assert len(rows)==28 and len({(x['fund_code'],x['period']) for x in rows})==28
 result={'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'half_years':rows,'component_cross_year_checks':checks,'nonzero_cross_year_changes':reclasses,'zero_missing_new_fields':True,'grouped_behavior_stats_computed':False,'interpretation':'reported stock transaction totals exclude fees; balances are book snapshots, not timing of available cash or forced-selling cause'}
 (R/'inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'fund_halves':len(rows),'cross_year_component_checks':len(checks),'nonzero_changes':len(reclasses),'grouped_stats_computed':False}))
if __name__=='__main__':main()
