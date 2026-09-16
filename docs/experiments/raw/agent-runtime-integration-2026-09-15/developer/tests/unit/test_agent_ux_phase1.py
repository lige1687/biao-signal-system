"""UX 第一期（2026-09-13）：降级直出四要素结构 + 下一步动作推导 + 字段贯通。

覆盖任务书场景 1/2/3/6/7 的后端可核事实：
- 模型不可用时直出仍是「现在怎么看/机会与风险/历史依据/接下来」结构，
  不出现运行编号/exact 等工程标识，无统计时如实说缺（场景 2/3）；
- next_steps ≤3、绑定原标的（draft_cn 带代码，切标的不串，场景 6）、
  无完全匹配历史时给「准备补测」（场景 4 前提）；
- 字段随普通回答/流式 done/历史消息三路下发（场景 1/8 的数据前提）。
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import lei_signal.plans.llm as llm
from lei_signal.api.app import create_app
from lei_signal.api.routes.agent import _build_next_steps, _degraded_reply
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.llm import ArkConfig

SYMBOL = "000001.SS"


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    index = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    price_data = PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info,
    )
    return analyze_bars(symbol, frame, price_data=price_data)


def _config() -> ArkConfig:
    return ArkConfig(api_key="test-only", base_url="https://example.test", model="test")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = str(tmp_path / "agent-ux.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    monkeypatch.setattr(llm, "load_ark_config", lambda: _config())
    return TestClient(app)


# ---------- _degraded_reply：模型不可用时的四要素直出 ----------

def _symbol_ctx() -> dict:
    return {
        "context_kind": "symbol",
        "display_name": "平安银行",
        "as_of": "2026-09-11",
        "assessment": {"color_cn": "绿色", "stage_cn": "阶段二",
                       "risk_state_cn": "风险升高"},
        "buy_point_review": {
            "candidates": [{"scenario_cn": "上升趋势中的回调", "state_cn": "等待触发",
                            "key_price": 10.5}],
            "tradability": {"tradable": False,
                            "blocking_reasons": ["盈亏比不足 3"]},
        },
        "volume_profile": {"poc": 10.2},
        "evidence_card": {
            "facts": {"symbol": SYMBOL, "as_of": "2026-09-11"},
            "history_and_scope": {
                "matched_runs": [
                    {"supports_question": False, "module": "B",
                     "exit_variant": "a6_1_costbasis", "run_id": "run_x",
                     "compatibility": "incompatible",
                     "differences_cn": ["模块不一致"], "summary": None},
                ],
                "winrate_evidence": {"compatibility": "unknown"},
                "note_cn": "缺同方法统计",
            },
            "pending_conditions": ["站上 20 日线", "量能回升"],
        },
    }


def test_degraded_reply_keeps_four_parts_without_engineering_codes() -> None:
    text = _degraded_reply(SYMBOL, _symbol_ctx())
    # 四件事都能读到
    assert "平安银行" in text and "000001.SS" in text
    assert "2026-09-11" in text
    assert "绿色" in text
    assert "机会" in text and "风险" in text
    assert "历史依据" in text
    assert "接下来" in text
    # 影响理解的信息可见
    assert "AI 讲解暂时不可用" in text
    # 可靠性一期：数据日期非今日时同强度说明「不能直接代表今天」
    assert "不能直接代表今天" in text
    # 不造数字：无统计时不给任何胜率数值（可说「没有可靠胜率」）
    assert not re.search(r"胜率[约为:：\s]*\d", text)
    # 工程标识不进正文（运行编号/英文枚举）
    assert "run_x" not in text
    assert "exact" not in text
    assert "a6_1_costbasis" not in text


def test_degraded_reply_leads_with_plain_answer_not_color() -> None:
    """可靠性一期（2026-09-14）：第一句是大白话回答，颜色/标签退到细节行。"""
    text = _degraded_reply(SYMBOL, _symbol_ctx())
    first_line = text.splitlines()[0]
    assert first_line.startswith("平安银行（000001.SS）：按系统数据")
    # 颜色不再出现在第一句
    assert "绿色" not in first_line


def test_degraded_reply_stale_date_vs_fresh_date() -> None:
    """数据日期是今天时不添加「过去数据」警示；不是今天时必须同强度说明。"""
    ctx = _symbol_ctx()
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    ctx["as_of"] = today
    ctx["evidence_card"] = {"facts": {"as_of": today}}
    fresh = _degraded_reply(SYMBOL, ctx)
    assert "不能直接代表今天" not in fresh
    ctx_stale = _symbol_ctx()  # as_of=2026-09-11 < 今天
    stale = _degraded_reply(SYMBOL, ctx_stale)
    assert "不能直接代表今天" in stale
    assert "先用最新数据核实" in stale


def test_degraded_reply_no_candidates_states_it_plainly() -> None:
    ctx = _symbol_ctx()
    ctx["buy_point_review"] = {"candidates": []}
    ctx["evidence_card"] = {}
    text = _degraded_reply(SYMBOL, ctx)
    assert "没有系统定义的买点候选" in text
    assert "接下来" in text


def test_degraded_reply_global_context_has_no_empty_symbol_block() -> None:
    text = _degraded_reply("", {"context_kind": "global"})
    assert "AI 讲解暂时不可用" in text
    assert "【】" not in text  # 旧版空段不得回归
    assert "标的名称或代码" in text


# ---------- _build_next_steps：≤3 个、绑定标的、来自既有事实 ----------

def test_next_steps_cap_three_and_expand_first() -> None:
    ctx = _symbol_ctx()
    ctx["buy_point_review"]["watch_conditions"] = [{"text_cn": "站上 20 日线"}]
    steps = _build_next_steps(ctx, SYMBOL)
    assert 1 <= len(steps) <= 3
    assert steps[0]["kind"] == "expand_evidence"
    kinds = [s["kind"] for s in steps]
    assert "ask_conditions" in kinds
    assert "prepare_backtest" in kinds  # 无 exact 匹配 → 建议补测


def test_next_steps_drafts_carry_symbol_against_cross_talk() -> None:
    ctx = _symbol_ctx()
    ctx["buy_point_review"]["candidates"] = [{"scenario_cn": "上升趋势中的回调"}]
    steps = _build_next_steps(ctx, "510300.SS")
    for s in steps:
        if s["kind"] in ("ask_conditions", "discuss_plan"):
            assert "510300" in (s.get("draft_cn") or ""), "动作草稿必须绑定原标的"


def test_next_steps_empty_without_symbol() -> None:
    assert _build_next_steps(_symbol_ctx(), None) == []


def test_next_steps_exact_match_suppresses_prepare_backtest() -> None:
    ctx = _symbol_ctx()
    ctx["evidence_card"]["history_and_scope"]["matched_runs"] = [
        {"supports_question": True, "module": "A", "exit_variant": "a6_1_costbasis",
         "run_id": "run_ok", "compatibility": "exact", "differences_cn": [],
         "summary": {"trade_count": 24, "win_rate": 0.58, "expectancy_r": 0.21}},
    ]
    kinds = [s["kind"] for s in _build_next_steps(ctx, SYMBOL)]
    assert "prepare_backtest" not in kinds


# ---------- 字段贯通：普通/流式/历史三路都有 next_steps ----------

def _chat(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "首段结论。\n\n其余说明。")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": SYMBOL, "message": "这个标的现在怎么看",
    })
    assert r.status_code == 200
    return r.json()


def test_chat_reply_and_history_carry_next_steps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = _chat(client, monkeypatch)
    assert isinstance(body["next_steps"], list) and body["next_steps"]
    assert body["next_steps"][0]["kind"] == "expand_evidence"
    msgs = client.get(f"/api/agent/sessions/{body['session_id']}/messages").json()
    assistant = [m for m in msgs if m["role"] == "assistant"]
    assert assistant and assistant[-1]["next_steps"] == body["next_steps"]


def test_stream_done_event_carries_next_steps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "首段结论。\n\n其余说明。")
    with client.stream("POST", "/api/agent/chat/stream", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": SYMBOL, "message": "这个标的现在怎么看",
        "client_request_id": "ux-stream-1",
    }) as r:
        assert r.status_code == 200
        done_payload = None
        for line in r.iter_lines():
            if line.startswith("event:") and "done" in line:
                continue
            if line.startswith("data:"):
                import json
                payload = json.loads(line[5:])
                if "next_steps" in payload:
                    done_payload = payload
    assert done_payload is not None
    assert done_payload["next_steps"][0]["kind"] == "expand_evidence"
