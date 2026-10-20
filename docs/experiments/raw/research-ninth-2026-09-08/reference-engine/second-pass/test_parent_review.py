"""Independent adversarial and exact-compatibility review; synthetic prices only."""
import sys
sys.dont_write_bytecode=True
import copy
import importlib.util
from pathlib import Path
import unittest
import engine

spec=importlib.util.spec_from_file_location('frozen_prior',Path(__file__).with_name('engine_baseline.py'))
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def bar(o=1.,c=None):
 c=o if c is None else c
 return dict(open=o,close=c,high=max(o,c)+.02,low=min(o,c)-.02,volume=1000)

def fixture():
 prices={'X':{'2023-12-29':bar(),**{f'2024-01-{d:02d}':bar() for d in [1,2,3,4,5,8,9,10]}}}
 obs={'X':{d:dict(ema20=.5,cost20=.5,sma20=.5,sma60=.4,ema20_slope=.01,sma20_slope=.01) for d in prices['X']}}
 return prices,obs

def candidate(**kw):
 c=dict(candidate_id='original-a',symbol='X',signal_date='2024-01-01',signal_ref=1.,stop=.9,target=None,upper=1.,variant='breakout',signal_accepted=False,signal_reject_reason='target_unavailable',target_source='missing',target_confirmed_at=None)
 c.update(kw);return c

def run(config='R0',c=None,prices=None,obs=None,actions=(),module=engine,**kw):
 if prices is None:prices,default=fixture();obs=obs or default
 return module.simulate(prices,list(actions),[] if config=='P6' else [c or candidate()],obs,
  start='2024-01-01',end='2024-01-10',weekly_per_symbol=kw.pop('weekly_per_symbol',250),fee=.001,
  config_id=config,limits={'X':1.},**kw)

class ParentReview(unittest.TestCase):
 def test_all_existing_configs_exactly_equal_with_prior_engine(self):
  for cfg in ['P'+str(i) for i in range(8)]:
   for scenario in ['plain','early_exit','split','dividend']:
    with self.subTest(config=cfg,scenario=scenario):
     prices,obs=fixture();actions=[];c=candidate(target=1.6,signal_accepted=True,signal_reject_reason=None)
     if scenario=='early_exit':prices['X']['2024-01-02']=bar(1.,.8)
     if scenario=='split':
      del prices['X']['2024-01-03']
      for d in prices['X']:
       if d>='2024-01-04':prices['X'][d]=bar(.2);obs['X'][d].update(ema20=.1,cost20=.1,sma20=.1,sma60=.08)
      actions=[dict(event_id='s',symbol='X',type='split',announcement_date='2023-12-20',ex_date='2024-01-03',ratio=5)]
     if scenario=='dividend':
      for d in prices['X']:
       if d>='2024-01-04':prices['X'][d]=bar(.9)
      actions=[dict(event_id='d',symbol='X',type='cash_dividend',announcement_date='2023-12-20',record_date='2024-01-02',ex_date='2024-01-04',pay_date='2024-01-06',cash_per_share=.1)]
     args=dict(config=cfg,c=c,prices=prices,obs=obs,actions=actions,weekly_per_symbol=2500)
     self.assertEqual(run(**args,module=engine),run(**args,module=old))

 def test_exact_rejection_whitelist_does_not_match_prefixes_or_missing(self):
  for why in [None,'','invalid_structure_risk','warmup_incomplete','target_unavailable_and_other','signal_reward_risk_below_3|other','missing_or_invalid_target','signal_rr_below3']:
   with self.subTest(reason=why):
    r=run(c=candidate(signal_reject_reason=why));self.assertEqual(r['trades'],[])
    self.assertEqual(r['orders'][0]['status'],'rejected');self.assertEqual(r['orders'][0]['candidate_metadata']['signal_reject_reason'],why)

 def test_original_multiple_invalid_fields_keep_rejection_priority(self):
  for cfg in ['P0','P5']:
   for stop,target in [(None,None),(0.,None),(-1.,0.),(.9,0.)]:
    with self.subTest(config=cfg,stop=stop,target=target):
     c=candidate(stop=stop,target=target,signal_accepted=True,signal_reject_reason=None)
     self.assertEqual(run(config=cfg,c=c),run(config=cfg,c=c,module=old))

 def test_white_reason_cannot_bypass_signal_positive_risk(self):
  for stop,ref in [(None,1.),(0.,1.),(-.1,1.),(1.,1.),(.9,.8),(.9,None),(.9,float('nan'))]:
   with self.subTest(stop=stop,ref=ref):
    r=run(c=candidate(stop=stop,signal_ref=ref));self.assertEqual(r['trades'],[])

 def test_target_not_used_or_destroyed_and_parent_config_mapped(self):
  for cfg,original in [('R0','P0'),('R1','P5')]:
   for target in [None,0.,.5,1.1]:
    with self.subTest(config=cfg,target=target):
     c=candidate(target=target);before=copy.deepcopy(c);r=run(config=cfg,c=c)
     self.assertEqual(len(r['trades']),1);self.assertEqual(c,before)
     o=r['orders'][0];self.assertEqual(o['target'],target)
     self.assertEqual(o['candidate_metadata']['target'],target)
     self.assertFalse(o['candidate_metadata']['signal_accepted'])
     self.assertEqual(o['candidate_metadata']['signal_reject_reason'],'target_unavailable')
     self.assertTrue(o['diagnostic_reference_only']);self.assertTrue(o['candidate_metadata']['diagnostic_reference_only'])
     self.assertEqual(o['original_candidate_id'],'original-a');self.assertEqual(o['original_config_id'],original)

 def test_split_pending_open_risk_still_rejected(self):
  prices,obs=fixture();prices['X']['2024-01-02']=bar(.17)
  for d in prices['X']:
   if d>='2024-01-03':prices['X'][d]=bar(.2)
  action=dict(event_id='s',symbol='X',type='split',announcement_date='2023-12-20',ex_date='2024-01-02',ratio=5)
  r=run(prices=prices,obs=obs,actions=[action]);self.assertEqual(r['trades'],[])
  self.assertEqual(r['orders'][0]['reason'],'nonpositive_open_risk')
  self.assertAlmostEqual(r['orders'][0]['stop'],.18)
  self.assertEqual(r['orders'][0]['candidate_metadata']['stop'],.9)

 def test_diagnostic_still_obeys_earliest_entry_and_close_exit(self):
  prices,obs=fixture();prices['X']['2024-01-02']=bar(1.,.8)
  r=run(prices=prices,obs=obs);self.assertEqual([x['date'] for x in r['trades']],['2024-01-02','2024-01-03'])
  self.assertEqual(r['trades'][1]['reason'],'structure_stop')

 def test_unknown_config_still_raises(self):
  with self.assertRaises(ValueError):run(config='R2')

 def test_prelabelled_root_diagnostic_metadata_no_duplicate_keyword(self):
  c=candidate(diagnostic_reference_only=True,original_candidate_id='P5-source-id',original_config_id='P5')
  r=run(config='R1',c=c);self.assertEqual(len(r['trades']),1)
  self.assertEqual(r['orders'][0]['original_candidate_id'],'P5-source-id')
  self.assertEqual(r['orders'][0]['candidate_metadata']['original_config_id'],'P5')

if __name__=='__main__':unittest.main(verbosity=2)
