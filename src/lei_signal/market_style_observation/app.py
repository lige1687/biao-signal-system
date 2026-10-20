"""Isolated 8192 preview API: facts on GET, one optional model choice on POST."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from lei_signal.market_style_observation.evidence import build_evidence
from lei_signal.market_style_observation.transport import invoke_selection
from lei_signal.plans import llm

app = FastAPI(title="Market style observation preview")

_LOCK = threading.Lock()
_SNAPSHOTS: dict[str, dict] = {}
_GENERATED: dict[str, dict] = {}
_IN_FLIGHT: set[str] = set()
_SNAPSHOT_TIMES: dict[str, float] = {}
_QUERY_CACHE: dict[tuple[str, int], tuple[float, dict]] = {}
_MODEL_REQUESTS = 0
_MAX_SNAPSHOTS = 24
_SNAPSHOT_TTL_SECONDS = 30 * 60

_PROMPT = (
    "你只负责为个人低频投资者挑选阅读顺序。给定四张已核的市场背景短卡，"
    "从中选3至4张不同topic的卡。输出严格JSON，例如"
    '{"selected_ids":["breadth","world_style","risk"]}。'
    "只输出ID，不写解释、数字、阈值、交易动作或其他字段。"
)


class InterpretRequest(BaseModel):
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")


def _snapshot_id(snapshot: dict) -> str:
    # Retrieval timestamp is metadata, not evidence. The same facts reuse one completion.
    evidence = {key: value for key, value in snapshot.items() if key != "asof"}
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _select_ids(raw: str, cards: list[dict]) -> list[str] | None:
    """Reject free-form text, invented cards, duplicates and repeated topics."""
    if len(raw) > 2048 or not raw.lstrip().startswith("{"):
        return None
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"selected_ids"}:
        return None
    selected = parsed["selected_ids"]
    if not isinstance(selected, list) or len(selected) not in (3, 4):
        return None
    if any(not isinstance(item, str) for item in selected) or len(set(selected)) != len(selected):
        return None
    known = {card["id"]: card for card in cards}
    if any(item not in known for item in selected):
        return None
    if len({known[item]["topic"] for item in selected}) != len(selected):
        return None
    return selected


def _error(status: int, code: str, *, usage: dict | None = None, elapsed_ms: int | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"generated": False, "error": code,
                                                     "usage": usage, "elapsed_ms": elapsed_ms,
                                                     "cost": None})


def _expire_snapshots() -> None:
    cutoff = time.monotonic() - _SNAPSHOT_TTL_SECONDS
    for key, created in list(_SNAPSHOT_TIMES.items()):
        if created < cutoff and key not in _IN_FLIGHT:
            _SNAPSHOT_TIMES.pop(key, None)
            _SNAPSHOTS.pop(key, None)
            _GENERATED.pop(key, None)


@app.get("/health")
def health() -> dict:
    with _LOCK:
        return {"ok": True, "model_requests": _MODEL_REQUESTS,
                "snapshots": len(_SNAPSHOTS), "completed": len(_GENERATED),
                "in_flight": len(_IN_FLIGHT)}


@app.get("/api/market-style/snapshot")
def snapshot(market: Literal["cn", "us"], window_days: int = Query(365)):
    if window_days not in (365, 1095, 1825):
        return _error(422, "invalid_window")
    cache_key = (market, window_days)
    with _LOCK:
        cached = _QUERY_CACHE.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
    result = build_evidence(market, window_days)
    sid = _snapshot_id(result)
    result["snapshot_id"] = sid
    with _LOCK:
        _expire_snapshots()
        _QUERY_CACHE[cache_key] = (time.monotonic() + 60, result)
        _SNAPSHOTS[sid] = result
        _SNAPSHOT_TIMES[sid] = time.monotonic()
        # Bounded RAM. Never evict an active request.
        if len(_SNAPSHOTS) > _MAX_SNAPSHOTS:
            for key in list(_SNAPSHOTS):
                if key != sid and key not in _IN_FLIGHT:
                    del _SNAPSHOTS[key]
                    _SNAPSHOT_TIMES.pop(key, None)
                    _GENERATED.pop(key, None)
                    if len(_SNAPSHOTS) <= _MAX_SNAPSHOTS:
                        break
    return result


@app.post("/api/market-style/interpret")
def interpret(body: InterpretRequest):
    global _MODEL_REQUESTS
    with _LOCK:
        _expire_snapshots()
        current = _SNAPSHOTS.get(body.snapshot_id)
        if current is None:
            return _error(404, "unknown_snapshot")
        cached = _GENERATED.get(body.snapshot_id)
        if cached is not None:
            return cached
        if body.snapshot_id in _IN_FLIGHT or _IN_FLIGHT:
            return _error(409, "model_request_in_progress")
        _IN_FLIGHT.add(body.snapshot_id)
    try:
        config = llm.load_ark_config()
        if config is None:
            return _error(503, "model_unavailable")
        compact = [{"id": card["id"], "topic": card["topic"],
                    "fact": card["fact"], "available": card["available"],
                    "data_date": card["data_date"]} for card in current["cards"]]
        prompt = json.dumps({"market": current["market"], "asof": current["asof"],
                             "cards": compact}, ensure_ascii=False, separators=(",", ":"))
        with _LOCK:
            _MODEL_REQUESTS += 1
        try:
            result = invoke_selection(prompt, _PROMPT, config)
        except Exception:  # provider failures must not expose payloads or become success
            return _error(503, "model_failed")
        raw = result["text"]
        usage = result["usage"]
        elapsed_ms = result["elapsed_ms"]
        if raw is None:
            return _error(503, result["error_code"] or "model_no_text", usage=usage, elapsed_ms=elapsed_ms)
        selected = _select_ids(raw, current["cards"])
        if selected is None:
            return _error(422, "invalid_model_selection", usage=usage, elapsed_ms=elapsed_ms)
        by_id = {card["id"]: card for card in current["cards"]}
        answer = {"generated": True, "mode": "evidence_selection",
                  "snapshot_id": body.snapshot_id, "cards": [by_id[item] for item in selected],
                  "model": config.model, "generated_at": datetime.now(timezone.utc).isoformat(),
                  "usage": usage, "elapsed_ms": elapsed_ms, "cost": None,
                  "limits": ["模型仅排列已核事实卡，事实、解释和来源均由服务端模板提供。",
                             "模型报告了本次token用量，实际费用未核得。" if usage else "本次未取得模型token用量，实际费用未核得。"]}
        with _LOCK:
            _GENERATED[body.snapshot_id] = answer
        return answer
    finally:
        with _LOCK:
            _IN_FLIGHT.discard(body.snapshot_id)
