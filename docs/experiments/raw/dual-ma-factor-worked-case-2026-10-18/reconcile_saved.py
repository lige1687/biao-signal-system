"""Reconcile saved small summaries only. No prices, fits, or market reruns."""
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs/experiments/raw/stock-color-account-2026-10-16/summary-tables.json'
data = json.loads(SOURCE.read_text())
out = {'mode': 'saved_summary_arithmetic_only', 'source': str(SOURCE),
       'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'markets': {}}
for market, values in data.items():
    costs = values['costs']
    primary = costs['10']
    result = {'common_wealth_end': primary['common_end'], 'performance': {}, 'increment': {}, 'cost_sensitivity': {}}
    for policy in ['buy_hold', 'sma_sma', 'ema_ema', 'dual_dual']:
        s = primary['cells'][policy]['summary']
        dd = s['drawdown']
        assert (date.fromisoformat(dd['longest_unrecovered_to']) - date.fromisoformat(dd['longest_unrecovered_from'])).days == dd['longest_observed_unrecovered_calendar_days']
        result['performance'][policy] = {
            'wealth_common_date': primary['wealth'][policy],
            'return_percent_common_date': 100 * (primary['wealth'][policy] - 1),
            'observed_drawdown_percent_full_period': 100 * dd['max_observed_close_drawdown'],
            'mean_exposure_percent_known_closes_full_period': 100 * s['average_exposure_known_closes'],
            'unknown_nav_days_full_period': s['total']['valuation_gap_closes'],
            'scheduled_days_full_period': s['total']['scheduled_closes'],
            'full_period_end': s['total']['end_date'],
            'transactions_full_period': s['entries'] + s['exits'],
            'fees_initial_unit_full_period': s['fees_total'],
            'saved_longest_underwater_days': dd['longest_observed_unrecovered_calendar_days'],
            'saved_underwater_from': dd['longest_unrecovered_from'],
            'saved_underwater_to': dd['longest_unrecovered_to'],
        }
    for fee, c in costs.items():
        w = c['wealth']
        rebuilt = {'entry': w['dual_sma'] - w['sma_sma'],
                   'exit': w['sma_dual'] - w['sma_sma'],
                   'interaction': w['dual_dual'] - w['dual_sma'] - w['sma_dual'] + w['sma_sma'],
                   'total': w['dual_dual'] - w['sma_sma']}
        for k, v in rebuilt.items():
            assert abs(v - c['four_grid'][k]) < 1e-12
        assert abs(sum(rebuilt[k] for k in ['entry', 'exit', 'interaction']) - rebuilt['total']) < 1e-12
        result['cost_sensitivity'][fee] = {k + '_return_pp': v * 100 for k, v in rebuilt.items()}
    p = result['performance']
    result['increment'] = {
        'dual_minus_sma_return_pp': 100 * (primary['wealth']['dual_dual'] - primary['wealth']['sma_sma']),
        'dual_minus_hold_return_pp': 100 * (primary['wealth']['dual_dual'] - primary['wealth']['buy_hold']),
        'dual_trade_count_reduction_percent': 100 * (1 - p['dual_dual']['transactions_full_period'] / p['sma_sma']['transactions_full_period']),
        'full_period_sma_minus_dual_fees_initial_percent': 100 * (p['sma_sma']['fees_initial_unit_full_period'] - p['dual_dual']['fees_initial_unit_full_period']),
        'advantage_shift_0_to_10_bps_pp': result['cost_sensitivity']['10']['total_return_pp'] - result['cost_sensitivity']['0']['total_return_pp'],
    }
    out['markets'][market] = result
out['limits'] = ['No independent daily price or cash reconstruction in this run.',
                 'Underwater dates arithmetic checked; saved duration not independently reconstructed.',
                 'CN wealth June26; remaining saved full-period measures through June30; do not silently combine.',
                 'Observed drawdown uses each policy valid closes, not a matched or complete daily risk comparison.']
(HERE / 'saved-reconciliation.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'source_sha256': out['source_sha256'], 'checked': ['six fee/market four-grids', 'eight saved duration date spans'], 'increment': {m:v['increment'] for m,v in out['markets'].items()}}, ensure_ascii=False, indent=2))
