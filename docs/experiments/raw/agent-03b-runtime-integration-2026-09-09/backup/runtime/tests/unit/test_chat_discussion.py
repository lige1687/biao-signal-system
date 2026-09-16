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


# ---- Fix 终审 FR-2：溯源禁令 + 用户数字回显纪律写进铁律 9 ----


def _condensed(prompt: str) -> str:
    """压掉换行与缩进后再断言：铁律文本有手工换行，逐字断言须跨行不敏感。"""
    return "".join(prompt.split())


def test_prompt_forbids_rule_id_and_research_proxy_markers():
    """FR-2: 铁律 9 —— 正文不得出现 rule_id 字样与研究代理标注字样。"""
    p = _condensed(DISCUSSION_SYSTEM_PROMPT)
    assert "不得出现rule_id字样与研究代理标注字样" in p
    assert "溯源信息由系统在别处呈现" in p


def test_prompt_requires_user_number_echo_discipline():
    """FR-2/M-8: 回显用户数字必须冠以用户来源并连接系统位，不得说成系统位。"""
    p = _condensed(DISCUSSION_SYSTEM_PROMPT)
    assert "必须冠以用户来源" in p
    assert "你提到的8700" in p
    assert "给出偏差百分比" in p
    assert "不得把用户数字说成系统位" in p
