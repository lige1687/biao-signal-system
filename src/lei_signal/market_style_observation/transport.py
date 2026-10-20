"""One bounded model request for selecting existing evidence card IDs."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from urllib.parse import urlsplit

import requests

from lei_signal.plans import llm

_MAX_RESPONSE_BYTES = 65_536
_MAX_OUTPUT_TOKENS = 1024


def _usage(value: object) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    keys = ("input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "total_tokens")
    result = {key: value[key] for key in keys if type(value.get(key)) is int and value[key] >= 0}
    return result or None


def _parse_response(payload: object, style: str) -> tuple[str | None, dict[str, int] | None, str]:
    if not isinstance(payload, dict):
        return None, None, "invalid_response"
    usage = _usage(payload.get("usage"))
    if style == llm.STYLE_ANTHROPIC:
        stop = payload.get("stop_reason")
        if stop == "max_tokens":
            return None, usage, "truncated"
        if stop not in ("end_turn", "stop_sequence"):
            return None, usage, "incomplete_output"
        blocks = payload.get("content")
        if not isinstance(blocks, list):
            return None, usage, "invalid_response"
        text = "\n".join(block["text"] for block in blocks
                         if isinstance(block, dict) and block.get("type") == "text"
                         and isinstance(block.get("text"), str)).strip()
    else:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            return None, usage, "invalid_response"
        choice = choices[0]
        if choice.get("finish_reason") == "length":
            return None, usage, "truncated"
        if choice.get("finish_reason") != "stop":
            return None, usage, "incomplete_output"
        message = choice.get("message")
        text = message.get("content", "").strip() if isinstance(message, dict) and isinstance(message.get("content"), str) else ""
    return (text, usage, "") if text else (None, usage, "empty_content")


def invoke_selection(prompt: str, system_prompt: str, config: llm.ArkConfig) -> dict:
    """Return text, observed token usage, elapsed time and a safe error code.

    The configured model and key are reused unchanged. No automatic retry occurs.
    """
    started = time.monotonic()
    host = (urlsplit(config.base_url).hostname or "").lower()
    if host != "api.deepseek.com":
        bounded = replace(config, timeout=min(config.timeout, 45.0),
                          max_tokens=min(config.max_tokens, 2048), retry_on_throttle=0)
        try:
            text = llm.post_user_content(prompt, bounded, system_prompt=system_prompt)
        except Exception:
            text = None
        return {"text": text, "usage": None, "elapsed_ms": round((time.monotonic() - started) * 1000),
                "error_code": "" if text else "model_no_text"}

    base = config.base_url.rstrip("/")
    if config.style == llm.STYLE_ANTHROPIC:
        url = base + "/v1/messages"
        headers = {"x-api-key": config.api_key, "anthropic-version": "2023-06-01",
                   "Content-Type": "application/json"}
        body = {"model": config.model, "max_tokens": _MAX_OUTPUT_TOKENS,
                "thinking": {"type": "disabled"}, "system": system_prompt,
                "messages": [{"role": "user", "content": prompt}]}
    elif config.style == llm.STYLE_OPENAI:
        url = base + "/chat/completions"
        headers = {"Authorization": "Bearer " + config.api_key, "Content-Type": "application/json"}
        body = {"model": config.model, "max_tokens": _MAX_OUTPUT_TOKENS,
                "thinking": {"type": "disabled"},
                "messages": [{"role": "system", "content": system_prompt},
                             {"role": "user", "content": prompt}]}
    else:
        return {"text": None, "usage": None, "elapsed_ms": 0, "error_code": "unsupported_protocol"}

    response = None
    try:
        response = requests.post(url, headers=headers, json=body, timeout=(5, 40), stream=True)
        if response.status_code != 200:
            return {"text": None, "usage": None,
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                    "error_code": f"provider_http_{response.status_code}"}
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=4096):
            if not chunk:
                continue
            size += len(chunk)
            if size > _MAX_RESPONSE_BYTES:
                return {"text": None, "usage": None,
                        "elapsed_ms": round((time.monotonic() - started) * 1000),
                        "error_code": "response_too_large"}
            chunks.append(chunk)
        payload = json.loads(b"".join(chunks).decode("utf-8"))
        text, usage, error_code = _parse_response(payload, config.style)
        return {"text": text, "usage": usage,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "error_code": error_code}
    except requests.Timeout:
        code = "timeout"
    except requests.RequestException:
        code = "connection_error"
    except (UnicodeError, ValueError, TypeError):
        code = "invalid_response"
    finally:
        if response is not None:
            response.close()
    return {"text": None, "usage": None,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "error_code": code}
