"""Input-only coverage audit. Never reads future targets or estimates returns."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.rules.clock_classifier import _classify_values, _params, clock_series

HERE = Path(__file__).resolve().parent
NAMES = {0: 'unknown', 1: 'up', 2: 'up', 3: 'sideways', 4: 'down', 5: 'down'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classes(close):
    # Keep every supplied date: a missing quote is not removed or forward-filled.
    close = pd.Series(close, dtype=float)
    close = close.where(np.isfinite(close) & (close > 0))
    frame = pd.DataFrame({'sma60': close.rolling(60, min_periods=60).mean(),
                          'sma20': close.rolling(20, min_periods=20).mean()})
    return clock_series(frame).to_numpy()


def scalar(close):
    out = []
    def mean_at(t, n):
        if t < n - 1:
            return math.nan
        values = close[t-n+1:t+1]
        if not all(math.isfinite(v) and v > 0 for v in values):
            return math.nan
        return math.fsum(values) / n
    for t in range(len(close)):
        a0, a1 = mean_at(t, 60), mean_at(t-60, 60)
        b0, b1 = mean_at(t, 20), mean_at(t-20, 20)
        a = math.log(a0/a1)*252/60 if a0 > 0 and a1 > 0 else math.nan
        b = math.log(b0/b1)*252/20 if b0 > 0 and b1 > 0 else math.nan
        if math.isnan(a): v = 0
        elif a > 1 or (a > .4 and b >= 2*a): v = 1
        elif a < -1 or (a < -.4 and b <= 2*a): v = 5
        elif a >= .1: v = 2
        elif a <= -.1: v = 4
        else: v = 3
        out.append(v)
    return np.array(out)


def support(values):
    values = list(map(int, values))
    mapped = [NAMES[v] for v in values]
    return {'five_class_dates': {str(v): values.count(v) for v in range(6)},
            'three_class_dates': {n: mapped.count(n) for n in ['unknown','up','sideways','down']},
            'continuous_runs': {n: sum(x == n and (i == 0 or mapped[i-1] != n)
                                     for i,x in enumerate(mapped)) for n in ['unknown','up','sideways','down']}}


def selftest():
    a = pd.Series([np.nan, -.1, .1, 0, .4, 1, 1.0001, -.4, -1, -1.0001, .5, -.5])
    b = pd.Series([0, 0, 0, 0, .8, 0, 0, -.8, 0, 0, 1, -1])
    assert _classify_values(a,b).tolist() == [0,4,2,3,2,2,1,4,4,5,1,5]
    paths = [np.full(280, 100.), np.exp(np.arange(280)/500),
             np.exp(-np.arange(280)/500)]
    hole = paths[1].copy(); hole[145] = np.nan; paths.append(hole)
    for p in paths:
        actual = classes(p)
        assert np.array_equal(actual, scalar(p))
        assert np.all(actual[:119] == 0)
        for n in [119,120,146,200,250]:
            assert np.array_equal(classes(p[:n]), actual[:n])
    assert support([1,2,3,0,4,5,3])['continuous_runs'] == {'unknown':1,'up':1,'sideways':2,'down':1}
    return {'slope_boundary_cases':12, 'synthetic_paths':4, 'prefix_checks':20,
            'independent_scalar_points':1120, 'run_count_case':1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path.cwd())
    ap.add_argument('--cache-root', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    started = time.monotonic()
    protocol = json.loads((HERE/'protocol.json').read_text())
    assert get_rule('clock_classifier').version == '2.0.0'
    assert _params(get_rule('clock_classifier')) == protocol['clock_parameters']
    checks = selftest()
    if args.self_test:
        args.output.write_text(json.dumps(checks, indent=2)+'\n'); return
    assert args.cache_root is not None
    for item in protocol['inputs'] + protocol['code']:
        p = (args.cache_root if item['location'] == 'CACHE' else args.root) / item['path']
        assert p.is_file() and p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], item['path']
    spy = pd.read_csv(args.root / protocol['spy'], usecols=['Date','Close'])
    assert spy.Date.is_unique and spy.Date.is_monotonic_increasing
    sv = classes(spy.Close)
    assert np.array_equal(sv, scalar(spy.Close.to_numpy()))
    # Read only dates from the sealed panel, not outcomes or fitted values.
    dates = pd.read_csv(args.root / protocol['aaii_panel'], usecols=['t']).t
    idx = pd.Index(spy.Date).get_indexer(dates)
    assert np.all(idx >= 0) and dates.is_unique
    daily_runs = np.cumsum(np.r_[True, np.array([NAMES[x] for x in sv[1:]]) !=
                               np.array([NAMES[x] for x in sv[:-1]])])
    selected = sv[idx]
    us = support(selected)
    us['date_range'] = [dates.min(), dates.max()]
    us['daily_environment_runs_touched'] = {n: len(set(daily_runs[idx[[NAMES[v] == n for v in selected]]]))
                                           for n in NAMES.values()}
    us['years_with_dates'] = {n: sorted(set(d[:4] for d,v in zip(dates,selected) if NAMES[v] == n))
                            for n in NAMES.values()}
    us['eras'] = {}
    for lo, hi in [('2010','2014'),('2015','2019'),('2020','2026')]:
        us['eras'][lo+'-'+hi] = support([v for d,v in zip(dates,selected) if lo <= d[:4] <= hi])
    hist = json.loads((args.cache_root/'sector_trend_history.json').read_text())
    flow = json.loads((args.cache_root/'tx_sector_flow_pilot.json').read_text())['boards']
    cn_dates = [r['date'] for r in hist]
    assert cn_dates == sorted(set(cn_dates))
    boards = sorted(set().union(*(r['boards'] for r in hist)))
    board_stats = {}; states = []
    def finite(x): return isinstance(x,(float,int)) and math.isfinite(x)
    for code in boards:
        records = [r['boards'].get(code,{}) for r in hist]
        close = [float(r['close']) if finite(r.get('close')) and r['close'] > 0 else math.nan for r in records]
        v = classes(close)
        assert np.array_equal(v, scalar(close)), code
        states.append(v)
        flow_dates = [p['date'][:10] for p in flow.get(code,[]) if finite(p.get('small_yi'))]
        assert len(flow_dates) == len(set(flow_dates)), code
        common = [d for d,c in zip(cn_dates,close) if math.isfinite(c) and d in set(flow_dates)]
        stat = support(v)
        stat.update({'finite_close':sum(math.isfinite(c) for c in close),
                     'b50_dates':sum(finite(r.get('b50')) for r in records),
                     'b200_dates':sum(finite(r.get('b200')) for r in records),
                     'same_date_flow_close':len(common), 'last_common_date':max(common) if common else None,
                     'has_all_three_price_states': all(stat['three_class_dates'][n]>0 for n in ['up','sideways','down'])})
        board_stats[code] = stat
    matrix = np.array(states)
    cn = {'date_range':[cn_dates[0],cn_dates[-1]], 'distinct_dates':len(cn_dates), 'distinct_boards':len(boards),
          'boards_with_all_three_states':sum(s['has_all_three_price_states'] for s in board_stats.values()),
          'boards_with_any_known_state':sum(s['three_class_dates']['unknown']<len(cn_dates) for s in board_stats.values()),
          'dates_any_board_known':int(np.sum(np.any(matrix!=0,axis=0))),
          'max_known_dates_per_board':max(sum(v for k,v in s['three_class_dates'].items() if k!='unknown') for s in board_stats.values()),
          'boards_with_140_same_date_flow_close':sum(s['same_date_flow_close']>=140 for s in board_stats.values()),
          'any_b200_values':sum(s['b200_dates'] for s in board_stats.values()),
          'any_board_state_date_counts':{n:int(sum(any(NAMES[v]==n for v in matrix[:,i]) for i in range(len(cn_dates))))
                                         for n in ['unknown','up','sideways','down']},
          'market_environment':'not computed: no separately qualified representative index bound in this audit',
          'qualification':'current-member synthetic board prices; retrospective shape coverage only, not historical member-qualified factors',
          'per_board':board_stats}
    checks.update({'real_scalar_points':len(sv)+matrix.size, 'source_hashes_verified':len(protocol['inputs'])+len(protocol['code'])})
    result = {'us_aaii_dates':us,'cn_board_input_support':cn,'checks':checks,
              'future_targets_read':False,'model_fits':0,'effectiveness':'not_evaluated',
              'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,
              'elapsed_seconds':time.monotonic()-started}
    assert not args.output.exists(), 'never overwrite a saved run'
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in cn.items() if k!='per_board'},ensure_ascii=False))
    print(json.dumps(us,ensure_ascii=False))


if __name__ == '__main__': main()
