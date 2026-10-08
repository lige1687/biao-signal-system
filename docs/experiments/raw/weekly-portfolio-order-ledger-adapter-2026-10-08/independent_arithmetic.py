"""Independently recompute saved synthetic amounts. No planner or ledger imports."""
from pathlib import Path
from fractions import Fraction as F
import json, shutil

B = Path(__file__).resolve().parent
r = json.loads((B / 'attempt-and-calendar-receipts-04.json').read_text())
checks = []

def eq(name, actual, expected, formula):
    assert F(str(actual)) == F(str(expected)), (name, actual, expected)
    checks.append({'name': name, 'actual': str(actual), 'expected': str(expected), 'formula': formula})

def money(a, stage): return json.loads(a[stage + '_json'])

two = r['test_two_valid_buys_exact_fees']['attempts']
eq('buy1 cost', F(money(two[0], 'before')['free_cash'])-F(money(two[0], 'after')['free_cash']),
   F('205.20'), '100*2 +max(.2,5)+.2=205.2')
eq('two buys final cash', money(two[-1], 'after')['free_cash'], F('410.50')-2*F('205.20'), '410.5-205.2-205.2=.1')
eq('two buys fees once', money(two[-1], 'after')['fees'], F(2)*(5+F('.2')), '2*(commission5+slippage.2)=10.4')
eq('two buys assets', money(two[-1], 'after')['equity'], F('410.50')-F('10.4'), 'initial410.5 minus totalfees10.4; 200 shares*2 +cash.1')
eq('two buys A total', money(two[-1], 'after')['shares']['A'], 100, 'one100 purchase')
eq('two buys A sellable', money(two[-1], 'after')['sellable']['A'], 0, 'Jan8 release not yet reached')
cap = r['test_first_over_cap_second_budget_unchanged']['attempts']
eq('over cap cash unchanged', money(cap[0], 'after')['free_cash'], '410.50', 'no first order fee or principal charged')
eq('second budget stays fixed', r['test_first_over_cap_second_budget_unchanged']['plan']['orders'][1]['budget'], '205.25', 'original second budget not enlarged after first rejection')
eq('one valid second final cash', money(cap[-1], 'after')['free_cash'], F('410.5')-F('205.2'), '410.5-205.2=205.3')
seq = r['test_sell_then_explicit_release_then_later_buy']
sale, buy = seq['sale'], seq['buy']
eq('sale cash remains original', money(sale, 'after')['free_cash'], 200, 'net sell proceeds initially restricted')
eq('sale restricted net', money(sale, 'after')['restricted_cash'], 180-5-F('.18'), '100*1.8 -commission5 -.18 slippage=174.82')
eq('sale fee', money(sale, 'after')['fees'], 5+F('.18'), '5.18 charged once')
eq('release cash', seq['current_cash']['amount'], 200+F('174.82'), 'explicit release turns restricted into currentfree374.82')
eq('release equity unchanged', seq['release'][0]['money']['equity'], money(sale, 'after')['equity'], 'same asset switches from restricted to free')
eq('later buy cost', F(money(buy, 'before')['free_cash'])-F(money(buy, 'after')['free_cash']),
   300+5+F('.3'), '300*1+commission5+.3=305.3')
eq('later final cash', money(buy, 'after')['free_cash'], F('374.82')-F('305.3'), '69.52')
eq('sell+buy fees', money(buy, 'after')['fees'], F('5.18')+F('5.30'), '10.48; no duplicate slippage')
eq('later final B', money(buy, 'after')['shares']['B'], 400, 'old100+new300')
eq('later B sellable', money(buy, 'after')['sellable']['B'], 100, 'new300 remain locked until explicitJan8')
eq('final marked assets', money(buy, 'after')['equity'], F(1000)-70-F('10.48'),
   'initial1000; A350 reprices2->1.8 loss70; totalfees10.48; assets919.52')

attempts = []
def walk(v):
    if isinstance(v, dict):
        if 'before_json' in v and 'after_json' in v:
            attempts.append(v)
        else:
            for x in v.values(): walk(x)
    elif isinstance(v, list):
        for x in v: walk(x)
walk(r)
refusals = [a for a in attempts if a['status'] in ('refused', 'replay_ignored')]
assert all(a['ledger_state_unchanged'] and money(a, 'before') == money(a, 'after') for a in refusals)
assert all(a['ledger_apply_count'] <= 1 for a in attempts)
output = {'command': 'python3 -B ' + str(B / 'independent_arithmetic.py'), 'exit_code': 0,
          'checks': checks, 'attempts': len(attempts), 'refusal_or_replay_unchanged': len(refusals),
          'filled': sum(a['status'] == 'filled' for a in attempts),
          'ledger_apply_calls': sum(a['ledger_apply_count'] for a in attempts),
          'planner_or_ledger_imported': False}
data = json.dumps(output, indent=2)+'\n'
assert shutil.disk_usage(B).free > len(data.encode())+1000000
p = B / 'independent-arithmetic.json'; p.write_text(data); assert p.read_text() == data
print('independent checks', len(checks), 'attempts', len(attempts), 'all pass')
