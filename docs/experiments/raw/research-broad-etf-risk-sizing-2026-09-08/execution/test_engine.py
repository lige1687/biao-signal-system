import importlib.util,sys,unittest
from pathlib import Path
H=Path(__file__).parent
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
old=load('old',H.parents[1]/'research-broad-etf-technical-2026-09-08/execution/engine.py');new=load('new',H/'engine.py')
def b(x):return dict(open=x,high=x,low=x,close=x,volume=1.)
def prices(open_price=10):return {'X':{'2024-01-01':b(10),'2024-01-02':b(10),'2024-01-03':b(open_price),'2024-01-04':b(open_price)}}
def c(stop=9,target=None,reject='target_unavailable'):
 return dict(candidate_id='R1-x',config_id='R1',symbol='X',signal_date='2024-01-02',signal_accepted=False,signal_reject_reason=reject,signal_ref=10.,target=target,stop=stop,upper=None,variant='breakout')
def run(m,cs=None,px=10,fee=.001,capital=100000,**extra):
 return m.simulate(prices(px),[],cs or [],{'X':{d:{'ema20':1.,'cost20':1.} for d in prices(px)['X']}},start='2024-01-02',end='2024-01-04',initial_per_symbol=capital,weekly_per_symbol=0,fee=fee,config_id='R1',limits={'X':.1},**extra)
class Tests(unittest.TestCase):
 def test_default_old_behavior_exact(self):self.assertEqual(run(old,[c()]),run(new,[c()]))
 def test_missing_target_bypassed_but_risk_sized(self):
  r=run(new,[c()],risk_sized_config_set={'R1'});self.assertEqual(r['trades'][0]['shares'],1000);self.assertEqual(r['trades'][0]['risk_budget'],1000)
 def test_below_three_bypassed(self):
  r=run(new,[c(target=10.5,reject='signal_reward_risk_below_3')],risk_sized_config_set={'R1'});self.assertEqual(r['orders'][0]['status'],'filled')
 def test_positive_risk_required(self):
  r=run(new,[c(stop=10)],risk_sized_config_set={'R1'});self.assertEqual(r['orders'][0]['reason'],'nonpositive_signal_risk')
 def test_under_one_lot_rejected(self):
  r=run(new,[c(stop=9)],capital=500,risk_sized_config_set={'R1'});self.assertEqual(r['orders'][0]['reason'],'insufficient_cash_or_risk_lot')
 def test_fee_cash_cap(self):
  r=run(new,[c(stop=9.9)],fee=.002,risk_sized_config_set={'R1'});self.assertEqual(r['trades'][0]['shares'],9900);self.assertLessEqual(r['trades'][0]['notional']+r['trades'][0]['fee'],100000)
 def test_budget_uses_prior_day_not_buy_day_close(self):
  p=prices();p['X']['2024-01-03']=dict(open=10.,high=11.,low=10.,close=11.,volume=1.)
  obs={'X':{d:{'ema20':1.,'cost20':1.} for d in p['X']}}
  r=new.simulate(p,[],[c()],obs,start='2024-01-02',end='2024-01-04',initial_per_symbol=100000,weekly_per_symbol=0,fee=.001,config_id='R1',limits={'X':.1},risk_sized_config_set={'R1'})
  self.assertEqual(r['trades'][0]['risk_budget'],1000.);self.assertEqual(r['trades'][0]['previous_product_equity'],100000.)
  self.assertEqual(r['daily'][1]['equity'],100990.)
if __name__=='__main__':unittest.main()
