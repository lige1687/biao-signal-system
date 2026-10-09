"""Artificial-only regression of two independent review findings."""
import runpy
from pathlib import Path
n=runpy.run_path(str(Path(__file__).with_name('effect_runner.py')),run_name='repair_test')
assert n['accepted_single_pass']({'status':'accepted_once','effect_passes':1})
for value in [True,False,1.0,'1',0,2,None]:
 assert not n['accepted_single_pass']({'status':'accepted_once','effect_passes':value})
rows=[]
for g in range(3):
 for j in range(4):
  rows.append(dict(asset='A',case_id=f'A-{g}-{j}',signal_date='2025-01-01',lifecycle=f'A-G{g}-L{j//2}',v_group=g,X=j+g*5,V=g*10+j,D=j+1))
yrows=[dict(r,Y=(i%4)+1,label_reason=None,V_volatility_pct=r['V'],D_frozen=r['D']) for i,r in enumerate(rows)]
for i in range(64):
 yrows.append(dict(asset='Z',case_id=f'Z{i}',signal_date='2025-01-01',lifecycle=f'Z-G{i%27}'))
support=dict(selected=rows,all_cases=yrows)
z=n['effect_result'](support,dict(schema='native-risk-d-mae-real-y/1',mature_count=75,rows=yrows))
assert z['main']['equal_asset_mean']['conditional_mean3'] is None
assert z['main']['per_asset']['A']['conditional_mean3']==1
assert len(z['delete_33'])==33
r=next(t for t in z['delete_33'] if t['lifecycle']=='A-G1-L0')
assert r['affected'] and r['fixed_conditional_assets']==['A']
assert r['per_asset']['A']['conditional_mean3'] is None
assert r['per_asset']['A']['conditional']['1']['n']==2
assert r['per_asset']['A']['conditional']['1']['V_min']==12
assert r['per_asset']['A']['conditional']['1']['V_max']==13
r=next(t for t in z['delete_33'] if t['asset']=='Z')
assert not r['affected'] and r['per_asset']['A']['conditional_mean3']==1
print('PASS: strict integer permit; lone-asset conditional deletion retained; unaffected groups preserved; V ranges')
