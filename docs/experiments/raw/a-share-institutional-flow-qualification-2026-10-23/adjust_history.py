"""Conditional reinvestment adjustment, defined before future price changes."""
import json,hashlib,datetime
from decimal import Decimal as D
from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'history-comparison.json';x=json.loads(p.read_text());jp=R/'jiashi-history/reinvestment-by-half.json';hp=R/'huaxia-history/reinvestment-by-half.json'
j=json.loads(jp.read_text());h=json.loads(hp.read_text());div={'070002':{f"{v['year']}H{v['half']}":v for v in j['half_years']},'000001':{v['period']:v for v in h['halves']}}
rows=[]
for v in x['periods']:
 ps={}
 for code in ['070002','000001']:
  a=x['funds'][code][v['period']];r=D(div[code][v['period']]['dividend_reinvestment_cny']);cash=D(div[code][v['period']]['cash_dividend_cny']);signed=(D(a['red_amount'])-D(a['sub_amount'])+r)/D(a['open_nav']);ps[code]={'reinvest_cny':str(r),'cash_distribution_cny':str(cash),'unclipped_adjusted_fraction':str(signed),'adjusted_pressure':str(max(signed,D(0)))}
 d=D(ps['070002']['adjusted_pressure'])-D(ps['000001']['adjusted_pressure']);direction=1 if d>0 else -1 if d<0 else 0
 rows.append({**v,'raw_direction':v['amount_direction'],'adjusted_direction':direction,'adjustment_changes_direction':direction!=v['amount_direction'],'funds':ps})
y={'at':datetime.datetime.now().astimezone().isoformat(),'definition':'max((redemptions - subscriptions + reinvestment)/beginning net assets, 0); cash distribution separate','evidence_limit':'Huaxia inclusion of reinvestment in subscription line is supported accounting-structure inference, no verbatim footnote; both report and conditional adjusted versions will be evaluated, no version selected by outcome','periods':rows,'source_bindings':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [p,jp,hp]},'future_prices_read':False}
(R/'adjusted-history-comparison.json').write_text(json.dumps(y,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{'period':v['period'],'raw':v['raw_direction'],'adjusted':v['adjusted_direction']} for v in rows],ensure_ascii=False))
