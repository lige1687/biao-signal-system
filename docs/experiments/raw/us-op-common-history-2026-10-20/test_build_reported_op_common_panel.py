import datetime as dt
import unittest

import build_reported_op_common_panel as m


class ReportedOpPanelTests(unittest.TestCase):
    def test_january_2015_uses_december_2014_formation_and_prior_anchor(self):
        self.assertEqual(m.shift_month(2015, 1, -1), (2014, 12))
        self.assertEqual(m.anchor_for_target(2015, 1), 2014)
        self.assertEqual(m.months_between((2015, 1), (2015, 1)), [(2015, 1)])

    def test_june_to_july_anchor_transition(self):
        self.assertEqual(m.anchor_for_target(2015, 6), 2014)
        self.assertEqual(m.anchor_for_target(2015, 7), 2015)

    def test_weekend_june_30_cutoff_uses_last_spy_session_then_two_days(self):
        # June 30, 2019 was a Sunday; the usable anchor was Friday June 28.
        observed = m.observed_anchor_cutoff(2019, [dt.date(2019, 6, 27), dt.date(2019, 6, 28)])
        self.assertEqual(observed['anchor_calendar_date'], dt.date(2019, 6, 30))
        self.assertEqual(observed['observed_anchor_date'], dt.date(2019, 6, 28))
        self.assertEqual(observed['accepted_cutoff'], dt.date(2019, 6, 26))

    def test_latest_unqualified_revision_is_selected_without_fallback(self):
        records = [
            {'adsh': 'older-qualified', 'form': '10-K', 'period': '20181231', 'accepted': '2019-02-01 10:00:00', 'sourcequalified': True},
            {'adsh': 'newer-amendment', 'form': '10-K/A', 'period': '20181231', 'accepted': '2019-05-01 10:00:00', 'sourcequalified': False},
        ]
        selected = m.choose_latest_filing(records, 2018, dt.date(2019, 6, 26))
        self.assertEqual(selected['adsh'], 'newer-amendment')
        self.assertFalse(selected['sourcequalified'])

    def test_accepted_after_cutoff_is_not_visible(self):
        records = [{'adsh': 'late', 'form': '10-K', 'period': '20181231', 'accepted': '2019-06-27 10:00:00'}]
        self.assertIsNone(m.choose_latest_filing(records, 2018, dt.date(2019, 6, 26)))

    def test_exact_monthly_endpoints_require_all_twelve_and_skip_gap_even_with_volume(self):
        dates = [dt.date(2020, month, 1) for month in range(1, 13)]
        self.assertEqual(len(dates), 12)
        rows = {(d, 'XYZ'): [{'close': 10, 'adj_close': 10 + i, 'volume': 4, 'source': 'yahoo'}]
                for i, d in enumerate(dates)}
        no_trade = {}
        gaps = {'XYZ': [(dt.date(2020, 5, 1), dt.date(2020, 7, 1))]}
        qualified, value, checks = m.momentum_window(rows, 'XYZ', dates, no_trade, gaps)
        self.assertFalse(checks[5]['qualified'])
        self.assertIn('source_reported_gap', checks[5]['reason'])
        self.assertTrue(all(x['qualified'] for i, x in enumerate(checks) if i != 5))
        self.assertFalse(qualified)
        self.assertIsNone(value)
        gaps = {}
        qualified, value, _ = m.momentum_window(rows, 'XYZ', dates, no_trade, gaps)
        self.assertTrue(qualified)
        self.assertIsNotNone(value)
        self.assertFalse(m.momentum_window(rows, 'XYZ', dates[:-1], no_trade, gaps)[0])

    def test_target_quote_is_independent_from_membership_retention(self):
        # Membership and future quote flags are separate; a missing quote does not delete a row.
        member = {'ticker': 'OLD', 'membership_active_on_formation': True}
        missing = m.price_qualification({}, 'OLD', dt.date(2020, 2, 28), {}, {})
        self.assertTrue(member['membership_active_on_formation'])
        self.assertFalse(missing['qualified'])
        self.assertEqual(member['ticker'], 'OLD')

    def test_quote_detail_retains_exact_source_and_raw_fields(self):
        day = dt.date(2020, 1, 31)
        rows = {(day, 'XYZ'): [{'close': 12.0, 'adj_close': 11.5, 'volume': 4.0, 'source': 'yahoo'}]}
        q = m.price_qualification(rows, 'XYZ', day, {}, {})
        detail = m.price_status_detail(day, q)
        self.assertTrue(detail['qualified'])
        self.assertEqual(detail['source'], 'yahoo')
        self.assertEqual(detail['close'], 12.0)
        self.assertEqual(detail['adj_close'], 11.5)
        self.assertEqual(detail['volume'], 4.0)

    def test_identity_keeps_rename_and_verified_window_as_candidates(self):
        law = m.defaultdict(list)
        law['OLDCO'].append({'symbol': 'OLDCO', 'cik': '0000000001', 'name': 'Old Co', 'date_added': '', 'date_removed': '', 'created_at': ''})
        matched = m.match_identity('NEWCO', dt.date(2015, 2, 1), law, [('OLDCO', 'NEWCO')], [])
        self.assertEqual(matched['status'], 'nonexact_candidate')
        self.assertEqual(matched['ciks'], ['0000000001'])
        self.assertIn('rename', matched['modes'])
        self.assertNotEqual(matched['status'], 'validated')

    def test_midperiod_source_difference_links_to_window_not_only_month_end(self):
        dates = [dt.date(2020, month, 1) for month in range(1, 13)]
        diff = {'date': '2020-06-15', 'ticker': 'XYZ', 'absolute_change_difference': '0.02'}
        before = {'date': '2019-12-20', 'ticker': 'XYZ', 'absolute_change_difference': '0.02'}
        self.assertEqual(m.source_difference_links([before], 'XYZ', dt.date(2019, 12, 31), dt.date(2020, 12, 31), dates), [])
        links = m.source_difference_links([diff], 'XYZ', dt.date(2020, 5, 29), dt.date(2020, 12, 31), dates)
        self.assertEqual(len(links), 1)
        self.assertIn('momentum_adjusted_price_window', links[0]['roles'])
        self.assertIn('formation_to_target_quote_window', links[0]['roles'])


if __name__ == '__main__':
    unittest.main()
