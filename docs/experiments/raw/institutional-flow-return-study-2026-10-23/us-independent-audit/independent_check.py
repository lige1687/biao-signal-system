"""Independent arithmetic/time audit of saved four-fund effects, without model imports."""

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import plistlib
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from scipy.stats import rankdata


ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result')
PREP = BASE / 'us-prepared'
EFFECTS = BASE / 'us-effects/v2'
OUT = BASE / 'us-independent-audit'
PLAN = ROOT / 'storage-plan.json'
EVENTS = ROOT / 'us-price-qualification/events.json'
FUNDS = ('S000000856', 'S000006037', 'S000007112', 'S000011202')
BASELINE = ('momentum_12_1', 'last21', 'vol63', 'log_holding_usd',
            'share_parnassus', 'share_contrafund', 'share_magellan')
MODELS = {'B': BASELINE, 'fitted_X': ('x',), 'B_plus_X': ('x',) + BASELINE}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for block in iter(lambda: fh.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def same(a, b, atol=1e-9, rtol=1e-9):
    if pd.isna(a) and pd.isna(b):
        return True
    return np.isclose(float(a), float(b), atol=atol, rtol=rtol)


def assert_close(a, b, label, issues, atol=1e-9, rtol=1e-9):
    if not same(a, b, atol, rtol):
        issues.append(dict(check=label, saved=None if pd.isna(b) else float(b),
                           independent=None if pd.isna(a) else float(a)))


def strict_group(scores):
    values = np.asarray(scores, dtype=float)
    if len(values) < 2 or len(np.unique(values)) < 2:
        return np.repeat('middle', len(values))
    ranks = rankdata(values, method='average')
    pct = (ranks - 1) / (len(values) - 1)
    return np.where(pct <= 1 / 3, 'lower', np.where(pct >= 2 / 3, 'upper', 'middle'))


def spearman(x, y):
    if len(x) < 10:
        return np.nan
    xr = rankdata(np.asarray(x, float), method='average')
    yr = rankdata(np.asarray(y, float), method='average')
    if np.std(xr) == 0 or np.std(yr) == 0:
        return np.nan
    return float(np.corrcoef(xr, yr)[0, 1])


def weighted_lstsq(frame, features):
    cols = ['z_' + c for c in features]
    x = frame[cols].to_numpy(float)
    y = frame.target_return.to_numpy(float)
    groups = frame.groupby('decision_date').target_return.transform('mean').to_numpy(float)
    sizes = frame.groupby('decision_date').decision_date.transform('size').to_numpy(float)
    weights = 1 / np.sqrt(sizes)
    # Augmented least squares is independent of the candidate's normal equations.
    lhs = np.vstack((x * weights[:, None], np.eye(len(features))))
    rhs = np.concatenate(((y - groups) * weights, np.zeros(len(features))))
    return np.linalg.lstsq(lhs, rhs, rcond=None)[0]


def score_and_group_checks(rows, issues):
    checked = collections.Counter()
    eligible = rows[rows.feature_eligible].copy()
    for decision, slice_ in eligible.groupby('decision_date', sort=True):
        for col in ('x',) + BASELINE:
            vals = slice_[col].to_numpy(float)
            std = np.std(vals, ddof=0)
            expected = (vals - np.mean(vals)) / std if std > 0 else np.zeros(len(vals))
            for i, (a, b) in enumerate(zip(expected, slice_['z_' + col])):
                assert_close(a, b, f'z_{col}:{decision}:{i}', issues)
                checked['z_values'] += 1
        for model, feature in (('raw_X', 'x'), ('momentum_12_1', 'momentum_12_1'),
                               ('raw_X_no_fidelity', 'x_no_fidelity')):
            for idx, value in slice_[feature].items():
                assert_close(value, rows.at[idx, 'score_' + model], f'score_{model}:{idx}', issues)
                checked['raw_scores'] += 1
        for model in ('raw_X', 'momentum_12_1', 'B', 'fitted_X', 'B_plus_X', 'raw_X_no_fidelity'):
            active = slice_[slice_['score_' + model].notna()]
            expected = strict_group(active['score_' + model].to_numpy(float))
            for idx, group in zip(active.index, expected):
                if rows.at[idx, 'group_' + model] != group:
                    issues.append(dict(check=f'group_{model}:{idx}', saved=rows.at[idx, 'group_' + model], independent=group))
                checked['groups'] += 1
            inactive = slice_[slice_['score_' + model].isna()]
            for idx in inactive.index:
                if pd.notna(rows.at[idx, 'group_' + model]):
                    issues.append(dict(check=f'unknown_group_{model}:{idx}', saved=rows.at[idx, 'group_' + model], independent=None))
    return checked


def pressure_checks(rows, issues):
    first = json.loads((PREP / 'qualification.json').read_text())
    second = json.loads((PREP / 'format-v2/qualification.json').read_text())
    flows_path = PREP / 'fund-flow-selection.csv'
    holding_path = PREP / 'format-v2/lag-holdings-identities.parquet'
    if sha(flows_path) != first['output_sha256'][flows_path.name]:
        raise ValueError('fund-flow input changed')
    if sha(holding_path) != second['repaired_lag_holdings_sha256']:
        raise ValueError('lag holding identity input changed')
    flows = pd.read_csv(flows_path, dtype={'series': str})
    holdings = pd.read_parquet(holding_path)
    if len(holdings) != second['row_count'] or len(flows) != 104:
        raise ValueError('prepared input row counts changed')
    rate = {(r.decision_date, r.series): float(r.redemption_pressure)
            for r in flows.itertuples(index=False) if r.status == 'selected'}
    by_key = rows.set_index(['decision_date', 'cusip'], verify_integrity=True)
    checked = collections.Counter()
    for key, g in holdings.groupby(['decision_date', 'cusip'], sort=True):
        if key not in by_key.index:
            issues.append(dict(check=f'missing_formation:{key}'))
            continue
        amounts = g.groupby('series').holding_value_usd.apply(lambda s: sum(map(float, s)))
        total = float(amounts.sum())
        expected = sum(float(v) * rate[(key[0], f)] for f, v in amounts.items()) / total
        retained = {f: v for f, v in amounts.items() if f in (FUNDS[0], FUNDS[3])}
        non_fidelity = (sum(float(v) * rate[(key[0], f)] for f, v in retained.items()) /
                        sum(map(float, retained.values()))) if retained else np.nan
        saved = by_key.loc[key]
        for label, a, b in (('x', expected, saved.x), ('x_no_fidelity', non_fidelity, saved.x_no_fidelity),
                            ('holding_usd', total, saved.holding_usd), ('log_holding_usd', math.log(total), saved.log_holding_usd),
                            ('share_parnassus', float(amounts.get(FUNDS[0], 0))/total, saved.share_parnassus),
                            ('share_contrafund', float(amounts.get(FUNDS[1], 0))/total, saved.share_contrafund),
                            ('share_magellan', float(amounts.get(FUNDS[2], 0))/total, saved.share_magellan)):
            assert_close(a, b, f'{label}:{key}', issues)
            checked[label] += 1
    if len(by_key) != holdings.groupby(['decision_date', 'cusip']).ngroups:
        issues.append(dict(check='formation_membership_mismatch', saved=len(by_key), independent=holdings.groupby(['decision_date', 'cusip']).ngroups))
    return checked


def training_checks(rows, ledger, issues):
    checked = collections.Counter()
    listed = {(r.decision_date, r.model): r for r in ledger.itertuples(index=False)}
    dates = sorted(rows.decision_date.unique())
    for decision in dates:
        d = pd.Timestamp(decision)
        prior = rows[(rows.feature_eligible) & rows.target_return.notna() & (rows.exit_date < d)].copy()
        mature = sorted(prior.decision_date.unique())
        active = rows[(rows.feature_eligible) & rows.decision_date.eq(decision)]
        for model, features in MODELS.items():
            saved_ledger = listed.get((decision, model))
            if len(mature) < 8:
                if saved_ledger is not None or active['score_' + model].notna().any():
                    issues.append(dict(check=f'premature_fit:{decision}:{model}'))
                continue
            if saved_ledger is None:
                issues.append(dict(check=f'missing_fit:{decision}:{model}'))
                continue
            if not (prior.exit_date < d).all():
                issues.append(dict(check=f'lookahead:{decision}:{model}'))
            for label, a, b in (('training_dates', len(mature), saved_ledger.training_dates),
                                ('training_rows', len(prior), saved_ledger.training_rows)):
                if a != b:
                    issues.append(dict(check=f'{label}:{decision}:{model}', saved=b, independent=a))
            latest_exit = prior.exit_date.max().date().isoformat()
            if latest_exit != saved_ledger.latest_training_target_exit:
                issues.append(dict(check=f'latest_exit:{decision}:{model}', saved=saved_ledger.latest_training_target_exit, independent=latest_exit))
            independent_beta = weighted_lstsq(prior, features)
            saved_beta = np.asarray(json.loads(saved_ledger.coefficients_json), float)
            if len(independent_beta) != len(saved_beta):
                issues.append(dict(check=f'beta_length:{decision}:{model}'))
                continue
            for i, (a, b) in enumerate(zip(independent_beta, saved_beta)):
                assert_close(a, b, f'beta:{decision}:{model}:{i}', issues, atol=1e-8, rtol=1e-8)
                checked['betas'] += 1
            forecast = active[['z_' + c for c in features]].to_numpy(float) @ independent_beta
            for idx, a in zip(active.index, forecast):
                assert_close(a, rows.at[idx, 'score_' + model], f'forecast:{decision}:{model}:{idx}', issues, atol=1e-8, rtol=1e-8)
                checked['forecasts'] += 1
            checked['fits'] += 1
    return checked


def metric_row(group, model):
    scored = group[group['score_' + model].notna()]
    observed = scored[scored.target_return.notna()]
    upper_all = scored[scored['group_' + model].eq('upper')]
    upper = upper_all[upper_all.target_return.notna()]
    lower = observed[observed['group_' + model].eq('lower')]
    mean = lambda frame: float(frame.target_return.mean()) if len(frame) else np.nan
    median = lambda frame: float(frame.target_return.median()) if len(frame) else np.nan
    pos = lambda frame: float((frame.target_return > 0).mean()) if len(frame) else np.nan
    all_mean = mean(observed)
    upper_mean = mean(upper)
    result = dict(formation_n=len(group), feature_n=len(scored), outcome_observed_n=len(observed),
                  outcome_unknown_n=len(scored) - len(observed), feature_holding_usd=float(scored.holding_usd.sum()),
                  ic=spearman(observed['score_' + model], observed.target_return),
                  upper_n=len(upper_all), upper_observed_n=len(upper), upper_unknown_n=len(upper_all)-len(upper),
                  upper_unknown_fraction=(len(upper_all)-len(upper))/len(upper_all) if len(upper_all) else np.nan,
                  upper_holding_usd=float(upper_all.holding_usd.sum()), upper_observed_return=upper_mean,
                  lower_observed_return=mean(lower), whole_observed_return=all_mean,
                  upper_observed_median=median(upper), lower_observed_median=median(lower),
                  whole_observed_median=median(observed), upper_positive_fraction=pos(upper),
                  lower_positive_fraction=pos(lower), whole_positive_fraction=pos(observed),
                  upper_minus_whole=upper_mean-all_mean if len(upper) and len(observed) else np.nan,
                  upper_after_20bp=upper_mean-0.002, whole_after_20bp=all_mean-0.002,
                  upper_after_50bp=upper_mean-0.005, whole_after_50bp=all_mean-0.005)
    return result


def metric_checks(rows, per_date, cells, sensitivity, summary, issues):
    checked = collections.Counter()
    by_metric = per_date.set_index(['decision_date', 'model'], verify_integrity=True)
    by_sens = sensitivity.set_index('decision_date', verify_integrity=True)
    by_cell = cells.set_index(['decision_date', 'cell'], verify_integrity=True)
    expected_metric_keys = set()
    for d, g in rows.groupby('decision_date', sort=True):
        for model in ('raw_X', 'momentum_12_1', 'B', 'fitted_X', 'B_plus_X', 'raw_X_no_fidelity'):
            if not g['score_' + model].notna().any():
                continue
            calc = metric_row(g, model)
            saved = by_sens.loc[d] if model == 'raw_X_no_fidelity' and d in by_sens.index else (by_metric.loc[(d, model)] if (d, model) in by_metric.index else None)
            if saved is None:
                issues.append(dict(check=f'missing_metric:{d}:{model}'))
                continue
            if model != 'raw_X_no_fidelity':
                expected_metric_keys.add((d, model))
            for k, v in calc.items():
                assert_close(v, saved[k], f'metric:{d}:{model}:{k}', issues, atol=1e-8, rtol=1e-8)
                checked['metric_cells'] += 1
        eligible = g[g.score_B.notna() & g.score_B_plus_X.notna()]
        b = eligible.group_B.eq('upper')
        bx = eligible.group_B_plus_X.eq('upper')
        for label, mask in (('both', b & bx), ('B_plus_X_only', ~b & bx), ('B_only', b & ~bx), ('neither', ~b & ~bx)):
            subset = eligible[mask]
            known = subset[subset.target_return.notna()]
            calc = dict(formation_n=len(subset), observed_n=len(known), unknown_n=len(subset)-len(known),
                        holding_usd=float(subset.holding_usd.sum()), observed_return=float(known.target_return.mean()) if len(known) else np.nan)
            saved = by_cell.loc[(d, label)] if (d, label) in by_cell.index else None
            if saved is None:
                issues.append(dict(check=f'missing_four_cell:{d}:{label}'))
                continue
            for k, v in calc.items():
                assert_close(v, saved[k], f'four_cell:{d}:{label}:{k}', issues, atol=1e-8, rtol=1e-8)
                checked['four_cell_fields'] += 1
    if expected_metric_keys != set(by_metric.index):
        issues.append(dict(check='per_date_row_set', saved=len(by_metric), independent=len(expected_metric_keys)))
    wide = per_date.pivot(index='decision_date', columns='model', values=['ic', 'upper_observed_return'])
    for field in ('ic', 'upper_observed_return'):
        diff = wide[field]['B_plus_X'] - wide[field]['B']
        saved = summary['paired_B_plus_X_minus_B'][field]
        if int(diff.notna().sum()) != saved['n']:
            issues.append(dict(check=f'paired_n:{field}', saved=saved['n'], independent=int(diff.notna().sum())))
        assert_close(diff.mean(), saved['mean'], f'paired_mean:{field}', issues)
        checked['paired_increments'] += 1
    common = rows[rows.feature_eligible]
    if not common.score_B.notna().equals(common.score_B_plus_X.notna()):
        issues.append(dict(check='B_BplusX_common_feature_rows'))
    if any(rows.loc[rows.feature_eligible & rows.target_return.isna(), 'group_raw_X'].isna()):
        issues.append(dict(check='future_unknown_dropped_from_formation_ranks'))
    return checked


def price_endpoint_sample(rows, issues, count=6):
    event = json.loads(EVENTS.read_text())
    source = Path(event['source_root']) / 'prices.parquet'
    observed = rows[rows.target_status.eq('observed_candidate') & rows.target_return.notna() & rows.ticker.notna()]
    if observed.empty:
        return []
    indices = np.linspace(0, len(observed)-1, min(count, len(observed)), dtype=int)
    selected = observed.iloc[indices]
    need = {(str(r.ticker), pd.Timestamp(date).date()) for r in selected.itertuples(index=False)
            for date in (r.entry_date, r.exit_date)}
    tickers = pa.array(sorted({t for t, _ in need}), type=pa.large_string())
    dates = pa.array([dt.datetime.combine(d, dt.time()) for d in sorted({d for _, d in need})],
                     type=pa.timestamp('us'))
    found = {}
    pf = pq.ParquetFile(source)
    for batch in pf.iter_batches(batch_size=131072, columns=['ticker', 'date', 'adj_close', 'volume', 'source']):
        ts = batch.column(batch.schema.get_field_index('ticker'))
        ds = batch.column(batch.schema.get_field_index('date'))
        sub = batch.filter(pc.and_(pc.is_in(ts, value_set=tickers), pc.is_in(ds, value_set=dates)))
        for x in sub.to_pylist():
            key = (x['ticker'], x['date'].date() if hasattr(x['date'], 'date') else x['date'])
            if key in need:
                if key in found:
                    issues.append(dict(check=f'duplicate_source_price:{key}'))
                found[key] = x
    sample = []
    for r in selected.itertuples(index=False):
        entry = (str(r.ticker), pd.Timestamp(r.entry_date).date())
        exit_ = (str(r.ticker), pd.Timestamp(r.exit_date).date())
        a, b = found.get(entry), found.get(exit_)
        if not a or not b:
            issues.append(dict(check=f'missing_source_endpoint:{r.decision_date}:{r.cusip}'))
            continue
        independent = float(b['adj_close']) / float(a['adj_close']) - 1
        assert_close(independent, r.target_return, f'source_return:{r.decision_date}:{r.cusip}', issues)
        sample.append(dict(decision_date=r.decision_date, cusip=r.cusip, ticker=r.ticker,
                           entry=str(entry[1]), exit=str(exit_[1]), entry_source=a['source'], exit_source=b['source'],
                           entry_adj_close=a['adj_close'], exit_adj_close=b['adj_close'],
                           saved_target_return=r.target_return, independent_target_return=independent))
    return sample


def guard_output():
    plan = json.loads(PLAN.read_text())
    mount = Path(plan['external_mount'])
    if OUT.parent.resolve() != Path(plan['output']).resolve():
        raise ValueError('output not under planned result')
    info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', str(mount)]))
    if mount.stat().st_dev != plan['external_device'] or info.get('VolumeUUID', '').upper() != plan['external_uuid'].upper():
        raise ValueError('external volume identity mismatch')
    if shutil.disk_usage(mount).free <= plan['external_reserve_bytes']:
        raise ValueError('external volume below reserve')
    if shutil.disk_usage(ROOT).free <= plan['internal_reserve_bytes']:
        raise ValueError('internal volume below reserve')
    if (OUT / 'audit.json').exists():
        raise ValueError('audit output exists; inspect before rerun')
    if (Path(__file__).parent / 'findings.md').exists():
        raise ValueError('local findings exist; inspect before rerun')


def audit():
    guard_output()
    summary_path = EFFECTS / 'summary.json'
    summary = json.loads(summary_path.read_text())
    inputs = {name: EFFECTS / name for name in summary['outputs_sha256']}
    for name, path in inputs.items():
        if sha(path) != summary['outputs_sha256'][name]:
            raise ValueError(f'candidate output hash mismatch: {name}')
    forms = pd.read_parquet(EFFECTS / 'formations.parquet')
    rows = pd.read_parquet(EFFECTS / 'forecast-rows.parquet')
    ledger = pd.read_csv(EFFECTS / 'fit-ledger.csv')
    per_date = pd.read_csv(EFFECTS / 'per-date-metrics.csv')
    cells = pd.read_csv(EFFECTS / 'four-cells.csv')
    sensitivity = pd.read_csv(EFFECTS / 'sensitivity-no-fidelity.csv')
    keys = ['decision_date', 'cusip']
    issues = []
    if forms.duplicated(keys).any() or rows.duplicated(keys).any():
        raise ValueError('duplicate formation key')
    if set(map(tuple, forms[keys].to_numpy())) != set(map(tuple, rows[keys].to_numpy())):
        issues.append(dict(check='formation_membership_changed_with_future_outcomes'))
    count = collections.Counter()
    count.update(pressure_checks(rows, issues))
    count.update(score_and_group_checks(rows, issues))
    count.update(training_checks(rows, ledger, issues))
    count.update(metric_checks(rows, per_date, cells, sensitivity, summary, issues))
    samples = price_endpoint_sample(rows, issues)
    receipt = dict(status='passed' if not issues else 'discrepancy', discrepancy_count=len(issues),
                   discrepancies=issues[:100], discrepancy_overflow=max(0, len(issues)-100),
                   checks=dict(count), source_endpoint_samples=samples,
                   candidate_summary_sha256=sha(summary_path),
                   candidate_output_sha256=summary['outputs_sha256'],
                   prepared_flow_sha256=sha(PREP / 'fund-flow-selection.csv'),
                   prepared_holding_sha256=sha(PREP / 'format-v2/lag-holdings-identities.parquet'),
                   price_source_declared_sha256=json.loads(EVENTS.read_text())['source_sha256']['prices.parquet'],
                   script_sha256=sha(__file__))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False, default=str))
    lines = ['# 美国四基金效果结果独立核对（2026-10-23）', '',
             f"结果：{receipt['status']}；发现差异 {len(issues)} 项。", '',
             '核对范围：从已保存的四基金申报资金流与期初持仓重算原始分数及基金构成；独立解带日期权重和固定惩罚的拟合；逐季度核对排名、分组、相关性、收益分组和两方法差额；从原价格分区抽查未来价格两端点。',
             '', f"逐项核对次数：{dict(count)}。", '',
             f"价格端点抽查：{len(samples)} 条，原始价格和计算值详见外盘 audit.json。", '',
             '这份核对验证保存数字是否按冻结定义计算；不提供新的收益实验、因果判断或交易授权。']
    if issues:
        lines += ['', '差异前 20 项：', ''] + [f"- `{x['check']}`：保存值 {x.get('saved')}，独立值 {x.get('independent')}" for x in issues[:20]]
    (Path(__file__).parent / 'findings.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'discrepancy_count', 'checks')}, ensure_ascii=False))


def synthetic():
    assert np.isclose((3*0.2 + 1*0)/4, 0.15)
    assert list(strict_group([1, 1, 1, 2, 3, 4])).count('lower') == 3
    assert list(strict_group([1, 1, 1])).count('middle') == 3
    assert np.isclose(spearman(list(range(10)), list(reversed(range(10)))), -1)
    t = pd.DataFrame({'decision_date': ['a']*4 + ['b']*2,
                      'target_return': [2., 0., 2., 0., 3., 1.],
                      'z_x': [1., -1., 1., -1., 2., -2.]})
    assert np.allclose(weighted_lstsq(t, ('x',)), [0.5])  # each date has unit weight; penalty is 1
    assert pd.Timestamp('2025-04-01') < pd.Timestamp('2025-06-30')
    assert not (pd.Timestamp('2025-07-01') < pd.Timestamp('2025-06-30'))
    print('independent audit synthetic checks passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--synthetic', action='store_true')
    p.add_argument('--audit', action='store_true')
    args = p.parse_args()
    if args.synthetic:
        synthetic()
    elif args.audit:
        audit()
    else:
        p.error('select --synthetic or --audit')
