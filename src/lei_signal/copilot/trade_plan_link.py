"""Current plan association, never a historical execution snapshot."""
from __future__ import annotations

import re
import sqlite3

from lei_signal.api.portfolio_workspace import _fund_suffix
from lei_signal.plans.store import get_plan, list_plans

ELIGIBLE_STATES = frozenset({'armed', 'entered', 'exited'})
NOTE_CN = '关联的是当前记录中的计划，不能证明事前已确认该计划；未关联时原计划情况未知。'


def _symbols(fund_code: str) -> set[str]:
    if not re.fullmatch(r'[0-9]{6}', fund_code):
        raise ValueError('fund_code 必须为六位数字代码')
    symbols = {f'{fund_code}.OF'}
    suffix = _fund_suffix(fund_code)
    if suffix:
        symbols.add(f'{fund_code}.{suffix}')
    return symbols


def candidate_plans(conn: sqlite3.Connection, fund_code: str) -> dict:
    symbols = _symbols(fund_code)
    plans = [p for symbol in sorted(symbols) for p in list_plans(conn, symbol=symbol)
             if p.state in ELIGIBLE_STATES]
    plans.sort(key=lambda p: (p.created_at, p.plan_id), reverse=True)
    return {'fund_code': fund_code, 'plans': [
        {key: getattr(p, key) for key in
         ('plan_id', 'symbol', 'state', 'reason', 'created_at', 'updated_at')}
        for p in plans], 'note_cn': NOTE_CN}


def validate_plan_link(conn: sqlite3.Connection, fund_code: str, plan_id: str) -> None:
    symbols = _symbols(fund_code)
    plan = get_plan(conn, plan_id)
    if plan is None or plan.symbol not in symbols or plan.state not in ELIGIBLE_STATES:
        raise ValueError('关联计划不存在、产品身份不一致或状态不可关联')
