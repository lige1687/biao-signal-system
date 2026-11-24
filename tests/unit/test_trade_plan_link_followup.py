"""Isolated follow-up API chain with synthetic records and no network."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lei_signal.api.routes import copilot
from lei_signal.copilot import trades, review
from lei_signal.plans.store import create_plan
from lei_signal.storage.sqlite_store import connect

@pytest.fixture
def env(tmp_path, monkeypatch):
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / 'synthetic.db')
    app.include_router(copilot.router)
    monkeypatch.setattr(trades, 'fetch_nav_history', lambda *a, **k: [])
    conn = connect(app.state.plans_db_path)
    yield TestClient(app), conn
    conn.close()

def plan(conn, symbol='510300.SS', state='armed'):
    p = create_plan(conn, symbol=symbol, module='A', direction='long', ruleset_version='test', reason='测试当前计划', thesis_cn='当前假设')
    conn.execute('UPDATE trade_plans SET state=? WHERE plan_id=?', (state,p.plan_id))
    conn.commit()
    return p.plan_id

def payload(plan_id=None, request_id='confirmation-1'):
    return dict(fund_code='510300',fund_name='测试ETF',side='buy',amount=1000,trade_date='2026-09-04',plan_id=plan_id,request_id=request_id)

def test_candidates_exact_identity_and_state(env):
    client, conn = env
    eligible = [plan(conn, '510300.SS', s) for s in ('armed','entered','exited')]
    eligible.append(plan(conn, '510300.OF'))
    for sym,state in [('510300.SZ','armed'),('510300','armed'),('510300.SS','draft'),('510300.SS','invalidated'),('000001.SZ','armed')]:
        plan(conn,sym,state)
    body = client.get('/api/copilot/trades/plans?fund_code=510300').json()
    assert body['fund_code']=='510300'
    assert {p['plan_id'] for p in body['plans']} == set(eligible)
    assert all(set(p)=={'plan_id','symbol','state','reason','created_at','updated_at'} for p in body['plans'])
    assert '当前' in body['note_cn'] and '事前' in body['note_cn']
    assert client.get('/api/copilot/trades/plans?fund_code=510300.SS').status_code==422

@pytest.mark.parametrize('symbol,state', [('510300.SZ','armed'),('510300','armed'),('000001.SZ','armed'),('510300.SS','draft'),('510300.SS','invalidated'),('999999.SS','armed')])
def test_reject_invalid_plan_without_insert(env,symbol,state):
    client, conn=env
    r=client.post('/api/copilot/trades',json=payload(plan(conn,symbol,state)))
    assert r.status_code==422
    assert conn.execute('SELECT COUNT(*) FROM fund_trades').fetchone()[0]==0

def test_missing_plan_refused(env):
    client,conn=env
    assert client.post('/api/copilot/trades',json=payload('missing')).status_code==422
    assert conn.execute('SELECT COUNT(*) FROM fund_trades').fetchone()[0]==0

def test_creation_retry_and_changed_plan_conflict(env):
    client,conn=env
    pid=plan(conn)
    first=client.post('/api/copilot/trades',json=payload(pid))
    assert first.status_code==200 and first.json()['plan_id']==pid
    conn.execute("UPDATE trade_plans SET state='invalidated' WHERE plan_id=?",(pid,));conn.commit()
    again=client.post('/api/copilot/trades',json=payload(pid))
    assert again.status_code==200 and again.json()['trade_id']==first.json()['trade_id']
    assert client.post('/api/copilot/trades',json=payload(plan(conn))).status_code==409
    assert client.post('/api/copilot/trades',json=payload('missing')).status_code==409
    assert conn.execute('SELECT COUNT(*) FROM fund_trades').fetchone()[0]==1

def test_review_current_source_preserves_old_cache(env):
    client,conn=env
    tid=client.post('/api/copilot/trades',json=payload()).json()['trade_id']
    old=review.build_trade_review(conn,tid);old.sections[0].lines=['旧缓存内容']
    review.save_review(conn,old);conn.commit()
    saved=conn.execute('SELECT payload,updated_at FROM trade_reviews').fetchone()
    body=client.get('/api/copilot/review/trade/'+tid).json()
    text=' '.join(s['heading_cn']+' '.join(s['lines']) for s in body['sections'])
    assert '未知' in text and '计划外' not in text and '旧缓存内容' not in text
    pid=plan(conn)
    conn.execute('UPDATE fund_trades SET plan_id=? WHERE trade_id=?',(pid,tid));conn.commit()
    body=client.get('/api/copilot/review/trade/'+tid).json()
    text=' '.join(s['heading_cn']+' '.join(s['lines']) for s in body['sections'])
    assert '当前关联计划' in text and '事前' in text and '当初' not in text
    assert tuple(conn.execute('SELECT payload,updated_at FROM trade_reviews').fetchone())==tuple(saved)
    assert client.get('/api/copilot/review/trade/missing').status_code==404

@pytest.mark.parametrize('code,accepted,rejected', [
    ('159915','159915.SZ','159915.SS'),
    ('012414','012414.OF','012414.SS'),
    ('000001','000001.OF','000001.SZ'),
])
def test_identity_requires_explicit_fund_or_correct_etf_exchange(env,code,accepted,rejected):
    client,conn=env
    good=plan(conn,accepted)
    bad=plan(conn,rejected)
    body=client.get('/api/copilot/trades/plans',params={'fund_code':code}).json()
    assert [p['plan_id'] for p in body['plans']]==[good]
    data=payload(good);data['fund_code']=code
    assert client.post('/api/copilot/trades',json=data).status_code==200
    data=payload(bad,'another-confirmation');data['fund_code']=code
    assert client.post('/api/copilot/trades',json=data).status_code==422
    assert conn.execute('SELECT COUNT(*) FROM fund_trades').fetchone()[0]==1

def test_r_reference_is_current_not_initial_snapshot(env):
    from lei_signal.portfolio.funddata import NavPoint
    client,conn=env
    pid=plan(conn)
    conn.execute('UPDATE trade_plans SET entry_price_ref=1,invalidation_price=0.9 WHERE plan_id=?',(pid,))
    trades.create_trade(conn,fund_code='510300',fund_name='测试ETF',side='buy',amount=10000,trade_date='2026-09-01',plan_id=pid)
    sold=trades.create_trade(conn,fund_code='510300',fund_name='测试ETF',side='sell',amount=5000,trade_date='2026-09-10',plan_id=pid)
    trades.price_pending_trades(conn,fetch_nav=lambda *a,**k:[NavPoint(date='2026-09-10',unit_nav=1.25),NavPoint(date='2026-09-01',unit_nav=1)])
    conn.commit()
    first=client.get('/api/copilot/review/trade/'+sold.trade_id).json()
    assert first['r_multiple']==pytest.approx(2)
    conn.execute('UPDATE trade_plans SET invalidation_price=0.95 WHERE plan_id=?',(pid,));conn.commit()
    current=client.get('/api/copilot/review/trade/'+sold.trade_id).json()
    assert current['r_multiple']==pytest.approx(4)
    text=' '.join(line for section in current['sections'] for line in section['lines'])
    assert '按当前计划参考价计算' in text
    assert '初始' not in text and '当初' not in text
