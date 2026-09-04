"""GLM 供应商分支与 chat_copilot 传输层。"""
from __future__ import annotations

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

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        calls["url"] = url
        calls["body"] = json

        class R:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "讲解文本"}}]}

        return R()

    monkeypatch.setattr(plans_llm.requests, "post", fake_post)
    cfg = ArkConfig(
        api_key="k", base_url="https://x/api/paas/v4",
        model="glm-4.6", style=STYLE_OPENAI,
    )
    out = plans_llm.chat_copilot({"a": 1}, "今天看什么？", cfg, system_prompt="SP")
    assert out == "讲解文本"
    assert calls["url"] == "https://x/api/paas/v4/chat/completions"
    msgs = calls["body"]["messages"]
    assert msgs[0] == {"role": "system", "content": "SP"}
    assert "今天看什么？" in msgs[1]["content"] and '"a": 1' in msgs[1]["content"]


def test_chat_copilot_failure_returns_none(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        raise plans_llm.requests.RequestException("boom")

    monkeypatch.setattr(plans_llm.requests, "post", fake_post)
    cfg = ArkConfig(api_key="k", style=STYLE_OPENAI)
    assert plans_llm.chat_copilot({}, "q", cfg, system_prompt="SP") is None
