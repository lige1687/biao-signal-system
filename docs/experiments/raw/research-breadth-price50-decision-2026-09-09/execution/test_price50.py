import importlib.util
from decimal import Decimal
from pathlib import Path
import pandas as pd

P=Path(__file__).with_name('run_price50.py')
spec=importlib.util.spec_from_file_location('price50_runner',P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_exactly_50_valid_and_equality_is_cash():
    idx=pd.date_range('2020-01-01',periods=51)
    s=pd.Series([1.0]*49+[1.0,1.1],index=idx)
    target,sma=m.price50_targets(s)
    assert target.iloc[:49].isna().all()
    assert target.iloc[49]==0.0  # close equals SMA
    assert target.iloc[50]==1.0


def test_missing_quote_does_not_count_toward_50():
    idx=pd.date_range('2020-01-01',periods=51)
    s=pd.Series([1.0]*51,index=idx); s.iloc[20]=float('nan')
    target,_=m.price50_targets(s)
    assert pd.isna(target.iloc[49])
    assert target.iloc[50]==0.0


def test_dividend_connection_avoids_false_price_drop():
    idx=pd.to_datetime(['2020-01-01','2020-01-02'])
    bars=pd.DataFrame({'close':[10.0,9.0]},index=idx)
    actions=[{'symbol':'sh510300','type':'cash_dividend','effective_date':'2020-01-02','cash':'1'}]
    out=m.continuous_close(bars,actions,'sh510300')
    assert abs(out.iloc[1]-10.0)<1e-12


def test_restriction_blocks_open_and_new_state_replaces_pending():
    day=pd.Timestamp('2021-02-08')
    bar=pd.Series({'open':1.0})
    restrictions=[{'symbol':'sz159915','date':'2021-02-08','open_buy_allowed':False,'open_sell_allowed':False,'reason':'suspension'}]
    assert m.block_reason('159915',day,'buy',bar,Decimal('1'),[],restrictions,[])=='suspension'
    state,pending=m.state_change_order(None,1.0,day-pd.Timedelta(days=1))
    assert pending['target']==1.0
    state,replacement=m.state_change_order(state,0.0,day)
    assert replacement['target']==0.0 and replacement['signal_date']==day


def test_dividend_cash_does_not_create_price_state_change():
    idx=pd.date_range('2020-01-01',periods=51)
    s=pd.Series([1.0]*51,index=idx)
    target,_=m.price50_targets(s)
    state,order=m.state_change_order(None,float(target.iloc[49]),idx[49])
    assert order is not None
    # Paying cash does not enter either price50_targets or state_change_order.
    state,next_order=m.state_change_order(state,float(target.iloc[50]),idx[50])
    assert next_order is None
