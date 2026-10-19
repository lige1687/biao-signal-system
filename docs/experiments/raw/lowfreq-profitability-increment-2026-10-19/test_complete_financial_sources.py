"""Synthetic planner boundary checks; no filesystem source data or HTTP."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('completion', Path(__file__).with_name('complete_financial_sources.py'))
completion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(completion)


class FrozenAcquirer:
    @staticmethod
    def _index_mapping(plan):
        return {'600000': 'issuer-one'}

    @staticmethod
    def _payload(code, org, category, date_range, page):
        return {'code': code, 'org': org, 'category': category, 'date_range': date_range,
                'page': page}

    @staticmethod
    def _targets(catalogs, years):
        return [{'code': '600000', 'announcement_id': '10', 'pdf_url': 'https://example.invalid/10.pdf'},
                {'code': '600000', 'announcement_id': '11', 'pdf_url': 'https://example.invalid/11.pdf'}]


def context(state, starts=None):
    return {'plan': {'categories': {'annual': 'A', 'correction': 'C'},
                     'query_date_range': '2014-01-01~2025-12-31',
                     'endpoint': 'https://example.invalid/query',
                     'annual_report_years': list(range(2013, 2025))},
            'cohort': {'fixed_codes': ['sh.600000']},
            'progress': {'codes': {'600000': state}}, 'acquirer': FrozenAcquirer,
            'starts': starts or {}, 'counts': {'catalog': 1, 'pdf': 0, 'total': 1}}


class CompletionTests(unittest.TestCase):
    def test_catalog_wave_only_known_unstarted_pages(self):
        state = {'catalogs': {'annual': {'status': 'incomplete', 'expected_pages': 3,
                                        'pages': [{'page': 1}]},
                              'correction': {'status': 'incomplete', 'expected_pages': None,
                                             'pages': []}}, 'pdfs': []}
        with patch.object(completion, 'snapshot_data', return_value=context(state, {'catalog:600000:annual:1': {}})):
            result = completion.propose({'schema': 'financial-completion-snapshot/1'})
        self.assertEqual(result['stage'], 'catalog')
        self.assertEqual([x['op_id'] for x in result['operations']],
                         ['catalog:600000:annual:2', 'catalog:600000:annual:3',
                          'catalog:600000:correction:1'])
        self.assertFalse(any(x['kind'] == 'pdf' for x in result['operations']))

    def test_started_without_finish_is_permanently_blocked(self):
        state = {'catalogs': {'annual': {'status': 'incomplete', 'expected_pages': None,
                                        'pages': []},
                              'correction': {'status': 'complete_empty'}}, 'pdfs': []}
        with patch.object(completion, 'snapshot_data', return_value=context(
            state, {'catalog:600000:annual:1': {'event': 'start'}})):
            result = completion.propose({'schema': 'financial-completion-snapshot/1'})
        self.assertEqual(result['operation_count'], 0)
        self.assertEqual(result['blocked'][0]['reason'], 'already_started_never_retry')

    def test_pdf_stage_only_after_all_catalogs_complete_and_unique(self):
        state = {'catalogs': {'annual': {'status': 'complete'},
                              'correction': {'status': 'complete_empty'}},
                 'pdfs': [{'announcement_id': '10', 'status': 'obtained'}]}
        with patch.object(completion, 'snapshot_data', return_value=context(state)):
            result = completion.propose({'schema': 'financial-completion-snapshot/1'})
        self.assertEqual(result['stage'], 'pdf')
        self.assertEqual([x['op_id'] for x in result['operations']], ['pdf:600000:11'])

    def test_prior_external_stop_cannot_be_bypassed_by_new_stage(self):
        state = {'catalogs': {'annual': {'status': 'complete'},
                              'correction': {'status': 'complete_empty'}}, 'pdfs': []}
        frozen = context(state)
        frozen['terminal_stop'] = 'prior_http_429'
        with patch.object(completion, 'snapshot_data', return_value=frozen):
            result = completion.propose({'schema': 'financial-completion-snapshot/1'})
        self.assertEqual(result['operation_count'], 0)
        self.assertEqual(result['blocked'], [{'reason': 'prior_http_429'}])

    def test_unretryable_catalog_failure_does_not_block_other_complete_codes(self):
        failed = {'catalogs': {'annual': {'status': 'incomplete', 'pages': []},
                               'correction': {'status': 'complete_empty'}}, 'pdfs': []}
        frozen = context(failed, {'catalog:600000:annual:1': {'event': 'start'}})
        frozen['cohort']['fixed_codes'].append('sh.600001')
        frozen['progress']['codes']['600001'] = {'catalogs': {
            'annual': {'status': 'complete'}, 'correction': {'status': 'complete_empty'}}, 'pdfs': []}
        with patch.object(completion, 'snapshot_data', return_value=frozen):
            result = completion.propose({'schema': 'financial-completion-snapshot/1'})
        self.assertEqual(result['stage'], 'pdf')
        self.assertTrue(result['operations'])
        self.assertTrue(all(x['code'] == '600001' for x in result['operations']))
        self.assertTrue(any(x['reason'] == 'catalog_incomplete_no_permitted_page_remaining'
                            for x in result['blocked']))


if __name__ == '__main__':
    unittest.main()
