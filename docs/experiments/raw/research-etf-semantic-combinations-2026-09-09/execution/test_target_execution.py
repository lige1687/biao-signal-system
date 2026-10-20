import importlib.util,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent
def load(n,p):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
e=load('target_engine',H/'engine.py');r=load('target_runner',H/'run.py')
def bar(o,c=None):c=o if c is None else c;return {'open':o,'high':max(o,c),'low':min(o,c),'close':c,'volume':1.}
def candidate():return {'candidate_id':'c','config_id':'R1','symbol':'X','signal_date':'2024-01-02','signal_accepted':True,'signal_reject_reason':None,'signal_ref':9.5,'target':10.,'stop':8.,'upper':None,'variant':'C'}
def sim(prices,actions=None):
 obs={'X':{d:{'ema20':1.,'cost20':1.} for d in prices['X']}}
 return e.simulate(prices,actions or [],[candidate()],obs,start='2024-01-02',end=max(prices['X']),initial_per_symbol=100000,weekly_per_symbol=0,fee=0.,config_id='R1',limits={'X':.2},blocked_dates={},limit_changes={},exit_rule=r.exit_rule('E0'))
class Tests(unittest.TestCase):
 def test_target_close_sells_only_next_open_at_actual_price(self):
  p={'X':{'2024-01-01':bar(9.5),'2024-01-02':bar(9.5),'2024-01-03':bar(9.5,10.),'2024-01-04':bar(9.5)}}
  x=sim(p);self.assertEqual([t['date'] for t in x['trades']],['2024-01-03','2024-01-04']);self.assertEqual(x['trades'][-1]['price'],9.5);self.assertEqual(x['trades'][-1]['reason'],'known_target_reached')
 def test_ex_dividend_transforms_target_before_close_test(self):
  p={'X':{'2024-01-01':bar(9.5),'2024-01-02':bar(9.5),'2024-01-03':bar(9.5),'2024-01-04':bar(8.5,9.2),'2024-01-05':bar(9.1)}}
  a=[{'event_id':'d','symbol':'X','type':'cash_dividend','announcement_date':'2024-01-01','record_date':'2024-01-03','ex_date':'2024-01-04','pay_date':'2024-01-05','cash_per_share':1.}]
  x=sim(p,a);self.assertEqual(x['orders'][-1]['signal_date'],'2024-01-04');self.assertAlmostEqual(x['roundtrips'][0]['target'],10*(8.5/9.5))
 def test_unadjusted_target_would_not_trigger(self):
  p={'X':{'2024-01-01':bar(9.5),'2024-01-02':bar(9.5),'2024-01-03':bar(9.5),'2024-01-04':bar(9.2)}}
  self.assertEqual([t['side'] for t in sim(p)['trades']],['buy'])
if __name__=='__main__':unittest.main()
