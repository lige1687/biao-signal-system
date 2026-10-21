"""One frozen account batch. Reuses saved groups, never reranks or filters by labels."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

D = Path(__file__).parent
MAIN = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
WORK = D.parents[3]
sys.path.insert(0, str(MAIN / 'src'))
from lei_signal.research.high52_revalidation import adapt_back_adjusted
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(ref):
    p = Path(ref['path'])
    if sha(p) != ref['sha256']:
        raise ValueError(f'changed input: {p}')
    return json.loads(p.read_text())


def save(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def build_targets(saved, calendar):
    """Whitelist membership fields only; saved outcome fields are not consulted."""
    month_ends = {day[:7]: day for day in calendar}
    groups = defaultdict(dict)
    for r in saved['groups']:
        key = (r['month'], r['universe'], r['factor'])
        if r['group'] in groups[key]:
            raise ValueError('duplicate group')
        groups[key][r['group']] = list(r['codes'])
    schedules, pools, seen = defaultdict(dict), {}, set()
    for r in saved['monthly']:
        month, universe, factor = r['month'], r['universe'], r['factor']
        key = (month, universe, factor)
        if key in seen:
            raise ValueError('duplicate month/factor')
        seen.add(key)
        bins = groups.get(key, {})
        if r['qualified']:
            if set(bins) != set(range(1, 6)):
                raise ValueError('qualified month missing group')
            union = sorted(code for codes in bins.values() for code in codes)
            if len(set(union)) != len(union) or len(union) != r['n']:
                raise ValueError('membership mismatch')
        else:
            if bins:
                raise ValueError('unqualified month has groups')
            union = []
        pool_key = (month, universe)
        if pool_key in pools and pools[pool_key] != union:
            raise ValueError('four factors do not share one pool')
        pools[pool_key] = union
        for group in range(1, 6):
            names = bins.get(group, [])
            schedules[f'{universe}__{factor}__G{group}'][month_ends[month]] = {
                'weights': {c: 1 / len(names) for c in names},
                'qualified': bool(r['qualified']), 'month': month,
            }
    for (month, universe), names in pools.items():
        schedules[f'{universe}__pool'][month_ends[month]] = {
            'weights': {c: 1 / len(names) for c in names},
            'qualified': bool(names), 'month': month,
        }
    if len(schedules) != 42 or any(len(v) != 132 for v in schedules.values()):
        raise ValueError('expected 42 schedules and 132 formation months')
    return dict(schedules)


def main():
    started = time.monotonic()
    contract = json.loads((D / 'contract.json').read_text())
    if contract.get('effects_authorized') is not True:
        raise ValueError('no frozen effects authorization')
    for ref in contract['bindings']:
        if sha(ref['path']) != ref['sha256']:
            raise ValueError(f"changed code/design: {ref['path']}")
    plan = read(contract['storage_plan'])
    recheck_saved_plan(MAIN, plan, plan['task_id'], plan['estimated_bytes'], plan['internal_metadata_bytes'])
    output = Path(plan['output'])
    output.mkdir(parents=True, exist_ok=False)
    manifest = read(contract['source_manifest'])
    calendar = [r[0] for r in read(contract['calendar'])['data'] if r[1] == '1']
    schedules = build_targets(read(contract['groups_result']), calendar)
    save(output / 'input-weights.json', schedules)
    market, source_audit = {}, []
    for index, (code, pair) in enumerate(sorted(manifest['asset_sources'].items()), 1):
        if not _still_mounted(plan):
            raise ValueError('bound disk disappeared')
        adapted = adapt_back_adjusted(read(pair['daily']), read(pair['adjustments']), code, calendar,
                                      factor_field='foreAdjustFactor')
        broken = set(adapted['break_dates'])
        by_day = {}
        for row in adapted['rows']:
            if not '2014-12-31' <= row['date'] <= '2025-12-31':
                continue
            item = {k: float(row[k]) if row[k] else None
                    for k in ('open', 'close', 'high', 'low', 'preclose', 'volume')}
            item.update({k: row[k] for k in ('tradestatus', 'isST')})
            item.update(source_valid=row['date'] not in broken, basis_break=row['date'] in broken)
            by_day[row['date']] = item
        for day in broken:
            if '2014-12-31' <= day <= '2025-12-31' and day not in by_day:
                by_day[day] = {'source_valid': False, 'basis_break': True}
        market[code] = by_day
        source_audit.append({'code': code, 'rows': len(by_day), 'break_dates': sorted(broken),
                             'failures': adapted['failures']})
        if index % 50 == 0:
            print(f'source qualification {index}/300', flush=True)
    save(output / 'source-audit.json', source_audit)
    spec = importlib.util.spec_from_file_location('group_engine', contract['engine']['path'])
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    for index, (name, schedule) in enumerate(sorted(schedules.items()), 1):
        for cost in (0, 25):
            if not _still_mounted(plan):
                raise ValueError('bound disk disappeared')
            result = engine.simulate(calendar, market, schedule, cost_bps=cost,
                                     initial_cash=100000, start_date='2014-12-31', end_date='2025-12-31')
            save(output / f'{name}__fee{cost}.json', result)
        print(f'continuous accounts {index}/42 (two costs)', flush=True)
    save(output / 'run-receipt.json', {'seconds': time.monotonic()-started, 'streams':84,
         'contract_sha256': sha(D/'contract.json'), 'core_attempt':1, 'market_requests':0,
         'old_studies_rerun':0, 'sorting_recomputed':False, 'execution_proxy_only':True})
    save(output / 'manifest.json', {'files': {p.name:{'sha256':sha(p),'bytes':p.stat().st_size}
         for p in sorted(output.iterdir()) if p.is_file() and not p.name.startswith('._')}})
    print(f'COMPLETE {output}', flush=True)


if __name__ == '__main__':
    main()
