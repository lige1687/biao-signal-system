import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).with_name('qualify_reported_op.py')
spec=importlib.util.spec_from_file_location('qualify_reported_op',SCRIPT)
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)

class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.sub={'adsh':'A','cik':'1','name':'TEST','sic':'1234','form':'10-K','fp':'FY','period':'20201231','fy':'2020','fye':'1231','filed':'20210201','accepted':'2021-02-01 10:00:00.0','source_zip':'sec-fsds-2021q1.zip'}
        self.facts=[]; self.pres=[]
        self.add('OperatingIncomeLoss','100','4','IS',2)
        self.add('InterestExpense','10','4','IS',4)
        self.add('Assets','1000','0','BS',2)
        self.add('Liabilities','400','0','BS',3)
        self.add(q.INCLUSIVE,'600','0','BS',4)
        self.add('PreferredStockValue','0','0','BS',5)
    def add(self,tag,value,qtrs,stmt,line,version='us-gaap/2020',ddate='20201231',uom='USD',segments='',coreg=''):
        self.facts.append({'adsh':'A','tag':tag,'version':version,'ddate':ddate,'qtrs':qtrs,'uom':uom,'segments':segments,'coreg':coreg,'value':value,'source_zip':'sample.zip'})
        self.pres.append({'adsh':'A','report':'1','line':str(line),'stmt':stmt,'inpth':'0','tag':tag,'version':version,'plabel':tag})
    def result(self): return q.qualify_filing(self.sub,self.facts,self.pres)
    def test_valid_structure_passes(self): self.assertTrue(self.result()['sourcequalified'])
    def test_per_share_preferred_cannot_substitute_total(self):
        self.facts=[x for x in self.facts if x['tag']!='PreferredStockValue'];self.pres=[x for x in self.pres if x['tag']!='PreferredStockValue']
        self.add('PreferredStockParOrStatedValuePerShare','0','0','BS',5)
        self.assertFalse(self.result()['sourcequalified'])
    def test_custom_same_name_is_not_standard(self):
        self.add('OperatingIncomeLoss','999','4','IS',1,version='0000123456-20-000001')
        self.assertTrue(self.result()['sourcequalified'])
    def test_parent_plus_nci_not_double_added(self):
        self.add('StockholdersEquity','500','0','BS',6);self.add('MinorityInterest','200','0','BS',7)
        self.assertFalse(self.result()['sourcequalified'])
    def test_interest_before_oi_rejected(self):
        self.pres=[p for p in self.pres if p['tag']!='InterestExpense'];self.pres.append({'adsh':'A','report':'1','line':'1','stmt':'IS','inpth':'0','tag':'InterestExpense','version':'us-gaap/2020'})
        self.assertFalse(self.result()['sourcequalified'])
    def test_missing_preferred_not_zero(self):
        self.facts=[x for x in self.facts if x['tag']!='PreferredStockValue']; self.pres=[x for x in self.pres if x['tag']!='PreferredStockValue']
        self.assertFalse(self.result()['sourcequalified'])
    def test_ambiguous_interest_values_rejected(self):
        self.add('InterestAndDebtExpense','11','4','IS',5)
        self.assertFalse(self.result()['sourcequalified'])
    def test_nonpositive_equity_rejected(self):
        for x in self.facts:
            if x['tag']==q.INCLUSIVE: x['value']='-600'
            if x['tag']=='Assets': x['value']='-200'
        self.assertFalse(self.result()['sourcequalified'])
    def test_nonzero_temporary_equity_rejected(self):
        self.add('RedeemableNoncontrollingInterestEquityCarryingAmount','20','0','BS',8)
        self.assertFalse(self.result()['sourcequalified'])
    def test_missing_interest_rejected(self):
        self.facts=[x for x in self.facts if x['tag']!='InterestExpense'];self.pres=[x for x in self.pres if x['tag']!='InterestExpense']
        self.assertFalse(self.result()['sourcequalified'])

if __name__=='__main__': unittest.main(verbosity=2)
