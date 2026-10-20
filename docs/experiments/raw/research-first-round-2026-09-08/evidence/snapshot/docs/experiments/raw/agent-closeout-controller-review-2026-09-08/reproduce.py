"""Independent acceptance probes. Temporary DBs/synthetic data; no production writes.

Run from repo root: PYTHONPATH=src python3.11 <this file>
Each probe records expected acceptance vs observed behavior and continues on failure.
"""
from __future__ import annotations
import copy
import dataclasses
import hashlib
import importlib.util
import io
import json
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from lei_signal import data_provenance as dp
from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal, observation as ob
from lei_signal.storage.sqlite_store import connect

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
RESULTS = {}

def card(symbol='A', date='2026-08-03'):
    return RecommendCardDTO(run_date=date, items=[RecommendItemDTO(symbol=symbol, verdict='waiting')])

def service():
    frame = pd.DataFrame({'close': np.arange(22)+100.}, index=pd.bdate_range('2026-08-03', periods=22))
    return SimpleNamespace(get=lambda _: SimpleNamespace(result=SimpleNamespace(frame=frame)))

def rec(c, symbol='A', shown=True, emitted_at=None):
    return ob.record_observations(c, source_type='recommendation', source_record_id='2026-08-03',
        observed_at='2026-08-03', evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=ob.RECOMMENDATION_EVAL_VERSION, shown=shown, emitted_at=emitted_at,
        items=[ob.ObservationItem(instrument_id=symbol, payload={'close':100}, claim='watch', horizons=(1,))])

def module():
    spec = importlib.util.spec_from_file_location('controller_closeout_sentiment', ROOT/'scripts/sentiment_journal.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def rows(c, sql, args=()):
    return [dict(r) for r in c.execute(sql, args)]

def current(c):
    return sorted(ob.current_claim_ids(c))

def q1(c, td):
    original = dp.ruleset_ref()
    for ver, date in [('fixture_v1','2026-08-03'), ('fixture_v2','2026-08-04')]:
        with patch.object(dp, 'ruleset_ref', return_value=dataclasses.replace(original, version=ver, config_hash=ver)):
            journal.save_recommendation(c, card(date=date))
    b = [x for x in ob.summarize(c)['buckets'] if x['evaluation_version']==ob.RECOMMENDATION_EVAL_VERSION and x['horizon_days']==1]
    return len(b)==2, {'expected_rule_groups':2,'actual_rule_groups':len(b),'buckets':b,
        'frozen_rules':rows(c,"SELECT rule_refs,rule_refs_frozen FROM agent_observations WHERE record_type='claim'")}

def q2(c, td):
    m=module(); path=td/'sync.db'; m._open_ledger_db=lambda:connect(path)
    fixture={'records':[{'date':'2026-08-03','picks':[{'code':'BK1','close':100.}],
                         'alarms':[],'origin':'live','content_hash':'same-input','as_of':'2026-08-03T18:00:00+08:00'}]}
    original=dp.rule_ref
    m._sync_observations(fixture)
    with connect(path) as read:
        before=rows(read,"SELECT observation_id,rule_refs_frozen FROM agent_observations WHERE record_type='claim'")
    def revised(key, **kwargs):
        return dataclasses.replace(original(key, **kwargs), version='fixture_new_version',config_hash='fixture_new_content')
    with patch.object(dp,'rule_ref',side_effect=revised):
        result=m._sync_observations(fixture)
    with connect(path) as read:
        after=rows(read,"SELECT observation_id,observed_at,emitted_at,rule_refs_frozen FROM agent_observations WHERE record_type='claim'")
        batches=read.execute("SELECT COUNT(*) FROM agent_observations WHERE record_type='display_batch'").fetchone()[0]
    return len(after)==len(before) and batches==1, {'same_source_revision':True,'sync_result':result,
        'claims_before':len(before),'claims_after':len(after),'batches_after':batches,'after':after}

def q3(c, td):
    rec(c,'A',True)
    before=current(c)
    rec(c,'B',False)
    summary=ob.summarize(c)
    after=current(c)
    return before==after and summary['display_batches']=={'recommendation':1}, {
        'shown_A_before':before,'current_after_hidden_B':after,'summary':summary,
        'records':rows(c,'SELECT instrument_id,record_type,display_status,superseded_by FROM agent_observations')}

def q4(c, td):
    with patch.object(ob,'_now',return_value='2026-08-03T10:00:00+00:00'):
        rec(c,shown=False,emitted_at='2026-08-03T10:00:00+00:00')
    with patch.object(ob,'_now',return_value='2026-08-20T10:00:00+00:00'):
        rec(c,shown=True,emitted_at='2026-08-20T10:00:00+00:00')
    ob.evaluate_recommendation_outcomes(c,service(),as_of='2026-08-04')
    ready=rows(c,"SELECT o.observed_at,o.first_shown_at,oc.eval_date,oc.status FROM agent_observations o JOIN agent_observation_outcomes oc USING(observation_id) WHERE oc.status='ready'")
    return not ready, {'as_of':'2026-08-04','actually_shown':'2026-08-20','ready_before_display':ready}

def q5(c, td):
    journal.save_recommendation(c,card())
    before=current(c)
    ob.backfill_from_recommendation_journal(c)
    after=current(c)
    return before==after, {'live_current_before':before,'current_after_backfill':after,
        'rows':rows(c,"SELECT observation_id,record_type,legacy_quality,first_shown_at,superseded_by FROM agent_observations")}

def q6(c, td):
    m=module(); path=td/'stats.db'; m._open_ledger_db=lambda:connect(path)
    fixture={'records':[]}
    for i,origin in enumerate(['live','live','legacy']):
        fixture['records'].append({'date':'2026-08-03','picks':[{'code':'A','name':f'wording {i}','close':100.}],
            'alarms':[],'origin':origin,'content_hash':f'revision_{i}',
            'review':{'t10':{'A':{'ret':.1,'eval_date':'2026-08-17'}},
                      't20':{'A':{'ret':.1,'eval_date':'2026-08-31'}},'a10':{},'a20':{},'done':True}})
    m._sync_observations(fixture)
    with connect(path) as r:
        ob.evaluate_sentiment_outcomes(r,lambda *args:('2026-08-31',110.),today='2026-09-02')
        b=[x for x in ob.summarize(r)['buckets'] if x['evaluation_version']==ob.SENTIMENT_ROWS_VERSION and x['horizon_days']==10]
    m.CACHE=td; m.JOURNAL=td/'journal.json'
    m.JOURNAL.write_text(json.dumps(fixture)); (td/'sector_trend_history.json').write_text('[]')
    output=io.StringIO()
    with redirect_stdout(output):m.review(save=False,as_of='2026-09-02')
    s=output.getvalue()
    return '到期3个' not in s, {'sqlite_groups':b,'script_output':s,
        'expected':'live same-sample revisions count once; legacy stays separate'}

def q7(c, td):
    m=module(); m.CACHE=td;m.JOURNAL=td/'journal.json';m._open_ledger_db=lambda:None
    (td/'sector_trend_history.json').write_text('[]')
    m.JOURNAL.write_text(json.dumps({'records':[
        {'picks':[{'code':'BAD','close':100.}],'alarms':[]},
        {'date':'2026-08-03','picks':[{'code':'GOOD','close':100.}],'alarms':[]}]}))
    output=io.StringIO(); error=None
    try:
        with redirect_stdout(output): m.review(save=False,as_of='2026-09-02')
    except Exception as exc:error=f'{type(exc).__name__}: {exc}'
    return error is None, {'error':error,'script_output':output.getvalue(),
        'expected':'bad source record isolated by the public review path; good record still reviewed'}

def q8(c, td):
    m=module(); path=td/'invalid.db';m._open_ledger_db=lambda:connect(path)
    result=m._sync_observations({'records':[{'date':'2026-08-03','picks':[{'close':100.}],'alarms':[],'origin':'live'}]})
    with connect(path) as r:s=ob.summarize(r)
    return not s['zero_trigger_days'], {'sync_result':result,'zero_trigger_days':s['zero_trigger_days'],
        'expected':'missing instrument is invalid input, not a verified zero-trigger day'}

def q9(c, td):
    # The legacy writer demonstrably replaced same-symbol content while preserving its
    # previously computed score. Both hashes are absent, exactly the pre-024 shape.
    legacy_namespace={'__name__':'controller_legacy_journal'}
    legacy_source=(OUT/'legacy_journal_HEAD.py').read_text()
    exec(compile(legacy_source,'legacy_journal_HEAD.py','exec'),legacy_namespace)
    legacy_namespace['save_recommendation'](c,card())
    c.execute('UPDATE recommendation_journal SET outcome=?',
              (json.dumps({'A':{'chg_1d':99.}}),))
    replacement=card()
    replacement.items[0].reasons=['changed after score was calculated']
    assert replacement.model_dump_json()!=card().model_dump_json()
    legacy_namespace['save_recommendation'](c,replacement)
    old=c.execute('SELECT payload_hash,outcome_payload_hash,payload,outcome FROM recommendation_journal').fetchone()
    assert old['payload_hash'] is None and old['outcome_payload_hash'] is None
    assert json.loads(old['outcome'])['A']['chg_1d']==99.
    preview=ob.backfill_preview(c)
    ob.backfill_from_recommendation_journal(c)
    migrated=rows(c,"SELECT o.claim,o.legacy_quality,oc.status,oc.change_pct,oc.eval_date FROM agent_observations o JOIN agent_observation_outcomes oc USING(observation_id) WHERE oc.evaluation_version=?",(ob.LEGACY_EVAL_VERSION,))
    return not any(r['legacy_quality']=='legacy' and r['status']=='ready' for r in migrated), {
        'known_unprovable_card_score_binding':True,'preview':preview,'migrated':migrated,
        'expected':'preserve original score as unattributed/unknown; never infer binding from missing hashes'}

sources=['src/lei_signal/copilot/observation.py','src/lei_signal/copilot/journal.py',
         'scripts/sentiment_journal.py','src/lei_signal/data_provenance.py',
         'src/lei_signal/dca/state.py','src/lei_signal/storage/sqlite_store.py',
         'tests/unit/test_integration_closeout.py']
hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
for fn in [q1,q2,q3,q4,q5,q6,q7,q8,q9]:
    with TemporaryDirectory(prefix='lei-closeout-audit-') as t:
        td=Path(t); c=connect(td/'probe.db')
        try:
            accepted,detail=fn(c,td)
            RESULTS[fn.__name__]={'accepted':accepted,'actual':detail}
        except Exception:
            RESULTS[fn.__name__]={'probe_error':traceback.format_exc()}
        finally:c.close()
out={'date':'2026-09-08','temporary_data_only':True,'source_sha256':hashes,'probes':RESULTS,
     'sources_unchanged_during_run':hashes=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}}
(OUT/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
for k,v in RESULTS.items():print(k, 'ERROR' if 'probe_error' in v else 'PASS' if v['accepted'] else 'FAIL')
print('source_snapshot_unchanged:',out['sources_unchanged_during_run'])
sys.exit(1 if any(not v.get('accepted',False) for v in RESULTS.values()) else 0)
