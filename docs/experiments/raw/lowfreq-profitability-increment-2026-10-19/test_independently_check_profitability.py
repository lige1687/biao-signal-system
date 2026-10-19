"""Synthetic arithmetic and cutoff checks; never opens real market outcomes."""
import importlib.util
import math
import unittest
from pathlib import Path

path=Path(__file__).with_name('independently_check_profitability.py')
spec=importlib.util.spec_from_file_location('independent_financial_check',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class IndependentFinancialCheckTests(unittest.TestCase):
    def members(self,n=6):
        return [{'code':f'sz.{i:06d}','industry':'C26','momentum':str(i),
                 'gpa':str(n-i),'cfoa':str(i%3)} for i in range(n)]

    def test_tie_average_percentiles_and_code_cutoff(self):
        group=self.members(6)
        for row in group: row['gpa']='1'
        w,d=mod.targets(group,'gpa')
        self.assertEqual({c for c,x in w['F'].items() if x>0},{'sz.000000','sz.000001'})
        self.assertEqual(d['sz.000000']['financial_percentile'],.5)
        self.assertEqual(d['sz.000005']['sector_selected_k'],2)
        self.assertEqual({c for c,x in w['M'].items() if x>0},{'sz.000004','sz.000005'})

    def test_tiny_sector_and_sector_mass_and_diversification(self):
        group=self.members(6)+[{'code':'sh.600001','industry':'C27','momentum':'-1','gpa':'-2','cfoa':'0'}]
        w,d=mod.targets(group,'gpa')
        for method in mod.METHODS:
            self.assertTrue(math.isclose(sum(w[method].values()),1))
            self.assertTrue(math.isclose(sum(w[method][r['code']] for r in group if r['industry']=='C26'),6/7))
            self.assertEqual(w[method]['sh.600001'],1/7)
        self.assertTrue(d['sh.600001']['tiny_no_selection'])
        self.assertNotEqual(w['M'],w['F'])
        for r in group:
            c=r['code'];self.assertEqual(w['D'][c],(w['P'][c]+w['M'][c])/2)

    def test_unknown_scenarios_keep_weight(self):
        group=self.members(6);w,_=mod.targets(group,'gpa')
        returns={r['code']:(None if r['code']=='sz.000000' else .1) for r in group}
        for method in mod.METHODS:
            weight=w[method]['sz.000000']
            minus=sum(x*(returns[c] if returns[c] is not None else -1) for c,x in w[method].items())
            zero=sum(x*(returns[c] if returns[c] is not None else 0) for c,x in w[method].items())
            self.assertTrue(math.isclose(zero-minus,weight))

    def test_periods_and_worst_tenth(self):
        self.assertTrue(mod.period('2017-06','2015-2019'))
        self.assertFalse(mod.period('2021-06','2015-2019'))
        self.assertFalse(mod.period('2017-06','without-2017'))
        x=mod.stats([.2,-.2,None,-.1,.1,.3])
        self.assertEqual(x['defined_months'],5)
        self.assertEqual(x['worst_month'],-.2)
        self.assertEqual(x['worst_10pct_mean'],-.2)
        self.assertEqual(mod.stats([None])['status'],'not_evaluated')

    def test_difference_report_not_false_pass(self):
        a=mod.Audit();a.check('weights','one','weight_F',.2,.3)
        self.assertEqual(len(a.diffs),1)
        self.assertEqual(a.counts['weights'],1)

    def test_quote_drawdown_is_incomplete_without_every_month(self):
        self.assertIsNone(mod.quote_drawdown([.1,None,-.2]))
        self.assertAlmostEqual(mod.quote_drawdown([.1,-.5,.2]),-.5)
        self.assertEqual(mod.quote_drawdown([.1,-1.,.5]),-1.)

    def test_global_spearman_and_constant_correlation(self):
        rows=self.members(6)
        self.assertAlmostEqual(mod.score_spearman(rows,'gpa'),-1.)
        self.assertIsNone(mod.correlation([1,1,1],[2,3,4]))
        self.assertIsNone(mod.correlation([1,2],[2,3]))
        for row in rows:row['gpa']='1'
        self.assertIsNone(mod.score_spearman(rows,'gpa'))

    def test_shared_circular_indices_and_missing_positions(self):
        series={('a','b','c'):[1,None,None,None,None,None],
                ('d','e','f'):[None]*6}
        result=mod.resample_intervals(series,n_months=6,draws=3,seed=7)
        a=result['a','b','c',6,.95];b=result['d','e','f',6,.975]
        self.assertEqual(a['draws_valid'],3)
        self.assertEqual((a['lower'],a['upper']),(1.,1.))
        self.assertEqual(b['draws_valid'],0)
        self.assertIsNone(b['lower'])
        self.assertEqual(a['shared_index_sha256'],b['shared_index_sha256'])
        self.assertEqual(a['shared_index_sha256'],
                         '2a13af8d2290162166240f58571e88de6c0e76eed4611e4677ad3994f218776a')
        # A different measure does not draw new month positions.
        self.assertEqual(result['a','b','c',12,.95]['shared_index_sha256'],a['shared_index_sha256'])

if __name__=='__main__':unittest.main()
