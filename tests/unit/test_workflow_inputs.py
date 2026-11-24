"""Paired synthetic checks; no historical identity qualification is claimed."""
from copy import deepcopy
from datetime import date, timedelta
import pytest
from lei_signal.research.workflow_inputs import prepare_observations, inspect_prefix_invariance


def case(n=16):
    days = [(date(2026, 1, 5) + timedelta(days=i)).isoformat() for i in range(n)]
    payload = {'calendar': days, 'data_mode': 'synthetic', 'bars': [
        dict(asset='A', date=d, status='quoted', close=100+i, open=100+i,
             high=101+i, low=99+i, action_known=True, open_actionable=True)
        for i,d in enumerate(days)]}
    contract = {'universe': {'assets': ['A'], 'allow_partial': False},
        'feature': {'kind': 'sma_distance', 'lookback': 2, 'missing_policy': 'real_quote', 'warmup': 3},
        'question': {'sampling': 'daily'},
        'target': {'kind': 'forward_return', 'start_offset': 1, 'end_offset': 3,
                   'entry_field': 'close', 'unit': 'percentage_point'}}
    return payload,contract


def obs(result,i):
    return result['observations'][i]


def gap(p,i,status,known=True):
    p['bars'][i].update(status=status, close=None, open=None,high=None,low=None,
                        action_known=known,open_actionable=False)


def test_actual_prefix_and_future_change():
    p,c=case()
    original=prepare_observations(p,c)
    q=deepcopy(p)
    q['bars'][10]['close']=500
    q['bars'][10]['high']=501
    altered=prepare_observations(q,c)
    assert [r['features'] for r in original['observations'][:10]] == [r['features'] for r in altered['observations'][:10]]
    assert inspect_prefix_invariance(p,c)['passed']
    assert not obs(original,15)['eligible']
    assert obs(original,15)['label_reason']=='immature_label'


def test_unknown_gap_vs_confirmed_halt_and_recovery():
    p,c=case(); gap(p,5,'vendor_missing')
    bad=prepare_observations(p,c)
    assert obs(bad,6)['features']['added'] is None
    assert obs(bad,8)['features']['added'] is not None
    p['bars'][5]['status']='halt'
    good=prepare_observations(p,c)
    assert obs(good,6)['features']['added'] is not None
    c['feature'].update(missing_policy='segmented',warmup=5)
    restarted=prepare_observations(p,c)
    assert obs(restarted,9)['features']['added'] is None
    assert obs(restarted,10)['features']['added'] is not None


def test_endpoint_path_open_and_action_distinct():
    p,c=case(); gap(p,4,'vendor_missing',True)
    assert obs(prepare_observations(p,c),2)['y'] is not None
    c['target']['kind']='mae'
    assert obs(prepare_observations(p,c),2)['label_reason']=='path_vendor_missing'
    p['bars'][4]['status']='halt'
    assert obs(prepare_observations(p,c),2)['y'] is not None
    p['bars'][3]['open_actionable']=False
    c['target']['entry_field']='open'
    assert obs(prepare_observations(p,c),2)['label_reason']=='entry_open_not_actionable'
    c['target']['entry_field']='close'; p['bars'][4]['action_known']=False
    assert obs(prepare_observations(p,c),2)['label_reason']=='action_unknown'


def test_endpoint_halt_return_vs_traded_close_path():
    p,c=case(); gap(p,5,'halt')
    assert obs(prepare_observations(p,c),2)['label_reason']=='endpoint_halt'
    c['target']['kind']='max_drawdown'
    assert obs(prepare_observations(p,c),2)['y']==0


def test_full_pool_absence_retained_and_event_not_prefiltered():
    p,c=case(); c['universe']['assets'].append('B'); c['feature']['kind']='decline_event'
    result=prepare_observations(p,c)
    assert len(result['observations'])==32
    assert result['coverage']['per_asset']['B']['raw']==0
    assert result['coverage']['per_asset']['B']['observations']==16
    assert all(r['tested_condition'] is False for r in result['observations'] if r['asset']=='A' and r['features']['added'] is not None)
    assert result['coverage']['common_comparison'] is None


def test_unfinished_week_not_selected():
    p,c=case(4); c['question'].update(sampling='periodic',frequency='weekly')
    assert prepare_observations(p,c)['observations']==[]
    p,c=case(8); c['question'].update(sampling='periodic',frequency='weekly')
    assert [r['date'] for r in prepare_observations(p,c)['observations']]==[p['calendar'][6]]
    assert inspect_prefix_invariance(p,c)['passed']


@pytest.mark.parametrize('mutation', ['date','reverse','duplicate','offset','outside'])
def test_invalid_time_raises(mutation):
    p,c=case()
    if mutation=='date': p['calendar'][0]='2026-01-99'
    if mutation=='reverse': p['calendar'].reverse()
    if mutation=='duplicate': p['calendar'][1]=p['calendar'][0]
    if mutation=='offset': c['target']['start_offset']=0
    if mutation=='outside': p['bars'][0]['date']='2025-01-01'
    with pytest.raises(ValueError): prepare_observations(p,c)


def test_missing_not_listed_terminated_and_unknown_actions_remain_reasons():
    p,c=case()
    for i,status in enumerate(['not_listed','terminated','action_unknown'],3): gap(p,i,status,False)
    result=prepare_observations(p,c)
    assert all(obs(result,i)['features']['added'] is None for i in range(3,6))
    assert obs(result,2)['label_reason']=='entry_not_listed'


def test_wrapper():
    from lei_signal.research.input_preflight import inspect_workflow_input
    p,c=case()
    assert inspect_workflow_input(p,c)==prepare_observations(p,c)


@pytest.mark.parametrize('field', ['feature_available_at','period_end'])
def test_future_availability_bad_and_correct_pair(field):
    p,c=case(); p['bars'][3][field]=p['calendar'][4]
    with pytest.raises(ValueError,match='after observation'):
        prepare_observations(p,c)
    p['bars'][3][field]=p['calendar'][3]
    assert prepare_observations(p,c)['coverage']['observations']==16


def test_feature_after_decision_bad_and_correct_pair():
    p,c=case()
    p['bars'][3].update(feature_available_at=p['calendar'][3]+'T16:00:00+08:00',
                        decision_at=p['calendar'][3]+'T15:00:00+08:00')
    with pytest.raises(ValueError,match='after decision_at'):
        prepare_observations(p,c)
    p['bars'][3]['decision_at']=p['calendar'][3]+'T17:00:00+08:00'
    assert prepare_observations(p,c)['coverage']['observations']==16


def test_explicit_period_end_and_prefix_use_same_frozen_calendar():
    p,c=case(4); c['question'].update(sampling='periodic',frequency='weekly')
    assert not prepare_observations(p,c)['observations']
    p['completed_period_ends']=[p['calendar'][-1]]
    assert len(prepare_observations(p,c)['observations'])==1
    assert inspect_prefix_invariance(p,c)['passed']


def test_absent_gap_is_not_confirmed_halt():
    p,c=case(); del p['bars'][5]
    result=prepare_observations(p,c)
    assert obs(result,6)['features']['added'] is None
    assert obs(result,2)['label_reason']=='action_unknown'


def test_explicit_warmup_required_and_hand_calculation():
    p,c=case(); del c['feature']['warmup']
    with pytest.raises((KeyError, ValueError)):
        prepare_observations(p,c)
    c['feature']['warmup']=3
    r=obs(prepare_observations(p,c),2)
    assert r['features']['lag_return']==pytest.approx(2)
    assert r['features']['added']==pytest.approx(100*(102/101.5-1))
    assert r['y']==pytest.approx(100*(105/103-1))
    c['target'].update(kind='downside_event',unit='probability',threshold=5)
    assert obs(prepare_observations(p,c),2)['y']==0


def test_prefix_respects_original_decision_cutoff():
    p,c=case(); p['decision_at']=p['calendar'][8]+'T17:00:00+08:00'
    assert inspect_prefix_invariance(p,c)['passed']


def test_mixed_timezone_availability_has_explicit_time_error():
    p,c=case()
    p['bars'][3].update(feature_available_at=p['calendar'][3]+'T16:00:00+08:00',
                        decision_at=p['calendar'][3]+'T15:00:00')
    with pytest.raises(ValueError,match='timezone'):
        prepare_observations(p,c)


@pytest.mark.parametrize('value', [0,-1,float('nan'),float('inf')])
def test_corrupt_quoted_price_is_error_not_unknown(value):
    p,c=case(); p['bars'][4]['close']=value
    with pytest.raises(ValueError,match='positive finite'):
        prepare_observations(p,c)
    p['bars'][4]['close']=None
    assert obs(prepare_observations(p,c),4)['features']['added'] is None


def test_optional_ohlc_validation_without_endpoint_overrequirement():
    p,c=case(); p['bars'][4]['low']=p['bars'][4]['close']+1
    with pytest.raises(ValueError,match='OHLC'):
        prepare_observations(p,c)
    p['bars'][4]['low']=None; p['bars'][4]['high']=None
    assert obs(prepare_observations(p,c),2)['y'] is not None
    c['target'].update(kind='mae',path_field='low')
    assert obs(prepare_observations(p,c),2)['label_reason']=='path_low_missing'


def test_intraday_low_mae_and_unknown_high_low_sequence():
    p,c=case(); p['bars'][4]['low']=80
    c['target'].update(kind='mae',path_field='close')
    assert obs(prepare_observations(p,c),2)['y']==0
    c['target']['path_field']='low'
    assert obs(prepare_observations(p,c),2)['y']==pytest.approx(100*(1-80/103))
    p['bars'][4]['high']=None
    assert obs(prepare_observations(p,c),2)['label_reason']=='path_high_missing'
    c['target']['kind']='max_drawdown'
    with pytest.raises(ValueError,match='close'):
        prepare_observations(p,c)


def test_daily_close_unavailable_before_market_even_without_availability_claim():
    p,c=case()
    p['bars'][3]['decision_at']=p['calendar'][3]+'T09:00:00+08:00'
    with pytest.raises(ValueError,match='daily close'):
        prepare_observations(p,c)
    p['bars'][3]['feature_available_at']=p['calendar'][3]
    with pytest.raises(ValueError,match='daily close'):
        prepare_observations(p,c)
    p['bars'][3].pop('feature_available_at')
    p['bars'][3]['decision_at']=p['calendar'][3]+'T16:00:00+08:00'
    assert prepare_observations(p,c)['coverage']['observations']==16


def test_low_before_close_entry_is_not_a_future_adverse_move():
    p,c=case(); p['bars'][3]['low']=80
    c['target'].update(kind='mae',path_field='low',entry_field='close')
    assert obs(prepare_observations(p,c),2)['y']==0
    c['target']['entry_field']='open'
    assert obs(prepare_observations(p,c),2)['y']==pytest.approx(100*(1-80/103))
