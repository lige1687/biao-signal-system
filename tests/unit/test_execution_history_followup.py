"""Execution history using synthetic SQLite and injected analysis only."""
import sqlite3
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lei_signal.storage.sqlite_store import connect
from lei_signal.plans import store
from lei_signal.copilot import trades
from lei_signal.api.routes import plans as routes

@pytest.fixture
def env(tmp_path):
    db=tmp_path/'synthetic.db';c=connect(db)
    app=FastAPI();app.state.plans_db_path=str(db);app.include_router(routes.router)
    yield c,TestClient(app),app
    c.close()

def draft(c, **over):
    data=dict(symbol='510300.SS',module='A',direction='long',ruleset_version='test',reason='理由',valid_until='2099-12-31',entry_price_ref=1,invalidation_price=.9,thesis_cn='草稿',invalidation_criteria_cn='失效',drawdown_playbook_cn='回撤',take_profit_plan_cn='止盈',stop_plan_cn='退出')
    data.update(over);return store.create_plan(c,**data)

def versions(c,pid):
    from lei_signal.plans.evidence import list_plan_versions
    return list_plan_versions(c,pid)

def action(c,p,kind='ENTER'):
    return store.upsert_action_item(c,plan_id=p.plan_id,kind=kind,source_alert_code='test',state='open',due_from='2026-09-01')

def test_confirmation_and_revision_are_complete_immutable(env):
    c,client,_=env;p=draft(c);store.update_draft(c,p.plan_id,{'thesis_cn':'编辑后','entry_price_ref':1.2})
    store.confirm_plan(c,p.plan_id)
    first=versions(c,p.plan_id)[0]
    assert first['event_kind']=='initial_confirmation'
    assert first['payload']['thesis_cn']=='编辑后' and first['payload']['entry_price_ref']==1.2
    assert first['payload']['state']=='armed' and first['payload']['symbol']=='510300.SS'
    store.append_revision(c,p.plan_id,changed_field='invalidation_price',old_value='.9',new_value='1',verdict='within_playbook',verdict_reason_cn='收紧',changed_by='user',apply_change=True)
    vs=versions(c,p.plan_id);assert len(vs)==2 and vs[0]==first
    assert vs[1]['event_kind']=='applied_revision' and vs[1]['payload']['invalidation_price']==1
    with pytest.raises(sqlite3.IntegrityError):c.execute('UPDATE trade_plan_versions SET payload_json=? WHERE version_id=?',('{}',first['version_id']))
    c.rollback()
    with pytest.raises(sqlite3.IntegrityError):c.execute('DELETE FROM trade_plan_versions WHERE version_id=?',(first['version_id'],))
    c.rollback()
    summary=client.get(f'/api/plans/{p.plan_id}/versions').json()
    assert len(summary['versions'])==2 and all('payload' not in v for v in summary['versions'])

def test_confirmation_rollback_no_half_state(env,monkeypatch):
    from lei_signal.plans import evidence
    c,_,_=env;p=draft(c)
    monkeypatch.setattr(evidence,'record_plan_version',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('injected')))
    with pytest.raises(RuntimeError):store.confirm_plan(c,p.plan_id)
    assert store.get_plan(c,p.plan_id).state=='draft' and versions(c,p.plan_id)==[]

def test_confirmation_analysis_edit_conflicts(env,monkeypatch):
    c,client,app=env;p=draft(c)
    def get(symbol):
        changed=connect(app.state.plans_db_path)
        store.update_draft(changed,p.plan_id,{'reason':'分析期间改动'})
        changed.close()
        return SimpleNamespace(result=object())
    app.state.analysis_service=SimpleNamespace(get=get)
    monkeypatch.setattr(routes,'context_from_result',lambda r:SimpleNamespace(ruleset_version='test'))
    monkeypatch.setattr(routes,'evaluate_draft_conformance',lambda *a:SimpleNamespace(can_confirm=True))
    r=client.post(f'/api/plans/{p.plan_id}/confirm')
    assert r.status_code==409 and store.get_plan(c,p.plan_id).state=='draft' and versions(c,p.plan_id)==[]

def test_trade_auto_pins_after_retry_lookup_and_legacy_stays_unknown(env):
    c,_,_=env;p=draft(c);store.confirm_plan(c,p.plan_id)
    args=dict(fund_code='510300',fund_name='测试',side='buy',amount=100,trade_date='2026-09-01',plan_id=p.plan_id,request_id='same')
    first=trades.create_trade(c,**args);c.commit()
    assert first.plan_version_id==versions(c,p.plan_id)[0]['version_id']
    store.append_revision(c,p.plan_id,changed_field='thesis_cn',old_value='草稿',new_value='后来',verdict='within_playbook',verdict_reason_cn='x',changed_by='user',apply_change=True)
    again=trades.create_trade(c,**args)
    assert again.trade_id==first.trade_id and again.plan_version_id==first.plan_version_id
    args['request_id']='new';new=trades.create_trade(c,**args);c.commit()
    assert new.plan_version_id==versions(c,p.plan_id)[-1]['version_id']
    legacy=draft(c);c.execute("UPDATE trade_plans SET state='armed' WHERE plan_id=?",(legacy.plan_id,));c.commit()
    args.update(plan_id=legacy.plan_id,request_id='old');assert trades.create_trade(c,**args).plan_version_id is None

@pytest.mark.parametrize('day',['2026-02-30','2026-9-01','2099-01-01','garbage'])
def test_bad_completion_date_refuses_zero_writes(env,day):
    c,client,_=env;p=draft(c);store.confirm_plan(c,p.plan_id);a=action(c,p)
    r=client.post(f'/api/plans/{p.plan_id}/actions/{a.action_id}/done',json={'actual_action_date':day})
    assert r.status_code==422 and store.get_action_item(c,a.action_id).state=='open'

def test_completion_identity_unknown_date_and_ownership(env):
    c,client,_=env;p=draft(c);store.confirm_plan(c,p.plan_id);a=action(c,p);other=draft(c,symbol='159915.SZ')
    assert client.post(f'/api/plans/{other.plan_id}/actions/{a.action_id}/done').status_code==404
    assert store.get_action_item(c,a.action_id).state=='open'
    first=client.post(f'/api/plans/{p.plan_id}/actions/{a.action_id}/done').json()
    assert first['actual_action_date'] is None and first['done_recorded_at'] and first['done_source']=='web'
    assert first['completion_evidence_supported'] is True
    assert store.get_plan(c,p.plan_id).entered_on is None
    assert client.post(f'/api/plans/{p.plan_id}/actions/{a.action_id}/done').json()==first
    assert client.post(f'/api/plans/{p.plan_id}/actions/{a.action_id}/done',json={'actual_action_date':'2026-09-02'}).status_code==409

def test_declared_date_and_supersede_rollback(env,monkeypatch):
    from lei_signal.plans import evidence,actions
    c,client,_=env;p=draft(c);store.confirm_plan(c,p.plan_id);a=action(c,p)
    previous=draft(c);store.confirm_plan(c,previous.plan_id)
    original=actions.handle_supersede
    def fail(conn,entered,**kw):
        original(conn,entered,**kw);raise RuntimeError('after supersede')
    monkeypatch.setattr(actions,'handle_supersede',fail)
    with pytest.raises(RuntimeError):evidence.complete_action(c,p.plan_id,a.action_id,actual_action_date='2026-09-03',source='web')
    assert store.get_action_item(c,a.action_id).state=='open'
    assert store.get_plan(c,p.plan_id).state=='armed' and store.get_plan(c,previous.plan_id).state=='armed'
    monkeypatch.setattr(actions,'handle_supersede',original)
    r=client.post(f'/api/plans/{p.plan_id}/actions/{a.action_id}/done',json={'actual_action_date':'2026-09-03'})
    assert r.status_code==200 and r.json()['due_from']=='2026-09-01' and r.json()['actual_action_date']=='2026-09-03'
    assert r.json()['closed_on'] is None
    assert store.get_plan(c,p.plan_id).entered_on=='2026-09-03'

def test_old_done_is_not_backfilled(env):
    c,client,_=env;p=draft(c);store.confirm_plan(c,p.plan_id);a=action(c,p)
    store.update_action_item(c,a.action_id,state='done')
    r=client.post(f'/api/plans/{p.plan_id}/actions/{a.action_id}/done').json()
    assert r['done_recorded_at'] is None and r['actual_action_date'] is None

def test_holding_confirmation_and_unapplied_revision(env):
    import hashlib,json
    c,_,_=env
    p=draft(c,plan_kind='holding_watch',take_profit_price=1.5,stop_price=.8,watch_signal_rule_ids=('test_rule',))
    store.confirm_holding_watch(c,p.plan_id,entered_on='2026-09-01')
    v=versions(c,p.plan_id)[0]
    assert v['payload']['state']=='entered' and v['payload']['stop_price']==.8
    assert v['payload']['watch_signal_rule_ids']==['test_rule']
    raw=json.dumps(v['payload'],ensure_ascii=False,sort_keys=True,separators=(',',':'))
    assert hashlib.sha256(raw.encode()).hexdigest()==v['content_sha256']
    store.append_revision(c,p.plan_id,changed_field='thesis_cn',old_value='草稿',new_value='未采纳',verdict='needs_review',verdict_reason_cn='待核',changed_by='user',apply_change=False)
    assert versions(c,p.plan_id)==[v]

def test_applied_revision_failure_rolls_back_and_legacy_has_no_version(env,monkeypatch):
    from lei_signal.plans import evidence
    c,_,_=env;p=draft(c);store.confirm_plan(c,p.plan_id)
    count=len(store.list_revisions(c,p.plan_id))
    monkeypatch.setattr(evidence,'record_plan_version',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('version write failure')))
    with pytest.raises(RuntimeError):
        store.append_revision(c,p.plan_id,changed_field='thesis_cn',old_value='草稿',new_value='不可保留',verdict='within_playbook',verdict_reason_cn='测试',changed_by='user',apply_change=True)
    assert store.get_plan(c,p.plan_id).thesis_cn=='草稿'
    assert len(store.list_revisions(c,p.plan_id))==count and len(versions(c,p.plan_id))==1
    old=draft(c);c.execute("UPDATE trade_plans SET state='armed' WHERE plan_id=?",(old.plan_id,));c.commit()
    store.append_revision(c,old.plan_id,changed_field='thesis_cn',old_value='草稿',new_value='旧计划现修改',verdict='within_playbook',verdict_reason_cn='测试',changed_by='user',apply_change=True)
    assert versions(c,old.plan_id)==[]

def test_completion_rejects_invalid_plan_state_and_fields_are_immutable(env):
    c,client,_=env;p=draft(c);a=action(c,p)
    url=f'/api/plans/{p.plan_id}/actions/{a.action_id}/done'
    assert client.post(url).status_code==409 and store.get_action_item(c,a.action_id).state=='open'
    store.confirm_plan(c,p.plan_id)
    first=client.post(url,json={'actual_action_date':'2026-09-04'}).json()
    with pytest.raises(sqlite3.IntegrityError):
        c.execute('UPDATE plan_action_items SET actual_action_date=? WHERE action_id=?',('2026-09-05',a.action_id))
    c.rollback()
    assert store.get_action_item(c,a.action_id).actual_action_date==first['actual_action_date']

def test_shanghai_date_boundary(env,monkeypatch):
    from datetime import datetime as RealDatetime, UTC
    from lei_signal.plans import evidence
    class FrozenDatetime(RealDatetime):
        @classmethod
        def now(cls,tz=None):
            frozen=RealDatetime(2026,10,7,16,30,tzinfo=UTC)
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)
    monkeypatch.setattr(evidence,'datetime',FrozenDatetime)
    assert evidence.validate_action_date('2026-10-08')=='2026-10-08'
    with pytest.raises(ValueError):evidence.validate_action_date('2026-10-09')

def test_concurrent_completion_keeps_one_first_record(env):
    from concurrent.futures import ThreadPoolExecutor
    from lei_signal.plans.evidence import complete_action
    c,_,app=env;p=draft(c);store.confirm_plan(c,p.plan_id);a=action(c,p)
    def complete(_):
        conn=connect(app.state.plans_db_path)
        try:return complete_action(conn,p.plan_id,a.action_id,actual_action_date='2026-09-04',source='web')
        finally:conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first,second=list(pool.map(complete,[1,2]))
    assert first==second and first.done_recorded_at
    assert store.get_plan(c,p.plan_id).state=='entered'

def test_feishu_unknown_date_uses_same_first_evidence(env,monkeypatch):
    from urllib.parse import parse_qs,urlparse
    from lei_signal.api.routes import feishu_webhook
    from lei_signal.notify.signing import build_action_url
    c,client,app=env;app.include_router(feishu_webhook.router)
    monkeypatch.setenv('FEISHU_ACTION_SECRET','synthetic-secret')
    p=draft(c);store.confirm_plan(c,p.plan_id);store.set_entered(c,p.plan_id,entered_on='2026-09-01');a=action(c,p,'EXIT')
    url=build_action_url('https://lei.example.test','synthetic-secret',p.plan_id,a.action_id,ttl_seconds=900)
    form={k:v[0] for k,v in parse_qs(urlparse(url).query).items()};form['operation']='done'
    first=client.post('/api/feishu-webhook/action/submit',data=form)
    assert first.status_code==200
    saved=store.get_action_item(c,a.action_id)
    assert saved.done_source=='feishu' and saved.done_recorded_at and saved.actual_action_date is None
    assert store.get_plan(c,p.plan_id).exited_on is None
    assert client.post('/api/feishu-webhook/action/submit',data=form).status_code==200
    assert store.get_action_item(c,a.action_id)==saved

def test_concurrent_revision_before_trade_insert_pins_latest(env):
    c,_,app=env;p=draft(c);store.confirm_plan(c,p.plan_id)
    class BeforeInsert:
        def execute(self,sql,args=()):
            if sql.lstrip().startswith('INSERT INTO fund_trades'):
                other=connect(app.state.plans_db_path)
                try:
                    store.append_revision(other,p.plan_id,changed_field='thesis_cn',old_value='草稿',new_value='同时保存的新版本',verdict='within_playbook',verdict_reason_cn='测试',changed_by='user',apply_change=True)
                finally:other.close()
            return c.execute(sql,args)
    saved=trades.create_trade(BeforeInsert(),fund_code='510300',fund_name='测试',side='buy',amount=100,trade_date='2026-09-01',plan_id=p.plan_id,request_id='race')
    c.commit()
    assert saved.plan_version_id==versions(c,p.plan_id)[-1]['version_id']

def test_corrupt_version_review_declines_without_error(env,monkeypatch):
    from lei_signal.plans import evidence
    from lei_signal.copilot.review import build_trade_review
    c,_,_=env;p=draft(c);store.confirm_plan(c,p.plan_id)
    saved=trades.create_trade(c,fund_code='510300',fund_name='测试',side='buy',amount=100,trade_date='2026-09-01',plan_id=p.plan_id)
    c.commit()
    monkeypatch.setattr(evidence,'get_plan_version',lambda *a:(_ for _ in ()).throw(ValueError('fingerprint mismatch')))
    review=build_trade_review(c,saved.trade_id)
    assert any('内容核对未通过' in line for section in review.sections for line in section.lines)
