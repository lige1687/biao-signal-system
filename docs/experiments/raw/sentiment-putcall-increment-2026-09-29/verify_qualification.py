"""Controller source arithmetic, independently read the original files."""
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CUT = dt.date(2012, 6, 11)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(dates):
    count = 0
    previous = None
    source_dates = price_dates
    for date in dates:
        if previous is None or (date - previous).days >= 4 or source_dates[date] != source_dates[previous] + 1:
            count += 1
        previous = date
    return count


price_dates = {dt.date.fromisoformat(r['Date']): i for i, r in enumerate(
    csv.DictReader((HERE / 'inputs/px_SPY.csv').open()))}
audit = json.loads((HERE / 'qualification/audit.json').read_text())
previous_audit = json.loads((HERE / 'qualification/audit-v1.json').read_text())
checks = {}
for product in ['equity', 'total']:
    path = HERE / f'inputs/{product}pc.csv'
    raw = list(csv.DictReader(io.StringIO('\n'.join(path.read_text(encoding='latin1').splitlines()[2:]))))
    normalized = list(csv.DictReader((HERE / f'qualification/normalized-{product}.csv').open()))
    assert len(raw) == len(normalized) == 3253
    independently_parsed = []
    for r, n in zip(raw, normalized):
        date = dt.datetime.strptime(r['DATE'], '%m/%d/%Y').date()
        calls = int(r.get('CALL', r.get('CALLS')))
        puts = int(r.get('PUT', r.get('PUTS')))
        total = int(r['TOTAL'])
        ratio = float(r['P/C Ratio'])
        assert calls > 0 and puts >= 0 and calls + puts == total
        assert date.isoformat() == n['date']
        assert calls == int(n['CALL']) and puts == int(n['PUT']) and total == int(n['TOTAL'])
        assert ratio == float(n['reported_ratio'])
        assert abs(puts / calls - float(n['ratio_exact'])) < 5.1e-11
        assert abs(puts / calls - ratio) <= .0050000001
        assert date in price_dates
        independently_parsed.append((date, ratio, puts / calls))
    assert len({r[0] for r in independently_parsed}) == len(raw)
    max_difference = max(abs(r[1] - r[2]) for r in independently_parsed)
    assert abs(max_difference - float(audit['products'][product]['max_ratio_abs_difference'])) < 2e-15
    assert sha(path) == audit['products'][product]['sha256']
    segments = {}
    for name, keep in [('pre_2012_06_11', lambda d: d < CUT),
                       ('post_2012_06_11_through_2019_10_04', lambda d: d >= CUT)]:
        rows = [r for r in independently_parsed if keep(r[0])]
        reported = [r[0] for r in rows if r[1] > 1]
        exact = [r[0] for r in rows if r[2] > 1]
        helper_period = audit['coverage_and_extremes'][product]['periods'][name]
        assert len(rows) == helper_period['unique_source_dates']
        assert len(reported) == helper_period['reported_ratio_gt_1_date_count']
        assert len(exact) == helper_period['ratio_exact_gt_1_date_count']
        info = dict(source_dates=len(rows), reported_gt1_dates=len(reported),
                    exact_gt1_dates=len(exact), reported_runs=runs(reported), exact_runs=runs(exact),
                    helper_gap_only_reported_runs=helper_period['reported_ratio_gt_1_run_count_gap_under_4_days'],
                    helper_gap_only_exact_runs=helper_period['ratio_exact_gt_1_run_count_gap_under_4_days'])
        segments[name] = info
    assert segments['post_2012_06_11_through_2019_10_04']['source_dates'] == 1842
    checks[product] = dict(original_sha256=sha(path), rows=len(raw),
                           max_reported_exact_difference=max_difference, segments=segments,
                           normalized_all_values_verified=True,
                           corrected_prior_max_difference=previous_audit['products'][product].get('max_ratio_abs_difference'))
assert checks['equity']['segments']['post_2012_06_11_through_2019_10_04']['reported_gt1_dates'] == 6
assert checks['total']['segments']['post_2012_06_11_through_2019_10_04']['reported_gt1_dates'] == 543
out = dict(passed=True, no_helper_imports=True, original_source_checks=checks,
           acceptance='source normalization and coverage arithmetic accepted; not predictive qualification',
           preserved_failure='audit-v1 retained: date object/string comparison marked present quotes missing; published and exact >1 now separate. Controller early incomplete read showed zero rounding error, final report and retained audit-v1 have correct nonzero maximum.',
           episode_definition='Controller requires adjacent actual quote rows plus gaps<4 days; helper gap-only runs are retained with their explicit name, not used as original strategy events.',
           remaining='First-release timing unknown; 2012 definition boundary and 2019 end must remain explicit. Exact ratios never replace original reported Equity>1.')
(HERE / 'controller-qualification-review.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False))
