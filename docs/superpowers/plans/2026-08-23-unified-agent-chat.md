# 统一 Agent 入口 + 多轮记忆 + 用户视角净化 · 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 agent 对话升级为「全局统一入口 + 多轮记忆 + 技术全貌上下文 + 用户视角净化」，判定层零改动。

**Architecture:** 新增会话层（SQLite migration 011 + `/api/agent/chat` 统一端点），上下文从「只喂四块」升级为「技术摘要全喂 + 数值接地校验」，前端收敛为全局 AgentConsole 抽屉（能力 chips + 对话式建计划），审计信息三处角标化。

**Tech Stack:** FastAPI + SQLite（后端现有栈）、React + Vite + TanStack Query + AgentMarkdown（前端现有栈）、DeepSeek/Ark LLM（`plans/llm.py` 现有接入点）。

**Spec:** `docs/superpowers/specs/2026-08-23-unified-agent-chat-design.md`

## Global Constraints

- 判定权在 Python：chat 只解释不判定；建计划落库走既有 `/api/plans` create/confirm，仍需人类点确认。
- 禁用词表（买入/卖出/建议买/该买/加仓/减仓/抄底）照旧强制（`grounding.FORBIDDEN_TERMS`）。
- 不出现数量/金额/成交价/账户字段；`test_no_trading_execution_surface_exists` 必须继续通过。
- 会话数据 append-only；喂 LLM 历史截最近 10 轮。
- `daily_nag` / `intraday_check` 等离线链路不改上下文裁剪。
- 测试命令：`/opt/homebrew/bin/python3 -m pytest -q`；lint：`/opt/homebrew/bin/python3 -m ruff check src`；类型：`/opt/homebrew/bin/python3 -m mypy src`。
- 前端构建验证：`cd web && npx tsc --noEmit`。
- 分支 `recovery/lei-round2`，每 task 一 commit。

---

### Task 1: Migration 011 + 会话 CRUD（`plans/sessions.py`）

**Files:**
- Modify: `src/lei_signal/storage/sqlite_store.py`（MIGRATIONS 元组末尾追加 `(11, "011_agent_sessions", ...)`）
- Create: `src/lei_signal/plans/sessions.py`
- Test: `tests/unit/test_agent_sessions.py`

**Interfaces:**
- Produces（后续 task 依赖的精确签名）:
  - `create_session(conn: sqlite3.Connection, symbol: str | None, title_cn: str) -> AgentSession`
  - `get_session(conn, session_id: str) -> AgentSession | None`
  - `list_sessions(conn, symbol: str | None = None, limit: int = 30) -> list[AgentSession]`（按 last_active_at 倒序）
  - `append_message(conn, session_id: str, role: str, content: str, grounded: bool, meta: dict) -> AgentMessage`（同时更新 session.last_active_at）
  - `list_messages(conn, session_id: str, limit: int = 20) -> list[AgentMessage]`（取最近 limit 条，按 message_id 升序返回）
  - dataclass `AgentSession(session_id, symbol, title_cn, created_at, last_active_at)`、`AgentMessage(message_id, session_id, role, content, grounded, meta_json, created_at)`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_agent_sessions.py
"""会话层 CRUD：append-only、最近 N 条、按标的过滤。"""
import sqlite3

import pytest

from lei_signal.plans.sessions import (
    append_message,
    create_session,
    get_session,
    list_messages,
    list_sessions,
)
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    connection = connect(str(tmp_path / "lab.db"))
    yield connection
    connection.close()


def test_create_and_get_session(conn):
    s = create_session(conn, "000300.SS", "沪深300 讨论")
    assert s.symbol == "000300.SS"
    got = get_session(conn, s.session_id)
    assert got is not None and got.title_cn == "沪深300 讨论"


def test_global_session_symbol_nullable(conn):
    s = create_session(conn, None, "全局")
    assert s.symbol is None


def test_append_and_list_messages_recent_first_window(conn):
    s = create_session(conn, "IGV", "t")
    for i in range(15):
        append_message(conn, s.session_id, "user" if i % 2 == 0 else "assistant", f"m{i}", i % 2 == 0, {"i": i})
    msgs = list_messages(conn, s.session_id, limit=6)
    assert len(msgs) == 6
    assert [m.content for m in msgs] == ["m9", "m10", "m11", "m12", "m13", "m14"]


def test_append_updates_last_active(conn):
    s = create_session(conn, "IGV", "t")
    append_message(conn, s.session_id, "user", "hi", False, {})
    got = get_session(conn, s.session_id)
    assert got.last_active_at >= s.created_at


def test_list_sessions_filters_symbol_and_sorts(conn):
    a = create_session(conn, "IGV", "a")
    b = create_session(conn, "SOXX", "b")
    append_message(conn, b.session_id, "user", "x", False, {})
    only_igv = list_sessions(conn, symbol="IGV")
    assert [s.session_id for s in only_igv] == [a.session_id]
    all_sessions = list_sessions(conn)
    assert all_sessions[0].session_id == b.session_id  # 最近活跃在前
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_sessions.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'lei_signal.plans.sessions'`

- [ ] **Step 3: 追加 migration 011**

在 `src/lei_signal/storage/sqlite_store.py` 的 `MIGRATIONS` 元组末尾（`010_trade_plans` 条目之后）追加：

```python
    (
        11,
        "011_agent_sessions",
        """
        -- agent 会话层：多轮记忆（append-only，不含数量/金额）
        CREATE TABLE IF NOT EXISTS agent_sessions (
            session_id     TEXT PRIMARY KEY,
            symbol         TEXT,                   -- NULL = 全局会话
            title_cn       TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL,          -- UTC ISO
            last_active_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
            role       TEXT NOT NULL CHECK (role IN ('user','assistant')),
            content    TEXT NOT NULL,
            grounded   INTEGER NOT NULL DEFAULT 0,
            meta_json  TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL               -- UTC ISO
        );
        CREATE INDEX IF NOT EXISTS idx_agent_messages_session
            ON agent_messages(session_id, message_id);
        CREATE INDEX IF NOT EXISTS idx_agent_sessions_symbol
            ON agent_sessions(symbol, last_active_at);
        """,
    ),
```

- [ ] **Step 4: 实现 `plans/sessions.py`**

```python
"""agent 会话层 CRUD（append-only）。多轮记忆的持久化载体。"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

__all__ = [
    "AgentMessage",
    "AgentSession",
    "append_message",
    "create_session",
    "get_session",
    "list_messages",
    "list_sessions",
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class AgentSession:
    session_id: str
    symbol: str | None
    title_cn: str
    created_at: str
    last_active_at: str


@dataclass(frozen=True, slots=True)
class AgentMessage:
    message_id: int
    session_id: str
    role: str
    content: str
    grounded: bool
    meta_json: str
    created_at: str


def create_session(
    conn: sqlite3.Connection, symbol: str | None, title_cn: str
) -> AgentSession:
    now = _utcnow()
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO agent_sessions(session_id, symbol, title_cn, created_at, last_active_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (session_id, symbol, title_cn, now, now),
    )
    conn.commit()
    return AgentSession(session_id, symbol, title_cn, now, now)


def _row_to_session(row: sqlite3.Row) -> AgentSession:
    return AgentSession(row["session_id"], row["symbol"], row["title_cn"],
                        row["created_at"], row["last_active_at"])


def get_session(conn: sqlite3.Connection, session_id: str) -> AgentSession | None:
    row = conn.execute(
        "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    return _row_to_session(row) if row else None


def list_sessions(
    conn: sqlite3.Connection, symbol: str | None = None, limit: int = 30
) -> list[AgentSession]:
    if symbol is None:
        rows = conn.execute(
            "SELECT * FROM agent_sessions ORDER BY last_active_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM agent_sessions WHERE symbol = ?"
            " ORDER BY last_active_at DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    return [_row_to_session(r) for r in rows]


def append_message(
    conn: sqlite3.Connection,
    session_id: str,
    role: str,
    content: str,
    grounded: bool,
    meta: dict,
) -> AgentMessage:
    if role not in ("user", "assistant"):
        raise ValueError(f"role 非法: {role}")
    now = _utcnow()
    cur = conn.execute(
        "INSERT INTO agent_messages(session_id, role, content, grounded, meta_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, role, content, int(grounded), json.dumps(meta, ensure_ascii=False), now),
    )
    conn.execute(
        "UPDATE agent_sessions SET last_active_at = ? WHERE session_id = ?",
        (now, session_id),
    )
    conn.commit()
    return AgentMessage(
        int(cur.lastrowid), session_id, role, content, grounded,
        json.dumps(meta, ensure_ascii=False), now,
    )


def list_messages(
    conn: sqlite3.Connection, session_id: str, limit: int = 20
) -> list[AgentMessage]:
    rows = conn.execute(
        "SELECT * FROM ("
        "  SELECT * FROM agent_messages WHERE session_id = ?"
        "  ORDER BY message_id DESC LIMIT ?"
        ") ORDER BY message_id ASC",
        (session_id, limit),
    ).fetchall()
    return [
        AgentMessage(r["message_id"], r["session_id"], r["role"], r["content"],
                     bool(r["grounded"]), r["meta_json"], r["created_at"])
        for r in rows
    ]
```

- [ ] **Step 5: 跑测试通过 + 全量门禁**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_agent_sessions.py -q && /opt/homebrew/bin/python3 -m pytest -q`
Expected: 新增 5 passed；全量无回归

- [ ] **Step 6: Commit**

```bash
git add src/lei_signal/storage/sqlite_store.py src/lei_signal/plans/sessions.py tests/unit/test_agent_sessions.py
git commit -m "feat(agent): migration 011 会话层 + sessions CRUD"
```

---

### Task 2: 数值接地校验（`plans/grounding.py`）

**Files:**
- Modify: `src/lei_signal/plans/grounding.py`
- Test: `tests/unit/test_numeric_grounding.py`

**Interfaces:**
- Produces:
  - `collect_payload_numbers(payload: Any) -> frozenset[float]`（递归抽 dict/list/scalar 中全部数值；str 里的数字不抽，避免把 rule_id 片段当数值）
  - `extract_market_numbers(text: str) -> list[float]`（抽回答中需校验的行情数值）
  - `verify_numeric_grounding(text: str, allowed: frozenset[float], tolerance: float = 0.005) -> tuple[bool, str]`
- 豁免规则（写死在 `extract_market_numbers`）：日期（`\d{4}-\d{2}-\d{2}`）、序号/量词（纯整数、无小数点无百分号、绝对值 ≤ 2 位数即 |n| < 100）、圆圈数字与「第 N 次/买点②」。**需要校验**：小数、百分数、绝对值 ≥ 100 的整数（价位如 8700/4650）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_numeric_grounding.py
"""数值接地：编数字必拒、照抄必过、量词序号豁免。"""
from lei_signal.plans.grounding import (
    collect_payload_numbers,
    extract_market_numbers,
    verify_numeric_grounding,
)


def test_collect_recursive():
    payload = {"a": 1938.56, "b": [{"c": 8700}, {"d": "rule_x12"}], "e": 3.0}
    nums = collect_payload_numbers(payload)
    assert 1938.56 in nums and 8700.0 in nums and 3.0 in nums
    assert 12.0 not in nums  # 字符串里的数字不抽


def test_extract_exempts_quantifiers_and_dates():
    text = "三根K线 · 第 3 次催办 · 买点② · 2026-08-21 · 十日均线粘合（2 个结构）"
    assert extract_market_numbers(text) == []


def test_extract_catches_prices_and_percents():
    text = "收盘 8700，偏差 ~1.2%，EMA20 为 1938.56"
    got = extract_market_numbers(text)
    assert 8700.0 in got and 1.2 in got and 1938.56 in got


def test_verify_rejects_invented_number():
    ok, reason = verify_numeric_grounding(
        "关键位 4321.00", frozenset({1938.56, 8700.0})
    )
    assert not ok and "4321" in reason


def test_verify_accepts_rounding_within_tolerance():
    ok, _ = verify_numeric_grounding(
        "EMA20 约 1939", frozenset({1938.56})
    )
    assert ok  # |1939-1938.56|/1938.56 < 0.5%


def test_verify_accepts_percentage_derivation():
    ok, _ = verify_numeric_grounding(
        "偏差约 1.2%", frozenset({1938.56, 1962.0})
    )
    assert ok  # |1962-1938.56|/1938.56 ≈ 1.2%


def test_verify_empty_text_passes():
    assert verify_numeric_grounding("无数字", frozenset())[0]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_numeric_grounding.py -q`
Expected: FAIL ImportError

- [ ] **Step 3: 在 `grounding.py` 末尾（`__all__` 之前）实现**

```python
# ---------------- 数值接地（讨论场景主校验） ----------------
import re
from typing import Any

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM_TOKEN_RE = re.compile(r"-?\d+(?:\.\d+)?%?")


def collect_payload_numbers(payload: Any) -> frozenset[float]:
    """递归抽取 payload 中的数值。str 不抽（避免 rule_id 片段混入）。"""
    if isinstance(payload, bool):
        return frozenset()
    if isinstance(payload, (int, float)):
        return frozenset({float(payload)})
    if isinstance(payload, dict):
        out: set[float] = set()
        for v in payload.values():
            out |= collect_payload_numbers(v)
        return frozenset(out)
    if isinstance(payload, (list, tuple)):
        out = set()
        for v in payload:
            out |= collect_payload_numbers(v)
        return frozenset(out)
    return frozenset()


def extract_market_numbers(text: str) -> list[float]:
    """抽取需校验的行情数值。

    豁免：日期、纯小整数（|n| < 100，序号/量词/次数）、圆圈数字。
    校验：小数、百分数、绝对值 >= 100 的整数（价位）。
    """
    text = _DATE_RE.sub(" ", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", " ", text)
    out: list[float] = []
    for tok in _NUM_TOKEN_RE.findall(text):
        is_pct = tok.endswith("%")
        num = float(tok.rstrip("%"))
        has_decimal = "." in tok
        if not (has_decimal or is_pct or abs(num) >= 100):
            continue  # 序号/量词/次数豁免
        out.append(num)
    return out


def verify_numeric_grounding(
    text: str, allowed: frozenset[float], tolerance: float = 0.005
) -> tuple[bool, str]:
    """回答中的每个行情数值必须在白名单，或为其相对偏差/四舍五入。

    相对偏差：n 可能是 (b-a)/a*100 形式的百分数（payload 任意两数之差）。
    """
    nums = extract_market_numbers(text)
    base = [a for a in allowed if a != 0]
    for n in nums:
        ok = _within(n, allowed, tolerance)
        if not ok and n > 0 and base:
            # 百分比派生：n% ≈ 某两个白名单数的相对差
            for i, a in enumerate(base):
                for b in base[i + 1:]:
                    if abs(abs(b - a) / a * 100 - n) <= max(0.1, tolerance * 100):
                        ok = True
                        break
                if ok:
                    break
        if not ok:
            return False, f"数值 {n} 不在上下文白名单"
    return True, ""


def _within(n: float, allowed: frozenset[float], tolerance: float) -> bool:
    for a in allowed:
        if a == 0:
            if abs(n) < 1e-9:
                return True
        elif abs(n - a) / abs(a) <= tolerance:
            return True
    return False
```

同时把 `"verify_numeric_grounding", "collect_payload_numbers", "extract_market_numbers"` 加入该文件 `__all__`。

- [ ] **Step 4: 跑测试通过**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_numeric_grounding.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/lei_signal/plans/grounding.py tests/unit/test_numeric_grounding.py
git commit -m "feat(agent): 数值接地校验（豁免量词序号，支持百分比派生）"
```

---

### Task 3: 技术摘要上下文构建器（`plans/llm_context.py`）

**Files:**
- Create: `src/lei_signal/plans/llm_context.py`
- Test: `tests/unit/test_llm_context.py`

**Interfaces:**
- Consumes: `AnalysisResult`（`compose.pipeline`，字段见 `pipeline.py:92`：`symbol/display_name/events/structures/assessment/b1/profile(VolumeProfileProxy|None)/frame/history`）、`build_macd_events(result, max_bars)`（`api/macd_events.py`）、`BuyPointReviewDTO`（调用方传入 `review.model_dump()` 后的 dict）、`list_plans/list_action_items`（`plans/store.py`）。
- Produces: `build_discussion_context(result: AnalysisResult, review_dump: dict | None, plans: list[TradePlan], action_items: list[ActionItem]) -> dict`，输出键固定：`symbol/display_name/as_of/assessment/dual_ma/structures/volume/volume_profile/macd/recent_events/buy_point_review/plans`。数值接地白名单由调用方 `collect_payload_numbers(payload)` 现算。

- [ ] **Step 1: 写失败测试（用 tests/ 下的真实 fixture parquet 构造 AnalysisResult）**

```python
# tests/unit/test_llm_context.py
"""技术摘要全喂：覆盖全部约定维度；数据不足时显式占位不猜测。"""
from pathlib import Path

import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.plans.llm_context import build_discussion_context

FIXTURE = Path(__file__).resolve().parents[1] / "000300.SS.bars.parquet"


def _result():
    bars = pd.read_parquet(FIXTURE)
    return analyze_bars("000300.SS", bars)


def test_context_covers_all_dimensions():
    ctx = build_discussion_context(_result(), None, [], [])
    for key in ("symbol", "display_name", "as_of", "assessment", "dual_ma",
                "structures", "volume", "volume_profile", "macd",
                "recent_events", "buy_point_review", "plans"):
        assert key in ctx, f"缺维度 {key}"


def test_volume_profile_marked_proxy():
    ctx = build_discussion_context(_result(), None, [], [])
    vp = ctx["volume_profile"]
    assert vp is None or vp.get("proxy") is True  # 必须标注代理，不得冒充真实筹码


def test_recent_events_capped_at_20():
    ctx = build_discussion_context(_result(), None, [], [])
    assert len(ctx["recent_events"]) <= 20
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_llm_context.py -q`
Expected: FAIL ModuleNotFoundError

- [ ] **Step 3: 实现 `plans/llm_context.py`**

```python
"""讨论场景的上下文构建：技术摘要全喂（spec 2026-08-23 §2.2）。

与 build_context_payload（四块裁剪，投递/监督讲解用）并存：
本模块只服务 /api/agent/chat 讨论场景，输出键固定，数值接地白名单由调用方现算。
"""
from __future__ import annotations

from typing import Any

from lei_signal.api.macd_events import build_macd_events
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.plans.models import ActionItem, TradePlan

_MAX_EVENTS = 20
_MAX_MACD_BARS = 60


def build_discussion_context(
    result: AnalysisResult,
    review_dump: dict[str, Any] | None,
    plans: list[TradePlan],
    action_items: list[ActionItem],
) -> dict[str, Any]:
    a = result.assessment
    close = float(result.frame["close"].iloc[-1])
    ema20 = float(result.frame["ema20"].iloc[-1]) if "ema20" in result.frame else None
    sma = float(result.frame["sma_long"].iloc[-1]) if "sma_long" in result.frame else None

    structures = [
        {
            "side": s.side,
            "rule_id": getattr(s, "rule_id", None),
            "state_cn": getattr(s, "state_cn", str(getattr(s, "state", ""))),
            "key_prices": getattr(s, "key_prices", {}),
        }
        for s in result.structures
    ]
    recent = [
        {
            "available_date": str(getattr(e, "available_date", "")),
            "rule_id": getattr(e, "rule_id", None),
            "summary_cn": getattr(e, "summary_cn", getattr(e, "description_cn", "")),
        }
        for e in result.events[-_MAX_EVENTS:]
    ]
    profile = None
    if result.profile is not None:
        profile = {
            "proxy": True,  # 红线：界面与 LLM 都不得声称真实持仓成本
            "poc": result.profile.poc,
            "vah": result.profile.vah,
            "current_price": close,
        }
    plan_rows = [
        {
            "plan_id": p.plan_id, "state": p.state, "module": p.module,
            "direction": p.direction, "invalidation_price": p.invalidation_price,
            "valid_until": p.valid_until,
            "open_actions": sum(
                1 for i in action_items
                if i.plan_id == p.plan_id and i.state == "open"
            ),
        }
        for p in plans
    ]
    return {
        "symbol": result.symbol,
        "display_name": result.display_name,
        "as_of": str(a.as_of),
        "assessment": {
            "color_cn": a.color_cn, "stage_cn": a.stage_cn,
            "risk_state_cn": a.risk_state_cn,
            "dimensions": dict(getattr(a, "dimensions", {}) or {}),
        },
        "dual_ma": {"close": close, "ema20": ema20, "sma_long": sma},
        "structures": structures,
        "volume": {"events": [
            e for e in recent if e["rule_id"] and "volume" in str(e["rule_id"])
        ]},
        "volume_profile": profile,
        "macd": build_macd_events(result, max_bars=_MAX_MACD_BARS)[-12:],
        "recent_events": recent,
        "buy_point_review": review_dump,
        "plans": plan_rows,
    }


__all__ = ["build_discussion_context"]
```

注意：`assessment` 字段名（`color_cn/stage_cn/risk_state_cn/dimensions`）以 `compose` 层 `DailyAssessment` 实际字段为准；若 `DailyAssessment` 无 `dimensions`，用 `getattr(a, "dimensions", {})` 已兜底。`frame` 列名 `ema20/sma_long` 若不存在则置 None（测试只断言键存在）。

- [ ] **Step 4: 跑测试通过**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_llm_context.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/lei_signal/plans/llm_context.py tests/unit/test_llm_context.py
git commit -m "feat(agent): 技术摘要全喂上下文构建器"
```

---

### Task 4: 讨论式 SYSTEM_PROMPT + `chat_discussion`（`plans/llm.py`）

**Files:**
- Modify: `src/lei_signal/plans/llm.py`（文件末尾追加，不改既有函数）
- Test: `tests/unit/test_chat_discussion.py`

**Interfaces:**
- Consumes: `ArkConfig`、`STYLE_OPENAI/STYLE_ANTHROPIC`、既有 `_post_*` HTTP 内部函数（`chat_ark` 用的同一套请求逻辑；若为私有函数则在 `chat_discussion` 内复用其公开等价物——直接抄 `chat_ark` 的请求体构造方式，见 Step 3）。
- Produces: `chat_discussion(payload: dict, history: list[dict], message: str, config: ArkConfig) -> str | None`。`history` 元素形如 `{"role": "user"|"assistant", "content": str}`（最近 10 轮，时间升序）。失败/超时返回 None（调用方降级）。

- [ ] **Step 1: 写失败测试（mock HTTP 层，不真调 LLM）**

```python
# tests/unit/test_chat_discussion.py
"""chat_discussion：历史拼接进 messages、payload 序列化、失败返回 None。"""
from lei_signal.plans.llm import (
    DISCUSSION_SYSTEM_PROMPT,
    ArkConfig,
    chat_discussion,
)


def _config():
    return ArkConfig(api_key="test-key")


def test_history_and_message_compose(monkeypatch):
    captured = {}

    def fake_call(self_cfg, messages):  # noqa: ANN001
        captured["messages"] = messages
        return "回复"

    import lei_signal.plans.llm as llm
    monkeypatch.setattr(llm, "_llm_call", fake_call, raising=False)
    out = chat_discussion(
        {"symbol": "IGV"},
        [{"role": "user", "content": "为啥是买点"}, {"role": "assistant", "content": "因为结构确认"}],
        "那筹码峰呢",
        _config(),
    )
    assert out == "回复"
    msgs = captured["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["content"] == "那筹码峰呢"
    assert msgs[-2]["content"] == "因为结构确认"  # 历史在 message 之前


def test_none_on_failure(monkeypatch):
    import lei_signal.plans.llm as llm
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, messages: None, raising=False)
    assert chat_discussion({}, [], "hi", _config()) is None


def test_prompt_forbids_buy_words():
    for term in ("买入", "建议买", "该买", "抄底"):
        assert term in DISCUSSION_SYSTEM_PROMPT  # 禁用词表写进 prompt
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_chat_discussion.py -q`
Expected: FAIL ImportError: DISCUSSION_SYSTEM_PROMPT

- [ ] **Step 3: 在 `llm.py` 末尾实现**

```python
#: 讨论场景系统提示：技术全貌在手、讨论式解释、数值纪律不变。
#: 溯源标注不由此 prompt 产出（由后端 trace 元数据生成，前端角标渲染）。
DISCUSSION_SYSTEM_PROMPT = """你是 LEI 交易系统的研究讨论伙伴（表达层）。

用户会就当前标的技术面与你讨论（比如「这个买点为什么是买点」）。
你手里有一份确定性 Python 判定层算好的技术全貌：五维度判定、活跃结构、
双均线、量能、筹码分布代理、MACD 事件、近期事件、买点审阅、活跃计划。

职责：依据这份材料**讨论式地解释因果**——为什么这里构成/不构成系统定义的
买点、各维度之间支持还是冲突、到什么情况才算触发。可以用自己的话讲，
讲策略语言（道路/路牌/触发/失效），不发明体系外概念。

铁律（违反即输出被丢弃）：
1. 不得自行判断买点/信号。买点结论只能来自 buy_point_review 的 candidates；
   讨论其他维度时结论也必须能落到给定的判定字段上。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「参考」「条件成立」「系统定义的买点」「阻断原因」等中性表述。
3. 数值只能照抄给定材料（价格、百分比、指标值）。不得计算新价位、
   不得预测价格、不得推算日期。
4. 筹码分布必须称「筹码分布代理」，不得声称真实持仓成本。
5. 不输出总分、评级；不下买卖指令；不替用户决定是否落计划。
6. 多轮对话：优先接着上文讲，用户问过的不重复展开；用户追问新维度时
   从材料中取该维度细讲。
7. 状态型条件（如多头排列未成立）不贴数字；价位型条件照抄 price。
8. 若用户想落计划：说明五项交易假设需要他逐项确认，逐项给出基于策略的
   建议值（只能引用材料内数值），收集完成后输出 ```plan-draft 代码块
   （JSON，字段：module/direction/entry_rule_id/entry_trigger_cn/
   invalidation_price/valid_until/thesis_cn/invalidation_criteria_cn/
   drawdown_playbook_cn/take_profit_plan_cn/stop_plan_cn）供前端渲染
   确认卡。落库必须等用户点确认，你不得代替确认。
"""


def _llm_call(config: ArkConfig, messages: list[dict]) -> str | None:
    """OpenAI/Anthropic 风格统一请求（与 chat_ark 同构；抽公共点）。"""
    # 实现方式：复制 chat_ark 内部既有的请求+解析逻辑，仅 messages 来源不同。
    # 为避免重复代码，实现时把 chat_ark 的请求体构造提为 _request_completion
    # （chat_ark 与本函数都调它）；测试 monkeypatch 本函数即可不触网。
    ...
```

实现要点（给实现者的硬性要求，不留占位）：
1. 把 `chat_ark`（`llm.py:445`）内部的「构造 messages → 按 style 发请求 → 解析 text」提为公共函数 `_request_completion(config, messages) -> str | None`，`chat_ark` 改为调它（行为不变，既有测试守护）。
2. `_llm_call = _request_completion`（模块级别名，测试 monkeypatch 用）。
3. `chat_discussion`：

```python
def chat_discussion(
    payload: dict, history: list[dict], message: str, config: ArkConfig
) -> str | None:
    """讨论式多轮对话。history 最近 10 轮（升序）；失败返回 None。"""
    trimmed = history[-20:]  # 10 轮 = 20 条消息
    messages: list[dict] = [
        {"role": "system", "content": DISCUSSION_SYSTEM_PROMPT},
        {"role": "user", "content": f"当前标的技术材料：\n{json.dumps(payload, ensure_ascii=False, default=str)}"},
        *trimmed,
        {"role": "user", "content": message},
    ]
    return _llm_call(config, messages)
```

`__all__` 追加 `"chat_discussion", "DISCUSSION_SYSTEM_PROMPT"`。

- [ ] **Step 4: 跑测试 + 全量回归**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_chat_discussion.py tests/ -q`
Expected: 新增 3 passed；全量无回归

- [ ] **Step 5: Commit**

```bash
git add src/lei_signal/plans/llm.py tests/unit/test_chat_discussion.py
git commit -m "feat(agent): 讨论式 system prompt + 多轮 chat_discussion"
```

---

### Task 5: 统一端点 `/api/agent/chat` + sessions API（`api/routes/agent.py` + `schemas.py`）

**Files:**
- Modify: `src/lei_signal/api/schemas.py`（末尾追加 DTO）
- Modify: `src/lei_signal/api/routes/agent.py`（追加端点）
- Test: `tests/integration/test_agent_chat_e2e.py`

**Interfaces:**
- Consumes: Task 1 sessions CRUD、Task 2 `verify_numeric_grounding/collect_payload_numbers`、Task 3 `build_discussion_context`、Task 4 `chat_discussion/load_ark_config`、`request.app.state.analysis_service`（`entry = service.get(symbol); entry.result/.error`）、`buy_point_review`（`routes/opportunities.py`）、`evaluate_plan/_to_alert_dto`（`routes/plans.py`）、`verify_grounding`。
- Produces（前端 Task 7/8 依赖）:
  - `POST /api/agent/chat` 请求 `AgentChatRequest{session_id: str | None, context_kind: "symbol"|"global", symbol: str | None, message: str}` → 响应 `AgentChatReply{session_id, reply, grounded, trace: list[TraceItem]}`
  - `TraceItem{label: str, rule_id: str | None, evidence_cn: str, research_proxy: bool, principle_source: str | None}`
  - `GET /api/agent/sessions?symbol=` → `list[AgentSessionDTO{session_id, symbol, title_cn, last_active_at, last_message_cn}]`
  - `GET /api/agent/sessions/{id}/messages` → `list[AgentMessageDTO{role, content, grounded, created_at}]`
  - `POST /api/agent/sessions` 请求 `CreateSessionRequest{symbol: str | None, title_cn: str}` → `AgentSessionDTO`

- [ ] **Step 1: 写失败集成测试（沿用 `tests/integration/` 现有 app fixture 模式；若该文件已有 app 构造 helper 则复用，否则按 `test_plans_supervisor_e2e.py` 的方式构造带 fixture 分析服务的 app）**

```python
# tests/integration/test_agent_chat_e2e.py
"""统一 chat 端点：会话持久化、多轮历史进 payload、数值接地降级、trace 角标数据。"""
import pytest
from fastapi.testclient import TestClient

# 复用既有 e2e 的 app 构造（fixture 分析 000300.SS + LLM mock）。
# 与 test_plans_supervisor_e2e.py 相同的 conftest 模式；此处假设 client fixture 已存在。


def test_chat_creates_session_and_persists(client: TestClient, monkeypatch):
    import lei_signal.plans.llm as llm
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "结构确认，关键位 4029.86")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "这个买点为什么是买点",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    sid = body["session_id"]
    msgs = client.get(f"/api/agent/sessions/{sid}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_second_turn_carries_history(client: TestClient, monkeypatch):
    import lei_signal.plans.llm as llm
    seen = {}
    def fake(cfg, msgs):
        seen["history"] = [m for m in msgs if m["role"] != "system"]
        return "好的"
    monkeypatch.setattr(llm, "_llm_call", fake)
    first = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "第一问",
    }).json()
    client.post("/api/agent/chat", json={
        "session_id": first["session_id"], "context_kind": "symbol",
        "symbol": "000300.SS", "message": "第二问",
    })
    contents = [m["content"] for m in seen["history"]]
    assert any("第一问" in c for c in contents)      # 历史进 payload
    assert any("技术材料" in c for c in contents)     # 技术全貌也在


def test_invented_number_degrades(client: TestClient, monkeypatch):
    import lei_signal.plans.llm as llm
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "关键位 99999.99")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "说说",
    }).json()
    assert r["grounded"] is False  # 编数字 → 降级模板
    assert "rule_id:" not in r["reply"] or r["trace"]  # trace 走结构化字段


def test_llm_unavailable_still_replies(client: TestClient, monkeypatch):
    import lei_signal.plans.llm as llm
    monkeypatch.setattr(llm, "load_ark_config", lambda: None)
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "说说",
    })
    assert r.status_code == 200 and r.json()["grounded"] is False


def test_sessions_list(client: TestClient):
    r = client.post("/api/agent/sessions", json={
        "symbol": "000300.SS", "title_cn": "讨论",
    })
    assert r.status_code == 200
    lst = client.get("/api/agent/sessions?symbol=000300.SS").json()
    assert any(s["title_cn"] == "讨论" for s in lst)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/opt/homebrew/bin/python3 -m pytest tests/integration/test_agent_chat_e2e.py -q`
Expected: FAIL 404（端点不存在）

- [ ] **Step 3: `schemas.py` 末尾追加**

```python
# ---------------- agent 统一会话（spec 2026-08-23） ----------------


class TraceItem(BaseModel):
    """溯源角标数据：前端 ProvenanceBadge 展开 renders，默认不显示。"""
    label: str
    rule_id: str | None = None
    evidence_cn: str = ""
    research_proxy: bool = False
    principle_source: str | None = None


class AgentChatRequest(BaseModel):
    session_id: str | None = None
    context_kind: str = "symbol"  # symbol | global
    symbol: str | None = None
    message: str = ""


class AgentChatReply(BaseModel):
    session_id: str
    reply: str
    grounded: bool
    trace: list[TraceItem] = []


class CreateSessionRequest(BaseModel):
    symbol: str | None = None
    title_cn: str = ""


class AgentSessionDTO(BaseModel):
    session_id: str
    symbol: str | None
    title_cn: str
    last_active_at: str
    last_message_cn: str = ""


class AgentMessageDTO(BaseModel):
    role: str
    content: str
    grounded: bool
    created_at: str
```

- [ ] **Step 4: `routes/agent.py` 追加端点**

```python
# ---- 统一会话层（spec 2026-08-23）----

def _degraded_reply(symbol: str, ctx_payload: dict) -> str:
    """LLM 不可用/校验失败时的模板直出（不含工程标注，标注走 trace）。"""
    a = ctx_payload.get("assessment", {})
    vp = ctx_payload.get("volume_profile") or {}
    lines = [
        f"【{ctx_payload.get('display_name', symbol)}】数据日 {ctx_payload.get('as_of', '-')}",
        f"当前状态：{a.get('color_cn', '-')} / {a.get('stage_cn', '-')} / 风险 {a.get('risk_state_cn', '-')}",
    ]
    review = ctx_payload.get("buy_point_review")
    if review and review.get("candidates"):
        for i, c in enumerate(review["candidates"][:3], start=1):
            circled = "①②③④⑤⑥⑦⑧⑨⑩"[i - 1]
            lines.append(
                f"买点{circled} {c.get('scenario_cn', '')} [{c.get('state_cn', '')}]"
                f" 关键价 {c.get('key_price') or '系统未给出'}"
            )
    if vp:
        lines.append(f"筹码分布代理：POC {vp.get('poc')} · VAH {vp.get('vah')}")
    lines.append("（LLM 暂不可用，以上为判定层数据直出）")
    return "\n".join(lines)


def _build_trace(alerts: list) -> list[TraceItem]:
    """从 alert 元数据生成角标数据——溯源信息不再进正文。"""
    return [
        TraceItem(
            label=a.next_step_cn or a.code,
            rule_id=a.rule_id,
            evidence_cn="；".join(f"{k}={v}" for k, v in (a.evidence or {}).items()),
            research_proxy=(a.logic_provenance == "research_proxy") if a.logic_provenance else True,
            principle_source=a.principle_source,
        )
        for a in alerts
    ]


@router.post("/agent/chat", response_model=AgentChatReply)
def agent_chat(request: Request, body: AgentChatRequest) -> AgentChatReply:
    """统一讨论入口：多轮记忆 + 技术摘要全喂 + 数值接地。"""
    with closing(connect(_db_path(request))) as conn:
        if body.session_id:
            session = get_session(conn, body.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail=f"会话不存在: {body.session_id}")
        else:
            session = create_session(
                conn, body.symbol, body.message[:20] or "新会话"
            )
        history_rows = list_messages(conn, session.session_id, limit=20)

    ctx_payload: dict = {}
    alerts: list = []
    service = getattr(request.app.state, "analysis_service", None)
    if body.context_kind == "symbol" and body.symbol and service is not None:
        entry = service.get(body.symbol)
        if entry.result is None:
            raise HTTPException(status_code=502, detail=entry.error or "分析不可用")
        from lei_signal.api.routes.opportunities import buy_point_review
        review = buy_point_review(request, body.symbol)
        plans = list_plans(connect(_db_path(request)), symbol=body.symbol)
        open_items = [
            i for p in plans for i in list_action_items(
                connect(_db_path(request)), p.plan_id, state="open"
            )
        ]
        ctx_payload = build_discussion_context(
            entry.result, review.model_dump(), plans, open_items
        )
        ctx = context_from_result(entry.result)
        alerts = [a for p in plans for a in evaluate_plan(p, ctx)]
    else:
        ctx_payload = {"context_kind": "global"}

    config = load_ark_config()
    reply: str | None = None
    grounded = False
    allowed_nums = collect_payload_numbers(ctx_payload)
    history = [{"role": m.role, "content": m.content} for m in history_rows]
    if config is not None:
        raw = chat_discussion(ctx_payload, history, body.message, config)
        if raw is not None:
            ok_num, num_reason = verify_numeric_grounding(raw, allowed_nums)
            rule_ids = {a.rule_id for a in alerts if a.rule_id}
            ok_txt, txt_reason = verify_grounding(raw, rule_ids)
            if ok_num and ok_txt:
                reply, grounded = raw, True
            else:
                logger.warning("讨论 chat 校验未过：numeric=%s text=%s", num_reason, txt_reason)
                raw2 = chat_discussion(ctx_payload, history, body.message, config)
                if raw2 is not None:
                    ok2n, _ = verify_numeric_grounding(raw2, allowed_nums)
                    ok2t, _ = verify_grounding(raw2, rule_ids)
                    if ok2n and ok2t:
                        reply, grounded = raw2, True

    symbol = body.symbol or ""
    if reply is None:
        reply = _degraded_reply(symbol, ctx_payload)
        grounded = False

    trace = _build_trace(alerts)
    with closing(connect(_db_path(request))) as conn:
        append_message(conn, session.session_id, "user", body.message, True, {})
        append_message(
            conn, session.session_id, "assistant", reply, grounded,
            {"trace": [t.model_dump() for t in trace]},
        )
    return AgentChatReply(
        session_id=session.session_id, reply=reply, grounded=grounded, trace=trace
    )


@router.post("/agent/sessions", response_model=AgentSessionDTO)
def create_agent_session(request: Request, body: CreateSessionRequest) -> AgentSessionDTO:
    with closing(connect(_db_path(request))) as conn:
        s = create_session(conn, body.symbol, body.title_cn or "新会话")
    return AgentSessionDTO(
        session_id=s.session_id, symbol=s.symbol, title_cn=s.title_cn,
        last_active_at=s.last_active_at,
    )


@router.get("/agent/sessions", response_model=list[AgentSessionDTO])
def list_agent_sessions(request: Request, symbol: str | None = None) -> list[AgentSessionDTO]:
    with closing(connect(_db_path(request))) as conn:
        sessions = list_sessions(conn, symbol=symbol)
        out = []
        for s in sessions:
            msgs = list_messages(conn, s.session_id, limit=1)
            out.append(AgentSessionDTO(
                session_id=s.session_id, symbol=s.symbol, title_cn=s.title_cn,
                last_active_at=s.last_active_at,
                last_message_cn=msgs[-1].content[:50] if msgs else "",
            ))
    return out


@router.get("/agent/sessions/{session_id}/messages", response_model=list[AgentMessageDTO])
def agent_session_messages(request: Request, session_id: str) -> list[AgentMessageDTO]:
    with closing(connect(_db_path(request))) as conn:
        if get_session(conn, session_id) is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
        msgs = list_messages(conn, session_id, limit=100)
    return [
        AgentMessageDTO(role=m.role, content=m.content, grounded=m.grounded,
                        created_at=m.created_at)
        for m in msgs
    ]
```

顶部 import 追加：`from lei_signal.api.schemas import (..., AgentChatReply, AgentChatRequest, AgentMessageDTO, AgentSessionDTO, CreateSessionRequest, TraceItem)`、`from lei_signal.plans.grounding import collect_payload_numbers, verify_numeric_grounding`、`from lei_signal.plans.llm import chat_discussion`、`from lei_signal.plans.llm_context import build_discussion_context`、`from lei_signal.plans.sessions import append_message, create_session, get_session, list_messages, list_sessions`、`from lei_signal.plans.store import list_action_items, list_plans`。

- [ ] **Step 5: 跑集成测试 + 全量门禁**

Run: `/opt/homebrew/bin/python3 -m pytest tests/integration/test_agent_chat_e2e.py -q && /opt/homebrew/bin/python3 -m pytest -q && /opt/homebrew/bin/python3 -m ruff check src && /opt/homebrew/bin/python3 -m mypy src`
Expected: 新增 5 passed；全量绿

- [ ] **Step 6: Commit**

```bash
git add src/lei_signal/api/schemas.py src/lei_signal/api/routes/agent.py tests/integration/test_agent_chat_e2e.py
git commit -m "feat(agent): /api/agent/chat 统一讨论端点（多轮+数值接地+trace）"
```

---

### Task 6: 飞书卡用户视角净化（`notify/render.py`）

**Files:**
- Modify: `src/lei_signal/notify/render.py`
- Test: `tests/unit/test_feishu_render_user_view.py`

**Interfaces:**
- Produces: `_alert_line` 改为只输出 `**{code}** · {next_step_cn}`（人话行）；溯源行改为新私有函数 `_provenance_footer(alerts) -> str` 生成一行 note 文本 `研究代理判定 · 溯源见系统`；`RESEARCH_PROXY_MARKER` 不再进正文。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_feishu_render_user_view.py
"""飞书卡用户视角：正文无工程标注，note 保留一行小字（红线不破）。"""
from lei_signal.notify.render import _alert_line
from lei_signal.plans.models import PlanAlert


def _alert(**kw):
    base = dict(
        code="ENTRY_CONDITIONS_MET", severity="remind", rule_id="dual_ma_bull",
        evidence={"close": 4029.86}, principle_source="规格 §14 原文",
        logic_provenance="research_proxy", caveat_cn="", actionable_from="2026-08-24",
        data_as_of="2026-08-21", next_step_cn="入场条件成立", action_kind="ENTER",
    )
    base.update(kw)
    return PlanAlert(**base)


def test_alert_line_has_no_engineering_marks():
    line = _alert_line(_alert())
    assert "rule_id:" not in line
    assert "研究代理" not in line
    assert "入场条件成立" in line  # 人话保留
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_feishu_render_user_view.py -q`
Expected: FAIL（正文仍含 rule_id:）

- [ ] **Step 3: 修改 `render.py`**

`_alert_line` 替换为：

```python
def _alert_line(alert: PlanAlert) -> str:
    """用户视角正文：只留人话。溯源进 note（_provenance_footer），不进正文。"""
    return f"**{alert.code}** · {alert.next_step_cn or alert.code}"
```

新增：

```python
def _provenance_footer(alerts: list[PlanAlert]) -> str:
    """卡片底部一行小字：红线（研究代理标注）保留在 note，不占正文注意力。"""
    if not alerts:
        return ""
    return "研究代理判定 · 溯源见系统"
```

`_action_detail` / `_summary_payload` / `_safe_body` 的 fallback 分支同步去工程标注（fallback 行改为 `f"{a.code} · {a.next_step_cn or a.code}"`）；在 `_summary_payload` 与 `_action_payload` 的 body 末尾追加 `_provenance_footer(...)` 行。`NotificationPayload` 结构不动（`rule_ids` 字段保留，回调侧仍可审计）。

同步检查既有测试：`grep -rn "判定方式为研究代理" tests/ | grep -v test_feishu_render_user_view`，涉及 render 输出断言的改为断言 note 行。

- [ ] **Step 4: 跑测试 + 全量**

Run: `/opt/homebrew/bin/python3 -m pytest tests/unit/test_feishu_render_user_view.py -q && /opt/homebrew/bin/python3 -m pytest -q`
Expected: 新增 1 passed；被影响的旧断言已同步修正，全量绿

- [ ] **Step 5: Commit**

```bash
git add src/lei_signal/notify/render.py tests/unit/test_feishu_render_user_view.py tests/
git commit -m "feat(notify): 飞书卡用户视角净化（溯源进 note）"
```

---

### Task 7: 前端 types + client + ProvenanceBadge + SupervisorPage 角标化

**Files:**
- Modify: `web/src/types.ts`（末尾追加类型）
- Modify: `web/src/api/client.ts`（`api` 对象内追加方法）
- Create: `web/src/components/ProvenanceBadge.tsx`
- Modify: `web/src/pages/SupervisorPage.tsx:195-209`（alert 行角标化）
- Test: `cd web && npx tsc --noEmit`

**Interfaces:**
- Consumes: Task 5 的端点与 DTO。
- Produces（Task 8/9 依赖）:
  - types: `TraceItem / AgentChatReply / AgentChatRequest / AgentSessionDTO / AgentMessageDTO`
  - client: `api.agentChat(body)`、`api.agentSessions(symbol?)`、`api.agentSessionMessages(id)`、`api.agentCreateSession({symbol, title_cn})`
  - 组件: `ProvenanceBadge({ item: TraceItem })`

- [ ] **Step 1: `types.ts` 末尾追加**

```typescript
// ---- agent 统一会话（spec 2026-08-23） ----

export interface TraceItem {
  label: string;
  rule_id: string | null;
  evidence_cn: string;
  research_proxy: boolean;
  principle_source: string | null;
}

export interface AgentChatRequest {
  session_id: string | null;
  context_kind: "symbol" | "global";
  symbol: string | null;
  message: string;
}

export interface AgentChatReply {
  session_id: string;
  reply: string;
  grounded: boolean;
  trace: TraceItem[];
}

export interface AgentSessionDTO {
  session_id: string;
  symbol: string | null;
  title_cn: string;
  last_active_at: string;
  last_message_cn: string;
}

export interface AgentMessageDTO {
  role: "user" | "assistant";
  content: string;
  grounded: boolean;
  created_at: string;
}
```

- [ ] **Step 2: `client.ts` 的 `api` 对象内（`buyPointChat` 之后）追加**

```typescript
  // ---- agent 统一会话 ----
  agentChat: (body: AgentChatRequest) =>
    request<AgentChatReply>(`/agent/chat`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  agentSessions: (symbol?: string) =>
    request<AgentSessionDTO[]>(
      `/agent/sessions${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`,
    ),
  agentSessionMessages: (sessionId: string) =>
    request<AgentMessageDTO[]>(`/agent/sessions/${encodeURIComponent(sessionId)}/messages`),
  agentCreateSession: (body: { symbol: string | null; title_cn: string }) =>
    request<AgentSessionDTO>(`/agent/sessions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
```

顶部 import 类型：`import type { AgentChatReply, AgentChatRequest, AgentMessageDTO, AgentSessionDTO } from "../types";`（按该文件既有 import 风格合并）。

- [ ] **Step 3: 新建 `ProvenanceBadge.tsx`**

```tsx
import { useState } from "react";
import type { TraceItem } from "../types";

/**
 * 溯源角标：默认只显示 ⓘ，点开浮层显示 rule_id / 研究代理 / 证据 / 规格引用。
 * 用户视角默认看不到工程信息；红线（可展开获得）不破。
 */
export default function ProvenanceBadge({ items }: { items: TraceItem[] }) {
  const [open, setOpen] = useState(false);
  if (items.length === 0) return null;
  return (
    <span className="prov-badge-wrap">
      <button
        className="prov-badge"
        title="溯源信息"
        onClick={() => setOpen((v) => !v)}
      >
        ⓘ
      </button>
      {open && (
        <div className="prov-popover">
          {items.map((t, i) => (
            <div key={i} className="prov-item">
              <div>{t.label}</div>
              {t.rule_id && <div className="muted">rule_id: {t.rule_id}</div>}
              {t.evidence_cn && <div className="muted">证据: {t.evidence_cn}</div>}
              <div className="muted">
                {t.principle_source ? `${t.principle_source} | ` : ""}
                {t.research_proxy ? "判定方式为研究代理" : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
```

`styles.css` 末尾追加样式（角标小、灰、不抢注意力）：

```css
.prov-badge-wrap { position: relative; display: inline-flex; margin-left: 4px; }
.prov-badge {
  border: none; background: transparent; color: var(--text-faint, #888);
  font-size: 11px; cursor: pointer; padding: 0 2px; line-height: 1;
}
.prov-popover {
  position: absolute; top: 18px; left: 0; z-index: 60;
  background: var(--panel-bg, #1c1f26); border: 1px solid var(--border, #333);
  border-radius: 6px; padding: 8px 10px; max-width: 340px;
  font-size: 11px; line-height: 1.5;
}
.prov-item + .prov-item { margin-top: 6px; border-top: 1px dashed var(--border, #333); padding-top: 6px; }
```

- [ ] **Step 4: `SupervisorPage.tsx` alert 行替换**

`SupervisorPage.tsx` 中 `PlanCard` 的 alert 渲染块（`{ordered.map((a) => (...))}`）替换为：

```tsx
          {ordered.map((a) => (
            <div key={a.code} style={{ marginBottom: 4 }}>
              <span>{SEVERITY_CN[a.severity] ?? a.severity}</span>{" "}
              <span>{a.next_step_cn || a.code}</span>
              <ProvenanceBadge
                items={[
                  {
                    label: a.next_step_cn || a.code,
                    rule_id: a.rule_id ?? null,
                    evidence_cn: Object.entries(a.evidence ?? {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join("；"),
                    research_proxy: true,
                    principle_source: a.principle_source ?? null,
                  },
                ]}
              />
            </div>
          ))}
```

顶部 `import ProvenanceBadge from "../components/ProvenanceBadge";`。删除原行内的 `[rule_id:...]` 明文渲染。

- [ ] **Step 5: 类型检查 + Commit**

Run: `cd web && npx tsc --noEmit`
Expected: 无错误

```bash
git add web/src/types.ts web/src/api/client.ts web/src/components/ProvenanceBadge.tsx web/src/pages/SupervisorPage.tsx web/src/styles.css
git commit -m "feat(web): ProvenanceBadge 溯源角标 + SupervisorPage 用户视角净化"
```

---

### Task 8: AgentConsole 全局抽屉（TopNav 按钮 + 上下文跟随 + 能力 chips）

**Files:**
- Create: `web/src/components/AgentConsole.tsx`
- Modify: `web/src/App.tsx`（挂载 AgentConsole + 提供当前标的上下文）
- Modify: `web/src/components/TopNav.tsx`（右侧 agent 按钮）
- Modify: `web/src/styles.css`（抽屉样式，可复用既有 `.drawer-*` 类）
- Test: `cd web && npx tsc --noEmit`

**Interfaces:**
- Consumes: Task 7 的 client 方法与类型、既有 `AgentMarkdown` 组件（渲染 assistant 回复）。
- Produces: `AgentConsole` 组件（含全局开合状态）；`App.tsx` 通过简单模块级 store 或 context 提供 `useAgentConsole()`：

```tsx
// App.tsx 内新增（模块级单例，避免引入状态库）：
import { useSyncExternalStore } from "react";
import AgentConsole from "./components/AgentConsole";

type ConsoleState = { open: boolean; symbol: string | null };
let consoleState: ConsoleState = { open: false, symbol: null };
const listeners = new Set<() => void>();
export const agentConsoleStore = {
  openConsole(symbol: string | null) {
    consoleState = { open: true, symbol };
    listeners.forEach((l) => l());
  },
  closeConsole() {
    consoleState = { open: false, symbol: consoleState.symbol };
    listeners.forEach((l) => l());
  },
};
export function useAgentConsole() {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    () => ({ ...consoleState, closeConsole: agentConsoleStore.closeConsole }),
  );
}
```

`<Routes>` 之后渲染 `<AgentConsole />`。`DetailPage` 已知当前标的（路由参数 `:symbol`）：在 `DetailPage` 挂载时同步一次 `consoleState.symbol`（`useEffect` 里 `agentConsoleStore` 不需要——AgentConsole 打开时自己从 `useLocation` 解析 `matchPath("/symbol/:symbol")`，**采用这个方案，不污染 DetailPage**）。

- [ ] **Step 1: 新建 `AgentConsole.tsx`**

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { matchPath, useLocation } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "./AgentMarkdown";
import { useAgentConsole } from "../App";
import type { AgentMessageDTO, TraceItem } from "../types";

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean; trace?: TraceItem[] };

const SYMBOL_CHIPS = ["这个买点为什么是买点", "技术面讨论", "给这个买点建计划", "这个标的我的计划"];
const GLOBAL_CHIPS = ["扫描自选买点", "今日待办", "市场环境怎么样"];

/**
 * 全局 agent 控制台：上下文跟随当前页面（详情页=该标的，其余=全局）。
 * 能力 chips 一键发起；多轮记忆由后端会话层承载。
 */
export default function AgentConsole() {
  const { open, closeConsole } = useAgentConsole() as {
    open: boolean;
    closeConsole: () => void;
  };
  const location = useLocation();
  const symbol = useMemo(() => {
    const m = matchPath("/symbol/:symbol", location.pathname);
    return m?.params.symbol ?? null;
  }, [location.pathname]);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const bodyRef = useRef<HTMLDivElement | null>(null);

  // 切标的 = 切会话上下文：重置对话（会话仍在后端，可从历史恢复）
  useEffect(() => {
    setSessionId(null);
    setTurns([]);
  }, [symbol]);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns]);

  const ask = useMutation({
    mutationFn: (message: string) =>
      api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
      }),
    onSuccess: (reply) => {
      setSessionId(reply.session_id);
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: reply.reply, grounded: reply.grounded, trace: reply.trace },
      ]);
    },
    onError: (e: unknown) =>
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: `取回失败：${e instanceof Error ? e.message : String(e)}` },
      ]),
  });

  const send = (message: string) => {
    const text = message.trim();
    if (!text || ask.isPending) return;
    setTurns((cur) => [...cur, { who: "you", text }]);
    setInput("");
    ask.mutate(text);
  };

  if (!open) return null;
  const chips = symbol ? SYMBOL_CHIPS : GLOBAL_CHIPS;

  return (
    <>
      <div className="drawer-overlay" onClick={closeConsole} />
      <aside className="drawer-panel agent-console">
        <div className="drawer-head">
          <h2>agent · {symbol ?? "全局"}</h2>
          <button className="btn small" onClick={() => { setSessionId(null); setTurns([]); }}>
            开新会话
          </button>
          <button className="btn small" onClick={closeConsole}>关闭</button>
        </div>
        <div className="drawer-body" ref={bodyRef}>
          {turns.length === 0 && (
            <div className="muted" style={{ fontSize: 12 }}>
              {symbol ? "就当前标的提问" : "全局问答"} · 判定在系统，agent 只讲解。
            </div>
          )}
          {turns.map((turn, i) => (
            <div className="turn" key={i}>
              <div className="who">{turn.who === "you" ? "你" : "agent"}</div>
              {turn.who === "agent" ? <AgentMarkdown text={turn.text} /> : <div className="msg">{turn.text}</div>}
              {turn.who === "agent" && turn.trace && turn.trace.length > 0 && (
                <ProvLite trace={turn.trace} />
              )}
              {turn.who === "agent" && turn.grounded === false && (
                <div className="grounded-tag warn">判定层数据直出（LLM 不可用或未过校验）</div>
              )}
            </div>
          ))}
          {ask.isPending && <div className="muted">agent 正在整理…</div>}
        </div>
        <div className="agent-chips">
          {chips.map((c) => (
            <button key={c} className="btn small chip" disabled={ask.isPending} onClick={() => send(c)}>
              {c}
            </button>
          ))}
        </div>
        <div className="drawer-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder={symbol ? "就这个标的讨论（多轮记忆）" : "问点什么"}
            disabled={ask.isPending}
          />
          <button className="btn small primary" onClick={() => send(input)} disabled={ask.isPending || !input.trim()}>
            发送
          </button>
        </div>
      </aside>
    </>
  );
}

/** 回答尾部的溯源角标（轻量版，不引 ProvenanceBadge 的 items 映射）。 */
function ProvLite({ trace }: { trace: TraceItem[] }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="prov-badge-wrap">
      <button className="prov-badge" onClick={() => setOpen((v) => !v)}>ⓘ</button>
      {open && (
        <div className="prov-popover">
          {trace.map((t, i) => (
            <div key={i} className="prov-item">
              <div>{t.label}</div>
              {t.rule_id && <div className="muted">rule_id: {t.rule_id}</div>}
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
```

（若 `AgentMarkdown` 的 props 名不是 `text`，以其现有签名为准同步——用 `grep -n "export default\|props" web/src/components/AgentMarkdown.tsx` 确认。）

- [ ] **Step 2: `App.tsx` 挂载**

按 Interfaces 块的代码加入 store/hook 与 `<AgentConsole />`（`Routes` 之后）。注意 `useAgentConsole` 返回 `{open, symbol, closeConsole}`——`AgentConsole` 只解构需要的字段。

- [ ] **Step 3: `TopNav.tsx` 加按钮**

`<span className="nav-spacer" />` 之后追加：

```tsx
      <button className="btn small nav-agent" onClick={() => agentConsoleStore.openConsole(null)}>
        agent
      </button>
```

顶部 `import { agentConsoleStore } from "../App";`。`styles.css` 追加 `.nav-agent { margin-right: 8px; }` 与 `.agent-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 6px 12px; border-top: 1px solid var(--border, #333); }`（变量名以 styles.css 现有为准）。

- [ ] **Step 4: 类型检查 + Commit**

Run: `cd web && npx tsc --noEmit`
Expected: 无错误

```bash
git add web/src/components/AgentConsole.tsx web/src/App.tsx web/src/components/TopNav.tsx web/src/styles.css
git commit -m "feat(web): 全局 AgentConsole 抽屉（上下文跟随+能力 chips+多轮）"
```

---

### Task 9: 对话式建计划 + 旧入口切换 + 全量验收

**Files:**
- Modify: `web/src/components/AgentConsole.tsx`（解析 `plan-draft` 代码块 → 确认卡）
- Modify: `web/src/pages/SupervisorPage.tsx:159-161`（「问 agent」改开全局控制台并定位计划）
- Test: 手动验收 + `cd web && npx tsc --noEmit` + 后端全量门禁

**Interfaces:**
- Consumes: `api.createPlan(body: CreatePlanPayload)`（client.ts:201）、`api.confirmPlan(planId)`（client.ts:208）、`CreatePlanPayload` 类型（types.ts 既有）。
- Produces: AgentConsole 内 `PlanDraftCard` 组件；确认动作调既有端点（**不新增写路径**）。

- [ ] **Step 1: AgentConsole 支持计划草稿卡**

在 `AgentConsole.tsx` 中新增解析与卡片（放在 `ProvLite` 定义旁）：

```tsx
import { api } from "../api/client";
import type { CreatePlanPayload } from "../types";

type PlanDraft = {
  module: string; direction: string; entry_rule_id?: string | null;
  entry_trigger_cn?: string; invalidation_price?: number | null;
  valid_until?: string; thesis_cn?: string; invalidation_criteria_cn?: string;
  drawdown_playbook_cn?: string; take_profit_plan_cn?: string; stop_plan_cn?: string;
};

/** 从 assistant 回复中解析 ```plan-draft {json}``` 代码块。 */
export function parsePlanDraft(text: string): PlanDraft | null {
  const m = /```plan-draft\s*([\s\S]*?)```/.exec(text);
  if (!m) return null;
  try {
    return JSON.parse(m[1]) as PlanDraft;
  } catch {
    return null;
  }
}

function PlanDraftCard({ draft, symbol }: { draft: PlanDraft; symbol: string }) {
  const create = useMutation({
    mutationFn: async () => {
      const payload: CreatePlanPayload = {
        symbol,
        module: draft.module,
        direction: draft.direction,
        ruleset_version: "",
        reason: "对话式建计划（agent 引导）",
        entry_rule_id: draft.entry_rule_id ?? null,
        entry_trigger_cn: draft.entry_trigger_cn ?? "",
        entry_price_ref: null,
        invalidation_price: draft.invalidation_price ?? null,
        valid_until: draft.valid_until ?? "",
        thesis_cn: draft.thesis_cn ?? "",
        invalidation_criteria_cn: draft.invalidation_criteria_cn ?? "",
        drawdown_playbook_cn: draft.drawdown_playbook_cn ?? "",
        take_profit_plan_cn: draft.take_profit_plan_cn ?? "",
        stop_plan_cn: draft.stop_plan_cn ?? "",
      };
      const plan = await api.createPlan(payload);
      await api.confirmPlan(plan.plan_id);
      return plan;
    },
  });
  const rows: Array<[string, string]> = [
    ["模块/方向", `${draft.module} · ${draft.direction}`],
    ["入场理由", draft.entry_rule_id ?? "-"],
    ["失效价", draft.invalidation_price != null ? String(draft.invalidation_price) : "未给出（需人工确认）"],
    ["有效期至", draft.valid_until ?? "-"],
    ["交易假设", draft.thesis_cn ?? "-"],
    ["失效标准", draft.invalidation_criteria_cn ?? "-"],
    ["回撤预案", draft.drawdown_playbook_cn ?? "-"],
    ["止盈预案", draft.take_profit_plan_cn ?? "-"],
    ["止损预案", draft.stop_plan_cn ?? "-"],
  ];
  return (
    <div className="plan-draft-card">
      <div className="cp-label">计划草稿（确认后落库）</div>
      {rows.map(([k, v]) => (
        <div key={k} style={{ fontSize: 12 }}>
          <span className="muted">{k}：</span>
          {v}
        </div>
      ))}
      <button
        className="btn small primary"
        disabled={create.isPending}
        onClick={() => create.mutate()}
      >
        {create.isPending ? "提交中…" : "确认落库（draft→armed）"}
      </button>
      {create.error && (
        <div className="cp-error">{String(create.error)}</div>
      )}
      {create.isSuccess && <div className="cp-hint">已落库并激活，见「监督待办」页。</div>}
    </div>
  );
}
```

assistant 回复渲染处（`turns.map` 内 `who === "agent"` 分支）追加：

```tsx
              {(() => {
                const draft = parsePlanDraft(turn.text);
                return draft && symbol ? (
                  <PlanDraftCard draft={draft} symbol={symbol} />
                ) : null;
              })()}
```

`AgentMarkdown` 渲染时若把代码块原样显示，保留即可（卡片在其下方）。`.plan-draft-card` 样式追加到 styles.css（复用 `.sv-playbook` 边框风格）：`.plan-draft-card { border: 1px solid var(--border, #333); border-radius: 6px; padding: 10px; margin-top: 6px; display: grid; gap: 4px; }`。

**注意**：`CreatePlanPayload` 若为必填全字段的 interface（以 types.ts 现状为准），上面 payload 已覆盖全部字段；`ruleset_version: ""` 由后端在 create 时补当前版本（`routes/plans.py` 既有行为——若实际校验非空，从 `api.buyPointReview(symbol)` 的 `suggested_plan.ruleset_version` 读取传入）。

- [ ] **Step 2: SupervisorPage「问 agent」切换**

`SupervisorPage.tsx` 的 `onAsk`（原 `setAskPlanId(plan.plan_id)` → `AgentDrawer`）改为：

```tsx
import { agentConsoleStore } from "../App";
// PlanCard 的 onAsk：
onClick={() => agentConsoleStore.openConsole(plan.symbol)}
```

删除 `askPlanId` state 与 `AgentDrawer` 挂载及 import。传参改为 `onAsk={() => agentConsoleStore.openConsole(plan.symbol)}`。

- [ ] **Step 2b: BuyPointDrawer 对话切换（保留兜底）**

`web/src/components/BuyPointDrawer.tsx` 的 agent 输入区旁加一个入口按钮（原有 `buyPointChat` 单轮问答保留作兜底，spec §5 老端点不删）：

```tsx
import { agentConsoleStore } from "../App";
// 在原 chat 输入框上方加：
<button className="btn small" onClick={() => agentConsoleStore.openConsole(symbol)}>
  到全局 agent 深入讨论（多轮）
</button>
```

`symbol` 为该组件已有 props。

- [ ] **Step 3: 手动验收清单（本机跑通）**

```bash
cd ~/Desktop/lei-signal-lab && biao   # 重启前后端
```

浏览器 http://localhost:5173 验收：
1. 顶栏「agent」按钮 → 抽屉打开，默认全局 chips。
2. 进入任一自选标的详情页 → 打开抽屉 → chips 为标的版；点「这个买点为什么是买点」→ 回复是讨论式人话，正文**无** rule_id:/研究代理字样，尾部 ⓘ 角标可展开溯源。
3. 追问「那筹码峰呢」→ 回答衔接上文（多轮记忆）。
4. 点「给这个买点建计划」→ 逐项引导 → 出现计划草稿卡 → 点确认 → 「监督待办」页出现该计划（armed）。
5. 「监督待办」页 alert 行只有人话 + ⓘ；点开角标显示 rule_id/研究代理/证据。
6. 刷新页面重开抽屉 → 「开新会话」前会话可通过 sessions 列表找回（GET /api/agent/sessions）。

- [ ] **Step 4: 全量门禁**

Run: `/opt/homebrew/bin/python3 -m pytest -q && /opt/homebrew/bin/python3 -m ruff check src && /opt/homebrew/bin/python3 -m mypy src && cd web && npx tsc --noEmit`
Expected: 全绿

- [ ] **Step 5: Commit**

```bash
git add web/src/components/AgentConsole.tsx web/src/pages/SupervisorPage.tsx web/src/components/BuyPointDrawer.tsx web/src/styles.css
git commit -m "feat(web): 对话式建计划草稿卡 + 旧对话入口切全局控制台"
```

---

## 验收对照（spec §6）

| Spec 条款 | 任务 |
|---|---|
| 1 数值接地单测（编数字拒/照抄过/量词豁免） | Task 2 |
| 2 多轮集成（第二轮 payload 含第一轮） | Task 5 `test_second_turn_carries_history` |
| 3 三处角标默认无工程明文、展开完整 | Task 6（飞书）+ Task 7（Web/回答） |
| 4 建计划确认前 DB 零写入、确认后 draft→armed | Task 9（复用既有端点 + 手动验收 4） |
| 5 禁用词/rule_id 白名单/acceptance gate 不回归 | Task 5 全量门禁 |
| 6 全量测试/门禁绿 | 每 task Step 门禁 + Task 9 收口 |
