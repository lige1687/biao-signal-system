"""Research input qualification only; no execution or production decision.

Stocks use raw Bao daily/hourly prices and effective dated action factors.
The independent ETF split-only source is restricted to f=1,u=0 reports;
unsupported cash adjustments are rejected rather than inferred.
"""
from bisect import bisect_right
from collections import Counter, defaultdict
from decimal import Decimal
import json

from lei_signal.research.etf_hourly_recovery import SLOTS, number, valid_bar


def parse_split_source(text, symbol, cutoff):
    prefix = 'var ' + symbol + 'hfq='
    if not text.startswith(prefix):
        raise ValueError('factor symbol or format mismatch')
    obj, _ = json.JSONDecoder().raw_decode(text[len(prefix):])
    rows = obj['data']
    if obj['total'] != len(rows):
        raise ValueError('factor row count mismatch')
    dates = [r['d'] for r in rows]
    if len(set(dates)) != len(dates):
        raise ValueError('duplicate factor date')
    output = []
    for row in sorted(rows, key=lambda x: x['d']):
        # Never use future factor changes even when the source contains them.
        if row['d'] > cutoff:
            continue
        if Decimal(row['f']) != 1 or Decimal(row['u']) != 0:
            raise ValueError('cash/non-unit factor unsupported in split-only branch')
        output.append({'dividOperateDate': row['d'], 'backAdjustFactor': str(number(row['s']))})
    if not output or output[0]['dividOperateDate'] != '1900-01-01':
        raise ValueError('explicit source initial split state missing')
    return output


def adjusted_daily(raw_rows, factors, calendar, *, code):
    """Preserve missing/halts; never default a missing factor to one."""
    raw = {}
    previous = ''
    for row in raw_rows:
        if row['date'] <= previous or row['code'] != code:
            raise ValueError('daily identity/order mismatch')
        previous = row['date']
        raw[previous] = row
    dates = [r['dividOperateDate'] for r in factors]
    if any(r.get('code', code) != code for r in factors):
        raise ValueError('factor identity mismatch')
    if dates != sorted(set(dates)):
        raise ValueError('factor date order')
    scales = [number(r['backAdjustFactor']) for r in factors]
    output = []
    for day in calendar:
        row = raw.get(day)
        index = bisect_right(dates, day) - 1
        reason = None
        if row is None:
            reason = 'vendor_missing'
        elif row.get('adjustflag') != '3':
            reason = 'raw_response_flag_mismatch'
        elif row.get('tradestatus') != '1' or Decimal(row.get('volume', '0')) <= 0:
            reason = 'halt_or_no_volume'
        elif not valid_bar(row):
            reason = 'invalid_raw_price'
        elif index < 0:
            reason = 'factor_effective_date_unknown'
        record = {'date': day, 'qualified': reason is None, 'reason': reason}
        for key in ('open', 'high', 'low', 'close'):
            record['adjusted_' + key] = float(number(row[key]) * scales[index]) if reason is None else None
        output.append(record)
    return output


def qualify_stock_hours(raw_hours, raw_daily, factors, daily):
    """Exact 60-minute OHLC to daily crosscheck; independent 15m not claimed."""
    groups = defaultdict(list)
    codes = {r['code'] for r in raw_daily}
    if len(codes) != 1:
        raise ValueError('daily identity mismatch')
    previous = ''
    for row in raw_hours:
        stamp = row['time']
        if row['code'] not in codes or stamp <= previous or len(stamp) != 17 or stamp[:8] != row['date'].replace('-', ''):
            raise ValueError('stock hour timestamp/order mismatch')
        previous = stamp
        groups[row['date']].append((stamp[8:10] + ':' + stamp[10:12], row))
    raw = {r['date']: r for r in raw_daily}
    dates = [r['dividOperateDate'] for r in factors]
    scales = [number(r['backAdjustFactor']) for r in factors]
    hours, audit = [], []
    for d in daily:
        day, group = d['date'], groups.get(d['date'], [])
        reason = None
        if not d['qualified']:
            reason = 'daily_' + d['reason']
        elif tuple(s for s, _ in group) != SLOTS:
            reason = 'missing_hour_slots'
        elif any(r.get('adjustflag') != '3' for _, r in group):
            reason = 'hour_raw_response_flag_mismatch'
        elif any(not valid_bar(r) for _, r in group):
            reason = 'invalid_hour_price'
        else:
            rows = [r for _, r in group]
            agg = {'open': number(rows[0]['open']), 'close': number(rows[-1]['close']),
                   'high': max(number(r['high']) for r in rows), 'low': min(number(r['low']) for r in rows)}
            if any(abs(agg[k] - number(raw[day][k])) > Decimal('0.00000001') for k in agg):
                reason = 'hour_daily_OHLC_mismatch'
        good = reason is None
        idx = bisect_right(dates, day) - 1
        audit.append({'date': day, 'qualified': good, 'reason': reason})
        for i, slot in enumerate(SLOTS):
            hours.append({'date': day, 'time': slot, 'hour_qualified': good,
                          'adjusted_close': float(number(group[i][1]['close']) * scales[idx]) if good else None})
    streak = longest = 0
    for row in audit:
        streak = streak + 1 if row['qualified'] else 0
        longest = max(longest, streak)
    return {'hours': hours, 'daily_audit': audit,
            'qualification': {'reason_counts': dict(Counter(r['reason'] or 'qualified' for r in audit)),
                              'longest_qualified_days': longest,
                              'independent_15minute_check': False}}
