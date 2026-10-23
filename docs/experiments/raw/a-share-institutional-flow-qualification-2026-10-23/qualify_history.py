"""Cross-period fund input qualification. No market prices or future outcomes."""
import json,datetime,hashlib,csv
from decimal import Decimal as D
from pathlib import Path
R=Path(__file__).resolve().parent
jp=R/'jiashi-history/qualification.json';hp=R/'huaxia-history/history-series.json'
j=json.loads(jp.read_text());h=json.loads(hp.read_text());assert j['periods_passed']==14 and len(h['reports'])==14
J={v['period']:v for v in j['reports']};H={v['key']:v for v in h['reports']}
def norm(v,kind):
 if kind=='J':return dict(open_units=D(v['opening_units']),sub_units=D(v['subscriptions_units']),red_units=D(v['redemptions_units']),close_units=D(v['closing_units']),open_nav=D(v['opening_net_assets_cny']),close_nav=D(v['closing_net_assets_cny']),sub_amount=D(v['subscription_net_asset_change_cny']),red_amount=-D(v['redemption_net_asset_change_cny']),pub=v['official_pub_date'],pdf=v['pdf_path'])
 f=v['flow'];n=v['financial']
 return dict(open_units=D(f['opening']),sub_units=D(f['subscriptions']),red_units=D(f['redemptions']),close_units=D(f['closing']),open_nav=D(n['net_assets_open_cny']),close_nav=D(n['net_assets_close_cny']),sub_amount=D(n['subscription_transaction_cny']),red_amount=-D(n['redemption_transaction_cny_signed']),pub=v['announcement_date'],pdf=v['pdf_path'])
series={};bridges=[]
for code,src,kind in [('070002',J,'J'),('000001',H,'H')]:
 series[code]={}
 for yr in range(2019,2026):
  a,b=norm(src[f'{yr}H1'],kind),norm(src[f'{yr}FY'],kind)
  assert a['open_units']+a['sub_units']-a['red_units']==a['close_units']
  assert b['open_units']+b['sub_units']-b['red_units']==b['close_units']
  assert a['open_units']==b['open_units'] and a['open_nav']==b['open_nav']
  c=dict(open_units=a['close_units'],close_units=b['close_units'],open_nav=a['close_nav'],close_nav=b['close_nav'],sub_units=b['sub_units']-a['sub_units'],red_units=b['red_units']-a['red_units'],sub_amount=b['sub_amount']-a['sub_amount'],red_amount=b['red_amount']-a['red_amount'],pub=max(a['pub'],b['pub']),pdf=b['pdf'])
  assert c['open_units']+c['sub_units']-c['red_units']==c['close_units']
  if yr>2019:
   prev=norm(src[f'{yr-1}FY'],kind);bridges.append({'fund':code,'year':yr,'unit_bridge':str(a['open_units']-prev['close_units']),'nav_bridge':str(a['open_nav']-prev['close_nav'])})
  for k,v in [(f'{yr}H1',a),(f'{yr}H2',c)]:
   assert v['open_nav']>0 and v['open_units']>0 and v['sub_units']>=0 and v['red_units']>=0
   v['net_redemption_fraction_amount']=(v['red_amount']-v['sub_amount'])/v['open_nav'];v['pressure_amount']=max(v['net_redemption_fraction_amount'],D(0));v['net_redemption_fraction_units']=(v['red_units']-v['sub_units'])/v['open_units'];v['pressure_units']=max(v['net_redemption_fraction_units'],D(0));series[code][k]={z:str(w) if isinstance(w,D) else w for z,w in v.items()}
rows=[]
for period in sorted(series['070002']):
 a=series['070002'][period];b=series['000001'][period];sign=lambda x:1 if x>0 else -1 if x<0 else 0
 d=D(a['pressure_amount'])-D(b['pressure_amount']);u=D(a['pressure_units'])-D(b['pressure_units']);yr=int(period[:4]);start_key=f'{yr}H1' if period.endswith('H2') else f'{yr-1}FY'
 rows.append({'period':period,'jiashi_amount_pressure':a['pressure_amount'],'huaxia_amount_pressure':b['pressure_amount'],'amount_direction':sign(d),'unit_direction':sign(u),'direction_agrees':sign(d)==sign(u),'necessary_reports_public_date':max(a['pub'],b['pub']),'start_holdings_period':start_key,'start_holdings_available':start_key in J and start_key in H})
valid=[v for v in rows if v['start_holdings_available']];nonzero=[v['amount_direction'] for v in valid if v['amount_direction']]
x={'at':datetime.datetime.now().astimezone().isoformat(),'source_bindings':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [jp,hp]},'reports_total':28,'funds':series,'cross_year_bridges':bridges,'periods':rows,'forming_periods_with_lag_holdings':len(valid),'amount_direction_switches_nonzero':sum(a!=b for a,b in zip(nonzero,nonzero[1:])),'definition_disagreements':sum(not v['direction_agrees'] for v in valid),'effect_data_read':False,'main_definition_reason':'fund share transaction CNY divided by beginning NAV matches asset-size mechanism; no outcome-driven choice','not_verified_external_cash':True}
(R/'history-comparison.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'reports':28,'bridges':bridges,'periods':rows,'switches':x['amount_direction_switches_nonzero'],'definition_disagreements':x['definition_disagreements']},ensure_ascii=False))
