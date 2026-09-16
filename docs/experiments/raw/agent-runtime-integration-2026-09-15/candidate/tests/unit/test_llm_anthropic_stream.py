"""讨论可靠性一期（2026-09-14）：Anthropic 风格网关的讨论流式回归。

基线缺陷：`chat_discussion_stream` 对 anthropic 风格（/api/coding、/api/plan
网关）退化为一次性非流式请求，思考型模型长输入 thinking 期间无字节，
稳定触发读超时（实测 ark-code-latest 180s 超时，见
docs/experiments/agent-real-conversation-case-2026-09-14.md）。
修复后：讨论流式路径对 anthropic 风格走 SSE 增量（stream=True），
thinking 增量跳过、text 增量逐段产出。
"""
from __future__ import annotations

from typing import Any

import pytest

from lei_signal.plans import llm
from lei_signal.plans.llm import ArkConfig, STYLE_ANTHROPIC


class _FakeSSEResponse:
    """requests.Response 替身：固定 SSE 帧，记录调用参数。"""

    status_code = 200
    encoding = "iso-8859-1"
    text = ""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def __enter__(self) -> "_FakeSSEResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = True) -> list[str]:  # noqa: ARG002
        return self._lines


@pytest.fixture()
def anthropic_config() -> ArkConfig:
    return ArkConfig(
        api_key="test-only",
        base_url="https://ark.example.test/api/plan",
        model="test-model",
        style=STYLE_ANTHROPIC,
        max_tokens=16000,
        timeout=180.0,
    )


def test_discussion_stream_anthropic_uses_sse_not_blocking(
    monkeypatch: pytest.MonkeyPatch, anthropic_config: ArkConfig,
) -> None:
    """核心回归：anthropic 风格讨论流式必须 stream=True，且增量按序产出。"""
    calls: dict[str, Any] = {}

    def fake_post(url: str, *, headers: dict, json: dict,  # noqa: A002
                  stream: bool, timeout: tuple) -> _FakeSSEResponse:
        calls.update({"url": url, "body": json, "stream": stream, "timeout": timeout})
        return _FakeSSEResponse([
            'data: {"type":"message_start"}',
            "",
            'data: {"type":"content_block_start","content_block":{"type":"thinking"}}',
            'data: {"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":"思考中"}}',
            'data: {"type":"content_block_start","content_block":{"type":"text"}}',
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"第一句。"}}',
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"第二句。"}}',
            'data: {"type":"message_stop"}',
        ])

    monkeypatch.setattr(llm.requests, "post", fake_post)
    pieces = list(llm.chat_discussion_stream(
        {"payload": 1}, [], "510300 最近怎么看？", anthropic_config,
    ))
    # 流式标记与超时形态（连接 10s + 读 config.timeout）
    assert calls["stream"] is True
    assert calls["timeout"] == (10, 180.0)
    assert calls["body"]["stream"] is True
    assert calls["url"].endswith("/v1/messages")
    # system 提到顶层，messages 不含 system 角色
    assert "system" in calls["body"]
    assert all(m.get("role") != "system" for m in calls["body"]["messages"])
    # thinking 增量被跳过，text 增量逐段产出（不是一次性整段）
    assert pieces == ["第一句。", "第二句。"]


def test_discussion_stream_anthropic_non_200_ends_empty(
    monkeypatch: pytest.MonkeyPatch, anthropic_config: ArkConfig,
) -> None:
    class _FailResponse(_FakeSSEResponse):
        status_code = 500
        text = "boom"

    monkeypatch.setattr(
        llm.requests, "post",
        lambda *a, **k: _FailResponse([]),
    )
    assert list(llm.chat_discussion_stream(
        {"payload": 1}, [], "问", anthropic_config,
    )) == []


def test_discussion_stream_anthropic_network_error_yields_sentinel(
    monkeypatch: pytest.MonkeyPatch, anthropic_config: ArkConfig,
) -> None:
    """连接期失败：无正文，仅产出 STREAM_INTERRUPTED 哨兵供调用方降级。"""
    import requests as _requests

    def boom(*a: Any, **k: Any) -> None:
        raise _requests.RequestException("read timeout")

    monkeypatch.setattr(llm.requests, "post", boom)
    pieces = list(llm.chat_discussion_stream(
        {"payload": 1}, [], "问", anthropic_config,
    ))
    assert len(pieces) == 1 and isinstance(pieces[0], llm.StreamInterrupt)
    assert pieces[0].reason == "connection_interrupted"


def test_openai_stream_midway_drop_yields_interrupt_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """可靠性一期：中途断流必须产出 STREAM_INTERRUPTED 哨兵，而非静默收尾。"""
    class _DropMidResponse:
        status_code = 200
        encoding = "iso-8859-1"
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def iter_lines(self, decode_unicode: bool = True):
            yield 'data: {"choices":[{"delta":{"content":"第一段"}}]}'
            yield 'data: {"choices":[{"delta":{"content":"第二段"}}]}'
            raise llm.requests.exceptions.ChunkedEncodingError("connection dropped")

    captured: dict[str, Any] = {}

    def fake_post(url, *, headers, json, stream, timeout):  # noqa: A002
        captured["stream"] = stream
        return _DropMidResponse()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    config = ArkConfig(api_key="k", base_url="https://glm.example.test", model="m")
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", config))
    assert pieces[:2] == ["第一段", "第二段"]
    assert isinstance(pieces[-1], llm.StreamInterrupt)
    assert pieces[-1].reason == "connection_interrupted"


def test_anthropic_accumulate_wrapper_returns_none_on_interrupt(
    monkeypatch: pytest.MonkeyPatch, anthropic_config: ArkConfig,
) -> None:
    """买点路径共用生成器：中断时包装函数返回 None（保持既有降级行为）。"""

    class _DropMidResponse(_FakeSSEResponse):
        def iter_lines(self, decode_unicode: bool = True):
            yield 'data: {"type":"content_block_start","content_block":{"type":"text"}}'
            yield 'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"部分"}}'
            raise llm.requests.exceptions.ChunkedEncodingError("dropped")

    monkeypatch.setattr(
        llm.requests, "post", lambda *a, **k: _DropMidResponse([]),
    )
    body: dict[str, Any] = {"model": "m", "max_tokens": 100, "stream": True}
    assert llm._post_streaming_anthropic(
        f"{anthropic_config.base_url}/v1/messages", {}, body, anthropic_config,
    ) is None


def test_buy_point_streaming_path_still_accumulates_full_text(
    monkeypatch: pytest.MonkeyPatch, anthropic_config: ArkConfig,
) -> None:
    """既有 `_post_streaming_anthropic`（买点路径）行为不回归：仍返回整段。"""

    def fake_post(url: str, *, headers: dict, json: dict,  # noqa: A002
                  stream: bool, timeout: tuple) -> _FakeSSEResponse:
        return _FakeSSEResponse([
            'data: {"type":"content_block_start","content_block":{"type":"text"}}',
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"甲"}}',
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"乙"}}',
            'data: {"type":"message_stop"}',
        ])

    monkeypatch.setattr(llm.requests, "post", fake_post)
    body: dict[str, Any] = {"model": "m", "max_tokens": 100, "stream": True}
    text = llm._post_streaming_anthropic(
        f"{anthropic_config.base_url}/v1/messages", {}, body, anthropic_config,
    )
    assert text == "甲乙"
