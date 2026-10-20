"""计划流程任务 P1/P3 后端验收（2026-09-13）。

- 版本端点 /plans/ruleset-version 返回服务端权威 rules_config 版本；
- 新建后版本变化 → confirm 409 RULESET_VERSION_CHANGED 且 state 保持 draft；
- P3：suggested_plan 只取规则可映射到 A/B/C/D 且与候选模块一致的合法候选；
  仅有不可映射早期信号时不给预填（待补）。

合成输入，无真实行情/模型；进程退出码反映断言结果。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import lei_signal.domain.rules_config as rules_config
from lei_signal.api.app import create_app
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars

SYMBOL = "000001.SS"


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 0.4,
                     "low": close - 0.5, "close": close, "volume": 1_000_000})
    index = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = str(tmp_path / "plan-flow.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    return TestClient(app)


def test_ruleset_version_endpoint_matches_authority(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rules_config, "ruleset_version", lambda: "9.9.9-test")
    r = client.get("/api/plans/ruleset-version")
    assert r.status_code == 200
    assert r.json() == {"ruleset_version": "9.9.9-test"}


def _create(client: TestClient, version: str) -> dict:
    r = client.post("/api/plans", json={
        "symbol": SYMBOL, "module": "A", "direction": "long",
        "ruleset_version": version, "reason": "P1 验收",
        "entry_rule_id": "first_ma_pullback", "entry_trigger_cn": "测试触发",
        "invalidation_price": 95.0, "valid_until": "2099-12-31",
        "thesis_cn": "测试假设", "invalidation_criteria_cn": "跌破 95",
        "drawdown_playbook_cn": "回踩 SMA60", "take_profit_plan_cn": "分批止盈",
        "stop_plan_cn": "结构止损", "target_b_price": 115.0,
        # 详情页表单路径：非讨论式保存（无编号/无来源字段）
        "source_session_id": None, "source_question_id": None,
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_confirm_rejects_after_version_change_and_keeps_draft(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rules_config, "ruleset_version", lambda: "2.1.0")
    plan = _create(client, "2.1.0")
    pid = plan["plan_id"]
    assert plan["state"] == "draft"

    # 新建后规则版本变化：确认必须 409（不是放行、也不是 422 语义）
    monkeypatch.setattr(rules_config, "ruleset_version", lambda: "3.0.0")
    r = client.post(f"/api/plans/{pid}/confirm")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "RULESET_VERSION_CHANGED"

    # draft 不变，草稿保留
    after = client.get(f"/api/plans/{pid}").json()
    assert after["state"] == "draft"
    assert after["ruleset_version"] == "2.1.0"  # 旧草稿不被静默重标

    # 版本恢复一致后再确认：不再报版本 409（版本门已过；此 fixture 上下文
    # 不可交易，落在既有 422 符合性硬阻断——属正确边界，非版本问题）
    monkeypatch.setattr(rules_config, "ruleset_version", lambda: "2.1.0")
    ok = client.post(f"/api/plans/{pid}/confirm")
    assert ok.status_code == 422
    assert ok.json()["detail"]["code"] == "CONFORMANCE_HARD_BLOCK"
    assert client.get(f"/api/plans/{pid}").json()["state"] == "draft"


# ---------- P3：suggested_plan 只用可映射合法候选 ----------

def _candidate(rule_id: str | None, module: str | None, state: str = "confirmed") -> dict:
    return {
        "rule_id": rule_id, "module": module, "direction": "long",
        "state": state, "scenario_cn": f"候选 {rule_id}",
        "first_seen": "2026-08-01", "last_seen": "2026-08-06",
        "key_price": 100.0, "invalidation_price": 95.0,
        "reward_risk_ratio": 3.0, "reward_risk_target": 115.0,
        "reward_risk_target_source_cn": "测试", "lifecycle_id": "lc-test",
        "recency": "recent", "condition_states": {},
    }


def _review_payload(candidates: list[dict], verdict: str = "actionable") -> dict:
    return {
        "symbol": SYMBOL, "display_name": SYMBOL, "as_of": "2026-08-06",
        "assessment": {"color": "green", "stage": "stage3", "risk_state": "neutral"},
        "last_close": 100.0, "verdict": verdict,
        "verdict_cn": "条件已成立" if verdict == "actionable" else "等待",
        "summary_cn": "测试", "tradability": {"tradable": True, "blocking_reasons": []},
        "candidates": candidates, "resonance_groups": [],
        "historical_structures": [], "watch_conditions": [],
        "has_active_plan": False, "active_plan_ids": [],
        "disclaimer_cn": "测试",
    }


def test_p3_suggested_uses_only_mappable_candidate() -> None:
    """P3：确认候选里混有不可映射早期信号（如 ema20_reclaim_rising，模块
    自报 A）时，预填必须跳过它取真正可映射的合法候选；仅有不可映射候选时
    返回 None（不给预填，转待补）。不得因 module or 'A' 兜底冒充完整计划。"""
    from types import SimpleNamespace

    from lei_signal.api.routes.opportunities import _legal_entry_candidate
    from lei_signal.research.module_backtest import MODULE_MAP

    assert "ema20_reclaim_rising" not in MODULE_MAP, "早期转强信号不应进模块映射"
    bad = SimpleNamespace(rule_id="ema20_reclaim_rising", module="A")
    good = SimpleNamespace(rule_id="two_b_reversal", module="C")
    # 坏候选在前：按原顺序取到的是第一个**合法**候选
    assert _legal_entry_candidate([bad, good]) is good
    assert _legal_entry_candidate([bad]) is None
    assert _legal_entry_candidate([]) is None
    # 规则可映射但与候选自报模块不一致 → 不合法（防串模块）
    mismatched = SimpleNamespace(rule_id="two_b_reversal", module="A")
    assert _legal_entry_candidate([mismatched]) is None
    # 映射模块兜底：候选模块缺失但规则可映射 → 合法（同一候选取值）
    no_module = SimpleNamespace(rule_id="first_ma_pullback", module=None)
    assert _legal_entry_candidate([no_module]) is no_module
