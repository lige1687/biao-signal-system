"""Controller stdlib reconstruction; never imports the executor or its labels."""
import csv
import datetime as dt
import io
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / 'executor/run-01'
START = dt.date(2012, 6, 11)
END = dt.date(2019, 10, 4)
BASE = ['r20', 'r63', 'dma200', 'dd252', 'rv20']
MODELS = dict(I=[], E=['e'], T=['c'], EQ=['e', 'eq'], B=BASE,
              BE=BASE+['e'], BT=BASE+['c'], BEQ=BASE+['e', 'eq'])
PAIRS = [(m, b) for b in ['B', 'I'] for m in MODELS if m != b] + [('BEQ', 'BE'), ('EQ', 'E')]
max_value_error = max_beta_error = max_prediction_error = 0.0


def approx(a, b, tol=2e-8):
    global max_value_error
    err = abs(float(a) - float(b))
    max_value_error = max(max_value_error, err)
    assert err <= tol * max(1, abs(float(b))), (a, b, err)


def quantile(values, q):
    v = sorted(values)
    z = (len(v)-1)*q
    k = math.floor(z)
    return v[k] + (v[min(k+1, len(v)-1)]-v[k])*(z-k)


def solve(matrix, rhs):
    mat = [list(row)+[v] for row, v in zip(matrix, rhs)]
    n = len(rhs)
    for k in range(n):
        pivot = max(range(k, n), key=lambda j: abs(mat[j][k]))
        mat[k], mat[pivot] = mat[pivot], mat[k]
        assert abs(mat[k][k]) > 1e-10, ('independent rank check', k)
        div = mat[k][k]
        mat[k] = [v/div for v in mat[k]]
        for j in range(n):
            if j != k:
                div = mat[j][k]
                mat[j] = [v-div*w for v, w in zip(mat[j], mat[k])]
    return [row[-1] for row in mat]


def original_product(product):
    text = (HERE / f'inputs/{product}pc.csv').read_text(encoding='latin1')
    assert f'PRODUCT: {product.upper()}' in text.splitlines()[1]
    return {dt.datetime.strptime(r['DATE'], '%m/%d/%Y').date(): float(r['P/C Ratio'])
            for r in csv.DictReader(io.StringIO('\n'.join(text.splitlines()[2:])))}


def read_rows(path):
    return list(csv.DictReader(path.open()))


def checked_score(rows, stored, model_names=MODELS):
    assert len(rows) == stored['n']
    losses = {}
    for model in model_names:
        key = 'pred_'+model
        valid = [r for r in rows if r[key] != '']
        assert len(valid) == stored['estimable_prediction_counts'][model]
        if len(valid) != len(rows):
            assert stored['mse'][model] is None
            continue
        losses[model] = sum((float(r['y'])-float(r[key]))**2 for r in rows)/len(rows)
        approx(losses[model], stored['mse'][model])
        approx(math.sqrt(losses[model]), stored['rmse'][model])
        negative = sum(float(r[key]) < 0 for r in rows)
        assert negative == stored['negative_prediction'][model]['negative_n']
        approx(negative/len(rows), stored['negative_prediction'][model]['share'])
    for m, b in PAIRS:
        name = m+'_vs_'+b
        if m in losses and b in losses:
            approx(100*(1-losses[m]/losses[b]), stored['improvement_pct'][name])
            approx(len(rows)*(losses[b]-losses[m]), stored['squared_error_reduction_sum'][name], tol=2e-7)
    return losses


def main():
    global max_beta_error, max_prediction_error
    prices = read_rows(HERE / 'inputs/px_SPY.csv')
    dates = [dt.date.fromisoformat(r['Date']) for r in prices]
    close = [float(r['Close']) for r in prices]
    assert dates == sorted(set(dates)) and all(math.isfinite(c) and c > 0 for c in close)
    positions = dict(zip(dates, range(len(dates))))
    equity, total = original_product('equity'), original_product('total')
    candidates = sorted(set(equity) & set(total))
    expected = {}
    for date in candidates:
        i = positions[date]+2
        if date < START or date > END or i < 251 or i+21 >= len(dates) or dates[i+21] > END:
            continue
        past_returns = [close[k]/close[k-1]-1 for k in range(i-19, i+1)]
        mean_return = sum(past_returns)/20
        path = close[i+1:i+22]
        peak = path[0]
        mdd = 0.0
        for price in path:
            peak = max(peak, price)
            mdd = max(mdd, 100*(1-price/peak))
        expected[date.isoformat()] = dict(source_date=date, t=dates[i], target_start=dates[i+1],
            target_end=dates[i+21], e=equity[date], c=total[date], eq=int(equity[date] > 1),
            r20=100*(close[i]/close[i-20]-1), r63=100*(close[i]/close[i-63]-1),
            dma200=100*(close[i]/(sum(close[i-199:i+1])/200)-1),
            dd252=100*(close[i]/max(close[i-251:i+1])-1),
            rv20=100*math.sqrt(sum((v-mean_return)**2 for v in past_returns)/19)*math.sqrt(20),
            y_return=100*(path[-1]/path[0]-1), y_mdd=mdd,
            source_quote_index=positions[date], t_index=i, target_start_index=i+1, target_end_index=i+21)
    obs = read_rows(RUN / 'observations.csv')
    assert len(obs) == len(candidates)
    assert {r['source_date'][:10] for r in obs} == {d.isoformat() for d in candidates}
    eligible = [r for r in obs if r['eligible'].lower() in ('true', '1')]
    assert {r['source_date'][:10] for r in eligible} == set(expected)
    for r in eligible:
        ex = expected[r['source_date'][:10]]
        for col in ['t', 'target_start', 'target_end']:
            assert r[col][:10] == ex[col].isoformat()
        for col in ['e', 'c', 'eq', 'y_return', 'y_mdd', *BASE,
                    'source_quote_index', 't_index', 'target_start_index', 'target_end_index']:
            approx(r[col], ex[col])
        assert r['exclusion'] == ''
    results = json.loads((RUN / 'results.json').read_text())
    root_metrics, block_checks = {}, {}
    fit_count = 0
    for target, ycol in [('window_mdd20', 'y_mdd'), ('forward_return20', 'y_return')]:
        pred = read_rows(RUN / f'predictions-{target}.csv')
        eval_expected = {k: r for k, r in expected.items() if 2015 <= r['t'].year <= 2019}
        assert {r['source_date'][:10] for r in pred} == set(eval_expected)
        for r in pred:
            approx(r['y'], expected[r['source_date'][:10]][ycol])
        fits = json.loads((RUN / f'fits-{target}.json').read_text())
        assert len(fits) == 5*len(MODELS)
        assert {(int(f['year']), f['model']) for f in fits} == {(y, m) for y in range(2015, 2020) for m in MODELS}
        for f in fits:
            year = int(f['year'])
            boundary = dt.date(year, 1, 1)
            train = [r for r in expected.values() if r['t'] < boundary and r['target_end'] < boundary]
            keys = f['features']
            assert keys == MODELS[f['model']]
            assert len(train) >= 400 and len(train) == f['train_rows']
            assert max(r['target_end'] for r in train).isoformat() == f['train_label_end_max'][:10]
            assert sum(r['eq'] for r in train) == f['train_extreme_rows']
            means = {k: sum(r[k] for r in train)/len(train) for k in keys}
            scales = {k: math.sqrt(sum((r[k]-means[k])**2 for r in train)/len(train)) for k in keys}
            for j, k in enumerate(keys):
                approx(means[k], f['mean'][j]); approx(scales[k], f['scale'][j])
            if f['status'] != 'estimable':
                assert f['model'] in ['EQ', 'BEQ']
                assert f['beta'] is None
                continue
            dim = len(keys)+1
            matrix = [[0.0]*dim for _ in range(dim)]
            rhs = [0.0]*dim
            for r in train:
                x = [1.0]+[(r[k]-means[k])/scales[k] for k in keys]
                for j in range(dim):
                    rhs[j] += x[j]*r[ycol]
                    for k in range(dim): matrix[j][k] += x[j]*x[k]
            beta = solve(matrix, rhs)
            err = max(abs(a-b) for a, b in zip(beta, f['beta']))
            max_beta_error = max(max_beta_error, err)
            assert err < 1e-7, (target, year, f['model'], err)
            for r in pred:
                ex = expected[r['source_date'][:10]]
                if ex['t'].year != year: continue
                estimate = beta[0]+sum(beta[j+1]*(ex[k]-means[k])/scales[k] for j, k in enumerate(keys))
                error = abs(estimate-float(r['pred_'+f['model']]))
                max_prediction_error = max(max_prediction_error, error)
                assert error < 1e-6, (target, year, f['model'], error)
            fit_count += 1
        result = results['targets'][target]
        mse = checked_score(pred, result['overall'])
        for year in range(2015, 2020):
            rows = [r for r in pred if expected[r['source_date'][:10]]['t'].year == year]
            checked_score(rows, result['annual'][str(year)])
            others = [r for r in pred if expected[r['source_date'][:10]]['t'].year != year]
            checked_score(others, result['remove_year_no_refit'][str(year)])
        for label, years in [('2015-2016', {2015, 2016}), ('2017-2019', {2017, 2018, 2019})]:
            checked_score([r for r in pred if expected[r['source_date'][:10]]['t'].year in years], result['bands'][label])
        for label, flag in [('equity_gt1', 1), ('equity_le1', 0)]:
            group = [r for r in pred if expected[r['source_date'][:10]]['eq'] == flag]
            checked_score(group, result['group_errors'][label])
            raw = result['raw_equity_groups'][label]
            assert len(group) == raw['mature_eligible_n']
            returns = [float(r['y_return']) for r in group]
            risks = [float(r['y_mdd']) for r in group]
            approx(sum(returns)/len(group), raw['return_mean'])
            approx(statistics.median(returns), raw['return_median'])
            approx(sum(r > 0 for r in returns)/len(group), raw['return_up_share'])
            approx(sum(risks)/len(group), raw['mdd_mean'])
            approx(statistics.median(risks), raw['mdd_median'])
        checked_score([r for r in pred if expected[r['source_date'][:10]]['eq'] == 0], result['drop_equity_gt1_no_refit'])
        draws = read_rows(RUN / f'draws-{target}.csv')
        assert len(draws) == 2000
        for index in [0, 999, 1999]:
            row = draws[index]
            starts = json.loads(row['block_starts'])
            assert all(0 <= i <= len(pred)-126 for i in starts)
            indices = [i+j for i in starts for j in range(126)][:len(pred)]
            assert len(indices) == len(pred)
            for model in mse:
                loss = sum((float(pred[i]['y'])-float(pred[i]['pred_'+model]))**2 for i in indices)/len(indices)
                approx(loss, row['mse_'+model])
            for m, b in PAIRS:
                if m in mse and b in mse:
                    approx(100*(1-float(row['mse_'+m])/float(row['mse_'+b])), row['improvement_'+m+'_vs_'+b])
        intervals = {}
        for m, b in PAIRS:
            name = m+'_vs_'+b
            saved = result['paired_block_intervals'][name]
            if m not in mse or b not in mse:
                assert saved['status'] == 'not_estimable'
                continue
            values = [float(d['improvement_'+name]) for d in draws]
            low, high = quantile(values, .025), quantile(values, .975)
            approx(low, saved['p2_5']); approx(high, saved['p97_5'])
            intervals[name] = [low, high]
        root_metrics[target] = dict(rows=len(pred), rmse_pp={m: math.sqrt(v) for m, v in mse.items()},
            improvement_pct=result['overall']['improvement_pct'],
            negative_predictions=result['overall']['negative_prediction'])
        block_checks[target] = dict(draws=2000, reconstructed=[0, 999, 1999], interval_endpoints=intervals)
    assert fit_count == results['estimable_fits']
    out = dict(passed=True, no_executor_imports=True, independently_verified_fit_count=fit_count,
               complete_common_population_verified=True, eligible_rows=len(expected),
               all_values_max_error=max_value_error, normal_equation_beta_max_error=max_beta_error,
               predictions_max_error=max_prediction_error, headline_recalculation=root_metrics,
               block_checks=block_checks,
               scope='Independent raw products/prices/time/labels, all fits and headline/annual/fixed-band/delete-year/delete-extreme/group scores. Three draws per target reconstructed; every saved interval endpoint checked. Same historical evidence, not new validation.')
    (HERE / 'independent-review.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ['headline_recalculation', 'block_checks']}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        index = 1
        while (HERE / f'independent-failure-{index:02}.json').exists(): index += 1
        (HERE / f'independent-failure-{index:02}.json').write_text(json.dumps(
            dict(passed=False, type=type(exc).__name__, error=str(exc)), ensure_ascii=False, indent=2)+'\n')
        raise
