"""04B 计划确认边界（2026-09-08 总控决定）：真实 HTTP 路由 + 临时库。

修复对象：总控 p1（agent-09r-controller-review-2026-09-08）——技术 entry
计划文字齐全但 invalidation_price=None、analysis_service=None 时确认返回 200
并把 state 改为 armed。

固定验收映射：
- 缺失效价 + 服务正常/缺席 -> 均 422；store 直接调用也拒绝（validate_entry_confirm_fields）；
- 非有限值/零/负数 -> 模型层（pydantic validator）与 store 层均不能绕过；
- 完整草稿 + 服务缺席/无结果/异常 -> 503 ANALYSIS_UNAVAILABLE，state 保持 draft；
- 完整草稿 + 有效分析 + 符合原规则 -> 200 armed；重复确认 422 PLAN_NOT_DRAFT；
- 已过期 -> 409 PLAN_EXPIRED；规则集版本不符 -> 409 RULESET_VERSION_CHANGED；
  符合性硬阻断 -> 422 CONFORMANCE_HARD_BLOCK（具体原因可见）；
- holding_watch 沿自身要求确认，不因 entry 新增失效价校验被误伤。

分析服务用可注入替身；其中「确认成功」闭环使用真实现有引擎
（analyze_bars + context_from_result + 真实规则账本），非全替身。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import plans as plans_route
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.rules_config import ruleset_version
from lei_signal.plans.context import context_from_result
from lei_signal.plans.store import (
    confirm_plan,
    create_plan,
    update_draft,
    validate_entry_confirm_fields,
)
from lei_signal.research.module_backtest import module_of
from lei_signal.storage.sqlite_store import connect

CUR_RULESET = ruleset_version()


# ---------------- 可注入分析服务 ----------------

class _Entry:
    def __init__(self, result=None, error: str | None = None) -> None:
        self.result = result
        self.error = error


class StubService:
    """固定分析结果替身：正常/无结果/异常三态可注入。"""

    def __init__(self, result=None, error: str | None = None,
                 exc: Exception | None = None) -> None:
        self._result, self._error, self._exc = result, error, exc

    def get(self, symbol: str):  # noqa: ANN001
        if self._exc is not None:
            raise self._exc
        return _Entry(self._result, self._error)


def make_client(tmp_path, service) -> TestClient:  # noqa: ANN001
    app = FastAPI()
    # 与生产 create_app 同一校验错误处理器（NaN 输入的 422 可序列化）
    from lei_signal.api.app import _install_validation_error_handler

    _install_validation_error_handler(app)
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.state.analysis_service = service
    app.include_router(plans_route.router)
    return TestClient(app)


def entry_payload(**over) -> dict:  # noqa: ANN003
    base = dict(
        symbol="515880.SS", module="A", direction="long",
        ruleset_version=CUR_RULESET, reason="04B 验收",
        valid_until="2099-12-31", entry_trigger_cn="t",
        thesis_cn="t", invalidation_criteria_cn="i",
        drawdown_playbook_cn="d", take_profit_plan_cn="tp",
        stop_plan_cn="sp", invalidation_price=9.0,
    )
    base.update(over)
    return base


@pytest.fixture(scope="module")
def real_result():
    bars = pd.read_parquet(Path("tests/fixtures/kline/000001.SS.bars.parquet"))
    return analyze_bars("000001.SS", bars)


def _conforming_payload(real_result) -> dict:  # noqa: ANN001
    """按真实引擎 ctx 构造一条能过符合性的技术 entry 计划。"""
    ctx = context_from_result(real_result)
    assert ctx.tradability_tradable, "fixture 应为可交易标的，否则测试前提不成立"
    close = ctx.current_close
    opp = ctx.opportunities[0] if ctx.opportunities else None
    if opp is not None:
        direction = opp.direction
        rule_id = opp.rule_id if module_of(opp.rule_id or "") else None
        lifecycle = opp.lifecycle_id
        module = module_of(opp.rule_id or "") or "A"
    else:
        direction, rule_id, lifecycle, module = "long", None, None, "A"
    invalidation = close * 0.95 if direction == "long" else close * 1.05
    return entry_payload(
        symbol="000001.SS", module=module, direction=direction,
        entry_rule_id=rule_id, entry_lifecycle_id=lifecycle,
        invalidation_price=round(invalidation, 4),
    )


# ---------------- 1. 缺失效价：服务正常/缺席均拒绝；store 直接调用也拒绝 ----------------

def test_missing_invalidation_rejected_service_up_and_down(tmp_path) -> None:  # noqa: ANN001
    """p1 回归：文字齐全、invalidation_price=None，服务缺席/正常确认均 422。"""
    conn = connect(tmp_path / "probe.db")
    for service in (None, StubService()):
        plan = create_plan(conn, **entry_payload(invalidation_price=None))
        client = make_client(tmp_path, service)
        resp = client.post(f"/api/plans/{plan.plan_id}/confirm")
        assert resp.status_code == 422, (service, resp.status_code, resp.text)
        assert resp.json()["detail"]["code"] == "INVALIDATION_PRICE_REQUIRED"
        row = dict(conn.execute(
            "SELECT state FROM trade_plans WHERE plan_id = ?",
            (plan.plan_id,)).fetchone())
        assert row["state"] == "draft"
        conn.execute("DELETE FROM trade_plans WHERE plan_id = ?", (plan.plan_id,))
        conn.commit()
    conn.close()


def test_store_direct_confirm_rejects_missing_and_invalid(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "probe.db")
    plan = create_plan(conn, **entry_payload(invalidation_price=None))
    with pytest.raises(ValueError, match="失效价"):
        confirm_plan(conn, plan.plan_id)
    # 提供非法值：store 在 create 即拒绝
    for bad in (float("inf"), float("nan"), 0, -1.0):
        with pytest.raises(ValueError, match="invalidation_price"):
            create_plan(conn, **entry_payload(invalidation_price=bad))
    # 库内被直接写入非法值（绕过 API/store 校验）时，确认前校验仍拦
    plan3 = create_plan(conn, **entry_payload(invalidation_price=None))
    conn.execute(
        "UPDATE trade_plans SET invalidation_price = ? WHERE plan_id = ?",
        (float("inf"), plan3.plan_id))
    from lei_signal.plans.store import get_plan

    with pytest.raises(ValueError, match="正的有限数值"):
        validate_entry_confirm_fields(get_plan(conn, plan3.plan_id))
    conn.close()


# ---------------- 2. 非有限值/零/负：模型层与 store 层均不能绕过 ----------------

@pytest.mark.parametrize("lit", ["NaN", "Infinity", "-Infinity"])
def test_http_create_rejects_nonfinite_literals(tmp_path, lit) -> None:  # noqa: ANN001
    """手写/异常客户端可发 NaN/Infinity 字面量（Python json 接受）：
    模型层必须 422 拦下（经与生产同一错误处理器，响应可序列化），且不落库。"""
    client = make_client(tmp_path, StubService())
    raw = json.dumps(entry_payload()).replace(
        '"invalidation_price": 9.0', f'"invalidation_price": {lit}')
    resp = client.post("/api/plans", content=raw,
                       headers={"Content-Type": "application/json"})
    assert resp.status_code == 422, (lit, resp.status_code, resp.text[:200])
    rows = connect(tmp_path / "probe.db").execute(
        "SELECT COUNT(*) FROM trade_plans").fetchone()[0]
    assert rows == 0, "非法价格不得落库"


@pytest.mark.parametrize("bad", [0, -5.0])
def test_http_create_rejects_invalid_invalidation_price(tmp_path, bad) -> None:  # noqa: ANN001
    client = make_client(tmp_path, StubService())
    resp = client.post("/api/plans", json=entry_payload(invalidation_price=bad))
    assert resp.status_code == 422, (bad, resp.status_code, resp.text)
    rows = connect(tmp_path / "probe.db").execute(
        "SELECT COUNT(*) FROM trade_plans").fetchone()[0]
    assert rows == 0, "非法价格不得落库"


def test_http_draft_update_rejects_invalid_invalidation_price(tmp_path) -> None:  # noqa: ANN001
    client = make_client(tmp_path, StubService())
    resp = client.post("/api/plans", json=entry_payload())
    assert resp.status_code == 201
    plan_id = resp.json()["plan_id"]
    for bad in (0, -1.0):
        r = client.put(f"/api/plans/{plan_id}/draft",
                       json={"invalidation_price": bad})
        assert r.status_code == 422, (bad, r.status_code)
    # NaN 字面量经原始 JSON 到达时同样被模型层拦截
    r = client.put(f"/api/plans/{plan_id}/draft",
                   content='{"invalidation_price": NaN}',
                   headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.status_code
    # 传 null（清空）仍然合法：草稿允许信息不全
    r = client.put(f"/api/plans/{plan_id}/draft",
                   json={"invalidation_price": None})
    assert r.status_code == 200, r.text
    conn = connect(tmp_path / "probe.db")
    with pytest.raises(ValueError, match="正的有限数值"):
        update_draft(conn, plan_id, {"invalidation_price": -1.0})
    conn.close()


def test_store_create_rejects_invalid_price(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "probe.db")
    for bad in (0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="invalidation_price"):
            create_plan(conn, **entry_payload(invalidation_price=bad))
    conn.close()


# ---------------- 3. 完整草稿 + 分析不可用：503，保持草稿 ----------------

def test_analysis_unavailable_keeps_draft(tmp_path) -> None:  # noqa: ANN001
    cases = (
        StubService(),
        StubService(error="行情源超时"),
        StubService(exc=RuntimeError("boom")),
    )
    for service in cases:
        client = make_client(tmp_path, service)
        plan_id = client.post("/api/plans", json=entry_payload()).json()["plan_id"]
        resp = client.post(f"/api/plans/{plan_id}/confirm")
        assert resp.status_code == 503, (resp.status_code, resp.text)
        body = resp.json()["detail"]
        assert body["code"] == "ANALYSIS_UNAVAILABLE"
        assert "暂时无法核实" in body["message"]
        conn = connect(tmp_path / "probe.db")
        row = dict(conn.execute(
            "SELECT state FROM trade_plans WHERE plan_id = ?",
            (plan_id,)).fetchone())
        conn.close()
        assert row["state"] == "draft", "分析不可用不得改变计划状态"
        conn2 = connect(tmp_path / "probe.db")
        n = conn2.execute(
            "SELECT COUNT(*) FROM trade_plans WHERE state='armed'").fetchone()[0]
        conn2.close()
        assert n == 0, "不写成功确认事件"


# ---------------- 4. 完整草稿 + 有效分析 + 符合原规则：确认成功；重复不重复确认 ----------------

def test_confirm_success_then_repeat_rejected(tmp_path, real_result) -> None:  # noqa: ANN001
    client = make_client(tmp_path, StubService(result=real_result))
    payload = _conforming_payload(real_result)
    resp = client.post("/api/plans", json=payload)
    assert resp.status_code == 201, resp.text
    plan_id = resp.json()["plan_id"]
    ok = client.post(f"/api/plans/{plan_id}/confirm")
    assert ok.status_code == 200, ok.text
    assert ok.json()["state"] == "armed"
    # 重复点击：不重复确认
    again = client.post(f"/api/plans/{plan_id}/confirm")
    assert again.status_code == 422
    assert again.json()["detail"]["code"] == "PLAN_NOT_DRAFT"
    conn = connect(tmp_path / "probe.db")
    rows = conn.execute(
        "SELECT COUNT(*) FROM trade_plans WHERE state='armed'").fetchone()[0]
    conn.close()
    assert rows == 1


# ---------------- 5. 过期 / 版本不符 / 符合性硬阻断：具体原因可见 ----------------

def test_expired_rejected_with_reason(tmp_path, real_result) -> None:  # noqa: ANN001
    client = make_client(tmp_path, StubService(result=real_result))
    plan_id = client.post(
        "/api/plans", json=entry_payload(valid_until="2020-01-01"),
    ).json()["plan_id"]
    resp = client.post(f"/api/plans/{plan_id}/confirm")
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "PLAN_EXPIRED"


def test_ruleset_version_conflict_rejected(tmp_path, real_result) -> None:  # noqa: ANN001
    client = make_client(tmp_path, StubService(result=real_result))
    plan_id = client.post(
        "/api/plans", json=entry_payload(ruleset_version="0.0.1"),
    ).json()["plan_id"]
    resp = client.post(f"/api/plans/{plan_id}/confirm")
    assert resp.status_code == 409, resp.text
    body = resp.json()["detail"]
    assert body["code"] == "RULESET_VERSION_CHANGED"
    assert "0.0.1" in body["message"]


def test_conformance_hard_block_visible(tmp_path, real_result) -> None:  # noqa: ANN001
    """失效价已被当前价击穿（long 时失效价高于现价）-> 422 + 硬阻断明细。"""
    ctx = context_from_result(real_result)
    close = ctx.current_close
    assert ctx.tradability_tradable
    client = make_client(tmp_path, StubService(result=real_result))
    plan_id = client.post(
        "/api/plans",
        json=entry_payload(symbol="000001.SS", direction="long",
                           invalidation_price=round(close * 1.05, 4)),
    ).json()["plan_id"]
    resp = client.post(f"/api/plans/{plan_id}/confirm")
    assert resp.status_code == 422, resp.text
    body = resp.json()["detail"]
    assert body["code"] == "CONFORMANCE_HARD_BLOCK"
    codes = {i["code"] for i in body["hard_issues"]}
    assert "INVALIDATION_ALREADY_BREACHED" in codes


# ---------------- 6. holding_watch 沿自身要求，不被 entry 新校验误伤 ----------------

def test_holding_watch_still_confirmable(tmp_path, real_result) -> None:  # noqa: ANN001
    ctx = context_from_result(real_result)
    close = ctx.current_close
    client = make_client(tmp_path, StubService(result=real_result))
    resp = client.post("/api/plans/holding-watch", json={
        "symbol": "000001.SS", "module": "A", "direction": "long",
        "ruleset_version": CUR_RULESET, "reason": "盯盘",
        "valid_until": "2099-12-31",
        "take_profit_plan_cn": "到减仓位分批", "stop_plan_cn": "收盘破位出",
        "take_profit_price": round(close * 1.10, 4),
        "stop_price": round(close * 0.90, 4),
    })
    assert resp.status_code == 201, resp.text
    plan_id = resp.json()["plan_id"]
    ok = client.post(f"/api/plans/{plan_id}/confirm")
    assert ok.status_code == 200, ok.text
    assert ok.json()["state"] == "entered"
    assert ok.json()["invalidation_price"] is None  # 不要求 entry 失效价
