"""主控复核 2026-09-15 固定补修一：流式完成契约（Anthropic/OpenAI 双协议）。

固定矩阵：正常完整流；正文后正常 EOF 但缺完成标记；服务端错误事件；
网络异常；输出额度截断。合成事件驱动，不发任何真实模型请求。
未完成判定不得依赖「Python 迭代器没抛异常」。
"""
from __future__ import annotations

from typing import Any

import pytest

from lei_signal.plans import llm
from lei_signal.plans.llm import (
    ArkConfig,
    STYLE_ANTHROPIC,
    StreamInterrupt,
)


def _anthro_config() -> ArkConfig:
    return ArkConfig(
        api_key="test-only", base_url="https://ark.example.test/api/plan",
        model="test-model", style=STYLE_ANTHROPIC,
        max_tokens=16000, timeout=180.0,
    )


def _openai_config() -> ArkConfig:
    return ArkConfig(api_key="k", base_url="https://glm.example.test", model="m")


class _FakeStreamResponse:
    def __init__(self, lines: list[str], *, status: int = 200, text: str = "") -> None:
        self._lines = lines
        self.status_code = status
        self.text = text
        self.encoding = "iso-8859-1"

    def __enter__(self) -> "_FakeStreamResponse":
        return self

    def __exit__(self, *a: Any) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = True):  # noqa: ARG002
        yield from self._lines


def _patch(monkeypatch: pytest.MonkeyPatch, response: Any) -> None:
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: response)


def _assert_pieces(pieces: list, *texts: str, reason: str | None = None) -> None:
    assert pieces[: len(texts)] == list(texts)
    if reason is None:
        assert all(isinstance(p, str) for p in pieces)
    else:
        assert isinstance(pieces[-1], StreamInterrupt)
        assert pieces[-1].reason == reason


# ---------- Anthropic 协议 ----------

ANTHRO_TEXT_BLOCKS = [
    'data: {"type":"message_start"}',
    'data: {"type":"content_block_start","content_block":{"type":"text"}}',
    'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"甲"}}',
    'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"乙"}}',
]


def test_anthropic_normal_complete_has_no_interrupt(monkeypatch) -> None:
    lines = ANTHRO_TEXT_BLOCKS + ['data: {"type":"message_stop"}']
    _patch(monkeypatch, _FakeStreamResponse(lines))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _anthro_config()))
    _assert_pieces(pieces, "甲", "乙", reason=None)


def test_anthropic_clean_eof_without_message_stop_is_incomplete(monkeypatch) -> None:
    # 主控探针场景①：连接正常关闭但无 message_stop → 不得当成完成
    _patch(monkeypatch, _FakeStreamResponse(list(ANTHRO_TEXT_BLOCKS)))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _anthro_config()))
    _assert_pieces(pieces, "甲", "乙", reason="no_completion_marker")


def test_anthropic_server_error_event_is_incomplete(monkeypatch) -> None:
    # 主控探针场景②：服务端在流内发 type=error → 不得当成完成
    lines = ANTHRO_TEXT_BLOCKS + [
        'data: {"type":"error","error":{"type":"overloaded_error","message":"overloaded"}}',
    ]
    _patch(monkeypatch, _FakeStreamResponse(lines))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _anthro_config()))
    _assert_pieces(pieces, "甲", "乙", reason="server_error_event")


def test_anthropic_network_exception_is_incomplete(monkeypatch) -> None:
    class _DropMid(_FakeStreamResponse):
        def iter_lines(self, decode_unicode: bool = True):
            yield from ANTHRO_TEXT_BLOCKS
            raise llm.requests.exceptions.ChunkedEncodingError("dropped")

    _patch(monkeypatch, _DropMid([]))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _anthro_config()))
    _assert_pieces(pieces, "甲", "乙", reason="connection_interrupted")


def test_anthropic_max_tokens_truncation_is_incomplete(monkeypatch) -> None:
    lines = ANTHRO_TEXT_BLOCKS + [
        'data: {"type":"message_delta","delta":{"stop_reason":"max_tokens","stop_sequence":null}}',
        'data: {"type":"message_stop"}',
    ]
    _patch(monkeypatch, _FakeStreamResponse(lines))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _anthro_config()))
    _assert_pieces(pieces, "甲", "乙", reason="max_tokens_truncated")
    # 买点包装函数保留原有语义：截断正文照常返回（不降级）
    body: dict[str, Any] = {"model": "m", "max_tokens": 100, "stream": True}
    text = llm._post_streaming_anthropic("https://x/v1/messages", {}, body, _anthro_config())
    assert text == "甲乙"


def test_anthropic_wrapper_returns_none_on_no_completion_marker(monkeypatch) -> None:
    _patch(monkeypatch, _FakeStreamResponse(list(ANTHRO_TEXT_BLOCKS)))
    body: dict[str, Any] = {"model": "m", "max_tokens": 100, "stream": True}
    assert llm._post_streaming_anthropic(
        "https://x/v1/messages", {}, body, _anthro_config(),
    ) is None


# ---------- OpenAI 协议 ----------

OPENAI_TEXT_LINES = [
    'data: {"choices":[{"delta":{"content":"甲"}}]}',
    'data: {"choices":[{"delta":{"content":"乙"}}]}',
]


def test_openai_normal_done_is_complete(monkeypatch) -> None:
    _patch(monkeypatch, _FakeStreamResponse(list(OPENAI_TEXT_LINES) + ["data: [DONE]"]))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config()))
    _assert_pieces(pieces, "甲", "乙", reason=None)


def test_openai_clean_eof_without_done_is_incomplete(monkeypatch) -> None:
    _patch(monkeypatch, _FakeStreamResponse(list(OPENAI_TEXT_LINES)))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config()))
    _assert_pieces(pieces, "甲", "乙", reason="no_completion_marker")


def test_openai_finish_reason_length_is_incomplete(monkeypatch) -> None:
    lines = list(OPENAI_TEXT_LINES) + [
        'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
        "data: [DONE]",
    ]
    _patch(monkeypatch, _FakeStreamResponse(lines))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config()))
    _assert_pieces(pieces, "甲", "乙", reason="max_tokens_truncated")


def test_openai_network_exception_is_incomplete(monkeypatch) -> None:
    class _DropMid(_FakeStreamResponse):
        def iter_lines(self, decode_unicode: bool = True):
            yield from OPENAI_TEXT_LINES
            raise llm.requests.exceptions.ChunkedEncodingError("dropped")

    _patch(monkeypatch, _DropMid([]))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config()))
    _assert_pieces(pieces, "甲", "乙", reason="connection_interrupted")


def test_openai_instream_error_then_eof_is_server_error(monkeypatch) -> None:
    """二轮复验遗漏一：流内 error 后连接正常关闭——原因是 server_error_event，
    不得降级成 no_completion_marker。"""
    lines = list(OPENAI_TEXT_LINES) + [
        'data: {"error":{"message":"provider failed","type":"server_error"}}',
    ]
    _patch(monkeypatch, _FakeStreamResponse(lines))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config()))
    _assert_pieces(pieces, "甲", "乙", reason="server_error_event")


def test_openai_instream_error_then_done_is_still_server_error(monkeypatch) -> None:
    """二轮复验遗漏一：错误不能被后来的结束标记洗成成功。"""
    lines = list(OPENAI_TEXT_LINES) + [
        'data: {"error":{"message":"provider failed","type":"server_error"}}',
        "data: [DONE]",
    ]
    _patch(monkeypatch, _FakeStreamResponse(lines))
    pieces = list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config()))
    _assert_pieces(pieces, "甲", "乙", reason="server_error_event")


def test_openai_non_200_ends_without_tokens(monkeypatch) -> None:
    _patch(monkeypatch, _FakeStreamResponse([], status=500, text="boom"))
    assert list(llm.chat_discussion_stream({"p": 1}, [], "问", _openai_config())) == []
