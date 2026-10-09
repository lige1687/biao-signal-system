"""Artificial-only checks; no saved source or Y is loaded."""
import runpy
from pathlib import Path

ns = runpy.run_path(str(Path(__file__).with_name('effect_runner.py')), run_name='synthetic_import')
ranks, rho, supported, evaluate = (ns[k] for k in ('ranks','rho','supported','evaluate'))
assert ranks([1,1,2,3]) == [1.5,1.5,3.0,4.0]
assert [min(2,int(3*(r-.5)//4)) for r in ranks([1,1,2,3])] == [0,0,1,2]
assert rho([1,2,3,4],[4,3,2,1]) == -1.0
assert rho([1,1,1,1],[1,2,3,4]) is None
assert not supported([{'lifecycle':'L1','X':i,'Y':i} for i in range(4)],'X')

def block(asset):
    out=[]
    for g in range(3):
        for j in range(4):
            out.append({'asset':asset,'case_id':f'{asset}-{g}-{j}','lifecycle':f'{asset}-G{g}-L{j//2}',
                        'v_group':g,'X':float(j+g*5),'V':float(g*10+j),
                        'D':float(j+1),'Y':float(j+1)})
    return out

rows=block('A')+block('B')
base=evaluate(rows)
assert base['fixed_marginal_assets']==['A','B']
assert base['fixed_conditional_assets']==['A','B']
assert base['equal_asset_mean']['conditional_mean3']==1.0
deleted=[r for r in rows if r['lifecycle']!='B-G1-L0']
trial=evaluate(deleted,base['fixed_marginal_assets'],base['fixed_conditional_assets'])
assert trial['per_asset']['B']['conditional']['1']['rho_X_Y'] is None
assert trial['equal_asset_mean']['conditional_mean3'] is None
assert trial['fixed_conditional_assets']==['A','B']
missing=[r for r in rows if r['asset']!='B']
assert evaluate(missing,base['fixed_marginal_assets'],base['fixed_conditional_assets'])['equal_asset_mean']['X'] is None
unaffected=evaluate(rows,base['fixed_marginal_assets'],base['fixed_conditional_assets'])
assert unaffected['equal_asset_mean']==base['equal_asset_mean']
print('synthetic_pass: ties, constant, 4/2 support, missing group, fixed assets, delete, unaffected')
