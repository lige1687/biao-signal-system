"""Only three review probes and affected legitimate paths; invented accounts."""
import importlib, json, sys
from dataclasses import asdict, replace
from decimal import Decimal as D
from pathlib import Path

def run(version):
    adapter = importlib.import_module('order_ledger_adapter' + ('_v2' if version == 2 else ''))
    fixtures = importlib.import_module('adapter_fixtures' + ('_v2' if version == 2 else ''))
    f = fixtures; p = adapter.planner; results = {}
    def attempt(a, d, plan, batch, order, at):
        return adapter.attempt_open(d, plan, order, a.opening(order.symbol, at), a.ledger, batch)
    def guard(a, callback):
        state = a.ledger.snapshot()
        try:
            value = callback(); return value, None
        except ValueError as e:
            assert a.ledger.snapshot() == state
            return None, {'reason': str(e), 'ledger_apply_count': 0, 'state_unchanged': True,
                          'money': a.ledger.receipt(f.NEXT)}
    # Both price refusals followed by a newly frozen later opening.
    c = f.calendar('2.001'); c['opens'][f.OPEN]['B']['price'] = D('2.001')
    a, d, plan = f.make(c); b = a.begin(d, plan)
    rejected = [attempt(a, d, plan, b, o, f.OPEN) for o in plan.orders]
    assert all(r.status == 'refused' and r.ledger_apply_count == 0 for r in rejected)
    later = p.plan_p0(d, current_cash=plan.current_cash, action_context=plan.action_context,
                       frozen_at=f.NEXTFREEZE, opening_at=f.NEXT)
    nb, refusal = guard(a, lambda: a.begin(d, later))
    fills = [] if refusal else [attempt(a, d, later, nb, o, f.NEXT) for o in later.orders]
    assert (refusal is not None) if version == 2 else (a.ledger.snapshot()['cash'] == D('200.30'))
    results['next_open_chase'] = {'initial_refusals': list(map(asdict, rejected)), 'guard': refusal,
                                 'subsequent_attempts': list(map(asdict, fills)), 'final': a.ledger.receipt(f.NEXT)}
    # Costs mismatch refuses original orders, only decision name then changes.
    a, d, plan = f.make(); b = a.begin(d, plan)
    wrong = replace(d, costs=p.Costs(0, 0, 0, 'wrong'))
    rejected = [attempt(a, wrong, plan, b, o, f.OPEN) for o in plan.orders]
    def renamed():
        nd, snap = a.decision(name='renamed-same-decision', decision_at=f.DEC,
                             reference_known_at=f.KNOWN, references={'A': 2, 'B': 2}, costs=f.COSTS)
        np = p.plan_p0(nd, current_cash=snap, action_context=plan.action_context,
                       frozen_at=f.FREEZE, opening_at=f.OPEN)
        return nd, np, a.begin(nd, np)
    value, refusal = guard(a, renamed)
    fills = [] if refusal else [attempt(a, value[0], value[1], value[2], o, f.OPEN) for o in value[1].orders]
    assert (refusal is not None) if version == 2 else (a.ledger.snapshot()['cash'] == D('.10'))
    results['decision_rename'] = {'initial_refusals': list(map(asdict, rejected)), 'guard': refusal,
                               'subsequent_attempts': list(map(asdict, fills)), 'final': a.ledger.receipt(f.OPEN)}
    # Real ledger cash already includes released sale; misleading omission double-counts planner budget.
    c = f.calendar(sell=True); c['opens'][f.NEXT]['B']['price'] = D('1.25')
    a, d, plan = f.make(c, sell=True); b = a.begin(d, plan)
    sale = attempt(a, d, plan, b, plan.orders[0], f.OPEN); r = a.sale_result(sale)
    a.apply_calendar_event({'kind': 'advance', 'id': 'explicit-release', 'at': f.PAY, 'phase': 3})
    snap = a.cash_snapshot(at=f.PAY)
    later = p.later_buys(d, plan, r, current_cash=snap, frozen_at=f.NEXTFREEZE, opening_at=f.NEXT)
    assert snap.amount == D('374.82') and not snap.includes_sale_proceeds
    assert later.orders[0].budget == 400 and later.orders[0].cap == D('1.315')
    nb, refusal = guard(a, lambda: a.begin(d, later))
    bad = None if refusal else attempt(a, d, later, nb, later.orders[0], f.NEXT)
    if version == 2: assert refusal is not None
    else: assert bad.status == 'refused' and bad.ledger_apply_count == 1 and bad.ledger_state_unchanged
    results['cash_proceeds_omission'] = {'sale': asdict(sale), 'release': a.calendar_events,
                                       'cash': asdict(snap), 'plan': asdict(later), 'guard': refusal,
                                       'attempt': asdict(bad) if bad else None, 'final': a.ledger.receipt(f.NEXT)}
    if version == 2:
        # A renamed decision created before binding also cannot bypass first begin.
        a, d, plan = f.make()
        nd, ns = a.decision(name='precreated-alternate-name', decision_at=f.DEC,
                           reference_known_at=f.KNOWN, references={'A': 2, 'B': 2}, costs=f.COSTS)
        np = p.plan_p0(nd, current_cash=ns, action_context=plan.action_context,
                      frozen_at=f.FREEZE, opening_at=f.OPEN)
        b = a.begin(d, plan)
        wrong = replace(d, costs=p.Costs(0, 0, 0, 'wrong'))
        rejected = [attempt(a, wrong, plan, b, o, f.OPEN) for o in plan.orders]
        _, refusal = guard(a, lambda: a.begin(nd, np))
        assert refusal is not None
        results['precreated_name_cannot_reset'] = {'guard': refusal, 'attempts': list(map(asdict, rejected))}
        # Receipt issuance is bound to this account and explicit release clock.
        a, d, plan = f.make(sell=True); b = a.begin(d, plan)
        sale = attempt(a, d, plan, b, plan.orders[0], f.OPEN); r = a.sale_result(sale)
        failures = []
        for clock, rid in ((f.OPEN, r.receipt_id), (f.OPEN, 'foreign-sale-id')):
            _, refusal = guard(a, lambda: a.cash_snapshot(at=clock, includes_sale_receipt=rid))
            assert refusal is not None; failures.append(refusal)
        a.apply_calendar_event({'kind': 'advance', 'id': 'bound-release', 'at': f.PAY, 'phase': 3})
        _, refusal = guard(a, lambda: a.cash_snapshot(at=f.PAY, includes_sale_receipt='foreign-sale-id'))
        assert refusal is not None; failures.append(refusal)
        results['unreleased_foreign_funding'] = {'refusals': failures, 'sale': asdict(sale), 'release': a.calendar_events}
        # Both orders retain original budget and successful replay is ignored.
        a, d, plan = f.make(); b = a.begin(d, plan)
        rs = [attempt(a, d, plan, b, o, f.OPEN) for o in plan.orders]
        replay = attempt(a, d, plan, b, plan.orders[0], f.OPEN)
        assert all(x.status == 'filled' for x in rs) and a.ledger.snapshot()['cash'] == D('.10')
        assert replay.status == 'replay_ignored' and replay.ledger_apply_count == 0
        results['legal_two_buys_replay'] = {'attempts': list(map(asdict, rs)), 'replay': asdict(replay)}
        a, d, plan = f.make(f.calendar('2.001')); b = a.begin(d, plan)
        rs = [attempt(a, d, plan, b, o, f.OPEN) for o in plan.orders]
        replay = attempt(a, d, plan, b, plan.orders[0], f.OPEN)
        assert [x.status for x in rs] == ['refused', 'filled'] and a.ledger.snapshot()['cash'] == D('205.30')
        assert replay.ledger_apply_count == 0 and replay.status == 'replay_ignored'
        results['legal_second_after_refusal'] = {'attempts': list(map(asdict, rs)), 'replay': asdict(replay)}
        a, d, plan = f.make(sell=True); b = a.begin(d, plan)
        sale = attempt(a, d, plan, b, plan.orders[0], f.OPEN); r = a.sale_result(sale)
        a.apply_calendar_event({'kind': 'advance', 'id': 'legal-release', 'at': f.PAY, 'phase': 3})
        snap = a.cash_snapshot(at=f.PAY, includes_sale_receipt=r.receipt_id)
        later = p.later_buys(d, plan, r, current_cash=snap, frozen_at=f.NEXTFREEZE, opening_at=f.NEXT)
        b = a.begin(d, later); buy = attempt(a, d, later, b, later.orders[0], f.NEXT)
        assert buy.status == 'filled' and a.ledger.snapshot()['cash'] == D('69.52')
        assert a.ledger.snapshot()['fees'] == D('10.48')
        results['legal_sale_release_buy'] = {'sale': asdict(sale), 'release': a.calendar_events,
                                           'snapshot': asdict(snap), 'plan': asdict(later), 'buy': asdict(buy)}
    return results

if __name__ == '__main__':
    version = int(sys.argv[1]); results = run(version)
    path = Path(__file__).parent / ('review-reproductions-v1.json' if version == 1 else 'targeted-results-v2.json')
    import shutil
    free = shutil.disk_usage(path.parent).free
    data = json.dumps({'version': version, 'free_before_write': free, 'checks': results}, indent=2, default=str) + '\n'
    if free < len(data.encode()) + 1048576: raise OSError('insufficient measured capacity')
    path.write_text(data); assert path.read_text() == data
    print(json.dumps({'version': version, 'checks': len(results), 'path': str(path), 'bytes': len(data.encode())}))
