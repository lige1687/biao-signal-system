"""Source-only synthetic checks; no market outcomes or real panel reads."""
import importlib.util
import math
import unittest
from pathlib import Path

path=Path(__file__).with_name('summarize_financial_source_coverage.py')
spec=importlib.util.spec_from_file_location('coverage_source_only',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CoverageTests(unittest.TestCase):
    def test_four_hold_all_five_select_one_and_decimal_equality(self):
        groups={'C26':['1','1.0','1.00','1'],'C27':['2','2','2','2','3']}
        x=mod.opportunity(groups)
        self.assertEqual(x['pool_n'],9)
        self.assertEqual(x['selected_slots'],5)
        self.assertTrue(math.isclose(x['tiny_hold_all_mass'],4/9))
        self.assertTrue(math.isclose(x['selected_fraction'],5/9))
        self.assertTrue(math.isclose(x['nonconstant_weight'],5/9))
        self.assertIsNone(mod.opportunity({})['selected_fraction'])

    def test_retrospective_exit_tag_cannot_filter_pool(self):
        row={'industry':'C26','gp_status':'qualified','cfo_status':'qualified',
             'outDate':'2016-01-01'}
        self.assertEqual(mod.pool_flags('eligible',row),(True,True,True))
        row['outDate']=''
        self.assertEqual(mod.pool_flags('eligible',row),(True,True,True))
        self.assertEqual(mod.pool_flags('not_eligible',row),(False,False,False))
        row['industry']='J66'
        self.assertEqual(mod.pool_flags('eligible',row),(False,False,False))

    def test_incomplete_but_terminal_is_distinct_from_pending(self):
        states={'A':{'code_status':'complete'},'B':{'code_status':'incomplete'}}
        label,complete,attempt=mod.source_state_summary(states,{'both_complete':1})
        self.assertEqual(label,'sources_incomplete_attempts_terminal')
        self.assertFalse(complete['all_codes_fully_complete'])
        self.assertTrue(attempt['terminal'])
        states['B']['code_status']='running'
        label,_,attempt=mod.source_state_summary(states,{'both_complete':1})
        self.assertEqual(label,'attempts_pending')
        self.assertFalse(attempt['terminal'])

    def test_impossible_recovery_dates_are_rejected(self):
        result={'status':'qualified','report_year':2019,'publication_date':'2020-04-01',
                'announcement_ids':['new-annual'],
                'recovery_evidence':[{'reason':'measurement_recovered_with_unreviewed_prior_notice',
                                      'notice_review_status':'unreviewed','financial_authenticity_certified':False,
                                      'publication_date':'2020-01-01','annual_fiscal_end':'2019-12-31',
                                      'annual_publication_date':'2020-04-01',
                                      'annual_announcement_ids':['new-annual']}]}
        with self.assertRaisesRegex(ValueError,'ordering'):
            mod.validate_recovery_evidence(result,'2020-04-30')
        result['recovery_evidence'][0]['publication_date']='2019-11-01'
        self.assertEqual(len(mod.validate_recovery_evidence(result,'2020-04-30')),1)
        result['status']='unknown'
        result['reason']='applicable_notice_unresolved'
        result['blockers']=[{'announcement_id':'later-unreviewed','reason':'unreviewed_notice'}]
        self.assertEqual(len(mod.validate_recovery_evidence(result,'2020-04-30')),1)
        self.assertEqual(result['status'],'unknown')
        result['recovery_evidence'][0]['annual_publication_date']='2020-05-01'
        with self.assertRaisesRegex(ValueError,'ordering'):
            mod.validate_recovery_evidence(result,'2020-04-30')
        result['recovery_evidence'][0]['annual_publication_date']='2020-04-01'
        result['status']='qualified'
        with self.assertRaisesRegex(ValueError,'16-month'):
            mod.validate_qualified_dates(result,'2021-06-30')
        result['publication_date']='2020-05-01'
        with self.assertRaisesRegex(ValueError,'16-month'):
            mod.validate_qualified_dates(result,'2020-04-30')

if __name__=='__main__':unittest.main()
