import math

from lei_signal.market_context.microstructure_equity import (
    adjusted_close, above_prior_quantile, back_factor_events, concentration,
    covered_concentration, cross_section, prior_percentiles, qualified_amount,
    aggregate_amount_concentration,
)


def test_concentration_rank_tie_and_missing():
    assert concentration({"a": 10, "b": 10, "c": 5, "d": 5}, 0.25) == 10 / 30
    assert concentration({"a": 10, "b": None}, 0.5) is None
    assert concentration({"a": 0, "b": 0}, 0.5) is None
    assert covered_concentration({"a": 10}, {"a", "b"}, 0.5) is None
    assert covered_concentration({"a": 10, "b": 0}, {"a", "b"}, 0.5) == 1
    assert covered_concentration({"a": 10, "b": 0}, {"a", "b"}, 0.5, {"b"}) is None
    assert qualified_amount('0', '', '0.000000') == 0
    assert qualified_amount('1', '', '0') is None
    assert qualified_amount('1', '10', '0') is None
    assert qualified_amount('0', '10', '2') is None
    assert qualified_amount('0', '0', '2') is None


def test_cross_section_zero_variance_and_missing_date():
    rows = {"a": [100, 101, 102], "b": [100, 101, 102]}
    assert cross_section(rows, 2)["correlation"] == 1
    assert cross_section({"a": [100, 100, 100], "b": [100, 101, 102]}, 2)["correlation"] is None
    assert cross_section({"a": [100, 101, None], "b": [100, 101, 102]}, 2)["correlation"] is None


def test_prior_percentiles_no_current_leak_or_fill():
    assert prior_percentiles([1, 2, 2, None, 3], 2) == [None, None, 50.0, None, None]
    assert above_prior_quantile(3, [1, None, 2], 95) is None


def test_back_adjustment_survives_cross_batch_reanchored_fore_factor():
    old = {'fields': ['code', 'dividOperateDate', 'foreAdjustFactor', 'backAdjustFactor'],
           'data': [['X', '2026-01-01', '1', '1']]}
    new = {'fields': ['code', 'dividOperateDate', 'foreAdjustFactor', 'backAdjustFactor'],
           'data': [['X', '2026-06-02', '1', '2']]}
    events = back_factor_events(old) | back_factor_events(new)
    assert adjusted_close(100, events['2026-01-01']) == adjusted_close(50, events['2026-06-02'])


def test_amount_aggregation_excludes_delisting_date_and_keeps_zero_suspension():
    days = ['2026-10-16', '2026-10-19']
    stocks = [('a', '2000-01-01', '2026-10-19', {'2026-10-16': 100.0}),
              ('b', '2000-01-01', None, dict.fromkeys(days, 0.0)),
              ('c', '2000-01-01', None, dict.fromkeys(days, 20.0))]
    result = aggregate_amount_concentration(stocks, days, daily_start=days[0], monthly_end='2026-10')
    assert result['daily'][1]['n'] == 2
    assert result['daily'][1]['missingStockDays'] == 0
    assert result['daily'][1]['denominator'] == 20.0
    assert result['daily'][1]['top5'] == 1
    assert result['monthly'][0]['n'] == 3
    assert result['monthly'][0]['top5'] == 100 / 140


def test_amount_monthly_ranks_stock_totals_and_never_fills_missing():
    days = ['2026-09-29', '2026-09-30']
    stocks = [('a', '2000-01-01', None, {days[0]: 90, days[1]: 10}),
              ('b', '2000-01-01', None, {days[0]: 10, days[1]: 90})]
    result = aggregate_amount_concentration(stocks, days, daily_start=days[0], monthly_end='2026-09')
    assert [p['top5'] for p in result['daily']] == [0.9, 0.9]
    assert result['monthly'][0]['top5'] == 0.5
    missing = aggregate_amount_concentration(stocks + [('c', days[1], None, {})], days,
                                            daily_start=days[0], monthly_end='2026-09')
    assert missing['daily'][0]['top5'] == 0.9
    assert missing['daily'][1]['top5'] is None
    assert missing['monthly'][0]['top5'] is None
    assert missing['monthly'][0]['missingStockDays'] == 1
    assert missing['monthly'][0]['missingCodes'] == ['c']
