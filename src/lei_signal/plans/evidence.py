"""Recorded plan versions and first user-declared completion evidence."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, date, datetime
import hashlib
import json
import re
import sqlite3
import uuid
from zoneinfo import ZoneInfo

class EvidenceConflict(ValueError):
    pass

class PlanFingerprintConflict(EvidenceConflict):
    pass

@contextmanager
def atomic(conn, *, commit=True):
    if commit and not conn.in_transaction:
        conn.execute('BEGIN IMMEDIATE')
    try:
        yield
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise

def _json(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def plan_fingerprint(plan):
    return hashlib.sha256(_json(asdict(plan)).encode()).hexdigest()

def record_plan_version(conn, plan, *, event_kind, source_revision_id=None):
    payload=_json(asdict(plan))
    version_id='pv_'+uuid.uuid4().hex
    conn.execute('INSERT INTO trade_plan_versions (version_id,plan_id,event_kind,recorded_at,content_sha256,source_revision_id,payload_json) VALUES (?,?,?,?,?,?,?)',
                 (version_id,plan.plan_id,event_kind,datetime.now(UTC).isoformat(),hashlib.sha256(payload.encode()).hexdigest(),source_revision_id,payload))
    return get_plan_version(conn,version_id)

def _version(row):
    if row is None:return None
    payload=json.loads(row['payload_json'])
    if hashlib.sha256(_json(payload).encode()).hexdigest()!=row['content_sha256']:
        raise ValueError('计划版本指纹不一致')
    return {k:row[k] for k in ('version_id','plan_id','event_kind','recorded_at','content_sha256','source_revision_id')} | {'payload':payload}

def list_plan_versions(conn,plan_id):
    return [_version(r) for r in conn.execute('SELECT * FROM trade_plan_versions WHERE plan_id=? ORDER BY rowid',(plan_id,))]

def get_plan_version(conn,version_id):
    return _version(conn.execute('SELECT * FROM trade_plan_versions WHERE version_id=?',(version_id,)).fetchone())

def latest_plan_version(conn,plan_id):
    return _version(conn.execute('SELECT * FROM trade_plan_versions WHERE plan_id=? ORDER BY rowid DESC LIMIT 1',(plan_id,)).fetchone())

def validate_action_date(value):
    if value is None:return None
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):
        raise ValueError('实际动作日期必须为YYYY-MM-DD或未知')
    parsed=date.fromisoformat(value)
    if parsed>datetime.now(ZoneInfo('Asia/Shanghai')).date():
        raise ValueError('实际动作日期不能晚于上海今日')
    return value

def complete_action(conn,plan_id,action_id,*,actual_action_date=None,source='web',commit=True):
    from lei_signal.plans import store, actions
    actual_action_date=validate_action_date(actual_action_date)
    with atomic(conn,commit=commit):
        item=store.get_action_item(conn,action_id)
        if item is None or item.plan_id!=plan_id:
            raise KeyError('待办不存在或不属于该计划')
        if item.state=='done':
            if item.actual_action_date!=actual_action_date:
                raise EvidenceConflict('已完成记录的实际日期声明不同，原记录保留')
            return item
        if item.state!='open':
            raise EvidenceConflict(f'待办当前状态不可完成: {item.state}')
        plan=store.get_plan(conn,plan_id)
        if plan is None:raise KeyError('计划不存在')
        if (item.kind=='ENTER' and plan.state!='armed') or (item.kind=='EXIT' and plan.state!='entered') or (item.kind=='REVIEW' and plan.state=='draft'):
            raise EvidenceConflict(f'计划状态不可完成此动作: {plan.state}')
        if item.kind not in ('ENTER','EXIT','REVIEW'):
            raise EvidenceConflict('未知待办类型')
        now=datetime.now(UTC).isoformat()
        conn.execute("UPDATE plan_action_items SET state='done',close_kind='done',actual_action_date=?,done_recorded_at=?,done_source=? WHERE action_id=?",
                     (actual_action_date,now,source,action_id))
        if item.kind=='ENTER':
            entered=store.set_entered(conn,plan_id,entered_on=actual_action_date,commit=False)
            actions.handle_supersede(conn,entered,commit=False)
        elif item.kind=='EXIT':
            store.set_exited(conn,plan_id,exited_on=actual_action_date,commit=False)
        return store.get_action_item(conn,action_id)
