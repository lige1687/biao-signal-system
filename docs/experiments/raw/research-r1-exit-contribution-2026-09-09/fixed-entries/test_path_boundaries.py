import unittest,importlib.util,sys
from pathlib import Path
from decimal import Decimal as D
P=Path(__file__).with_name('run_fixed_entries.py');s=importlib.util.spec_from_file_location('fx',P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def base():
 bm={d:{'open':o,'close':c} for d,o,c in [('2020-01-01','10','10'),('2020-01-02','10','9'),('2020-01-03','9','9'),('2020-01-04','8','7'),('2020-01-05','6','6')]}
 obs={'X':{d:{'ema20':'10','cost20':'10'} for d in bm}}
 rt={'symbol':'X','entry_date':'2020-01-02','initial_stop':'8','position_id':'P','candidate_id':'C','exit_date':None,'net_pnl':'0','net_return':'0'}
 buy={'shares':'100','notional':'1000','fee':'1','price':'10','account_id':'A'}
 cfg={'blocked_dates':{'X':[]},'limits':{'X':'1'},'limit_changes':{'X':[]}}
 return bm,obs,rt,buy,cfg
def run(method,actions=None,blocked=None):
 bm,o,r,b,c=base();c['blocked_dates']['X']=blocked or [];return m.path(r,b,None,D('.001'),method,bm,actions or [],o,c)[0]
class Boundaries(unittest.TestCase):
 def test_road_and_structure_diverge(self):
  self.assertEqual(run('road_or_structure')['exit_date'],'2020-01-03')
  self.assertEqual(run('structure_only')['exit_date'],'2020-01-05')
 def test_structure_priority(self):
  bm,o,r,b,c=base();r['initial_stop']='9.5';p=m.path(r,b,None,D('.001'),'road_or_structure',bm,[],o,c)[0];self.assertEqual(p['exit_reason'],'structure_stop')
 def test_blocked_exit_delays(self):self.assertEqual(run('road_or_structure',blocked=['2020-01-03'])['exit_date'],'2020-01-04')
 def test_entry_ex_day_does_not_readjust_stop(self):
  a={'event_id':'D','symbol':'X','type':'cash_dividend','effective_date':'2020-01-02','record_date':'2020-01-01','pay_date':'2020-01-04','cash':'1'}
  p=run('structure_only',[a]);self.assertEqual(p['initial_stop'],p['final_stop']);self.assertEqual(p['dividend_accrued'],0)
 def test_record_then_sell_still_keeps_dividend(self):
  a={'event_id':'D','symbol':'X','type':'cash_dividend','effective_date':'2020-01-04','record_date':'2020-01-02','pay_date':'2020-01-05','cash':'1'}
  p=run('road_or_structure',[a]);self.assertEqual(p['exit_date'],'2020-01-03');self.assertEqual(p['dividend_accrued'],D(100));self.assertEqual(p['dividend_paid'],D(100))
 def test_equal_road_threshold_not_exit(self):
  bm,o,r,b,c=base();bm['2020-01-02']['close']='10';o['X']['2020-01-02']={'ema20':'10','cost20':'11'}
  p=m.path(r,b,None,D('.001'),'road_or_structure',bm,[],o,c)[0];self.assertNotEqual(p['exit_signal_date'],'2020-01-02')
if __name__=='__main__':unittest.main()
