"""Report arithmetic from frozen results; no data requests or factor re-estimation."""
import argparse
import collections
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


def mean(xs):
    return math.fsum(xs) / len(xs)


def chunks(xs, n=3):
    q, r = divmod(len(xs), n)
    start = 0
    for i in range(n):
        end = start + q + (i < r)
        yield xs[start:end]
        start = end


def risk(xs):
    wealth = peak = 1.0
    drawdown = 0.0
    for x in xs:
        wealth *= 1 + x
        peak = max(peak, wealth)
        drawdown = max(drawdown, 1 - wealth / peak)
    return dict(monthly_mean_pct=100*mean(xs), monthly_std_pct=100*statistics.stdev(xs),
                worst_month_pct=100*min(xs), worst10_months_mean_pct=100*mean(sorted(xs)[:math.ceil(len(xs)*.1)]),
                marked_price_max_drawdown_pct=100*drawdown)


def run(result, output):
    p = Path(result)
    manifest = json.loads((p/'manifest.json').read_text())
    for name, sha in manifest['outputs'].items():
        assert hashlib.sha256((p/name).read_bytes()).hexdigest() == sha
    monthly = list(csv.DictReader((p/'monthly.csv').open()))
    panel = collections.defaultdict(list)
    for row in csv.DictReader((p/'per_stock_month.csv').open()):
        panel[row['month']].append(row)
    perf = json.loads((p/'performance.json').read_text())
    result = dict(source_manifest_sha256=hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest(),
                  market_rerun=False, exact_dates=[monthly[0]['entry_date'], monthly[-1]['exit_date']],
                  monthly_eligible=[int(r['pool_count']) for r in monthly], conditional={}, exclusion_2023_07={})
    dates = [r['month'] for r in monthly]
    for key, bundle in perf['comparisons'].items():
        result['exclusion_2023_07'][key] = {
            scenario: 100*mean([x for m,x in zip(dates,bundle[scenario]['monthly_values']) if m != '2023-07'])
            for scenario in ('scenario_minus100','scenario_zero')}
    for include_short, kind in ((False,'vol_amount_9'),(True,'vol_amount_short_27')):
        returns = collections.defaultdict(list)
        unknown, halt, replacement, support, selected_counts = [], [], [], [], []
        previous = None
        for month in dates:
            rows = [r for r in panel[month] if r['eligibility_reason'] == 'eligible']
            assert rows
            cells = []
            for vg in chunks(sorted(rows,key=lambda r:(float(r['vol60']),r['code']))):
                for ag in chunks(sorted(vg,key=lambda r:(float(r['amount20']),r['code']))):
                    if include_short:
                        cells.extend(chunks(sorted(ag,key=lambda r:(float(r['short']),r['code']))))
                    else:
                        cells.append(ag)
            weights = {}
            for cell in cells:
                support.append(len(cell))
                top = sorted(cell,key=lambda r:(-float(r['momentum']),r['code']))[:math.ceil(len(cell)/5)]
                for r in top:
                    weights[r['code']] = len(cell)/len(rows)/len(top)
            assert abs(math.fsum(weights.values())-1)<1e-12
            bycode = {r['code']:r for r in rows}
            observed = math.fsum(w*float(bycode[c]['future_return']) for c,w in weights.items() if bycode[c]['future_return'] != '')
            uw = math.fsum(w for c,w in weights.items() if bycode[c]['future_return'] == '')
            returns['scenario_zero'].append(observed)
            returns['scenario_minus100'].append(observed-uw)
            unknown.append(uw)
            halt.append(math.fsum(w for c,w in weights.items() if bycode[c]['either_halt']=='True'))
            selected_counts.append(len(weights))
            if previous is not None:
                replacement.append(.5*math.fsum(abs(weights.get(c,0)-previous.get(c,0)) for c in weights.keys()|previous.keys()))
            previous=weights
        bundle=perf['conditional_comparisons'][kind]
        summary={scenario:risk(xs) for scenario,xs in returns.items()}
        summary.update(mean_unknown_weight_pct=100*mean(unknown),mean_either_halt_weight_pct=100*mean(halt),
                       mean_target_replacement_pct=100*mean(replacement),cell_support_minmax=[min(support),max(support)],
                       selected_count_minmax=[min(selected_counts),max(selected_counts)],period={},annual={})
        for scenario in returns:
            base=[json.loads(r['methods'])['pool_equal'][scenario] for r in monthly]
            delta=[a-b for a,b in zip(returns[scenario],base)]
            assert abs(100*mean(delta)-bundle[scenario]['mean_percentage_points'])<1e-10
            summary['annual'][scenario]={str(y):100*mean([v for m,v in zip(dates,delta) if m.startswith(str(y))]) for y in range(2015,2026)}
            summary['period'][scenario]={label:100*mean([v for m,v in zip(dates,delta) if ((m<'2020-01')==early)]) for label,early in [('2015-2019',True),('2020-2025',False)]}
            result['exclusion_2023_07'].setdefault(kind,{})[scenario]=100*mean([v for m,v in zip(dates,delta) if m!='2023-07'])
        result['conditional'][kind]=summary
    result['excluded_months']=1
    result['remaining_months']=131
    result['exclusion_warning']='same saved result; no new independent confirmation; no compressed-calendar risk path calculated'
    with Path(output).open('x') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k!='monthly_eligible'},ensure_ascii=False))


if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--result',required=True)
    a.add_argument('--out',required=True)
    args=a.parse_args()
    run(args.result,args.out)
