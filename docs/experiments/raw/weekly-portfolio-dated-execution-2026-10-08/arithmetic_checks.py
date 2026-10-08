"""Read-only independent Decimal arithmetic; does not import the ledger."""
from pathlib import Path
from decimal import Decimal as D
import json
BASE=Path(__file__).resolve().parent
traces=json.loads((BASE/'event-receipts.json').read_text())
checks=[]
def check(label,actual,expected,reason):
    assert D(actual)==D(expected),(label,actual,expected)
    checks.append({'label':label,'actual':actual,'expected':str(expected),'formula':reason})

a=traces['test_group1_lots_repeat_open_weekend_holiday']
for r in a:
    if r['accepted']:
        check('group1 conserved assets '+r['event']['id'],r['state']['equity'],D(200)+D(100)*2,'opening cash200 + original100*2 =400; fee0')
check('same opening sellable',a[1]['state']['sellable']['A'],100,'original lot100; new100 release on Jan6')
check('explicit Jan6 release',a[-1]['state']['sellable']['A'],200,'original100 + newly released100')
b=traces['test_group2_paid_after_open_target_qualification']
for r in b:
    if r['accepted']:
        check('group2 assets '+r['event']['id'],r['state']['equity'],200,'100 shares*2 sold; no fees; restricted and free are same asset')
arrival=next(r for r in b if r['event']['id']=='arrive')
check('Jan6 10:00 cash',arrival['state']['free_cash'],200,'payment at10:00; Jan6 09:30 earlier opening cannot be reused')
c=traces['test_group3_mixed_free_restricted_and_sale_fee']
check('mixed free remains usable',c[0]['state']['free_cash'],100,'initial free100 unaffected by restricted sale200')
check('mixed restricted',c[0]['state']['restricted_cash'],200,'100 sold*2 fee0')
check('cash after release',c[-1]['state']['free_cash'],300,'free100 + restricted200')
check('assets after release',c[-1]['state']['equity'],300,'cash conversion does not create assets')
d=traces['test_group4_split_all_lots_entitlement_preserved']
split=next(r for r in d if r['accepted'] and r['event']['kind']=='split')
check('split total',split['state']['shares']['A'],400,'(released100 + pending100)*2')
check('split sellable',split['state']['sellable']['A'],200,'only original released100*2')
check('split receivable preserved',split['state']['receivable'],10,'locked100*.1; not multiplied by2')
check('split mark conversion',split['state']['equity'],390,'400*.95+10=390; prior dividend effective mark1.9 was explicit synthetic assumption')
sale=next(r for r in d if r['accepted'] and r['event']['kind']=='sell')
check('subsequent price jump explicitly counted',sale['state']['equity'],810,'sold200*2 + remaining200*2 + receivable10; fixture next-open price2 differs from split mark.95')
e=traces['test_group5_payment_due_and_units_unchanged']
check('unpaid assets',e[0]['state']['equity'],200,'100*1.9+10')
check('paid assets',e[-1]['state']['equity'],200,'100*1.9+cash10')
check('paid accounting units',e[-1]['state']['units'],1000,'payment is internal asset transfer, units unchanged')
f=traces['test_13_ex_dividend_deposit_prior_complete_nav']
check('deposit units',f[0]['state']['units'],1100,'prior saved NAV1: original1000 + deposit100/1')
check('ex dividend assets',f[-1]['state']['equity'],1100,'cash100 + stock100*9 + receivable100')
checks.append({'label':'known wrong ex-dividend mixture','wrong_nav':str(D(1000+100)/1000),
               'wrong_result_nav':str(D(1100)/(D(1000)+D(100)/D('1.1'))),
               'correct_result_nav':'1','formula':'old nominal mark1000 + today receivable100 is wrong deposit denominator'})
result={'command':'python3 -B '+str(BASE/'arithmetic_checks.py'),'exit_code':0,
        'checks':checks,'scope':'Independent arithmetic from saved receipts; not a second ledger implementation'}
(BASE/'independent-arithmetic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('independent arithmetic checks:',len(checks),'exit0')
