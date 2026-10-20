"""验收A-1：端到端复现「准备阶段失败：database is locked」。

对隔离服务的新临时库，从本进程持写锁（BEGIN IMMEDIATE）35 秒（模拟
持续持锁的后台写者），同时向真实 /api/agent/chat/stream 发首问，逐 SSE
事件记录墙钟时间。预期：~30s busy_timeout 等待后收到
「准备阶段失败：database is locked」，且隔离服务日志出现对应 traceback。
锁释放后重发同一问题：应正常进入流程且不产生重复问题记录。
"""
import json
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

DB = sys.argv[1]
OUT = Path(__file__).parent / "acceptance-A-db-lock.json"
QUESTION = "510300 最近怎么看？先说判断，再讲机会和风险，现有依据够不够？"
URL = "http://127.0.0.1:8021/api/agent/chat/stream"

timeline: list[dict] = []


def ts() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def read_sse(tag: str) -> None:
    import requests
    t0 = time.time()
    timeline.append({"t": ts(), "event": f"{tag}:request_sent",
                     "since_start_s": 0.0})
    resp = requests.post(URL, json={"context_kind": "symbol", "symbol": "510300",
                                    "message": QUESTION}, stream=True, timeout=120)
    timeline.append({"t": ts(), "event": f"{tag}:http_status",
                     "data": resp.status_code,
                     "since_start_s": round(time.time() - t0, 3)})
    ev = {}
    for line in resp.iter_lines(decode_unicode=True):
        if line is None:
            continue
        if line.startswith("event:"):
            ev["name"] = line[6:].strip()
        elif line.startswith("data:"):
            ev["data"] = line[5:].strip()
            timeline.append({
                "t": ts(),
                "event": f"{tag}:{ev.get('name')}",
                "data": json.loads(ev["data"]),
                "since_start_s": round(time.time() - t0, 3),
            })
            if ev.get("name") == "done":
                break


def hold_lock(seconds: float) -> None:
    conn = sqlite3.connect(DB, timeout=1)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS lock_probe (id INTEGER PRIMARY KEY, t TEXT)")
    conn.execute("INSERT INTO lock_probe (t) VALUES (?)", (ts(),))
    # 注意：不提交——保持写事务开启，整个 sleep 期间持有写锁；结束时回滚。
    print(f"[{ts()}] write lock held (uncommitted) for {seconds}s", flush=True)
    time.sleep(seconds)
    conn.rollback()
    conn.close()
    print(f"[{ts()}] lock released", flush=True)


# —— 第一问：持锁期间发出 ——
holder = threading.Thread(target=hold_lock, args=(35.0,))
holder.start()
time.sleep(0.5)  # 确保锁已拿到
read_sse("attempt1")
holder.join()

# —— 第二问：锁已释放，重发同一问题 ——
timeline.append({"t": ts(), "event": "lock_released_retry_next"})
read_sse("attempt2")

# —— 业务记录核对：两次尝试共留下多少问题/消息 ——
conn = sqlite3.connect(DB)
counts = {
    "messages": conn.execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0],
    "sessions": conn.execute("SELECT COUNT(*) FROM agent_sessions").fetchone()[0],
    "trade_plans": conn.execute("SELECT COUNT(*) FROM trade_plans").fetchone()[0],
    "fund_trades": conn.execute("SELECT COUNT(*) FROM fund_trades").fetchone()[0],
}
conn.close()
timeline.append({"t": ts(), "event": "db_counts", "data": counts})
OUT.write_text(json.dumps(timeline, ensure_ascii=False, indent=2))
print(json.dumps(counts, ensure_ascii=False))
print(f"saved {OUT}")
