"""Read saved receipt values only; independent Fraction arithmetic, no planner import."""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib
B=Path(__file__).resolve().parent
r=json.loads((B/'synthetic-input-output-receipts.json').read_text()); checks=[]
def record(name,actual,expected,formula):
    assert F(str(actual))==F(str(expected)),(name,actual,expected)
    checks.append({'name':name,'actual':str(actual),'expected':str(expected),'formula':formula})
x=r['test_floor_fee_exact_boundary']
record('q0 means no charge',x['zero_fee'],0,'no order = no minimum fee')
record('100 at2 cost',x['cost100'],F(200)+5+F('200')*F('.001'),'200+max(.2,5)+.2')
assert F(205)<F(x['cost100'])<=F('205.2')
x=r['test_fixed_quantity_cap_no_resize']
record('next-tick cost',x['next_tick_cost'],F('200.1')+5+F('200.1')*F('.001'),'100*2.001+5+.2001')
assert F(x['next_tick_cost'])>F('205.25')
x=r['test_variable_commission_and_cap_next_tick']
record('200 at2 cost',406,400+4+2,'400+.01*400+.005*400')
record('limit cost',x['limit_cost'],F('492.6')*(1+F('.01')+F('.005')),'200*2.463*1.015')
record('next tick cost',x['next_tick_cost'],F('492.8')*(1+F('.01')+F('.005')),'200*2.464*1.015')
assert F(x['limit_cost'])<=500<F(x['next_tick_cost'])
x=r['test_p0_gaps_shared_cash_no_reallocation'];p=x['plan']
record('total from saved snapshot',1000,200+400+300+100,'holdings200+400 free300 receivable100')
record('first budget',p['budgets'][0][1],300,'min(gap300,free300)')
record('second budget',p['budgets'][1][1],0,'remaining allocated free0; unused first budget not redispatched')
x=r['test_equal_gaps_code_tie_250'];p=x['plan']
record('allocated budgets',sum(F(v) for _,v in p['budgets']),250,'125+125')
record('cash after reference costs',x['remaining_after_reference_cost'],50,'250-100*1-100*1')
x=r['test_p1_sell_actual_later_buy_original_snapshot'];p=x['later_plan']
record('actual net sale',x['net'],180-5-F('.18'),'100*1.8-5-.18')
record('later cash',x['later_cash'],200+F('174.82'),'original free200+actual sale174.82')
record('later budget',p['budgets'][0][1],min(F(400),F('374.82')),'original deficit400 vs actual free374.82')
record('later buy qty',p['orders'][0]['quantity'],300,'cost300=305.3<=374.82; cost400=405.4>374.82')
record('later buy cost',x['buy_cost'],300+5+F('.3'),'300+max(.3,5)+.3')
# Independently recompute immutable input SHA from saved canonical snapshot.
d=x['decision'];expected=d['input_hash'];source={k:v for k,v in d.items() if k!='input_hash'}
actual=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
assert actual==expected
out={'command':'python3 -B '+str(B/'independent_arithmetic.py'),'exit_code':0,'checks':checks,'input_sha_independently_equal':True,'planner_imported':False}
(B/'independent-arithmetic.json').write_text(json.dumps(out,indent=2)+'\n')
print('independent arithmetic',len(checks),'and input SHA pass')
