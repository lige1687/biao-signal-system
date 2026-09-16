import unittest
from cash_engine import simulate


def prices(start='2023-01-01',end='2023-01-12',value=10,symbols=('x',)):
    import datetime as dt
    dates=[]; day=dt.date.fromisoformat(start)
    while day<=dt.date.fromisoformat(end):
        dates.append(day.isoformat()); day+=dt.timedelta(days=1)
    return {s:{d:dict(open=value,close=value) for d in dates} for s in symbols}


def run(p,**kw):
    return simulate(p,kw.pop('events',[]),start=kw.pop('start','2023-01-02'),end=kw.pop('end','2023-01-12'),weekly=kw.pop('weekly',1000),fee=kw.pop('fee',0),cash_rate=kw.pop('cash_rate',0),rebalance=kw.pop('rebalance',False),limits={s:10 for s in p},**kw)


class CashChecks(unittest.TestCase):
    def test_flat_funding_is_not_profit(self):
        r=run(prices()); self.assertAlmostEqual(r['daily'][-1]['equity'],2000)
        self.assertTrue(all(abs(d['nav']-1)<1e-12 for d in r['daily']))
    def test_fees_lots_and_nonnegative_cash(self):
        r=run(prices(),fee=.01,weekly=1050)
        self.assertAlmostEqual(r['daily'][-1]['equity'],2080)
        self.assertEqual(sum(t['fee'] for t in r['trades']),20)
        self.assertTrue(all(t['shares']%100==0 for t in r['trades']))
        self.assertTrue(all(d['cash']>=0 for d in r['daily']))
    def test_dividend_receivable_not_spendable(self):
        p=prices()
        for d in p['x']:
            if d>='2023-01-04':p['x'][d]={'open':9,'close':9}
        e=[dict(symbol='x',type='cash_dividend',record_date='2023-01-03',ex_date='2023-01-04',pay_date='2023-01-06',cash_per_share=1,event_id='e')]
        r=run(p,events=e,end='2023-01-06')
        by={d['date']:d for d in r['daily']}
        self.assertEqual(by['2023-01-04']['receivable'],100)
        self.assertEqual(by['2023-01-04']['cash'],0)
        self.assertEqual(by['2023-01-06']['cash'],100)
        self.assertTrue(all(abs(d['equity']-1000)<1e-10 for d in r['daily']))
    def test_buy_on_ex_date_gets_no_old_dividend(self):
        p=prices()
        e=[dict(symbol='x',type='cash_dividend',record_date='2023-01-01',ex_date='2023-01-02',pay_date='2023-01-06',cash_per_share=1,event_id='e')]
        r=run(p,events=e,end='2023-01-06')
        self.assertEqual(sum(x['amount'] for x in r['events'] if x['kind']=='dividend_paid'),0)
    def test_split_conserves_wealth(self):
        p=prices()
        for d in p['x']:
            if d>='2023-01-04':p['x'][d]={'open':2,'close':2}
        r=run(p,events=[dict(symbol='x',type='split',ex_date='2023-01-04',ratio=5,event_id='s')],end='2023-01-06')
        self.assertEqual(r['daily'][-1]['units_x'],500)
        self.assertAlmostEqual(r['daily'][-1]['equity'],1000)
    def test_missing_day_is_not_relabelled(self):
        p=prices(); del p['x']['2023-01-02']
        r=run(p,end='2023-01-04'); self.assertEqual(r['trades'][0]['date'],'2023-01-03')
        self.assertEqual(r['daily'][0]['cash'],1000)
    def test_open_limit_blocks_trade(self):
        p=prices();p['x']['2023-01-02']={'open':11,'close':10}
        r=simulate(p,[],start='2023-01-02',end='2023-01-04',weekly=1000,fee=0,cash_rate=0,rebalance=False,limits={'x':.10})
        self.assertEqual(r['trades'][0]['date'],'2023-01-03')
    def test_quarterly_flat_assets_only_lose_fees(self):
        p=prices('2022-12-31','2023-04-10',symbols=('x','y'))
        r=run(p,end='2023-04-10',weekly=4100,fee=.001,rebalance=True)
        self.assertAlmostEqual(r['daily'][-1]['equity'],sum(f['amount'] for f in r['flows'])-sum(t['fee'] for t in r['trades']),places=7)
    def test_same_flows_across_arms(self):
        p=prices('2022-12-31','2023-04-10',symbols=('x','y'))
        a=run(p,end='2023-04-10',rebalance=True);b=run(p,end='2023-04-10');c=run({'x':p['x']},end='2023-04-10')
        self.assertEqual(a['flows'],b['flows']);self.assertEqual(a['flows'],c['flows'])
    def test_close_information_does_not_change_same_open_orders(self):
        p=prices('2022-12-31','2023-04-03',symbols=('x','y'))
        a=run(p,end='2023-04-03',weekly=4000,rebalance=True)
        p['x']['2023-04-01']['close']=100
        b=run(p,end='2023-04-03',weekly=4000,rebalance=True)
        self.assertEqual([t for t in a['trades'] if t['date']=='2023-04-01'],[t for t in b['trades'] if t['date']=='2023-04-01'])
    def test_cash_interest_not_assigned_to_receivable(self):
        p=prices(value=100);a=run(p,end='2023-01-08',cash_rate=.02)
        self.assertAlmostEqual(a['daily'][-1]['cash'],1000*(1.02)**(7/365),places=7)
    def test_record_date_missing_stops_for_held_asset(self):
        p=prices();del p['x']['2023-01-03']
        e=[dict(symbol='x',type='cash_dividend',record_date='2023-01-03',ex_date='2023-01-04',pay_date='2023-01-06',cash_per_share=1,event_id='e')]
        with self.assertRaises(ValueError):run(p,events=e)

if __name__=='__main__':unittest.main(verbosity=2)
