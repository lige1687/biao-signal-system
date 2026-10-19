#!/usr/bin/env python3
"""Frozen monthly reversal chain diagnostic; descriptive, not a trading backtest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.factor_lab.diagnostics import _cross_section_ic  # noqa: E402


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def checked(bound):
    p = Path(bound['path'])
    require(p.is_file() and sha(p) == bound['sha256'], f'input hash mismatch: {p}')
    return json.loads(p.read_text())


def rows(doc, fields):
    names = doc.get('fields')
    require(isinstance(names, list) and len(names) == len(set(names)) and set(fields) <= set(names),
            f'missing or duplicate fields: {fields}')
    for row in doc.get('data', []):
        require(isinstance(row, list) and len(row) == len(names), 'malformed row width')
        yield dict(zip(names, row))


def valid_date(value):
    require(isinstance(value, str) and len(value) == 10, f'invalid date: {value}')
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'invalid date: {value}') from exc
    require(d.isoformat() == value, f'noncanonical date: {value}')
    return value


def price(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and x > 0 else None


def month_steps():
    p = pd.period_range('2014-12', '2025-11', freq='M')
    require(len(p) == 132, 'formation month count')
    return p


def calendar_dates(doc):
    sessions = defaultdict(list)
    seen = set()
    previous = ''
    for r in rows(doc, {'calendar_date', 'is_trading_day'}):
        d = valid_date(r['calendar_date'])
        require(d not in seen and d > previous, f'calendar duplicate/unsorted: {d}')
        require(r['is_trading_day'] in ('0', '1'), f'invalid trading flag: {d}')
        seen.add(d)
        previous = d
        if r['is_trading_day'] == '1':
            sessions[d[:7]].append(d)
    needed = pd.period_range('2014-11', '2026-01', freq='M')
    require(all(sessions[str(m)] for m in needed), 'calendar missing required month')
    return sessions


def tie_weights(scores):
    """Each exact-score tie occupies its whole rank interval fractionally."""
    n = len(scores)
    require(n >= 5, 'fewer than five eligible names')
    order = np.argsort(np.asarray(scores), kind='stable')
    result = np.zeros((n, 5), dtype=float)
    pos = 0
    while pos < n:
        end = pos + 1
        while end < n and scores[order[end]] == scores[order[pos]]:
            end += 1
        for g in range(5):
            overlap = max(0.0, min(float(end), n * (g + 1) / 5) - max(float(pos), n * g / 5))
            result[order[pos:end], g] = overlap / (end - pos) * 5 / n
        pos = end
    require(np.allclose(result.sum(axis=0), 1) and np.allclose(result.sum(axis=1), 5/n),
            'tie weights do not conserve mass')
    return result


def qualification_at_exact_ends(by_date, prior_date, decision_date):
    if any(row.get('adjustflag', '2') != '2' for row in by_date.values()):
        return 'source_adjustment_metadata_conflict_quarantined'
    x, y = by_date.get(prior_date), by_date.get(decision_date)
    if x is None:
        return 'missing_prior_month_end'
    if y is None:
        return 'missing_current_month_end'
    if x['tradestatus'] != '1':
        return 'prior_month_end_not_trading'
    if y['tradestatus'] != '1':
        return 'current_month_end_not_trading'
    if y['isST'] != '0':
        return 'current_month_end_ST'
    p, q = price(x['close']), price(y['close'])
    if p is None:
        return 'invalid_prior_month_end_price'
    if q is None:
        return 'invalid_current_month_end_price'
    return None


def score_at_exact_ends(by_date, prior_date, decision_date):
    if qualification_at_exact_ends(by_date, prior_date, decision_date) is not None:
        return None
    return price(by_date[decision_date]['close'])/price(by_date[prior_date]['close']) - 1


def make_scores(records, sessions):
    out = []
    qualification = []
    valid_quotes = {}
    for code, by_date in records.items():
        valid_quotes[code] = [d for d, r in by_date.items()
                              if r['tradestatus'] == '1' and price(r['close']) is not None]
    for m in month_steps():
        prev = str(m - 1)
        cur = str(m)
        a, b = sessions[prev][-1], sessions[cur][-1]
        for code, by_date in records.items():
            reason = qualification_at_exact_ends(by_date, a, b)
            qualification.append({'formation_month': cur, 'code': code, 'prior_date': a,
                                  'decision_date': b, 'eligible': reason is None,
                                  'exclusion_reason': reason})
            if reason is not None:
                continue
            raw = score_at_exact_ends(by_date, a, b)
            q = price(by_date[b]['close'])
            alt = None
            span = None
            pos = bisect_right(valid_quotes[code], b) - 1
            if pos >= 21:
                prior21 = valid_quotes[code][pos - 21]
                alt = q / price(by_date[prior21]['close']) - 1
                span = (date.fromisoformat(b) - date.fromisoformat(prior21)).days
            out.append({'formation_month': cur, 'code': code, 'prior_month_end': a,
                        'current_month_end': b, 'prior_date': a, 'decision_date': b,
                        'eligible': True, 'score': raw, 'raw_score': raw, 'reversal_score': -raw,
                        'valid_quote_21_return': alt, 'valid_quote_21_span_days': span,
                        'calendar_vs_21_disagree': alt is not None and not math.isclose(raw, alt, abs_tol=1e-12)})
    return (pd.DataFrame(out).sort_values(['formation_month', 'code']).reset_index(drop=True),
            pd.DataFrame(qualification).sort_values(['formation_month', 'code']).reset_index(drop=True))


def make_labels(scores, records, sessions):
    out = []
    for r in scores.itertuples(index=False):
        m = pd.Period(r.formation_month, freq='M')
        start, end = sessions[str(m + 1)][0], sessions[str(m + 2)][0]
        x, y = records[r.code].get(start), records[r.code].get(end)
        a, b = price(x['close']) if x else None, price(y['close']) if y else None
        if x is None or y is None:
            reason = 'missing_exact_future_quote'
        elif a is None or b is None:
            reason = 'invalid_exact_future_price'
        else:
            reason = 'known_suspended_quote' if x['tradestatus'] != '1' or y['tradestatus'] != '1' else 'known_traded_quote'
        out.append({'formation_month': r.formation_month, 'code': r.code,
                    'decision_date': r.decision_date, 'entry_date': start, 'exit_date': end,
                    'return': b/a - 1 if a is not None and b is not None else None,
                    'missing_reason': reason if a is None or b is None else None,
                    'label_month': str(m + 1), 'future_start': start, 'future_end': end,
                    'future_return': b/a - 1 if a is not None and b is not None else None,
                    'future_reason': reason, 'future_start_status': x['tradestatus'] if x else None,
                    'future_end_status': y['tradestatus'] if y else None})
    return pd.DataFrame(out)


def ic_for(group, value_col='future_return'):
    clean = group[group[value_col].notna()]
    pair = pd.DataFrame({'observation_date': pd.to_datetime(clean['formation_month']),
                         'exclusion_reason': None, 'value': clean['raw_score'],
                         'target': clean[value_col]})
    if pair.empty:
        return None, 'fewer_than_min_pairs', 0
    lib = _cross_section_ic(pair, min_pairs=3)['periods'][0]
    independent = None
    if len(clean) >= 3 and clean['raw_score'].nunique() > 1 and clean[value_col].nunique() > 1:
        independent = clean['raw_score'].rank(method='average').corr(clean[value_col].rank(method='average'))
    if lib['ic'] is None:
        require(independent is None or pd.isna(independent), 'IC undefined mismatch')
    else:
        require(math.isclose(lib['ic'], independent, abs_tol=1e-12), 'IC implementation mismatch')
    return lib['ic'], lib['reason'], len(clean)


def block_interval(values, seed=20261020):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return None
    rng = np.random.default_rng(seed)
    draws = np.empty(2000)
    for i in range(len(draws)):
        starts = rng.integers(0, len(a), size=math.ceil(len(a)/12))
        idx = np.concatenate([(s + np.arange(12)) % len(a) for s in starts])[:len(a)]
        draws[i] = a[idx].mean()
    return [float(x) for x in np.quantile(draws, [.025, .975])]


def evaluate(scores, labels):
    panel = scores.merge(labels, on=['formation_month', 'code'], validate='one_to_one')
    parts, groups = [], []
    rng = np.random.default_rng(20261020)
    for month, frame in panel.groupby('formation_month', sort=True):
        frame = frame.copy()
        w = tie_weights(frame['raw_score'].tolist())
        for g in range(5):
            frame[f'group_{g+1}_weight'] = w[:, g]
        known = frame['future_return'].notna().to_numpy()
        ret = frame['future_return'].fillna(0).to_numpy(dtype=float)
        ic, reason, n = ic_for(frame)
        perm = frame.copy()
        perm.loc[known, 'permuted_return'] = rng.permutation(ret[known])
        pic, _, _ = ic_for(perm, 'permuted_return')
        parts.append({'formation_month': month, 'label_month': str(pd.Period(month, freq='M')+1),
                      'eligible': len(frame), 'known': int(known.sum()), 'missing': int((~known).sum()),
                      'suspended_quote_count': int((frame['future_reason'] == 'known_suspended_quote').sum()),
                      'ic_raw': ic, 'ic_reversal': -ic if ic is not None else None,
                      'ic_reason': reason, 'ic_pairs': n, 'ic_permuted': pic,
                      'all_observed_contribution': float(ret.sum()/len(frame)),
                      'all_unknown_weight': float((~known).sum()/len(frame))})
        for g in range(5):
            groups.append({'formation_month': month, 'label_month': str(pd.Period(month, freq='M')+1),
                           'group': g+1, 'eligible_weight': float(w[:, g].sum()),
                           'observed_contribution': float((w[:, g]*ret).sum()),
                           'unknown_weight': float(w[~known, g].sum()),
                           'known_weight': float(w[known, g].sum())})
        yield_frame = frame
        if month == panel['formation_month'].min():
            all_frames = [yield_frame]
        else:
            all_frames.append(yield_frame)
    return pd.concat(all_frames, ignore_index=True), pd.DataFrame(parts), pd.DataFrame(groups)


def summarize(panel, periodic, quintiles):
    vals = periodic['ic_raw'].dropna().to_numpy(float)
    year = periodic.copy()
    year['year'] = year['label_month'].str[:4]
    q = quintiles.pivot(index='formation_month', columns='group', values='observed_contribution')
    uq = quintiles.pivot(index='formation_month', columns='group', values='unknown_weight')
    year['low_minus_high_observed_contribution'] = year['formation_month'].map(q[1]-q[5])
    year['low_minus_high_unknown_weight'] = year['formation_month'].map(uq[1]-uq[5])
    subsets = {'2015-2019': year[year['year'].between('2015','2019')],
               '2020-2025': year[year['year'].between('2020','2025')]}
    def count_range(s):
        return {'min': int(s.min()), 'median': float(s.median()), 'max': int(s.max())}
    def period_summary(frame):
        return {'months': len(frame),
                'mean_ic': float(frame['ic_raw'].mean()) if frame['ic_raw'].notna().any() else None,
                'mean_all_observed_contribution': float(frame['all_observed_contribution'].mean()),
                'mean_all_unknown_weight': float(frame['all_unknown_weight'].mean()),
                'mean_low_minus_high_observed_contribution': float(frame['low_minus_high_observed_contribution'].mean()),
                'mean_low_minus_high_unknown_weight': float(frame['low_minus_high_unknown_weight'].mean())}
    return {'months': len(periodic), 'valid_ic_months': len(vals),
            'mean_ic_raw': float(vals.mean()) if len(vals) else None,
            'mean_ic_reversal': float(-vals.mean()) if len(vals) else None,
            'mean_ic_permuted': float(periodic['ic_permuted'].mean()) if periodic['ic_permuted'].notna().any() else None,
            'mean_ic_block12_95_interval': block_interval(vals),
            'yearly_mean_ic': {y: float(g['ic_raw'].mean()) if g['ic_raw'].notna().any() else None for y,g in year.groupby('year')},
            'yearly': {y: period_summary(g) for y,g in year.groupby('year')},
            'eras': {k: period_summary(v) for k,v in subsets.items()},
            'eligible_per_month': count_range(periodic['eligible']),
            'known_per_month': count_range(periodic['known']),
            'missing_per_month': count_range(periodic['missing']),
            'future_reasons': dict(Counter(panel['future_reason'])),
            'calendar_21_eligible': int(panel['valid_quote_21_return'].notna().sum()),
            'calendar_21_disagreements': int(panel['calendar_vs_21_disagree'].sum()),
            'group_mean_observed_contribution': {str(i): float(quintiles.loc[quintiles.group==i,'observed_contribution'].mean()) for i in range(1,6)},
            'group_mean_unknown_weight': {str(i): float(quintiles.loc[quintiles.group==i,'unknown_weight'].mean()) for i in range(1,6)},
            'low_minus_high_observed_contribution_mean': float((q[1]-q[5]).mean()),
            'low_minus_high_unknown_weight_mean': float((uq[1]-uq[5]).mean()),
            'all_mean_observed_contribution': float(periodic['all_observed_contribution'].mean()),
            'all_mean_unknown_weight': float(periodic['all_unknown_weight'].mean()),
            'interpretation': 'Descriptive monthly quotation proxy; missing outcomes retain unknown weight. No annualized or tradable-return claim.'}


def load_inputs(design):
    require(design['schema'] == 'classic-chain-diagnostic/1', 'wrong design schema')
    for name, bound_code in design['code_reuse'].items():
        p = Path(bound_code['path'])
        require(p.is_file() and sha(p) == bound_code['sha256'], f'code reuse hash mismatch: {name}')
    bound = design['inputs']['price_contract']
    contract = checked(bound)
    require(contract['schema'] == 'lowfreq-evaluator-contract/1' and len(contract['sources']) == 600,
            'price contract shape/source count')
    cohort = checked(contract['cohort'])
    all_codes = []
    for r in rows(cohort, {'code'}):
        all_codes.append(r['code'])
    require(len(all_codes) == 2595 and len(set(all_codes)) == 2595, 'cohort census identity')
    sessions = calendar_dates(checked(contract['calendar']))
    selected = [s['code'] for s in contract['sources']]
    expected = sorted(all_codes,
                      key=lambda code: (hashlib.sha256(f'lowfreq-20141231-v1|{code}'.encode()).hexdigest(), code))[:600]
    require(len(set(selected)) == 600 and set(selected) == set(expected), 'source code identity/selection')
    records = {}
    for source in contract['sources']:
        require(source.get('status') == 'ok' and source['request']['code'] == source['code']
                and source['request']['adjustflag'] == '2', f'source contract: {source["code"]}')
        doc = checked(source)
        require(doc.get('error_code') == '0', f'provider error: {source["code"]}')
        by_date = {}
        previous = ''
        for r in rows(doc, {'date','code','close','tradestatus','isST','adjustflag'}):
            d = valid_date(r['date'])
            require(d > previous and r['code'] == source['code'] and d not in by_date,
                    f'duplicate/unsorted/wrong code: {source["code"]} {d}')
            require(r['adjustflag'] in ('2','3') and r['tradestatus'] in ('0','1') and r['isST'] in ('0','1'),
                    f'invalid source flag: {source["code"]} {d}')
            previous = d
            by_date[d] = {k: r[k] for k in ('date', 'close', 'tradestatus', 'isST', 'adjustflag')}
        records[source['code']] = by_date
    return contract, sessions, records


def self_test():
    w = tie_weights([1, 1, 1, 2, 3])
    require(np.allclose(w.sum(axis=0), 1) and np.allclose(w[:3,0], [1/3]*3), 'hand tie')
    ranked = pd.DataFrame({'formation_month':['2020-01']*5,
                           'raw_score':[1.,1.,2.,3.,4.], 'future_return':[1.,1.,2.,3.,4.]})
    require(math.isclose(ic_for(ranked)[0], 1), 'hand tied rank IC')
    toy = pd.DataFrame({'formation_month':['2020-01']*5, 'code':list('abcde'),
                        'raw_score':[1.,2.,3.,4.,5.]})
    labels = pd.DataFrame({'formation_month':['2020-01']*5, 'code':list('abcde'),
                           'future_return':[.5,.4,None,.2,.1],
                           'future_reason':['known_traded_quote']*5})
    panel, p, q = evaluate(toy, labels)
    require(math.isclose(p.iloc[0].ic_raw, -1) and math.isclose(p.iloc[0].ic_reversal, 1), 'sign flip')
    require(math.isclose(q.loc[q.group==3,'unknown_weight'].iloc[0], 1), 'unknown mass')
    require(ic_for(panel.assign(raw_score=1.))[0] is None, 'constant score')
    quotes = {'2019-12-31': {'close':'10','tradestatus':'1','isST':'0'},
              '2020-01-31': {'close':'8','tradestatus':'1','isST':'0'},
              '2020-02-03': {'close':'9','tradestatus':'1','isST':'0'}}
    before = score_at_exact_ends(quotes, '2019-12-31', '2020-01-31')
    quotes['2020-02-03']['close'] = '1000'
    require(before == score_at_exact_ends(quotes, '2019-12-31', '2020-01-31'), 'future mutation altered scores')
    require(qualification_at_exact_ends(quotes, '2019-12-31', '2020-01-31') is None, 'eligible toy')
    require(qualification_at_exact_ends(quotes, '2019-12-31', '2020-03-31') == 'missing_current_month_end', 'missing endpoint reason')
    quotes['2020-01-31']['isST'] = '1'
    require(qualification_at_exact_ends(quotes, '2019-12-31', '2020-01-31') == 'current_month_end_ST', 'ST reason')
    print('SELF_TEST_OK hand_ties constant_ic sign_flip future_mutation unknown_weight')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--design', type=Path)
    ap.add_argument('--storage-plan', type=Path)
    args = ap.parse_args()
    if args.self_test:
        self_test(); return
    require(args.design and args.storage_plan, '--design and --storage-plan required')
    require(args.design.resolve() == HERE/'design.json', 'design path differs from frozen path')
    design = json.loads(args.design.read_text())
    contract, sessions, records = load_inputs(design)  # all bound input hashes before any statistics
    plan = json.loads(args.storage_plan.read_text())
    require(plan['task_id'] == 'personal-lowfreq-system-audit-20261018', 'wrong storage task')
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(ROOT, plan, plan['task_id'], plan['estimated_bytes'], plan['internal_metadata_bytes'])
    output = Path(plan['output'])/'classic-factor-chain-diagnostic-2026-10-20'
    require(not output.exists(), 'refuse existing result directory')
    scores, qualification = make_scores(records, sessions)
    labels = make_labels(scores, records, sessions)
    panel, periodic, quintiles = evaluate(scores, labels)
    summary = summarize(panel, periodic, quintiles)
    summary['qualification_reasons'] = {str(k):int(v) for k,v in qualification['exclusion_reason'].fillna('eligible').value_counts().items()}
    output.mkdir(parents=True, exist_ok=False)
    for name, frame in [('qualification',qualification),('scores',scores),('labels',labels),('panel',panel),('periodic',periodic),('quintiles',quintiles)]:
        frame.to_csv(output/f'{name}.csv', index=False)
    (output/'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n')
    manifest = {'design_sha256': sha(args.design), 'contract_sha256': sha(design['inputs']['price_contract']['path']),
                'cohort_sha256': contract['cohort']['sha256'], 'calendar_sha256': contract['calendar']['sha256'],
                'sources': {s['code']:s['sha256'] for s in contract['sources']},
                'reused_code_sha256': {k:v['sha256'] for k,v in design['code_reuse'].items()},
                'code_sha256': sha(__file__),
                'estimated_bytes': plan['estimated_bytes']}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'output':str(output), 'months':summary['months'], 'mean_ic_raw':summary['mean_ic_raw']}))


if __name__ == '__main__':
    main()
