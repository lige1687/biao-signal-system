"""Independent readback through the existing frozen Rank IC interface.

No source download, parameter selection, or production changes. Monthly windows
are partitioned by their ACTUAL session count solely to satisfy the fixed-length
interface. Results are recombined with equal weight per original month.
"""
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from lei_signal.research.factor_lab.rank_ic_evaluation import (
    RankICContract, RankICScore, RankICUniverse, RankICCheckpoint,
    RankICLabelWindow, RankICRealBinding, frame_sha256,
    session_sequence_sha256, evaluate_frozen_rank_ic,
)


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE/'storage-plan-core.json').read_text())
    out = Path(plan['output'])/'classic-factor-chain-diagnostic-2026-10-20'
    design_path = HERE/'design.json'
    design = json.loads(design_path.read_text())
    bound = design['inputs']['price_contract']
    assert digest(bound['path']) == bound['sha256']
    source_contract = json.loads(Path(bound['path']).read_text())
    assert digest(source_contract['calendar']['path']) == source_contract['calendar']['sha256']
    doc = json.loads(Path(source_contract['calendar']['path']).read_text())
    cal = pd.DataFrame(doc['data'], columns=doc['fields'])
    sessions = cal.loc[cal.is_trading_day.eq('1'), 'calendar_date'].tolist()
    si = {d:i for i,d in enumerate(sessions)}
    s0 = pd.read_csv(out/'scores.csv', dtype={'code':str})
    l0 = pd.read_csv(out/'labels.csv', dtype={'code':str})
    p0 = pd.read_csv(out/'periodic.csv')
    codes = tuple(sorted(x['code'] for x in source_contract['sources']))
    schedule = l0[['decision_date','entry_date','exit_date']].drop_duplicates().copy()
    assert len(schedule) == 132
    schedule['intervals'] = schedule.apply(lambda r:si[r.exit_date]-si[r.entry_date], axis=1)
    approval = HERE/'authorization-and-boundary.json'
    contracts, outputs = [], []
    for count, dates in schedule.groupby('intervals', sort=True):
        checkpoints = tuple(RankICCheckpoint(d, 'historical') for d in dates.decision_date)
        ss = s0[s0.decision_date.isin(dates.decision_date)]
        ll = l0[l0.decision_date.isin(dates.decision_date)]
        scores = pd.DataFrame({'asset_id':ss.code, 'asset_type':'stock',
            'checkpoint_at':ss.decision_date, 'computed_through_at':ss.decision_date,
            'source_available_at':None, 'raw':ss.raw_score, 'reversal':ss.reversal_score}).reset_index(drop=True)
        labels = pd.DataFrame({'asset_id':ll.code, 'checkpoint_at':ll.decision_date,
            'forward_return':ll.future_return, 'label_start_at':ll.entry_date,
            'label_end_at':ll.exit_date, 'label_available_at':None,
            'label_quality_valid':ll.future_return.notna()}).reset_index(drop=True)
        windows = []
        for r in dates.itertuples():
            seq = tuple(sessions[si[r.decision_date]:si[r.exit_date]+1])
            windows.append(RankICLabelWindow(r.decision_date, 'historical600', r.entry_date,
                r.exit_date, seq, si[r.entry_date]-si[r.decision_date],
                si[r.exit_date]-si[r.decision_date], source_contract['calendar']['path'],
                session_sequence_sha256(seq)))
        binding = RankICRealBinding('classic-chain-diagnostic-2026-10-20',
            frame_sha256(scores), frame_sha256(labels), bound['path'], str(design_path),
            str(approval), bound['sha256'], digest(design_path), digest(approval))
        c = RankICContract(contract_id=f'classic-chain-native-review/{count}',
            data_mode='historical_reconstruction', purpose='return_ranking', label_semantics='higher_return',
            scores=(RankICScore('raw','raw','raw_factor','lower_score_higher_label',
                'local.classic.monthly-reversal-diagnostic@1.0.0'),
                RankICScore('reversal','reversal','raw_factor','higher_score_higher_label',
                'local.classic.monthly-reversal-diagnostic@1.0.0')),
            universes=(RankICUniverse('historical600','stock',codes),), checkpoints=checkpoints,
            window_start='2014-12-01', window_end='2026-01-15', evaluation_as_of='2026-10-20',
            temporal_basis='session_date_after_close', availability_context='retrospective_after_close',
            min_assets=3, score_mask_policy='common', time_weighting='equal_checkpoint',
            label_horizon='next calendar month; first-session-close to following first-session-close',
            label_overlap='nonoverlapping', label_horizon_session_intervals=int(count),
            label_windows=tuple(windows), real_binding=binding,
            source_evidence=bound['path'], after_close_scenario='Historical completed-day quotation reconstruction; original provider arrival times and full shareholder returns unqualified.')
        result = evaluate_frozen_rank_ic(scores, labels, c)
        assert result.metadata['live_qualified'] is False
        contracts.append(asdict(c)); outputs.append(result.periodic)
    native = pd.concat(outputs, ignore_index=True)
    raw = native[native.score.eq('raw')].copy()
    rev = native[native.score.eq('reversal')].copy()
    raw['formation_month'] = raw.checkpoint.str[:7]
    merged = p0.merge(raw, on='formation_month', validate='one_to_one')
    assert len(merged) == 132
    assert np.allclose(merged.ic_raw, merged.rank_ic, atol=1e-12, rtol=0)
    assert (merged.known == merged.eligible_assets).all()
    by_date = native.pivot(index='checkpoint', columns='score', values='rank_ic')
    assert np.allclose(by_date.raw, -by_date.reversal, atol=1e-12, rtol=0)
    # Independent arithmetic from original JSON, not runner helper functions.
    checks = []
    for code in (codes[0], codes[len(codes)//2], codes[-1]):
        source = next(x for x in source_contract['sources'] if x['code']==code)
        assert digest(source['path']) == source['sha256']
        d = json.loads(Path(source['path']).read_text())
        frame = pd.DataFrame(d['data'], columns=d['fields']).set_index('date')
        pair = s0[s0.code.eq(code)].merge(l0[l0.code.eq(code)], on=['formation_month','code','decision_date'])
        for i in sorted(set([0,len(pair)//2,len(pair)-1])):
            r = pair.iloc[i]
            actual = float(frame.loc[r.current_month_end,'close'])/float(frame.loc[r.prior_month_end,'close'])-1
            assert abs(actual-r.raw_score)<1e-12
            if pd.notna(r.future_return):
                actual_y = float(frame.loc[r.exit_date,'close'])/float(frame.loc[r.entry_date,'close'])-1
                assert abs(actual_y-r.future_return)<1e-12
            assert r.prior_date < r.decision_date < r.entry_date < r.exit_date
            checks.append({'code':code,'month':r.formation_month,'score':float(r.raw_score),
                           'label':float(r.future_return) if pd.notna(r.future_return) else None})
    target = out/'native-review'
    target.mkdir(exist_ok=False)
    native.to_csv(target/'periodic.csv', index=False)
    (target/'contracts.json').write_text(json.dumps(contracts,ensure_ascii=False,indent=2))
    receipt = {'status':'passed_bounded_historical_diagnostic','months':132,
        'native_rows':len(native),'actual_interval_lengths':sorted(int(x) for x in schedule.intervals.unique()),
        'max_ic_absolute_difference':float(np.max(np.abs(merged.ic_raw-merged.rank_ic))),
        'native_mean_raw_ic':float(raw.rank_ic.mean()),'native_mean_reversal_ic':float(rev.rank_ic.mean()),
        'independent_endpoint_checks':checks,'source_arrival_unknown':True,'live_qualified':False,
        'all_native_contracts':str(target/'contracts.json'),'code_sha256':digest(__file__)}
    (HERE/'native-review-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    main()
