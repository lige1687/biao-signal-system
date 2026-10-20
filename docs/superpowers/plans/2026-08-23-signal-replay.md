# 今日自选信号 · 历史回放 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 横幅支持选过去交易日 D，展示/补算截至 D 的全自选买卖信号（快照优先，回放补算落库）。

**Architecture:** 复用 `pipeline.analyze(as_of=day)` 的既有行情截断（无前视）；回放模块组装买点（`build_review`）+ 卖点（`extract_sell_signals`）写两表 `scan_date=D`；API 参数化 `_build_response`；前端横幅加日期选择与回放状态机。

**Tech Stack:** Python 3.11 + FastAPI + SQLite（WAL）；React 18 + TanStack Query。

**设计文档:** `docs/superpowers/specs/2026-08-23-signal-replay-design.md`

## Global Constraints

- 判定规则零改动：回放只通过 `analyze(symbol, as_of=day)` 截断行情，不写任何新规则。
- 回放不显示"已有计划"（`active_plan_ids=()`）：计划是当下事实。
- 红点（`/api/plans/summary`）不参与回放。
- 回放口径声明常驻：当前自选 × 行情截至所选交易日重算，含成分前视，仅形态参考。
- DATA_UNAVAILABLE 显式落 unavailable 行，不静默。
- 工作区有 ~576 个无关未提交文件：`git add` 只用精确路径；对含用户 WIP 的共享文件（types.ts/client.ts/styles.css）用索引级拆分提交（构造「HEAD + 本任务改动」blob，`git hash-object -w` + `git update-index --cacheinfo "100644,$blob,<path>"`），提交前必须 `git diff HEAD -- <file>` 检查非本任务 hunk。
- pytest 从项目根：`cd ~/Desktop/lei-signal-lab && python3 -m pytest -q`（当前基线 1056 passed / 1 skipped）。
- UI 只改 `web/`，Streamlit 零改动。

---

### Task 1: 回放计算 `run_signal_replay`

**Files:**
- Create: `src/lei_signal/api/signal_replay.py`
- Test: `tests/unit/test_signal_replay.py`

**Interfaces:**
- Consumes: `lei_signal.compose.pipeline.analyze(symbol, *, as_of: date, cache_root=None, sqlite_path=None)`（截断在 pipeline.py:217-218）；`lei_signal.api.routes.opportunities.build_review`；`lei_signal.api.sell_signals.extract_sell_signals`；`lei_signal.api.signal_alerts_store`（`SignalAlertRow/upsert_signal_alerts/SIDE_SELL/SIDE_UNAVAILABLE`）；`lei_signal.api.opportunity_scan`（`today_date/upsert_scan_results/list_scan`）；`lei_signal.api.watchlist.list_watchlist`；`lei_signal.api.config.cache_root/sqlite_path`。
- Produces（Task 2/4 依赖）: `run_signal_replay(db_path: str, day: date, *, symbols: list[str] | None = None, max_workers: int = 4) -> dict`，返回 `{"scan_date", "as_of", "scanned", "sell_rows", "unavailable", "buy_rows", "generated_at"}`。

**实现要点：**
- symbols 为 None 时读全自选；为空列表仍写 meta 行（幂等清空语义）。
- **首个标的串行 analyze（V8 预热）**，其余 `ThreadPoolExecutor(max_workers)`（同 daily_scan.py:80-84 的规避注释）。
- 每标的：异常或结果缺 frame → unavailable 行（error 原文透传）；否则 `build_review(result, symbol=s, display_name=..., active_plan_ids=())`，verdict=="none" 跳过买点行（同 `run_opportunity_scan` 的 `only_with_candidates` 过滤），卖点行来自 `extract_sell_signals(result)`。
- 落库：一个连接里先 `upsert_scan_results(conn, day_str, buy_items)` 再 `upsert_signal_alerts(conn, day_str, AS_OF_CLOSE, sell_and_unavailable_rows)`。
- 测试通过 monkeypatch 本模块命名空间的 `analyze` 和 `build_review`（本模块 `from lei_signal.compose.pipeline import analyze`、`from lei_signal.api.routes.opportunities import build_review`，patch 目标 `lei_signal.api.signal_replay.analyze` / `...signal_replay.build_review`），不触网。

- [ ] **Step 1: 写失败测试**

```python
"""run_signal_replay 回放门禁：analyze(as_of=day) 截断、两表落库、幂等、显式不可用。

analyze 与 build_review 均 monkeypatch 本模块命名空间, 不触网。
"""
from __future__ import annotations

from contextlib import closing
from datetime import date
from types import SimpleNamespace

import pandas as pd

from lei_signal.api.opportunity_scan import list_scan
from lei_signal.api.services import AnalysisEntry  # noqa: F401  (类型参考)
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.api import signal_replay
from lei_signal.storage.sqlite_store import connect

DAY = date(2026, 8, 21)  # 周五


def _result(symbol: str = "600519.SS", *, with_exit: bool = True) -> SimpleNamespace:
    frame = pd.DataFrame(
        {"close": [10.0] * 3},
        index=pd.bdate_range("2026-08-19", periods=3),  # 最后一根 = 08-21
    )
    today = frame.index[-1].date()
    events = [SimpleNamespace(
        rule_id="exit_ema20_costbasis", available_date=today,
        reason_cn="抵扣价退出触发",
        evidence={"ema20": 10.5, "close_lag20": 10.8, "close": 10.1},
    )] if with_exit else []
    return SimpleNamespace(
        frame=frame, display_name=f"标的{symbol}", events=events,
        structures=[], history=[],
    )


def _none_review(monkeypatch) -> None:
    review = SimpleNamespace(
        verdict="none", verdict_cn="", display_name="", has_active_plan=False,
        candidates=[], resonance_groups=[], watch_conditions=[], tradability=None,
    )
    monkeypatch.setattr(signal_replay, "build_review", lambda *a, **kw: review)


def test_replay_passes_as_of_and_persists_both_tables(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    seen: dict[str, object] = {}

    def fake_analyze(symbol, *, as_of=None, **kw):
        seen[symbol] = as_of
        if symbol == "bad.SS":
            raise RuntimeError("DATA_UNAVAILABLE: 行情获取失败")
        return _result(symbol)

    monkeypatch.setattr(signal_replay, "analyze", fake_analyze)
    db = str(tmp_path / "lab.db")
    summary = signal_replay.run_signal_replay(
        db, DAY, symbols=["600519.SS", "bad.SS"], max_workers=1,
    )

    assert seen == {"600519.SS": DAY, "bad.SS": DAY}  # as_of 逐标的透传
    assert summary["scan_date"] == DAY.isoformat()
    assert summary["as_of"] == "close"
    assert summary["sell_rows"] == 1 and summary["unavailable"] == 1
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, DAY.isoformat()) == "close"
        sell = list_signal_alerts(conn, DAY.isoformat(), side=SIDE_SELL)
        assert len(sell) == 1
        assert sell[0].symbol == "600519.SS" and sell[0].kind == "exit_proxy"
        assert sell[0].is_new is True  # 相对截断后最后一根(08-21) 计算
        unavailable = list_signal_alerts(conn, DAY.isoformat(), side=SIDE_UNAVAILABLE)
        assert len(unavailable) == 1 and "DATA_UNAVAILABLE" in (unavailable[0].error or "")
        buy = list_scan(conn, DAY.isoformat())
        assert [r.symbol for r in buy] == ["bad.SS"]  # none-verdict 被过滤, 错误行保留
        assert buy[0].error and "DATA_UNAVAILABLE" in buy[0].error


def test_replay_is_idempotent_rewrite(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    monkeypatch.setattr(
        signal_replay, "analyze", lambda symbol, *, as_of=None, **kw: _result(symbol),
    )
    signal_replay.run_signal_replay(db, DAY, symbols=["600519.SS"], max_workers=1)
    # 第二轮无信号 -> 卖点/买点行整体重写清空, meta 保留
    monkeypatch.setattr(
        signal_replay, "analyze",
        lambda symbol, *, as_of=None, **kw: _result(symbol, with_exit=False),
    )
    signal_replay.run_signal_replay(db, DAY, symbols=["600519.SS"], max_workers=1)
    with closing(connect(db)) as conn:
        assert list_signal_alerts(conn, DAY.isoformat(), side=SIDE_SELL) == []
        assert list_scan(conn, DAY.isoformat()) == []
        assert get_scan_as_of(conn, DAY.isoformat()) == "close"


def test_replay_first_symbol_serial_warms_up(monkeypatch, tmp_path) -> None:
    """首标的必须串行（V8 预热），其后才进线程池：用调用序号断言首个调用发生在任何并发调用前。"""
    _none_review(monkeypatch)
    order: list[str] = []
    import threading

    monkeypatch.setattr(signal_replay, "analyze", lambda symbol, *, as_of=None, **kw: (
        order.append(symbol), _result(symbol))[-1])
    db = str(tmp_path / "lab.db")
    signal_replay.run_signal_replay(
        db, DAY, symbols=["a.SS", "b.SS", "c.SS"], max_workers=2,
    )
    assert set(order) == {"a.SS", "b.SS", "c.SS"}
    assert order[0] == "a.SS"  # 首标的先行
    assert threading.active_count() >= 1  # 无崩溃即通过


def test_replay_empty_symbols_writes_meta_only(tmp_path) -> None:
    db = str(tmp_path / "lab.db")
    summary = signal_replay.run_signal_replay(db, DAY, symbols=[], max_workers=1)
    assert summary["scanned"] == 0
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, DAY.isoformat()) == "close"
        assert list_signal_alerts(conn, DAY.isoformat(), side=SIDE_SELL) == []
        assert list_scan(conn, DAY.isoformat()) == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signal_replay.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'lei_signal.api.signal_replay'`

- [ ] **Step 3: 写实现**

```python
"""历史交易日信号回放：analyze(as_of=day) 截断行情后重跑既有规则，落两表。

设计（docs/superpowers/specs/2026-08-23-signal-replay-design.md）：
- 无前视由 pipeline.analyze 的 as_of 截断保证（pipeline.py:217-218），本模块零判定；
- 绕过 AnalysisService TTL 缓存（key 不含日期），直接调 pipeline.analyze；
- 回放不显示「已有计划」（active_plan_ids=()，计划是当下事实）；
- 写 signal_alerts + daily_opportunity_scan 两表 scan_date=day, as_of='close'，幂等重写；
- 快照优先：GET 侧有快照秒开，本模块只负责补算。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, date, datetime
from typing import Any

from lei_signal.api import config
from lei_signal.api.opportunity_scan import (
    today_date,
    upsert_scan_results,
)
from lei_signal.api.routes.opportunities import (
    VERDICT_NONE,
    build_review,
)
from lei_signal.api.sell_signals import extract_sell_signals
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    upsert_signal_alerts,
)
from lei_signal.api.signal_scan import AS_OF_CLOSE
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.compose.pipeline import analyze
from lei_signal.storage.sqlite_store import connect
```

主体实现：

```python
def _replay_one(symbol: str, day: date, db_path: str) -> tuple[ScanItemDTO | None, list[SignalAlertRow], SignalAlertRow | None]:
    """单标的回放：返回 (买点行或None, 卖点行, 不可用行或None)。"""
    try:
        result = analyze(
            symbol, as_of=day,
            cache_root=config.cache_root(), sqlite_path=db_path,
        )
    except Exception as exc:  # noqa: BLE001  单标的失败不影响整体
        return None, [], SignalAlertRow(
            scan_date=day.isoformat(), symbol=symbol, display_name=symbol,
            side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
            title="数据不可用", error=f"{type(exc).__name__}: {exc}",
        )
    if result is None or getattr(result, "frame", None) is None or len(result.frame.index) == 0:
        return None, [], SignalAlertRow(
            scan_date=day.isoformat(), symbol=symbol, display_name=symbol,
            side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
            title="数据不可用", error="分析结果为空",
        )
    display_name = getattr(result, "display_name", "") or symbol
    review = build_review(result, symbol=symbol, display_name=display_name, active_plan_ids=())
    buy: ScanItemDTO | None = None
    if review.verdict != VERDICT_NONE:
        best = review.candidates[0] if review.candidates else None
        if best is None and review.resonance_groups:
            best = review.resonance_groups[0].candidates[0]
        missing = "；".join(w.text_cn for w in review.watch_conditions[:2])
        buy = ScanItemDTO(
            symbol=symbol, display_name=review.display_name,
            verdict=review.verdict, verdict_cn=review.verdict_cn,
            best_scenario_cn=best.scenario_cn if best else None,
            best_state=best.state if best else None,
            reward_risk_ratio=best.reward_risk_ratio if best else None,
            reward_risk_computable=bool(best.reward_risk_computable) if best else False,
            blocking_reasons=(
                list(review.tradability.blocking_reasons) if review.tradability else []
            ),
            missing_summary_cn=missing, has_active_plan=False,
        )
    sell = [
        SignalAlertRow(
            scan_date=day.isoformat(), symbol=symbol, display_name=display_name,
            side=SIDE_SELL, tier=s.tier, kind=s.kind, kind_cn=s.kind_cn,
            title=s.title, reason_cn=s.reason_cn, is_new=s.is_new,
            key_prices=dict(s.key_prices), provenance=s.provenance,
            available_date=s.available_date,
        )
        for s in extract_sell_signals(result)
    ]
    return buy, sell, None


def run_signal_replay(
    db_path: str,
    day: date,
    *,
    symbols: list[str] | None = None,
    max_workers: int = 4,
) -> dict:
    """回放 day 交易日：当前自选 × 截断行情，整体重写两表。"""
    if symbols is None:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(connect(db_path)) as conn:
            symbols = [i.symbol for i in list_watchlist(conn)]
    wanted = list(symbols)
    day_str = day.isoformat()

    outcomes: dict[str, Any] = {}
    if wanted:
        # 首标的串行预热 V8（mini_racer 并发初始化会崩, 同 daily_scan.py 规避）
        outcomes[wanted[0]] = _replay_one(wanted[0], day, db_path)
        if len(wanted) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    s: pool.submit(_replay_one, s, day, db_path) for s in wanted[1:]
                }
                for s, fut in futures.items():
                    outcomes[s] = fut.result()

    buy_items: list[ScanItemDTO] = []
    sell_rows: list[SignalAlertRow] = []
    for s in wanted:
        buy, sells, unavailable = outcomes.get(s, (None, [], None))
        if unavailable is not None:
            buy_items.append(ScanItemDTO(
                symbol=s, verdict=VERDICT_NONE, verdict_cn="当前无机会",
                error=unavailable.error,
            ))
            sell_rows.append(unavailable)
            continue
        if buy is not None:
            buy_items.append(buy)
        sell_rows.extend(sells)

    with closing(connect(db_path)) as conn:
        upsert_scan_results(conn, day_str, buy_items)
        upsert_signal_alerts(conn, day_str, AS_OF_CLOSE, sell_rows)

    return {
        "scan_date": day_str,
        "as_of": AS_OF_CLOSE,
        "scanned": len(wanted),
        "buy_rows": sum(1 for it in buy_items if not it.error),
        "sell_rows": sum(1 for r in sell_rows if r.side == SIDE_SELL),
        "unavailable": sum(1 for r in sell_rows if r.side == SIDE_UNAVAILABLE),
        "generated_at": datetime.now(UTC).isoformat(),
    }


__all__ = ["run_signal_replay"]
```

（`AS_OF_CLOSE = "close"` 单一来源在 `signal_scan.py`，勿重复定义。）

- [ ] **Step 4: 跑测试确认通过**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signal_replay.py -q`
Expected: `4 passed`

- [ ] **Step 5: 全量回归 + 提交**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest -q` → 1060 passed / 1 skipped（1056+4）

```bash
cd ~/Desktop/lei-signal-lab
git add src/lei_signal/api/signal_replay.py tests/unit/test_signal_replay.py
git commit -m "feat(replay): run_signal_replay 历史交易日回放（analyze as_of 截断 + 两表幂等落库）"
```

---

### Task 2: API 路由 `GET/POST /api/signals/day/{date}`

**Files:**
- Modify: `src/lei_signal/api/schemas.py`（`SignalsTodayResponse` 加 `available: bool = True` 字段，位置在 `scanned` 之后）
- Modify: `src/lei_signal/api/routes/signals.py`（`_build_response` 参数化 + 两个新路由）
- Test: `tests/unit/test_signals_day_routes.py`

**Interfaces:**
- Consumes: Task 1 的 `run_signal_replay`；`DEFAULT_TRADING_CALENDAR.is_trading_day`（`lei_signal.data.calendar`）；既有 `_build_response / _db_path / get_scan_as_of`。
- Produces（Task 3 依赖）：
  - `GET /api/signals/day/{day}`（ISO 日期）：过去交易日 + 有快照 → 完整 `SignalsTodayResponse`；无快照 → 同结构但 `available=false, as_of=null, 各分组空`；非过去/非交易日/格式错 → 422（detail 含建议日期）。
  - `POST /api/signals/day/{day}/replay` → 校验同上，执行回放后返回完整响应。
  - `SignalsTodayResponse.available: bool`（默认 True，今日接口行为不变）。

- [ ] **Step 1: 写失败测试**

```python
"""/api/signals/day/{date} 路由门禁：快照优先、回放补算、日期校验。"""
from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import today_date
from lei_signal.api.signal_alerts_store import upsert_signal_alerts
from lei_signal.storage.sqlite_store import connect

PAST = "2026-08-21"  # 周五


def _app(tmp_path):
    app = create_app(analysis_service=SimpleNamespace())
    db = str(tmp_path / "lab.db")
    app.state.plans_db_path = db
    return app, db


def _seed_snapshot(db: str, day: str) -> None:
    with closing(connect(db)) as conn:
        upsert_signal_alerts(conn, day, "close", [])


def test_day_with_snapshot_returns_full(tmp_path) -> None:
    app, db = _app(tmp_path)
    _seed_snapshot(db, PAST)
    with TestClient(app) as client:
        resp = client.get(f"/api/signals/day/{PAST}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["scan_date"] == PAST and body["as_of"] == "close"


def test_day_without_snapshot_returns_available_false(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get(f"/api/signals/day/{PAST}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["as_of"] is None and body["sell_hard"] == []


def test_today_and_future_rejected(tmp_path) -> None:
    app, _db = _app(tmp_path)
    today = today_date()
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    with TestClient(app) as client:
        assert client.get(f"/api/signals/day/{today}").status_code == 422
        assert client.get(f"/api/signals/day/{tomorrow}").status_code == 422


def test_non_trading_day_rejects_with_suggestion(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get("/api/signals/day/2026-08-23")  # 周日
    assert resp.status_code == 422
    assert "2026-08-21" in resp.json()["detail"]


def test_bad_format_rejected(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/signals/day/20260821").status_code == 422


def test_replay_runs_and_persists(tmp_path, monkeypatch) -> None:
    app, db = _app(tmp_path)
    from lei_signal.api import signal_replay
    monkeypatch.setattr(
        signal_replay, "run_signal_replay",
        lambda db_path, day, **kw: {"scan_date": day.isoformat(), "as_of": "close",
                                    "scanned": 0, "buy_rows": 0, "sell_rows": 0,
                                    "unavailable": 0, "generated_at": "x"},
    )
    with TestClient(app) as client:
        resp = client.post(f"/api/signals/day/{PAST}/replay")
    assert resp.status_code == 200
    assert resp.json()["available"] is True
    with closing(connect(db)) as conn:
        assert conn.execute(
            "SELECT title FROM signal_alerts WHERE scan_date=? AND side='meta'", (PAST,),
        ).fetchone() is not None  # 回放落了 meta 行
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signals_day_routes.py -q`
Expected: FAIL（404，路由不存在）

- [ ] **Step 3: 实现**

`schemas.py` `SignalsTodayResponse` 的 `scanned` 字段后加：

```python
    available: bool = True
```

`routes/signals.py` 三处修改：

1. `_build_response` 签名与首行改为：

```python
def _build_response(db_path: str, scan_date: str | None = None) -> SignalsTodayResponse:
    scan_date = scan_date or today_date()
```

2. 文件末尾（`__all__` 前）追加校验函数与两个路由：

```python
def _validate_replay_day(raw: str) -> date:
    """校验回放日期：过去 + 交易日；否则 422 并给出建议。"""
    from datetime import date as date_cls, timedelta

    try:
        day = date_cls.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=422, detail="日期格式应为 YYYY-MM-DD") from None
    if day.isoformat() >= today_date():
        raise HTTPException(
            status_code=422,
            detail="只能回放过去的交易日；今天的信号请用 /api/signals/today",
        )
    from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR  # noqa: PLC0415

    if DEFAULT_TRADING_CALENDAR.is_trading_day(day):
        return day
    probe = day
    for _ in range(10):
        probe = probe - timedelta(days=1)
        if DEFAULT_TRADING_CALENDAR.is_trading_day(probe):
            raise HTTPException(
                status_code=422,
                detail=f"{raw} 非交易日，最近的过去交易日是 {probe.isoformat()}",
            )
    raise HTTPException(status_code=422, detail=f"{raw} 非交易日且往前 10 天无交易日")


@router.get("/signals/day/{day}", response_model=SignalsTodayResponse)
def day_signals(request: Request, day: str) -> SignalsTodayResponse:
    """历史交易日信号（读库快照优先）：横幅回放模式的数据源。"""
    target = _validate_replay_day(day)
    db_path = _db_path(request)
    with closing(connect(db_path)) as conn:
        if get_scan_as_of(conn, target.isoformat()) is None:
            return SignalsTodayResponse(
                scan_date=target.isoformat(), as_of=None, available=False,
            )
    return _build_response(db_path, scan_date=target.isoformat())


@router.post("/signals/day/{day}/replay", response_model=SignalsTodayResponse)
def replay_day_signals(request: Request, day: str) -> SignalsTodayResponse:
    """回放补算：当前自选 × 行情截至该日重算（无前视），整体重写该日两表。

    全自选约 30-60 秒，同步执行；幂等，重复调用整体重写。
    """
    from lei_signal.api.signal_replay import run_signal_replay  # noqa: PLC0415

    target = _validate_replay_day(day)
    db_path = _db_path(request)
    run_signal_replay(db_path, target)
    return _build_response(db_path, scan_date=target.isoformat())
```

3. `__all__` 追加 `"day_signals", "replay_day_signals"`。

（路由顺序：放在文件既有两个路由之后即可；FastAPI 路径 `/signals/day/{day}` 与 `/signals/today` 无冲突。）

- [ ] **Step 4: 跑测试确认通过**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signals_day_routes.py tests/unit/test_signals_routes.py -q`
Expected: `10 passed`（新增 6 + 既有 4 无回归）

- [ ] **Step 5: 全量回归 + 提交**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest -q` → 1066 passed / 1 skipped

```bash
cd ~/Desktop/lei-signal-lab
git add src/lei_signal/api/schemas.py src/lei_signal/api/routes/signals.py tests/unit/test_signals_day_routes.py
git commit -m "feat(replay): /api/signals/day/{date} 快照优先读 + 回放补算路由"
```

---

### Task 3: 前端横幅回放模式

**Files:**
- Modify: `web/src/types.ts`（`SignalsToday` 加 `available?: boolean`；位置在接口内 `scanned` 后）
- Modify: `web/src/api/client.ts`（`signalsToday` 附近加两个方法）
- Modify: `web/src/components/TodaySignalBanner.tsx`（回放状态机）
- Modify: `web/src/styles.css`（末尾追加回放样式）

**Interfaces:**
- Consumes: Task 2 的两个端点；现有 `SignalsToday` 类型。
- Produces: `api.signalsDay(date: string)`、`api.replayDay(date: string)`。

**WIP 纪律**：types.ts / client.ts / styles.css 含用户未提交 WIP——**提交必须用索引级拆分**（Global Constraints 的命令模板），提交后 `git diff HEAD -- <这四个文件>` 只允许出现用户 WIP hunk。TodaySignalBanner.tsx 为本功能自有文件，普通 `git add`。

- [ ] **Step 1: types.ts**（`SignalsToday` 接口 `scanned: number;` 后加）

```ts
  available?: boolean;
```

- [ ] **Step 2: client.ts**（`refreshSignals` 之后加，`SignalsToday` 已在顶部 import）

```ts
  signalsDay: (day: string) => request<SignalsToday>(`/signals/day/${day}`),
  replayDay: (day: string) =>
    request<SignalsToday>(`/signals/day/${day}/replay`, { method: "POST" }),
```

- [ ] **Step 3: TodaySignalBanner.tsx 回放状态机**

组件内新增（放在 `const [open, setOpen] = useState(false);` 之后）：

```tsx
  // 回放模式：选了过去交易日则切换数据源（红点/今日查询不受影响）
  const [replayDate, setReplayDate] = useState("");
  const isReplay = replayDate !== "";
  const dayQuery = useQuery({
    queryKey: ["signalsDay", replayDate],
    queryFn: () => api.signalsDay(replayDate),
    enabled: isReplay,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const replay = useMutation({
    mutationFn: () => api.replayDay(replayDate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["signalsDay", replayDate] });
    },
  });
  const replayError: string | null =
    isReplay && dayQuery.isError
      ? "该日期不可用（非交易日或格式错误）"
      : isReplay && replay.isError
        ? "回放计算失败，请稍后重试"
        : null;
```

展示数据源切换（放在现有 `const asOf = ...` 一组之前，并把这组派生值改为从 `active` 取）：

```tsx
  const active = isReplay ? dayQuery.data : data;
```

然后把现有 `asOf/scanned/failed/scanTime/buyA/buyW/buyB/sellH/sellWarn/sellS/unavailable/empty` 的右侧数据源全部从 `data?.` 改为 `active?.`（`failed` 改为 `(!isReplay && isError && !data) || (isReplay && dayQuery.isError && !dayQuery.data)`）。头部 JSX 改动：

```tsx
        <b>{isReplay ? `🔔 自选信号 · ${replayDate}` : "🔔 今日自选信号"}</b>
        {isReplay && <span className="sig-asof replay">回放</span>}
```

刷新按钮与日期选择区域（替换现有「刷新」按钮块）：

```tsx
        <input
          type="date"
          className="sig-date"
          value={replayDate}
          max={new Date(Date.now() - 86400_000).toISOString().slice(0, 10)}
          onChange={(e) => {
            setReplayDate(e.target.value);
            setOpen(true);
          }}
          aria-label="选择回放交易日"
        />
        {isReplay ? (
          <>
            <button
              className="btn small"
              disabled={replay.isPending || active?.available === false}
              onClick={() => replay.mutate()}
            >
              {replay.isPending ? "回放计算中…" : "回放计算"}
            </button>
            <button
              className="btn small"
              onClick={() => {
                setReplayDate("");
                setOpen(false);
              }}
            >
              回到今天
            </button>
          </>
        ) : (
          <button
            className="btn small"
            disabled={refresh.isPending}
            onClick={() => refresh.mutate()}
          >
            {refresh.isPending ? "扫描中…" : "刷新"}
          </button>
        )}
```

回放专属提示（插在展开区 `{open && scanned && (` 内部最上方）：

```tsx
          {isReplay && (
            <div className="muted sig-replay-note">
              回放口径：当前自选 × 行情截至 {replayDate} 重算，含成分前视，仅形态参考，不构成买卖建议。
            </div>
          )}
          {isReplay && active?.available === false && !replay.isPending && (
            <div className="sig-empty">
              该日无快照。点 [回放计算] 补算（约 1 分钟，算完永久保存）。
            </div>
          )}
          {replayError && (
            <div className="sig-empty" role="alert">{replayError}</div>
          )}
```

（`scanned` 判定同步改为 `asOf != null || active?.available === true`；`回放计算中…` 期间按钮 disabled。）

- [ ] **Step 4: styles.css 末尾追加**

```css
/* ---- 今日自选信号 · 历史回放 ---- */
.sig-asof.replay { background: var(--text-faint); }
.sig-date {
  background: transparent;
  color: inherit;
  border: 1px solid rgba(128, 128, 128, 0.5);
  border-radius: 4px;
  padding: 1px 4px;
  font-size: 12px;
}
.sig-replay-note { padding: 4px 0; font-size: 12px; }
```

- [ ] **Step 5: 构建验证 + 索引级拆分提交**

Run: `cd web && npm run build` → 零 TS 错误

```bash
cd ~/Desktop/lei-signal-lab
# TodaySignalBanner.tsx 普通提交; 其余三个文件先 git diff HEAD -- <file> 检查,
# 有非本任务 hunk 的用 hash-object/update-index 拆分（HEAD + 本任务改动 only）
git add web/src/components/TodaySignalBanner.tsx
# ...types.ts/client.ts/styles.css 按 Global Constraints 模板 staging ...
git commit -m "feat(replay): 横幅历史回放模式——日期选择/快照秒开/回放补算/口径声明"
git diff HEAD -- web/src/types.ts web/src/api/client.ts web/src/styles.css | grep -cE "signalsDay|replayDay|available\?|sig-date|sig-replay"  # 应为 0（全部已入提交）
```

---

### Task 4: 端到端验收（controller 执行）

- [ ] **Step 1:** `python3 -m pytest -q` 全量 + `cd web && npm run build` + ruff 新文件清零。
- [ ] **Step 2:** `biao restart-backend`，`POST /api/signals/day/2026-08-21/replay`（真实回放，计时），随后 `GET` 两次（第二次应秒回同数据）。
- [ ] **Step 3:** 浏览器验收：横幅选 2026-08-21 → 回放计算 → 展示当天信号 + 口径声明 + 「回放」徽标；回到今天数据无损；红点不变。
- [ ] **Step 4:** 验收记录追加到 `docs/superpowers/specs/2026-08-23-signal-replay-design.md`，提交 `docs(replay): 历史回放验收记录`。

---

## Self-Review 记录

- **Spec 覆盖**：§2.1 回放计算→Task 1；§2.2 API→Task 2；§3 前端→Task 3；§4 错误处理→Task 1(unavailable)/Task 2(422)/Task 3(replayError)；§5 测试→各任务；§6 验收→Task 4。§2.1 的 as_of 实现发现已回写 spec。
- **占位符**：无 TBD/TODO；Task 1 import 已修正为单一正确来源。
- **类型一致性**：`run_signal_replay(db_path, day, *, symbols, max_workers)` 与 Task 2 monkeypatch 签名一致；`available` 字段名前后端一致（`available?: boolean` ↔ `available: bool = True`）；`api.signalsDay/replayDay` 与 Task 3 使用处一致。
