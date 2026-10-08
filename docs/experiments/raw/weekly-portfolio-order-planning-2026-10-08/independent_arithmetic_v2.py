"""Saved receipt arithmetic and plan identity recomputation. No planner import."""
from pathlib import Path
from fractions import Fraction as F
import hashlib, json, shutil

B = Path(__file__).resolve().parent
r = json.loads((B / 'synthetic-receipts-v2.json').read_text())
checks = []

def eq(name, actual, expected, reason):
    assert F(str(actual)) == F(str(expected)), (name, actual, expected)
    checks.append({'name': name, 'actual': str(actual), 'expected': str(expected), 'formula': reason})

def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def check_plan(p):
    content = {'decision_hash': p['decision_hash'], 'cash': p['current_cash'],
               'actions': p['action_context'], 'funding_receipt': p['funding_receipt'],
               'frozen_at': p['frozen_at'], 'opening_at': p['opening_at'],
               'complete_plan': {'status': p['status'], 'reason': p['reason'],
                                 'ordering': p['ordering'], 'budgets': p['budgets'],
                                 'unallocated': p['unallocated'],
                                 'orders': [{k: v for k, v in o.items()
                                             if k not in ('order_id', 'decision_hash', 'plan_hash')}
                                            for o in p['orders']]}}
    assert digest(content) == p['plan_hash']
    for i, o in enumerate(p['orders']):
        assert o['plan_hash'] == p['plan_hash']
        assert o['order_id'] == digest((p['plan_hash'], i, o['symbol'], o['side']))

x = r['test_current_cash_outflow_not_old_free']; p = x['plan']
eq('cash after unrelated outflow', p['orders'][0]['budget'], '174.82', 'actual current cash; old free200 is not added')
eq('affordable whole lot', p['orders'][0]['quantity'], 100, '100 cost105.1 <=174.82; 200 cost205.2 >174.82')
eq('actual100cost', 105.1, F(100)+5+F('.1'), '100+5+.1')
x = r['test_cash_excluding_proceeds_add_once_and_included_never_twice']
eq('excluding snapshot adds exactly once', x['excluding']['orders'][0]['budget'], '174.82', 'current excluding cash0 +180-5-.18')
eq('included snapshot unchanged', x['included']['orders'][0]['budget'], '174.82', 'current included cash174.82; no additional sale')
eq('legal original available path', x['original_legal_path']['orders'][0]['budget'], '374.82', 'current excluding cash200 + net174.82')
x = r['test_plan_identity_binds_cash_receipt_and_contents']; high = x['high']; low = x['low']
eq('high original reference quantity', high['orders'][0]['quantity'], 300, 'reference1 cost305.3 <=374.82')
eq('low current available', low['orders'][0]['budget'], '244.95', 'current excluding200 +100*.5-5-.05')
eq('low quantity', low['orders'][0]['quantity'], 200, 'reference1 cost205.2 <=244.95; 300 cost305.3 >244.95')
assert high['decision_hash'] == low['decision_hash']
assert high['plan_hash'] != low['plan_hash'] and high['orders'][0]['order_id'] != low['orders'][0]['order_id']
# Independent cap arithmetic at each permitted tick and its next tick.
for p in (high, low):
    o = p['orders'][0]; q = F(o['quantity']); cap = F(o['cap']); budget = F(o['budget'])
    for price, fits in ((cap, True), (cap+F('.001'), False)):
        n = q*price; amount = n+max(n*F('.001'), F(5))+n*F('.001')
        assert (amount <= budget) == fits
        checks.append({'name': 'cap fits' if fits else 'next tick exceeds', 'cost': str(amount),
                       'budget': str(budget), 'fits': fits})
plans = []
for test in r.values():
    for value in test.values():
        if isinstance(value, dict) and 'plan_hash' in value:
            check_plan(value); plans.append(value)
x = r['test_known_action_inherited_cannot_be_omitted']
assert x['initial']['action_context'] == x['later']['action_context']
assert x['later']['status'] == 'unsupported' and not x['later']['orders']
output = {'command': 'python3 -B ' + str(B / 'independent_arithmetic_v2.py'), 'exit_code': 0,
          'amount_checks': checks, 'complete_plan_hashes_recomputed': len(plans),
          'order_ids_recomputed': sum(len(p['orders']) for p in plans),
          'inherited_action_context_equal': True, 'planner_imported': False}
data = json.dumps(output, indent=2) + '\n'
assert shutil.disk_usage(B).free > len(data.encode()) + 1000000
p = B / 'independent-arithmetic-v2.json'
p.write_text(data); assert p.read_text() == data
print('amount checks', len(checks), 'plan hashes', len(plans), 'all pass')
