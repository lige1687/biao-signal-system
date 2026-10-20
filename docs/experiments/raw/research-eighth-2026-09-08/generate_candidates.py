"""Frozen research candidates using only price actions known at each decision."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import json
import hashlib
import gzip
from datetime import timedelta
import pandas as pd
import numpy as np

P = Path(__file__).resolve().parent
PACKAGE = P / 'b-research-fix/research-package'
sys.path.insert(0, str(PACKAGE / 'src'))
sys.path.insert(0, str(P / 'product-qualification/price-helper'))
from price_basis import PriceBasis
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.dense_breakout import detect_dense_breakout_events
from lei_signal.rules.reward_risk_filter import _target_b
from lei_signal.rules.resistance_b1 import find_b1
from lei_signal.domain.rules_config import get_rule, load_ruleset

START, END = '2015-01-01', '2026-06-30'
SYMBOLS = ['sh510300', 'sh513100', 'sh518880', 'sz159915']
FIELDS = ['open', 'high', 'low', 'close', 'volume']

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def plain(x):
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    if isinstance(x, np.integer):
        return int(x)
    if hasattr(x, 'isoformat'):
        return x.isoformat()
    return x

def load_inputs():
    Q = P / 'product-qualification'
    bars = {}
    for s in SYMBOLS:
        f = Q / 'bars-helper-native' / f'{s}-nominal.csv'
        frame = pd.read_csv(f, dtype={'date': str})
        assert frame.date.is_unique and frame.date.is_monotonic_increasing
        assert frame.date.max() <= END
        assert np.isfinite(frame[FIELDS].to_numpy()).all()
        assert (frame[['open', 'high', 'low', 'close']] > 0).all().all()
        bars[s] = frame.to_dict('records')
    actions = json.loads((Q / 'actions.json').read_text())
    assert all(a['announcement_date'] < a['effective_date'] for a in actions)
    assert len(actions) == 14
    return bars, actions

def frame_asof(s, bars, actions, asof):
    """No later rows enter the feature frame, even within an adjustment epoch."""
    observed = {s: [r for r in bars[s] if r['date'] <= asof]}
    known = [a for a in actions if a['symbol'] == s and a['announcement_date'] <= asof]
    basis = PriceBasis(observed, known)
    rows = []
    for r in observed[s]:
        out = basis.bar(s, r, asof, 'cash_proportional_v1')
        rows.append({'date': r['date'], **{f: float(out[f]) for f in FIELDS}})
    frame = pd.DataFrame(rows).set_index('date')
    frame.index = pd.to_datetime(frame.index)
    return compute_features(frame)

def target_for(frame, pivots, pos):
    close = float(frame.close.iloc[pos]); day = frame.index[pos].date()
    lookback = int(get_rule('reward_risk_filter').param('range_lookback', 60))
    target, source = _target_b(frame, position=pos, entry_price=close, pivots=pivots,
                             as_of=day, range_lookback=lookback, gaps=None)
    confirmed, source_day = None, None
    if source == 'swing_high':
        b1 = find_b1(pivots, as_of=day, current_close=close)
        assert b1 is not None and b1.available_date <= day
        assert float(b1.price) == float(target)
        confirmed, source_day = b1.available_date.isoformat(), b1.pivot_date.isoformat()
    elif source is not None:
        confirmed = day.isoformat()
        source_day = day.isoformat()  # aggregate of history available by this date
    return target, source, confirmed, source_day

def qualify(ref, stop, target):
    if stop is None or not np.isfinite(stop) or stop >= ref or stop <= 0:
        return None, False, 'invalid_structure_risk'
    if target is None or not np.isfinite(target) or target <= ref:
        return None, False, 'target_unavailable'
    rr = (target - ref) / (ref - stop)
    return rr, rr >= 3, None if rr >= 3 else 'signal_reward_risk_below_3'

def extract(s, frame, lo, hi):
    events = detect_dense_breakout_events(frame, s)
    byday = {}
    for e in events:
        if (e.evidence.get('sub_rule') == 'dense_breakout_confirmed'
                and e.evidence.get('variant') == 'breakout'):
            byday.setdefault(e.available_date.isoformat(), []).append(e)
    pivots = confirmed_pivots(frame)
    highest = frame.close.shift(1).rolling(60, min_periods=60).max()
    lowest = frame.close.shift(1).rolling(60, min_periods=60).min()
    road = (frame.close > frame.ema20) & (frame.close > frame.close_lag20)
    candidates, observations, event_rows = [], {}, []
    for i, (ts, row) in enumerate(frame.iterrows()):
        d = ts.date().isoformat()
        if not lo <= d <= hi:
            continue
        needed = ['ema20', 'sma20', 'sma60', 'sma120', 'ema120', 'close_lag20']
        if i < 119 or any(not np.isfinite(row[k]) for k in needed):
            continue
        observations[d] = plain({'ema20': row.ema20, 'cost20': row.close_lag20,
                                 'ema20_slope': row.ema20_slope, 'sma20_slope': row.sma20_slope,
                                 'sma20': row.sma20, 'sma60': row.sma60,
                                 'close': row.close, 'basis_as_of': d})
        recipes = []
        if row.close > highest.iloc[i]:
            recipes.append(('P0', 'donchian60', lowest.iloc[i], None, None))
            if road.iloc[i]:
                recipes.append(('P1', 'donchian60', lowest.iloc[i], None, None))
        if road.iloc[i] and not road.iloc[i-1]:
            recipes.append(('P5', 'road_on', lowest.iloc[i], None, None))
        for e in byday.get(d, []):
            event_rows.append(plain({'symbol': s, 'signal_date': d, 'event_id': e.event_id,
                                     'lifecycle_id': e.lifecycle_id, 'evidence': e.evidence}))
            for cfg in ['P2', 'P3', 'P4', 'P7']:
                stop = lowest.iloc[i] if cfg == 'P2' else e.evidence.get('stop_price')
                recipes.append((cfg, 'B:' + e.event_id, stop,
                                e.evidence.get('breakout_reference'), e.lifecycle_id))
        if not recipes:
            continue
        target, source, confirmed, source_day = target_for(frame, pivots, i)
        for cfg, kind, stop, upper, lifecycle in recipes:
            ref = float(row.close)
            rr, accepted, reason = qualify(ref, stop, target)
            candidates.append(plain({'config_id': cfg, 'symbol': s, 'signal_date': d,
                'known_at': d+'T15:00:00+08:00', 'candidate_id': f'{cfg}:{s}:{d}:{kind}',
                'opportunity_key': f'{s}:{d}:{kind}', 'kind': kind, 'structure_id': lifecycle,
                'variant': 'breakout', 'signal_ref': ref, 'stop': stop, 'target': target, 'upper': upper,
                'signal_rr': rr, 'signal_accepted': bool(accepted), 'signal_reject_reason': reason,
                'target_source': source, 'target_confirmed_at': confirmed, 'target_source_date': source_day,
                'basis_as_of': d, 'rule_version': '2.1.0+b-research-fix-eighth',
                'full_B_qualified': False, 'discipline_scope': 'frozen proxy, warmup, known stop/target, signal and open RR; not all nine disciplines'}))
    return candidates, observations, event_rows

def generate(bars, actions):
    all_candidates, all_obs, all_events, epochs = [], {}, [], []
    for s in SYMBOLS:
        boundaries = sorted({START} | {a['effective_date'] for a in actions
                                      if a['symbol'] == s and START <= a['effective_date'] <= END})
        all_obs[s] = {}
        for k, lo in enumerate(boundaries):
            hi = (pd.Timestamp(boundaries[k+1]) - timedelta(days=1)).date().isoformat() if k+1 < len(boundaries) else END
            frame = frame_asof(s, bars, actions, hi)
            c, o, e = extract(s, frame, lo, hi)
            all_candidates.extend(c); all_obs[s].update(o); all_events.extend(e)
            epochs.append({'symbol': s, 'from': lo, 'through': hi, 'input_rows': len(frame),
                           'decision_rows': len(o), 'candidate_rows': len(c), 'raw_B_events': len(e)})
        print(s, 'epochs complete', flush=True)
    assert len({x['candidate_id'] for x in all_candidates}) == len(all_candidates)
    all_candidates.sort(key=lambda x: (x['signal_date'], x['symbol'], x['candidate_id']))
    return all_candidates, all_obs, all_events, epochs

def forward_checks(bars, actions, candidates, observations):
    """Independently truncate on fixed year and action boundary dates; compare exact-day results."""
    findings = []
    for s in SYMBOLS:
        dates = [r['date'] for r in bars[s] if START <= r['date'] <= END]
        chosen = {next(d for d in dates if d.startswith(str(y))) for y in range(2015, 2027)}
        for a in actions:
            if a['symbol'] == s and START <= a['effective_date'] <= END:
                before = [d for d in dates if d < a['effective_date']]
                after = [d for d in dates if d >= a['effective_date']]
                if before: chosen.add(before[-1])
                if after: chosen.add(after[0])
        for d in sorted(chosen):
            truncated = {s: [r for r in bars[s] if r['date'] <= d]}
            known = [a for a in actions if a['announcement_date'] <= d]
            frame = frame_asof(s, truncated, known, d)
            actual, obs, _ = extract(s, frame, d, d)
            expected = [c for c in candidates if c['symbol'] == s and c['signal_date'] == d]
            assert plain(actual) == plain(expected), ('candidate_forward_difference', s, d)
            assert obs.get(d) == observations[s].get(d), ('feature_forward_difference', s, d)
            findings.append({'symbol': s, 'date': d, 'candidate_count': len(actual), 'matched': True})
        print(s, 'fixed forward checks complete', flush=True)
    return findings

def main():
    out = P / 'candidate-study'; out.mkdir(exist_ok=True)
    bars, actions = load_inputs()
    # Accept only the already frozen research protocol.
    assert sha(P/'protocol.md') == json.loads((P/'protocol-lock.json').read_text())['protocol_sha256']
    assert sha(P/'protocol-addendum-01.md') == json.loads((P/'protocol-addendum-01-lock.json').read_text())['sha256']
    inputs = list((P/'product-qualification/bars-helper-native').glob('*.csv'))
    inputs += [P/'product-qualification/actions.json', P/'product-qualification/price-helper/price_basis.py',
               P/'protocol.md', P/'protocol-addendum-01.md', Path(__file__)]
    inputs += list((PACKAGE/'src').rglob('*.py')) + list((PACKAGE/'configs').glob('*.yaml'))
    lock = {'files': {str(f): sha(f) for f in sorted(inputs)}, 'ruleset_version': load_ruleset()['ruleset_version']}
    (out/'run-lock.json').write_text(json.dumps(lock, indent=2)+'\n')
    candidates, obs, events, epochs = generate(bars, actions)
    for name, data in [('candidates', candidates), ('exit-observations', obs), ('B-events', events), ('epochs', epochs)]:
        with gzip.open(out/(name+'.json.gz'), 'wt') as f:
            json.dump(plain(data), f, ensure_ascii=False, allow_nan=False)
    pd.DataFrame(candidates).to_csv(out/'candidates.csv', index=False)
    checks = forward_checks(bars, actions, candidates, obs)
    (out/'forward-checks.json').write_text(json.dumps(checks, indent=2)+'\n')
    counts = pd.DataFrame(candidates).groupby(['config_id','symbol']).agg(raw=('candidate_id','size'), signal_accepted=('signal_accepted','sum')).reset_index().to_dict('records')
    (out/'summary.json').write_text(json.dumps({'raw_candidate_rows': len(candidates), 'raw_B_events': len(events),
        'by_config_symbol': counts, 'forward_checks': len(checks), 'full_B_qualified': False}, indent=2)+'\n')
    assert all(sha(Path(f)) == h for f, h in lock['files'].items()), 'input changed during generation'
    print('candidate generation and forward checks finished', flush=True)

if __name__ == '__main__':
    main()
