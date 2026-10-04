"""Source provenance and margin-series boundaries, without network or databases."""
from datetime import UTC, datetime
import pytest
from lei_signal.fundamentals.market_context import make_series, financing_series, metadata_for
from lei_signal.fundamentals.service import _TtlCache


def test_series_keeps_zero_drops_future_and_preserves_absent_points():
    s = make_series('余额', '亿', {'2026-09-28': 0, '2026-09-29': None, '2026-10-05': 2}, today='2026-10-04', metadata={})
    assert s['dates'] == ['2026-09-28', '2026-09-29']
    assert s['values'] == [0, None]


@pytest.mark.parametrize('rows', [ {'2026-02-30': 1}, {'2026-09-01': float('inf')}, {'2026-09-01': True}, {'2026-09-01': '1'} ])
def test_bad_source_values_are_not_coerced(rows):
    with pytest.raises(ValueError):
        make_series('值', '%', rows, today='2026-10-04', metadata={})


def test_financing_fields_do_not_fabricate_repayment_or_net_flow():
    raw={'2026-09-29': {'rzye_yi':100, 'rqye_yi':2, 'buy_yi':7},'2026-09-30': {'rzye_yi':101, 'rqye_yi':None, 'buy_yi':0}}
    out=financing_series(raw, '2026-10-04', {})
    assert set(out)=={'margin_rzye','margin_rqye','margin_buy'}
    assert out['margin_rzye']['values']==[100,101]
    assert out['margin_rqye']['values']==[2,None]
    assert out['margin_buy']['values']==[7,0]


def test_obtained_time_is_not_publication_or_verified_vintage():
    m=metadata_for('eastmoney-margin', '2026-10-04T04:00:00+00:00')
    assert m['retrieved_at']=='2026-10-04T04:00:00+00:00'
    assert m['published_at'] is None and m['vintage'] is None
    assert m['historical_prediction_use']=='unqualified'
    assert m['unit_definition'] and m['source_url'].startswith('https://')


def test_pe_identity_is_provider_specific_not_official_equivalence():
    m=metadata_for('legulegu-hs300', None)
    assert m['provider']=='乐咕乐股，经AkShare'
    assert '官方' in m['limitations'] and m['value_status']=='provider_observed'
    assert m['retrieved_at'] is None


def test_cache_keeps_source_obtained_time_across_cache_hits():
    cache=_TtlCache();calls=[]
    assert cache.retrieved_at_for('x') is None
    cache.get_or_load('x', 100, lambda:calls.append(1) or {'x':1})
    first=cache.retrieved_at_for('x');assert datetime.fromisoformat(first).tzinfo is not None
    cache.get_or_load('x',100,lambda:calls.append(2) or {})
    assert cache.retrieved_at_for('x')==first and calls==[1]
    cache.invalidate('x');assert cache.retrieved_at_for('x') is None


def test_context_partial_source_failure_still_has_independent_series(monkeypatch):
    from lei_signal.fundamentals import sources
    from lei_signal.fundamentals.service import FundamentalsService
    def fail(*a,**k):raise sources.FundamentalsSourceError('upstream secret should not leave service')
    monkeypatch.setattr(sources,'fetch_margin_history',lambda *a,**k:{'2026-09-30':{'rzye_yi':100,'rqye_yi':2,'buy_yi':3}})
    monkeypatch.setattr(sources,'fetch_treasury_history',fail)
    monkeypatch.setattr(sources,'fetch_hs300_pe_history',fail)
    monkeypatch.setattr(sources,'fetch_us_ey_history',fail)
    out=FundamentalsService().market_context(lookback_days=1095)
    assert out['series']['margin_rzye']['values']==[100]
    assert out['series']['us_2y']['dates']==[]
    assert 'secret' not in str(out)
    assert out['source_gaps']['finra_margin']['status']=='permission_unconfirmed'


def test_context_inverse_pe_is_historical_earnings_yield_not_forecast(monkeypatch):
    from lei_signal.fundamentals import sources
    from lei_signal.fundamentals.service import FundamentalsService
    monkeypatch.setattr(sources,'fetch_margin_history',lambda *a,**k:{})
    monkeypatch.setattr(sources,'fetch_treasury_history',lambda *a,**k:{'2026-09-30':{'cn_2y':1.0,'us_2y':3.0,'cn_10y':1.7,'us_10y':3.7}})
    monkeypatch.setattr(sources,'fetch_hs300_pe_history',lambda:{'2026-09-30':20})
    monkeypatch.setattr(sources,'fetch_us_ey_history',lambda:{'2026-09-01':4.5})
    out=FundamentalsService().market_context(lookback_days=1095)
    assert out['series']['earnings_yield_cn']['values']==[5.0]
    assert out['series']['earnings_yield_us']['values']==[4.5]
    assert out['series']['cn_10_2_spread']['values']==[.7]
    assert 'earnings_forward' not in out['series']
    assert out['source_gaps']['earnings_forward']['status']=='missing_input'


@pytest.mark.parametrize('bad', ['3', True, float('inf'), []])
def test_bad_treasury_or_pe_does_not_destroy_independent_financing(monkeypatch, bad):
    from lei_signal.fundamentals import sources
    from lei_signal.fundamentals.service import FundamentalsService
    monkeypatch.setattr(sources, 'fetch_margin_history', lambda *a: {'2026-09-30': {'rzye_yi': 10}})
    monkeypatch.setattr(sources, 'fetch_treasury_history', lambda *a: {'2026-09-30': {'cn_2y': bad, 'cn_10y': 2, 'us_2y': 3, 'us_10y': 4}})
    monkeypatch.setattr(sources, 'fetch_hs300_pe_history', lambda: {'2026-09-30': bad})
    monkeypatch.setattr(sources, 'fetch_us_ey_history', lambda: {})
    out = FundamentalsService().market_context()
    assert out['series']['margin_rzye']['values'] == [10]
    assert out['series']['cn_10_2_spread']['dates'] == []
    assert out['series']['earnings_yield_cn']['dates'] == []
    assert out['series']['us_10_2_spread']['values'] == [1]
