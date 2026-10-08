"""Retrospective liquidity requirement for fixed saved fills, not a strategy rerun."""
import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
D = Decimal
TOL = D('0.000001')
SOURCE = ROOT / 'docs/experiments/raw/factor-module-a-continuation-2026-09-27'


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    qualification_path = ROOT / 'docs/experiments/raw/remaining-four-increments-2026-10-07/capital/source-qualification.json'
    qualification = json.loads(qualification_path.read_text())
    checks = [{'path': p, 'expected': rec['sha256'], 'actual': sha(ROOT / p)} for p, rec in qualification['files'].items()]
    dump('input-checks.json', checks)
    assert all(x['actual'] == x['expected'] for x in checks), 'frozen source changed; stop before statistics'
    accounts = [a for a in json.loads((SOURCE / 'accounts.json').read_text()) if a['fee_scenario_id'] == 'base' and a['policy_id'] in ('A_ALL', 'A_SMA')]
    assert len(accounts) == 12
    for a in accounts:
        for path in (SOURCE / a['daily_path'], SOURCE / a['ledger_path']):
            assert str(path.relative_to(ROOT)) in qualification['files']
    dump('frozen-analysis.json', {
        'question': 'Exact saved quantities and fees; retrospective minimum cash with all sales before purchases or all purchases before sales within each day. Payments only at day end.',
        'baseline': '6 independent accounts with 100000 CNY each, separately for A_ALL and A_SMA.',
        'formula': 'C_min=max(0,-min(cumulative cash flow across all execution/payment prefixes)); round upward to cents.',
        'forbidden_claims': ['prospective capital recommendation', 'same strategy under smaller initial cash', 'observed broker settlement order', 'return or drawdown improvement'],
        'qualification_sha256': sha(qualification_path),
        'run_sha256': sha(Path(__file__)),
        'binding_count': len(checks),
    })
    summaries = {}
    paths = []
    conflicts = []
    validation = {'input_hashes': len(checks), 'account_daily_cash_rows': 0, 'aggregate_daily_cash_rows': 0, 'bound_feasibility_proofs': 0}
    for policy in ('A_ALL', 'A_SMA'):
        selected = [a for a in accounts if a['policy_id'] == policy]
        assert len(selected) == 6 and len({a['symbol'] for a in selected}) == 6
        daily = {}
        events = defaultdict(lambda: {'buys': [], 'sells': [], 'payments': []})
        dates = None
        for a in selected:
            assert a['status'] == 'completed' and D(a['initial_cash_cny']) == D(100000)
            rows = list(csv.DictReader((SOURCE / a['daily_path']).open()))
            days = [r['date'] for r in rows]
            assert days == sorted(set(days)) and (dates is None or days == dates)
            dates = days
            daily[a['symbol']] = {r['date']: D(r['cash']) for r in rows}
            ledger = json.loads((SOURCE / a['ledger_path']).read_text())
            changes = defaultdict(lambda: D(0))
            for fill in ledger['fills']:
                day = fill['date']
                assert day in daily[a['symbol']] and fill['decision_at'] < day
                delta, price, fee = (D(fill[k]) for k in ('units_delta', 'price', 'fee'))
                assert delta != 0 and price > 0 and fee == abs(delta * price) * D('0.001')
                cashflow = -delta * price - fee
                kind = 'buys' if delta > 0 else 'sells'
                assert (cashflow < 0) == (kind == 'buys')
                events[day][kind].append({'symbol': a['symbol'], 'cashflow': cashflow, 'units_delta': delta, 'price': price, 'fee': fee})
                changes[day] += cashflow
            for action in ledger['action_ledger']:
                assert action['type'] in ('record_right', 'ex_receivable', 'split_day_end', 'payment_day_end')
                if action['type'] == 'payment_day_end':
                    amount = D(action['amount'])
                    assert amount >= 0 and action['date'] in daily[a['symbol']]
                    events[action['date']]['payments'].append({'symbol': a['symbol'], 'cashflow': amount})
                    changes[action['date']] += amount
            running = D(100000)
            for day in dates:
                running += changes[day]
                assert abs(running - daily[a['symbol']][day]) <= TOL, (policy, a['symbol'], day, 'cash identity')
                validation['account_daily_cash_rows'] += 1
        baseline = D(600000)
        eod_flows = [sum((daily[a['symbol']][day] for a in selected), D(0)) - baseline for day in dates]
        min_eod = min([D(0)] + eod_flows)
        policy_result = {'symbols': [a['symbol'] for a in selected], 'days': len(dates), 'start': dates[0], 'end': dates[-1], 'original_initial_cash': baseline,
                         'daily_close_only_requirement': -min_eod, 'end_cash_change': eod_flows[-1], 'orders_fixed': True, 'scenarios': {}}
        for scenario, sequence in [('sell_first', ('sells', 'buys', 'payments')), ('buy_first', ('buys', 'sells', 'payments'))]:
            cumulative = D(0)
            prefixes = [(None, 'initial', cumulative)]
            for n, day in enumerate(dates):
                before = cumulative
                amounts = {k: sum((v['cashflow'] for v in events[day][k]), D(0)) for k in sequence}
                stages = {}
                for kind in sequence:
                    # Within a stage every movement has the same sign; its endpoint
                    # and the previous endpoint include the worst cash balance.
                    cumulative += amounts[kind]
                    prefixes.append((day, kind, cumulative))
                    stages[kind] = cumulative
                assert abs(cumulative - eod_flows[n]) <= TOL
                validation['aggregate_daily_cash_rows'] += 1
                if any(events[day][k] for k in sequence):
                    paths.append({'policy': policy, 'scenario': scenario, 'date': day, 'before': before, **amounts, 'after_buys': stages['buys'], 'after_sells': stages['sells'], 'end': cumulative})
                if scenario == 'sell_first' and events[day]['buys'] and events[day]['sells']:
                    conflicts.append({'policy': policy, 'date': day, **events[day], 'before': before, 'sell_first_trough': min(before, before + amounts['sells'] + amounts['buys']), 'buy_first_trough': before + amounts['buys']})
            trough = min(v for _, _, v in prefixes)
            exact = max(D(0), -trough)
            rounded = exact.quantize(D('0.01'), rounding=ROUND_CEILING)
            assert all(v + rounded >= 0 for _, _, v in prefixes)
            assert rounded == 0 or any(v + rounded - D('0.01') < 0 for _, _, v in prefixes)
            validation['bound_feasibility_proofs'] += 1
            policy_result['scenarios'][scenario] = {'minimum_initial_cash_exact': exact, 'minimum_initial_cash_cents': rounded,
                'binding_dates_and_stages': [(day, stage) for day, stage, v in prefixes if v == trough],
                'cash_balance_min_at_600k': baseline + trough, 'difference_from_600k': baseline - rounded,
                'cashflow_events': sum(len(events[day][k]) for day in dates for k in sequence)}
        assert policy_result['scenarios']['sell_first']['minimum_initial_cash_exact'] <= policy_result['scenarios']['buy_first']['minimum_initial_cash_exact'] <= baseline
        summaries[policy] = policy_result
    dump('cashflow-paths.json', paths)
    dump('same-day-conflicts.json', conflicts)
    dump('result.json', {'status': 'completed_conditional_fixed_execution_funding_only', 'policies': summaries, 'validation': validation,
                         'cash_interest_or_external_flows': 'No additional cash movements needed to reconcile all saved daily cash rows.',
                         'limits': ['Historical hindsight funding need, not a tradable initial-budget selector.', 'Fixed quantities originated in separate 100000 accounts; changing capital and recalculating quantity is a different unrun study.', 'No broker timing, execution liquidity or sell-proceeds availability is certified.', 'Short actual trade history and source quality inherited; no new forecast/factor validity.']})
    dump('manifest.json', {'inputs': checks, 'artifacts': {p.name: sha(p) for p in HERE.iterdir() if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({'policies': summaries, 'validation': validation}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
