"""Read-only input inventory; never calculates future returns or factor effects."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent

def fingerprint(p):
    return {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    pool = ROOT / 'docs/experiments/raw/exit_three_piece'
    source = json.loads((pool / 'pool_manifest.json').read_text())
    rows = []
    for symbol in source['pool_symbols']:
        path = pool / 'pool' / (symbol + '.bars.parquet')
        meta = path.with_suffix('.meta.json')
        if not path.exists():
            rows.append({'symbol': symbol, 'missing': True})
            continue
        f = pd.read_parquet(path)
        dates = pd.to_datetime(f.index)
        ohlc = f[['open','high','low','close']]
        bad = ((ohlc <= 0).any(axis=1) | ohlc.isna().any(axis=1)
               | (f.low > f[['open','close']].min(axis=1))
               | (f.high < f[['open','close']].max(axis=1)))
        kind = ('index' if symbol == '000300.SS' else
                'ETF_candidate' if symbol.startswith(('15','51','56','58')) else 'stock_candidate')
        row = {'symbol': symbol, 'instrument_class': kind,
               'input': fingerprint(path), 'rows': len(f),
               'first': dates.min().date().isoformat(), 'last': dates.max().date().isoformat(),
               'duplicate_dates': int(dates.duplicated().sum()),
               'sorted': bool(dates.is_monotonic_increasing), 'invalid_ohlc_rows': int(bad.sum()),
               'price_basis': 'tencent_qfq; source README, not economic_price',
               'corporate_action_reconstruction': 'not_in_pool_manifest',
               'exchange_calendar_and_suspension_classification': 'not_in_pool_manifest',
               'historical_vendor_arrival': 'unknown',
               'sampling': 'union of old strategy run symbols; not representative random sample',
               'effect_eligible_current_contract': False}
        if meta.exists():
            row['metadata'] = fingerprint(meta)
            row['fetched_at'] = json.loads(meta.read_text()).get('fetched_at')
        rows.append(row)
    result = {'scope': 'all 127 retained inputs; no outcome values or candidate selection',
              'sources': [fingerprint(pool / 'pool_manifest.json'), fingerprint(pool / 'README.md')],
              'summary': {'symbols': len(rows), 'present': sum(not r.get('missing') for r in rows),
                          'classes': {k:sum(r.get('instrument_class')==k for r in rows)
                                      for k in ['index','ETF_candidate','stock_candidate']},
                          'bad_ohlc_rows': sum(r.get('invalid_ohlc_rows',0) for r in rows)},
              'rows': rows,
              'limitations': ['File presence does not qualify market data or licensing.',
                              'Current surviving/run-selected pool cannot estimate an entire sector/stock universe.',
                              'No exchange-day gaps inferred from quote-date union; do not invent suspension status.',
                              'qfq input cannot silently replace frozen economic prices.',
                              'Do not upload these input prices to Git.']}
    (OUT / 'universe-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['summary']))

if __name__ == '__main__':
    main()
