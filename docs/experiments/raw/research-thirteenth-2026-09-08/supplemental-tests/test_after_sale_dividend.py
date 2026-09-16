"""Regression: payment after sale must remain in terminal cash, not only accrued P&L."""
import importlib.util,json
from pathlib import Path
import pandas as pd

def test_dividend_paid_on_later_day_after_position_closed(tmp_path):
    p=Path(__file__).resolve().parents[1]/'execution/run_accounts.py'
    spec=importlib.util.spec_from_file_location('phase13_supplement_runner',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.BASE=tmp_path;cfg=tmp_path/'A20E';cfg.mkdir()
    base=dict(config_id='A20E',position_id='p',candidate_id='c',symbol='x',entry_date='2015-01-05',initial_stop=9,net_pnl=0)
    (cfg/'roundtrips.json').write_text(json.dumps([base]))
    pd.DataFrame([dict(date='2015-01-05',position_id='p',side='buy',shares=100,price=10,notional=1000,fee=1)]).to_csv(cfg/'trades.csv',index=False)
    prices={'x':{d:dict(open=p,close=p) for d,p in [('2015-01-04',10),('2015-01-05',10),('2015-01-06',10),('2015-01-07',8),('2015-01-08',8),('2015-01-09',8)]}}
    actions=[dict(symbol='x',event_id='div',type='cash_dividend',record_date='2015-01-06',ex_date='2015-01-07',pay_date='2015-01-09',cash_per_share=1)]
    settings=dict(blocked_dates={'x':[]},limits={'x':.5},limit_changes={'x':[]})
    result=m.fixed_position_path(base,prices,actions,{'x':{}},settings,'S')
    assert result['exit_date']=='2015-01-08'
    assert result['dividends']==100
    assert any(e['kind']=='dividend_paid' and e['date']=='2015-01-09' and e['amount']==100 for e in result['events'])
    assert abs(result['terminal_value_from_entry_cash']-(-101.8))<1e-10
    assert abs(result['net_pnl']-result['terminal_value_from_entry_cash'])<1e-10
