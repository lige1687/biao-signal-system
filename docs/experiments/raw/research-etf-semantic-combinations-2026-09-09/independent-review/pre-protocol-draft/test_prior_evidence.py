import unittest
from prior_evidence import build_evidence
class EvidenceTests(unittest.TestCase):
 def rows(self):
  return [
   {'candidate_id':'a','group':'g','exit_variant':'fast','signal_date':'2020-01-01','outcome_known_date':'2020-01-05','net_return':'-.1','holding_days':4},
   {'candidate_id':'a','group':'g','exit_variant':'slow','signal_date':'2020-01-01','outcome_known_date':'2020-02-01','net_return':'.2','holding_days':31},
   {'candidate_id':'b','group':'g','exit_variant':'fast','signal_date':'2020-01-10','outcome_known_date':None,'net_return':'.5','holding_days':30},
   {'candidate_id':'b','group':'g','exit_variant':'slow','signal_date':'2020-01-10','outcome_known_date':None,'net_return':'1','holding_days':30}]
 def test_future_outcome_never_visible(self):
  x=build_evidence(self.rows(),['2020-01-20'],group_fields=['group']);a={r['exit_variant']:r for r in x};self.assertEqual(a['fast']['visible_completed'],1);self.assertEqual(a['slow']['visible_completed'],0)
 def test_unresolved_explicit(self):
  x=build_evidence(self.rows(),['2020-01-20'],group_fields=['group']);self.assertTrue(all(r['unresolved_count']>=1 for r in x))
 def test_same_mature_candidate_cohort(self):
  x=build_evidence(self.rows(),['2020-01-20'],group_fields=['group'],maturity_days=15);a={r['exit_variant']:r for r in x};self.assertEqual(a['fast']['cohort_count'],1);self.assertEqual(a['slow']['cohort_count'],1)
 def test_same_day_visibility_is_explicit(self):
  x=build_evidence(self.rows(),['2020-01-05'],group_fields=['group'],inclusive_known=False);a={r['exit_variant']:r for r in x};self.assertEqual(a['fast']['visible_completed'],0)
 def test_no_results_is_not_zero(self):
  x=build_evidence(self.rows(),['2019-12-31'],group_fields=['group']);self.assertEqual(x,[])
if __name__=='__main__':unittest.main()
