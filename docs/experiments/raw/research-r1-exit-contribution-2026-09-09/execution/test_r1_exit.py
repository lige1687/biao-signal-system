import importlib.util,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r1test',HERE/'engine.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def b(o,c=None): c=o if c is None else c;return dict(open=o,high=max(o,c),low=min(o,c),close=c,volume=1.)
def candidate(stop=8.): return dict(candidate_id='r1-1',config_id='R1',symbol='X',signal_date='2024-01-02',signal_accepted=True,signal_reject_reason=None,signal_ref=10.,target=None,stop=stop,upper=None,variant='diagnostic')
def road(p,o,c):
 if c<o['ema20'] and c<o['cost20']:return 'ema_cost_exit'
def run(prices,rule=road,stop=8.,blocked=None,actions=None):
 obs={'X':{d:{'ema20':9.5,'cost20':9.5} for d in prices['X']}}
 return m.simulate(prices,actions or [],[candidate(stop)],obs,start='2024-01-02',end=max(prices['X']),initial_per_symbol=100000,weekly_per_symbol=0,fee=.001,config_id='R1',limits={'X':.1},limit_changes={},blocked_dates={'X':blocked or []},exit_rule=rule)
class Tests(unittest.TestCase):
 def test_road_weak_differs_before_structure_break(self):
  p={'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(10,9),'2024-01-04':b(9)}}
  self.assertEqual([x['side'] for x in run(p)['trades']],['buy','sell']);self.assertEqual([x['side'] for x in run(p,lambda p,o,c:None)['trades']],['buy'])
 def test_structure_has_priority_same_day(self):
  p={'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(10,7),'2024-01-04':b(7)}}
  self.assertEqual(run(p,lambda p,o,c:'road')['orders'][-1]['reason'],'structure_stop')
 def test_equal_stop_does_not_exit(self):
  p={'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(10,8),'2024-01-04':b(8)}}
  self.assertEqual([x['side'] for x in run(p,lambda p,o,c:None)['trades']],['buy'])
 def test_signal_after_buy_sells_next_day(self):
  p={'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(10,7),'2024-01-04':b(7)}}
  self.assertEqual([x['date'] for x in run(p)['trades']],['2024-01-03','2024-01-04'])
 def test_blocked_exit_delays(self):
  p={'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(10,7),'2024-01-04':b(7),'2024-01-05':b(7)}}
  self.assertEqual(run(p,blocked=['2024-01-04'])['trades'][-1]['date'],'2024-01-05')
 def test_terminal_open_position(self):
  p={'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(10)}}
  self.assertFalse(run(p,lambda p,o,c:None)['roundtrips'][0]['closed'])
if __name__=='__main__':unittest.main()
