"""Bounded model transport for selecting IDs from existing opportunity evidence.

This module does not interpret evidence or make trading judgments. For the
DeepSeek Anthropic-compatible endpoint, the opportunity request uses the
non-streaming, thinking-disabled shape observed to return a complete response.
The HTTP body is still read in bounded chunks. Other providers keep streaming.
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from typing import Any
from urllib.parse import urlsplit

import requests

from lei_signal.plans import llm

_MAX_OUTPUT_TOKENS = 4096
_MAX_TEXT_CHARS = 131072
_ATTEMPT_SECONDS = 75.0
_TOTAL_SECONDS = 160.0
_MAX_ATTEMPTS = 2


def load_opportunity_config() -> llm.ArkConfig | None:
    """Keep the original endpoint/key/style and select this workflow's approved model.

    User authorization: 2026-10-18, opportunity reviews only. Official model table:
    https://api-docs.deepseek.com/quick_start/pricing
    deepseek-flash points to DeepSeek-V4.1-Flash-1017; Pro is still the 0813 release.
    This local override does not change global configuration or other agents.
    """
    config = llm.load_ark_config()
    if (config is not None
            and (urlsplit(config.base_url).hostname or "").lower() == "api.deepseek.com"):
        return replace(config, model="deepseek-flash")
    return config


def _usage(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    allowed = (
        "input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "total_tokens",
    )
    return {key: value[key] for key in allowed if type(value.get(key)) is int and value[key] >= 0}


def _failure(code: str, retryable: bool, *, usage: dict | None = None,
             finish_reason: str | None = None, phase: str = "connecting") -> dict:
    return {"text": None, "error_code": code, "retryable": retryable,
            "usage": usage or {}, "finish_reason": finish_reason, "phase": phase}


def _network_failure(exc: requests.RequestException, phase: str, usage: dict | None = None) -> dict:
    # requests may wrap urllib3 ReadTimeoutError as ConnectionError while reading SSE.
    timed_out = isinstance(exc, requests.Timeout) or "timed out" in str(exc).lower()
    return _failure("timeout" if timed_out else "connection_error", True,
                    usage=usage, phase=phase)


def _append(parts: list[str], piece: Any, size: int) -> int:
    if not isinstance(piece, str):
        return size
    size += len(piece)
    if size > _MAX_TEXT_CHARS:
        raise OverflowError("output_too_large")
    parts.append(piece)
    return size


def _read_anthropic(response: requests.Response, deadline: float) -> dict:
    parts: list[str] = []
    size = 0
    usage: dict[str, int] = {}
    finish_reason: str | None = None
    completed = False
    phase = "headers"
    try:
        for line in response.iter_lines(decode_unicode=True):
            if time.monotonic() >= deadline:
                return _failure("timeout", True, usage=usage,
                                finish_reason=finish_reason, phase=phase)
            if not line or not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except (TypeError, ValueError):
                return _failure("stream_protocol_error", False, usage=usage, phase=phase)
            if not isinstance(event, dict):
                return _failure("stream_protocol_error", False, usage=usage, phase=phase)
            phase = "events"
            kind = event.get("type")
            if kind == "message_start":
                usage.update(_usage((event.get("message") or {}).get("usage")))
            elif kind == "content_block_start":
                block = event.get("content_block") or {}
                if block.get("type") == "text":
                    size = _append(parts, block.get("text"), size)
                    if size:
                        phase = "output"
            elif kind == "content_block_delta":
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta":
                    size = _append(parts, delta.get("text"), size)
                    if size:
                        phase = "output"
            elif kind == "message_delta":
                delta = event.get("delta") or {}
                finish_reason = delta.get("stop_reason") or finish_reason
                usage.update(_usage(event.get("usage")))
            elif kind == "error":
                error = event.get("error") or {}
                return _failure(
                    "stream_error", error.get("type") == "overloaded_error",
                    usage=usage, phase=phase,
                )
            elif kind == "message_stop":
                completed = True
                break
    except OverflowError:
        return _failure("output_too_large", False, usage=usage, phase=phase)
    except requests.RequestException as exc:
        return _network_failure(exc, phase, usage)
    except (AttributeError, TypeError, ValueError):
        return _failure("stream_protocol_error", False, usage=usage, phase=phase)
    if not completed:
        return _failure("stream_incomplete", True, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    if finish_reason == "max_tokens":
        return _failure("truncated", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    if finish_reason not in ("end_turn", "stop_sequence"):
        return _failure("incomplete_output", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    text = "".join(parts).strip()
    if not text:
        return _failure("empty_content", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    return {"text": text, "error_code": "", "retryable": False,
            "usage": usage, "finish_reason": finish_reason, "phase": "complete"}


def _read_anthropic_json(response: requests.Response, deadline: float) -> dict:
    """Read a non-streaming Messages body without buffering an unbounded response."""
    chunks: list[bytes] = []
    size = 0
    phase = "headers"
    try:
        for chunk in response.iter_content(chunk_size=4096):
            if time.monotonic() >= deadline:
                return _failure("timeout", True, phase=phase)
            if not isinstance(chunk, bytes):
                return _failure("invalid_response", False, phase=phase)
            size += len(chunk)
            if size > _MAX_TEXT_CHARS:
                return _failure("output_too_large", False, phase=phase)
            if chunk:
                chunks.append(chunk)
                phase = "body"
        if time.monotonic() >= deadline:
            return _failure("timeout", True, phase=phase)
        message = json.loads(b"".join(chunks).decode("utf-8"))
    except requests.RequestException as exc:
        return _network_failure(exc, phase)
    except (UnicodeDecodeError, ValueError, TypeError):
        return _failure("invalid_response", False, phase=phase)
    if not isinstance(message, dict):
        return _failure("invalid_response", False, phase=phase)
    usage = _usage(message.get("usage"))
    finish_reason = message.get("stop_reason")
    if finish_reason == "max_tokens":
        return _failure("truncated", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    if finish_reason not in ("end_turn", "stop_sequence"):
        return _failure("incomplete_output", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    blocks = message.get("content")
    if not isinstance(blocks, list):
        return _failure("invalid_response", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    parts: list[str] = []
    text_size = 0
    for block in blocks:
        if not isinstance(block, dict):
            return _failure("invalid_response", False, usage=usage,
                            finish_reason=finish_reason, phase=phase)
        if block.get("type") == "text":
            piece = block.get("text")
            if not isinstance(piece, str):
                return _failure("invalid_response", False, usage=usage,
                                finish_reason=finish_reason, phase=phase)
            text_size = _append(parts, piece, text_size)
    text = "".join(parts).strip()
    if not text:
        return _failure("empty_content", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    return {"text": text, "error_code": "", "retryable": False,
            "usage": usage, "finish_reason": finish_reason, "phase": "complete"}


def _read_openai(response: requests.Response, deadline: float) -> dict:
    parts: list[str] = []
    size = 0
    usage: dict[str, int] = {}
    finish_reason: str | None = None
    completed = False
    phase = "headers"
    try:
        for line in response.iter_lines(decode_unicode=True):
            if time.monotonic() >= deadline:
                return _failure("timeout", True, usage=usage,
                                finish_reason=finish_reason, phase=phase)
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                completed = True
                break
            try:
                chunk = json.loads(data)
            except (TypeError, ValueError):
                return _failure("stream_protocol_error", False, usage=usage, phase=phase)
            if not isinstance(chunk, dict):
                return _failure("stream_protocol_error", False, usage=usage, phase=phase)
            phase = "events"
            if chunk.get("error"):
                return _failure("stream_error", False, usage=usage, phase=phase)
            usage.update(_usage(chunk.get("usage")))
            for choice in chunk.get("choices") or []:
                if not isinstance(choice, dict):
                    continue
                finish_reason = choice.get("finish_reason") or finish_reason
                size = _append(parts, (choice.get("delta") or {}).get("content"), size)
                if size:
                    phase = "output"
    except OverflowError:
        return _failure("output_too_large", False, usage=usage, phase=phase)
    except requests.RequestException as exc:
        return _network_failure(exc, phase, usage)
    except (AttributeError, TypeError, ValueError):
        return _failure("stream_protocol_error", False, usage=usage, phase=phase)
    if not completed:
        return _failure("stream_incomplete", True, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    if finish_reason == "length":
        return _failure("truncated", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    if finish_reason != "stop":
        return _failure("incomplete_output", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    text = "".join(parts).strip()
    if not text:
        return _failure("empty_content", False, usage=usage,
                        finish_reason=finish_reason, phase=phase)
    return {"text": text, "error_code": "", "retryable": False,
            "usage": usage, "finish_reason": finish_reason, "phase": "complete"}


def _single_call(
    prompt: str, system_prompt: str, config: llm.ArkConfig, remaining_seconds: float,
) -> dict:
    base = config.base_url.rstrip("/")
    host = (urlsplit(base).hostname or "").lower()
    deepseek = host == "deepseek.com" or host.endswith(".deepseek.com")
    max_tokens = max(1, min(config.max_tokens, _MAX_OUTPUT_TOKENS))
    if config.style == llm.STYLE_ANTHROPIC:
        url = base + "/v1/messages"
        headers = {"x-api-key": config.api_key, "anthropic-version": "2023-06-01",
                   "Content-Type": "application/json"}
        body: dict[str, Any] = {"model": config.model, "max_tokens": max_tokens,
                                "system": system_prompt, "stream": True,
                                "messages": [{"role": "user", "content": prompt}]}
        if deepseek:
            body["stream"] = False
            body["thinking"] = {"type": "disabled"}
        reader = _read_anthropic_json if deepseek else _read_anthropic
    else:
        url = base + "/chat/completions"
        headers = {"Authorization": "Bearer " + config.api_key,
                   "Content-Type": "application/json"}
        body = {"model": config.model, "max_tokens": max_tokens, "stream": True,
                "messages": [{"role": "system", "content": system_prompt},
                             {"role": "user", "content": prompt}]}
        if deepseek:
            body["thinking"] = {"type": "disabled"}
            body["stream_options"] = {"include_usage": True}
        reader = _read_openai
    timeout = min(max(float(config.timeout), 1.0), _ATTEMPT_SECONDS, remaining_seconds)
    bounded_json = deepseek and config.style == llm.STYLE_ANTHROPIC
    if timeout <= 0 or (bounded_json and timeout <= 1):
        return _failure("timeout", True)
    deadline = time.monotonic() + timeout
    if bounded_json:
        connect_timeout = min(10.0, timeout - 1.0)
        read_timeout = max(1.0, timeout - connect_timeout)
    else:
        connect_timeout = min(10.0, timeout)
        read_timeout = min(15.0, timeout)
    try:
        with requests.post(url, headers=headers, json=body, stream=True,
                           timeout=(connect_timeout, read_timeout)) as response:
            status = response.status_code
            if status != 200:
                if status in (401, 403):
                    code, retryable = "auth_error", False
                elif status == 402:
                    code, retryable = "insufficient_balance", False
                elif status in (400, 422):
                    code, retryable = "invalid_request", False
                elif status == 429:
                    code, retryable = "rate_limited", True
                elif status >= 500:
                    code, retryable = "provider_error", True
                else:
                    code, retryable = "http_error", False
                # Keep only the numeric status, never headers or error bodies.
                return {**_failure(code, retryable, phase="headers"), "http_status": status}
            return reader(response, deadline)
    except requests.RequestException as exc:
        return _network_failure(exc, "connecting")


def call_model(prompt: str, *, system_prompt: str, config: llm.ArkConfig | None = None) -> dict:
    """Return the complete text or a classified failure, without exposing request data.

    One transient failure may be retried. A 200 response with missing text or a
    token-limit stop is terminal because repeating the same request is unlikely
    to help. The caller validates the returned JSON and evidence IDs.
    """
    started = time.monotonic()
    resolved = config if config is not None else load_opportunity_config()
    if resolved is None:
        result = _failure("missing_config", False, phase="config")
        attempts = 0
        model = None
    else:
        model = resolved.model
        attempts = 0
        total_deadline = started + _TOTAL_SECONDS
        for _ in range(_MAX_ATTEMPTS):
            remaining = total_deadline - time.monotonic()
            if remaining <= 0:
                result = _failure("timeout", True)
                break
            attempts += 1
            result = _single_call(prompt, system_prompt, resolved, remaining)
            if not result["retryable"] or result["text"] is not None:
                break
            if attempts < _MAX_ATTEMPTS:
                remaining = total_deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(1.0, remaining))
    return {**result, "attempts": attempts, "model": model,
            "elapsed_ms": round((time.monotonic() - started) * 1000)}
