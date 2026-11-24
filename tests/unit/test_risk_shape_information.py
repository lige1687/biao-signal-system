"""Independent risk-shape arithmetic and causal boundary checks."""
from copy import deepcopy
from datetime import date, timedelta
import json
import math
from pathlib import Path
import statistics

import pytest

from lei_signal.research import risk_shape_information as risk
from lei_signal.research import workflow_inputs as shared
from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research.workflow import run_rehearsal

ROOT=Path(__file__).resolve().parents[2]
DRAFT=ROOT/'docs/experiments/raw/risk-shape-information-2026-10-03/draft-vol_instability20-main.json'


def fixture(n=530):
    days=[(date(2023,1,1)+timedelta(days=i)).isoformat() for i in range(n)]
    bars=[]
    for j,asset in enumerate(('synthetic-A','synthetic-B')):
        for i,day in enumerate(days):
            price=100+j+0.07*i+3*math.sin(i/6+j/2)+1.3*math.sin(i/13)
            bars.append(dict(asset=asset,date=day,status='quoted',open=price,high=price+1,
                             low=price-1,close=price,action_known=True))
    c=json.loads(DRAFT.read_text())
    c['universe']['assets']=['synthetic-A','synthetic-B']
    c['feature']['anchor_asset']='synthetic-A'
    c['question']['period']=[days[0],days[-1]]
    return dict(data_mode='synthetic',calendar=days,bars=bars),c


def test_independent_three_formulas_and_price_scale():
    p,_=fixture()
    a=[r['close'] for r in p['bars'][:530]][:271]
    b=[r['close'] for r in p['bars'][530:]][:271]
    actual=risk.candidate_values(b,a)
    own=[100*(b[i]/b[i-1]-1) for i in range(211,271)]
    market=[100*(a[i]/a[i-1]-1) for i in range(211,271)]
    rolling=[statistics.stdev(own[i-4:i+1]) for i in range(40,60)]
    assert actual['vol_instability20']==pytest.approx(statistics.stdev(rolling)/statistics.mean(rolling))
    def independent_beta(indices):
        xx=[market[i] for i in indices]; yy=[own[i] for i in indices]
        return statistics.covariance(xx,yy)/statistics.variance(xx)
    assert actual['beta_asymmetry60']==pytest.approx(independent_beta([i for i,x in enumerate(market) if x<0])-independent_beta([i for i,x in enumerate(market) if x>0]))
    negative=[x<0 for x in own]
    previous_neg=[negative[i+1] for i in range(59) if negative[i]]
    previous_other=[negative[i+1] for i in range(59) if not negative[i]]
    assert actual['negative_cluster60']==pytest.approx(sum(previous_neg)/len(previous_neg)-sum(previous_other)/len(previous_other))
    assert risk.candidate_values([x*7 for x in b],[x*11 for x in a])==pytest.approx(actual)


def test_candidate_denominator_and_conditional_variance_boundaries():
    assert risk.candidate_values([100.0]*61,[100.0]*61)=={
        'vol_instability20':None,'beta_asymmetry60':None,'negative_cluster60':None}
    # Two conditional anchor groups vary by less than the frozen variance floor.
    market=[-1.0-1e-8*(i%3) if i%2 else 1.0+1e-8*(i%3) for i in range(60)]
    anchor=[100.0]
    own=[100.0]
    for r in market:
        anchor.append(anchor[-1]*(1+r/100))
        own.append(own[-1]*(1+(r*0.7+0.1)/100))
    assert risk.candidate_values(own,anchor)['beta_asymmetry60'] is None


def test_common_clock_anchor_and_prefix_without_labels(monkeypatch):
    p,c=fixture()
    monkeypatch.setattr(shared,'_label',lambda *a,**k: pytest.fail('outcome accessed'))
    prepared=risk.prepare_risk_shape_observations(p,c)
    assert prepared['coverage']['per_asset']['synthetic-A']['anchor_excluded']==530
    rows=prepared['observations']
    assert len(rows)==1060
    assert all(not r['eligible'] and r['feature_reason']=='anchor_excluded' for r in rows[:530])
    assert rows[530+250]['ready_252'] is False
    assert rows[530+251]['ready_252'] is True
    short=deepcopy(p); short['bars']=[r for r in p['bars'] if r['date']<=p['calendar'][300]]
    assert risk.prepare_risk_shape_observations(short,c)['observations'][:602]==rows[:301]+rows[530:831]
    for asset in ('synthetic-A','synthetic-B'):
        q=deepcopy(p)
        row=next(r for r in q['bars'] if r['asset']==asset and r['date']==p['calendar'][275])
        row.update(status='vendor_missing',open=None,high=None,low=None,close=None)
        changed=risk.prepare_risk_shape_observations(q,c)['observations']
        target=changed[530:]
        assert not target[526]['ready_252'] and target[527]['ready_252']
        assert target[274]['features']==rows[530+274]['features']


def test_contract_refusals_and_six_rehearsals():
    import glob
    for name in risk.REFS:
        for mode in ('main','solo'):
            path=DRAFT.parent/f'draft-{name}-{mode}.json'
            c=json.loads(path.read_text())
            validate_workflow_contract(c)
            wrong=deepcopy(c); wrong['feature']['candidate']='other'
            with pytest.raises(ValueError): validate_workflow_contract(wrong)
            wrong=deepcopy(c); wrong['evaluator']['baseline_features']=[]
            with pytest.raises(ValueError): validate_workflow_contract(wrong)
            result=run_rehearsal(c)
            assert result['fits']==2 and result['performance']
            assert result['coverage']['anchor_excluded']==600
            assert result['coverage']['common_ready']>0


def test_exact_target_and_authorization():
    p,c=fixture()
    for key,value in (('path_field','low'),('end_offset',20),('price_measure','provider_index_price')):
        wrong=deepcopy(c); wrong['target'][key]=value
        with pytest.raises(ValueError): risk.prepare_risk_shape_observations(p,wrong)
    real=deepcopy(p); real['data_mode']='historical_reconstruction'
    c['permissions']['real_labels']=False
    with pytest.raises(ValueError,match='authorization'):
        risk.prepare_risk_shape_observations(real,c,compute_labels=True)


def test_snapshot_cutoff_censors_future_labels():
    p,c=fixture()
    p['decision_at']=p['calendar'][300]+'T16:00:00'
    rows=risk.prepare_risk_shape_observations(p,c,compute_labels=True)['observations'][301:]
    assert rows[280]['y'] is None
    assert rows[280]['target_label_reason']=='immature_label'
    assert rows[278]['label_end']==p['calendar'][299]


def test_qualification_is_source_only_and_counts_anchor(monkeypatch):
    p,c=fixture()
    monkeypatch.setattr(risk,'qualify_top_panel',lambda *a: {'quality':{},'warnings':[]})
    monkeypatch.setattr(shared,'_label',lambda *a,**k: pytest.fail('future outcome accessed'))
    q=risk.build_qualification(p,c,ROOT)
    assert q['outcome_values_used_for_design'] is False
    assert q['counts']['assets']==2 and q['counts']['observations']==1060
    assert q['coverage']['anchor_excluded']==530
    assert q['coverage']['common_ready']>0
