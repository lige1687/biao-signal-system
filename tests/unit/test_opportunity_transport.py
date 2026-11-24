"""The opportunity transport is exercised without network calls or private data."""

from __future__ import annotations

import json

import requests

from lei_signal.copilot import opportunity_transport as transport
from lei_signal.plans.llm import STYLE_ANTHROPIC, STYLE_OPENAI, ArkConfig


class FakeResponse:
    def __init__(self, status=200, events=(), text="", body=None, chunks=None):
        self.status_code = status
        self.events = events
        self.text = text
        self.body = body
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_lines(self, **_kwargs):
        for event in self.events:
            if isinstance(event, Exception):
                raise event
            if event == "[DONE]":
                yield "data: [DONE]"
            else:
                yield "data: " + json.dumps(event)

    def iter_content(self, **_kwargs):
        if self.chunks is not None:
            for chunk in self.chunks:
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk
        elif self.body is not None:
            yield self.body if isinstance(self.body, bytes) else json.dumps(self.body).encode()


def anthropic_config():
    return ArkConfig(api_key="test-secret", base_url="https://api.deepseek.com/anthropic",
                     model="deepseek-v4-pro[1m]", style=STYLE_ANTHROPIC,
                     max_tokens=16000, timeout=180)


def openai_config():
    return ArkConfig(api_key="test-secret", base_url="https://api.deepseek.com",
                     model="deepseek-v4-pro[1m]", style=STYLE_OPENAI)


def generic_anthropic_config():
    return ArkConfig(api_key="test-secret", base_url="https://example.com/anthropic",
                     model="existing-model", style=STYLE_ANTHROPIC)


def anthropic_message(text='{"reviews":[]} ', *, stop="end_turn"):
    return {"type": "message", "content": [{"type": "text", "text": text}],
            "stop_reason": stop, "usage": {"input_tokens": 12, "output_tokens": 8}}


def anthropic_events(text='{"reviews":[]} ', *, stop="end_turn"):
    return [
        {"type": "message_start", "message": {"usage": {"input_tokens": 12}}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}},
        {"type": "message_delta", "delta": {"stop_reason": stop},
         "usage": {"output_tokens": 8}},
        {"type": "message_stop"},
    ]


def test_deepseek_anthropic_uses_proven_nonstreaming_request_and_bounded_read(monkeypatch):
    captured = []

    def post(url, **kwargs):
        captured.append((url, kwargs))
        return FakeResponse(body=anthropic_message())

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("evidence IDs only", system_prompt="select IDs",
                                  config=anthropic_config())
    assert result["text"] == '{"reviews":[]}'
    assert result["error_code"] == ""
    assert result["attempts"] == 1
    assert result["usage"] == {"input_tokens": 12, "output_tokens": 8}
    assert result["finish_reason"] == "end_turn"
    assert result["phase"] == "complete"
    assert result["elapsed_ms"] >= 0
    url, kwargs = captured[0]
    assert url == "https://api.deepseek.com/anthropic/v1/messages"
    assert kwargs["json"]["model"] == "deepseek-v4-pro[1m]"
    assert kwargs["json"]["thinking"] == {"type": "disabled"}
    assert "reasoning" not in kwargs["json"]
    assert kwargs["json"]["max_tokens"] == 4096
    assert kwargs["json"]["stream"] is False
    assert kwargs["stream"] is True
    assert kwargs["timeout"] == (10.0, 65.0)


def test_deepseek_nonstreaming_read_timeout_respects_short_attempt_budget(monkeypatch):
    captured = []

    def post(*_args, **kwargs):
        captured.append(kwargs)
        return FakeResponse(body=anthropic_message())

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport._single_call("prompt", "system", anthropic_config(), 8.0)
    assert result["text"] == '{"reviews":[]}'
    assert captured[0]["timeout"] == (7.0, 1.0)


def test_timeout_retries_once_and_reports_failure(monkeypatch):
    calls = []

    def post(*_args, **_kwargs):
        calls.append(1)
        raise requests.ReadTimeout("secret-bearing upstream details")

    monkeypatch.setattr(transport.requests, "post", post)
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert len(calls) == 2
    assert result["text"] is None
    assert result["error_code"] == "timeout"
    assert result["retryable"] is True
    assert result["attempts"] == 2
    assert "secret" not in str(result)


def test_empty_200_is_terminal(monkeypatch):
    calls = []

    def post(*_args, **_kwargs):
        calls.append(1)
        return FakeResponse(body=anthropic_message(""))

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "empty_content"
    assert result["attempts"] == len(calls) == 1
    assert result["usage"]["output_tokens"] == 8
    assert result["phase"] == "body"


def test_auth_error_does_not_retry_or_read_body(monkeypatch):
    calls = []

    def post(*_args, **_kwargs):
        calls.append(1)
        return FakeResponse(status=401, text="private response and token")

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "auth_error"
    assert result["retryable"] is False
    assert len(calls) == 1
    assert result["phase"] == "headers"
    assert "private" not in str(result)
    assert "token" not in str(result)
    assert result["http_status"] == 401


def test_insufficient_balance_records_status_without_body_or_retry(monkeypatch):
    calls = []

    def post(*_args, **_kwargs):
        calls.append(1)
        return FakeResponse(status=402, text="private response and token")

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "insufficient_balance"
    assert result["http_status"] == 402
    assert result["attempts"] == len(calls) == 1
    assert "private" not in str(result) and "token" not in str(result)


def test_429_retries_once_then_succeeds(monkeypatch):
    responses = iter([FakeResponse(status=429), FakeResponse(body=anthropic_message())])
    monkeypatch.setattr(transport.requests, "post", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == ""
    assert result["attempts"] == 2


def test_provider_500_retries_once(monkeypatch):
    calls = []

    def post(*_args, **_kwargs):
        calls.append(1)
        return FakeResponse(status=503)

    monkeypatch.setattr(transport.requests, "post", post)
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "provider_error"
    assert result["retryable"] is True
    assert result["attempts"] == len(calls) == 2


def test_truncated_response_rejected_even_with_partial_text(monkeypatch):
    partial = anthropic_message('{"reviews":[', stop="max_tokens")
    monkeypatch.setattr(
        transport.requests, "post",
        lambda *_args, **_kwargs: FakeResponse(body=partial),
    )
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["text"] is None
    assert result["error_code"] == "truncated"
    assert result["finish_reason"] == "max_tokens"
    assert result["attempts"] == 1


def test_stream_error_does_not_expose_event_body(monkeypatch):
    event = {"type": "error", "error": {"type": "invalid_request_error",
                                         "message": "private event body"}}
    monkeypatch.setattr(transport.requests, "post",
                        lambda *_args, **_kwargs: FakeResponse(events=[event]))
    result = transport.call_model("prompt", system_prompt="system",
                                  config=generic_anthropic_config())
    assert result["error_code"] == "stream_error"
    assert result["retryable"] is False
    assert "private" not in str(result)


def test_missing_completion_marker_is_not_success(monkeypatch):
    monkeypatch.setattr(transport.requests, "post",
                        lambda *_args, **_kwargs: FakeResponse(events=anthropic_events()[:-1]))
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    result = transport.call_model("prompt", system_prompt="system",
                                  config=generic_anthropic_config())
    assert result["text"] is None
    assert result["error_code"] == "stream_incomplete"
    assert result["attempts"] == 2


def test_read_timeout_wrapped_as_connection_error_keeps_header_phase(monkeypatch):
    chunks = [requests.ConnectionError("Read timed out.")]
    monkeypatch.setattr(transport.requests, "post",
                        lambda *_args, **_kwargs: FakeResponse(chunks=chunks))
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "timeout"
    assert result["phase"] == "headers"
    assert result["attempts"] == 2


def test_generic_anthropic_stays_streaming(monkeypatch):
    captured = []

    def post(*_args, **kwargs):
        captured.append(kwargs)
        return FakeResponse(events=anthropic_events())

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system",
                                  config=generic_anthropic_config())
    assert result["text"] == '{"reviews":[]}'
    assert captured[0]["json"]["stream"] is True
    assert "thinking" not in captured[0]["json"]
    assert "reasoning" not in captured[0]["json"]


def test_deepseek_nonstreaming_invalid_json_is_terminal_and_private(monkeypatch):
    calls = []

    def post(*_args, **_kwargs):
        calls.append(1)
        return FakeResponse(body=b'{"content": [private source text')

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "invalid_response"
    assert result["attempts"] == len(calls) == 1
    assert "private" not in str(result)


def test_deepseek_nonstreaming_rejects_invalid_text_block(monkeypatch):
    malformed = anthropic_message()
    malformed["content"][0]["text"] = {"private": "source"}
    monkeypatch.setattr(transport.requests, "post",
                        lambda *_args, **_kwargs: FakeResponse(body=malformed))
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "invalid_response"
    assert "private" not in str(result)


def test_deepseek_nonstreaming_body_size_limit(monkeypatch):
    monkeypatch.setattr(transport.requests, "post",
                        lambda *_args, **_kwargs: FakeResponse(
                            chunks=[b'x' * (transport._MAX_TEXT_CHARS + 1)]))
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["error_code"] == "output_too_large"
    assert result["attempts"] == 1


def test_openai_compatible_stream(monkeypatch):
    events = [
        {"choices": [{"delta": {"content": '{"reviews":[]}'}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 10, "completion_tokens": 5, "other": "ignore"}},
        "[DONE]",
    ]
    bodies = []

    def post(*_args, **kwargs):
        bodies.append(kwargs["json"])
        return FakeResponse(events=events)

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system", config=openai_config())
    assert result["text"] == '{"reviews":[]}'
    assert result["usage"] == {"prompt_tokens": 10, "completion_tokens": 5}
    assert bodies[0]["thinking"] == {"type": "disabled"}


def test_openai_length_stop_rejects_partial_json(monkeypatch):
    events = [{"choices": [{"delta": {"content": '{"reviews":['},
                            "finish_reason": "length"}]}, "[DONE]"]
    monkeypatch.setattr(transport.requests, "post",
                        lambda *_args, **_kwargs: FakeResponse(events=events))
    result = transport.call_model("prompt", system_prompt="system", config=openai_config())
    assert result["text"] is None
    assert result["error_code"] == "truncated"
    assert result["finish_reason"] == "length"


def test_generic_openai_provider_keeps_its_original_model(monkeypatch):
    bodies = []
    config = ArkConfig(api_key="test-secret", base_url="https://example.com/v1",
                       model="existing-model", style=STYLE_OPENAI)

    def post(*_args, **kwargs):
        bodies.append(kwargs["json"])
        return FakeResponse(status=400)

    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system", config=config)
    assert result["error_code"] == "invalid_request"
    assert result["attempts"] == 1
    assert bodies[0]["model"] == "existing-model"
    assert "thinking" not in bodies[0]
    assert "stream_options" not in bodies[0]


def test_missing_config_does_not_call_network(monkeypatch):
    monkeypatch.setattr(transport.llm, "load_ark_config", lambda: None)
    monkeypatch.setattr(transport.requests, "post", lambda *_args, **_kwargs: 1 / 0)
    result = transport.call_model("prompt", system_prompt="system")
    assert result["error_code"] == "missing_config"
    assert result["attempts"] == 0
    assert result["model"] is None


def test_default_opportunity_config_selects_latest_deepseek_without_mutating_original(monkeypatch):
    original = anthropic_config()
    monkeypatch.setattr(transport.llm, "load_ark_config", lambda: original)
    resolved = transport.load_opportunity_config()
    assert resolved.model == "deepseek-flash"
    assert resolved.api_key == original.api_key
    assert resolved.base_url == original.base_url
    assert resolved.style == original.style
    assert resolved.max_tokens == original.max_tokens
    assert resolved.timeout == original.timeout
    assert original.model == "deepseek-v4-pro[1m]"
    captured = []
    def post(*_args, **kwargs):
        captured.append(kwargs["json"]["model"])
        return FakeResponse(body=anthropic_message())
    monkeypatch.setattr(transport.requests, "post", post)
    result = transport.call_model("prompt", system_prompt="system")
    assert result["model"] == "deepseek-flash"
    assert captured == ["deepseek-flash"]


def test_explicit_config_keeps_historical_model_without_loading_defaults(monkeypatch):
    def unexpected_default():
        raise AssertionError("explicit configuration must bypass defaults")
    monkeypatch.setattr(transport.llm, "load_ark_config", unexpected_default)
    monkeypatch.setattr(
        transport.requests, "post", lambda *_args, **_kwargs: FakeResponse(body=anthropic_message())
    )
    result = transport.call_model("prompt", system_prompt="system", config=anthropic_config())
    assert result["model"] == "deepseek-v4-pro[1m]"


def test_opportunity_config_keeps_other_provider_and_missing_config(monkeypatch):
    for original in (generic_anthropic_config(), None):
        monkeypatch.setattr(transport.llm, "load_ark_config", lambda original=original: original)
        assert transport.load_opportunity_config() is original


def test_similar_deepseek_hostname_is_not_overridden(monkeypatch):
    from dataclasses import replace
    original = replace(anthropic_config(), base_url="https://api.deepseek.com.example.org/anthropic")
    monkeypatch.setattr(transport.llm, "load_ark_config", lambda: original)
    assert transport.load_opportunity_config() is original
