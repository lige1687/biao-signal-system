"""Read saved v2 receipts and recompute critical amounts without importing ledger."""
from pathlib import Path
from decimal import Decimal as D
import json
BASE=Path(__file__).resolve().parent
traces=json.loads((BASE/'event-receipts-v2-final.json').read_text())
steps=json.loads((BASE/'event-step-money-receipts-v2.json').read_text())
checks=[]
def check(name,actual,expected,formula):
    assert D(actual)==D(expected),(name,actual,expected)
    checks.append({'name':name,'actual':str(actual),'expected':str(expected),'formula':formula})

for r in traces['test_group1_lots_repeat_open_weekend_holiday']:
    if r['accepted']:
        check('group1 assets '+r['event']['id'],r['state']['equity'],400,'initial200cash + original100*2; buy fee0')
for r in traces['test_group2_paid_after_open_target_qualification']:
    if r['accepted']:
        check('group2 assets '+r['event']['id'],r['state']['equity'],200,'sale100*2; payment transfers restricted200 to free200')
for r in traces['test_group3_mixed_free_restricted_and_sale_fee']:
    if r['accepted']:
        check('group3 assets '+r['event']['id'],r['state']['equity'],300,'free100 + sold100*2 =300')
for r in traces['test_repair_R1_required_split_and_dividend']:
    if r['accepted']:
        check('R1 fixed assets '+r['event']['id'],r['state']['equity'],200,'split100*2=200 shares; sell100*1, keep100*1')
r2=traces['test_repair_R2_latest_required_close_before_deposit']
check('R2 correct units',r2[-1]['state']['units'],D(1000)+D(100)/D('.3'),'saved Jan2equity300 /units1000=.3; deposit100/.3')
check('R2 correct assets',r2[-1]['state']['equity'],400,'hold100*3 + deposit100')
check('R2 correct NAV',D(r2[-1]['state']['equity'])/D(r2[-1]['state']['units']),D('.3'),'400/(1000+100/.3)=.3')
split=next(s for s in steps if s['accepted'] and s['event']['id']=='s' and s['event']['at']=='2026-01-06T08:00:00+08:00')
check('R4 pre-split',split['before']['equity'],390,'two100lots*1.9 + receivable10')
check('R4 post-split',split['after']['equity'],390,'four100shares*.95 + receivable10')
check('R4 split released',split['after']['sellable']['A'],200,'original100released*2; pending100*2 remains locked')
sale=next(r for r in traces['test_group4_split_all_lots_entitlement_preserved'] if r['accepted'] and r['event']['kind']=='sell')
check('R4 separate price input',sale['state']['equity'],810,'next-open price2: sold200*2 + held200*2 + receivable10; not split return')
refused=[s for s in steps if not s['accepted']]
assert all(s['money_state_unchanged'] and s['before']==s['after'] for s in refused)
result={'command':'python3 -B '+str(BASE/'arithmetic_checks_v2.py'),'exit_code':0,'checks':checks,
        'rejected_before_after_equal':len(refused),'independence':'direct saved receipt arithmetic; no ledger import',
        'limits':'same synthetic input assumptions; no true exchange/account qualification'}
(BASE/'independent-arithmetic-v2.json').write_text(json.dumps(result,indent=2)+'\n')
print('v2 independent arithmetic',len(checks),'rejected balances equal',len(refused),'exit0')
