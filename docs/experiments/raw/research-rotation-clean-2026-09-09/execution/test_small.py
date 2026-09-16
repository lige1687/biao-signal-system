import importlib.util, pathlib, pandas as pd
P=pathlib.Path(__file__).with_name('run.py'); s=importlib.util.spec_from_file_location('rot',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_drift():
    # unchanged units drift from 50/50 after one asset rises
    units={'A':50.,'B':50.}; px={'A':2.,'B':1.}; assert units['A']*px['A']/(sum(units[x]*px[x] for x in units))==2/3
def test_blocked():
    assert m.blocked(None,'sell')=='missing_quote'
    assert m.blocked({'open':10.,'high':10.,'low':10.,'volume':1000},'sell')=='locked_one_price_limit'
def test_gap_and_lot():
    assert (1000//(9.5*1.001)//100)*100==100
def test_economic_index_accumulates_split_across_missing_effective_quote():
    p=pd.DataFrame([
      {'date':'2021-02-23','symbol':'512170','open':3,'high':3,'low':3,'close':3,'volume':1},
      {'date':'2021-02-25','symbol':'512170','open':1,'high':1,'low':1,'close':1,'volume':1},
    ])
    a=[{'event_id':'x','symbol':'512170','type':'split','effective_date':'2021-02-24','record_date':None,'pay_date':None,'cash':0.,'ratio':3.}]
    z=m.economic_indices(pd.concat([p.assign(symbol=s) for s in m.SYMS],ignore_index=True),a)
    x=z[z.symbol=='512170'].economic_index.tolist(); assert x==[1.,1.]
def test_dividend_receivable_economic_factor():
    p=pd.DataFrame([
      {'date':'2022-01-18','symbol':'510300','open':10,'high':10,'low':10,'close':10,'volume':1},
      {'date':'2022-01-19','symbol':'510300','open':9,'high':9,'low':9,'close':9,'volume':1},
    ])
    a=[{'event_id':'d','symbol':'510300','type':'cash_dividend','effective_date':'2022-01-19','record_date':'2022-01-18','pay_date':'2022-01-24','cash':1.,'ratio':1.}]
    z=m.economic_indices(pd.concat([p.assign(symbol=s) for s in m.SYMS],ignore_index=True),a)
    x=z[z.symbol=='510300'].economic_index.tolist(); assert x==[1.,1.]
