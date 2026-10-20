import sys
sys.dont_write_bytecode = True

import unittest
from copy import deepcopy

from engine import simulate


def bar(open=1., close=None):
    close = open if close is None else close
    return dict(open=open, close=close, high=max(open, close) + .02, low=min(open, close) - .02, volume=1000)


def data():
    return {'X': {'2023-12-29': bar(), **{f'2024-01-{d:02d}': bar() for d in [1, 2, 3, 4, 5, 8, 9, 10]}}}


def candidate(cid='a', date='2024-01-01', **kw):
    kw = deepcopy(kw)
    c = dict(
        symbol='X',
        signal_date=date,
        candidate_id=cid,
        stop=kw.pop('stop', .9),
        target=kw.pop('target', 1.6),
        upper=kw.pop('upper', 1.),
        variant=kw.pop('variant', 'breakout')
    )
    c.update(kw)
    return c


def observations(prices):
    return {s: {d: dict(ema20=.5, cost20=.5, ema20_slope=.01, sma20_slope=.01, sma20=.5, sma60=.4) for d in rows} for s, rows in prices.items()}


def run(prices=None, cs=None, actions=None, config='R0', **kw):
    prices = prices or data()
    return simulate(
        prices,
        actions or [],
        [candidate()] if cs is None else cs,
        kw.pop('obs', observations(prices)),
        start='2024-01-01',
        end=kw.pop('end', '2024-01-10'),
        config_id=config,
        limits={s: 1. for s in prices},
        **kw
    )


class DiagnosticReferenceTests(unittest.TestCase):
    def test_missing_target_r0_buys_and_p0_rejects(self):
        c_missing_target = candidate('m1', target=None, signal_ref=1.2)
        p0 = run(config='P0', cs=[deepcopy(c_missing_target)])
        r0 = run(config='R0', cs=[deepcopy(c_missing_target)])
        self.assertEqual(p0['orders'][0]['reason'], 'missing_or_invalid_target')
        self.assertEqual(p0['trades'], [])
        self.assertEqual(len(r0['trades']), 1)
        self.assertTrue(r0['orders'][0]['diagnostic_reference_only'])
        self.assertTrue(r0['orders'][0]['candidate_metadata'].get('diagnostic_reference_only'))

    def test_low_rr_r1_buys_while_p5_rejects(self):
        c_low_rr = candidate('r1', signal_ref=1.0, target=1.2, stop=.9)
        p5 = run(config='P5', cs=[deepcopy(c_low_rr)], obs=observations(data()))
        r1 = run(config='R1', cs=[deepcopy(c_low_rr)], obs=observations(data()))
        self.assertEqual(p5['orders'][0]['reason'], 'signal_rr_below3')
        self.assertEqual(p5['trades'], [])
        self.assertEqual(len(r1['trades']), 1)

    def test_diagnostic_invalid_stop_or_signal_ref(self):
        bad_stop = candidate('bad-stop', stop=0.0, target=1.6, signal_ref=1.2)
        p_zero = run(config='R1', cs=[deepcopy(bad_stop)], obs=observations(data()))
        self.assertEqual(p_zero['orders'][0]['reason'], 'invalid_stop')
        self.assertEqual(p_zero['trades'], [])

        bad_stop = candidate('bad-stop-2', stop=-0.1, target=1.6, signal_ref=1.2)
        p_negative = run(config='R1', cs=[deepcopy(bad_stop)], obs=observations(data()))
        self.assertEqual(p_negative['orders'][0]['reason'], 'invalid_stop')
        self.assertEqual(p_negative['trades'], [])

        bad_signal_ref = candidate('bad-ref', stop=1.0, target=1.6, signal_ref=None)
        p_ref = run(config='R1', cs=[deepcopy(bad_signal_ref)], obs=observations(data()))
        self.assertEqual(p_ref['orders'][0]['reason'], 'nonpositive_signal_risk')
        self.assertEqual(p_ref['trades'], [])

    def test_open_gap_below_stop_still_rejects(self):
        p = data()
        p['X']['2024-01-02'] = bar(1.0)
        c = candidate('below-open', stop=1.1, target=1.8, signal_ref=1.2)
        r = run(config='R1', prices=p, cs=[deepcopy(c)], obs=observations(p))
        self.assertEqual(r['orders'][0]['reason'], 'nonpositive_open_risk')
        self.assertEqual(r['trades'], [])

    def test_signal_accepted_false_unrelated_or_none_still_rejects(self):
        c = candidate('reject-other', signal_accepted=False, signal_reject_reason='position_blocked', stop=.9, target=1.6, signal_ref=1.2)
        r_other = run(config='R1', cs=[deepcopy(c)], obs=observations(data()))
        self.assertEqual(r_other['orders'][0]['reason'], 'position_blocked')
        self.assertEqual(r_other['trades'], [])

        c = candidate('reject-none', signal_accepted=False, signal_reject_reason=None, stop=.9, target=1.6, signal_ref=1.2)
        r_none = run(config='R1', cs=[deepcopy(c)], obs=observations(data()))
        self.assertEqual(r_none['orders'][0]['reason'], 'signal_rejected')
        self.assertEqual(r_none['trades'], [])

    def test_target_and_source_preserved_with_diagnostic_metadata(self):
        c = candidate(
            'meta-1',
            signal_accepted=False,
            signal_reject_reason='target_unavailable',
            signal_ref=1.2,
            target=2.2,
            target_source='confirmed_high',
            target_source_date='2023-12-20'
        )
        r = run(config='R0', cs=[deepcopy(c)], obs=observations(data()))
        self.assertEqual(len(r['trades']), 1)
        o = r['orders'][0]
        self.assertEqual(o['reason'], 'candidate_entry')
        self.assertEqual(o['candidate_metadata']['target'], c['target'])
        self.assertEqual(o['candidate_metadata']['target_source'], c['target_source'])
        self.assertEqual(o['candidate_metadata']['target_source_date'], c['target_source_date'])
        self.assertIs(o['candidate_metadata']['signal_accepted'], False)
        self.assertEqual(o['original_candidate_id'], c['candidate_id'])
        self.assertEqual(o['original_config_id'], 'P0')
        self.assertEqual(o['candidate_metadata']['original_candidate_id'], c['candidate_id'])
        self.assertEqual(o['candidate_metadata']['original_config_id'], 'P0')
        self.assertEqual(o['candidate_metadata']['diagnostic_reference_only'], True)

    def test_next_union_quote_date_only(self):
        p = data()
        del p['X']['2024-01-02']
        r = run(config='R0', prices=p, cs=[candidate('union-date')], obs=observations(p))
        self.assertEqual(r['orders'][0]['planned_date'], '2024-01-03')
        self.assertEqual(r['trades'][0]['date'], '2024-01-03')
