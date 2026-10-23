"""Frozen four-fund US holder-pressure study. Synthetic/prepare never read outcomes."""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import plistlib
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'storage-plan.json'
DESIGN = ROOT / 'design-before-effects.json'
EVENTS = ROOT / 'us-price-qualification/events.json'
PREP = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/us-prepared')
PREP_V2 = PREP / 'format-v2'
OUT = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/us-effects/v2')
FUNDS = ('S000000856', 'S000006037', 'S000007112', 'S000011202')
B_COLS = ('momentum_12_1', 'last21', 'vol63', 'log_holding_usd', 'share_parnassus', 'share_contrafund', 'share_magellan')
ALL_COLS = ('x',) + B_COLS
REGULAR_SOURCES = {'yahoo', 'tiingo', 'crsp'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def guard_storage():
    plan = json.loads(PLAN.read_text())
    assert OUT.resolve().is_relative_to(Path(plan['output']).resolve())
    mount = Path(plan['external_mount'])
    info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', str(mount)]))
    assert info['VolumeUUID'].upper() == plan['external_uuid'].upper()
    assert mount.stat().st_dev == plan['external_device']
    import shutil
    assert shutil.disk_usage(mount).free > plan['external_reserve_bytes']
    assert shutil.disk_usage(ROOT).free > plan['internal_reserve_bytes']


def refuse_existing(names):
    if any((OUT / name).exists() for name in names):
        raise RuntimeError('Output exists: inspect prior run; no overwrite or retry')


def ticker_forms(ticker):
    if not isinstance(ticker, str) or not ticker.strip():
        return ()
    t = ticker.strip().upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}(?:[.-][A-Z0-9]{1,2})?', t):
        return ()
    return tuple(dict.fromkeys((t, t.replace('.', '-'), t.replace('-', '.'))))


def weighted_pressure(holdings, fund_rates):
    total = sum(holdings.values())
    if total <= 0 or any(f not in fund_rates or not np.isfinite(fund_rates[f]) for f in holdings):
        return np.nan
    return sum(amount * max(fund_rates[f], 0.0) for f, amount in holdings.items()) / total


def planned_dates():
    return [pd.Timestamp(year, month, {3: 31, 6: 30, 9: 30, 12: 31}[month]).date().isoformat()
            for year in range(2020, 2027) for month in (3, 6, 9, 12)
            if (year, month) <= (2026, 6)]


def daily_vol(adjusted):
    a = np.asarray(adjusted, dtype=float)
    return float(np.std(a[1:] / a[:-1] - 1, ddof=0))


def event_index(data):
    point = collections.defaultdict(set)
    no_trade = collections.defaultdict(set)
    gap = collections.defaultdict(list)
    for e in data['events']:
        t = e['ticker']
        if e['type'] in ('manual_override', 'spin_off'):
            point[t].add(pd.Timestamp(e['event_date']))
        elif e['type'] == 'no_trade_day':
            no_trade[t].add(pd.Timestamp(e['event_date']))
        elif e['type'] == 'exit_gap':
            gap[t].append((pd.Timestamp(e['last_trade']), pd.Timestamp(e['next_trade'])))
    return point, no_trade, gap


def intersects(points, ticker, start, end):
    return any(start < d <= end for d in points.get(ticker, ()))


def crosses_exit_gap(gaps, ticker, start, end):
    return any(last_trade < end and next_trade > start for last_trade, next_trade in gaps.get(ticker, ()))


def price_usable(row, ticker, no_trade, gaps):
    if row is None or not np.isfinite(row['adj_close']) or row['adj_close'] <= 0:
        return False
    if row['source'] not in REGULAR_SOURCES or row['date'] in no_trade.get(ticker, ()):
        return False
    if any(a < row['date'] < b for a, b in gaps.get(ticker, ())):
        return False
    vol = row['volume']
    if row['source'] != 'crsp' and (not np.isfinite(vol) or vol <= 0):
        return False
    return True


class PriceSeries:
    """Compact sorted arrays: avoid one Python dict per daily price row."""

    def __init__(self, frame):
        self.dates = frame.date.to_numpy(dtype='datetime64[ns]')
        self.adj_close = frame.adj_close.to_numpy(dtype=float)
        self.volume = frame.volume.to_numpy(dtype=float)
        categories = pd.Categorical(frame.source)
        self.source_codes = categories.codes.astype(np.int16)
        self.sources = tuple(str(x) for x in categories.categories)

    def get(self, date):
        needle = np.datetime64(pd.Timestamp(date), 'ns')
        ix = np.searchsorted(self.dates, needle)
        if ix >= len(self.dates) or self.dates[ix] != needle:
            return None
        code = int(self.source_codes[ix])
        return dict(date=pd.Timestamp(self.dates[ix]), adj_close=float(self.adj_close[ix]),
                    volume=float(self.volume[ix]), source=self.sources[code] if code >= 0 else None)

    def has_on_or_before(self, date):
        return len(self.dates) > 0 and self.dates[0] <= np.datetime64(pd.Timestamp(date), 'ns')


def load_prices(tickers, start='2018-01-01'):
    event = json.loads(EVENTS.read_text())
    path = Path(event['source_root']) / 'prices.parquet'
    if sha(path) != event['source_sha256']['prices.parquet']:
        raise ValueError('Price hash mismatch')
    keep = set(tickers) | {'SPY'}
    blocks = []
    keep_arrow = pa.array(sorted(keep), type=pa.large_string())
    start_arrow = pa.scalar(pd.Timestamp(start).to_pydatetime())
    for batch in pq.ParquetFile(path).iter_batches(batch_size=250000, columns=['ticker', 'date', 'adj_close', 'volume', 'source']):
        ticker_col = batch.column(batch.schema.get_field_index('ticker'))
        date_col = batch.column(batch.schema.get_field_index('date'))
        mask = pc.and_(pc.is_in(ticker_col, value_set=keep_arrow), pc.greater_equal(date_col, start_arrow))
        filtered = batch.filter(mask)
        if filtered.num_rows:
            blocks.append(filtered.to_pandas())
    if not blocks:
        raise ValueError('No prices for target tickers')
    prices = pd.concat(blocks, ignore_index=True)
    if prices.duplicated(['ticker', 'date']).any():
        raise ValueError('Duplicate ticker/date price')
    prices.sort_values(['ticker', 'date'], inplace=True)
    calendar = sorted(prices.loc[prices.ticker.eq('SPY'), 'date'].unique())
    if len(calendar) < 300:
        raise ValueError('No adequate SPY calendar')
    by = {t: PriceSeries(g) for t, g in prices.groupby('ticker', sort=False)}
    return by, calendar, event_index(event)


def zscore_by_date(frame, columns):
    """All feature-eligible formation rows set same-date mean/population SD."""
    out = frame.copy()
    for c in columns:
        mean = out.groupby('decision_date')[c].transform('mean')
        std = out.groupby('decision_date')[c].transform(lambda x: x.std(ddof=0))
        out['z_' + c] = ((out[c] - mean) / std.where(std.gt(0), np.nan)).fillna(0.0)
    return out


def price_features(ticker, decision, calendar, prices, event):
    points, no_trade, gaps = event
    ix = np.searchsorted(calendar, np.datetime64(decision), side='right') - 1
    if ix < 252:
        return None, 'history_too_short'
    dates = [calendar[ix - k] for k in (252, 21, 0)]
    rows = [prices.get(ticker, {}).get(d) for d in dates]
    if not all(price_usable(r, ticker, no_trade, gaps) for r in rows):
        return None, 'history_endpoint_invalid'
    if intersects(points, ticker, dates[0], dates[-1]):
        return None, 'history_manual_action'
    if crosses_exit_gap(gaps, ticker, dates[0], dates[-1]):
        return None, 'history_exit_rights_unverified'
    if ticker == 'T' and dates[0] < pd.Timestamp('2022-04-11'):
        return None, 'history_dividend_basis_unverified'
    vol_dates = calendar[ix - 63:ix + 1]
    vol_rows = [prices.get(ticker, {}).get(d) for d in vol_dates]
    if len(vol_rows) != 64 or not all(price_usable(r, ticker, no_trade, gaps) for r in vol_rows):
        return None, 'history_vol63_incomplete'
    return dict(momentum_12_1=rows[1]['adj_close'] / rows[0]['adj_close'] - 1,
                last21=rows[2]['adj_close'] / rows[1]['adj_close'] - 1,
                vol63=daily_vol([r['adj_close'] for r in vol_rows])), None


def synthetic():
    assert ticker_forms('BRK.B') == ('BRK.B', 'BRK-B')
    assert ticker_forms(' ABC ') == ('ABC',)
    assert not ticker_forms('A/B')
    p = collections.defaultdict(set, {'ABC': {pd.Timestamp('2020-05-01')}})
    assert intersects(p, 'ABC', pd.Timestamp('2020-04-30'), pd.Timestamp('2020-05-01'))
    assert not intersects(p, 'ABC', pd.Timestamp('2020-05-01'), pd.Timestamp('2020-06-01'))
    s = pd.Series([1., 1., 1., 2., 3., 4.])
    ranks = s.rank(method='average')
    pct = (ranks - 1) / (len(s) - 1)
    assert sum(pct <= 1/3) == 3 and sum(pct >= 2/3) == 2
    x = np.array([[1., 0.], [0., 1.]])
    y = np.array([2., 3.])
    assert np.allclose(np.linalg.solve(x.T @ x + np.eye(2), x.T @ y), [1., 1.5])
    training = pd.DataFrame({'decision_date': ['a', 'a', 'b'], 'z_x': [1., 1., 2.],
                             'return_demeaned': [1., 1., 2.]})
    # First date has two rows but the same total weight as the second date.
    assert np.allclose(fit_ridge(training, ('x',)), [5 / 6])
    assert quarter_after('2026-06-30') == pd.Timestamp('2026-09-30')
    assert after([pd.Timestamp('2020-03-31'), pd.Timestamp('2020-04-01')], pd.Timestamp('2020-03-31')) == pd.Timestamp('2020-04-01')
    px = {'ABC': {pd.Timestamp('2020-04-01'): dict(date=pd.Timestamp('2020-04-01'), adj_close=10., volume=100., source='yahoo'),
                  pd.Timestamp('2020-07-01'): dict(date=pd.Timestamp('2020-07-01'), adj_close=11., volume=100., source='yahoo')}}
    assert target_return('ABC', pd.Timestamp('2020-04-01'), pd.Timestamp('2020-07-01'), px,
                         (p, {}, {}))[1] == 'future_manual_action_unverified'
    assert np.isclose(weighted_pressure({'a': 3., 'b': 1.}, {'a': 0.2, 'b': -0.1}), 0.15)
    assert np.isnan(weighted_pressure({'a': 3., 'b': 1.}, {'a': 0.2}))
    assert len(planned_dates()) == 26 and planned_dates()[0] == '2020-03-31' and planned_dates()[-1] == '2026-06-30'
    assert np.isclose(daily_vol([1., 2., 3.]), 0.25)
    cutoff = pd.Timestamp('2020-06-30')
    assert not (pd.Timestamp('2020-07-01') < cutoff)
    assert pd.Timestamp('2020-04-01') < cutoff
    assert group_of(pd.Series([1., 1., 1.])).eq('middle').all()
    # Unknown future labels must not affect ranking on the full formation pool.
    whole = group_of(pd.Series([1., 2., 3., 4.]))
    assert whole.iloc[3] == 'upper' and whole.equals(group_of(pd.Series([1., 2., 3., 4.])))
    future_only = PriceSeries(pd.DataFrame({'date': [pd.Timestamp('2021-01-01')],
                                            'adj_close': [10.], 'volume': [100.], 'source': ['yahoo']}))
    assert not future_only.has_on_or_before(pd.Timestamp('2020-12-31'))
    missing_source = PriceSeries(pd.DataFrame({'date': [pd.Timestamp('2020-01-01')],
                                              'adj_close': [10.], 'volume': [100.], 'source': [None]}))
    assert missing_source.get('2020-01-01')['source'] is None
    assert not price_usable(missing_source.get('2020-01-01'), 'ABC', {}, {})
    cal = list(pd.bdate_range('2020-01-01', periods=270))
    complete = {'ABC': {d: dict(date=d, adj_close=10. + i / 1000, volume=100., source='yahoo')
                        for i, d in enumerate(cal)}}
    old_gap = {'ABC': [(cal[50], cal[52])]}
    assert price_features('ABC', cal[-1], cal, complete, ({}, {}, old_gap))[1] == 'history_exit_rights_unverified'
    print(json.dumps({'synthetic': 'passed', 'effects_calculated': False}))


def prepare():
    guard_storage()
    refuse_existing(('formations.parquet', 'feature-qualification.json'))
    qpath = PREP / 'qualification.json'
    q2path = PREP_V2 / 'qualification.json'
    if not qpath.exists() or not q2path.exists():
        raise RuntimeError('Canonical US prepared inputs missing; wait for preparation owner')
    q = json.loads(qpath.read_text())
    q2 = json.loads(q2path.read_text())
    if sha(qpath) != q2['original_qualification_sha256']:
        raise ValueError('Original preparation receipt changed')
    inputs = {'fund-flow-selection.csv': PREP / 'fund-flow-selection.csv',
              'lag-holdings-identities.parquet': PREP_V2 / 'lag-holdings-identities.parquet'}
    if sha(inputs['fund-flow-selection.csv']) != q['output_sha256']['fund-flow-selection.csv']:
        raise ValueError('Fund flow input hash mismatch')
    if sha(inputs['lag-holdings-identities.parquet']) != q2['repaired_lag_holdings_sha256']:
        raise ValueError('Repaired identity input hash mismatch')
    if q2['row_count'] != 9423 or q2['repaired_ticker_status_counts'].get('candidate_only') != 8884:
        raise ValueError('Unexpected canonical format-v2 scope')
    h = pd.read_parquet(inputs['lag-holdings-identities.parquet'])
    f = pd.read_csv(inputs['fund-flow-selection.csv'], dtype={'series': str})
    assert set(f.series.dropna()) == set(FUNDS)
    names = set()
    for t in h.ticker.dropna():
        names.update(ticker_forms(t))
    prices, calendar, events = load_prices(names)
    flows = {(r.decision_date, r.series): r for r in f.itertuples(index=False)}
    records = []
    # Group by contemporaneously known issuer CUSIP; preserve every formation.
    for (decision, cusip), group in h.groupby(['decision_date', 'cusip'], dropna=False, sort=True):
        d = pd.Timestamp(decision)
        holdings = collections.defaultdict(float)
        for r in group.itertuples(index=False):
            holdings[r.series] += float(r.holding_value_usd)
        total = sum(holdings.values())
        rates = {}
        flow_bad = False
        for fund, amount in holdings.items():
            fr = flows.get((str(decision), fund))
            if fr is None or fr.status != 'selected' or not np.isfinite(fr.redemption_pressure):
                flow_bad = True
            else:
                rates[fund] = float(fr.redemption_pressure)
        x = weighted_pressure(holdings, rates) if not flow_bad else np.nan
        non_fidelity = {f: a for f, a in holdings.items() if f in (FUNDS[0], FUNDS[3])}
        x_no_fidelity = weighted_pressure(non_fidelity, rates) if non_fidelity and not flow_bad else np.nan
        raw_tickers = sorted(set(group.ticker.dropna().astype(str)))
        reasons = []
        ticker = None
        if len(raw_tickers) != 1 or not group.ticker_status.eq('candidate_only').all():
            reasons.append('historical_identifier_ambiguous')
        else:
            forms = ticker_forms(raw_tickers[0])
            # Future-only price existence cannot decide a formation-date identity.
            matches = [t for t in forms if t in prices and prices[t].has_on_or_before(d)]
            if len(matches) == 1:
                ticker = matches[0]
            else:
                reasons.append('price_ticker_missing_or_ambiguous')
        features = None
        if ticker in ('COR', 'STI'):
            reasons.append('known_ticker_reuse')
        elif ticker:
            features, err = price_features(ticker, d, calendar, prices, events)
            if err:
                reasons.append(err)
        if features is None:
            features = dict.fromkeys(('momentum_12_1', 'last21', 'vol63'), np.nan)
        rec = dict(decision_date=str(decision), cusip=cusip, ticker=ticker,
                   original_ticker=raw_tickers[0] if len(raw_tickers) == 1 else None,
                   identity_status='|'.join(reasons) if reasons else 'candidate_exact',
                   holding_usd=total, x=x, x_no_fidelity=x_no_fidelity,
                   log_holding_usd=math.log(total) if total > 0 else np.nan,
                   share_parnassus=holdings.get(FUNDS[0], 0.) / total if total > 0 else np.nan,
                   share_contrafund=holdings.get(FUNDS[1], 0.) / total if total > 0 else np.nan,
                   share_magellan=holdings.get(FUNDS[2], 0.) / total if total > 0 else np.nan,
                   covered_funds='|'.join(sorted(holdings)), **features)
        rec['feature_eligible'] = not reasons and all(np.isfinite(rec[c]) for c in ALL_COLS)
        records.append(rec)
    formations = pd.DataFrame.from_records(records).sort_values(['decision_date', 'cusip'])
    if sorted(formations.decision_date.unique()) != planned_dates():
        raise ValueError('Formation dates are not complete fixed 26-quarter grid')
    OUT.mkdir(parents=True, exist_ok=True)
    formations.to_parquet(OUT / 'formations.parquet', index=False)
    summary = dict(stage='prepare', effects_calculated=False, source_hashes={str(v): sha(v) for v in inputs.values()},
                   preparation_receipts_sha256={str(qpath): sha(qpath), str(q2path): sha(q2path)},
                   prices_sha256=json.loads(EVENTS.read_text())['source_sha256']['prices.parquet'],
                   design_sha256=sha(DESIGN), events_sha256=sha(EVENTS), formations_sha256=sha(OUT / 'formations.parquet'),
                   decision_dates=int(formations.decision_date.nunique()), formations=len(formations),
                   feature_eligible=int(formations.feature_eligible.sum()),
                   identity_status_counts=formations.identity_status.value_counts().to_dict())
    (OUT / 'feature-qualification.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False))


def quarter_after(date):
    date = pd.Timestamp(date)
    month = ((date.month - 1) // 3 + 1) * 3
    if month == 12:
        return pd.Timestamp(date.year + 1, 3, 31)
    next_month = month + 3
    return pd.Timestamp(date.year, next_month, {3: 31, 6: 30, 9: 30, 12: 31}[next_month])


def after(calendar, date):
    k = np.searchsorted(calendar, np.datetime64(date), side='right')
    return calendar[k] if k < len(calendar) else pd.NaT


def target_return(ticker, entry, exit_date, prices, events):
    points, no_trade, gaps = events
    if ticker in ('COR', 'STI'):
        return np.nan, 'ticker_reuse'
    if pd.isna(entry) or pd.isna(exit_date):
        return np.nan, 'future_calendar_unavailable'
    rows = prices.get(ticker, {})
    a, b = rows.get(entry), rows.get(exit_date)
    if not price_usable(a, ticker, no_trade, gaps) or not price_usable(b, ticker, no_trade, gaps):
        return np.nan, 'future_quote_missing_or_nontrade'
    if intersects(points, ticker, entry, exit_date):
        return np.nan, 'future_manual_action_unverified'
    if ticker == 'T' and entry < pd.Timestamp('2022-04-11'):
        return np.nan, 'future_dividend_basis_unverified'
    # A corporate transaction can leave rights unknown even where a later ticker quote exists.
    if crosses_exit_gap(gaps, ticker, entry, exit_date):
        return np.nan, 'exit_gap_rights_unverified'
    return b['adj_close'] / a['adj_close'] - 1, 'observed_candidate'


def fit_ridge(train, features):
    x = train[['z_' + c for c in features]].to_numpy(float)
    y = train['return_demeaned'].to_numpy(float)
    n = train.groupby('decision_date')['decision_date'].transform('size').to_numpy(float)
    w = 1.0 / n
    # Exactly sum_date mean_squared_error_date + 1*||beta||^2, no division by dates.
    return np.linalg.solve((x * w[:, None]).T @ x + np.eye(len(features)), (x * w[:, None]).T @ y)


def group_of(scores):
    if len(scores) < 2 or scores.nunique(dropna=True) < 2:
        return pd.Series('middle', index=scores.index)
    ranks = scores.rank(method='average')
    p = (ranks - 1) / (len(scores) - 1)
    return pd.Series(np.where(p <= 1 / 3, 'lower', np.where(p >= 2 / 3, 'upper', 'middle')), index=scores.index)


def metric_date(group, model):
    score = group['score_' + model]
    usable = group[score.notna()]
    if usable.empty:
        return None, None
    observed = usable[usable.target_return.notna()]
    ic = observed['score_' + model].corr(observed.target_return, method='spearman') if len(observed) >= 10 else np.nan
    if not np.isfinite(ic):
        ic = np.nan
    all_avg = observed.target_return.mean() if len(observed) else np.nan
    upper = observed[observed['group_' + model].eq('upper')]
    lower = observed[observed['group_' + model].eq('lower')]
    upper_all = usable[usable['group_' + model].eq('upper')]
    record = dict(decision_date=group.decision_date.iloc[0], model=model, formation_n=len(group),
                  feature_n=len(usable), outcome_observed_n=len(observed), outcome_unknown_n=len(usable)-len(observed),
                  feature_holding_usd=float(usable.holding_usd.sum()), ic=ic,
                  upper_n=len(upper_all), upper_observed_n=len(upper), upper_unknown_n=len(upper_all)-len(upper),
                  upper_unknown_fraction=(len(upper_all)-len(upper))/len(upper_all) if len(upper_all) else np.nan,
                  upper_holding_usd=float(upper_all.holding_usd.sum()), upper_observed_return=upper.target_return.mean(),
                  lower_observed_return=lower.target_return.mean(), whole_observed_return=all_avg,
                  upper_observed_median=upper.target_return.median(),
                  lower_observed_median=lower.target_return.median(),
                  whole_observed_median=observed.target_return.median(),
                  upper_positive_fraction=float(upper.target_return.gt(0).mean()) if len(upper) else np.nan,
                  lower_positive_fraction=float(lower.target_return.gt(0).mean()) if len(lower) else np.nan,
                  whole_positive_fraction=float(observed.target_return.gt(0).mean()) if len(observed) else np.nan,
                  upper_minus_whole=upper.target_return.mean()-all_avg if len(upper) and len(observed) else np.nan)
    for cost in (0.002, 0.005):
        suffix = '20bp' if cost == 0.002 else '50bp'
        record['upper_after_' + suffix] = record['upper_observed_return'] - cost
        record['whole_after_' + suffix] = all_avg - cost
    return record, observed


def bootstrap_quarterly(series, n_draw=2000, seed=20261023):
    """Circular 4-quarter blocks on full chronological calendar; retain missing dates."""
    values = np.asarray(series, float)
    if len(values) == 0 or not np.isfinite(values).any():
        return None
    rng = np.random.default_rng(seed)
    sample = np.empty(n_draw)
    n = len(values)
    blocks = math.ceil(n / 4)
    for i in range(n_draw):
        starts = rng.integers(0, n, size=blocks)
        ix = np.concatenate([(np.arange(s, s + 4) % n) for s in starts])[:n]
        v = values[ix]
        sample[i] = np.nanmean(v) if np.isfinite(v).any() else np.nan
    good = sample[np.isfinite(sample)]
    if not len(good):
        return None
    return [float(np.quantile(good, 0.025)), float(np.quantile(good, 0.975))]


def finite_float(value):
    return float(value) if value is not None and np.isfinite(value) else None


def summarize(per_date, dates):
    table = per_date.set_index(['decision_date', 'model'])
    summary = {}
    for model in ('raw_X', 'momentum_12_1', 'B', 'fitted_X', 'B_plus_X'):
        rows = table.xs(model, level='model', drop_level=False) if model in table.index.get_level_values('model') else pd.DataFrame()
        ic = rows['ic'].to_numpy(float) if len(rows) else np.array([])
        summary[model] = dict(ic_n=int(np.isfinite(ic).sum()), ic_mean=finite_float(np.nanmean(ic)) if np.isfinite(ic).any() else None,
                              ic_median=finite_float(np.nanmedian(ic)) if np.isfinite(ic).any() else None,
                              ic_positive_fraction=finite_float(np.mean(ic[np.isfinite(ic)] > 0)) if np.isfinite(ic).any() else None,
                              upper_minus_whole_mean=finite_float(rows.upper_minus_whole.mean()) if len(rows) else None)
    wide = per_date.pivot(index='decision_date', columns='model', values=['ic', 'upper_observed_return']).reindex(dates)
    paired = {}
    for col in ('ic', 'upper_observed_return'):
        if ('B_plus_X' in wide[col]) and ('B' in wide[col]):
            dif = wide[col]['B_plus_X'] - wide[col]['B']
            paired[col] = dict(n=int(dif.notna().sum()), mean=finite_float(dif.mean()) if dif.notna().any() else None,
                               block95=bootstrap_quarterly(dif.to_numpy(float)))
    for model in summary:
        for col in ('ic', 'upper_minus_whole'):
            if col == 'upper_minus_whole':
                vector = per_date[per_date.model.eq(model)].set_index('decision_date')[col].reindex(dates).to_numpy(float)
            else:
                vector = wide['ic'][model].to_numpy(float) if model in wide['ic'] else np.array([])
            summary[model][col + '_block95'] = bootstrap_quarterly(vector)
    return summary, paired


def effects():
    guard_storage()
    refuse_existing(('forecast-rows.parquet', 'per-date-metrics.csv', 'four-cells.csv',
                     'sensitivity-no-fidelity.csv', 'fit-ledger.csv', 'summary.json'))
    prepared_manifest = json.loads((OUT / 'feature-qualification.json').read_text())
    if sha(OUT / 'formations.parquet') != prepared_manifest['formations_sha256']:
        raise ValueError('Formation hash mismatch')
    if sha(DESIGN) != prepared_manifest['design_sha256'] or sha(EVENTS) != prepared_manifest['events_sha256']:
        raise ValueError('Design or event inventory changed after prepare')
    formation = pd.read_parquet(OUT / 'formations.parquet')
    tnames = set(formation.ticker.dropna())
    prices, calendar, events = load_prices(tnames)
    dates = planned_dates()
    if sorted(formation.decision_date.unique()) != dates:
        raise ValueError('Prepared formation dates do not match full planned grid')
    schedule = {}
    fit_rows = []
    for d in dates:
        entry = after(calendar, pd.Timestamp(d))
        exit_date = after(calendar, quarter_after(d))
        schedule[d] = (entry, exit_date)
    result = formation.copy()
    result['entry_date'] = result.decision_date.map(lambda d: schedule[d][0])
    result['exit_date'] = result.decision_date.map(lambda d: schedule[d][1])
    outcomes = [target_return(r.ticker, r.entry_date, r.exit_date, prices, events)
                if r.feature_eligible else (np.nan, 'feature_unavailable') for r in result.itertuples(index=False)]
    result['target_return'] = [x[0] for x in outcomes]
    result['target_status'] = [x[1] for x in outcomes]
    # Same common B/X/B+X feature population, irrespective of future outcomes.
    eligible = result[result.feature_eligible].copy()
    eligible = zscore_by_date(eligible, ALL_COLS)
    result = result.merge(eligible[['decision_date', 'cusip'] + ['z_' + c for c in ALL_COLS]],
                          on=['decision_date', 'cusip'], how='left', validate='one_to_one')
    for m in ('raw_X', 'momentum_12_1', 'B', 'fitted_X', 'B_plus_X', 'raw_X_no_fidelity'):
        result['score_' + m] = np.nan
        result['group_' + m] = None
    result.loc[result.feature_eligible, 'score_raw_X'] = result.loc[result.feature_eligible, 'x']
    result.loc[result.feature_eligible, 'score_momentum_12_1'] = result.loc[result.feature_eligible, 'momentum_12_1']
    result.loc[result.feature_eligible, 'score_raw_X_no_fidelity'] = result.loc[result.feature_eligible, 'x_no_fidelity']
    for d in dates:
        mask = result.feature_eligible & result.decision_date.eq(d)
        prior = result[result.feature_eligible & result.target_return.notna() & result.exit_date.lt(pd.Timestamp(d))].copy()
        valid_dates = sorted(prior.decision_date.unique())
        if len(valid_dates) >= 8:
            prior['return_demeaned'] = prior.target_return - prior.groupby('decision_date').target_return.transform('mean')
            for m, features in (('B', B_COLS), ('fitted_X', ('x',)), ('B_plus_X', ALL_COLS)):
                beta = fit_ridge(prior, features)
                x = result.loc[mask, ['z_' + c for c in features]].to_numpy(float)
                result.loc[mask, 'score_' + m] = x @ beta
                fit_rows.append(dict(decision_date=d, model=m, training_dates=len(valid_dates),
                                     training_rows=len(prior), first_training_date=valid_dates[0],
                                     last_training_date=valid_dates[-1],
                                     latest_training_target_exit=prior.exit_date.max().date().isoformat(),
                                     features='|'.join(features), coefficients_json=json.dumps(beta.tolist())))
        for m in ('raw_X', 'momentum_12_1', 'B', 'fitted_X', 'B_plus_X', 'raw_X_no_fidelity'):
            values = result.loc[mask, 'score_' + m]
            if values.notna().any():
                valid = values.dropna()
                result.loc[valid.index, 'group_' + m] = group_of(valid).to_numpy()
    metrics = []
    cells = []
    sensitivity = []
    for d, group in result.groupby('decision_date', sort=True):
        for m in ('raw_X', 'momentum_12_1', 'B', 'fitted_X', 'B_plus_X'):
            row, _ = metric_date(group, m)
            if row:
                metrics.append(row)
        sensitivity_row, _ = metric_date(group, 'raw_X_no_fidelity')
        if sensitivity_row:
            sensitivity.append(sensitivity_row)
        eligible_d = group[group.score_B.notna() & group.score_B_plus_X.notna()]
        b = eligible_d.group_B.eq('upper')
        bx = eligible_d.group_B_plus_X.eq('upper')
        for label, sel in (('both', b & bx), ('B_plus_X_only', ~b & bx), ('B_only', b & ~bx), ('neither', ~b & ~bx)):
            subset = eligible_d[sel]
            known = subset[subset.target_return.notna()]
            cells.append(dict(decision_date=d, cell=label, formation_n=len(subset), observed_n=len(known),
                              unknown_n=len(subset)-len(known), holding_usd=float(subset.holding_usd.sum()),
                              observed_return=known.target_return.mean()))
    per_date = pd.DataFrame(metrics)
    cells = pd.DataFrame(cells)
    sensitivity = pd.DataFrame(sensitivity)
    model_summary, paired = summarize(per_date, dates)
    earlylate = {}
    for label, test in (('early_2020_2022', per_date.decision_date.le('2022-12-31')),
                        ('late_2023_2026', per_date.decision_date.ge('2023-01-01'))):
        earlylate[label] = {m: float(g.ic.mean()) if g.ic.notna().any() else None
                            for m, g in per_date[test].groupby('model')}
    influence = {}
    for m, g in per_date.groupby('model'):
        vals = g.set_index('decision_date').ic.dropna()
        if len(vals) > 1:
            leave = {d: float(vals.drop(index=d).mean()) for d in vals.index}
            base = float(vals.mean())
            influence[m] = dict(leave_one_range=[min(leave.values()), max(leave.values())],
                                most_influential_date=max(leave, key=lambda d: abs(leave[d]-base)))
    result.to_parquet(OUT / 'forecast-rows.parquet', index=False)
    per_date.to_csv(OUT / 'per-date-metrics.csv', index=False)
    cells.to_csv(OUT / 'four-cells.csv', index=False)
    sensitivity.to_csv(OUT / 'sensitivity-no-fidelity.csv', index=False)
    pd.DataFrame(fit_rows, columns=('decision_date', 'model', 'training_dates', 'training_rows',
                                   'first_training_date', 'last_training_date',
                                   'latest_training_target_exit', 'features', 'coefficients_json')).to_csv(OUT / 'fit-ledger.csv', index=False)
    summary = dict(stage='effects', effect_run_count=1, design_sha256=sha(DESIGN), events_sha256=sha(EVENTS),
                   formation_sha256=sha(OUT / 'formations.parquet'), date_count=len(dates),
                   model_summary=model_summary, paired_B_plus_X_minus_B=paired, early_late_ic=earlylate,
                   leave_one_quarter=influence, formation_count=len(result),
                   no_fidelity_sensitivity=dict(formation_dates=int(sensitivity.decision_date.nunique()) if len(sensitivity) else 0,
                                                ic_mean=float(sensitivity.ic.mean()) if len(sensitivity) and sensitivity.ic.notna().any() else None,
                                                signal_known_rows=int(result.score_raw_X_no_fidelity.notna().sum())),
                   target_status_counts=result.target_status.value_counts().to_dict(),
                   outputs_sha256={p.name: sha(p) for p in (OUT / 'forecast-rows.parquet', OUT / 'per-date-metrics.csv', OUT / 'four-cells.csv', OUT / 'sensitivity-no-fidelity.csv', OUT / 'fit-ledger.csv')})
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({'stage':'effects', 'formation_count':len(result), 'date_count':len(dates),
                      'target_status_counts':summary['target_status_counts']}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--synthetic', action='store_true')
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--effects', action='store_true')
    args = parser.parse_args()
    if args.synthetic:
        synthetic()
    elif args.prepare:
        prepare()
    else:
        effects()


if __name__ == '__main__':
    main()
