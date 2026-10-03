"""Independent simple-return arithmetic and causal engineering checks only."""
from copy import deepcopy
from datetime import date, timedelta
import json
import math
from pathlib import Path
import statistics

import pytest

from lei_signal.research import classic_volatility_risk_information as risk
from lei_signal.research import workflow_inputs as shared
from lei_signal.research import workflow
from lei_signal.research.question_contract import validate_workflow_contract

ROOT = Path(__file__).resolve().parents[2]


def fixture(n=560):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(days):
        c = 100 + .1 * i + 3 * math.sin(i / 8)
        bars.append(dict(asset='synthetic-A', date=day, status='quoted',
                         open=c, high=c+1, low=c-1, close=c, action_known=True))
    payload = dict(data_mode='synthetic', calendar=days, bars=bars)
    contract = dict(feature=dict(kind=risk.KIND, definition_ref=risk.DEFINITION_REF,
                                lookback=20, warmup=252, missing_policy='segmented'),
                    target=dict(kind='forward_volatility', start_offset=1, end_offset=21,
                                entry_field='close', price_measure='economic_price', unit='percentage_point'),
                    question=dict(sampling='daily', period=[days[0], days[-1]]),
                    universe=dict(assets=['synthetic-A']))
    return payload, contract


def full_contract():
    c = json.loads((ROOT/'docs/experiments/raw/tsfresh-factor-validation-2026-10-02/freeze-joint/contract.json').read_text())
    _, small = fixture()
    c['feature'] = {**small['feature'], 'bar_frequency': 'daily_quote'}
    c['target'] = small['target']
    c['question']['factor_refs'] = [risk.DEFINITION_REF]
    c['question']['target'].update(kind='forward_volatility', price_basis='close_to_close_path')
    c['question']['method']['name'] = 'prediction_ridge'
    c['question']['primary_metric']['name'] = 'MSE'
    c['evaluator'].update(kind='prediction_ridge', baseline_features=list(risk.BASELINE_FEATURES),
                          added_features=['volatility20'], **{'lambda': 1.0})
    c['split']['folds'][0]['eval_start'] = '2025-01-02'
    c['split']['folds'][1]['eval_start'] = '2026-01-05'
    c['dependence']['block_length'] = 60
    c['research_design']['sample_fit']['model_feature_count'] = 7
    return c


def test_manual_past_and_future_arithmetic():
    p, c = fixture()
    rows = risk.prepare_risk_observations(p, c, compute_labels=True)['observations']
    prices = [r['close'] for r in p['bars']]
    t = 270
    f = rows[t]['features']
    current = [prices[j]/prices[j-1]-1 for j in range(t-19, t+1)]
    future = [prices[j]/prices[j-1]-1 for j in range(t+2, t+22)]
    assert f['volatility20'] == pytest.approx(100*statistics.stdev(current))
    assert rows[t]['y'] == pytest.approx(100*statistics.stdev(future))
    assert rows[t]['label_end'] == p['calendar'][t+21]
    assert f['return20'] == pytest.approx(100*(prices[t]/prices[t-20]-1))
    assert f['S'] == int(prices[t] > sum(prices[t-19:t+1])/20 and prices[t] > prices[t-20])
    ema = sum(prices[:20])/20
    previous = None
    for price in prices[20:t+1]:
        previous = ema
        ema = 2/21*price + 19/21*ema
    assert f['E'] == int(prices[t] > ema and ema > previous)
    assert not rows[250]['ready_252'] and rows[251]['ready_252']
    assert len(rows) == len(p['calendar'])
    assert rows[-1]['target_label_reason'] == 'immature_label'
    assert f['volatility20'] != pytest.approx(100*statistics.stdev(current)*math.sqrt(252))
    assert rows[t]['y'] != pytest.approx(100*statistics.pstdev(future))
    assert rows[t]['y'] != pytest.approx(100*statistics.stdev(
        math.log(prices[j]/prices[j-1]) for j in range(t+2, t+22)))


def test_future_mutation_and_prefix_isolation(monkeypatch):
    p, c = fixture()
    monkeypatch.setattr(shared, '_label', lambda *a, **k: pytest.fail('future outcome accessed'))
    base = risk.prepare_risk_observations(p, c)['observations']
    changed = deepcopy(p)
    for r in changed['bars'][280:]:
        for key in ('open', 'high', 'low', 'close'):
            r[key] *= 3
    assert risk.prepare_risk_observations(changed, c)['observations'][:280] == base[:280]
    short = deepcopy(p)
    short['bars'] = short['bars'][:280]
    assert risk.prepare_risk_observations(short, c)['observations'] == base[:280]


@pytest.mark.parametrize('status', ['vendor_missing', 'halt'])
def test_gap_resets_252_and_does_not_compress_future_path(status):
    p, c = fixture()
    p['bars'][275].update(status=status, open=None, high=None, low=None, close=None)
    rows = risk.prepare_risk_observations(p, c, compute_labels=True)['observations']
    assert not rows[526]['ready_252'] and rows[527]['ready_252']
    assert rows[270]['y'] is None
    assert rows[270]['target_label_reason'] == 'path_'+status
    assert rows[270]['label_end'] == p['calendar'][291]


@pytest.mark.parametrize('field,value', [('kind','forward_return'), ('end_offset',20), ('unit','fraction'), ('path_field','low'), ('ddof',0), ('ddof',True), ('annualized',True)])
def test_wrong_target_is_rejected(field, value):
    p, c = fixture()
    c['target'][field] = value
    with pytest.raises(ValueError):
        risk.prepare_risk_observations(p, c)


def test_wrong_definition_and_real_permission():
    p, c = fixture()
    c['feature']['definition_ref'] = 'etf.reference.volatility20@0.0.0'
    with pytest.raises(ValueError):
        risk.prepare_risk_observations(p, c)
    p, c = fixture()
    p['data_mode'] = 'historical_reconstruction'
    c['permissions'] = {'real_labels': True}
    with pytest.raises(ValueError, match='authorization'):
        risk.prepare_risk_observations(p, c, compute_labels=True)


def test_qualification_never_reads_labels(monkeypatch):
    p, c = fixture()
    c['data'] = {'sha256': 'synthetic-only'}
    c['split'] = {'folds': [{'train_end':p['calendar'][310], 'eval_start':p['calendar'][311], 'eval_end':p['calendar'][-1]}]}
    monkeypatch.setattr(risk, 'qualify_top_panel', lambda *a: {'quality': {}, 'warnings': []})
    monkeypatch.setattr(shared, '_label', lambda *a, **k: pytest.fail('qualification label read'))
    q = risk.build_qualification(p, c, ROOT)
    assert q['outcome_values_used_for_design'] is False
    assert q['counts']['observations'] == len(p['calendar'])
    assert q['scientific_support']['folds'][0]['train'] == 39


def test_contract_rehearsal_and_cache_bindings(monkeypatch):
    c = full_contract()
    validate_workflow_contract(c)
    bad = deepcopy(c)
    bad['evaluator']['added_features'] = ['vol20']
    with pytest.raises(ValueError):
        validate_workflow_contract(bad)
    result = workflow.run_rehearsal(c)
    assert result['fits'] == 2 and result['performance']
    # Bindings read source bytes, never prepare any real future outcomes.
    monkeypatch.setattr(shared, '_label', lambda *a, **k: pytest.fail('binding read outcome'))
    bindings = workflow.actual_bindings(c, ROOT)
    assert 'src/lei_signal/research/classic_volatility_risk_information.py' in bindings['files']
    dep = 'src/lei_signal/research/factor_lab/benchmarks.py'
    assert dep in bindings['files']
    old = workflow.cache_keys(c, bindings)
    mutated = deepcopy(bindings)
    mutated['files'][dep] = 'changed-source'
    assert workflow.cache_keys(c, mutated)['features'] != old['features']


def test_real_identity_and_router_no_partial_authorization(monkeypatch):
    p, c = fixture()
    p['data_mode'] = 'historical_reconstruction'
    p['price_series'] = 'economic_price'
    c['question']['period'] = ['2022-01-04', '2026-06-30']
    with pytest.raises(ValueError, match='four ETFs'):
        risk.prepare_risk_observations(p, c)
    p, c = fixture()
    p['data_mode'] = 'historical_reconstruction'
    c['permissions'] = {'real_labels': True, 'effect_authorized': False}
    seen = []
    monkeypatch.setattr(risk, 'prepare_risk_observations', lambda *a, **kw: seen.append(kw['compute_labels']))
    shared.prepare_observations(p, c)
    assert seen == [False]


def test_old_mae_halt_path_semantics_unchanged():
    p, c = fixture()
    rows = p['bars']
    rows[275].update(status='halt', open=None, high=None, low=None, close=None)
    target = {**c['target'], 'kind': 'mae'}
    y, end, reason = shared._label(rows, 270, target)
    assert y is not None and end == p['calendar'][291] and reason is None
