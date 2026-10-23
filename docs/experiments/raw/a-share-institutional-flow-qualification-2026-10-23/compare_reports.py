"""One-interval input identifiability; no prices, future returns or fitting."""
import csv,hashlib,json,math,datetime
from pathlib import Path
from decimal import Decimal as D
R=Path(__file__).resolve().parent
out=Path(json.loads((R/'storage-plan.json').read_text())['output'])/'comparison'
assert not out.exists(), 'Do not overwrite an existing comparison'
h=json.loads((R/'huaxia/fields.json').read_text())
jr=R.parent/'institutional-flow-return-study-2026-10-23/cn-source-qualification'
j=json.loads((jr/'070002-2024FY-fields.json').read_text())
old=Path('/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china/070002-holdings.csv')
def rows(p,period=None):
 with Path(p).open() as f:a=list(csv.DictReader(f))
 if period:a=[v for v in a if v['period_end']==period]
 assert len(a)==len({v['stock_code'] for v in a})
 return {v['stock_code']:v for v in a}
paths=[old,jr/'070002-2024FY-holdings.csv',Path(h['2024H1']['holdings_csv']),Path(h['2024FY']['holdings_csv'])]
f={'070002':[rows(paths[0],'2024-06-30'),rows(paths[1])],'000001':[rows(paths[2]),rows(paths[3])]}
flows={'070002':{k.replace('_units',''):D(v) for k,v in j['derived_2024H2_flow'].items()},'000001':{k:D(v) for k,v in h['2024H2_derived_flow'].items()}}
for v in flows.values():assert v['opening']+v['subscriptions']-v['redemptions']==v['closing']
p={k:max((v['redemptions']-v['subscriptions'])/v['opening'],D(0)) for k,v in flows.items()}
summary={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'scope':'Two named selected funds, 2024H2; no return data read','funds':{},'sources':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in paths},'net_cash_interpretation':False,'causal_or_active_discretionary_interpretation':False}
for fund,(start,end) in f.items():
 summary['funds'][fund]={'start_holdings':len(start),'end_holdings':len(end),'union':len(set(start)|set(end)),'both':len(set(start)&set(end)),'new_in_report':len(set(end)-set(start)),'absent_from_end_report':len(set(start)-set(end)),'h2_units':{k:str(v) for k,v in flows[fund].items()},'net_redemption_unit_fraction':float(p[fund]),'start_value':str(sum(D(v['fair_value_cny']) for v in start.values())),'end_value':str(sum(D(v['fair_value_cny']) for v in end.values()))}
initial=set(f['070002'][0])|set(f['000001'][0]);joint=set(f['070002'][0])&set(f['000001'][0]);allfour=joint & set(f['070002'][1]) & set(f['000001'][1])
pressure=[]
for code in sorted(initial):
 a=D(f['070002'][0].get(code,{}).get('fair_value_cny','0'));b=D(f['000001'][0].get(code,{}).get('fair_value_cny','0'));w=a/(a+b);x=(a*p['070002']+b*p['000001'])/(a+b);linear=p['000001']+(p['070002']-p['000001'])*w
 pressure.append(dict(code=code,jiashi_fraction=str(w),pressure=str(x),linear_identity_residual=str(x-linear)))
q=[]
for code in sorted(allfour):
 vals=[D(f[fund][t][code]['shares'].replace(',','')) for fund in ['070002','000001'] for t in [0,1]]
 assert all(v>0 for v in vals)
 q.append({'code':code,'name_start':f['070002'][0][code]['stock_name'],'jiashi_q0':str(vals[0]),'jiashi_q1':str(vals[1]),'huaxia_q0':str(vals[2]),'huaxia_q1':str(vals[3]),'relative_share_ratio':float((vals[1]/vals[0])/(vals[3]/vals[2])),'log_relative_share_ratio':math.log(float((vals[1]/vals[0])/(vals[3]/vals[2]))),'interpretation':'reported share-count ratio only; common proportional share changes cancel; differential events not verified'})
summary.update(initial_union=len(initial),initial_common=len(joint),final_union=len(set(f['070002'][1])|set(f['000001'][1])),final_common=len(set(f['070002'][1])&set(f['000001'][1])),four_observation_common=len(allfour),pressure_values_unique=len({v['pressure'] for v in pressure}),pressure_affine_max_residual=max(float(abs(D(v['linear_identity_residual']))) for v in pressure),relative_share_ratios=q,returns_calculated=False,IC_evaluated=False,independent_cross_sectional_information_after_ownership=0)
assert summary['pressure_affine_max_residual']<1e-24
out.mkdir(parents=True)
for name,data in [('pressure-by-code.csv',pressure),('relative-reported-shares.csv',q)]:
 if data:
  with (out/name).open('w') as file:
   w=csv.DictWriter(file,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(R/'comparison-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
