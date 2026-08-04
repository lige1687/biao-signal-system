"""ark 表达层门禁：上下文裁剪 / 无凭据降级 / 失败降级 / 接地校验（全 mock，不打真网络）。"""
from __future__ import annotations

import json
from unittest.mock import patch

from lei_signal.plans.grounding import (
    FORBIDDEN_TERMS,
    RESEARCH_PROXY_MARKER,
    render_alerts,
    template_render,
    verify_grounding,
)
from lei_signal.plans.llm import (
    ENV_API_KEY,
    ArkConfig,
    build_context_payload,
    call_ark,
    load_ark_config,
    make_ark_renderer,
)
from lei_signal.plans.models import PLAN_ARMED, ActionItem, TradePlan
from lei_signal.plans.monitor import MonitorContext, OpportunityRef, evaluate_plan

RULESET = "1.3.0"


def _plan() -> TradePlan:
    return TradePlan(
        plan_id="p1", symbol="000001.SS", module="A", direction="long",
        entry_rule_id="first_ma_pullback", entry_lifecycle_id="lc1",
        entry_trigger_cn="站回 SMA20", entry_price_ref=3800.0, invalidation_price=3900.0,
        target_b_price=4200.0, target_b_source="swing_high", reward_risk_at_plan=3.5,
        valid_until="2026-12-31", state=PLAN_ARMED, ruleset_version=RULESET, reason="x",
        thesis_cn="冲多头回调", invalidation_criteria_cn="跌破失效价",
        drawdown_playbook_cn="回踩 SMA60 正常", take_profit_plan_cn="到 B 分批",
        stop_plan_cn="破失效价次日开盘出",
    )


def _alerts() -> list:
    ctx = MonitorContext(
        last_bar_date="2026-08-04", cache_fallback_used=False, current_close=3820.0,
        ema20=3800.0, tradability_tradable=True, ruleset_version=RULESET,
        opportunities=(
            OpportunityRef("lc1", True, "confirmed", "first_ma_pullback", 3.5, True, "long"),
        ),
    )
    return evaluate_plan(_plan(), ctx)


# ---------------------------------------------------------------- 上下文裁剪


def test_context_payload_only_has_four_blocks() -> None:
    """规格 §7.2：只喂 plan / alerts / action_items / context_min。"""
    items = [ActionItem(
        action_id="a1", plan_id="p1", kind="ENTER", source_alert_code="ENTRY_CONDITIONS_MET",
        state="open", due_from="2026-08-05", nag_count=2,
    )]
    payload = build_context_payload(
        _alerts(), plan=_plan(), action_items=items,
        context_min={"last_bar_date": "2026-08-04", "provider": "fixture"},
    )
    assert set(payload) <= {"plan", "alerts", "action_items", "context_min", "frozen_playbook"}
    # 不得包含大块 DTO 字段
    serialized = json.dumps(payload, ensure_ascii=False)
    for banned in ("chart", "concepts", "scenario_backtests", "recent_events"):
        assert banned not in serialized, f"上下文不应包含 {banned}"


def test_context_payload_excludes_closed_action_items() -> None:
    items = [
        ActionItem(action_id="a1", plan_id="p1", kind="ENTER", source_alert_code="C",
                   state="done", due_from="2026-08-05"),
        ActionItem(action_id="a2", plan_id="p1", kind="REVIEW", source_alert_code="C",
                   state="open", due_from="2026-08-05"),
    ]
    payload = build_context_payload(_alerts(), plan=_plan(), action_items=items)
    kinds = [i["kind"] for i in payload["action_items"]]
    assert kinds == ["REVIEW"]  # done 的不喂


def test_context_payload_carries_two_layer_provenance() -> None:
    """两层标注必须进上下文，否则 LLM 无从复述。"""
    payload = build_context_payload(_alerts(), plan=_plan())
    breached = [a for a in payload["alerts"] if a["code"] == "INVALIDATION_BREACHED"]
    assert breached
    assert breached[0]["principle_source"] == "规格 §14 原文"
    assert breached[0]["logic_provenance"] == "research_proxy"


# ---------------------------------------------------------------- 配置与降级


def test_load_ark_config_returns_none_without_key(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    assert load_ark_config() is None


def test_make_ark_renderer_returns_none_without_key(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    assert make_ark_renderer(plan=_plan()) is None


def test_render_alerts_uses_template_when_no_renderer() -> None:
    """无凭据 -> renderer 为 None -> 直接模板，不做无意义重试。"""
    alerts = _alerts()
    out = render_alerts(alerts, plan=_plan(), llm_render=None)
    assert out == template_render(alerts, plan=_plan())


# ---------------------------------------------------------------- call_ark（mock）


class _Resp:
    def __init__(self, status: int, payload: dict) -> None:
        self.status_code = status
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_call_ark_success() -> None:
    payload = {"choices": [{"message": {"content": "讲解文本"}}]}
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(200, payload)) as post:
        text = call_ark({"alerts": []}, ArkConfig(api_key="k", model="m"))
    assert text == "讲解文本"
    # 校验请求构造：Bearer 头 + chat/completions
    _, kwargs = post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer k"
    assert kwargs["json"]["model"] == "m"


def test_call_ark_non_200_returns_none() -> None:
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(500, {})):
        assert call_ark({}, ArkConfig(api_key="k")) is None


def test_call_ark_network_error_returns_none() -> None:
    import requests as _requests
    with patch("lei_signal.plans.llm.requests.post",
               side_effect=_requests.ConnectionError("boom")):
        assert call_ark({}, ArkConfig(api_key="k")) is None


def test_call_ark_empty_choices_returns_none() -> None:
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(200, {"choices": []})):
        assert call_ark({}, ArkConfig(api_key="k")) is None


# ---------------------------------------------------------------- 端到端（mock ark）


def test_ark_renderer_output_passing_grounding_is_used() -> None:
    """LLM 输出合规 -> 采用其输出。"""
    alerts = _alerts()
    allowed = {a.rule_id for a in alerts if a.rule_id}
    good = "提醒：条件成立 [rule_id:" + sorted(allowed)[0] + " | 证据:x=1]"
    payload = {"choices": [{"message": {"content": good}}]}
    renderer = make_ark_renderer(plan=_plan(), config=ArkConfig(api_key="k"))
    assert renderer is not None
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(200, payload)):
        out = render_alerts(alerts, plan=_plan(), llm_render=renderer)
    assert out == good


def test_ark_renderer_forbidden_term_falls_back_to_template() -> None:
    """LLM 输出含禁用词 -> 两次都拒 -> 降级模板。"""
    alerts = _alerts()
    bad = "建议买入该标的"
    payload = {"choices": [{"message": {"content": bad}}]}
    renderer = make_ark_renderer(plan=_plan(), config=ArkConfig(api_key="k"))
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(200, payload)):
        out = render_alerts(alerts, plan=_plan(), llm_render=renderer)
    assert out == template_render(alerts, plan=_plan())
    assert all(t not in out for t in FORBIDDEN_TERMS)


def test_ark_renderer_fake_rule_id_falls_back_to_template() -> None:
    """LLM 编造 rule_id -> 超集 -> 降级模板。"""
    alerts = _alerts()
    payload = {"choices": [{"message": {"content": "见 [rule_id:made_up_rule]"}}]}
    renderer = make_ark_renderer(plan=_plan(), config=ArkConfig(api_key="k"))
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(200, payload)):
        out = render_alerts(alerts, plan=_plan(), llm_render=renderer)
    assert out == template_render(alerts, plan=_plan())


def test_ark_unavailable_falls_back_to_template() -> None:
    """ark 宕机（call_ark 返回 None -> renderer 抛错）-> 降级模板，不抛给用户。"""
    alerts = _alerts()
    renderer = make_ark_renderer(plan=_plan(), config=ArkConfig(api_key="k"))
    with patch("lei_signal.plans.llm.requests.post", return_value=_Resp(503, {})):
        out = render_alerts(alerts, plan=_plan(), llm_render=renderer)
    assert out == template_render(alerts, plan=_plan())
    # 降级输出仍带两层标注
    assert RESEARCH_PROXY_MARKER in out
    ok, _ = verify_grounding(out, {a.rule_id for a in alerts if a.rule_id})
    assert ok
