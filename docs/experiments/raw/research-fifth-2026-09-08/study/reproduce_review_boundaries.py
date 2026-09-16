"""Independent malformed-input probes; never runs candidate strategy results."""
import importlib.util
import json
from pathlib import Path

root = Path(__file__).parent
spec = importlib.util.spec_from_file_location('review_target', root / 'cash_engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
quotes = {f'2023-01-{i:02d}': {'open': 10 if i < 4 else 9, 'close': 10 if i < 4 else 9} for i in range(1, 7)}
event = dict(symbol='x', type='cash_dividend', event_id='e1', record_date='2023-01-03', ex_date='2023-01-04', pay_date='2023-01-06', cash_per_share=1)
kwargs = dict(start='2023-01-02', end='2023-01-06', weekly=1000, fee=0, cash_rate=0, rebalance=False, limits={'x': 1})
cases = {
    'same_economic_dividend_different_ids': [event, dict(event, event_id='e2')],
    'invalid_split_date': [dict(symbol='x', type='split', event_id='s', ex_date='2023-02-30', ratio=5)],
}
results = {}
for name, events in cases.items():
    try:
        result = engine.simulate({'x': quotes}, events, **kwargs)
        results[name] = dict(rejected=False, final_equity=result['daily'][-1]['equity'])
    except ValueError as error:
        results[name] = dict(rejected=True, error=str(error))
print(json.dumps(results, ensure_ascii=False, indent=2))
