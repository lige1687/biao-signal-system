import importlib.util,pathlib
P=pathlib.Path(__file__).with_name('run.py');s=importlib.util.spec_from_file_location('mixed',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_fee_budget_lot():
    assert int(250000/(4.856*1.001)/100)*100==51400
def test_split_mark():
    u={'x':100};p={'x':6};m.apply_split_to_account('x',3,u,p);assert u['x']*p['x']==600
def test_blocks():
    assert m.blocked(None,'buy')=='missing_quote'
