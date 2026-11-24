"""Audit fixed, already reported US events; never execute WorkBuddy scripts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parent
validation_path = ROOT / 'workbuddy-us-validation-json-v4.snapshot'
price_path = ROOT / 'workbuddy-us-gspc-json-v4.snapshot'
validation = json.loads(validation_path.read_text())
raw = json.loads(price_path.read_text())['chart']['result'][0]
assert raw['meta']['symbol'] == '^GSPC'
prices = {
    datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%d'): float(c)
    for t, c in zip(raw['timestamp'], raw['indicators']['quote'][0]['close'])
    if c is not None
}
dates = sorted(prices)
position = {d: i for i, d in enumerate(dates)}
values = [prices[d] for d in dates]


def path(day, delay):
    start = position[day] + delay
    end = start + 250
    assert end < len(dates)
    future = values[start:end + 1]
    return {
        'signal_date': day, 'start': dates[start], 'end': dates[end],
        'start_close': values[start], 'end_close': values[end],
        'price_change_pct': 100 * (values[end] / values[start] - 1),
        'lowest_close_relative_to_start_pct': 100 * (min(future) / values[start] - 1),
    }


events = []
for (day, breadth), original in zip(validation['sig_idx'], validation['sig_r']):
    a, b = path(day, 0), path(day, 1)
    events.append({'breadth_200': breadth, 'original_reported_pct': original,
                   'same_close_full_calendar': a, 'next_close_full_calendar': b,
                   'same_close_report_difference_pp': a['price_change_pct'] - original})

assert len(events) == len(validation['sig_idx']) == len(validation['sig_r']) == 5
baseline = [100 * (values[i + 250] / values[i] - 1)
            for i, d in enumerate(dates)
            if validation['range'][0] <= d <= validation['range'][1]
            and i + 250 < len(dates) and dates[i + 250] <= validation['range'][1]]
summary = {}
for key in ['same_close_full_calendar', 'next_close_full_calendar']:
    rs = [x[key]['price_change_pct'] for x in events]
    summary[key] = {'n': len(rs), 'mean_pct': statistics.mean(rs),
                    'median_pct': statistics.median(rs), 'positive_count': sum(r > 0 for r in rs),
                    'worst_pct': min(rs),
                    'worst_adverse_path_pct': min(x[key]['lowest_close_relative_to_start_pct'] for x in events)}

result = {
    'source_symbol': raw['meta']['symbol'],
    'source_price_range': [dates[0], dates[-1]],
    'review_range': validation['range'],
    'events_fixed_from_existing_result': True, 'new_threshold_searches': 0,
    'reported_sig_k': validation['sig_k'], 'actual_event_count': len(events),
    'reported_count_matches_events': validation['sig_k'] == len(events),
    'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [validation_path, price_path]},
    'events': events, 'summary': summary,
    'full_calendar_baseline': {'n': len(baseline), 'mean_pct': statistics.mean(baseline),
                               'positive_pct': 100 * sum(v > 0 for v in baseline) / len(baseline)},
    'reported_conditional_randomization': validation['cond'],
    'reported_erp': validation['erp'],
    'limitations': [
        'Five reported events only; no independent sample or breadth membership/PIT qualification.',
        'All-date baseline overlaps heavily and is not conditional increment.',
        'No p-values recomputed: original date-level randomization does not preserve crisis dependence.',
        'Historical index price paths, not ETF/account returns and not exact top/bottom accuracy.',
        'No threshold selection or historical strategy source modification.'
    ],
}
(ROOT / 'workbuddy-us-fixed-audit-v4.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'summary': summary, 'baseline': result['full_calendar_baseline'],
                  'max_report_difference_pp': max(abs(x['same_close_report_difference_pp']) for x in events)}, ensure_ascii=False))
