"""Synthetic time-boundary checks only; not an empirical regime/effect test.

Caller must qualify actual exchange month-end closes and truthful version arrival
times. This helper does not establish either. available_at is no earlier than
both publication and actual research acquisition; never backdate late data.
"""
import calendar
from datetime import datetime
from math import isfinite
from pathlib import Path
import json


def timestamp(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone required')
    return dt


def classify(formation_month, decision_at, rows, *, formation_close_at):
    decision = timestamp(decision_at)
    year, month = map(int, formation_month.split('-'))
    end = timestamp(formation_close_at)
    if end is None or end.strftime('%Y-%m') != formation_month:
        raise ValueError('qualified formation close time required')
    if decision < end:
        raise ValueError('formation month not completed')
    serial = year*12+month-1
    months = [f'{x//12:04d}-{x%12+1:02d}' for x in range(serial-9, serial+1)]
    selected = []
    for m in months:
        eligible = [r for r in rows if r['month'] == m and timestamp(r.get('available_at')) is not None and timestamp(r['available_at']) <= decision]
        if not eligible:
            return {'state': 'unknown', 'reason': 'required_month_not_available', 'month': m}
        latest = max(timestamp(r['available_at']) for r in eligible)
        versions = [r for r in eligible if timestamp(r['available_at']) == latest]
        values = {float(r['close']) for r in versions}
        if len(values) != 1:
            raise ValueError('conflicting equally available versions')
        value = next(iter(values))
        if not isfinite(value) or value <= 0:
            return {'state': 'unknown', 'reason': 'invalid_price', 'month': m}
        selected.append(value)
    avg = sum(selected)/10
    return {'state': 'strong' if selected[-1] > avg else 'weak', 'close': selected[-1], 'sma10': avg, 'formation_month': formation_month, 'effective_at': 'next tradable open after decision; not assigned by this qualifier'}


def check():
    rows = []
    for m in range(1, 11):
        month = f'2024-{m:02d}'
        last = calendar.monthrange(2024, m)[1]
        rows.append({'month': month, 'close': 99+m, 'available_at': f'{month}-{last}T23:00:00+00:00'})
    decision = '2024-10-31T23:30:00+00:00'
    def run(month, dt, values):
        return classify(month, dt, values, formation_close_at='2024-10-31T20:00:00+00:00')
    base = run('2024-10', decision, rows)
    assert base['state'] == 'strong'
    future = {'month':'2024-11', 'close': 1000000, 'available_at':'2024-11-30T23:00:00+00:00'}
    assert run('2024-10', decision, rows+[future]) == base
    revision = {'month':'2024-10', 'close': .01, 'available_at':'2024-11-01T01:00:00+00:00'}
    assert run('2024-10', decision, rows+[revision]) == base
    assert run('2024-10', decision, list(reversed(rows))) == base
    equal = [r|{'close':100} for r in rows]
    assert run('2024-10', decision, equal)['state'] == 'weak'
    assert run('2024-10', decision, rows[:-1])['state'] == 'unknown'
    unknown = rows[:-1]+[rows[-1]|{'available_at':None}]
    assert run('2024-10', decision, unknown)['state'] == 'unknown'
    late = rows[:-1]+[rows[-1]|{'available_at':'2024-11-01T00:00:00+00:00'}]
    assert run('2024-10', decision, late)['state'] == 'unknown'
    assert run('2024-10', '2024-10-31T22:00:00+00:00', rows)['state'] == 'unknown'
    invalid = rows[:-1]+[rows[-1]|{'close':0}]
    assert run('2024-10', decision, invalid)['state'] == 'unknown'
    try:
        run('2024-10', decision, rows+[rows[-1]|{'close':1}])
    except ValueError:
        pass
    else:
        raise AssertionError('ambiguous version accepted')
    try:
        run('2024-10', '2024-10-31T19:00:00+00:00', rows)
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete month accepted')
    output = {'synthetic_cases_passed':12, 'real_market_rows_consumed':0, 'real_effect_runs':0, 'future_append_and_late_revision_do_not_change_old_state':True, 'available_at_required':True, 'unknown_not_neutral':True, 'historical_supplier_availability_proven':False, 'execution_eligibility_proven':False, 'exchange_monthend_calendar_verified':False, 'each_month_close_timestamp_verified':False, 'availability_field_truth_verified':False, 'invariance_scope':'only supplied examples with truthful new-record availability after original decision'}
    (Path(__file__).parent/'forward-qualification-receipt.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(output))


if __name__ == '__main__':
    check()
