import unittest
from prior_evidence import build_prior_evidence
class Tests(unittest.TestCase):
 def data(self):
  base=[]
  for v,ex,ret in [('E0','2020-01-09','.1'),('E1','2020-01-20','-.1')]:
   base.append({'candidate_id':'a','symbol':'X','group':'G0','variant':v,'fee':'0.001','signal_date':'2020-01-01','entered':True,'exit_date':ex,'net_return':ret,'maturity_quote_date':'2020-04-01','return_at_60':'.05','holding_days':8})
  for v in ('E0','E1'):base.append({'candidate_id':'b','symbol':'X','group':'G0','variant':v,'fee':'0.001','signal_date':'2020-01-10','entered':False,'exit_date':None,'net_return':None,'maturity_quote_date':None,'return_at_60':None,'holding_days':0})
  return base
 def runx(self,day):return build_prior_evidence(self.data(),[{'candidate_id':'z','symbol':'X','signal_date':day}],groups=['G0','GP'],variants=['E0','E1'],fees=['0.001'])
 def test_strict_exit_before(self):
  x=self.runx('2020-01-20');d={r['variant']:r for r in x if r['group']=='G0'};self.assertEqual(d['E0']['completed_evidence']['count'],1);self.assertEqual(d['E1']['completed_evidence']['count'],0)
 def test_future_unentered_not_unresolved(self):self.assertTrue(all(r['unresolved_count']==0 for r in self.runx('2020-02-01')))
 def test_empty_groups_are_rows(self):self.assertEqual(len(self.runx('2020-02-01')),4)
 def test_quote_maturity_strict(self):
  a=self.runx('2020-04-01');b=self.runx('2020-04-02');self.assertEqual(a[0]['mature_60_evidence']['count'],0);self.assertEqual(b[0]['mature_60_evidence']['count'],1)
 def test_current_candidate_excluded(self):
  x=build_prior_evidence(self.data(),[{'candidate_id':'a','symbol':'X','signal_date':'2020-02-01'}],groups=['G0'],variants=['E0','E1'],fees=['0.001']);self.assertTrue(all(r['completed_evidence']['count']==0 for r in x))
 def test_threshold_distinct_candidates(self):self.assertTrue(all(r['history_display_status']=='insufficient_history' for r in self.runx('2021-01-01')))
if __name__=='__main__':unittest.main()
