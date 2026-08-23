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
        [
            {"role": "user", "content": "为啥是买点"},
            {"role": "assistant", "content": "因为结构确认"},
        ],
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
