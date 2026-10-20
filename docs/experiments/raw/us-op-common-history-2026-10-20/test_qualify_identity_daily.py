import importlib.util
from pathlib import Path
P=Path(__file__).with_name('qualify_identity_daily.py')
spec=importlib.util.spec_from_file_location('identity_daily',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def run():
    assert m.norm('BRK.B')==m.norm('BRK-B')
    assert ('STI','legacy_month_suffix_candidate') in m.candidate_aliases('STI-201912')
    assert m.temporal_eligible({'date_added':'2010-01-01*','date_removed':'2020-01-01*','created_at':'2012-01-01'},'2015-01-01')
    assert not m.temporal_eligible({'date_added':'2010-01-01','date_removed':'2015-01-01','created_at':'2010-01-01'},'2015-01-01')
    assert not m.temporal_eligible({'date_added':'2010-01-01','date_removed':'','created_at':'2016-01-01'},'2015-12-31')
    assert m.rename_reachable('A',[('A','B'),('B','C')])=={'B','C'}
    assert m.status_for({'1'},{'exact','rename'})=='exact'
    assert m.status_for({'1','2'},{'exact'})=='ambiguous'
    assert m.status_for({'1'},{'rename'})=='rename'
    assert m.status_for(set(),set())=='no_candidate'
    print('PASS: 9 synthetic assertions')
if __name__=='__main__': run()
