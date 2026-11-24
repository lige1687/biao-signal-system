import pytest
from lei_signal.research.hourly_coverage_expansion import adjusted_daily, parse_split_source, qualify_stock_hours


def test_split_uses_reported_state_and_ignores_future():
    text = 'var sh512800hfq={"total":3,"data":[{"d":"2027-01-01","f":"1","s":"4","u":"0"},{"d":"2025-07-07","f":"1","s":"2","u":"0"},{"d":"1900-01-01","f":"1","s":"1","u":"0"}]} /* ignored comment */'
    rows = parse_split_source(text, 'sh512800', '2026-06-30')
    assert [r['backAdjustFactor'] for r in rows] == ['1', '2']
    with pytest.raises(ValueError):
        parse_split_source(text, 'sh512170', '2026-06-30')
    with pytest.raises(ValueError):
        parse_split_source(text.replace('"u":"0"', '"u":"1"'), 'sh512800', '2026-06-30')


def raw():
    return {'date': '2025-01-02', 'code': 'sh.600000', 'open': '10', 'high': '12', 'low': '9', 'close': '11', 'volume': '100', 'tradestatus': '1', 'adjustflag': '3'}


def test_unknown_factor_not_one_and_actual_flag_required():
    r = raw()
    assert adjusted_daily([r], [], [r['date']], code=r['code'])[0]['reason'] == 'factor_effective_date_unknown'
    factors = [{'dividOperateDate': '2025-01-03', 'backAdjustFactor': '2'}]
    assert not adjusted_daily([r], factors, [r['date']], code=r['code'])[0]['qualified']
    factors[0]['dividOperateDate'] = '2025-01-01'
    assert adjusted_daily([r], factors, [r['date']], code=r['code'])[0]['adjusted_close'] == 22
    r['adjustflag'] = '1'
    assert adjusted_daily([r], factors, [r['date']], code=r['code'])[0]['reason'] == 'raw_response_flag_mismatch'


def test_missing_hour_invalidates_day_and_stock_close_must_match():
    r = raw(); factors = [{'dividOperateDate': '2025-01-01', 'backAdjustFactor': '2'}]
    daily = adjusted_daily([r], factors, [r['date']], code=r['code'])
    hours = [{**r, 'time': '20250102' + t + '00000'} for t in ['1030', '1130', '1400', '1500']]
    assert all(x['hour_qualified'] for x in qualify_stock_hours(hours, [r], factors, daily)['hours'])
    assert not any(x['hour_qualified'] for x in qualify_stock_hours(hours[:-1], [r], factors, daily)['hours'])
    hours[-1]['close'] = '10.9'
    assert qualify_stock_hours(hours, [r], factors, daily)['daily_audit'][0]['reason'] == 'hour_daily_OHLC_mismatch'
    hours[-1]['close'] = '11'
    hours[0]['adjustflag'] = '1'
    assert qualify_stock_hours(hours, [r], factors, daily)['daily_audit'][0]['reason'] == 'hour_raw_response_flag_mismatch'
