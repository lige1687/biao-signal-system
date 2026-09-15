"""Independent probes; temporary databases, no model or external network calls."""
import json
import sqlite3
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from starlette.requests import Request
from lei_signal.storage.write_tx import TrackedConnection, active_writers_snapshot
from lei_signal.storage.sqlite_store import connect
from lei_signal.api.routes import agent

results = {}
with tempfile.TemporaryDirectory() as temp:
    db = str(Path(temp) / 'tx.db')
    setup = sqlite3.connect(db)
    setup.execute('CREATE TABLE t (x INTEGER)')
    setup.commit()
    setup.close()
    c = sqlite3.connect(db, factory=TrackedConnection)
    c.cursor().execute('INSERT INTO t VALUES(1)')
    results['cursor_write'] = {'transaction_open': c.in_transaction, 'tracked': active_writers_snapshot()}
    c.rollback()
    c.execute('BEGIN')
    results['deferred_begin_without_write'] = active_writers_snapshot()
    c.rollback()
    holder = sqlite3.connect(db)
    holder.execute('BEGIN IMMEDIATE')
    c.execute('PRAGMA busy_timeout=20')
    try:
        c.execute('INSERT INTO t VALUES(2)')
    except sqlite3.OperationalError as exc:
        results['failed_waiter_registered_as_writer'] = {'error': str(exc), 'tracked': active_writers_snapshot()}
    c.rollback()
    holder.rollback()
    holder.close()
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('CREATE TABLE parent(id INTEGER PRIMARY KEY)')
    c.execute('CREATE TABLE child(pid INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)')
    c.commit()
    try:
        with c:
            c.execute('INSERT INTO child VALUES(99)')
    except sqlite3.IntegrityError:
        results['commit_failure'] = {'transaction_still_open': c.in_transaction, 'uncommitted_rows': c.execute('SELECT COUNT(*) FROM child').fetchone()[0]}
    c.rollback()
    c.close()
    plain = sqlite3.connect(db)
    plain.execute('PRAGMA foreign_keys=ON')
    try:
        with plain:
            plain.execute('INSERT INTO child VALUES(99)')
    except sqlite3.IntegrityError:
        results['commit_failure_native'] = {'transaction_still_open': plain.in_transaction, 'uncommitted_rows': plain.execute('SELECT COUNT(*) FROM child').fetchone()[0]}
    plain.close()

    chatdb = str(Path(temp) / 'chat.db')
    connect(chatdb).close()
    app = FastAPI()
    app.state.plans_db_path = chatdb
    app.state.watchlist_db_path = chatdb
    request = Request({'type':'http', 'method':'POST', 'path':'/', 'headers':[], 'app':app})
    body = agent.AgentChatRequest(context_kind='global', message='合成问题', client_request_id='controller-early-close')
    gate, finished = threading.Event(), threading.Event()
    original_enter = agent._enter_chat
    def delayed_enter(*args, **kwargs):
        assert gate.wait(5)
        return original_enter(*args, **kwargs)
    def fake_prepare(*args, **kwargs):
        finished.set()
        return (kwargs['session_id'], [], {}, [], None, {})
    # Capture the synchronous iterator supplied to the real HTTP response wrapper.
    # This isolates its cancellation contract without an HTTP client's buffering.
    with patch('fastapi.responses.StreamingResponse', lambda content, **kw: content), patch.object(agent, '_enter_chat', delayed_enter), patch.object(agent, '_prepare_discussion', fake_prepare):
        stream = agent.agent_chat_stream(request, body)
        first = next(stream)
        stream.close()
        gate.set()
        assert finished.wait(5)
    c = sqlite3.connect(chatdb)
    state = c.execute('SELECT answer_state FROM agent_chat_requests WHERE client_request_id=?', (body.client_request_id,)).fetchone()[0]
    c.close()
    retry = original_enter(request, body)
    results['close_after_receipt_before_identity'] = {'received': '已收到问题' in first, 'state_after_worker_finished': state, 'retry_kind': retry.kind}

out = Path(__file__).with_name('results.json')
out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(out.read_text())
