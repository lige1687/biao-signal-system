import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,P/file); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
v1=load('qualify_reported_op_v1','qualify_reported_op.py')
v2=load('qualify_reported_op_v2','qualify_reported_op_v2.py')

class V2QualificationTests(unittest.TestCase):
    def setUp(self):
        self.sub={'adsh':'A','cik':'1','name':'TEST','sic':'1234','form':'10-K','fp':'FY','period':'20201231','fy':'2020','fye':'1231','filed':'20210201','accepted':'2021-02-01 10:00:00.0','source_zip':'sec-fsds-2021q1.zip'}
        self.facts=[];self.pres=[]
        self.add('OperatingIncomeLoss','100','4','IS',2)
        self.add('InterestExpense','10','4','IS',4)
        self.add('Assets','1000','0','BS',2);self.add('Liabilities','400','0','BS',3)
        self.add(v2.INCLUSIVE,'600','0','BS',4);self.add('PreferredStockValue','0','0','BS',5)
    def add(self,tag,value,qtrs,stmt,line,report='1',version='us-gaap/2020'):
        self.facts.append({'adsh':'A','tag':tag,'version':version,'ddate':'20201231','qtrs':qtrs,'uom':'USD','segments':'','coreg':'','value':value,'source_zip':'sample.zip'})
        self.pres.append({'adsh':'A','report':report,'line':str(line),'stmt':stmt,'inpth':'0','tag':tag,'version':version,'plabel':tag})
    def test_valid_source_and_negative_interest_flags_manual_review(self):
        self.assertTrue(v2.qualify_filing(self.sub,self.facts,self.pres)['sourcequalified'])
        for row in self.facts:
            if row['tag']=='InterestExpense':row['value']='-10'
        r=v2.qualify_filing(self.sub,self.facts,self.pres)
        self.assertTrue(r['sourcequalified']);self.assertTrue(r['manual_review_required']);self.assertFalse(r['automatic_scoring_eligible'])
    def test_multireport_cross_line_false_positive_rejected(self):
        # A has OI line 20 and interest line 10 (interest is before OI).
        # B has OI line 3 but no interest. V1 mixed B's minimum line with A's report;
        # v2 pairs actual report/line and finds no permissible interest row.
        self.facts=[r for r in self.facts if r['tag'] not in ('OperatingIncomeLoss','InterestExpense')]
        self.pres=[r for r in self.pres if r['tag'] not in ('OperatingIncomeLoss','InterestExpense')]
        self.add('OperatingIncomeLoss','100','4','IS',20,'A')
        self.add('OperatingIncomeLoss','100','4','IS',3,'B')
        self.add('InterestExpense','10','4','IS',10,'A')
        self.assertTrue(v1.qualify_filing(self.sub,self.facts,self.pres)['sourcequalified'])
        r=v2.qualify_filing(self.sub,self.facts,self.pres)
        self.assertFalse(r['sourcequalified'])
        self.assertFalse(r['steps']['interest']['passed'])
        self.assertEqual({(x['report'],x['line']) for x in r['source_facts']['operating_income'][0]['presentation']},{('A','20'),('B','3')})
        self.assertEqual(r['source_facts']['interest'],[])
        self.assertEqual(len(r['unmatched_or_pre_oi_interest_lines']),1)
    def test_interest_values_conflict_across_legal_reports_rejected(self):
        self.facts=[r for r in self.facts if r['tag']!='OperatingIncomeLoss'];self.pres=[r for r in self.pres if r['tag']!='OperatingIncomeLoss']
        self.facts=[r for r in self.facts if r['tag']!='InterestExpense'];self.pres=[r for r in self.pres if r['tag']!='InterestExpense']
        self.add('OperatingIncomeLoss','100','4','IS',2,'A');self.add('OperatingIncomeLoss','100','4','IS',2,'B')
        self.add('InterestExpense','10','4','IS',4,'A');self.add('InterestExpense','11','4','IS',4,'B')
        r=v2.qualify_filing(self.sub,self.facts,self.pres)
        self.assertFalse(r['steps']['interest']['passed'])

if __name__=='__main__':unittest.main(verbosity=2)
