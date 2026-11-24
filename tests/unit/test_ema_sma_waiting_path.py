from datetime import date, timedelta
from fractions import Fraction
import copy
import pytest
from lei_signal.research import ema_sma_waiting_path as m


def fixture(prices):
    calendar = [(date(2020, 1, 1)+timedelta(days=i)).isoformat() for i in range(len(prices))]
    bars = [dict(asset='X', date=d, status='quoted', action_known=True, open=p, high=p, low=p, close=p, exact_nominal_close=str(p)) for d,p in zip(calendar, prices)]
    return {'data_mode':'synthetic','calendar':calendar,'bars':bars}, {'data':{'mode':'synthetic'},'feature':{'kind':m.KIND,'definition_ref':m.DEFINITION_REF},'universe':{'assets':['X']},'question':{'period':[calendar[0],calendar[-1]]}}


def test_exact_equality_tiny_difference_and_prefix():
    p,c = fixture(['100']*260 + ['100.000000000000000000000000000001'])
    rows=m.prepare_waiting_observations(p,c)['observations']
    assert rows[-2]['E'] is False and rows[-2]['S'] is False
    assert rows[-1]['E'] is True and rows[-1]['S'] is True
    short=copy.deepcopy(p);short['calendar']=short['calendar'][:-1];short['bars']=short['bars'][:-1]
    assert m.prepare_waiting_observations(short,c)['observations']==rows[:-1]
    assert all(r['label'] is None and r['label_end'] is None for r in rows)


def test_missing_resets_and_left_boundary_is_not_start():
    p,c=fixture([100]*252+[110]*260)
    p['bars'][253].update(status='vendor_missing',open=None,high=None,low=None,close=None)
    rows=m.prepare_waiting_observations(p,c)['observations']
    assert rows[251]['prev_E'] is None and not rows[251]['is_t0']
    assert rows[253]['E'] is None
    assert not rows[504]['ready_252']
    assert rows[505]['ready_252'] and rows[505]['prev_E'] is None
    assert not rows[505]['is_t0']


def test_real_gate_precedes_source_read():
    p,c=fixture([100]*280);p['data_mode']='real';c['data']['mode']='real'
    with pytest.raises(ValueError,match='authorization'):m.evaluate_waiting_paths(p,c)


def test_cash_action_changes_equal_nominal_direction():
    p,c=fixture([100]*260)
    p['economic_actions']=[dict(symbol='X',close_effective_date=p['calendar'][-1],event_id='cash',type='cash_dividend',cash='1')]
    r=m.prepare_waiting_observations(p,c)['observations'][-1]
    assert r['E'] is True and r['S'] is True


def path_fixture(monkeypatch, confirm=None, failure=None, missing=None, length=280):
    p,c=fixture([100]*length)
    i=252
    states=[dict(E=False,S=False,ready_252=True,continuous_close=252) for _ in range(length)]
    for j in range(i,length):states[j]['E']=True
    if confirm is not None:states[i+confirm]['S']=True
    if failure is not None:states[i+failure]['E']=False
    if missing is not None:states[i+missing]['E']=None;states[i+missing]['S']=None
    closes=[Fraction(100+j,100) for j in range(length)]
    if missing is not None:closes[i+missing]=None
    monkeypatch.setattr(m,'_inputs',lambda *args: {'X':(closes,states)})
    return p,c,i


@pytest.mark.parametrize('confirm,failure,missing,status',[(3,None,None,'confirmed'),(21,None,None,'too_late'),(None,3,None,'ema_failed'),(None,None,3,'missing'),(None,None,None,'no_confirmation'),(3,3,None,'ema_failed')])
def test_window_states_and_failure_priority(monkeypatch,confirm,failure,missing,status):
    p,c,i=path_fixture(monkeypatch,confirm,failure,missing)
    result=m.evaluate_waiting_paths(p,c)
    r=next(r for r in result['event_ledger'] if r['date']==p['calendar'][i])
    assert r['status']==status
    assert r['early_path']['intervals']==20 if missing is None else r['early_path'] is None
    if status=='confirmed':
        assert r['paired'] and r['waiting_path']['intervals']==17
        assert r['terminal_date']==p['calendar'][i+21]
        assert r['terminal_difference']==pytest.approx(r['waiting_path']['terminal_return']-r['early_path']['terminal_return'])
    else:
        assert r['waiting_cost'] is None and r['terminal_difference'] is None


def test_confirmation_day20_observation_at_h_has_zero_duration(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=20)
    r=m.evaluate_waiting_paths(p,c)['event_ledger'][0]
    assert r['waiting_entry_date']==r['terminal_date']
    assert r['waiting_path']['intervals']==0 and r['waiting_path']['terminal_return']==0
    assert r['paired']


def test_immature_start_is_retained(monkeypatch):
    p,c,i=path_fixture(monkeypatch,length=260)
    r=m.evaluate_waiting_paths(p,c)['event_ledger'][0]
    assert r['status']=='immature' and r['early_path'] is None and not r['paired']


def test_integrated_prefix_start_and_paired_common_terminal():
    p,c=fixture([100]*252+[110]*20+[90]*10+[100]*40)
    rows=m.prepare_waiting_observations(p,c)['observations']
    starts=[r for r in rows if r['is_t0']]
    assert len(starts)==1 and starts[0]['date']==p['calendar'][282]
    assert starts[0]['prev_E'] is False and starts[0]['E'] is True and starts[0]['S'] is False
    cut=copy.deepcopy(p);cut['calendar']=cut['calendar'][:283];cut['bars']=cut['bars'][:283]
    assert m.prepare_waiting_observations(cut,c)['observations']==rows[:283]
    r=m.evaluate_waiting_paths(p,c)['event_ledger'][0]
    assert r['status']=='confirmed' and r['early_path']['intervals']==20
    assert r['waiting_entry_date']<=r['terminal_date'] and r['paired']
    assert r['waiting_cost']==0 and r['terminal_difference']==0


def test_confirmation_then_missing_retains_confirm_but_null_prices(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=3,missing=10)
    r=m.evaluate_waiting_paths(p,c)['event_ledger'][0]
    assert r['status']=='confirmed' and r['confirmation_date'] is not None
    assert not r['paired'] and r['waiting_cost'] is None and r['terminal_difference'] is None
    assert r['outcome_reason']=='missing_price_path'


def test_untrusted_observations_rejected(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=3)
    observations=m.prepare_waiting_observations(p,c)['observations']
    observations[0]['is_t0']=True
    with pytest.raises(ValueError,match='differ'):m.evaluate_waiting_paths(p,c,observations)


def test_independent_all_prefix_formula():
    p,c=fixture([100]*252+[110]*20+[90]*10+[100]*40)
    p['bars'][150].update(status='vendor_missing',open=None,high=None,low=None,close=None)
    check=m.inspect_waiting_prefix_invariance(p,c)
    assert check['ok'] and check['asset_prefixes_checked']==322
    assert check['compared_period_rows']==322 and check['future_outcomes']==0


def test_changing_future_cannot_rewrite_earlier_start():
    p,c=fixture([100]*252+[110]*20+[90]*10+[100]*40)
    original=m.prepare_waiting_observations(p,c)['observations']
    changed=copy.deepcopy(p)
    for row in changed['bars'][283:]:
        row.update(open=1000,high=1000,low=1000,close=1000,exact_nominal_close='1000')
    altered=m.prepare_waiting_observations(changed,c)['observations']
    assert original[:283]==altered[:283]
    short=copy.deepcopy(changed);short['calendar']=short['calendar'][:283];short['bars']=short['bars'][:283]
    assert m.prepare_waiting_observations(short,c)['observations']==original[:283]


def test_phase_numbers_exclude_cross_year_but_keep_all_starts(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=3)
    start=date(2024,12,20)-timedelta(days=i)
    p['calendar']=[(start+timedelta(days=j)).isoformat() for j in range(len(p['calendar']))]
    for row,d in zip(p['bars'],p['calendar']):row['date']=d
    c['question']['period']=[p['calendar'][0],p['calendar'][-1]]
    result=m.evaluate_waiting_paths(p,c)
    full=next(r for r in result['performance'] if r['group']=='all')
    phase=next(r for r in result['period_comparisons'] if r['group']=='2022-2024')
    assert full['starts']==1 and full['paired_rows']==1
    assert phase['starts']==1 and phase['cross_boundary_outcomes']==1 and phase['numeric_rows']==0
    assert phase['paired_rows']==0 and phase['equal_asset_means']['waiting_cost'] is None
    assert phase['price_path_means']['early_path']['rows']==0
    assert len(result['event_ledger'])==1


def test_support_lists_and_missing_assets_are_explicit(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=3)
    c['universe']['assets']=['X','Y']
    result=m.evaluate_waiting_paths(p,c)
    group=result['coverage']
    assert group['supported_assets']==['X'] and group['missing_assets']==['Y']
    assert group['price_path_means']['waiting_path']['supported_assets']==['X']
    assert group['price_path_means']['waiting_path']['missing_assets']==['Y']
    empty=next(r for r in result['performance'] if r['group']=='Y')
    assert empty['supported_assets']==[] and empty['missing_assets']==['Y']


def test_real_label_permission_without_effect_authorization_is_blocked():
    p,c=fixture([100]*280);p['data_mode']='real';c['data']['mode']='real'
    c['permissions']={'real_labels':True}
    with pytest.raises(ValueError,match='effect_authorized'):m.evaluate_waiting_paths(p,c)


def test_confirmation_with_immature_terminal_is_separate(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=3,length=260)
    result=m.evaluate_waiting_paths(p,c)
    r=result['event_ledger'][0]
    assert r['status']=='confirmed' and not r['window_mature'] and not r['price_outcome_mature']
    assert result['coverage']['confirmed']==1 and result['coverage']['confirmed_mature_price_rows']==0
    assert result['coverage']['immature_outcomes']==1


def test_phase_contained_numbers_are_retained(monkeypatch):
    p,c,i=path_fixture(monkeypatch,confirm=3)
    start=date(2025,3,1)-timedelta(days=i)
    p['calendar']=[(start+timedelta(days=j)).isoformat() for j in range(len(p['calendar']))]
    for row,d in zip(p['bars'],p['calendar']):row['date']=d
    c['question']['period']=[p['calendar'][0],p['calendar'][-1]]
    result=m.evaluate_waiting_paths(p,c)
    phase=next(r for r in result['period_comparisons'] if r['group']=='2025')
    assert phase['starts']==1 and phase['numeric_rows']==1 and phase['cross_boundary_outcomes']==0
    assert phase['paired_rows']==1 and phase['equal_asset_means']['waiting_cost'] is not None


def test_event_and_equal_asset_means_have_distinct_weights():
    def row(asset,value):
        path={k:value for k in ('terminal_return','lowest_close_decline','highest_close_rise','peak_to_trough_decline','intervals')}
        return {'asset':asset,'status':'confirmed','confirmation_date':'2025-01-01','paired':True,
                'waiting_cost':value,'terminal_difference':value,'early_path':path,
                'before_waiting_path':path,'waiting_path':path,'outcome_reason':None}
    group=m._group([row('X',0),row('X',0),row('Y',12)],['X','Y','Z'])
    assert group['equal_asset_means']['waiting_cost']==6
    assert group['raw_event_means']['waiting_cost']==4
    assert group['price_path_means']['early_path']['values']['terminal_return']==6
    assert group['price_path_means']['early_path']['raw_event_means']['terminal_return']==4
    assert group['expected_assets']==['X','Y','Z'] and group['missing_assets']==['Z']
