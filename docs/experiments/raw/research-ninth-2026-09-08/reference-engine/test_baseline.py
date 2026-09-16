import unittest
from engine import simulate

def bar(open=1., close=None):
    close=open if close is None else close
    return dict(open=open,close=close,high=max(open,close)+.02,low=min(open,close)-.02,volume=1000)

def data():
    return {'X':{'2023-12-29':bar(),**{f'2024-01-{d:02d}':bar() for d in [1,2,3,4,5,8,9,10]}}}

def candidate(cid='a',date='2024-01-01',**kw):
    return dict(symbol='X',signal_date=date,candidate_id=cid,stop=.9,target=1.6,upper=1.,variant='breakout',**kw)

def observations(prices):
    return {s:{d:dict(ema20=.5,cost20=.5,ema20_slope=.01,sma20_slope=.01,sma20=.5,sma60=.4) for d in rows} for s,rows in prices.items()}

def run(prices=None,cs=None,actions=None,config='P0',**kw):
    prices=prices or data()
    return simulate(prices,actions or [],[candidate()] if cs is None else cs,kw.pop('obs',observations(prices)),start='2024-01-01',end=kw.pop('end','2024-01-10'),config_id=config,limits={s:1. for s in prices},**kw)

class AccountTests(unittest.TestCase):
    def test_plain_buy_and_deposits_not_return(self):
        r=run();self.assertEqual(len(r['trades']),1);self.assertEqual(r['trades'][0]['shares'],200)
        end=r['daily'][-1];self.assertAlmostEqual(end['equity'],499.8);self.assertAlmostEqual(end['total_funding'],500)
        self.assertAlmostEqual(end['nav'],.9992)

    def test_gap_rr_rejected_once(self):
        p=data();p['X']['2024-01-02']=bar(1.2);r=run(p)
        self.assertEqual(len(r['orders']),1);self.assertEqual(r['orders'][0]['reason'],'open_rr_below3');self.assertEqual(r['trades'],[])

    def test_missing_target(self):
        c=candidate();c['target']=None;r=run(cs=[c]);self.assertEqual(len(r['orders']),1)
        self.assertEqual(r['orders'][0]['reason'],'missing_or_invalid_target');self.assertEqual(r['trades'],[])

    def test_signal_rejection_not_rescued(self):
        r=run(cs=[candidate(signal_accepted=False,signal_reject_reason='signal_rr_below3')]);self.assertEqual(len(r['orders']),1)
        self.assertEqual(r['orders'][0]['reason'],'signal_rr_below3');self.assertEqual(r['trades'],[])

    def test_holding_duplicate_and_same_day_duplicate(self):
        r=run(cs=[candidate('a'),candidate('b'),candidate('c','2024-01-02')]);self.assertEqual(len(r['orders']),3)
        self.assertEqual(len(r['trades']),1);self.assertEqual(sum(o['status']=='rejected' for o in r['orders']),2)

    def test_tplus_and_exit_close_not_consumed(self):
        p=data();p['X']['2024-01-02']=bar(1.,.8);p['X']['2024-01-03']=bar(.75,1.4);r=run(p)
        self.assertEqual(len(r['trades']),2);self.assertEqual(r['trades'][1]['date'],'2024-01-03');self.assertEqual(r['trades'][1]['price'],.75)
        self.assertAlmostEqual(r['roundtrips'][0]['net_pnl'],-50.35)
        self.assertEqual(r['roundtrips'][0]['valuation_date'],'2024-01-03')

    def test_sell_deferred_until_available(self):
        p=data();p['X']['2024-01-02']=bar(1.,.8);del p['X']['2024-01-03'];r=run(p,blocked_dates={'X':['2024-01-04']})
        self.assertEqual(len(r['trades']),2);self.assertEqual(r['trades'][1]['date'],'2024-01-05')
        sell=[o for o in r['orders'] if o['side']=='sell'][0];self.assertGreaterEqual(len(sell['attempts']),2)

    def test_buy_missing_union_session_expires(self):
        p=data();del p['X']['2024-01-02'];p['Y']={'2023-12-29':bar(),'2024-01-02':bar()};r=run(p)
        self.assertEqual(len(r['orders']),1);self.assertEqual(r['orders'][0]['attempts'][0]['date'],'2024-01-02');self.assertEqual(r['trades'],[])

    def test_dividend_after_sale_receivable_then_holiday_payment(self):
        p=data();p['X']['2024-01-02']=bar(1.,.8)
        act=dict(event_id='div',symbol='X',type='cash_dividend',announcement_date='2023-12-20',record_date='2024-01-02',ex_date='2024-01-04',pay_date='2024-01-06',cash_per_share=.1)
        r=run(p,actions=[act]);self.assertEqual(len(r['trades']),2);days={d['date']:d for d in r['daily']}
        self.assertAlmostEqual(days['2024-01-04']['receivable'],20);self.assertAlmostEqual(days['2024-01-06']['receivable'],0)
        self.assertAlmostEqual(days['2024-01-06']['cash']-days['2024-01-05']['cash'],20)
        self.assertAlmostEqual(r['roundtrips'][0]['dividend_accrued'],20);self.assertAlmostEqual(r['roundtrips'][0]['dividend_paid'],20)

    def test_split_without_quote_rebases_quantity_and_levels(self):
        p=data();del p['X']['2024-01-03']
        for d in p['X']:
            if d>='2024-01-04':p['X'][d]=bar(.2)
        act=dict(event_id='split',symbol='X',type='split',announcement_date='2023-12-20',ex_date='2024-01-03',ratio=5)
        obs=observations(p)
        for d in obs['X']:
            if d>='2024-01-03':obs['X'][d].update(ema20=.1,cost20=.1,sma20=.1,sma60=.08)
        r=run(p,actions=[act],obs=obs);self.assertEqual(len(r['trades']),1);days={d['date']:d for d in r['daily']}
        self.assertEqual(days['2024-01-03']['units_X'],1000);self.assertAlmostEqual(days['2024-01-03']['equity'],days['2024-01-02']['equity'])
        self.assertAlmostEqual(r['roundtrips'][0]['stop'],.18)

    def test_tail_missing_not_liquidated(self):
        p=data();p['X']['2024-01-10']={k:None for k in ['open','high','low','close','volume']};r=run(p)
        self.assertEqual(len(r['trades']),1);self.assertFalse(r['roundtrips'][0]['closed']);self.assertIn('X',r['daily'][-1]['stale_symbols'])

    def test_holiday_deposit_and_insufficient_lot(self):
        p=data();del p['X']['2024-01-01'];r=run(p,cs=[],config='P6',weekly_per_symbol=50)
        self.assertEqual(len(r['daily']),10);self.assertEqual(r['daily'][0]['cash'],50);self.assertEqual(r['trades'],[])

    def test_p7_risk_size(self):
        r=run(config='P7',weekly_per_symbol=2500);self.assertEqual(len(r['trades']),1);self.assertEqual(r['trades'][0]['shares'],200)
        self.assertAlmostEqual(r['trades'][0]['risk_budget'],25)

    def test_structure_priority_and_no_sell_day_reentry(self):
        p=data();p['X']['2024-01-02']=bar(1.,.8);obs=observations(p);obs['X']['2024-01-02'].update(ema20=1.,cost20=1.)
        r=run(p,cs=[candidate('a'),candidate('b','2024-01-02')],obs=obs)
        self.assertEqual(len(r['trades']),2);sells=[o for o in r['orders'] if o['side']=='sell'];self.assertEqual(len(sells),1);self.assertEqual(sells[0]['reason'],'structure_stop')

    def test_dividend_rebases_pending_buy_proportionally(self):
        p=data();p['X']['2024-01-02']=bar(.9)
        for d in p['X']:
            if d>'2024-01-02':p['X'][d]=bar(.9)
        act=dict(event_id='d',symbol='X',type='cash_dividend',announcement_date='2023-12-20',record_date='2024-01-01',ex_date='2024-01-02',pay_date='2024-01-04',cash_per_share=.1)
        r=run(p,actions=[act]);self.assertEqual(len(r['trades']),1);self.assertAlmostEqual(r['roundtrips'][0]['stop'],.81)

    def test_b3_uses_price_below_sma_and_cost_even_positive_slopes(self):
        p=data();p['X']['2024-01-02']=bar(1.,.95);obs=observations(p)
        obs['X']['2024-01-02'].update(sma20=1.1,cost20=1.1,ema20_slope=.1,sma20_slope=.1)
        r=run(p,config='P4',obs=obs);self.assertEqual(len(r['trades']),2)
        self.assertEqual(r['trades'][1]['reason'],'b_breakout_two_actions')

    def test_b3_negative_slopes_alone_do_not_exit(self):
        p=data();p['X']['2024-01-02']=bar(1.,.95);obs=observations(p)
        obs['X']['2024-01-02'].update(sma20=.8,cost20=.8,ema20_slope=-.1,sma20_slope=-.1)
        r=run(p,config='P4',obs=obs);self.assertEqual(len(r['trades']),1)

    def test_old_dividend_does_not_transfer_to_new_position(self):
        p=data();p['X']['2024-01-02']=bar(1.,.8)
        for d in p['X']:
            if d>='2024-01-04':p['X'][d]=bar(.9)
        act=dict(event_id='div',symbol='X',type='cash_dividend',announcement_date='2023-12-20',record_date='2024-01-02',ex_date='2024-01-04',pay_date='2024-01-06',cash_per_share=.1)
        r=run(p,actions=[act],cs=[candidate('old'),candidate('new','2024-01-03')])
        self.assertEqual(len(r['roundtrips']),2);old,new=r['roundtrips']
        self.assertEqual(old['dividend_paid'],20);self.assertEqual(old['dividend_accrued'],20)
        self.assertEqual(new['dividend_paid'],0);self.assertEqual(new['dividend_accrued'],0)
        self.assertAlmostEqual(old['net_pnl'],19.6);self.assertEqual(new['entry_date'],'2024-01-04')

    def test_dividend_exday_wealth_conservation(self):
        p=data()
        for d in p['X']:
            if d>='2024-01-04':p['X'][d]=bar(.9)
        act=dict(event_id='div',symbol='X',type='cash_dividend',announcement_date='2023-12-20',record_date='2024-01-02',ex_date='2024-01-04',pay_date='2024-01-06',cash_per_share=.1)
        r=run(p,actions=[act]);days={x['date']:x for x in r['daily']}
        self.assertAlmostEqual(days['2024-01-03']['equity'],days['2024-01-04']['equity'])
        self.assertAlmostEqual(days['2024-01-04']['equity'],days['2024-01-06']['equity'])
        self.assertAlmostEqual(r['roundtrips'][0]['net_pnl'],-.2)

    def test_p7_current_monday_deposit_not_previous_risk_wealth(self):
        r=run(config='P7',weekly_per_symbol=2500,cs=[candidate(date='2024-01-05')]);self.assertEqual(len(r['trades']),1)
        t=r['trades'][0];self.assertEqual(t['date'],'2024-01-08');self.assertEqual(t['previous_product_equity'],2500);self.assertEqual(t['risk_budget'],25);self.assertEqual(t['shares'],200)

    def test_gap_below_stop_rejected_and_no_new_hard_open_exit(self):
        p=data();p['X']['2024-01-02']=bar(.8);r=run(p)
        self.assertEqual(r['trades'],[]);self.assertEqual(r['orders'][0]['reason'],'nonpositive_open_risk')
        p=data();p['X']['2024-01-03']=bar(.8,1.);r=run(p)
        self.assertEqual(len(r['trades']),1)

    def test_no_cash_borrowed_between_products(self):
        p=data();p['Y']={d:bar(.1) for d in p['X']};r=run(p,weekly_per_symbol=100)
        self.assertEqual(r['trades'],[]);self.assertEqual(r['orders'][0]['reason'],'insufficient_cash_or_risk_lot')

    def test_real_candidate_metadata_cannot_override_account_order_id(self):
        c=candidate(signal_ref=1.,signal_rr=6.,signal_accepted=True,signal_reject_reason=None,
            config_id='P0',known_at='2024-01-01',basis_as_of='2024-01-01',discipline_scope='research_proxy',
            full_B_qualified=False,kind='donchian60',opportunity_key='X:2024-01-01',rule_version='2.1.0',
            structure_id='s',target_confirmed_at='2023-12-29',target_source='confirmed_high',target_source_date='2023-12-20',
            seedmeta={'source':'synthetic interface check'},order_id='upstream-identity')
        r=run(cs=[c]);self.assertEqual(len(r['trades']),1);o=r['orders'][0]
        self.assertEqual(o['order_id'],'P0-O1');self.assertEqual(o['candidate_id'],'a')
        self.assertEqual(o['candidate_metadata']['order_id'],'upstream-identity')
        self.assertEqual(o['seedmeta'],c['seedmeta']);self.assertEqual(c['order_id'],'upstream-identity')

if __name__=='__main__':unittest.main(verbosity=2)
