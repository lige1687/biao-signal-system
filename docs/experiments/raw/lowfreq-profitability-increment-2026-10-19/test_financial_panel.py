"""Synthetic, offline tests of time and source boundary rules."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('financial_panel', Path(__file__).with_name('build_financial_panel.py'))
panel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(panel)


def annual(code='sh.600000', aid='1', year=2017, pub='2018-03-01',
           assets='100', revenue='60', cost='30', cfo='20', category='annual'):
    amounts = {'assets': assets, 'revenue': revenue, 'cost': cost, 'cfo': cfo}
    fields = {name: {'status': 'qualified' if value is not None else 'unknown',
                     'value_yuan': value} for name, value in amounts.items()}
    return {'code': code, 'id': aid, 'year': year, 'title': f'{year}年年度报告',
            'publication_date': pub, 'categories': {category}, 'pdf': {'sha256': 'a'*64},
            'prepared': {'header_evidence': {'document_form': 'suspected_full_text',
                                             'identity_status': 'match'},
                         'financial_parser_result': {'report_year': year, 'publication_date': pub,
                                                     'fields': fields}}}


def notice(code='sh.600000', aid='n', pub='2019-04-01', title='财务更正公告'):
    return {'code': code, 'id': aid, 'year': None, 'title': title,
            'publication_date': pub, 'categories': {'correction'}, 'pdf': {'sha256': 'b'*64},
            'prepared': {'header_evidence': {'document_form': 'notice', 'identity_status': 'match'}},
            'prepared_binding': {'notice_text': {'path': '/synthetic', 'sha256': 'c'*64}}}


def index(*records):
    return {(r['code'], r['id']): r for r in records}


class FinancialPanelTests(unittest.TestCase):
    def test_v2_recovers_measurement_without_clearing_unread_event(self):
        current = annual(year=2019, pub='2020-03-01')
        event = {'record': notice(pub='2018-04-01'), 'review': None}
        result = panel.select_feature(index(current), {current['code']: [event]},
                                      current['code'], '2020-04-01', 'gp',
                                      allow_measurement_recovery=True)
        self.assertEqual(result['status'], 'qualified')
        recovery = result['recovery_evidence'][0]
        self.assertEqual(recovery['reason'], 'measurement_recovered_with_unreviewed_prior_notice')
        self.assertEqual(recovery['notice_review_status'], 'unreviewed')
        self.assertEqual(recovery['continuing_scope'], 'unknown')
        self.assertIsNone(event['review'])
        self.assertFalse(recovery['financial_authenticity_certified'])

    def test_v2_date_boundary_and_past_month_remain_unknown(self):
        current = annual(aid='2', year=2019, pub='2020-03-01')
        for event_date in ('2019-12-31', '2020-01-02'):
            event = {'record': notice(pub=event_date), 'review': None}
            result = panel.select_feature(index(current), {current['code']: [event]},
                                          current['code'], '2020-04-01', 'gp',
                                          allow_measurement_recovery=True)
            self.assertEqual(result['reason'], 'applicable_notice_unresolved')
        old = annual(year=2018, pub='2019-03-01')
        event = {'record': notice(pub='2019-04-01'), 'review': None}
        result = panel.select_feature(index(old, current), {old['code']: [event]},
                                      old['code'], '2019-05-01', 'gp', allow_measurement_recovery=True)
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')

    def test_v2_never_overrides_known_current_conflict_or_failed_latest(self):
        current = annual(year=2019, pub='2020-03-01')
        event = {'record': notice(pub='2018-04-01'), 'review': {
            'disposition': 'financial_correction', 'affected_years': [2019],
            'affected_fields': ['assets'], 'continuing_scope': 'cleared'}}
        result = panel.select_feature(index(current), {current['code']: [event]},
                                      current['code'], '2020-04-01', 'gp', allow_measurement_recovery=True)
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')
        event['review'] = None
        newer = annual(aid='2', year=2019, pub='2020-03-15')
        newer['prepared'] = None
        result = panel.select_feature(index(current, newer), {current['code']: [event]},
                                      current['code'], '2020-04-01', 'gp', allow_measurement_recovery=True)
        self.assertEqual(result['reason'], 'latest_full_annual_field_or_identity_unknown')
        event['ambiguous_annual'] = True
        result = panel.select_feature(index(current), {current['code']: [event]},
                                      current['code'], '2020-04-01', 'gp', allow_measurement_recovery=True)
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')

    def test_missing_source_publication_date_never_silently_disappears(self):
        old = annual()
        newer = annual(aid='2', year=2018, pub=None)
        result = panel.select_feature(index(old, newer), {}, old['code'], '2019-04-01', 'gp')
        self.assertEqual(result['reason'], 'source_publication_date_unknown')
        event = {'record': notice(pub=None), 'review': None}
        result = panel.select_feature(index(old), {old['code']: [event]},
                                      old['code'], '2018-04-01', 'gp')
        self.assertEqual(result['reason'], 'source_publication_date_unknown')

    def test_new_annual_failed_cannot_fall_back(self):
        old = annual()
        newer = annual(aid='2', year=2018, pub='2019-03-01')
        newer['prepared'] = None
        result = panel.select_feature(index(old, newer), {}, old['code'], '2019-04-01', 'gp')
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['report_year'], 2018)
        self.assertEqual(result['announcement_ids'], ['2'])

    def test_correction_cannot_change_past_or_unrelated_newer_year(self):
        old = annual()
        newer = annual(aid='2', year=2018, pub='2019-03-01')
        item = {'record': notice(), 'review': {'disposition': 'financial_correction',
                'affected_years': [2017], 'affected_fields': ['assets'],
                'continuing_scope': 'cleared'}}
        prior = panel.select_feature(index(old), {old['code']: [item]}, old['code'], '2018-04-01', 'gp')
        self.assertEqual(prior['status'], 'qualified')
        current = panel.select_feature(index(old, newer), {old['code']: [item]}, old['code'], '2019-05-01', 'gp')
        self.assertEqual(current['status'], 'qualified')
        self.assertEqual(current['report_year'], 2018)

    def test_same_day_cash_conflict_leaves_gp(self):
        first = annual()
        second = annual(aid='2', cfo='21')
        gp = panel.select_feature(index(first, second), {}, first['code'], '2018-04-01', 'gp')
        cash = panel.select_feature(index(first, second), {}, first['code'], '2018-04-01', 'cfo')
        self.assertEqual(gp['status'], 'qualified')
        self.assertEqual(gp['announcement_ids'], ['1', '2'])
        self.assertEqual(cash['reason'], 'same_day_dependent_amount_conflict')

    def test_ratio_equal_but_amount_conflict_unknown(self):
        first = annual()
        second = annual(aid='2', assets='200', revenue='120', cost='60', cfo='40')
        self.assertEqual(panel.select_feature(index(first, second), {}, first['code'],
                                              '2018-04-01', 'gp')['reason'],
                         'same_day_dependent_amount_conflict')

    def test_unread_notice_does_not_auto_recover_next_period(self):
        old = annual()
        newer = annual(aid='2', year=2019, pub='2020-03-01')
        event = {'record': notice(pub='2018-04-01'), 'review': None}
        result = panel.select_feature(index(old, newer), {old['code']: [event]},
                                      old['code'], '2020-04-01', 'gp')
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')

    def test_unknown_continuing_scope_blocks_new_year(self):
        newer = annual(aid='2', year=2019, pub='2020-03-01')
        event = {'record': notice(pub='2018-04-01'),
                 'review': {'disposition': 'financial_correction',
                            'affected_years': [2017], 'affected_fields': ['assets'],
                            'continuing_scope': 'unknown'}}
        result = panel.select_feature(index(newer), {newer['code']: [event]},
                                      newer['code'], '2020-04-01', 'gp')
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')

    def test_scoped_new_period_recovery_retains_evidence(self):
        newer = annual(aid='2', year=2019, pub='2020-03-01')
        event = {'record': notice(pub='2018-04-01'),
                 'review': {'disposition': 'financial_correction',
                            'affected_years': None, 'affected_fields': ['assets'],
                            'continuing_scope': 'cleared'}}
        result = panel.select_feature(index(newer), {newer['code']: [event]},
                                      newer['code'], '2020-04-01', 'gp')
        self.assertEqual(result['status'], 'qualified')
        self.assertEqual(result['recovery_evidence'][0]['announcement_id'], 'n')

    def test_cleared_continuation_does_not_clear_affected_year(self):
        current = annual()
        event = {'record': notice(pub='2018-03-10'),
                 'review': {'disposition': 'financial_correction',
                            'affected_years': [2017], 'affected_fields': ['assets'],
                            'continuing_scope': 'cleared'}}
        result = panel.select_feature(index(current), {current['code']: [event]},
                                      current['code'], '2018-04-01', 'gp')
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')

    def test_extends_never_recovers_new_year_by_annual_alone(self):
        newer = annual(aid='2', year=2019, pub='2020-03-01')
        event = {'record': notice(pub='2018-04-01'),
                 'review': {'disposition': 'financial_correction',
                            'affected_years': [2017], 'affected_fields': ['assets'],
                            'continuing_scope': 'extends'}}
        result = panel.select_feature(index(newer), {newer['code']: [event]},
                                      newer['code'], '2020-04-01', 'gp')
        self.assertEqual(result['reason'], 'applicable_notice_unresolved')

    def test_incomplete_catalog_blocks_even_prepared_document(self):
        current = annual()
        coverage = {current['code']: {'annual': 'complete', 'correction': 'pending'}}
        result = panel.select_feature(index(current), {}, current['code'], '2018-04-01', 'gp', coverage)
        self.assertEqual(result['reason'], 'source_catalog_incomplete')
        coverage[current['code']]['correction'] = 'complete_empty'
        self.assertEqual(panel.select_feature(index(current), {}, current['code'],
                                              '2018-04-01', 'gp', coverage)['status'], 'qualified')

    def test_annual_category_notice_can_be_reviewed(self):
        current = annual()
        item = notice(aid='2', pub='2018-03-20', title='2017年年度报告更正公告')
        item['categories'] = {'annual'}
        events = panel.events_for(index(current, item), {'decisions': []}, None)
        self.assertFalse(events[current['code']][0]['ambiguous_annual'])
        events[current['code']][0]['review'] = {'disposition': 'unrelated_business'}
        self.assertEqual(panel.select_feature(index(current, item), events,
                                              current['code'], '2018-04-01', 'gp')['status'], 'qualified')

    def test_full_correction_is_version_not_self_block(self):
        original = annual()
        correction = annual(aid='2', pub='2018-03-20', category='correction', revenue='70')
        events = panel.events_for(index(original, correction), {'decisions': []}, None)
        self.assertEqual(events, {})
        result = panel.select_feature(index(original, correction), events,
                                      original['code'], '2018-04-01', 'gp')
        self.assertEqual(result['status'], 'qualified')
        self.assertEqual(result['announcement_ids'], ['2'])

    def test_ambiguous_annual_blocks_old_version_after_publication(self):
        old = annual()
        unknown = {'code': old['code'], 'id': '2', 'year': None,
                   'title': '年度报告（更新后）', 'publication_date': '2018-03-20',
                   'categories': {'annual'}, 'pdf': {'status': 'failed'}, 'prepared': None}
        records = index(old, unknown)
        events = panel.events_for(records, {'decisions': []}, None)
        self.assertEqual(panel.select_feature(records, events, old['code'],
                                              '2018-03-10', 'gp')['status'], 'qualified')
        self.assertEqual(panel.select_feature(records, events, old['code'],
                                              '2018-04-01', 'gp')['reason'],
                         'applicable_notice_unresolved')

    def test_english_same_day_does_not_replace_chinese_annual(self):
        chinese = annual(year=2023, pub='2024-03-01')
        english = annual(aid='2', year=2023, pub='2024-03-01', assets=None)
        english['title'] = '2023年年度报告（英文版）'
        records = index(chinese, english)
        self.assertFalse(panel.full_candidate(english))
        result = panel.select_feature(records, panel.events_for(records, {'decisions': []}, None),
                                      chinese['code'], '2024-04-01', 'gp')
        self.assertEqual(result['status'], 'qualified')
        self.assertEqual(result['announcement_ids'], ['1'])

    def test_audit_letter_does_not_raise_report_year(self):
        old = annual(year=2023, pub='2024-03-01')
        audit = annual(aid='2', year=2024, pub='2025-03-01')
        audit['title'] = '2024年年度报告审计意见'
        audit['prepared'] = None
        records = index(old, audit)
        self.assertEqual(panel.excluded_doc_kind(audit['title']), '审计')
        self.assertFalse(panel.full_candidate(audit))
        result = panel.select_feature(records, {}, old['code'], '2025-04-01', 'gp')
        self.assertEqual(result['report_year'], 2023)

    def test_excluded_correction_stays_notice_event(self):
        old = annual()
        correction = notice(aid='2', pub='2018-03-20', title='2017年年度报告审计意见更正公告')
        self.assertFalse(panel.full_candidate(correction))
        records = index(old, correction)
        events = panel.events_for(records, {'decisions': []}, None)
        self.assertEqual(len(events[old['code']]), 1)
        self.assertEqual(panel.select_feature(records, events, old['code'],
                                              '2018-04-01', 'gp')['reason'],
                         'applicable_notice_unresolved')

    def test_catalog_expected_retains_failed_and_unissued(self):
        code = 'sh.600000'
        def ann(aid, title):
            return {'announcementId': aid, 'announcementTitle': title,
                    'announcementTime': 1552262400000, 'secCode': '600000'}
        progress = {'codes': {'600000': {'catalogs': {
            'annual': {'exact_announcements': [ann('1', '2018年年度报告'), ann('2', '2019年年度报告')]},
            'correction': {'exact_announcements': [ann('3', '更正公告')]}},
            'pdfs': [{'announcement_id': '1', 'status': 'obtained'},
                     {'announcement_id': '2', 'status': 'failed'}]}}}
        records = panel.expected_index(progress, [code])
        self.assertEqual(len(records), 3)
        self.assertIsNone(records[(code, '3')]['pdf'])
        self.assertEqual(records[(code, '2')]['pdf']['status'], 'failed')

    def test_strict_day_and_age(self):
        item = annual(year=2017, pub='2018-04-30')
        records = index(item)
        self.assertEqual(panel.select_feature(records, {}, item['code'], '2018-04-30', 'gp')['status'], 'unknown')
        self.assertEqual(panel.select_feature(records, {}, item['code'], '2019-04-30', 'gp')['status'], 'qualified')
        self.assertEqual(panel.select_feature(records, {}, item['code'], '2019-05-01', 'gp')['reason'],
                         'annual_older_than_16_months')


if __name__ == '__main__':
    unittest.main()
