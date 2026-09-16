import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from lei_signal.storage import sqlite_store as new

raw=Path(__file__).resolve().parent
oldpath=Path('/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/agent-03b-runtime-integration-2026-09-09/backup/runtime/src/lei_signal/storage/sqlite_store.py')
spec=importlib.util.spec_from_file_location('old_sqlite_store',oldpath)
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
assert list(new.MIGRATIONS[:len(old.MIGRATIONS)])==list(old.MIGRATIONS),'old migration changed'
with tempfile.TemporaryDirectory(prefix='lei-migration-integration-') as tmp:
 db=Path(tmp)/'legacy.db'
 with old.connect(db) as conn:
  conn.execute("INSERT INTO assets(symbol,display_name) VALUES('518880.SS','历史标的')")
  conn.execute("INSERT INTO agent_sessions VALUES('legacy','518880.SS','原会话','2026-09-01','2026-09-01')")
  conn.execute("INSERT INTO agent_messages(session_id,role,content,created_at) VALUES('legacy','user','原问题','2026-09-01')")
  conn.execute("INSERT INTO agent_messages(session_id,role,content,created_at) VALUES('legacy','assistant','原回答','2026-09-01')")
  before={t:[dict(r) for r in conn.execute('SELECT * FROM '+t)] for t in ('assets','agent_sessions','agent_messages')}
 with new.connect(db) as conn:
  for table,rows in before.items():
   columns=list(rows[0]);actual=[dict(r) for r in conn.execute('SELECT '+','.join(columns)+' FROM '+table)]
   assert actual==rows,table
  assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert not conn.execute('PRAGMA foreign_key_check').fetchall()
  assert new.apply_migrations(conn)==()
  assert all(r['question_id'] is None for r in conn.execute('SELECT question_id FROM agent_messages'))
  added=[r['name'] for r in conn.execute('SELECT name FROM schema_migrations WHERE ordinal>22')]
  assert len(added)==7
  counts={t:conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('agent_backtest_requests','agent_chat_requests','agent_plan_draft_bindings','agent_observations')}
  assert not any(counts.values())
 result={'old_migrations_unchanged':True,'original_rows_preserved':True,'legacy_question_binding_unknown':True,'integrity':'ok','idempotent':True,'new_migrations':added,'new_business_rows':counts,'real_database_accessed':False}
(raw/'migration-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
