import unittest, math
from cash_engine import simulate
from test_cash_engine import prices, run

class HistoryChecks(unittest.TestCase):
    def test_nonfinite_close_rejected(self):
        p=prices();p['x']['2023-01-02']['close']=float('nan')
        with self.assertRaises(ValueError):run(p)
    def test_bad_event_sequence_rejected(self):
        e=dict(symbol='x',type='cash_dividend',event_id='e',record_date='2023-01-03',ex_date='2023-01-04',pay_date='2023-01-02',cash_per_share=1)
        with self.assertRaises(ValueError):run(prices(),events=[e])
    def test_duplicate_event_rejected(self):
        e=dict(symbol='x',type='cash_dividend',event_id='e',record_date='2023-01-03',ex_date='2023-01-04',pay_date='2023-01-05',cash_per_share=1)
        with self.assertRaises(ValueError):run(prices(),events=[e,e])
    def test_same_economic_event_different_id_rejected(self):
        e=dict(symbol='x',type='cash_dividend',event_id='e',record_date='2023-01-03',ex_date='2023-01-04',pay_date='2023-01-05',cash_per_share=1)
        with self.assertRaises(ValueError):run(prices(),events=[e,dict(e,event_id='other')])
    def test_impossible_split_date_rejected(self):
        e=dict(symbol='x',type='split',event_id='e',ex_date='2023-02-30',ratio=5)
        with self.assertRaises(ValueError):run(prices(),events=[e])
    def test_limit_change_only_from_effective_date(self):
        p=prices('2020-08-16','2020-08-25')
        for d in ['2020-08-17','2020-08-24']:p['x'][d]={'open':11.5,'close':10}
        r=simulate(p,[],start='2020-08-17',end='2020-08-25',weekly=1200,fee=0,cash_rate=0,rebalance=False,limits={'x':.1},limit_changes={'x':[('2020-08-24',.2)]})
        self.assertNotIn('2020-08-17',[t['date'] for t in r['trades']])
        self.assertIn('2020-08-24',[t['date'] for t in r['trades']])
    def test_late_resume_blocks_open_not_close_mark(self):
        p=prices('2021-02-05','2021-02-10');del p['x']['2021-02-08']
        p['x']['2021-02-09']={'open':10.1,'close':10.2}
        r=simulate(p,[],start='2021-02-08',end='2021-02-10',weekly=2000,fee=0,cash_rate=0,rebalance=False,limits={'x':.1},blocked_dates={'x':['2021-02-08','2021-02-09']})
        self.assertEqual(r['trades'][0]['date'],'2021-02-10')
        self.assertEqual(r['daily'][1]['mark_x'],10.2)
        self.assertEqual(r['daily'][1]['cash'],2000)
    def test_split_during_missing_day_then_resume(self):
        p=prices('2022-01-09','2022-01-17');del p['x']['2022-01-13']
        for d in p['x']:
            if d>'2022-01-13':p['x'][d]={'open':2,'close':2}
        e=dict(symbol='x',type='split',ex_date='2022-01-13',ratio=5,event_id='s')
        r=simulate(p,[e],start='2022-01-10',end='2022-01-17',weekly=1000,fee=0,cash_rate=0,rebalance=False,limits={'x':.1},blocked_dates={'x':['2022-01-13']})
        self.assertEqual(r['daily'][3]['units_x'],500)
        self.assertEqual(r['daily'][3]['mark_x'],2)
        self.assertTrue(all(abs(d['nav']-1)<1e-12 for d in r['daily']))
        self.assertEqual(r['daily'][-1]['equity'],2000)

if __name__=='__main__':unittest.main(verbosity=2)
