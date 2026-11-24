"""Independent arithmetic and timing counterexamples for price composition."""
from copy import deepcopy
from datetime import date, timedelta
import json
import math
from pathlib import Path
import pytest
from lei_signal.research import session_composition_information as session
from lei_signal.research import workflow_inputs as shared
from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research.workflow import run_rehearsal

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'docs/experiments/raw/session-composition-information-2026-10-04'
NAME = 'overnight_minus_intraday20'


def fixture(n=530):
    days=[(date(2023,1,1)+timedelta(days=i)).isoformat() for i in range(n)]
    bars=[]
    for j,asset in enumerate(('synthetic-A','synthetic-B')):
        for i,day in enumerate(days):
            price=100+j+0.07*i+3*math.sin(i/6+j/2)+1.3*math.sin(i/13)
            op=price*math.exp(0.002*math.sin(i/5+j))
            bars.append(dict(asset=asset,date=day,status='quoted',open=op,
                high=max(op,price)+1,low=min(op,price)-1,close=price,action_known=True))
    c=json.loads((RAW/'draft-main.json').read_text())
    c['universe']['assets']=['synthetic-A','synthetic-B'];c['feature']['anchor_asset']='synthetic-A'
    c['question']['period']=[days[0],days[-1]]
    return dict(data_mode='synthetic',calendar=days,bars=bars),c


def test_product_identity_and_scale_and_same_total_different_composition():
    closes=[100.0]+[100.0*math.exp(i*.001) for i in range(1,21)]
    opens=[100.0]+[closes[i-1]*math.exp(.002) for i in range(1,21)]
    actual=session.candidate_values(closes,opens)[NAME]
    overnight=100*math.log(math.prod(opens[i]/closes[i-1] for i in range(1,21)))
    daytime=100*math.log(math.prod(closes[i]/opens[i] for i in range(1,21)))
    assert actual==pytest.approx(6.0)
    assert overnight+daytime==pytest.approx(100*math.log(closes[-1]/closes[0]))
    assert actual==pytest.approx(overnight-daytime)
    assert session.candidate_values([x*17 for x in closes],[x*17 for x in opens])[NAME]==pytest.approx(actual)
    alternate=[opens[0]]+closes[:-1]
    assert session.candidate_values(closes,alternate)[NAME]==pytest.approx(-2.0)


def test_flat_invalid_and_effective_cash_split_boundary():
    assert session.candidate_values([100.0]*21,[100.0]*21)[NAME]==0
    assert session.candidate_values([100.0]*20,[100.0]*20)[NAME] is None
    for value in (0,-1,float('nan'),float('inf'),True):
        opens=[100.0]*21;opens[-1]=value
        assert session.candidate_values([100.0]*21,opens)[NAME] is None
    # 100 prior nominal close, ex-date nominal open90/close99 plus cash10.
    closes=[100.0]*20+[109.0]; opens=[100.0]*21
    # Correct economic open stays100, so the known cash removal is not a -10% gap.
    assert session.candidate_values(closes,opens)[NAME]==pytest.approx(-100*math.log(1.09))
    # Split2 with nominal50 and economic100 does not create a price jump.
    assert session.candidate_values([100.0]*21,[100.0]*21)[NAME]==0


def test_prefix_no_labels_warmup_and_missing_anchor():
    p,c=fixture()
    original=shared._label
    shared._label=lambda *a,**k: pytest.fail('future outcomes read during qualification')
    try:
        rows=session.prepare_session_composition_observations(p,c)['observations']
        assert not rows[530+250]['ready_252'] and rows[530+251]['ready_252']
        assert all(not r['eligible'] for r in rows[:530])
        short=deepcopy(p);short['bars']=[r for r in p['bars'] if r['date']<=p['calendar'][300]]
        got=session.prepare_session_composition_observations(short,c)['observations']
        assert got==rows[:301]+rows[530:831]
        q=deepcopy(p)
        r=next(r for r in q['bars'] if r['asset']=='synthetic-A' and r['date']==p['calendar'][275])
        r.update(status='vendor_missing',open=None,high=None,low=None,close=None)
        changed=session.prepare_session_composition_observations(q,c)['observations'][530:]
        assert not changed[526]['ready_252'] and changed[527]['ready_252']
        assert changed[274]['features']==rows[804]['features']
    finally:
        shared._label=original


def test_snapshot_and_authorization_and_exact_target():
    p,c=fixture();p['decision_at']=p['calendar'][300]+'T16:00:00'
    rows=session.prepare_session_composition_observations(p,c,compute_labels=True)['observations'][301:]
    assert rows[280]['y'] is None and rows[278]['label_end']==p['calendar'][299]
    for key,value in [('path_field','low'),('end_offset',20),('price_measure','provider_index_price')]:
        wrong=deepcopy(c);wrong['target'][key]=value
        with pytest.raises(ValueError):session.prepare_session_composition_observations(p,wrong)
    p['data_mode']='historical_reconstruction';c['permissions']['real_labels']=False
    with pytest.raises(ValueError,match='authorization'):
        session.prepare_session_composition_observations(p,c,compute_labels=True)


def test_two_exact_contracts_and_rehearsal():
    for mode in ('main','solo'):
        c=json.loads((RAW/f'draft-{mode}.json').read_text());validate_workflow_contract(c)
        wrong=deepcopy(c);wrong['feature']['lookback']=60
        with pytest.raises(ValueError):validate_workflow_contract(wrong)
        wrong=deepcopy(c);wrong['evaluator']['added_features']=['unapproved']
        with pytest.raises(ValueError):validate_workflow_contract(wrong)
        result=run_rehearsal(c)
        assert result['fits']==2 and result['performance']
        assert result['coverage']['anchor_excluded']==600
