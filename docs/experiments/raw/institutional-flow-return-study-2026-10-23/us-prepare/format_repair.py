"""Requalify only the exact terminal ' US' identifier format from saved v1 rows.

The original 108 N-PORT partitions and any price or return series are not read.
"""

import argparse
import collections
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import prepare


SOURCE = prepare.OUT / 'lag-holdings-identities.parquet'
SOURCE_QUALIFICATION = prepare.OUT / 'qualification.json'
OUTPUT = prepare.OUT / 'format-v2'
FROZEN_SCRIPT = Path(__file__).with_name('prepare-v1-frozen.py')


def resolved(raw, strip_us):
    direct = prepare.ticker(raw)
    if direct or not strip_us:
        return direct, False
    if raw.endswith(' US'):
        suffix_base = prepare.ticker(raw[:-3])
        if suffix_base:
            return suffix_base, True
    return None, False


def ticker_status(raw_tickers, strip_us):
    values, invalid = set(), False
    normalized = False
    for raw in raw_tickers.split('|') if raw_tickers else ():
        value, changed = resolved(raw, strip_us)
        normalized |= changed
        if value:
            values.add(value)
        else:
            invalid = True
    if len(values) > 1:
        return None, 'ticker_conflict', normalized
    if not values:
        return None, 'ticker_missing', normalized
    if invalid:
        return None, 'ticker_invalid', normalized
    return next(iter(values)), 'candidate_only', normalized


def batches():
    return pq.ParquetFile(SOURCE).iter_batches(batch_size=512)


def verify_first_version(qualification):
    if prepare.sha256_file(SOURCE) != qualification['output_sha256'][SOURCE.name]:
        raise ValueError('v1 lag holdings hash mismatch')
    if prepare.sha256_file(FROZEN_SCRIPT) != qualification['preparation_script_sha256']:
        raise ValueError('v1 source snapshot hash mismatch')
    if prepare.sha256_file(Path(prepare.__file__)) != qualification['preparation_script_sha256']:
        raise ValueError('v1 preparation code changed after first output')
    n = 0
    for batch in batches():
        for row in batch.to_pylist():
            n += 1
            if row['ticker_status'].startswith('isin_'):
                continue
            value, status, _ = ticker_status(row['evidence_raw_tickers'], False)
            if status != row['ticker_status'] or value != row['ticker']:
                raise ValueError(f'v1 status reconstruction mismatch at row {n}')
    if n != qualification['qualified_lag_holdings']:
        raise ValueError('v1 row count mismatch')
    return n


def guard_output():
    prepare.guard_output_storage()
    plan = json.loads(prepare.STORAGE_PLAN.read_text())
    if shutil.disk_usage(prepare.ROOT).free < plan['internal_reserve_bytes']:
        raise ValueError('internal storage below plan reserve; wait for controller recheck')
    if not OUTPUT.resolve().is_relative_to(prepare.OUT.resolve()):
        raise ValueError('format-v2 path escaped external output')
    for name in ('lag-holdings-identities.parquet', 'qualification.json'):
        if (OUTPUT / name).exists():
            raise ValueError('format-v2 output exists; inspect it before rerunning')


def run():
    first = json.loads(SOURCE_QUALIFICATION.read_text())
    row_count = verify_first_version(first)
    guard_output()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    counts_old, counts_new, transitions = collections.Counter(), collections.Counter(), collections.Counter()
    values_old = collections.defaultdict(lambda: Decimal(0))
    values_new = collections.defaultdict(lambda: Decimal(0))
    normalized_rows = 0
    writer = None
    staged = OUTPUT / 'lag-holdings-identities.parquet.inprogress'
    try:
        for batch in batches():
            converted = []
            for original in batch.to_pylist():
                row = dict(original)
                old_status = row['ticker_status']
                old_ticker = row['ticker']
                value, new_status, changed = ticker_status(row['evidence_raw_tickers'], True)
                if old_status.startswith('isin_'):
                    value, new_status = old_ticker, old_status
                row['ticker_original'] = old_ticker
                row['ticker_status_original'] = old_status
                row['ticker'] = value
                row['ticker_status'] = new_status
                row['terminal_us_suffix_seen'] = changed
                row['identity_format_version'] = 'format-v2-terminal-US-only'
                converted.append(row)
                normalized_rows += changed
                counts_old[old_status] += 1
                counts_new[new_status] += 1
                transitions[f'{old_status}->{new_status}'] += 1
                amount = Decimal(row['holding_value_usd'])
                values_old[old_status] += amount
                values_new[new_status] += amount
            table = pa.Table.from_pylist(converted)
            if writer is None:
                writer = pq.ParquetWriter(staged, table.schema, compression='zstd')
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    final_table = OUTPUT / 'lag-holdings-identities.parquet'
    staged.rename(final_table)
    receipt = {
        'decision': 'pre-effect exact terminal space-US source-format repair',
        'row_count': row_count,
        'original_ticker_status_counts': dict(counts_old),
        'repaired_ticker_status_counts': dict(counts_new),
        'status_transitions': dict(transitions),
        'rows_with_recognized_terminal_us_suffix': normalized_rows,
        'original_holding_value_by_status_usd': {k: str(v) for k, v in values_old.items()},
        'repaired_holding_value_by_status_usd': {k: str(v) for k, v in values_new.items()},
        'original_preparation_script_sha256': first['preparation_script_sha256'],
        'repair_script_sha256': prepare.sha256_file(Path(__file__)),
        'original_qualification_path': str(SOURCE_QUALIFICATION),
        'original_qualification_sha256': prepare.sha256_file(SOURCE_QUALIFICATION),
        'original_lag_holdings_sha256': first['output_sha256'][SOURCE.name],
        'source_file_sha256': {k: v['sha256'] for k, v in first['source_files'].items()},
        'repaired_lag_holdings_sha256': prepare.sha256_file(final_table),
        'effects_calculated': 0,
    }
    (OUTPUT / 'qualification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps({k: receipt[k] for k in ('row_count', 'repaired_ticker_status_counts', 'status_transitions')}, ensure_ascii=False))


def synthetic():
    assert ticker_status('MSFT|MSFT US', True)[:2] == ('MSFT', 'candidate_only')
    assert ticker_status('MSFT US|AAPL', True)[1] == 'ticker_conflict'
    assert ticker_status('MSFT|MSFT UK', True)[1] == 'ticker_invalid'
    assert ticker_status('BRK/B|BRK-B', True)[1] == 'ticker_invalid'
    assert ticker_status('MSFT|MSFT US', False)[1] == 'ticker_invalid'
    print('format-v2 synthetic checks passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.synthetic:
        synthetic()
    elif args.run:
        run()
    else:
        parser.error('select --synthetic or --run')
