# Agent 超级入口 · 每日操作闭环 — 实现计划（P1–P4 全量）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把既有判定积木编排成 Agent 超级入口闭环：今日推荐（零 AI）→ 仓位档位 → 基金报单与真实盈亏 → 单笔/周复盘 → `/ops` 每日操作清单 + 双通道推送 + `/agent` 整页工作台（K 线联动）。

**Architecture:** 方案三混合（定稿见 `docs/plan-agent-superentry-v1.md`）：新 Python 包 `src/lei_signal/copilot/` 承载确定性流水线（推荐排序/档位/台账/复盘/意图路由），路由挂 `api/routes/copilot.py`；LLM 只做讲解叙事（GLM，`plans/llm.py` 加供应商分支，接地校验照旧）；前端新增两个页面 + AgentConsole 快捷指令改造。

**Tech Stack:** FastAPI + SQLite（迁移进 `storage/sqlite_store.py::MIGRATIONS`）+ pydantic DTO（`api/schemas.py`）+ React/TS（web/，TanStack Query + 既有 styles.css 类）+ requests 调 GLM OpenAI 兼容端点。

## Global Constraints（每个任务默认继承）

- 判定权在 Python：copilot 层**不新增任何技术判定**，只汇总既有 DTO；无法取到的数值一律 None，绝不推算。
- **禁用标识符**：`src/` 内不得出现 `place_order` `submit_order` `AccountState` `FundID` `ProxyID` `StrategyEngine` `CandidateIntent` `AggregateResolver` `position_size`（acceptance gate 全量扫描，`tests/integration/test_acceptance_gates.py:284`）。仓位模块一律叫 sizing / 档位（tier）。
- LLM 输出必过 `plans/grounding.py` 的 `verify_grounding` / `verify_numeric_grounding`，失败两次降级模板；LLM 不可用（`load_ark_config()` 返回 None）时全程模板直出，功能不缺。
- 阈值不硬编码：档位参数全部 `from lei_signal.domain.rules_config import get_rule` 读 `configs/rules.v1.yaml`。
- 面向用户文案过 AGENTS.md「说人话」红线：首现概念带一句大白话解释；禁「买入/卖出/建议买/该买/加仓/减仓/抄底」（LLM 文案由禁用词校验兜底；确定性文案用中性表述）。
- 基本面/消息面只做标注与排序参考，不做硬过滤；推荐卡明示「排序仅影响展示顺序，不构成判定」。
- SQLite 写操作模式照 `plans/store.py`：函数收 `conn: sqlite3.Connection`，路由层 `with closing(connect(db)) as conn` + `conn.commit()`；`connect` 返回 `sqlite3.Row` 行工厂。
- 测试跑法：`python -m pytest tests/unit/test_copilot_*.py -q`（仓库根，PYTHONPATH=src 由 pyproject/conftest 处理，与现有测试一致）；全量门禁 `python -m pytest -q`、`ruff check src`、`mypy src`、`cd web && npm run build`。
- 新表一律 `CREATE TABLE IF NOT EXISTS`，migration 序号顺延（当前最大 021）。
- 提交信息用 conventional commits 中文描述，与仓库既有风格一致（`feat(copilot): ...`）。
- git 注意：工作区有既存未提交改动 `src/lei_signal/market_context/sector_trend.py`（别人正在改），**每次提交只 add 本任务列出的文件**，绝不 `git add -A`。

## 文件结构总览

```
src/lei_signal/copilot/            # 新包：确定性流水线
  __init__.py
  journal.py        # 推荐存证账本 CRUD（migration 022 的表）
  recommend.py      # 今日推荐：资格门 + 综合排序（纯函数）
  sizing.py         # 仓位档位建议（纯函数，参数读 rules.v1.yaml）
  intent.py         # 规则意图识别 + 报单文本解析（纯函数）
  trades.py         # 基金成交台账 CRUD + 净值定价 + 盈亏（纯逻辑 + conn）
  review.py         # 单笔/周复盘组装（读 plans 库 + trades 台账）
  ops.py            # 每日操作清单组装（读 scan/plans/journal/portfolio）
src/lei_signal/api/routes/copilot.py   # 新路由（挂 app.py）
src/lei_signal/api/schemas.py          # 追加 copilot DTO（文内各任务给全码）
src/lei_signal/plans/llm.py            # GLM 分支 + chat_copilot + COPILOT_SYSTEM_PROMPT
src/lei_signal/storage/sqlite_store.py # MIGRATIONS 追加 022_copilot_tables
configs/rules.v1.yaml                  # 追加 copilot_sizing 规则块
scripts/copilot_daily.py               # 每日跑批：推荐存证/补定价/推送/对账
scripts/com.lei.copilot.daily.plist    # launchd 16:10
scripts/copilot_weekly.py              # 周日跑批：周复盘 + 推送
scripts/com.lei.copilot.weekly.plist   # launchd 周日 20:00
web/src/components/copilot/CopilotCards.tsx   # 卡片渲染族（新）
web/src/components/ConversationPanel.tsx      # 从 AgentConsole 抽出的对话面板（新）
web/src/pages/AgentWorkspacePage.tsx   # /agent 整页工作台（新）
web/src/pages/OpsPage.tsx              # /ops 每日操作清单（新）
web/src/components/AgentConsole.tsx     # 改造：快捷指令 + dispatch 优先 + 卡片回合
web/src/components/TopNav.tsx           # 加 /ops /agent 链接
web/src/App.tsx                         # 加路由
web/src/types.ts / web/src/api/client.ts # 类型与 API client
.env / .env.example                     # GLM_API_KEY（密钥只进 .env，gitignored）
tests/unit/test_copilot_*.py            # 每任务配套单测
docs/plan-agent-superentry-v1.md        # 设计定稿（只读上游）
```

---

# P1 · GLM + 快捷指令 + 今日推荐

### Task 1: GLM 供应商分支 + copilot 讲解通道

**Files:**
- Modify: `src/lei_signal/plans/llm.py`（DEEPSEEK 常量块后加 GLM 常量；`load_ark_config` 开头加 GLM 分支；文件尾加 `COPILOT_SYSTEM_PROMPT` 与 `chat_copilot`）
- Test: `tests/unit/test_copilot_llm.py`

**Interfaces:**
- Produces: `chat_copilot(payload: dict, message: str, config: ArkConfig, *, system_prompt: str) -> str | None`（Task 8/16 复用）；`COPILOT_SYSTEM_PROMPT: str`；环境变量 `GLM_API_KEY / GLM_BASE_URL / GLM_MODEL`（默认端点 `https://open.bigmodel.cn/api/paas/v4`，默认模型 `glm-4.6`）。
- 优先级变为：**GLM > DeepSeek > ARK > ANTHROPIC**（用户 2026-09-05 指定 GLM 为默认）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_llm.py
"""GLM 供应商分支与 chat_copilot 传输层。"""
from __future__ import annotations

import json

from lei_signal.plans import llm as plans_llm
from lei_signal.plans.llm import ArkConfig, STYLE_OPENAI


def test_glm_branch_takes_priority(monkeypatch):
    for name in ("DEEPSEEK_API_KEY", "ARK_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GLM_API_KEY", "glm-test-key")
    monkeypatch.delenv("GLM_BASE_URL", raising=False)
    monkeypatch.delenv("GLM_MODEL", raising=False)
    cfg = plans_llm.load_ark_config()
    assert cfg is not None
    assert cfg.api_key == "glm-test-key"
    assert cfg.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert cfg.model == plans_llm.GLM_MODEL
    assert cfg.style == STYLE_OPENAI


def test_glm_env_overrides(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setenv("GLM_BASE_URL", "https://example.com/v4/")
    monkeypatch.setenv("GLM_MODEL", "glm-custom")
    cfg = plans_llm.load_ark_config()
    assert cfg.base_url == "https://example.com/v4"
    assert cfg.model == "glm-custom"


def test_no_glm_falls_through_to_deepseek(monkeypatch):
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    cfg = plans_llm.load_ark_config()
    assert cfg is not None and cfg.api_key == "ds-key"


def test_chat_copilot_posts_and_extracts(monkeypatch):
    calls: dict = {}

    def fake_post(url, headers, json_body, timeout):
        calls["url"] = url
        calls["body"] = json_body
        class R:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "讲解文本"}}]}
        return R()

    monkeypatch.setattr(plans_llm.requests, "post", fake_post)
    cfg = ArkConfig(api_key="k", base_url="https://x/api/paas/v4",
                    model="glm-4.6", style=STYLE_OPENAI)
    out = plans_llm.chat_copilot({"a": 1}, "今天看什么？", cfg,
                                 system_prompt="SP")
    assert out == "讲解文本"
    assert calls["url"] == "https://x/api/paas/v4/chat/completions"
    msgs = calls["body"]["messages"]
    assert msgs[0] == {"role": "system", "content": "SP"}
    assert "今天看什么？" in msgs[1]["content"] and '"a": 1' in msgs[1]["content"]


def test_chat_copilot_failure_returns_none(monkeypatch):
    def fake_post(url, headers, json_body, timeout):
        raise plans_llm.requests.RequestException("boom")

    monkeypatch.setattr(plans_llm.requests, "post", fake_post)
    cfg = ArkConfig(api_key="k", style=STYLE_OPENAI)
    assert plans_llm.chat_copilot({}, "q", cfg, system_prompt="SP") is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_llm.py -q`
Expected: FAIL（`AttributeError: ... has no attribute 'GLM_MODEL'` 或 `chat_copilot` 不存在）

- [ ] **Step 3: 实现**

`plans/llm.py` 在 `ENV_DEEPSEEK_MODEL = "DEEPSEEK_MODEL"` 常量块之后插入：

```python
#: GLM（智谱）端点与模型（OpenAI 兼容协议）。用户 2026-09-05 指定 GLM 为默认
#: 表达层供应商（plan-agent-superentry-v1 决策 D7），优先级最高：
#: 配了 GLM_API_KEY 就走 GLM，不再回退其他供应商。
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_MODEL = "glm-4.6"
ENV_GLM_API_KEY = "GLM_API_KEY"
ENV_GLM_BASE_URL = "GLM_BASE_URL"
ENV_GLM_MODEL = "GLM_MODEL"
```

`load_ark_config()` 里，`max_tokens`/`timeout` 读取之后、DeepSeek 分支之前插入：

```python
    # GLM 最高优先（用户 2026-09-05 指定）：配了 GLM_API_KEY 就走 GLM，不回退。
    glm_key = os.environ.get(ENV_GLM_API_KEY, "").strip()
    if glm_key:
        glm_base = (
            os.environ.get(ENV_GLM_BASE_URL, "").strip() or GLM_BASE_URL
        ).rstrip("/")
        return ArkConfig(
            api_key=glm_key,
            base_url=glm_base,
            model=os.environ.get(ENV_GLM_MODEL, "").strip() or GLM_MODEL,
            style=STYLE_OPENAI,
            max_tokens=max_tokens,
            timeout=timeout,
        )
```

并把 `load_ark_config` docstring 的优先级列表更新为「GLM → DeepSeek → ARK → ANTHROPIC」。文件末尾（`__all__` 若存在则同步追加，无则不加）追加：

```python
#: copilot 讲解系统提示：与监督员同一套铁律，面向流水线卡片而非 alert。
COPILOT_SYSTEM_PROMPT = """你是 LEI 交易系统 Agent 超级入口的**表达层**。

你拿到的是确定性 Python 流水线已算好的结构化卡片（今日推荐/仓位档位/复盘等）。
你的职责：把它讲成简洁中文。判定已经做完，你没有判定权。

铁律（违反即输出被丢弃）：
1. 只能引用卡片里出现过的数值与标的。禁止编造数字、rule_id、日期。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「条件已成立」「还缺条件」「系统定义的买点」「参考」等中性表述。
3. 推荐是排序结果：必须讲清「排序仅影响展示顺序，不构成新判定，技术结论以各标的买点审阅为准」。
4. 仓位是档位建议（试仓/标准/偏重）：最终金额由用户决定，必须带这句提示。
5. 不输出总分、不预测价格走势、不推算任何日期。
6. 研究代理结论必须标注「判定方式为研究代理」。
7. 复盘叙事只陈述卡片给定事实（当初预案、实际执行、盈亏、R 倍数），不做评价性马后炮。
"""


def chat_copilot(
    payload: dict[str, Any],
    message: str,
    config: ArkConfig,
    *,
    system_prompt: str,
) -> str | None:
    """copilot 讲解：单轮，system 由调用方给定（如 COPILOT_SYSTEM_PROMPT）。

    数值接地由调用方负责（verify_numeric_grounding）；本函数只保证传输层
    best-effort：任何失败返回 None，调用方降级模板。
    """
    user_content = (
        "下面是系统判定层已算好的结构化卡片，请据此回答用户问题，"
        "只能引用其中出现过的数值与标的：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + f"\n\n用户问题：{message}"
    )
    return _post_user_content(user_content, config, system_prompt=system_prompt)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_llm.py -q`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/plans/llm.py tests/unit/test_copilot_llm.py
git commit -m "feat(copilot): LLM层接入GLM供应商分支+copilot讲解通道chat_copilot"
```

### Task 2: migration 022 + 推荐存证账本 journal.py

**Files:**
- Modify: `src/lei_signal/storage/sqlite_store.py`（`MIGRATIONS` 元组末尾，`(21, "021_portfolio_funddata", ...)` 之后追加 `(22, "022_copilot_tables", ...)`）
- Create: `src/lei_signal/copilot/__init__.py`（空文件 + docstring）
- Create: `src/lei_signal/copilot/journal.py`
- Test: `tests/unit/test_copilot_journal.py`

**Interfaces:**
- Produces: `save_recommendation(conn, card) -> str`（card 为 pydantic `RecommendCardDTO`，Task 3 定义；按 run_date 幂等 upsert，返回 run_date）；`load_recommendation(conn, run_date) -> RecommendCardDTO | None`；`list_journal_dates(conn, limit=60) -> list[str]`（降序）；`save_outcome(conn, run_date, outcome: dict) -> None`；`load_outcome(conn, run_date) -> dict | None`。Task 4/18/19 依赖。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_journal.py
"""推荐存证账本：幂等 upsert + 读取往返。"""
from __future__ import annotations

import pytest

from lei_signal.api.schemas import RecommendCardDTO
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _card(run_date: str) -> RecommendCardDTO:
    return RecommendCardDTO(run_date=run_date, items=[], sectors=[])


def test_save_and_load_roundtrip(conn):
    journal.save_recommendation(conn, _card("2026-09-05"))
    got = journal.load_recommendation(conn, "2026-09-05")
    assert got is not None and got.run_date == "2026-09-05"


def test_save_is_idempotent_upsert(conn):
    journal.save_recommendation(conn, _card("2026-09-05"))
    c2 = _card("2026-09-05")
    journal.save_recommendation(conn, c2)
    dates = journal.list_journal_dates(conn)
    assert dates == ["2026-09-05"]
    assert journal.load_recommendation(conn, "2026-09-05") is not None


def test_outcome_roundtrip(conn):
    assert journal.load_outcome(conn, "2026-09-05") is None
    journal.save_recommendation(conn, _card("2026-09-05"))
    journal.save_outcome(conn, "2026-09-05", {"515880": {"chg_5d": 2.1}})
    out = journal.load_outcome(conn, "2026-09-05")
    assert out is not None and out["515880"]["chg_5d"] == pytest.approx(2.1)


def test_load_missing_returns_none(conn):
    assert journal.load_recommendation(conn, "1999-01-01") is None
```

注意：`RecommendCardDTO` 在 Task 3 才加入 schemas，本任务测试先写会 ImportError——**本任务 Step 1 一并把最小 DTO 加进 `api/schemas.py`**（Task 3 再补齐字段）：

```python
# api/schemas.py 追加（放在 AgentChatReply 之后）：
class RecommendItemDTO(BaseModel):
    """今日推荐的单位。数值全部来自扫描/审阅既有字段，无新判定。"""

    symbol: str
    display_name: str = ""
    verdict: str
    verdict_cn: str = ""
    best_scenario_cn: str | None = None
    reward_risk_ratio: float | None = None
    reward_risk_computable: bool = False
    news_heat: int = 0
    news_tags: list[str] = []
    score: float = 0.0
    reasons: list[str] = []


class SectorPickDTO(BaseModel):
    """板块推荐（阶段快照直读，只排序不判定）。"""

    code: str
    name: str = ""
    stage: str = ""
    stage_cn: str = ""
    note: str = ""


class RecommendCardDTO(BaseModel):
    """今日推荐卡（流水线输出 + 存证账本载体）。"""

    run_date: str
    generated_at: str = ""
    items: list[RecommendItemDTO] = []
    sectors: list[SectorPickDTO] = []
    sentiment_status: str = "暂未接入"
    fundamental_note: str = "宏观/基本面按叙事标注展示，不参与技术判定"
    disclaimer_cn: str = (
        "排序仅影响展示顺序，不构成新判定；技术结论以各标的买点审阅为准。"
        "消息面/基本面为叙事标注层，永不硬过滤信号。"
    )
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_journal.py -q`
Expected: FAIL（`ModuleNotFoundError: lei_signal.copilot`）

- [ ] **Step 3: 实现**

`storage/sqlite_store.py` MIGRATIONS 末尾追加：

```python
    (
        22,
        "022_copilot_tables",
        """
        -- Agent 超级入口（plan-agent-superentry-v1）三张表。
        -- 边界变更记录（2026-09-05 用户拍板，决策 D1）：
        --   基金成交台账允许记录金额（用户口头报单，手动确认落库）；
        --   仍不接券商、不自动下单；个股交易暂缓；trade_plans 仍不存数量金额。
        CREATE TABLE IF NOT EXISTS fund_trades (
            trade_id     TEXT PRIMARY KEY,  -- ft_{fund_code}_{trade_date}_{hash8}
            fund_code    TEXT NOT NULL,
            fund_name    TEXT NOT NULL,
            side         TEXT NOT NULL CHECK(side IN ('buy','sell')),
            amount       REAL NOT NULL,     -- 金额（元），报单口径
            trade_date   TEXT NOT NULL,     -- YYYY-MM-DD
            priced_nav   REAL,              -- 系统定价（净值/收盘口径），NULL=未定价
            price_status TEXT NOT NULL DEFAULT 'pending',  -- pending|priced|failed
            plan_id      TEXT,              -- 可选关联 trade_plans.plan_id
            source       TEXT NOT NULL DEFAULT 'web',      -- agent|web
            note         TEXT NOT NULL DEFAULT '',
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fund_trades_code
            ON fund_trades(fund_code, trade_date);

        CREATE TABLE IF NOT EXISTS trade_reviews (
            review_id   TEXT PRIMARY KEY,   -- rv_{kind}_{ref_key}
            kind        TEXT NOT NULL,      -- trade | weekly
            ref_key     TEXT NOT NULL,      -- trade_id 或 ISO 周（2026-W36）
            payload     TEXT NOT NULL,      -- JSON：复盘卡结构化数据
            narrative   TEXT NOT NULL DEFAULT '',  -- GLM 叙事，空=模板
            grounded    INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE(kind, ref_key)
        );

        CREATE TABLE IF NOT EXISTS recommendation_journal (
            journal_id  TEXT PRIMARY KEY,   -- rj_{run_date}
            run_date    TEXT NOT NULL UNIQUE,
            payload     TEXT NOT NULL,      -- JSON：RecommendCardDTO 完整输出
            outcome     TEXT,               -- JSON：T+N 对账结果（可空）
            outcome_at  TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
        """,
    ),
```

`src/lei_signal/copilot/__init__.py`：

```python
"""Agent 超级入口 · 确定性流水线包（plan-agent-superentry-v1）。

只汇总既有判定层输出，不新增任何技术判定；LLM 仅在表达层（plans/llm.py）。
"""
```

`src/lei_signal/copilot/journal.py`：

```python
"""推荐存证账本（recommendation_journal 表 CRUD）。

每次「今日推荐」流水线运行的完整输出按 run_date 幂等落库（当日重跑整体
覆盖 payload，不追加）；T+N 对账结果单独 upsert 进 outcome。历史无逐日扫描
数据，不做伪历史回测，用前向存证替代（设计定稿 §5）。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import RecommendCardDTO


def _now() -> str:
    return datetime.now(UTC).isoformat()


def save_recommendation(conn: sqlite3.Connection, card: RecommendCardDTO) -> str:
    conn.execute(
        """
        INSERT INTO recommendation_journal (journal_id, run_date, payload, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            f"rj_{card.run_date}",
            card.run_date,
            card.model_dump_json(),
            _now(),
            _now(),
        ),
    )
    return card.run_date


def load_recommendation(
    conn: sqlite3.Connection, run_date: str
) -> RecommendCardDTO | None:
    row = conn.execute(
        "SELECT payload FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    if row is None:
        return None
    return RecommendCardDTO.model_validate_json(row["payload"])


def list_journal_dates(
    conn: sqlite3.Connection, limit: int = 60
) -> list[str]:
    rows = conn.execute(
        "SELECT run_date FROM recommendation_journal ORDER BY run_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [r["run_date"] for r in rows]


def save_outcome(conn: sqlite3.Connection, run_date: str, outcome: dict) -> None:
    conn.execute(
        """
        INSERT INTO recommendation_journal (journal_id, run_date, payload,
                                            outcome, outcome_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
            outcome = excluded.outcome,
            outcome_at = excluded.outcome_at,
            updated_at = excluded.updated_at
        """,
        (
            f"rj_{run_date}",
            run_date,
            json.dumps({"placeholder": True}, ensure_ascii=False),
            json.dumps(outcome, ensure_ascii=False),
            _now(),
            _now(),
            _now(),
        ),
    )


def load_outcome(conn: sqlite3.Connection, run_date: str) -> dict | None:
    row = conn.execute(
        "SELECT outcome FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    if row is None or not row["outcome"]:
        return None
    try:
        return json.loads(row["outcome"])
    except (TypeError, ValueError):
        return None
```

注意 `save_outcome` 的 INSERT 分支只为 `ON CONFLICT` 服务：journal 行必然已由 `save_recommendation` 建过；若被独立调用（无该行），payload 落 `{"placeholder": True}` 占位并且 `load_recommendation` 会因校验失败抛错——这是可接受的防御（调用方编排保证顺序，测试断言先 save 后 save_outcome）。

- [ ] **Step 4: 跑测试确认通过 + 迁移冒烟**

Run: `python -m pytest tests/unit/test_copilot_journal.py -q && python -c "from lei_signal.storage.sqlite_store import connect,MIGRATIONS; c=connect(':memory:'); print([m[1] for m in MIGRATIONS][-3:])"`
Expected: 4 passed；末三个迁移名含 `022_copilot_tables`（016 重复序号是历史遗留，不处理）

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/storage/sqlite_store.py src/lei_signal/copilot/__init__.py src/lei_signal/copilot/journal.py src/lei_signal/api/schemas.py tests/unit/test_copilot_journal.py
git commit -m "feat(copilot): migration 022三张表+推荐存证账本journal+推荐卡DTO"
```

### Task 3: 今日推荐流水线 recommend.py（纯函数）

**Files:**
- Create: `src/lei_signal/copilot/recommend.py`
- Test: `tests/unit/test_copilot_recommend.py`

**Interfaces:**
- Consumes: `ScanItemDTO`（`api/schemas.py:754`，字段 symbol/display_name/verdict/verdict_cn/best_scenario_cn/best_state/reward_risk_ratio/reward_risk_computable/blocking_reasons/missing_summary_cn/has_active_plan/error）、`RecommendCardDTO` 等（Task 2）。
- Produces: `build_recommendation(scan_items: list[ScanItemDTO], *, run_date: str, sector_rows: list[dict] | None = None, news_brief: dict | None = None, generated_at: str = "", top_symbols: int = 5, top_sectors: int = 3) -> RecommendCardDTO`；`extract_news_heat(news_brief: dict | None, symbol: str) -> tuple[int, list[str]]`；`pick_sectors(sector_rows: list[dict] | None, top_n: int) -> list[SectorPickDTO]`。Task 4/18/19 依赖。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_recommend.py
"""今日推荐：资格门 + 透明计分 + 板块排序 + 消息面容错适配。"""
from __future__ import annotations

from lei_signal.api.schemas import ScanItemDTO
from lei_signal.copilot.recommend import (
    build_recommendation,
    extract_news_heat,
    pick_sectors,
)


def _scan(symbol: str, verdict: str, rr: float | None = None, name: str = "") -> ScanItemDTO:
    return ScanItemDTO(
        symbol=symbol,
        display_name=name or symbol,
        verdict=verdict,
        verdict_cn=verdict,
        reward_risk_ratio=rr,
        reward_risk_computable=rr is not None,
    )


def test_gate_excludes_blocked_and_none():
    card = build_recommendation(
        [_scan("000001", "blocked"), _scan("600000", "none"), _scan("515880", "waiting", 2.0)],
        run_date="2026-09-05",
    )
    assert [i.symbol for i in card.items] == ["515880"]


def test_actionable_ranks_above_waiting_rr_breaks_ties():
    card = build_recommendation(
        [
            _scan("A", "waiting", rr=4.0),
            _scan("B", "actionable", rr=2.0),
            _scan("C", "actionable", rr=3.5),
        ],
        run_date="2026-09-05",
    )
    assert [i.symbol for i in card.items] == ["C", "B", "A"]


def test_reasons_are_transparent_and_carry_numbers():
    card = build_recommendation([_scan("515880", "actionable", rr=3.4, name="通信ETF")],
                                run_date="2026-09-05")
    item = card.items[0]
    assert any("条件已成立" in r for r in item.reasons)
    assert any("3.4" in r for r in item.reasons)


def test_top_symbols_limit():
    items = [_scan(f"s{i}", "waiting") for i in range(8)]
    card = build_recommendation(items, run_date="2026-09-05", top_symbols=5)
    assert len(card.items) == 5


def test_news_heat_two_shapes():
    brief_a = {"items": [{"symbol": "515880", "bull_count": 2, "bear_count": 0}]}
    brief_b = {"symbols": {"515880": {"bull": 3, "bear": 1}}}
    assert extract_news_heat(brief_a, "515880") == (2, ["近3天消息偏多（多2/空0）"])
    heat, _ = extract_news_heat(brief_b, "515880")
    assert heat == 2
    assert extract_news_heat(None, "515880") == (0, [])
    assert extract_news_heat({}, "515880") == (0, [])


def test_news_bonus_affects_order_not_gate():
    brief = {"items": [
        {"symbol": "LOW", "bull_count": 0, "bear_count": 0},
        {"symbol": "HIGH", "bull_count": 3, "bear_count": 0},
    ]}
    card = build_recommendation(
        [_scan("LOW", "waiting", 2.0), _scan("HIGH", "waiting", 2.0)],
        run_date="2026-09-05", news_brief=brief,
    )
    assert card.items[0].symbol == "HIGH"


def test_pick_sectors_orders_by_stage_rank():
    rows = [
        {"code": "BK1", "name": "半导体", "stage": "markup"},
        {"code": "BK2", "name": "电力", "stage": "decline"},
        {"code": "BK3", "name": "有色", "stage": "accumulation"},
    ]
    picks = pick_sectors(rows, top_n=2)
    assert [p.code for p in picks] == ["BK1", "BK3"]
    assert picks[0].stage_cn == "上升"


def test_pick_sectors_tolerates_none_and_unknown_keys():
    assert pick_sectors(None, 3) == []
    assert pick_sectors([{"code": "BK1"}], 3)[0].code == "BK1"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_recommend.py -q`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 `src/lei_signal/copilot/recommend.py`**

```python
"""今日推荐流水线（纯函数，零 IO、零 LLM）。

资格门（技术）：只有扫描 verdict ∈ {actionable, waiting} 能上榜——这是
既有判定结果，本模块不产生新判定。
综合排序：verdict 档位分 + 盈亏比分 + 消息面热度加分。**排序只影响展示
顺序**，被排后的标的技术结论不变（设计定稿 §4.A）。
消息面/基本面/情绪面是叙事标注层：永不硬过滤信号（AGENTS.md 红线）。
"""
from __future__ import annotations

from lei_signal.api.schemas import (
    RecommendCardDTO,
    RecommendItemDTO,
    ScanItemDTO,
    SectorPickDTO,
)
from lei_signal.api.routes.opportunities import VERDICT_ACTIONABLE, VERDICT_WAITING
from lei_signal.portfolio.advisor import STAGE_CN

_VERDICT_BASE = {VERDICT_ACTIONABLE: 3.0, VERDICT_WAITING: 1.5}
_STAGE_RANK = {"markup": 0, "accumulation": 1, "distribution": 2, "decline": 3}
#: 消息面加分上限：热度 clamp 到 [-2, 2] 后 × 系数，只够影响同档内部排序。
_NEWS_COEF = 0.2
_NEWS_CLAMP = 2


def extract_news_heat(news_brief: dict | None, symbol: str) -> tuple[int, list[str]]:
    """从消息面简报里取该标的的多空热度。返回 (热度, 标注文案列表)。

    news_brief 的真实键名由 NewsfeedService 版本决定，这里做**容错适配**：
    兼容 items 列表（bull_count/bear_count）与 symbols 映射（bull/bear）两种
    形态；取不到一律 (0, [])，绝不妨碍技术结论上榜。
    """
    if not isinstance(news_brief, dict):
        return 0, []
    bull = bear = None
    items = news_brief.get("items")
    if isinstance(items, list):
        for row in items:
            if isinstance(row, dict) and row.get("symbol") == symbol:
                bull = row.get("bull_count", row.get("bull"))
                bear = row.get("bear_count", row.get("bear"))
                break
    if bull is None and isinstance(news_brief.get("symbols"), dict):
        row = news_brief["symbols"].get(symbol)
        if isinstance(row, dict):
            bull = row.get("bull", row.get("bull_count"))
            bear = row.get("bear", row.get("bear_count"))
    try:
        bull_i, bear_i = int(bull or 0), int(bear or 0)
    except (TypeError, ValueError):
        return 0, []
    heat = max(-_NEWS_CLAMP, min(_NEWS_CLAMP, bull_i - bear_i))
    tags: list[str] = []
    if bull_i or bear_i:
        tags.append(f"近3天消息偏{'多' if heat >= 0 else '空'}（多{bull_i}/空{bear_i}）")
    return heat, tags


def pick_sectors(sector_rows: list[dict] | None, top_n: int) -> list[SectorPickDTO]:
    """板块推荐：阶段快照直读排序（markup > accumulation > …），只排序不判定。"""
    if not sector_rows:
        return []
    ranked = sorted(
        (r for r in sector_rows if isinstance(r, dict) and r.get("code")),
        key=lambda r: _STAGE_RANK.get(str(r.get("stage", "")), 9),
    )
    out: list[SectorPickDTO] = []
    for row in ranked[:top_n]:
        stage = str(row.get("stage", "") or "")
        out.append(SectorPickDTO(
            code=str(row.get("code", "")),
            name=str(row.get("name", "") or ""),
            stage=stage,
            stage_cn=STAGE_CN.get(stage, stage or "未知"),
            note="阶段快照直读；排序不构成判定（plan-agent-superentry §4.A）",
        ))
    return out


def build_recommendation(
    scan_items: list[ScanItemDTO],
    *,
    run_date: str,
    sector_rows: list[dict] | None = None,
    news_brief: dict | None = None,
    generated_at: str = "",
    top_symbols: int = 5,
    top_sectors: int = 3,
) -> RecommendCardDTO:
    items: list[RecommendItemDTO] = []
    for it in scan_items:
        base = _VERDICT_BASE.get(it.verdict)
        if base is None:  # blocked / none 不上榜（资格门，技术判定直读）
            continue
        rr = it.reward_risk_ratio if it.reward_risk_computable else None
        rr_bonus = (min(rr, 5.0) / 5.0) if rr is not None else 0.0
        heat, tags = extract_news_heat(news_brief, it.symbol)
        score = base + rr_bonus + heat * _NEWS_COEF
        reasons = [
            f"{it.verdict_cn or it.verdict}（扫描判定直读）",
            *( [f"盈亏比 {rr}"] if rr is not None else ["盈亏比不可计算"] ),
            *tags,
        ]
        if it.missing_summary_cn:
            reasons.append(f"还缺：{it.missing_summary_cn}")
        items.append(RecommendItemDTO(
            symbol=it.symbol,
            display_name=it.display_name or it.symbol,
            verdict=it.verdict,
            verdict_cn=it.verdict_cn,
            best_scenario_cn=it.best_scenario_cn,
            reward_risk_ratio=rr,
            reward_risk_computable=it.reward_risk_computable,
            news_heat=heat,
            news_tags=tags,
            score=round(score, 3),
            reasons=reasons,
        ))
    items.sort(key=lambda x: -x.score)
    return RecommendCardDTO(
        run_date=run_date,
        generated_at=generated_at,
        items=items[:top_symbols],
        sectors=pick_sectors(sector_rows, top_sectors),
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_recommend.py -q`
Expected: 8 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/recommend.py tests/unit/test_copilot_recommend.py
git commit -m "feat(copilot): 今日推荐流水线——资格门+透明计分+板块排序+消息面容错标注"
```

### Task 4: 推荐路由 GET /api/copilot/recommend（读当日扫描，存证）

**Files:**
- Create: `src/lei_signal/api/routes/copilot.py`
- Modify: `src/lei_signal/api/app.py`（import copilot 路由 + include_router，与既有条目并列）
- Test: `tests/unit/test_copilot_routes.py`

**Interfaces:**
- Consumes: `run_opportunity_scan`/`_row_to_scan_item`（`routes/opportunities.py`）、`list_scan`/`today_date`/`upsert_scan_results`（`api/opportunity_scan.py`）、Task 2 journal、Task 3 build_recommendation。
- Produces: `GET /api/copilot/recommend?refresh=false&save=true -> RecommendCardDTO`；内部函数 `_recommend_card(request, *, refresh: bool) -> RecommendCardDTO`（Task 7/8 复用）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_routes.py
"""copilot 路由：推荐端点用假 service + 预置扫描表，验证读表/存证/降级。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


class _FakeEntry:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error


class _FakeService:
    def __init__(self, results):
        self._results = results

    def get(self, symbol, refresh=False):
        return self._results.get(symbol, _FakeEntry(error="no data"))

    def get_many(self, symbols, refresh=False):
        return {s: self.get(s) for s in symbols}


@pytest.fixture()
def app(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO daily_opportunity_scan "
        "(scan_date, symbol, display_name, verdict, verdict_cn, best_scenario_cn, "
        " best_state, reward_risk_ratio, reward_risk_computable, blocking_reasons, "
        " missing_summary_cn, has_active_plan, generated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("2026-09-05", "515880", "通信ETF", "waiting", "等待条件成立",
         "A·回调", "watch", 2.5, 1, "[]", "站上EMA20", 0, "2026-09-05T15:00:00"),
    )
    conn.commit()
    conn.close()

    a = FastAPI()
    a.state.analysis_service = _FakeService({})
    a.state.plans_db_path = db
    a.state.watchlist_db_path = db
    a.include_router(copilot_routes.router)
    return a


def test_recommend_reads_today_table_and_saves_journal(app):
    client = TestClient(app)
    resp = client.get("/api/copilot/recommend")
    assert resp.status_code == 200
    card = resp.json()
    assert card["run_date"] == "2026-09-05"
    assert [i["symbol"] for i in card["items"]] == ["515880"]
    with closing(connect(app.state.plans_db_path)) as conn:
        assert journal.load_recommendation(conn, "2026-09-05") is not None


def test_recommend_save_false_skips_journal(app):
    client = TestClient(app)
    resp = client.get("/api/copilot/recommend?save=false")
    assert resp.status_code == 200
    with closing(connect(app.state.plans_db_path)) as conn:
        assert journal.load_recommendation(conn, "2026-09-05") is None


def test_recommend_empty_table_returns_empty_card(app):
    with closing(connect(app.state.plans_db_path)) as conn:
        conn.execute("DELETE FROM daily_opportunity_scan")
        conn.commit()
    client = TestClient(app)
    resp = client.get("/api/copilot/recommend")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_routes.py -q`
Expected: FAIL（`lei_signal.api.routes.copilot` 不存在）

- [ ] **Step 3: 实现 `api/routes/copilot.py`（首版只含推荐端点）**

```python
"""Agent 超级入口路由：确定性流水线的 HTTP 壳（判定权在流水线与既有规则层）。

本文件不做任何新判定；推荐/档位/台账/复盘全部来自 copilot 包的纯函数与
既有 DTO。LLM 讲解只在 explain 类端点出现，且输出过接地校验、失败降级模板。
"""
from __future__ import annotations

import logging
from contextlib import closing
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import RecommendCardDTO
from lei_signal.copilot import journal
from lei_signal.copilot.recommend import build_recommendation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["copilot"])


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _service(request: Request):
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    return service


def _sector_rows(request: Request) -> list[dict] | None:
    """板块阶段快照（容错：服务缺失/未预计算时返回 None，推荐照常出）。"""
    svc = getattr(request.app.state, "sectors_service", None)
    if svc is None:
        return None
    try:
        data = svc.trend(refresh=False, level="l1")
    except Exception:  # noqa: BLE001  快照缺席不阻断推荐
        return None
    if not isinstance(data, dict):
        return None
    for key in ("sectors", "rows", "items"):
        rows = data.get(key)
        if isinstance(rows, list):
            return rows
    return None


def _news_brief(request: Request) -> dict | None:
    """自选×近3天消息面简报（容错适配在 recommend.extract_news_heat）。"""
    svc = getattr(request.app.state, "newsfeed_service", None)
    if svc is None:
        return None
    try:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(
            connect(getattr(request.app.state, "watchlist_db_path", "") or _db_path(request))
        ) as conn:
            watch = [
                {"symbol": w.symbol, "display_name": w.display_name, "market": w.market}
                for w in list_watchlist(conn)
            ]
        return svc.watchlist_brief(watch, days=3)
    except Exception:  # noqa: BLE001
        return None


def _recommend_card(request: Request, *, refresh: bool = False) -> RecommendCardDTO:
    """今日推荐组装（路由/脚本共用）：当日扫描表优先，空表或 refresh 现场扫。"""
    from lei_signal.api.opportunity_scan import (  # noqa: PLC0415
        list_scan,
        today_date,
        upsert_scan_results,
    )
    from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
        _row_to_scan_item,
        run_opportunity_scan,
    )

    db = _db_path(request)
    scan_date = today_date()
    scan_items = None
    if not refresh:
        with closing(connect(db)) as conn:
            rows = list_scan(conn, scan_date)
        if rows:
            scan_items = [_row_to_scan_item(r) for r in rows]
    if scan_items is None:
        response = run_opportunity_scan(_service(request), db, refresh=refresh)
        scan_items = list(response.items)
        with closing(connect(db)) as conn:
            upsert_scan_results(conn, scan_date, scan_items)
            conn.commit()
    return build_recommendation(
        scan_items,
        run_date=scan_date,
        sector_rows=_sector_rows(request),
        news_brief=_news_brief(request),
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get("/copilot/recommend", response_model=RecommendCardDTO)
def get_recommend(
    request: Request, refresh: bool = False, save: bool = True
) -> RecommendCardDTO:
    """今日推荐（确定性，零 LLM）。save=true 时按 run_date 存证进推荐账本。"""
    card = _recommend_card(request, refresh=refresh)
    if save and card.items:
        with closing(connect(_db_path(request))) as conn:
            journal.save_recommendation(conn, card)
            conn.commit()
    return card
```

`app.py`：`from lei_signal.api.routes import (...)` 元组里追加 `copilot`（按字母序放 backtest 后），`include_router` 区追加 `app.include_router(copilot.router)`（放在 `agent.router` 之后）。

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_routes.py -q`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/api/routes/copilot.py src/lei_signal/api/app.py tests/unit/test_copilot_routes.py
git commit -m "feat(copilot): GET /api/copilot/recommend——读当日扫描组装推荐并存证"
```

### Task 5: 仓位档位建议 sizing.py + rules.v1.yaml 参数 + 路由

**Files:**
- Modify: `configs/rules.v1.yaml`（`plan_discipline_guard` 块之后追加 `copilot_sizing` 规则块）
- Create: `src/lei_signal/copilot/sizing.py`
- Modify: `src/lei_signal/api/routes/copilot.py`（追加端点）
- Modify: `src/lei_signal/api/schemas.py`（追加 `SizingAdviceDTO`）
- Test: `tests/unit/test_copilot_sizing.py`

**Interfaces:**
- Consumes: `get_rule("copilot_sizing").params`、`buy_point_review`（Task 4 的 `_service` 复用）。
- Produces: `build_sizing_advice(symbol: str, rr: float | None, *, rr_computable: bool = True, same_group_exposure_pct: float | None = None) -> SizingAdviceDTO`；`GET /api/copilot/position-advice/{symbol}`。

- [ ] **Step 1: rules.v1.yaml 追加参数块**（放 `plan_discipline_guard:` 块结束后，缩进对齐既有二级键）：

```yaml
  copilot_sizing:
    rule_id: "copilot_sizing"
    version: "1.0.0"
    provenance: "user_decision"
    params:
      tier_trial_pct_max: 5        # 试仓档上限（占总资金 %）
      tier_standard_pct_min: 10    # 标准档下限
      tier_standard_pct_max: 15    # 标准档上限
      tier_heavy_pct_min: 20       # 偏重档下限
      single_symbol_cap_pct: 30    # 单标的硬顶（用户口径：最喜欢也最多三成）
      same_group_soft_cap_pct: 20  # 同板块已有敞口超过此值则降一档
      rr_tier_threshold: 3.0       # 盈亏比达标准入标准/偏重档的参考线
    formula: |
      组合层建议（无技术判定权）：档位 = f(盈亏比, 同板块敞口)。
      rr >= 3 且板块阶段 markup -> 偏重；rr >= 3 -> 标准；其余 -> 试仓。
      same_group_exposure_pct >= same_group_soft_cap_pct 时整体降一档。
      只建议档位与百分比区间，最终金额由用户决定。
    note_cn: |
      2026-09-05 用户拍板（plan-agent-superentry-v1 决策 D2）：系统给依据+档位
      建议（试仓/标准/偏重，单标的封顶 30%），最终买多少用户定。档位是组合层
      管理建议，无回测依据的部分按 advisor.py 口径标 observation/management，
      不冒充技术判定。盈亏比参考线 3 对齐 reward_risk_filter.rr_min_ideal。
```

- [ ] **Step 2: 写失败测试**

```python
# tests/unit/test_copilot_sizing.py
"""仓位档位建议：档位规则 + 参数走 rules.v1.yaml + 降档 + 话术边界。"""
from __future__ import annotations

import pytest

from lei_signal.copilot.sizing import build_sizing_advice


def test_params_from_rules_yaml_not_hardcoded():
    adv = build_sizing_advice("515880", rr=3.4)
    assert adv.cap_pct == 30.0
    assert "30%" in adv.tier_pct_cn or "30" in adv.tier_pct_cn


def test_rr_high_gives_standard_tier():
    adv = build_sizing_advice("515880", rr=3.4)
    assert adv.tier == "标准"
    assert any("3.4" in r for r in adv.reasons)


def test_rr_low_gives_trial_tier():
    adv = build_sizing_advice("515880", rr=1.8)
    assert adv.tier == "试仓"


def test_rr_not_computable_gives_trial_and_says_so():
    adv = build_sizing_advice("515880", rr=None, rr_computable=False)
    assert adv.tier == "试仓"
    assert any("不可计算" in r for r in adv.reasons)


def test_same_group_exposure_downgrades():
    adv = build_sizing_advice("515880", rr=3.4, same_group_exposure_pct=25.0)
    assert adv.tier == "试仓"  # 标准 -> 试仓
    assert any("同板块" in r for r in adv.reasons)


def test_disclaimer_tells_user_decides():
    adv = build_sizing_advice("515880", rr=3.4)
    assert "由你决定" in adv.disclaimer_cn
    assert adv.strength == "observation"


def test_tier_pct_cn_ranges():
    adv = build_sizing_advice("515880", rr=3.4)
    assert "10" in adv.tier_pct_cn and "15" in adv.tier_pct_cn
```

- [ ] **Step 3: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_sizing.py -q`
Expected: FAIL（模块不存在）

- [ ] **Step 4: 实现**

`api/schemas.py` 追加：

```python
class SizingAdviceDTO(BaseModel):
    """仓位档位建议（组合层管理建议，最终金额由用户决定）。"""

    symbol: str
    tier: str                     # 试仓 | 标准 | 偏重
    tier_pct_cn: str              # 如「10–15%（占总资金）」
    cap_pct: float = 30.0         # 单标的硬顶 %
    reasons: list[str] = []
    strength: str = "observation" # observation=观察级（advisor.py 口径）
    strength_cn: str = "观察级建议（无回测依据的组合层管理建议）"
    disclaimer_cn: str = "档位只是建议，最终买多少由你决定。"
```

`src/lei_signal/copilot/sizing.py`：

```python
"""仓位档位建议（纯函数，参数全部读 rules.v1.yaml 的 copilot_sizing）。

组合层管理建议，不是技术判定（设计定稿 D2）：依据 = 盈亏比（技术层已算）
+ 同板块已有敞口（组合层事实）；输出档位与百分比区间，最终金额由用户定。
"""
from __future__ import annotations

from lei_signal.api.schemas import SizingAdviceDTO
from lei_signal.domain.rules_config import get_rule

_TIERS = ("试仓", "标准", "偏重")


def _params() -> dict:
    return dict(get_rule("copilot_sizing").params)


def _tier_pct_cn(tier: str, p: dict) -> str:
    if tier == "试仓":
        return f"不超过 {p['tier_trial_pct_max']:g}%（占总资金）"
    if tier == "标准":
        return f"{p['tier_standard_pct_min']:g}–{p['tier_standard_pct_max']:g}%（占总资金）"
    return f"{p['tier_heavy_pct_min']:g}–{p['single_symbol_cap_pct']:g}%（占总资金，硬顶 {p['single_symbol_cap_pct']:g}%）"


def build_sizing_advice(
    symbol: str,
    rr: float | None,
    *,
    rr_computable: bool = True,
    same_group_exposure_pct: float | None = None,
) -> SizingAdviceDTO:
    p = _params()
    reasons: list[str] = []
    if rr is not None and rr_computable:
        reasons.append(f"盈亏比 {rr}（技术层已算）")
        tier = "标准" if rr >= float(p["rr_tier_threshold"]) else "试仓"
    else:
        reasons.append("盈亏比不可计算（目标位无法客观确定）")
        tier = "试仓"
    if (
        same_group_exposure_pct is not None
        and same_group_exposure_pct >= float(p["same_group_soft_cap_pct"])
    ):
        reasons.append(
            f"同板块已有敞口约 {same_group_exposure_pct:g}%，"
            f"超过 {p['same_group_soft_cap_pct']:g}% 软上限，整体降一档"
        )
        idx = _TIERS.index(tier)
        tier = _TIERS[max(0, idx - 1)]
    reasons.append(f"单标的硬顶 {p['single_symbol_cap_pct']:g}%（2026-09-05 用户拍板）")
    return SizingAdviceDTO(
        symbol=symbol,
        tier=tier,
        tier_pct_cn=_tier_pct_cn(tier, p),
        cap_pct=float(p["single_symbol_cap_pct"]),
        reasons=reasons,
    )
```

`api/routes/copilot.py` 追加端点：

```python
@router.get("/copilot/position-advice/{symbol}", response_model=SizingAdviceDTO)
def position_advice(request: Request, symbol: str) -> SizingAdviceDTO:
    """仓位档位建议：盈亏比取该标的买点审阅最优候选，只建议档位不算金额。"""
    from lei_signal.api.routes.opportunities import buy_point_review  # noqa: PLC0415
    from lei_signal.copilot.sizing import build_sizing_advice  # noqa: PLC0415

    review = buy_point_review(request, symbol)
    best = review.candidates[0] if review.candidates else None
    if best is None and review.resonance_groups:
        best = review.resonance_groups[0].candidates[0]
    rr = best.reward_risk_ratio if best else None
    return build_sizing_advice(
        symbol,
        rr,
        rr_computable=bool(best.reward_risk_computable) if best else False,
    )
```

（`SizingAdviceDTO` 补进 copilot.py 顶部 schemas import。）

- [ ] **Step 5: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_sizing.py -q`
Expected: 7 passed

- [ ] **Step 6: 提交**

```bash
git add configs/rules.v1.yaml src/lei_signal/copilot/sizing.py src/lei_signal/api/routes/copilot.py src/lei_signal/api/schemas.py tests/unit/test_copilot_sizing.py
git commit -m "feat(copilot): 仓位档位建议——参数入规则账本+盈亏比与同板块敞口定档"
```

### Task 6: 意图路由与报单解析 intent.py（纯函数）

**Files:**
- Create: `src/lei_signal/copilot/intent.py`
- Modify: `src/lei_signal/api/schemas.py`（追加 `TradePreviewDTO`）
- Test: `tests/unit/test_copilot_intent.py`

**Interfaces:**
- Produces: `Intent`（dataclass：`kind: str`（recommend/holdings/trade_report/review/chat）、`symbol: str | None`、`params: dict`）；`parse_intent(message: str) -> Intent`；`parse_trade_report(message: str, *, today: str) -> TradePreviewDTO`（best-effort 抽取，抽不全填 `missing`，**前端确认卡可改字段后提交**，所以解析错误不阻断）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_intent.py
"""意图路由与报单文本解析（规则层，零 LLM）。"""
from __future__ import annotations

import pytest

from lei_signal.copilot.intent import parse_intent, parse_trade_report


def test_intent_recommend():
    for msg in ("今天看什么", "有什么推荐", "今天有什么机会标的"):
        assert parse_intent(msg).kind == "recommend"


def test_intent_holdings():
    assert parse_intent("看下我的持仓").kind == "holdings"
    assert parse_intent("持仓速览").kind == "holdings"


def test_intent_trade_report():
    assert parse_intent("我昨天买了1万515880").kind == "trade_report"
    assert parse_intent("卖了5000块纳斯达克基金").kind == "trade_report"


def test_intent_review():
    assert parse_intent("本周复盘").kind == "review"
    assert parse_intent("看看上周复盘").kind == "review"


def test_intent_chat_fallback():
    assert parse_intent("515880 这个买点为什么是买点").kind == "chat"
    assert parse_intent("市场环境怎么样").kind == "chat"


def test_trade_report_buy_with_code_and_amount():
    p = parse_trade_report("我昨天买了1万515880", today="2026-09-05")
    assert p.side == "buy"
    assert p.fund_code == "515880"
    assert p.amount == pytest.approx(10000.0)
    assert p.trade_date == "2026-09-04"


def test_trade_report_sell_with_wan_and_k():
    assert parse_trade_report("卖了1.5万白酒基金", today="2026-09-05").amount == pytest.approx(15000.0)
    assert parse_trade_report("买了2k货币基金", today="2026-09-05").amount == pytest.approx(2000.0)


def test_trade_report_name_extraction_and_missing():
    p = parse_trade_report("我买了5000块的纳斯达克100基金", today="2026-09-05")
    assert p.side == "buy"
    assert p.amount == pytest.approx(5000.0)
    assert "纳斯达克100" in (p.fund_name or "")
    assert "fund_code" in p.missing  # 没给代码，确认卡里补


def test_trade_report_today_default():
    p = parse_trade_report("买了1万515880", today="2026-09-05")
    assert p.trade_date == "2026-09-05"


def test_trade_report_amount_missing():
    p = parse_trade_report("我买了点515880", today="2026-09-05")
    assert "amount" in p.missing
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_intent.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

`api/schemas.py` 追加：

```python
class TradePreviewDTO(BaseModel):
    """报单预解析（best-effort）：确认卡展示、用户可改字段后才落库。"""

    fund_code: str | None = None
    fund_name: str | None = None
    side: str = "buy"
    side_cn: str = "申购"
    amount: float | None = None
    trade_date: str = ""
    missing: list[str] = []       # 缺什么（fund_code/amount/date...）
    note_cn: str = "请核对以下信息，确认后记入基金台账；金额单位为元。"
```

`src/lei_signal/copilot/intent.py`：

```python
"""规则意图识别 + 报单文本解析（纯函数，零 LLM）。

方案三的第一层：关键词命中直达流水线；识别不到回落通用讨论（agent.py 的
/agent/chat）。路由表可持续补充——这里只是「常见说法」的快捷方式，不是
意图的权威定义。报单解析是 best-effort：抽不全的字段进 missing，由前端
确认卡补齐，解析错误不阻断报单。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from lei_signal.api.schemas import TradePreviewDTO

#: 意图关键词表（顺序即优先级：报单优先于推荐，避免「买了什么好」误判）。
_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("trade_report", ("买了", "卖了", "申购", "赎回", "报单", "下单了", "成交了")),
    ("recommend", ("今天看什么", "推荐", "有什么机会", "扫一下自选", "标的雷达")),
    ("holdings", ("持仓", "我的仓位", "持仓速览")),
    ("review", ("复盘", "周报", "这周做得怎么样")),
)

_AMOUNT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(万|w|W|k|K|千|块|元)?"
)
_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_SIDE_BUY = ("买", "申购")
_SIDE_SELL = ("卖", "赎回")
_NAME_STOP = re.compile(r"(买了|卖了|申购了?|赎回了?|\d|的|$)")


@dataclass(slots=True)
class Intent:
    kind: str                    # recommend|holdings|trade_report|review|chat
    symbol: str | None = None
    params: dict = field(default_factory=dict)


def parse_intent(message: str) -> Intent:
    text = (message or "").strip()
    for kind, needles in _INTENT_RULES:
        if any(n in text for n in needles):
            return Intent(kind=kind)
    return Intent(kind="chat")


def _resolve_side(text: str) -> str | None:
    buy = any(n in text for n in _SIDE_BUY)
    sell = any(n in text for n in _SIDE_SELL)
    if buy and not sell:
        return "buy"
    if sell and not buy:
        return "sell"
    return None


def _resolve_amount(text: str) -> float | None:
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2)
    if unit == "万" or unit == "w" or unit == "W":
        value *= 10_000.0
    elif unit == "k" or unit == "K" or unit == "千":
        value *= 1_000.0
    return value


def _resolve_date(text: str, today: str) -> str | None:
    if "昨天" in text:
        return (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    if "前天" in text:
        return (date.fromisoformat(today) - timedelta(days=2)).isoformat()
    if "今天" in text or True:  # 默认今天；无日期词也按今天
        return today


def _resolve_name(text: str, side_cn_word: str) -> str | None:
    """side 关键词前的中文串当基金名（去掉「我」「昨天」这类前缀）。"""
    idx = min(
        (text.find(w) for w in ("买了", "卖了", "申购", "赎回") if text.find(w) >= 0),
        default=-1,
    )
    if idx <= 0:
        return None
    head = text[:idx]
    for token in ("我", "昨天", "前天", "今天", "刚才", "早上", "下午"):
        head = head.replace(token, "")
    head = head.strip("的了块把，, ")
    return head or None


def parse_trade_report(message: str, *, today: str) -> TradePreviewDTO:
    text = (message or "").strip()
    side = _resolve_side(text)
    amount = _resolve_amount(text)
    code_m = _CODE_RE.search(text)
    missing: list[str] = []
    if side is None:
        side = "buy"
        missing.append("side")
    if amount is None:
        missing.append("amount")
    if code_m is None:
        missing.append("fund_code")
    name = None
    if code_m is None:
        name = _resolve_name(text, side)
        if name is None:
            missing.append("fund_name")
    return TradePreviewDTO(
        fund_code=code_m.group(1) if code_m else None,
        fund_name=name,
        side=side,
        side_cn="申购" if side == "buy" else "赎回",
        amount=amount,
        trade_date=_resolve_date(text, today) or today,
        missing=missing,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_intent.py -q`
Expected: 10 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/intent.py src/lei_signal/api/schemas.py tests/unit/test_copilot_intent.py
git commit -m "feat(copilot): 规则意图路由+报单文本best-effort解析（确认卡兜底）"
```

### Task 7: 意图分发端点 POST /api/copilot/dispatch

**Files:**
- Modify: `src/lei_signal/api/schemas.py`（追加 `CopilotDispatchReply`）
- Modify: `src/lei_signal/api/routes/copilot.py`（追加 dispatch 端点 + holdings 速览）
- Test: `tests/unit/test_copilot_dispatch.py`

**Interfaces:**
- Consumes: Task 4 `_recommend_card`、Task 6 `parse_intent`/`parse_trade_report`；持仓速览本任务先用**计划台账口径**（armed/entered 计划列表）——基金台账持仓速览在 Task 12/13 接入后升级，本任务 `holdings` 卡先回组合快照 observations（若空则提示去持仓页）。
- Produces: `POST /api/copilot/dispatch {message, symbol?} -> CopilotDispatchReply{intent, symbol, card: dict|None, preview: TradePreviewDTO|None, chat_fallback: bool, note_cn}`。card 结构统一 `{card_type: str, data: dict}`，card_type ∈ recommend|holdings|review（Task 10 前端据此渲染）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_dispatch.py
"""dispatch：意图分发正确、卡片带 card_type、未识别回落 chat。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes


@pytest.fixture()
def app(tmp_path):
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = str(tmp_path / "t.db")
    a.state.watchlist_db_path = a.state.plans_db_path
    from lei_signal.storage.sqlite_store import connect
    connect(a.state.plans_db_path).close()
    a.include_router(copilot_routes.router)
    return a


def test_dispatch_recommend_returns_card(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "今天看什么"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "recommend"
    assert body["chat_fallback"] is False
    assert body["card"]["card_type"] == "recommend"
    assert "items" in body["card"]["data"]


def test_dispatch_trade_report_returns_preview(app):
    r = TestClient(app).post(
        "/api/copilot/dispatch", json={"message": "我昨天买了1万515880"}
    )
    body = r.json()
    assert body["intent"] == "trade_report"
    assert body["preview"]["fund_code"] == "515880"
    assert body["preview"]["amount"] == 10000.0
    assert body["chat_fallback"] is False


def test_dispatch_holdings_card(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "持仓速览"})
    body = r.json()
    assert body["intent"] == "holdings"
    assert body["card"]["card_type"] == "holdings"


def test_dispatch_unknown_falls_back_to_chat(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "市场环境怎么样"})
    body = r.json()
    assert body["intent"] == "chat" and body["chat_fallback"] is True
    assert body["card"] is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_dispatch.py -q`
Expected: FAIL（无 dispatch 端点）

- [ ] **Step 3: 实现**

`api/schemas.py` 追加：

```python
class CopilotDispatchRequest(BaseModel):
    message: str = ""
    symbol: str | None = None


class CopilotDispatchReply(BaseModel):
    """意图分发结果：命中流水线回 card/preview，否则 chat_fallback 走 /agent/chat。"""

    intent: str
    symbol: str | None = None
    card: dict | None = None        # {card_type, data}
    preview: TradePreviewDTO | None = None
    chat_fallback: bool = False
    note_cn: str = ""
```

`api/routes/copilot.py` 追加（imports 补 `CopilotDispatchReply, CopilotDispatchRequest` 与 `parse_intent, parse_trade_report`）：

```python
@router.post("/copilot/dispatch", response_model=CopilotDispatchReply)
def dispatch(request: Request, body: CopilotDispatchRequest) -> CopilotDispatchReply:
    """一句话入口：规则识别意图 → 直达流水线（零 LLM）；识别不到回落通用讨论。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot.intent import parse_intent, parse_trade_report  # noqa: PLC0415

    intent = parse_intent(body.message)
    note = ""
    if intent.kind == "recommend":
        card = _recommend_card(request)
        with closing(connect(_db_path(request))) as conn:
            if card.items:
                journal.save_recommendation(conn, card)
                conn.commit()
        return CopilotDispatchReply(
            intent="recommend", card={"card_type": "recommend", "data": card.model_dump()},
            note_cn="推荐为排序结果，不构成新判定；点击标的可看买点审阅。",
        )
    if intent.kind == "trade_report":
        preview = parse_trade_report(body.message, today=today_date())
        return CopilotDispatchReply(
            intent="trade_report", preview=preview,
            note_cn="已按你的话抽出信息，请核对后确认记入台账。",
        )
    if intent.kind == "holdings":
        with closing(connect(_db_path(request))) as conn:
            plans = [
                {"plan_id": p.plan_id, "symbol": p.symbol, "state": p.state,
                 "module": p.module, "direction": p.direction,
                 "valid_until": p.valid_until}
                for p in list_plans(conn)
                if p.state in ("armed", "entered")
            ]
        data = {
            "active_plans": plans,
            "fund_positions": [],
            "hint_cn": "基金持仓与真实盈亏在基金台账（P2）接入后在此展示；"
                       "明细见「我的持仓」页。",
        }
        return CopilotDispatchReply(
            intent="holdings",
            card={"card_type": "holdings", "data": data},
        )
    if intent.kind == "review":
        return CopilotDispatchReply(
            intent="review", chat_fallback=True,
            note_cn="复盘流水线在 P3 接入；当前先用通用讨论回答。",
        )
    return CopilotDispatchReply(
        intent="chat", symbol=body.symbol, chat_fallback=True,
        note_cn="未命中快捷指令，已转通用讨论。",
    )
```

（`list_plans` 从 `lei_signal.plans.store` 导入，加到文件顶部 import 区。）

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_dispatch.py -q`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/api/schemas.py src/lei_signal/api/routes/copilot.py tests/unit/test_copilot_dispatch.py
git commit -m "feat(copilot): POST /api/copilot/dispatch——意图分发端点（零LLM直达流水线）"
```

### Task 8: 推荐讲解端点（GLM 一次调用 + 接地 + 降级）

**Files:**
- Modify: `src/lei_signal/api/routes/copilot.py`（追加 explain 端点）
- Test: `tests/unit/test_copilot_explain.py`

**Interfaces:**
- Consumes: Task 1 `chat_copilot`/`COPILOT_SYSTEM_PROMPT`/`load_ark_config`；Task 4 `_recommend_card`；`plans/grounding.py` 的 `verify_grounding`/`verify_numeric_grounding`/`collect_payload_numbers`。
- Produces: `POST /api/copilot/recommend/explain {question?} -> {reply: str, grounded: bool, card: RecommendCardDTO}`。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_explain.py
"""推荐讲解：GLM 接地通过 / 禁用词降级 / 编数值降级 / 无凭据模板直出。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.plans import llm as plans_llm


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = str(tmp_path / "t.db")
    a.state.watchlist_db_path = a.state.plans_db_path
    a.include_router(copilot_routes.router)
    return a


def _with_llm(app, monkeypatch, reply_text):
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        plans_llm, "load_ark_config", lambda: plans_llm.ArkConfig(api_key="k")
    )
    monkeypatch.setattr(
        copilot_routes.plans_llm, "chat_copilot",
        lambda payload, message, config, *, system_prompt: reply_text,
    )
    # 路由内部经模块属性调用（agent.py 同款 monkeypatch 点）
    return TestClient(app)


def test_no_credentials_template(app):
    r = TestClient(app).post("/api/copilot/recommend/explain", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is False
    assert "排序仅影响展示顺序" in body["reply"]


def test_grounded_llm_reply_passes(app, monkeypatch):
    client = _with_llm(
        app, monkeypatch,
        "今日自选里值得先看的是通信ETF，条件仍在等待成立；排序仅影响展示顺序，不构成新判定。",
    )
    body = client.post("/api/copilot/recommend/explain", json={}).json()
    assert body["grounded"] is True


def test_banned_word_degrades(app, monkeypatch):
    client = _with_llm(app, monkeypatch, "建议买入515880。")
    body = client.post("/api/copilot/recommend/explain", json={}).json()
    assert body["grounded"] is False
    assert "排序仅影响展示顺序" in body["reply"]


def test_fabricated_number_degrades(app, monkeypatch):
    client = _with_llm(app, monkeypatch, "515880 今天涨了 88.8%，排序仅影响展示顺序。")
    body = client.post("/api/copilot/recommend/explain", json={}).json()
    assert body["grounded"] is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_explain.py -q`
Expected: FAIL（端点不存在）

- [ ] **Step 3: 实现（copilot.py 追加）**

```python
_EXPLAIN_DEFAULT_Q = "请概括今日推荐：先看什么、为什么、还缺什么条件。"

_EXPLAIN_TEMPLATE = (
    "【今日推荐·数据直出】{run_date}\n"
    "{items}"
    "{sectors}"
    "排序仅影响展示顺序，不构成新判定；技术结论以各标的买点审阅为准。"
)


def _explain_template(card: RecommendCardDTO) -> str:
    lines = [
        f"· {i.display_name}（{i.symbol}）[{i.verdict_cn}] "
        + "；".join(i.reasons[:3])
        for i in card.items
    ]
    sectors = [f"· {s.name}（{s.stage_cn}）" for s in card.sectors]
    return _EXPLAIN_TEMPLATE.format(
        run_date=card.run_date,
        items="\n".join(lines) + ("\n" if lines else "今日无上榜标的。\n"),
        sectors=("板块：" + "、".join(sectors) + "\n") if sectors else "",
    )


class ExplainRequest(BaseModel):
    question: str = ""


class ExplainReply(BaseModel):
    reply: str
    grounded: bool
    card: RecommendCardDTO


@router.post("/copilot/recommend/explain", response_model=ExplainReply)
def explain_recommend(request: Request, body: ExplainRequest) -> ExplainReply:
    """推荐讲解：一次 GLM 调用；数值/禁用词接地，失败降级模板直出。"""
    card = _recommend_card(request)
    config = plans_llm.load_ark_config()
    reply: str | None = None
    grounded = False
    if config is not None:
        payload = card.model_dump()
        allowed_nums = collect_payload_numbers(payload)
        raw = plans_llm.chat_copilot(
            payload,
            body.question.strip() or _EXPLAIN_DEFAULT_Q,
            config,
            system_prompt=plans_llm.COPILOT_SYSTEM_PROMPT,
        )
        if raw is not None:
            ok_num, _ = verify_numeric_grounding(raw, allowed_nums)
            ok_txt, _ = verify_grounding(raw, {""})  # 白名单空 = 只查禁用词
            if ok_num and ok_txt:
                reply, grounded = raw, True
            else:
                logger.warning("推荐讲解接地未过，降级模板")
    if reply is None:
        reply, grounded = _explain_template(card), False
    return ExplainReply(reply=reply, grounded=grounded, card=card)
```

imports 补：`from pydantic import BaseModel`（文件顶部如无）、`from lei_signal.plans import llm as plans_llm`、`from lei_signal.plans.grounding import collect_payload_numbers, verify_grounding, verify_numeric_grounding`。注意测试 monkeypatch 的是 `copilot_routes.plans_llm.chat_copilot` 与 `copilot_routes.plans_llm.load_ark_config`，因此路由内**必须**经 `plans_llm.` 模块属性调用（agent.py 同款约定）。

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_explain.py -q`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/api/routes/copilot.py tests/unit/test_copilot_explain.py
git commit -m "feat(copilot): 推荐讲解端点——GLM单次调用+数值与禁用词接地+模板降级"
```

### Task 9: 前端 types + api client

**Files:**
- Modify: `web/src/types.ts`（文件尾追加）
- Modify: `web/src/api/client.ts`（`export const api = {` 对象内追加方法）

**Interfaces:**
- Produces（前端全局用，Task 10/14/17/22/23 消费）:

```ts
// ---- Copilot（Agent 超级入口） ----
export interface RecommendItem {
  symbol: string;
  display_name: string;
  verdict: string;
  verdict_cn: string;
  best_scenario_cn: string | null;
  reward_risk_ratio: number | null;
  reward_risk_computable: boolean;
  news_heat: number;
  news_tags: string[];
  score: number;
  reasons: string[];
}
export interface SectorPick {
  code: string; name: string; stage: string; stage_cn: string; note: string;
}
export interface RecommendCard {
  run_date: string;
  generated_at: string;
  items: RecommendItem[];
  sectors: SectorPick[];
  sentiment_status: string;
  fundamental_note: string;
  disclaimer_cn: string;
}
export interface SizingAdvice {
  symbol: string; tier: string; tier_pct_cn: string; cap_pct: number;
  reasons: string[]; strength: string; strength_cn: string; disclaimer_cn: string;
}
export interface TradePreview {
  fund_code: string | null; fund_name: string | null;
  side: "buy" | "sell"; side_cn: string;
  amount: number | null; trade_date: string;
  missing: string[]; note_cn: string;
}
export interface FundTrade {
  trade_id: string; fund_code: string; fund_name: string;
  side: "buy" | "sell"; side_cn: string;
  amount: number; trade_date: string;
  priced_nav: number | null;
  price_status: "pending" | "priced" | "failed"; price_status_cn: string;
  plan_id: string | null; source: string; note: string; created_at: string;
}
export interface FundPosition {
  fund_code: string; fund_name: string;
  shares: number; cost: number;
  latest_nav: number | null; latest_nav_date: string;
  market_value: number | null; unrealized_pnl: number | null;
  realized_pnl: number; note: string;
}
export interface CopilotDispatchReply {
  intent: string; symbol: string | null;
  card: { card_type: string; data: unknown } | null;
  preview: TradePreview | null;
  chat_fallback: boolean; note_cn: string;
}
export interface ExplainReply { reply: string; grounded: boolean; card: RecommendCard; }
export interface ReviewSection { heading_cn: string; lines: string[]; }
export interface ReviewCard {
  review_id: string; kind: "trade" | "weekly"; ref_key: string; title_cn: string;
  sections: ReviewSection[];
  r_multiple: number | null; realized_pnl: number | null;
  narrative: string; grounded: boolean;
}
export interface OpsTodo {
  action_id: string; plan_id: string; symbol: string;
  kind: string; kind_cn: string; next_step_cn: string;
  due_from: string; nag_count: number;
}
export interface OpsLine { symbol: string; display_name: string; text_cn: string; }
export interface OpsCard {
  run_date: string; generated_at: string;
  holdings_actions: OpsLine[];
  recommendations: RecommendCard | null;
  plan_todos: OpsTodo[];
  watch_triggers: OpsLine[];
  push_summary_cn: string;
}
```

client.ts（`api` 对象内追加；`request` 泛型与既有方法一致）：

```ts
  // ---- Copilot（Agent 超级入口） ----
  copilotDispatch: (body: { message: string; symbol?: string | null }) =>
    request<CopilotDispatchReply>(`/copilot/dispatch`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  copilotRecommend: () => request<RecommendCard>(`/copilot/recommend`),
  copilotRecommendExplain: (question: string) =>
    request<ExplainReply>(`/copilot/recommend/explain`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  copilotPositionAdvice: (symbol: string) =>
    request<SizingAdvice>(`/copilot/position-advice/${encodeURIComponent(symbol)}`),
  copilotTradesPreview: (message: string) =>
    request<TradePreview>(`/copilot/trades/preview`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  copilotTradesCreate: (t: {
    fund_code: string; fund_name: string; side: "buy" | "sell";
    amount: number; trade_date: string; note?: string;
  }) =>
    request<FundTrade>(`/copilot/trades`, {
      method: "POST",
      body: JSON.stringify(t),
    }),
  copilotTrades: () => request<{ trades: FundTrade[]; positions: FundPosition[] }>(`/copilot/trades`),
  copilotReviewTrade: (tradeId: string) =>
    request<ReviewCard>(`/copilot/review/trade/${encodeURIComponent(tradeId)}`),
  copilotReviewWeekly: (week?: string) =>
    request<ReviewCard>(`/copilot/review/weekly${week ? `?week=${week}` : ""}`),
  opsToday: () => request<OpsCard>(`/ops/today`),
```

（顶部 import type 一并补齐这些新类型名。）

- [ ] **Step 1: 追加 types.ts 与 client.ts 内容（按上方代码原样）**
- [ ] **Step 2: 构建验证**

Run: `cd web && npm run build`
Expected: tsc 无错误（未使用类型报错不存在——verbatimModuleSyntax 下仅 import type）

- [ ] **Step 3: 提交**

```bash
git add web/src/types.ts web/src/api/client.ts
git commit -m "feat(copilot-web): 前端类型与API client——dispatch/推荐/档位/台账/复盘/清单"
```

### Task 10: AgentConsole 快捷指令 + 卡片回合（前端 P1 核心）

**Files:**
- Create: `web/src/components/copilot/CopilotCards.tsx`
- Modify: `web/src/components/AgentConsole.tsx`
- Modify: `web/src/styles.css`（追加少量类）

**Interfaces:**
- Consumes: Task 9 client 方法；`AgentMarkdown`、`useAgentConsole` 既有导出；路由跳转 `useNavigate`。
- Produces: `Turn` 扩展 `{ who; text; grounded?; trace?; card? }`；`CopilotCards.tsx` 导出 `RecommendCardView`、`TradeConfirmCard`、`HoldingsCardView`、`ReviewCardView`（Task 14/17 复用 ReviewCardView）。

- [ ] **Step 1: 新建 `web/src/components/copilot/CopilotCards.tsx`（完整文件）**

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type {
  FundTrade, RecommendCard, ReviewCard, SizingAdvice, TradePreview,
} from "../../types";

/** 推荐卡：前5标的+前3板块，symbol 可点击跳详情；「让AI讲讲」按需一次调用。 */
export function RecommendCardView({ card }: { card: RecommendCard }) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const explain = useMutation({
    mutationFn: () => api.copilotRecommendExplain(""),
    onSuccess: (r) => setNarrative(r.reply),
  });
  return (
    <div className="cp-card">
      <div className="cp-label">
        今日推荐 · {card.run_date}（排序仅影响展示，不构成新判定）
      </div>
      {card.items.length === 0 && <div className="muted">今日无上榜标的。</div>}
      {card.items.map((it) => (
        <div key={it.symbol} className="cp-row">
          <Link to={`/symbol/${it.symbol}`} className="cp-sym">
            {it.display_name}
          </Link>
          <span className={`badge v-${it.verdict}`}>{it.verdict_cn}</span>
          <span className="muted">{it.reasons.slice(0, 3).join("；")}</span>
        </div>
      ))}
      {card.sectors.length > 0 && (
        <div className="cp-row">
          板块：
          {card.sectors.map((s) => (
            <span key={s.code} className="cp-chip">
              {s.name}·{s.stage_cn}
            </span>
          ))}
        </div>
      )}
      <div className="muted" style={{ fontSize: 11 }}>{card.disclaimer_cn}</div>
      {narrative && (
        <div className="cp-narrative">
          <span className="muted">AI讲解：</span>
          {narrative}
        </div>
      )}
      <button
        className="btn small"
        disabled={explain.isPending || !!narrative}
        onClick={() => explain.mutate()}
      >
        {explain.isPending ? "生成中…" : narrative ? "已讲解" : "让AI讲讲"}
      </button>
    </div>
  );
}

/** 报单确认卡：字段可改，确认后才落库（设计定稿 D1 红线）。 */
export function TradeConfirmCard({ preview }: { preview: TradePreview }) {
  const qc = useQueryClient();
  const [code, setCode] = useState(preview.fund_code ?? "");
  const [name, setName] = useState(preview.fund_name ?? "");
  const [amount, setAmount] = useState(
    preview.amount != null ? String(preview.amount) : "",
  );
  const [date, setDate] = useState(preview.trade_date);
  const create = useMutation({
    mutationFn: () =>
      api.copilotTradesCreate({
        fund_code: code.trim(),
        fund_name: name.trim() || code.trim(),
        side: preview.side,
        amount: Number(amount),
        trade_date: date,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["copilotTrades"] });
      qc.invalidateQueries({ queryKey: ["opsToday"] });
    },
  });
  const missingHint = preview.missing.length
    ? `待补：${preview.missing.join("、")}`
    : "信息已抽全，请核对";
  return (
    <div className="cp-card">
      <div className="cp-label">报单确认（{preview.side_cn}）· 确认后记入基金台账</div>
      <div className="muted" style={{ fontSize: 11 }}>
        {missingHint}。金额单位为元；定价按报单日基金净值（ETF按单位净值）。
      </div>
      <div className="cp-form">
        <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="基金代码（6位）" />
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="基金名称" />
        <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="金额（元）" />
        <input value={date} onChange={(e) => setDate(e.target.value)} placeholder="日期 YYYY-MM-DD" />
      </div>
      <button
        className="btn small primary"
        disabled={
          create.isPending ||
          create.isSuccess ||
          !/^\d{6}$/.test(code.trim()) ||
          !(Number(amount) > 0) ||
          !/^\d{4}-\d{2}-\d{2}$/.test(date)
        }
        onClick={() => create.mutate()}
      >
        {create.isPending ? "记账中…" : create.isSuccess ? "已记账" : "确认记账"}
      </button>
      {create.error && (
        <div className="cp-error">
          {create.error instanceof Error ? create.error.message : String(create.error)}
        </div>
      )}
    </div>
  );
}

/** 持仓速览卡（P1 计划口径；P2 后带基金持仓与真实盈亏）。 */
export function HoldingsCardView({
  data,
}: {
  data: { active_plans: Array<{ plan_id: string; symbol: string; state: string; valid_until: string }>; fund_positions: unknown[]; hint_cn: string };
}) {
  return (
    <div className="cp-card">
      <div className="cp-label">持仓速览</div>
      {data.active_plans.map((p) => (
        <div key={p.plan_id} className="cp-row">
          <Link to={`/symbol/${p.symbol}`} className="cp-sym">{p.symbol}</Link>
          <span className="muted">
            计划 {p.state} · 有效期至 {p.valid_until}
          </span>
        </div>
      ))}
      {data.active_plans.length === 0 && <div className="muted">暂无进行中的计划。</div>}
      <div className="muted" style={{ fontSize: 11 }}>{data.hint_cn}</div>
      <Link to="/portfolio" className="cp-link">去「我的持仓」页</Link>
    </div>
  );
}

/** 复盘卡（单笔/周报共用，P3 接线）。 */
export function ReviewCardView({ review }: { review: ReviewCard }) {
  return (
    <div className="cp-card">
      <div className="cp-label">{review.title_cn}</div>
      {review.sections.map((s) => (
        <div key={s.heading_cn} className="cp-section">
          <div className="cp-sub">{s.heading_cn}</div>
          {s.lines.map((l, i) => (
            <div key={i} style={{ fontSize: 12 }}>{l}</div>
          ))}
        </div>
      ))}
      {review.r_multiple != null && (
        <div style={{ fontSize: 12 }}>
          R 倍数：{review.r_multiple.toFixed(2)}（当初准备亏的钱为1份，结果赚了几个1份）
        </div>
      )}
      {review.narrative && (
        <div className="cp-narrative">
          <span className="muted">AI复盘：</span>
          {review.narrative}
        </div>
      )}
    </div>
  );
}

/** 仓位档位卡（供推荐卡与档位端点共用展示）。 */
export function SizingAdviceView({ advice }: { advice: SizingAdvice }) {
  return (
    <div className="cp-card">
      <div className="cp-label">
        仓位建议 · {advice.tier}档 {advice.tier_pct_cn}
      </div>
      {advice.reasons.map((r, i) => (
        <div key={i} style={{ fontSize: 12 }}>· {r}</div>
      ))}
      <div className="muted" style={{ fontSize: 11 }}>
        {advice.strength_cn}；{advice.disclaimer_cn}
      </div>
    </div>
  );
}

/** 卡片分发（对话流内按 card_type 渲染）。 */
export function CopilotCardDispatcher({
  card,
  preview,
}: {
  card: { card_type: string; data: unknown } | null;
  preview: TradePreview | null;
}) {
  if (preview) return <TradeConfirmCard preview={preview} />;
  if (!card) return null;
  if (card.card_type === "recommend")
    return <RecommendCardView card={card.data as RecommendCard} />;
  if (card.card_type === "holdings")
    return (
      <HoldingsCardView
        data={card.data as Parameters<typeof HoldingsCardView>[0]["data"]}
      />
    );
  if (card.card_type === "review")
    return <ReviewCardView review={card.data as ReviewCard} />;
  return null;
}

export type { FundTrade };
```

- [ ] **Step 2: 改 AgentConsole.tsx（三处小改，不动既有 PlanDraft 体系）**

1) `Turn` 类型与 chips 常量替换：

```ts
type Turn = {
  who: "you" | "agent";
  text: string;
  grounded?: boolean;
  trace?: TraceItem[];
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
};

const SYMBOL_CHIPS = ["这个买点为什么是买点", "技术面讨论", "给这个买点建计划", "这个标的我的计划"];
const GLOBAL_CHIPS = ["今天看什么", "持仓速览", "我要报单", "本周复盘"];
```

2) 新增 dispatch 优先的发送逻辑（放在 `ask` mutation 之后）：

```ts
  const dispatch = useMutation({
    mutationFn: (message: string) =>
      api.copilotDispatch({ message, symbol: symbol ?? undefined }),
    onSuccess: (reply, message) => {
      setTurns((cur) => [
        ...cur,
        { who: "you", text: message },
        {
          who: "agent",
          text: reply.note_cn,
          card: reply.card,
          preview: reply.preview,
          grounded: true,
        },
      ]);
      if (reply.chat_fallback) ask.mutate({ message, symbol, sessionId, epoch: epochRef.current });
    },
    onError: (_e, message) => {
      ask.mutate({ message, symbol, sessionId, epoch: epochRef.current });
    },
  });
```

`send()`（若原文件为 `const send = (text: string) => {...}` 则改其内部；否则把输入框 onClick/onKeyDown 的 `send(input)` 调用替换为 `dispatchAndSend(input)`）：

```ts
  const dispatchAndSend = (raw: string) => {
    const message = raw.trim();
    if (!message) return;
    setInput("");
    dispatch.mutate(message);
  };
```

3) 对话渲染分支：turns.map 里 agent 回合追加 `{t.card || t.preview ? <CopilotCardDispatcher card={t.card ?? null} preview={t.preview ?? null} /> : null}`；顶部 chips 点击改为 `dispatchAndSend(label)`（SYMBOL_CHIPS 保持走 `ask`，因为标的问题走通用讨论）；header 加「展开成工作台」链接：

```tsx
<Link to="/agent" className="cp-link" onClick={closeConsole}>展开成工作台</Link>
```

import 补：`import { Link } from "react-router-dom";`、`import { CopilotCardDispatcher } from "./copilot/CopilotCards";`、`import type { TradePreview } from "../types";`。

- [ ] **Step 3: styles.css 追加**

```css
/* ---- Copilot 卡片 ---- */
.cp-card { border: 1px solid var(--border, #d8d8d8); border-radius: 10px;
  padding: 10px 12px; margin: 8px 0; display: flex; flex-direction: column; gap: 6px;
  background: var(--panel, #fafafa); }
.cp-label { font-weight: 600; font-size: 12px; }
.cp-row { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; font-size: 12px; }
.cp-sym { font-weight: 600; color: inherit; }
.cp-chip { border: 1px solid #ccc; border-radius: 999px; padding: 0 8px; font-size: 11px; }
.cp-form { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.cp-form input { font-size: 12px; padding: 4px 6px; }
.cp-narrative { border-left: 3px solid #bbb; padding-left: 8px; font-size: 12px; }
.cp-section { margin: 4px 0; }
.cp-sub { font-weight: 600; font-size: 12px; margin-bottom: 2px; }
.cp-link { font-size: 12px; }
.cp-error { color: #b00; font-size: 12px; }
```

- [ ] **Step 4: 构建验证**

Run: `cd web && npm run build`
Expected: tsc 通过

- [ ] **Step 5: 提交**

```bash
git add web/src/components/copilot/CopilotCards.tsx web/src/components/AgentConsole.tsx web/src/styles.css
git commit -m "feat(copilot-web): AgentConsole快捷指令+dispatch优先+确认卡/推荐卡/速览卡渲染"
```

### Task 11: GLM 密钥环境接线

**Files:**
- Modify: `.env.example`（追加说明行；真实密钥**只**写 `.env`，gitignored）
- Modify: `.env`（本机私有，不 add 不提交——只写入内容）

- [ ] **Step 1: `.env.example` 追加**

```bash
# Agent 超级入口表达层 LLM（GLM，OpenAI 兼容）。优先级 GLM > DeepSeek > ARK。
# GLM_API_KEY=（真实密钥只写在 .env，绝不提交）
# GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
# GLM_MODEL=glm-4.6
```

- [ ] **Step 2: 写入本机 `.env`（密钥来自用户 2026-09-05 提供）**

```bash
grep -q '^GLM_API_KEY=' .env 2>/dev/null || printf '\nGLM_API_KEY=d8cce5d726f44966bb86ae5736216541.rT6F2NCioI9ZZCLO\n' >> .env
grep -q '^GLM_MODEL=' .env 2>/dev/null || printf 'GLM_MODEL=glm-4.6\n' >> .env
git check-ignore .env && echo "OK: .env 已被 git 忽略"
```

Expected: `OK: .env 已被 git 忽略`（若无输出则停下修 .gitignore，不许继续）

- [ ] **Step 3: 验证后端能拿到配置**

Run: `PYTHONPATH=src GLM_API_KEY=$(grep '^GLM_API_KEY=' .env | cut -d= -f2) python -c "from lei_signal.plans.llm import load_ark_config; c=load_ark_config(); assert c and c.model=='glm-4.6'; print('GLM config OK:', c.base_url, c.model)"`
Expected: `GLM config OK: https://open.bigmodel.cn/api/paas/v4 glm-4.6`

- [ ] **Step 4: 提交（只提交 .env.example）**

```bash
git add .env.example
git commit -m "docs(copilot): .env.example登记GLM表达层供应商配置项"
```

---

# P2 · 基金交易台账 + 真实盈亏

### Task 12: 台账核心 trades.py（定价 + 盈亏纯逻辑）

**Files:**
- Create: `src/lei_signal/copilot/trades.py`
- Modify: `src/lei_signal/api/schemas.py`（追加 `FundTradeDTO`/`FundPositionDTO`/`TradesResponseDTO`）
- Test: `tests/unit/test_copilot_trades.py`

**Interfaces:**
- Consumes: `lei_signal.portfolio.funddata.fetch_nav_history(code, page_size=40) -> list[NavPoint(date, unit_nav)]`（最新在前）。
- Produces:
  - `create_trade(conn, *, fund_code, fund_name, side, amount, trade_date, plan_id=None, source="web", note="") -> FundTradeDTO`
  - `price_pending_trades(conn, *, fetch_nav=fetch_nav_history) -> int`（补定价，返回定价成功数）
  - `list_trades(conn, fund_code: str | None = None) -> list[FundTradeDTO]`
  - `position_summary(conn, *, fetch_nav=fetch_nav_history) -> list[FundPositionDTO]`（每基金：份额=Σ金额/定价净值；卖出按均价成本结转；浮动盈亏=份额×最新净值−剩余成本）
  - `realized_pnl_of(conn, trade_id) -> dict`（Task 15 复用：realized_pnl / shares_sold / avg_cost / priced_nav）

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_trades.py
"""基金台账：创建/定价/盈亏三件套。fetch_nav 全部注入假数据，不打网络。"""
from __future__ import annotations

import pytest

from lei_signal.copilot import trades
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _nav(*points: tuple[str, float]):
    def fetch(code, page_size=40):
        return [NavPoint(date=d, unit_nav=v) for d, v in points]
    return fetch


def test_create_trade_pending(conn):
    t = trades.create_trade(conn, fund_code="012414", fund_name="测试基金",
                            side="buy", amount=10000.0, trade_date="2026-09-04")
    assert t.price_status == "pending" and t.priced_nav is None


def test_price_pending_uses_nav_on_or_before_date(conn):
    trades.create_trade(conn, fund_code="012414", fund_name="测试",
                        side="buy", amount=10000.0, trade_date="2026-09-04")
    n = trades.price_pending_trades(
        conn, fetch_nav=_nav(("2026-09-05", 1.25), ("2026-09-04", 1.20), ("2026-09-03", 1.18))
    )
    assert n == 1
    rows = trades.list_trades(conn)
    assert rows[0].priced_nav == pytest.approx(1.20)
    assert rows[0].price_status == "priced"


def test_price_pending_qdii_missing_day_falls_back_latest(conn):
    """QDII T+1：当日净值未发布时用 ≤ 日期的最近净值（与 nav_update 口径一致）。"""
    trades.create_trade(conn, fund_code="270042", fund_name="QDII",
                        side="buy", amount=5000.0, trade_date="2026-09-05")
    trades.price_pending_trades(conn, fetch_nav=_nav(("2026-09-03", 2.00)))
    rows = trades.list_trades(conn)
    assert rows[0].priced_nav == pytest.approx(2.00)


def test_price_pending_no_nav_marks_failed(conn):
    trades.create_trade(conn, fund_code="000000", fund_name="无数据",
                        side="buy", amount=1000.0, trade_date="2026-09-05")
    n = trades.price_pending_trades(conn, fetch_nav=lambda code, page_size=40: [])
    assert n == 0
    assert trades.list_trades(conn)[0].price_status == "pending"  # 留 pending 次日再试


def test_position_summary_buy_sell_realized(conn):
    # 买 10000 @1.00 -> 份额10000；卖 5000 @1.25 -> 份额4000，实现 5000-5000*1.0=0
    trades.create_trade(conn, fund_code="012414", fund_name="T", side="buy",
                        amount=10000.0, trade_date="2026-09-01")
    trades.create_trade(conn, fund_code="012414", fund_name="T", side="sell",
                        amount=5000.0, trade_date="2026-09-10")
    trades.price_pending_trades(conn, fetch_nav=_nav(
        ("2026-09-10", 1.25), ("2026-09-01", 1.00)))
    pos = trades.position_summary(conn, fetch_nav=_nav(("2026-09-10", 1.25)))
    assert len(pos) == 1
    p = pos[0]
    assert p.shares == pytest.approx(10000.0 - 4000.0)
    assert p.realized_pnl == pytest.approx(5000.0 - 4000.0 * 1.00)  # 卖价-均价成本
    assert p.market_value == pytest.approx(6000.0 * 1.25)


def test_realized_pnl_of(conn):
    trades.create_trade(conn, fund_code="012414", fund_name="T", side="buy",
                        amount=10000.0, trade_date="2026-09-01")
    sell = trades.create_trade(conn, fund_code="012414", fund_name="T", side="sell",
                               amount=5000.0, trade_date="2026-09-10")
    trades.price_pending_trades(conn, fetch_nav=_nav(
        ("2026-09-10", 1.25), ("2026-09-01", 1.00)))
    info = trades.realized_pnl_of(conn, sell.trade_id)
    assert info["priced_nav"] == pytest.approx(1.25)
    assert info["realized_pnl"] == pytest.approx(1000.0)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_trades.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

`api/schemas.py` 追加：

```python
class FundTradeDTO(BaseModel):
    """基金成交台账一行（手动报单，用户确认落库；不接券商）。"""

    trade_id: str
    fund_code: str
    fund_name: str
    side: str
    side_cn: str
    amount: float
    trade_date: str
    priced_nav: float | None
    price_status: str          # pending | priced | failed
    price_status_cn: str
    plan_id: str | None = None
    source: str = "web"
    note: str = ""
    created_at: str = ""


class FundPositionDTO(BaseModel):
    """单基金持仓汇总（份额/成本/最新净值/浮盈/已实现）。"""

    fund_code: str
    fund_name: str
    shares: float
    cost: float                     # 剩余成本（元）
    latest_nav: float | None
    latest_nav_date: str = ""
    market_value: float | None      # shares × latest_nav（无净值则 None）
    unrealized_pnl: float | None
    realized_pnl: float = 0.0
    note: str = ""


class TradesResponseDTO(BaseModel):
    trades: list[FundTradeDTO] = []
    positions: list[FundPositionDTO] = []
```

`src/lei_signal/copilot/trades.py`：

```python
"""基金成交台账：手动报单 → 净值定价 → 份额/盈亏核算。

口径（设计定稿 D1，2026-09-05 用户拍板）：
- 只做基金（场外与 ETF 统一按天天基金「单位净值」定价；ETF 的折溢价差异
  在 disclaimer 里说明，不引入第二条行情数据链路）。
- 报单默认收盘口径：找 ≤ trade_date 的最近一个净值日（QDII T+1 缺日属正常）。
- 份额 = 金额 ÷ 定价净值；买入累成本，卖出按持仓均价结转；
  已实现盈亏 = 卖出金额 −（均价成本 × 卖出份额）。
- 无净值可依时保持 pending，跑批次日补（不猜数）。
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from typing import Callable

from lei_signal.api.schemas import FundPositionDTO, FundTradeDTO
from lei_signal.portfolio.funddata import NavPoint, fetch_nav_history

NavFetcher = Callable[[str], list[NavPoint]]

_STATUS_CN = {"pending": "待定价", "priced": "已定价", "failed": "定价失败"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dto(row: sqlite3.Row) -> FundTradeDTO:
    return FundTradeDTO(
        trade_id=row["trade_id"],
        fund_code=row["fund_code"],
        fund_name=row["fund_name"],
        side=row["side"],
        side_cn="申购" if row["side"] == "buy" else "赎回",
        amount=float(row["amount"]),
        trade_date=row["trade_date"],
        priced_nav=float(row["priced_nav"]) if row["priced_nav"] is not None else None,
        price_status=row["price_status"],
        price_status_cn=_STATUS_CN.get(row["price_status"], row["price_status"]),
        plan_id=row["plan_id"],
        source=row["source"],
        note=row["note"] or "",
        created_at=row["created_at"],
    )


def _nav_on_or_before(navs: list[NavPoint], day: str) -> float | None:
    for p in navs:  # 最新在前：第一个 date <= day 即答案
        if p.date <= day:
            return p.unit_nav
    return None


def create_trade(
    conn: sqlite3.Connection,
    *,
    fund_code: str,
    fund_name: str,
    side: str,
    amount: float,
    trade_date: str,
    plan_id: str | None = None,
    source: str = "web",
    note: str = "",
) -> FundTradeDTO:
    if side not in ("buy", "sell"):
        raise ValueError(f"side 只能是 buy/sell，收到 {side}")
    if amount <= 0:
        raise ValueError("amount 必须为正数（单位：元）")
    created = _now()
    h = hashlib.sha1(f"{fund_code}{side}{amount}{trade_date}{created}".encode()).hexdigest()[:8]
    trade_id = f"ft_{fund_code}_{trade_date}_{h}"
    conn.execute(
        """INSERT INTO fund_trades
           (trade_id, fund_code, fund_name, side, amount, trade_date,
            priced_nav, price_status, plan_id, source, note, created_at, updated_at)
           VALUES (?,?,?,?,?,?,NULL,'pending',?,?,?,?,?)""",
        (trade_id, fund_code, fund_name, side, amount, trade_date,
         plan_id, source, note, created, created),
    )
    row = conn.execute(
        "SELECT * FROM fund_trades WHERE trade_id = ?", (trade_id,)
    ).fetchone()
    return _row_to_dto(row)


def price_pending_trades(
    conn: sqlite3.Connection, *, fetch_nav: NavFetcher = fetch_nav_history
) -> int:
    """补定价所有 pending 成交。无净值数据保持 pending（次日跑批再试），不猜数。"""
    rows = conn.execute(
        "SELECT * FROM fund_trades WHERE price_status = 'pending' ORDER BY trade_date"
    ).fetchall()
    nav_cache: dict[str, list[NavPoint]] = {}
    priced = 0
    for row in rows:
        code = row["fund_code"]
        if code not in nav_cache:
            try:
                nav_cache[code] = fetch_nav(code)
            except Exception:  # noqa: BLE001  网络失败：留 pending 次日再试
                nav_cache[code] = []
        nav = _nav_on_or_before(nav_cache[code], row["trade_date"])
        if nav is None:
            continue
        conn.execute(
            "UPDATE fund_trades SET priced_nav = ?, price_status = 'priced', "
            "updated_at = ? WHERE trade_id = ?",
            (nav, _now(), row["trade_id"]),
        )
        priced += 1
    return priced


def list_trades(
    conn: sqlite3.Connection, fund_code: str | None = None
) -> list[FundTradeDTO]:
    if fund_code:
        rows = conn.execute(
            "SELECT * FROM fund_trades WHERE fund_code = ? ORDER BY trade_date, created_at",
            (fund_code,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM fund_trades ORDER BY trade_date DESC, created_at DESC"
        ).fetchall()
    return [_row_to_dto(r) for r in rows]


def position_summary(
    conn: sqlite3.Connection, *, fetch_nav: NavFetcher = fetch_nav_history
) -> list[FundPositionDTO]:
    """按基金汇总：份额/成本/浮盈/已实现（只按已定价成交计算，pending 不计）。"""
    rows = conn.execute(
        "SELECT * FROM fund_trades WHERE price_status = 'priced' "
        "ORDER BY trade_date, created_at"
    ).fetchall()
    by_code: dict[str, dict] = {}
    for row in rows:
        st = by_code.setdefault(row["fund_code"], {
            "name": row["fund_name"], "shares": 0.0, "cost": 0.0, "realized": 0.0,
        })
        nav = float(row["priced_nav"])
        shares_delta = float(row["amount"]) / nav
        if row["side"] == "buy":
            st["shares"] += shares_delta
            st["cost"] += float(row["amount"])
        else:
            avg = st["cost"] / st["shares"] if st["shares"] > 0 else 0.0
            st["realized"] += float(row["amount"]) - avg * shares_delta
            st["shares"] -= shares_delta
            st["cost"] -= avg * shares_delta
    out: list[FundPositionDTO] = []
    for code, st in sorted(by_code.items()):
        latest: NavPoint | None = None
        try:
            navs = fetch_nav(code)
            latest = navs[0] if navs else None
        except Exception:  # noqa: BLE001
            latest = None
        mv = st["shares"] * latest.unit_nav if latest else None
        out.append(FundPositionDTO(
            fund_code=code,
            fund_name=st["name"],
            shares=st["shares"],
            cost=st["cost"],
            latest_nav=latest.unit_nav if latest else None,
            latest_nav_date=latest.date if latest else "",
            market_value=mv,
            unrealized_pnl=(mv - st["cost"]) if mv is not None else None,
            realized_pnl=st["realized"],
            note="只按已定价成交核算；待定价记录不计入",
        ))
    return out


def realized_pnl_of(conn: sqlite3.Connection, trade_id: str) -> dict:
    """单笔卖出的已实现盈亏明细（复盘用；买入或未定价返回空字段）。"""
    row = conn.execute(
        "SELECT * FROM fund_trades WHERE trade_id = ?", (trade_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"成交不存在: {trade_id}")
    prior = conn.execute(
        "SELECT * FROM fund_trades WHERE fund_code = ? AND price_status='priced' "
        "AND (trade_date < ? OR (trade_date = ? AND created_at <= ?)) "
        "ORDER BY trade_date, created_at",
        (row["fund_code"], row["trade_date"], row["trade_date"], row["created_at"]),
    ).fetchall()
    shares = cost = 0.0
    for r in prior:
        nav = float(r["priced_nav"])
        delta = float(r["amount"]) / nav
        if r["side"] == "buy":
            shares += delta
            cost += float(r["amount"])
        else:
            avg = cost / shares if shares > 0 else 0.0
            shares -= delta
            cost -= avg * delta
    nav = float(row["priced_nav"]) if row["priced_nav"] is not None else None
    if row["side"] != "sell" or nav is None:
        return {"priced_nav": nav, "shares_sold": None, "avg_cost": None,
                "realized_pnl": None}
    shares_sold = float(row["amount"]) / nav
    avg = cost / shares if shares > 0 else 0.0
    return {
        "priced_nav": nav,
        "shares_sold": shares_sold,
        "avg_cost": avg,
        "realized_pnl": float(row["amount"]) - avg * shares_sold,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_trades.py -q`
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/trades.py src/lei_signal/api/schemas.py tests/unit/test_copilot_trades.py
git commit -m "feat(copilot): 基金成交台账——净值定价+份额/已实现/浮动盈亏核算"
```

### Task 13: 台账路由 + 守门测试边界记录 + holdings 卡升级

**Files:**
- Modify: `src/lei_signal/api/routes/copilot.py`（preview/create/list 三端点；dispatch 的 holdings 卡换成真实持仓）
- Modify: `tests/integration/test_acceptance_gates.py`（`test_no_trading_execution_surface_exists` docstring 记录边界变更）
- Modify: `AGENTS.md`（「其他既有约束」追加一条边界记录）
- Test: `tests/unit/test_copilot_trades_routes.py`

**Interfaces:**
- Produces: `POST /api/copilot/trades/preview {message} -> TradePreviewDTO`；`POST /api/copilot/trades {fund_code, fund_name, side, amount, trade_date, note?} -> FundTradeDTO`（**结构化字段直传，绕过文本解析**——确认卡已让人核对过）；`GET /api/copilot/trades -> TradesResponseDTO`。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_trades_routes.py
"""台账路由：预览→确认→列表链路 + 校验拒绝（fetch_nav 注入，不打网络）。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.copilot import trades as trades_mod
from lei_signal.portfolio.funddata import NavPoint


@pytest.fixture()
def app(tmp_path, monkeypatch):
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = str(tmp_path / "t.db")
    a.state.watchlist_db_path = a.state.plans_db_path
    a.include_router(copilot_routes.router)
    def fake_fetch(code, page_size=40):
        return [NavPoint(date="2026-09-05", unit_nav=1.10),
                NavPoint(date="2026-09-04", unit_nav=1.00)]
    monkeypatch.setattr(trades_mod, "fetch_nav_history", fake_fetch)
    return a


def test_preview_then_create_then_list(app):
    client = TestClient(app)
    pv = client.post("/api/copilot/trades/preview",
                     json={"message": "我昨天买了1万012414"}).json()
    assert pv["fund_code"] == "012414" and pv["amount"] == 10000.0
    created = client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "测试基金", "side": "buy",
        "amount": 10000.0, "trade_date": "2026-09-04",
    })
    assert created.status_code == 200
    body = created.json()
    assert body["price_status"] == "priced"      # 创建即尝试定价
    assert body["priced_nav"] == pytest.approx(1.00)
    listed = client.get("/api/copilot/trades").json()
    assert len(listed["trades"]) == 1
    assert listed["positions"][0]["shares"] == pytest.approx(10000.0)


def test_create_rejects_bad_payload(app):
    client = TestClient(app)
    r = client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "x", "side": "hold",
        "amount": 1.0, "trade_date": "2026-09-04",
    })
    assert r.status_code in (400, 422)
    r2 = client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "x", "side": "buy",
        "amount": -5, "trade_date": "2026-09-04",
    })
    assert r2.status_code in (400, 422)


def test_dispatch_holdings_includes_fund_positions(app):
    client = TestClient(app)
    client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "测试基金", "side": "buy",
        "amount": 10000.0, "trade_date": "2026-09-04",
    })
    body = client.post("/api/copilot/dispatch",
                       json={"message": "持仓速览"}).json()
    data = body["card"]["data"]
    assert len(data["fund_positions"]) == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_trades_routes.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

`copilot.py` 追加（imports 补 `TradePreviewDTO, FundTradeDTO, TradesResponseDTO` 与 `from lei_signal.copilot import trades as trades_mod`、`from lei_signal.copilot.intent import parse_trade_report`）：

```python
class TradeCreateRequest(BaseModel):
    fund_code: str
    fund_name: str
    side: str
    amount: float
    trade_date: str
    note: str = ""


class TradePreviewRequest(BaseModel):
    message: str


@router.post("/copilot/trades/preview", response_model=TradePreviewDTO)
def trades_preview(body: TradePreviewRequest) -> TradePreviewDTO:
    """报单预解析 → 确认卡（零 LLM）。解析是 best-effort，落库走 /copilot/trades。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415

    return parse_trade_report(body.message, today=today_date())


@router.post("/copilot/trades", response_model=FundTradeDTO)
def trades_create(request: Request, body: TradeCreateRequest) -> FundTradeDTO:
    """确认卡落库（结构化字段直传）+ 立即尝试定价。"""
    from fastapi import HTTPException  # noqa: PLC0415

    try:
        trade = trades_mod.create_trade(
            connect(_db_path(request)),
            fund_code=body.fund_code.strip(),
            fund_name=body.fund_name.strip() or body.fund_code.strip(),
            side=body.side,
            amount=body.amount,
            trade_date=body.trade_date,
            source="web",
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    conn = connect(_db_path(request))
    trades_mod.price_pending_trades(conn, fetch_nav=trades_mod.fetch_nav_history)
    conn.commit()
    conn.close()
    row = trades_mod.list_trades(connect(_db_path(request)), body.fund_code.strip())
    for t in row:
        if t.trade_id == trade.trade_id:
            return t
    return trade


@router.get("/copilot/trades", response_model=TradesResponseDTO)
def trades_list(request: Request) -> TradesResponseDTO:
    conn = connect(_db_path(request))
    out = TradesResponseDTO(
        trades=trades_mod.list_trades(conn),
        positions=trades_mod.position_summary(
            conn, fetch_nav=trades_mod.fetch_nav_history
        ),
    )
    conn.close()
    return out
```

dispatch 的 holdings 分支把 `"fund_positions": []` 换成：

```python
        with closing(connect(_db_path(request))) as conn:
            fund_positions = [
                p.model_dump() for p in trades_mod.position_summary(
                    conn, fetch_nav=trades_mod.fetch_nav_history
                )
            ]
```

（`data` 里 `fund_positions: fund_positions`，hint_cn 改为「盈亏按报单日净值核算；明细见我的持仓页」。）

**守门测试与文档记录**（边界变更三处留痕）：

1. `tests/integration/test_acceptance_gates.py::test_no_trading_execution_surface_exists` docstring 末尾追加一段：

```python
    """（前略）边界变更记录（2026-09-05 用户拍板，plan-agent-superentry-v1 决策 D1）：
    fund_trades 基金成交台账允许记录金额（用户手动报单+确认落库），仍不接券商、
    不自动下单、个股交易暂缓。禁用符号表本身不放宽——copilot 代码继续不得出现
    任何下单/账户类标识符。"""
```

2. `AGENTS.md`「其他既有约束（提醒）」末尾追加一行：

```markdown
- 基金成交台账（copilot/fund_trades）是 2026-09-05 用户拍板的边界变更：允许记录
  手动报单的基金买卖金额（确认卡确认后落库），仍不接券商、不自动下单、个股暂缓；
  `trade_plans` 计划台账继续不存数量金额。
```

- [ ] **Step 4: 跑测试 + 守门**

Run: `python -m pytest tests/unit/test_copilot_trades_routes.py tests/integration/test_acceptance_gates.py -q`
Expected: 全部 passed（守门测试仍绿）

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/api/routes/copilot.py tests/unit/test_copilot_trades_routes.py tests/integration/test_acceptance_gates.py AGENTS.md
git commit -m "feat(copilot): 台账三端点+确认卡直传落库+守门边界变更留痕"
```

### Task 14: 持仓页基金台账区（前端）

**Files:**
- Modify: `web/src/pages/PortfolioPage.tsx`（追加「基金台账」区块）
- Modify: `web/src/components/copilot/CopilotCards.tsx`（追加 `TradesLedgerView` 导出）

**Interfaces:**
- Consumes: `api.copilotTrades()`；既有 PortfolioPage 的区块样式类。
- Produces: `TradesLedgerView`（含每笔卖出的「复盘」按钮位，Task 17 接线）。

- [ ] **Step 1: CopilotCards.tsx 追加**

```tsx
export function TradesLedgerView() {
  const q = useQuery({
    queryKey: ["copilotTrades"],
    queryFn: () => api.copilotTrades(),
  });
  if (q.isLoading) return <div className="muted">台账加载中…</div>;
  if (q.isError) return <div className="cp-error">台账加载失败</div>;
  const { trades, positions } = q.data ?? { trades: [], positions: [] };
  return (
    <div className="cp-card">
      <div className="cp-label">基金台账（真实成交 · 确认后记账 · 按报单日净值定价）</div>
      {positions.length > 0 && (
        <div className="cp-section">
          <div className="cp-sub">持仓与盈亏</div>
          {positions.map((p) => (
            <div key={p.fund_code} className="cp-row">
              <span className="cp-sym">{p.fund_name}（{p.fund_code}）</span>
              <span className="muted">
                份额 {p.shares.toFixed(2)} · 成本 {p.cost.toFixed(0)} 元
                {p.market_value != null && <> · 现值 {p.market_value.toFixed(0)} 元</>}
                {p.unrealized_pnl != null && (
                  <> · 浮动 {p.unrealized_pnl >= 0 ? "+" : ""}{p.unrealized_pnl.toFixed(0)}</>
                )}
                {p.realized_pnl !== 0 && (
                  <> · 已实现 {p.realized_pnl >= 0 ? "+" : ""}{p.realized_pnl.toFixed(0)} 元</>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="cp-section">
        <div className="cp-sub">成交记录</div>
        {trades.length === 0 && (
          <div className="muted">还没有记录。对 agent 说「我买了1万012414」即可报单。</div>
        )}
        {trades.map((t) => (
          <div key={t.trade_id} className="cp-row">
            <span>{t.trade_date}</span>
            <span className="cp-sym">{t.fund_name}</span>
            <span>{t.side_cn} {t.amount.toFixed(0)} 元</span>
            <span className="muted">
              {t.price_status_cn}
              {t.priced_nav != null && ` @${t.priced_nav.toFixed(4)}`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

（import 顶部补 `useQuery`：`import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";`。）

- [ ] **Step 2: PortfolioPage.tsx 追加区块**（在持仓分组渲染之后、页面尾注之前插入）：

```tsx
<TradesLedgerView />
```

import 补 `import { TradesLedgerView } from "../components/copilot/CopilotCards";`。

- [ ] **Step 3: 构建验证 + 提交**

Run: `cd web && npm run build`

```bash
git add web/src/pages/PortfolioPage.tsx web/src/components/copilot/CopilotCards.tsx
git commit -m "feat(copilot-web): 持仓页基金台账区——真实成交+持仓盈亏速览"
```

---

# P3 · 复盘

### Task 15: 单笔复盘 review.py（纪律面 + 结果面）

**Files:**
- Create: `src/lei_signal/copilot/review.py`
- Modify: `src/lei_signal/api/schemas.py`（追加 `ReviewSectionDTO`/`ReviewCardDTO`）
- Test: `tests/unit/test_copilot_review.py`

**Interfaces:**
- Consumes: Task 12 `realized_pnl_of`/`list_trades`；`plans.store.get_plan`/`list_action_items`；`plans.monitor.evaluate_plan`（只读纪律事实：催办/推迟/修订计数从 SQL 直读，不重跑判定）。
- Produces: `build_trade_review(conn, trade_id) -> ReviewCardDTO | None`；`save_review(conn, review) -> None`（upsert trade_reviews）；`get_review(conn, kind, ref_key) -> ReviewCardDTO | None`。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_review.py
"""单笔复盘：纪律面（预案原文+催办/推迟/复议计数）+ 结果面（盈亏/R倍数）。"""
from __future__ import annotations

import pytest

from lei_signal.copilot import review, trades
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _nav(*p):
    return lambda code, page_size=40: [NavPoint(date=d, unit_nav=v) for d, v in p]


def _seed_trade(conn) -> str:
    t1 = trades.create_trade(conn, fund_code="012414", fund_name="T",
                             side="buy", amount=10000.0, trade_date="2026-09-01")
    t2 = trades.create_trade(conn, fund_code="012414", fund_name="T",
                             side="sell", amount=5000.0, trade_date="2026-09-10")
    trades.price_pending_trades(conn, fetch_nav=_nav(
        ("2026-09-10", 1.25), ("2026-09-01", 1.00)))
    assert t1.price_status != "failed"
    return t2.trade_id


def test_trade_review_without_plan(conn):
    tid = _seed_trade(conn)
    card = review.build_trade_review(conn, tid)
    assert card is not None and card.kind == "trade"
    joined = "\n".join(l for s in card.sections for l in s.lines)
    assert "无关联计划" in joined
    assert card.realized_pnl == pytest.approx(1000.0)


def test_trade_review_with_plan_discipline(conn):
    from lei_signal.plans.store import create_plan_draft, confirm_plan
    tid = _seed_trade(conn)
    trade = trades.list_trades(conn)[0]
    plan = create_plan_draft(conn, symbol="515880", module="A", direction="long",
        entry_rule_id="pullback_watch", reason="测试",
        valid_until="2026-10-01", thesis_cn="冲通信回调",
        invalidation_criteria_cn="跌破结构C点", drawdown_playbook_cn="回踩均线正常",
        take_profit_plan_cn="到前高减半", stop_plan_cn="收盘破失效价退出",
        invalidation_price=0.90, entry_price_ref=1.00)
    confirm_plan(conn, plan.plan_id)
    conn.execute(
        "UPDATE fund_trades SET plan_id = ? WHERE trade_id = ?",
        (plan.plan_id, tid),
    )
    conn.commit()
    card = review.build_trade_review(conn, tid)
    joined = "\n".join(l for s in card.sections for l in s.lines)
    assert "冲通信回调" in joined          # 当初预案原文
    assert card.r_multiple == pytest.approx(
        1000.0 / ((1.00 - 0.90) / 1.00 * 5000.0)
    )  # 风险额 = 金额×|入场-失效|/入场 = 500


def test_review_save_and_get_roundtrip(conn):
    tid = _seed_trade(conn)
    card = review.build_trade_review(conn, tid)
    review.save_review(conn, card)
    got = review.get_review(conn, "trade", tid)
    assert got is not None and got.review_id == card.review_id


def test_review_missing_trade_returns_none(conn):
    assert review.build_trade_review(conn, "ft_x_y_z") is None
```

注意：`create_plan_draft`/`confirm_plan` 的真实签名以 `plans/store.py` 为准——实现本任务前先读该文件；若参数名不同（如五项预案为位置参数或另有必填），**以 store 实际签名为准调整测试夹具**，断言不变。

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_review.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

`api/schemas.py` 追加：

```python
class ReviewSectionDTO(BaseModel):
    heading_cn: str
    lines: list[str] = []


class ReviewCardDTO(BaseModel):
    """复盘卡：纪律面（我照系统做了吗）与结果面（结果怎样）分开陈述。"""

    review_id: str
    kind: str                    # trade | weekly
    ref_key: str
    title_cn: str
    sections: list[ReviewSectionDTO] = []
    r_multiple: float | None = None
    realized_pnl: float | None = None
    narrative: str = ""          # GLM 叙事，空=模板
    grounded: bool = False
```

`src/lei_signal/copilot/review.py`：

```python
"""复盘组装：纪律面与结果面分开（监督员 v2 路线第 5 条的落地）。

纪律面全部直读 plans 库既有事实（预案原文、催办次数、推迟原因、复议记录），
不重跑判定、不做评价；结果面来自基金台账核算。R 倍数 = 实际盈亏 ÷ 初始风险额
（风险额 = 卖出金额 × |参考入场价 − 失效价| ÷ 参考入场价），仅有关联计划且
两价齐备时计算，否则明说不可算。
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import ReviewCardDTO, ReviewSectionDTO
from lei_signal.copilot import trades as trades_mod
from lei_signal.plans.store import get_plan, list_action_items


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _counts(conn: sqlite3.Connection, plan_id: str) -> dict[str, int]:
    def one(sql: str) -> int:
        row = conn.execute(sql, (plan_id,)).fetchone()
        return int(row[0]) if row else 0

    return {
        "nags": one("SELECT COALESCE(SUM(nag_count),0) FROM plan_action_items WHERE plan_id = ?"),
        "defers": one(
            "SELECT COUNT(*) FROM plan_annotations WHERE plan_id = ? AND kind = 'defer_reason'"
        ),
        "revisions": one(
            "SELECT COUNT(*) FROM trade_plan_revisions WHERE plan_id = ? AND revision_no > 0"
        ),
    }


def build_trade_review(
    conn: sqlite3.Connection, trade_id: str
) -> ReviewCardDTO | None:
    rows = trades_mod.list_trades(conn)
    trade = next((t for t in rows if t.trade_id == trade_id), None)
    if trade is None:
        return None
    pnl_info = trades_mod.realized_pnl_of(conn, trade_id)
    sections: list[ReviewSectionDTO] = []

    plan = get_plan(conn, trade.plan_id) if trade.plan_id else None
    if plan is not None:
        c = _counts(conn, plan.plan_id)
        sections.append(ReviewSectionDTO(
            heading_cn="当初怎么说的（纪律面）",
            lines=[
                f"入场理由：{plan.entry_rule_id or '-'}（模块 {plan.module}）",
                f"交易假设：{plan.thesis_cn or '-'}",
                f"失效标准：{plan.invalidation_criteria_cn or '-'}",
                f"建计划时盈亏比参考：{plan.reward_risk_at_plan if plan.reward_risk_at_plan is not None else '当时未算出'}",
                f"催办 {c['nags']} 次、推迟 {c['defers']} 次、修订 {c['revisions']} 次（都是监督留痕）",
            ],
        ))
    else:
        sections.append(ReviewSectionDTO(
            heading_cn="当初怎么说的（纪律面）",
            lines=["无关联计划——这笔是计划外操作，复盘时先问自己为什么没走计划流程。"],
        ))

    result_lines = [
        f"{trade.trade_date} {trade.side_cn} {trade.fund_name}（{trade.fund_code}）"
        f" {trade.amount:.0f} 元",
    ]
    if pnl_info.get("realized_pnl") is not None:
        result_lines.append(
            f"已实现盈亏 {pnl_info['realized_pnl']:+.0f} 元"
            f"（定价净值 {pnl_info['priced_nav']}）"
        )
    else:
        result_lines.append("已实现盈亏：该笔未定价或非卖出，暂不可算（跑批补定价后再看）")
    r_multiple: float | None = None
    if plan is not None and pnl_info.get("realized_pnl") is not None:
        entry = getattr(plan, "entry_price_ref", None)
        inv = getattr(plan, "invalidation_price", None)
        if entry and inv and entry > 0 and entry != inv:
            shares_sold = pnl_info.get("shares_sold") or 0.0
            risk_amount = float(trade.amount) * abs(entry - inv) / entry
            if risk_amount > 0:
                r_multiple = pnl_info["realized_pnl"] / risk_amount
                result_lines.append(
                    f"R 倍数 {r_multiple:.2f}（大白话：当初准备亏的钱为 1 份，"
                    f"这笔结果等于 {r_multiple:.2f} 份）"
                )
    sections.append(ReviewSectionDTO(heading_cn="结果怎么样（结果面）", lines=result_lines))

    return ReviewCardDTO(
        review_id=f"rv_trade_{trade_id}",
        kind="trade",
        ref_key=trade_id,
        title_cn=f"单笔复盘 · {trade.fund_name} {trade.side_cn} {trade.trade_date}",
        sections=sections,
        r_multiple=r_multiple,
        realized_pnl=pnl_info.get("realized_pnl"),
    )


def save_review(conn: sqlite3.Connection, review: ReviewCardDTO) -> None:
    conn.execute(
        """INSERT INTO trade_reviews (review_id, kind, ref_key, payload,
                                      narrative, grounded, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(kind, ref_key) DO UPDATE SET
               payload = excluded.payload,
               narrative = excluded.narrative,
               grounded = excluded.grounded,
               updated_at = excluded.updated_at""",
        (review.review_id, review.kind, review.ref_key, review.model_dump_json(),
         review.narrative, int(review.grounded), _now(), _now()),
    )


def get_review(
    conn: sqlite3.Connection, kind: str, ref_key: str
) -> ReviewCardDTO | None:
    row = conn.execute(
        "SELECT payload FROM trade_reviews WHERE kind = ? AND ref_key = ?",
        (kind, ref_key),
    ).fetchone()
    if row is None:
        return None
    return ReviewCardDTO.model_validate_json(row["payload"])
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_review.py -q`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/review.py src/lei_signal/api/schemas.py tests/unit/test_copilot_review.py
git commit -m "feat(copilot): 单笔复盘——纪律面读监督留痕+结果面R倍数核算"
```

### Task 16: 周复盘 + 叙事生成 + 复盘路由

**Files:**
- Modify: `src/lei_signal/copilot/review.py`（追加 `build_weekly_review`）
- Modify: `src/lei_signal/api/routes/copilot.py`（两个复盘端点 + 叙事生成）
- Test: `tests/unit/test_copilot_review_weekly.py`

**Interfaces:**
- Consumes: Task 15；`plans_llm.chat_copilot`（monkeypatch 点同 agent.py 约定）。
- Produces: `build_weekly_review(conn, week_iso: str) -> ReviewCardDTO`（week_iso 形如 `2026-W36`）；`GET /api/copilot/review/trade/{trade_id}`（首访组装+存库，带 GLM 叙事 best-effort）；`GET /api/copilot/review/weekly?week=`（缺省上一完整 ISO 周）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_review_weekly.py
"""周复盘聚合 + 复盘端点叙事降级。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.copilot import review, trades
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import connect


def _nav(*p):
    return lambda code, page_size=40: [NavPoint(date=d, unit_nav=v) for d, v in p]


@pytest.fixture()
def seeded(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    trades.create_trade(c, fund_code="012414", fund_name="T",
                        side="buy", amount=10000.0, trade_date="2026-08-31")
    trades.create_trade(c, fund_code="012414", fund_name="T",
                        side="sell", amount=5000.0, trade_date="2026-09-02")
    trades.price_pending_trades(c, fetch_nav=_nav(
        ("2026-09-02", 1.25), ("2026-08-31", 1.00)))
    yield c
    c.close()


def test_weekly_groups_trades_in_iso_week(seeded):
    # 2026-09-02 属 ISO 周 2026-W36（2026-08-31 周一起）
    card = review.build_weekly_review(seeded, "2026-W36")
    joined = "\n".join(l for s in card.sections for l in s.lines)
    assert "1" in joined                 # 2 笔成交
    assert card.realized_pnl == pytest.approx(2500.0)


def test_weekly_empty_week_is_honest(seeded):
    card = review.build_weekly_review(seeded, "2026-W01")
    joined = "\n".join(l for s in card.sections for l in s.lines)
    assert "本周没有台账成交" in joined


def test_review_endpoint_template_without_llm(seeded, monkeypatch, tmp_path):
    for name in ("GLM_API_KEY", "DEEPSEEK_API_KEY", "ARK_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = seeded and str(tmp_path / "t.db")
    # 直接复用已 seed 的库路径：重新指向同一文件
    a.state.plans_db_path = "file:unused"
    seeded.close()
    import shutil
    shutil.copy(str(tmp_path / "t.db"), str(tmp_path / "t2.db"))
    a.state.plans_db_path = str(tmp_path / "t2.db")
    a.state.watchlist_db_path = a.state.plans_db_path
    a.include_router(copilot_routes.router)
    r = TestClient(a).get("/api/copilot/review/weekly")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "weekly" and body["grounded"] is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_review_weekly.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

`review.py` 追加：

```python
def _iso_week_of(day: str) -> str:
    from datetime import date

    d = date.fromisoformat(day)
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def _prev_iso_week(today: str | None = None) -> str:
    from datetime import date, timedelta

    d = (date.fromisoformat(today) if today else date.today()) - timedelta(days=7)
    return _iso_week_of(d.isoformat())


def build_weekly_review(conn: sqlite3.Connection, week_iso: str) -> ReviewCardDTO:
    rows = trades_mod.list_trades(conn)
    in_week = [t for t in rows if _iso_week_of(t.trade_date) == week_iso]
    sections: list[ReviewSectionDTO] = []
    total_realized = 0.0
    lines: list[str] = []
    sells = [t for t in in_week if t.side == "sell"]
    for t in in_week:
        lines.append(f"{t.trade_date} {t.side_cn} {t.fund_name} {t.amount:.0f} 元"
                     f"（{t.price_status_cn}）")
    for t in sells:
        info = trades_mod.realized_pnl_of(conn, t.trade_id)
        if info.get("realized_pnl") is not None:
            total_realized += info["realized_pnl"]
    if not in_week:
        lines.append("本周没有台账成交——没有记录就没有复盘，下周记得报单。")
    sections.append(ReviewSectionDTO(
        heading_cn=f"{week_iso} 操作清单", lines=lines,
    ))
    sections.append(ReviewSectionDTO(
        heading_cn="本周结果",
        lines=[f"共 {len(in_week)} 笔（卖出 {len(sells)} 笔），"
               f"已实现盈亏合计 {total_realized:+.0f} 元（大白话：落袋的部分）"],
    ))
    # 纪律面：本周进入终态的计划（exited/invalidated/superseded）
    term_rows = conn.execute(
        "SELECT symbol, state, exit_reason_rule_id, exited_on FROM trade_plans "
        "WHERE state IN ('exited','invalidated','superseded') AND exited_on IS NOT NULL"
    ).fetchall()
    term_lines = [
        f"{r['symbol']} → {r['state']}"
        + (f"（{r['exit_reason_rule_id']}）" if r["exit_reason_rule_id"] else "")
        + f" @ {r['exited_on']}"
        for r in term_rows
        if r["exited_on"] and _iso_week_of(str(r["exited_on"])[:10]) == week_iso
    ]
    sections.append(ReviewSectionDTO(
        heading_cn="本周了结的计划（纪律面）",
        lines=term_lines or ["本周无计划了结记录。"],
    ))
    return ReviewCardDTO(
        review_id=f"rv_weekly_{week_iso}",
        kind="weekly",
        ref_key=week_iso,
        title_cn=f"周复盘 · {week_iso}",
        sections=sections,
        realized_pnl=total_realized,
    )


def attach_narrative(
    conn: sqlite3.Connection, review: ReviewCardDTO, *, config
) -> ReviewCardDTO:
    """GLM 复盘叙事（best-effort）：失败/无凭据保持模板，接地校验数值。"""
    if config is None:
        return review
    from lei_signal.plans import llm as plans_llm  # noqa: PLC0415
    from lei_signal.plans.grounding import (  # noqa: PLC0415
        collect_payload_numbers,
        verify_numeric_grounding,
    )

    raw = plans_llm.chat_copilot(
        review.model_dump(), "请把这份复盘讲成大白话总结，只陈述给定事实。",
        config, system_prompt=plans_llm.COPILOT_SYSTEM_PROMPT,
    )
    if raw is None:
        return review
    ok, _ = verify_numeric_grounding(raw, collect_payload_numbers(review.model_dump()))
    if not ok:
        return review
    review.narrative = raw
    review.grounded = True
    return review
```

`copilot.py` 追加端点（imports 补 review 模块）：

```python
@router.get("/copilot/review/trade/{trade_id}", response_model=ReviewCardDTO)
def trade_review(request: Request, trade_id: str) -> ReviewCardDTO:
    with closing(connect(_db_path(request))) as conn:
        card = review_mod.get_review(conn, "trade", trade_id)
        if card is None:
            card = review_mod.build_trade_review(conn, trade_id)
            if card is None:
                raise HTTPException(status_code=404, detail=f"成交不存在: {trade_id}")
            card = review_mod.attach_narrative(conn, card, config=plans_llm.load_ark_config())
            review_mod.save_review(conn, card)
            conn.commit()
    return card


@router.get("/copilot/review/weekly", response_model=ReviewCardDTO)
def weekly_review(request: Request, week: str | None = None) -> ReviewCardDTO:
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415

    week_iso = week or review_mod._prev_iso_week(today_date())
    with closing(connect(_db_path(request))) as conn:
        card = review_mod.get_review(conn, "weekly", week_iso)
        if card is None:
            card = review_mod.build_weekly_review(conn, week_iso)
            card = review_mod.attach_narrative(conn, card, config=plans_llm.load_ark_config())
            review_mod.save_review(conn, card)
            conn.commit()
    return card
```

dispatch 的 review 分支改为直达周复盘：

```python
    if intent.kind == "review":
        with closing(connect(_db_path(request))) as conn:
            week_iso = review_mod._prev_iso_week(today_date())
            card = review_mod.get_review(conn, "weekly", week_iso)
            if card is None:
                card = review_mod.build_weekly_review(conn, week_iso)
                review_mod.save_review(conn, card)
                conn.commit()
        return CopilotDispatchReply(
            intent="review",
            card={"card_type": "review", "data": card.model_dump()},
        )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_review_weekly.py tests/unit/test_copilot_dispatch.py -q`
Expected: 全部 passed（dispatch 原 review chat_fallback 断言已被本任务替换——若 dispatch 测试仍断言 `chat_fallback=True`，把它改成断言 `card["card_type"] == "review"`）

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/review.py src/lei_signal/api/routes/copilot.py tests/unit/test_copilot_review_weekly.py tests/unit/test_copilot_dispatch.py
git commit -m "feat(copilot): 周复盘聚合+GLM叙事接地+复盘路由接入dispatch"
```

### Task 17: 前端复盘卡接线

**Files:**
- Modify: `web/src/components/copilot/CopilotCards.tsx`（`TradesLedgerView` 卖出行加「复盘」按钮；新增 `ReviewFetcher`）
- Modify: `web/src/pages/PortfolioPage.tsx`（台账区上方加「本周复盘」按钮）

- [ ] **Step 1: CopilotCards.tsx 追加**

```tsx
export function ReviewFetcher({
  weekly,
  tradeId,
}: {
  weekly?: boolean;
  tradeId?: string;
}) {
  const [card, setCard] = useState<ReviewCard | null>(null);
  const q = useMutation({
    mutationFn: () =>
      weekly ? api.copilotReviewWeekly() : api.copilotReviewTrade(tradeId!),
    onSuccess: setCard,
  });
  return (
    <div style={{ display: "inline" }}>
      <button
        className="btn small"
        disabled={q.isPending || !!card}
        onClick={() => q.mutate()}
      >
        {q.isPending ? "生成中…" : card ? "已生成" : weekly ? "本周复盘" : "复盘"}
      </button>
      {card && <ReviewCardView review={card} />}
    </div>
  );
}
```

`TradesLedgerView` 卖出行（`t.side === "sell"`）追加 `<ReviewFetcher tradeId={t.trade_id} />`。

- [ ] **Step 2: PortfolioPage 台账区块头部追加 `<ReviewFetcher weekly />`**

- [ ] **Step 3: 构建 + 提交**

Run: `cd web && npm run build`

```bash
git add web/src/components/copilot/CopilotCards.tsx web/src/pages/PortfolioPage.tsx
git commit -m "feat(copilot-web): 复盘卡接线——持仓页周复盘入口+卖出单笔复盘"
```

---

# P4 · 清单页 + 工作台 + 跑批

### Task 18: 每日操作清单 ops.py + GET /api/ops/today

**Files:**
- Create: `src/lei_signal/copilot/ops.py`
- Modify: `src/lei_signal/api/schemas.py`（追加 Ops DTO 三件）
- Modify: `src/lei_signal/api/routes/copilot.py`（追加端点）
- Test: `tests/unit/test_copilot_ops.py`

**Interfaces:**
- Consumes: `list_scan`（当日扫描）、`plans.store.list_plans`/`list_action_items`、`journal.load_recommendation`、`portfolio.store.get_meta`（observations）。
- Produces: `build_ops_today(conn, *, run_date: str, recommend_card: RecommendCardDTO | None) -> OpsCardDTO`；`GET /api/ops/today`。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_ops.py
"""操作清单组装：待办/持仓处理/推荐/观察触发四段。"""
from __future__ import annotations

import pytest

from lei_signal.api.schemas import RecommendCardDTO
from lei_signal.copilot import ops
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def test_empty_db_honest_empty_sections(conn):
    card = ops.build_ops_today(conn, run_date="2026-09-05", recommend_card=None)
    assert card.plan_todos == []
    assert card.recommendations is None
    assert "暂无" in card.push_summary_cn or card.push_summary_cn


def test_waiting_scan_rows_become_watch_triggers(conn):
    conn.execute(
        "INSERT OR REPLACE INTO daily_opportunity_scan "
        "(scan_date, symbol, display_name, verdict, verdict_cn, best_scenario_cn, "
        " best_state, reward_risk_ratio, reward_risk_computable, blocking_reasons, "
        " missing_summary_cn, has_active_plan, generated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("2026-09-05", "515880", "通信ETF", "waiting", "等待条件成立",
         "A·回调", "watch", 2.5, 1, "[]", "站上EMA20", 0, "x"),
    )
    conn.commit()
    card = ops.build_ops_today(
        conn, run_date="2026-09-05",
        recommend_card=RecommendCardDTO(run_date="2026-09-05"),
    )
    assert any(t.symbol == "515880" for t in card.watch_triggers)


def test_exit_todo_ranked_first(conn):
    from lei_signal.plans.store import create_plan_draft, confirm_plan
    plan = create_plan_draft(conn, symbol="515880", module="A", direction="long",
        entry_rule_id="pullback_watch", reason="t", valid_until="2026-10-01",
        thesis_cn="t", invalidation_criteria_cn="t", drawdown_playbook_cn="t",
        take_profit_plan_cn="t", stop_plan_cn="t")
    confirm_plan(conn, plan.plan_id)
    conn.execute(
        "INSERT INTO plan_action_items (action_id, plan_id, kind, state, due_from, "
        "nag_count, source_alert_code) VALUES (?,?,?,?,?,?,?)",
        ("a1", plan.plan_id, "EXIT", "open", "2026-09-05", 3, "INVALIDATION_BREACHED"),
    )
    conn.commit()
    card = ops.build_ops_today(conn, run_date="2026-09-05", recommend_card=None)
    assert card.plan_todos and card.plan_todos[0].kind == "EXIT"
    assert card.plan_todos[0].nag_count == 3
    assert "EXIT" in card.push_summary_cn or "退出" in card.push_summary_cn
```

（夹具若与 `plans.store.create_plan_draft` 实际签名不符，以实际为准微调，断言不变——同 Task 15 约定。）

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_ops.py -q`
Expected: FAIL

- [ ] **Step 3: 实现**

`api/schemas.py` 追加：

```python
class OpsTodoDTO(BaseModel):
    action_id: str
    plan_id: str
    symbol: str
    kind: str
    kind_cn: str
    next_step_cn: str = ""
    due_from: str = ""
    nag_count: int = 0


class OpsLineDTO(BaseModel):
    symbol: str
    display_name: str = ""
    text_cn: str


class OpsCardDTO(BaseModel):
    """每日操作清单（确定性组装，零 LLM；页面与推送共用）。"""

    run_date: str
    generated_at: str = ""
    holdings_actions: list[OpsLineDTO] = []
    recommendations: RecommendCardDTO | None = None
    plan_todos: list[OpsTodoDTO] = []
    watch_triggers: list[OpsLineDTO] = []
    push_summary_cn: str = ""
```

`src/lei_signal/copilot/ops.py`：

```python
"""每日操作清单组装（纯读，零 LLM）：页面与每日跑批推送共用。

四段：① 持仓要处理的（EXIT 类待办 + 组合 observations）
     ② 今日推荐（推荐账本当日存证，缺省 None）
     ③ 计划待办催办（open 待办，EXIT 优先）
     ④ 观察触发（当日扫描 waiting 项还缺什么）
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import OpsCardDTO, OpsLineDTO, OpsTodoDTO, RecommendCardDTO

_KIND_CN = {"ENTER": "入场", "EXIT": "退出", "REVIEW": "复核"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def build_ops_today(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    recommend_card: RecommendCardDTO | None,
) -> OpsCardDTO:
    rows = conn.execute(
        """SELECT a.action_id, a.plan_id, a.kind, a.due_from, a.nag_count,
                  p.symbol
           FROM plan_action_items a
           JOIN trade_plans p ON p.plan_id = a.plan_id
           WHERE a.state = 'open'
           ORDER BY CASE a.kind WHEN 'EXIT' THEN 0 WHEN 'ENTER' THEN 1 ELSE 2 END,
                    a.nag_count DESC"""
    ).fetchall()
    todos = [
        OpsTodoDTO(
            action_id=r["action_id"],
            plan_id=r["plan_id"],
            symbol=r["symbol"],
            kind=r["kind"],
            kind_cn=_KIND_CN.get(r["kind"], r["kind"]),
            next_step_cn="见计划卡（判定层已给出 next_step）",
            due_from=r["due_from"] or "",
            nag_count=int(r["nag_count"] or 0),
        )
        for r in rows
    ]
    holdings: list[OpsLineDTO] = [
        OpsLineDTO(
            symbol=t.symbol,
            text_cn=f"{t.kind_cn}待办（已催 {t.nag_count} 次）——按计划处理",
        )
        for t in todos
        if t.kind == "EXIT"
    ]
    obs_row = conn.execute(
        "SELECT value FROM portfolio_meta WHERE key = 'observations'"
    ).fetchone()
    if obs_row:
        import json  # noqa: PLC0415

        try:
            for note in json.loads(obs_row["value"]) or []:
                if isinstance(note, str):
                    holdings.append(OpsLineDTO(symbol="-", text_cn=f"组合提示：{note}"))
        except (TypeError, ValueError):
            pass
    watch: list[OpsLineDTO] = []
    for r in conn.execute(
        "SELECT symbol, display_name, missing_summary_cn, verdict FROM "
        "daily_opportunity_scan WHERE scan_date = ? AND verdict IN ('waiting')",
        (run_date,),
    ).fetchall():
        watch.append(OpsLineDTO(
            symbol=r["symbol"],
            display_name=r["display_name"] or r["symbol"],
            text_cn=f"还缺：{r['missing_summary_cn'] or '条件未齐'}（条件成立即构成系统买点）",
        ))
    exit_n = sum(1 for t in todos if t.kind == "EXIT")
    enter_n = sum(1 for t in todos if t.kind == "ENTER")
    parts = []
    if exit_n:
        parts.append(f"{exit_n} 个退出待办（最优先）")
    if enter_n:
        parts.append(f"{enter_n} 个入场待办")
    if recommend_card and recommend_card.items:
        parts.append(f"今日推荐 {len(recommend_card.items)} 个标的")
    summary = "；".join(parts) + "。" if parts else "今日无必须处理的待办。"
    return OpsCardDTO(
        run_date=run_date,
        generated_at=_now(),
        holdings_actions=holdings,
        recommendations=recommend_card,
        plan_todos=todos,
        watch_triggers=watch,
        push_summary_cn=summary,
    )
```

`copilot.py` 追加：

```python
@router.get("/ops/today", response_model=OpsCardDTO)
def ops_today(request: Request) -> OpsCardDTO:
    """每日操作清单（页面数据源；推送由 scripts/copilot_daily.py 同源组装）。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot import ops as ops_mod  # noqa: PLC0415

    run_date = today_date()
    with closing(connect(_db_path(request))) as conn:
        rec = journal.load_recommendation(conn, run_date)
        return ops_mod.build_ops_today(
            conn, run_date=run_date, recommend_card=rec
        )
```

（schemas import 补 `OpsCardDTO`。）

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_ops.py -q`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/ops.py src/lei_signal/api/schemas.py src/lei_signal/api/routes/copilot.py tests/unit/test_copilot_ops.py
git commit -m "feat(copilot): 每日操作清单组装+GET /api/ops/today（页面/推送同源）"
```

### Task 19: 推荐对账打分 score_journal_outcomes

**Files:**
- Modify: `src/lei_signal/copilot/journal.py`（追加 `score_journal_outcomes`）
- Test: `tests/unit/test_copilot_outcome.py`

**Interfaces:**
- Consumes: `AnalysisService.get(symbol).result.frame`（含 `date`/`close` 列的 DataFrame）。
- Produces: `score_journal_outcomes(conn, service, *, horizons: tuple[int, ...] = (1, 5, 20), today: str | None = None) -> int`——给**尚无 outcome** 的账本日补 T+N 涨跌幅（{symbol: {chg_1d, chg_5d, chg_20d}}，百分点）；返回补写条数。Task 20 跑批调用。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/test_copilot_outcome.py
"""推荐对账：T+N 涨跌幅打分（前向存证，D9）。"""
from __future__ import annotations

import pandas as pd

from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


class _FakeResult:
    def __init__(self, frame):
        self.frame = frame


class _FakeEntry:
    def __init__(self, frame):
        self.result = _FakeResult(frame)
        self.error = None


class _FakeService:
    def __init__(self, frames):
        self._frames = frames

    def get(self, symbol, refresh=False):
        return _FakeEntry(self._frames[symbol])


def _frame(closes):  # 2026-09-01 起逐日
    dates = pd.bdate_range("2026-09-01", periods=len(closes))
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "close": closes,
    })


def test_scores_one_five_twenty(conn_like := None):
    conn = connect(":memory:")
    card = RecommendCardDTO(
        run_date="2026-09-01",
        items=[RecommendItemDTO(symbol="515880", verdict="waiting")],
    )
    journal.save_recommendation(conn, card)
    svc = _FakeService({"515880": _frame([1.0] * 25)})
    n = journal.score_journal_outcomes(conn, svc, today="2026-10-01")
    assert n == 1
    out = journal.load_outcome(conn, "2026-09-01")
    assert out["515880"]["chg_1d"] == 0.0
    assert "chg_20d" in out["515880"]


def test_skips_already_scored_and_missing_data():
    conn = connect(":memory:")
    card = RecommendCardDTO(
        run_date="2026-09-01",
        items=[RecommendItemDTO(symbol="515880", verdict="waiting")],
    )
    journal.save_recommendation(conn, card)
    svc = _FakeService({})  # 无数据
    assert journal.score_journal_outcomes(conn, svc, today="2026-10-01") == 0
    # 手动补 outcome 后不再重打
    journal.save_outcome(conn, "2026-09-01", {})
    assert journal.score_journal_outcomes(conn, svc, today="2026-10-01") == 0


def test_not_enough_future_days_scores_partial_or_skips():
    conn = connect(":memory:")
    card = RecommendCardDTO(
        run_date="2026-09-01",
        items=[RecommendItemDTO(symbol="515880", verdict="waiting")],
    )
    journal.save_recommendation(conn, card)
    svc = _FakeService({"515880": _frame([1.0, 1.1])})  # 只有 2 天
    n = journal.score_journal_outcomes(conn, svc, today="2026-09-03")
    assert n in (0, 1)
    if n == 1:
        out = journal.load_outcome(conn, "2026-09-01")
        assert "chg_1d" in out["515880"]
        assert "chg_20d" not in out["515880"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/unit/test_copilot_outcome.py -q`
Expected: FAIL

- [ ] **Step 3: 实现（journal.py 追加）**

```python
def _outcome_changes(frame, run_date: str, horizons: tuple[int, ...]) -> dict[str, float]:
    """run_date 收盘为基准的 T+N 收盘涨跌幅（百分点）。数据不足的档位跳过。"""
    import pandas as pd  # noqa: PLC0415
    from datetime import date as _date  # noqa: PLC0415

    pairs = sorted(zip(
        pd.to_datetime(frame["date"]).dt.date.tolist(),
        frame["close"].astype(float).tolist(),
    ))
    base_i = max(
        (k for k, (d, _) in enumerate(pairs) if d <= _date.fromisoformat(run_date)),
        default=None,
    )
    if base_i is None or pairs[base_i][1] <= 0:
        return {}
    base = pairs[base_i][1]
    out: dict[str, float] = {}
    for h in horizons:
        j = base_i + h
        if j < len(pairs):
            out[f"chg_{h}d"] = round((pairs[j][1] / base - 1.0) * 100.0, 2)
    return out


def score_journal_outcomes(
    conn: sqlite3.Connection,
    service,
    *,
    horizons: tuple[int, ...] = (1, 5, 20),
    today: str | None = None,
) -> int:
    """给尚无 outcome 的推荐账本日补 T+N 对账（只补一次，幂等）。

    前向存证口径（设计定稿 §5）：不做伪历史回测，从推荐次日起用真实行情
    逐档打分；行情不足的档位跳过，已有 outcome 的日期不重打。
    """
    from datetime import UTC as _UTC  # noqa: PLC0415
    from datetime import datetime as _dt  # noqa: PLC0415

    today = today or _dt.now(_UTC).date().isoformat()
    rows = conn.execute(
        "SELECT run_date FROM recommendation_journal "
        "WHERE outcome IS NULL AND run_date < ? ORDER BY run_date",
        (today,),
    ).fetchall()
    written = 0
    for row in rows:
        run_date = row["run_date"]
        card = load_recommendation(conn, run_date)
        if card is None or not card.items:
            continue
        outcome: dict[str, dict[str, float]] = {}
        for item in card.items:
            try:
                entry = service.get(item.symbol)
            except Exception:  # noqa: BLE001  单标的失败不影响其余
                continue
            if getattr(entry, "result", None) is None:
                continue
            changes = _outcome_changes(entry.result.frame, run_date, horizons)
            if changes:
                outcome[item.symbol] = changes
        if outcome:
            save_outcome(conn, run_date, outcome)
            written += 1
    return written
```

（`:memory:` 连接由 `connect` 建表后即可用——迁移在建库时全量执行。）

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/unit/test_copilot_outcome.py -q`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/copilot/journal.py tests/unit/test_copilot_outcome.py
git commit -m "feat(copilot): 推荐存证T+N对账打分——前向存证不做伪历史回测"
```

### Task 20: 每日跑批 copilot_daily.py + launchd

**Files:**
- Create: `scripts/copilot_daily.py`
- Create: `scripts/com.lei.copilot.daily.plist`

**Interfaces:**
- Consumes: Task 12 `price_pending_trades`、Task 19 `score_journal_outcomes`、Task 18 `build_ops_today`、`run_opportunity_scan`/`upsert_scan_results`、`SectorsService`/`NewsfeedService`/`AnalysisService`（`app.py` 同款构造）、`notify.macos.MacNotifier`/`notify.feishu_webhook.FeishuWebhookNotifier`/`notify.base.NotificationPayload`。
- Produces: CLI：`python3 scripts/copilot_daily.py [--dry-run] [--db path]`；launchd 每交易日 16:10（扫描 15:00 之后）。

- [ ] **Step 1: 实现 `scripts/copilot_daily.py`（照 daily_scan.py 的入口骨架）**

```python
"""Agent 超级入口 · 每日跑批（16:10 收盘扫描之后触发）。

职责（顺序）：
1. 补定价 pending 基金成交（QDII T+1 次日补）。
2. 确保当日机会扫描落库（15:00 launchd 已跑；空表则现场重扫兜底）。
3. 组装今日推荐并存证 recommendation_journal（确定性，零 LLM）。
4. 组装 /ops 清单；有 EXIT/actionable 级事件时飞书+macOS 双通道推送
   （纯观察只亮红点不推，设计定稿 §E）。
5. 给历史推荐账本补 T+N 对账（score_journal_outcomes）。

判定权全部在既有规则层与 copilot 纯函数；本脚本只编排、落库、投递。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import closing
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.opportunity_scan import (  # noqa: E402
    list_scan,
    today_date,
    upsert_scan_results,
)
from lei_signal.api.routes.opportunities import (  # noqa: E402
    _row_to_scan_item,
    run_opportunity_scan,
)
from lei_signal.api.sectors_service import SectorsService  # noqa: E402
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.copilot import journal, ops as ops_mod, trades as trades_mod  # noqa: E402
from lei_signal.copilot.recommend import build_recommendation  # noqa: E402
from lei_signal.newsfeed.service import NewsfeedService  # noqa: E402
from lei_signal.notify.base import NotificationPayload  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def _push(title: str, body_md: str, *, dry_run: bool) -> None:
    payload = NotificationPayload(
        title=title, body_md=body_md, tier=1, plan_id="copilot-daily",
    )
    for notifier in _notifiers(dry_run):
        try:
            notifier.send(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[{type(notifier).__name__}] 投递失败：{exc}", file=sys.stderr)


def _notifiers(dry_run: bool) -> list:
    from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier  # noqa: PLC0415
    from lei_signal.notify.macos import MacNotifier  # noqa: PLC0415

    out = [MacNotifier(dry_run=dry_run)]
    url = os.environ.get("FEISHU_WEBHOOK_URL")
    if url:
        out.append(FeishuWebhookNotifier(url, dry_run=dry_run))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db", default=os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path()))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    service = AnalysisService(max_workers=8)
    db = args.db
    run_date = today_date()

    with closing(connect(db)) as conn:
        priced = trades_mod.price_pending_trades(conn)
        conn.commit()
        logging.info("补定价完成：%d 笔", priced)

    with closing(connect(db)) as conn:
        rows = list_scan(conn, run_date)
    if not rows:
        response = run_opportunity_scan(service, db)
        with closing(connect(db)) as conn:
            upsert_scan_results(conn, run_date, response.items)
            conn.commit()
        rows = list_scan(connect(db), run_date)
    scan_items = [_row_to_scan_item(r) for r in rows]

    sector_rows = None
    try:
        data = SectorsService().trend(refresh=False, level="l1")
        sector_rows = next(
            (data[k] for k in ("sectors", "rows", "items")
             if isinstance(data, dict) and isinstance(data.get(k), list)),
            None,
        ) if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        sector_rows = None
    news_brief = None
    try:
        news_brief = NewsfeedService().watchlist_brief([], days=3) or None
    except Exception:  # noqa: BLE001
        news_brief = None

    card = build_recommendation(scan_items, run_date=run_date,
                                sector_rows=sector_rows, news_brief=news_brief)
    with closing(connect(db)) as conn:
        if card.items:
            journal.save_recommendation(conn, card)
        ops_card = ops_mod.build_ops_today(conn, run_date=run_date, recommend_card=card)
        scored = journal.score_journal_outcomes(conn, service)
        conn.commit()
    logging.info("推荐 %d 项；对账补写 %d 日", len(card.items), scored)

    has_exit = any(t.kind == "EXIT" for t in ops_card.plan_todos)
    has_actionable = any(i.verdict == "actionable" for i in card.items)
    if (has_exit or has_actionable) and not args.dry_run:
        _push(
            f"LEI 今日操作（{run_date}）",
            ops_card.push_summary_cn
            + "\n详情打开看板 /ops 页。退出待办最优先。",
            dry_run=args.dry_run,
        )
    else:
        logging.info("无推送级事件（exit=%s actionable=%s）", has_exit, has_actionable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: plist `scripts/com.lei.copilot.daily.plist`（照 com.lei.daily.brief.plist 结构，改 Label/ProgramArguments/StartCalendarInterval Hour=16 Minute=10）**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.lei.copilot.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>scripts/copilot_daily.py</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/yongbiaoli/lei-signal-sync</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>10</integer></dict>
  <key>StandardOutPath</key><string>/tmp/lei-copilot-daily.log</string>
  <key>StandardErrorPath</key><string>/tmp/lei-copilot-daily.err</string>
</dict>
</plist>
```

- [ ] **Step 3: 干跑验证**

Run: `PYTHONPATH=src python3 scripts/copilot_daily.py --dry-run 2>&1 | tail -5`
Expected: 输出补定价/推荐/对账日志，无异常退出（网络服务失败会容错降级，不影响退出码 0）

- [ ] **Step 4: 提交（plist 安装属部署动作，收尾任务统一做）**

```bash
git add scripts/copilot_daily.py scripts/com.lei.copilot.daily.plist
git commit -m "feat(copilot): 每日跑批——补定价/推荐存证/清单组装/双通道推送/T+N对账"
```

### Task 21: 周复盘跑批 copilot_weekly.py + launchd

**Files:**
- Create: `scripts/copilot_weekly.py`
- Create: `scripts/com.lei.copilot.weekly.plist`

- [ ] **Step 1: 实现（结构同 Task 20，核心两行：build + save + push）**

```python
"""Agent 超级入口 · 周复盘跑批（每周日 20:00）。

组装上一完整 ISO 周的周复盘（复用 copilot.review，确定性零 LLM 叙事由
端点按需补），存 trade_reviews，并飞书+macOS 推送摘要。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import closing
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.opportunity_scan import today_date  # noqa: E402
from lei_signal.copilot import review as review_mod  # noqa: E402
from lei_signal.notify.base import NotificationPayload  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db", default=os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path()))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    week_iso = review_mod._prev_iso_week(today_date())
    with closing(connect(args.db)) as conn:
        card = review_mod.build_weekly_review(conn, week_iso)
        review_mod.save_review(conn, card)
        conn.commit()
    body = card.push_summary if hasattr(card, "push_summary") else "\n".join(
        f"【{s.heading_cn}】" + "；".join(s.lines[:3]) for s in card.sections
    )
    logging.info("周复盘已存证：%s", week_iso)
    if not args.dry_run:
        from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier  # noqa: PLC0415
        from lei_signal.notify.macos import MacNotifier  # noqa: PLC0415

        payload = NotificationPayload(
            title=f"LEI 周复盘 {week_iso}",
            body_md=body, tier=2, plan_id="copilot-weekly",
        )
        for notifier in [MacNotifier(dry_run=False)] + (
            [FeishuWebhookNotifier(os.environ["FEISHU_WEBHOOK_URL"])]
            if os.environ.get("FEISHU_WEBHOOK_URL") else []
        ):
            try:
                notifier.send(payload)
            except Exception as exc:  # noqa: BLE001
                print(f"[{type(notifier).__name__}] 投递失败：{exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: plist（同 Task 20 模板：Label `com.lei.copilot.weekly`，Weekday=0（周日）Hour=20 Minute=0）**
- [ ] **Step 3: 干跑验证**

Run: `PYTHONPATH=src python3 scripts/copilot_weekly.py --dry-run`
Expected: 退出码 0，日志含周号

- [ ] **Step 4: 提交**

```bash
git add scripts/copilot_weekly.py scripts/com.lei.copilot.weekly.plist
git commit -m "feat(copilot): 周复盘跑批+周日launchd推送"
```

### Task 22: OpsPage + 导航入口（前端）

**Files:**
- Create: `web/src/pages/OpsPage.tsx`
- Modify: `web/src/App.tsx`（路由 `/ops` 与 `/agent` 一次加好）
- Modify: `web/src/components/TopNav.tsx`（追加两个 NavLink）

- [ ] **Step 1: OpsPage.tsx（完整文件）**

```tsx
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { RecommendCardView } from "../components/copilot/CopilotCards";

export default function OpsPage() {
  const q = useQuery({
    queryKey: ["opsToday"],
    queryFn: () => api.opsToday(),
    refetchInterval: 60_000,
  });
  if (q.isLoading) return <div className="muted page-pad">清单加载中…</div>;
  if (q.isError || !q.data)
    return <div className="cp-error page-pad">清单加载失败，稍后重试。</div>;
  const ops = q.data;
  return (
    <div className="page-pad" style={{ maxWidth: 860, margin: "0 auto" }}>
      <h2>今日操作 · {ops.run_date}</h2>
      <div className="muted">{ops.push_summary_cn}</div>

      <section>
        <h3>① 持仓要处理的</h3>
        {ops.holdings_actions.length === 0 && <div className="muted">暂无。</div>}
        {ops.holdings_actions.map((l, i) => (
          <div key={i} className="cp-row">
            {l.symbol !== "-" && (
              <Link to={`/symbol/${l.symbol}`} className="cp-sym">
                {l.display_name || l.symbol}
              </Link>
            )}
            <span>{l.text_cn}</span>
          </div>
        ))}
      </section>

      <section>
        <h3>② 今日推荐</h3>
        {ops.recommendations ? (
          <RecommendCardView card={ops.recommendations} />
        ) : (
          <div className="muted">今日尚未生成推荐（收盘后自动生成）。</div>
        )}
      </section>

      <section>
        <h3>③ 计划待办</h3>
        {ops.plan_todos.length === 0 && <div className="muted">暂无待办。</div>}
        {ops.plan_todos.map((t) => (
          <div key={t.action_id} className="cp-row">
            <Link to={`/symbol/${t.symbol}`} className="cp-sym">{t.symbol}</Link>
            <span className={t.kind === "EXIT" ? "cp-error" : ""}>
              {t.kind_cn}待办 · 已催 {t.nag_count} 次 · 可执行自 {t.due_from || "-"}
            </span>
            <Link to="/plans" className="cp-link">去监督待办处理</Link>
          </div>
        ))}
      </section>

      <section>
        <h3>④ 观察触发</h3>
        {ops.watch_triggers.length === 0 && <div className="muted">暂无观察项。</div>}
        {ops.watch_triggers.map((l, i) => (
          <div key={i} className="cp-row">
            <Link to={`/symbol/${l.symbol}`} className="cp-sym">
              {l.display_name || l.symbol}
            </Link>
            <span className="muted">{l.text_cn}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
```

（若 `page-pad` 类不存在，用既有页面容器的类名——对齐 `SupervisorPage.tsx` 外层容器写法。）

- [ ] **Step 2: App.tsx 加两条路由（import OpsPage/AgentWorkspacePage + `<Route path="/ops" .../>` `<Route path="/agent" .../>`，AgentWorkspacePage 由 Task 23 创建——本任务先只加 `/ops`，Task 23 补 `/agent`）；TopNav 在「我的持仓」后追加 `<NavLink to="/ops">今日操作</NavLink>`**
- [ ] **Step 3: 构建 + 提交**

Run: `cd web && npm run build`

```bash
git add web/src/pages/OpsPage.tsx web/src/App.tsx web/src/components/TopNav.tsx
git commit -m "feat(copilot-web): /ops每日操作清单页+顶栏导航"
```

### Task 23: Agent 工作台 /agent（整页对话 + 联动 K 线）

**Files:**
- Modify: `src/lei_signal/api/schemas.py`（`AgentChatReply` 加 `resolved_symbol: str | None = None`）
- Modify: `src/lei_signal/api/routes/agent.py`（`agent_chat` 返回值带 `resolved_symbol=symbol`）
- Create: `web/src/pages/AgentWorkspacePage.tsx`
- Modify: `web/src/App.tsx`（`/agent` 路由）、`web/src/components/TopNav.tsx`（「工作台」链接）
- Modify: `web/src/styles.css`（工作台布局类）

**Interfaces:**
- Consumes: `api.agentChat`（types 的 `AgentChatReply` 加 `resolved_symbol?: string | null`）、`api.copilotDispatch`、`api.symbolDetail`（client.ts 里 `/symbols/{symbol}/detail` 的既有封装，方法名以文件为准）、`KlineChart`、`CopilotCardDispatcher`。

- [ ] **Step 1: 后端两处小改**（schemas 加字段；agent.py `AgentChatReply(... )` 构造加 `resolved_symbol=symbol`；前端 `types.ts` 的 `AgentChatReply` 加 `resolved_symbol?: string | null`）

- [ ] **Step 2: AgentWorkspacePage.tsx（完整文件；方法名 `api.symbolDetail` 若与 client.ts 不符，以 client.ts 实际为准）**

```tsx
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AgentMarkdown from "../components/AgentMarkdown";
import KlineChart from "../components/KlineChart";
import { CopilotCardDispatcher } from "../components/copilot/CopilotCards";
import type { TradePreview } from "../types";

type Turn = {
  who: "you" | "agent";
  text: string;
  grounded?: boolean;
  card?: { card_type: string; data: unknown } | null;
  preview?: TradePreview | null;
};

const QUICK = [
  { label: "今天看什么", kind: "recommend" },
  { label: "持仓速览", kind: "holdings" },
  { label: "我要报单", kind: "trade" },
  { label: "本周复盘", kind: "review" },
] as const;

export default function AgentWorkspacePage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns]);

  const dispatch = useMutation({
    mutationFn: (message: string) =>
      api.copilotDispatch({ message, symbol: symbol ?? undefined }),
    onSuccess: (reply, message) => {
      setTurns((cur) => [
        ...cur,
        { who: "you", text: message },
        { who: "agent", text: reply.note_cn, card: reply.card,
          preview: reply.preview, grounded: true },
      ]);
      if (reply.chat_fallback) chat.mutate(message);
    },
  });

  const chat = useMutation({
    mutationFn: (message: string) =>
      api.agentChat({
        session_id: sessionId,
        context_kind: symbol ? "symbol" : "global",
        symbol,
        message,
      }),
    onSuccess: (r) => {
      setSessionId(r.session_id);
      if (r.resolved_symbol) setSymbol(r.resolved_symbol);
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: r.reply, grounded: r.grounded },
      ]);
    },
  });

  const detail = useQuery({
    queryKey: ["symbolDetail", symbol],
    queryFn: () => api.symbolDetail(symbol!),
    enabled: !!symbol,
    staleTime: 60_000,
  });

  const send = (raw: string) => {
    const message = raw.trim();
    if (!message) return;
    setInput("");
    setTurns((cur) => [...cur]);  // 触发滚动
    if (/买了|卖了|申购|赎回|今天看什么|推荐|持仓|复盘/.test(message)) {
      dispatch.mutate(message);
    } else if (symbol) {
      chat.mutate(message);
    } else {
      chat.mutate(message);
    }
  };

  return (
    <div className="ws-layout">
      <div className="ws-chat">
        <div className="ws-quick">
          {QUICK.map((q) => (
            <button
              key={q.kind}
              className="btn small"
              onClick={() =>
                q.kind === "trade"
                  ? setInput("我")
                  : dispatch.mutate(q.label)
              }
            >
              {q.label}
            </button>
          ))}
          {symbol && (
            <Link to={`/symbol/${symbol}`} className="cp-link">
              {symbol} 大图
            </Link>
          )}
        </div>
        <div className="ws-turns" ref={bodyRef}>
          {turns.length === 0 && (
            <div className="muted">
              说一句话开始：点上方快捷指令，或直接问（如「515880 现在怎么看」）。
            </div>
          )}
          {turns.map((t, i) => (
            <div key={i} className={t.who === "you" ? "ws-you" : "ws-agent"}>
              {t.text && <AgentMarkdown text={t.text} />}
              <CopilotCardDispatcher card={t.card ?? null} preview={t.preview ?? null} />
            </div>
          ))}
          {(dispatch.isPending || chat.isPending) && (
            <div className="muted">思考中…</div>
          )}
        </div>
        <div className="drawer-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.nativeEvent.isComposing || e.keyCode === 229)
                return;
              if (e.key === "Enter") send(input);
            }}
            placeholder={symbol ? `就 ${symbol} 讨论，或随便问` : "问点什么"}
          />
          <button
            className="btn small primary"
            disabled={dispatch.isPending || chat.isPending || !input.trim()}
            onClick={() => send(input)}
          >
            发送
          </button>
        </div>
      </div>
      <div className="ws-side">
        {symbol ? (
          detail.data ? (
            <KlineChart
              payload={detail.data.chart}
              display="day"
              onPick={() => {}}
              onDownload={() => {}}
            />
          ) : (
            <div className="muted">K线加载中…</div>
          )
        ) : (
          <div className="muted">
            右栏会自动跟随对话里提到的标的（K 线 + 买卖点标记）；提到代码即切。
          </div>
        )}
      </div>
    </div>
  );
}
```

（KlineChart 的 `display` 取值以 `klineTimeframe.ts` 的 `Timeframe` 为准——若 `"day"` 不是合法值，用 DetailPage 默认值；`onPick/onDownload` 为必填时传 no-op。）

- [ ] **Step 3: styles.css 追加**

```css
/* ---- Agent 工作台 ---- */
.ws-layout { display: grid; grid-template-columns: minmax(360px, 1fr) minmax(320px, 1fr);
  gap: 12px; height: calc(100vh - 90px); padding: 12px; }
.ws-chat { display: flex; flex-direction: column; min-height: 0;
  border: 1px solid var(--border, #ddd); border-radius: 12px; }
.ws-quick { display: flex; gap: 8px; padding: 8px; flex-wrap: wrap;
  border-bottom: 1px solid var(--border, #eee); }
.ws-turns { flex: 1; overflow-y: auto; padding: 10px; display: flex;
  flex-direction: column; gap: 10px; }
.ws-you { align-self: flex-end; background: #e8f0fe; border-radius: 10px;
  padding: 6px 10px; max-width: 85%; font-size: 13px; }
.ws-agent { align-self: flex-start; max-width: 95%; font-size: 13px; }
.ws-side { border: 1px solid var(--border, #ddd); border-radius: 12px;
  overflow: hidden; min-height: 0; }
@media (max-width: 900px) { .ws-layout { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: 构建 + 后端测试回归**

Run: `cd web && npm run build && cd .. && python -m pytest tests/unit/test_agent_chat.py -q`
Expected: build 通过；agent chat 测试仍绿（AgentChatReply 新增字段有默认值，不破坏既有断言）

- [ ] **Step 5: 提交**

```bash
git add src/lei_signal/api/schemas.py src/lei_signal/api/routes/agent.py web/src/pages/AgentWorkspacePage.tsx web/src/App.tsx web/src/components/TopNav.tsx web/src/styles.css web/src/types.ts
git commit -m "feat(copilot-web): /agent整页工作台——左对话右联动K线+快捷指令条"
```

### Task 24: 全量门禁 + 部署动作 + 收尾

- [ ] **Step 1: 全量后端门禁**

Run: `python -m pytest -q && ruff check src && mypy src`
Expected: 全绿（既有测试零回归；若守门扫描误报，检查是否引入禁用标识符）

- [ ] **Step 2: 前端构建**

Run: `cd web && npm run build`
Expected: tsc + vite 构建通过

- [ ] **Step 3: launchd 安装（部署动作）**

```bash
launchctl unload scripts/com.lei.copilot.daily.plist 2>/dev/null; launchctl load scripts/com.lei.copilot.daily.plist
launchctl unload scripts/com.lei.copilot.weekly.plist 2>/dev/null; launchctl load scripts/com.lei.copilot.weekly.plist
launchctl list | grep copilot
```

Expected: 列表出现 com.lei.copilot.daily / com.lei.copilot.weekly

- [ ] **Step 4: 端到端手验清单（写进提交说明）**

1. `curl -s localhost:8000/api/copilot/recommend | head -c 400` —— 返回推荐卡 JSON
2. `curl -s -X POST localhost:8000/api/copilot/dispatch -H 'Content-Type: application/json' -d '{"message":"我昨天买了1万515880"}'` —— 返回 preview 确认卡数据
3. `curl -s -X POST localhost:8000/api/copilot/trades -H 'Content-Type: application/json' -d '{"fund_code":"515880","fund_name":"通信ETF","side":"buy","amount":10000,"trade_date":"2026-09-04"}'` —— 落库并定价
4. 浏览器：`/ops` 出清单；`/agent` 说「515880」右栏出 K 线；持仓页见台账
5. `python3 scripts/copilot_daily.py --dry-run` 退出码 0

- [ ] **Step 5: 收尾提交（若 Steps 1-4 产生修正）**

```bash
git add -u && git commit -m "chore(copilot): P1-P4全量门禁修正与收尾" || true
```

---

## 计划自审记录

- 规格覆盖：定稿 §2 D1→Task 12/13；D2→Task 5；D3→Task 10/22/23；D4→Task 20/21；D5→Task 3/4（宇宙=扫描表+板块快照）；D6→Task 6/7；D7→Task 1/11；D8→Task 2 DTO 字段 sentiment_status；D9→Task 2/19。§4.A→Task 3/4；§B→Task 5；§C→Task 12/13/14；§D→Task 15/16/17；§E→Task 18/20/22；§F→Task 10/23；§G→Task 6/7；§H→Task 1；§I→Task 3 适配器容错。§7 端点全部落位；§9 分期一致；§10 门禁落 Task 24 与各任务 Step。
- 类型一致性：`build_recommendation`/`save_recommendation`/`build_sizing_advice`/`parse_trade_report`/`create_trade`/`price_pending_trades`/`position_summary`/`realized_pnl_of`/`build_trade_review`/`build_weekly_review`/`build_ops_today`/`score_journal_outcomes` 在消费任务中的签名与定义一致；DTO 字段前后端对齐（types.ts 与 schemas.py 同名同型）。
- 已知实现期自由度（非占位符）：`plans.store.create_plan_draft` 测试夹具签名以实际为准（Task 15/18 已注明）；`api.symbolDetail` 方法名以 client.ts 为准（Task 23 已注明）；`KlineChart.display` 合法值以 klineTimeframe 为准（Task 23 已注明）。
