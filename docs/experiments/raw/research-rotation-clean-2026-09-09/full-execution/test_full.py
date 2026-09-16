import importlib.util, pathlib
P=pathlib.Path(__file__).with_name('run.py'); s=importlib.util.spec_from_file_location('fullrot',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

def test_split_without_quote_preserves_marked_value():
    units={'512890':1000.}; marks={'512890':4.}
    before=units['512890']*marks['512890']
    m.apply_split_to_account('512890',2.,units,marks)
    assert units['512890']==2000 and marks['512890']==2.
    assert units['512890']*marks['512890']==before

def test_missing_and_halt_block_fills():
    assert m.blocked(None,'sell')=='missing_quote'
    bar={'open':1.,'high':1.1,'low':.9,'volume':100}
    assert m.blocked(bar,'buy',{'blocks_open_buy':True})=='known_open_restriction'

def test_fee_inclusive_lot_floor():
    target=250000.; price=4.856; fee=.001
    qty=int(target/(price*(1+fee))/100)*100
    assert qty==51400
