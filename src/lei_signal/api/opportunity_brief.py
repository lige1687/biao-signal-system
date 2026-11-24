"""Pure, source-bound display brief for one opportunity review subject."""

from __future__ import annotations

from datetime import date
from typing import Any


def _day(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        parsed = date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None
    return parsed if value[:10] == parsed else None


def _citable(evidence: dict) -> bool:
    ref = evidence.get("source_ref")
    return bool(
        evidence.get("public") is True
        and evidence.get("role") != "lead"
        and evidence.get("provenance") != "unverified_news"
        and isinstance(ref, str)
        and (ref.startswith("https://") or (ref.startswith("/") and not ref.startswith("//")))
        and any(_day(evidence.get(field)) for field in ("published_at", "report_date", "date"))
    )


def _counter_citable(evidence: dict) -> bool:
    if _citable(evidence):
        return True
    ref = evidence.get("source_ref")
    return bool(
        evidence.get("category") == "technical"
        and evidence.get("scope") == "same_product"
        and evidence.get("role") in {"support", "opposition", "condition", "context"}
        and evidence.get("provenance")
        in {"existing_rule", "research_proxy", "lei_explicit", "existing_backtest"}
        and _day(evidence.get("date"))
        and isinstance(ref, str)
        and (ref.startswith("/symbol/") or ref == "/portfolio")
    )


def _point_evidence(item: dict, point: dict, *, counter: bool = False) -> list[dict] | None:
    ids = point.get("evidence_ids") or []
    if (
        not isinstance(ids, list)
        or not ids
        or not all(isinstance(value, str) and value for value in ids)
    ):
        return None
    by_id = {
        e.get("id"): e for e in item.get("card", {}).get("evidence", []) if isinstance(e, dict)
    }
    evidence = [by_id.get(value) for value in ids]
    eligible = _counter_citable if counter else _citable
    return evidence if all(isinstance(e, dict) and eligible(e) for e in evidence) else None


def _context_priority(e: dict, focus: str | None) -> int:
    # Existing fund disclosure rows include an overview as well as individual
    # stocks. Lead with the fund's stated allocation and the known coverage.
    if focus == "mixed" and e.get("provenance") == "disclosed":
        text = str(e.get("text") or "")
        if text.startswith("基金经理观点："):
            return -2
        if "已披露股票覆盖基金净值" in text:
            return -1
        if text.startswith("披露股票："):
            return 8
    if e.get("relevance") == "indirect":
        return 10
    kind = e.get("narrative_kind") or ("industry" if e.get("category") == "industry" else "profile")
    preferred = "industry" if focus == "sector" else "macro" if focus == "broad" else None
    if (
        focus == "mixed"
        and (e.get("report_date") or e.get("published_at"))
        and e.get("scope") == "same_product"
    ):
        return 0
    rank = 0 if kind == preferred else 3 if kind in {"industry", "macro"} else 6
    relation = (
        0
        if focus == "sector" and kind == "industry" and e.get("scope") == "industry_reference"
        else 1
    )
    return rank + relation + (0 if e.get("relevance") == "direct" else 2)


def _background(items: list[dict]) -> list[dict]:
    focus = next(
        (
            item.get("card", {}).get("narrative_focus", {}).get("kind")
            for item in items
            if isinstance(item.get("card", {}).get("narrative_focus"), dict)
        ),
        None,
    )
    candidates = []
    for item in items:
        stage = item.get("audit", {}).get("agents", {}).get("context") or {}
        if stage.get("status") != "complete":
            continue
        for point in stage.get("points") or []:
            if not isinstance(point, dict) or not str(point.get("text") or "").strip():
                continue
            evidence = _point_evidence(item, point)
            if evidence is None:
                continue
            tone = {
                "support": "positive",
                "risk": "negative",
                "neutral": "unclear",
                "unknown": "pending",
            }.get(point.get("stance"), "unclear")
            candidates.append(
                (
                    min(_context_priority(e, focus) for e in evidence),
                    {
                        "text": point["text"].strip(),
                        "tone": tone,
                        "kind": "agent",
                        "evidence": evidence,
                    },
                )
            )
    if candidates:
        ordered = [entry for _, entry in sorted(candidates, key=lambda pair: pair[0])]
    else:
        ordered = []
        sources = []
        for item in items:
            for evidence in item.get("card", {}).get("evidence", []):
                if (
                    isinstance(evidence, dict)
                    and _citable(evidence)
                    and evidence.get("category") in {"industry", "fundamentals", "macro"}
                    and evidence.get("role") in {"context", "support"}
                ):
                    sources.append((_context_priority(evidence, focus), evidence))
        for _, evidence in sorted(sources, key=lambda pair: pair[0]):
            ordered.append(
                {
                    "text": evidence.get("text") or "",
                    "tone": "unclear",
                    "kind": "source",
                    "evidence": [evidence],
                }
            )
    unique = []
    seen = set()
    for entry in ordered:
        if entry["text"] and entry["text"] not in seen:
            unique.append(entry)
            seen.add(entry["text"])
        if len(unique) == 2:
            break
    return unique


def _opposition(item: dict | None) -> dict:
    unavailable = {
        "status": "unavailable",
        "kind": "unavailable",
        "text": "独立反方资料未取得或引用未核实",
        "evidence": [],
    }
    if not item:
        return unavailable
    stage = item.get("audit", {}).get("agents", {}).get("counter") or {}
    if stage.get("status") != "complete":
        return unavailable
    points = stage.get("points") or []
    if not points or any(
        not isinstance(point, dict) or _point_evidence(item, point, counter=True) is None
        for point in points
    ):
        return unavailable
    when = stage.get("generated_at") or item.get("audit", {}).get("generated_at")
    if not when:
        return unavailable
    # A critic can discuss limits of a supporting rule. Its risk label does not
    # reverse that rule's direction. Keep technical opposition in the rule's
    # original words, and label other critic observations as checks.
    opposing = []
    for point in points:
        for evidence in _point_evidence(item, point, counter=True) or []:
            if (
                evidence.get("category") == "technical"
                and evidence.get("role") == "opposition"
                and evidence not in opposing
            ):
                opposing.append(evidence)
    if opposing:
        return {
            "status": "complete",
            "kind": "opposition",
            "text": f"原规则的反向条件：{opposing[0]['text']}",
            "evidence": [opposing[0]],
        }
    point = next(
        (
            point
            for point in points
            if point.get("stance") in {"risk", "unknown"} and str(point.get("text") or "").strip()
        ),
        None,
    )
    if not point:
        return unavailable
    return {
        "status": "complete",
        "kind": "check",
        "text": f"反方审查于{when}记录：{point['text'].strip()}",
        "evidence": _point_evidence(item, point, counter=True),
    }


def _technical_valid(technical: dict | None, subject: dict) -> bool:
    if not isinstance(technical, dict):
        return False
    expected = subject.get("id") if subject.get("kind") == "symbol" else subject.get("symbol")
    meta = technical.get("meta") or {}
    chart = technical.get("chart") or {}
    dates = chart.get("dates") or []
    ohlc = chart.get("ohlc") or []
    as_of = _day(technical.get("as_of"))
    return bool(
        expected
        and technical.get("symbol") == expected
        and meta.get("freshness") == "current"
        and meta.get("bar_status") in {"closed", "intraday"}
        and isinstance(dates, list)
        and len(dates) >= 2
        and isinstance(ohlc, list)
        and len(ohlc) == len(dates)
        and isinstance(technical.get("signals"), list)
        and as_of
        and _day(meta.get("last_bar_date")) == as_of
        and _day(dates[-1]) == as_of
    )


def _missing_conditions(signals: list[dict]) -> str:
    conditions = list(
        dict.fromkeys(
            condition.strip()
            for signal in signals
            for condition in signal.get("missing_conditions") or []
            if isinstance(condition, str) and condition.strip()
        )
    )
    return "；".join(conditions[:2]) + (f"等{len(conditions)}项" if len(conditions) > 2 else "")


def _signal_description(signal: dict, *, intraday: bool) -> str:
    state = {"new": "已触发", "active": "仍在观察", "waiting": "等待条件"}[signal["status"]]
    if intraday:
        state = "等待条件" if signal["status"] == "waiting" else "盘中观察"
    missing = _missing_conditions([signal])
    detail = f"，还差：{missing}" if missing else ""
    return f"{signal['event_date']} {signal.get('title') or '技术事件'}（{state}{detail}）"


def _key_gaps(board: dict, items: list[dict], *, technical_valid: bool, errors: dict) -> list[dict]:
    """Keep selected-product gaps separate from a batch's unfinished review."""
    candidates = []
    if not technical_valid:
        candidates.append(
            {
                "kind": "technical",
                "text": "同产品技术资料读取未完成，需恢复读取后核对买卖条件。"
                if errors.get("technical")
                else "同产品技术资料未取得或产品、日期、收盘状态未核对通过，需补齐后确认买卖条件。",
            }
        )
    for item in items:
        audit = item.get("audit") or {}
        for agent, label in (("context", "基本面与新闻分析"), ("counter", "反方检查")):
            stage = (audit.get("agents") or {}).get(agent) or {}
            if stage.get("status") in {"failed", "pending", "running"}:
                candidates.append(
                    {
                        "kind": "review",
                        "side": item["card"].get("intent"),
                        "agent": agent,
                        "text": f"本产品{label}尚未完成，需核对该环节后再理解完整审查。",
                    }
                )
    for item in items:
        for agent in ("context", "counter"):
            stage = (item.get("audit", {}).get("agents") or {}).get(agent) or {}
            # Failed model output is not adopted as an analysis or a factual gap.
            if stage.get("status") != "complete":
                continue
            for gap in stage.get("gaps") or []:
                if isinstance(gap, str) and gap.strip():
                    candidates.append(
                        {
                            "kind": "agent",
                            "text": gap.strip(),
                            "side": item["card"].get("intent"),
                            "agent": agent,
                        }
                    )
    if board.get("status") in {"partial", "pending", "running", "failed"}:
        candidates.append(
            {
                "kind": "review",
                "text": "本批审查尚未全部完成，需核对未完成环节；当前产品按已取得资料理解。",
            }
        )
    unique, seen = [], set()
    for gap in candidates:
        if gap["text"] not in seen:
            unique.append(gap)
            seen.add(gap["text"])
        if len(unique) == 2:
            break
    return unique


def build_product_brief(
    board: dict,
    subject_key: str,
    *,
    technical: dict | None = None,
    market: dict | None = None,
    errors: dict | None = None,
) -> dict:
    """Arrange existing review material without creating a trading judgment."""
    items = [
        item
        for item in board.get("items", [])
        if item.get("card", {}).get("subject", {}).get("key") == subject_key
    ]
    if not items:
        raise ValueError(f"机会审查中没有对象：{subject_key}")
    by_side = {item["card"].get("intent"): item for item in items}
    subject = items[0]["card"]["subject"]
    errors = dict(errors or {})
    if market and market.get("subject_key") != subject_key:
        market = None
        errors["market"] = "取得的净值资料不属于当前基金，已停止展示"
    valid = _technical_valid(technical, subject)
    directions = {}
    for side, label in (("buy", "买入"), ("sell", "卖出")):
        if not valid:
            directions[side] = {
                "status": "unavailable",
                "text": f"{label}时点缺少同产品且日期一致的近期技术资料，无法确认",
                "signals": [],
            }
            continue
        as_of = _day(technical["as_of"])
        signals = [
            signal
            for signal in technical.get("signals", [])
            if isinstance(signal, dict)
            and signal.get("side") == side
            and signal.get("is_recent") is True
            and signal.get("status") in {"new", "active", "waiting"}
            and (day := _day(signal.get("event_date")))
            and day <= as_of
        ]
        if not signals:
            directions[side] = {
                "status": "none",
                "text": f"截至{as_of}，{label}侧没有新的或仍需关注的近期技术事件",
                "signals": [],
            }
            continue
        intraday = (technical.get("meta") or {}).get("bar_status") == "intraday"
        status = (
            "waiting" if intraday or all(s["status"] == "waiting" for s in signals) else "attention"
        )
        displayed = signals[:2]
        # Preserve both states even when the waiting event is third or later.
        if any(s["status"] == "waiting" for s in signals) and any(
            s["status"] != "waiting" for s in signals
        ):
            displayed = [
                next(s for s in signals if s["status"] != "waiting"),
                next(s for s in signals if s["status"] == "waiting"),
            ]
        names = "、".join(_signal_description(signal, intraday=intraday) for signal in displayed)
        more = f"等{len(signals)}项" if len(signals) > 2 else ""
        suffix = "，盘中待收盘核对" if intraday else ""
        directions[side] = {
            "status": status,
            "text": f"{label}侧近期事件：{names}{more}{suffix}。",
            "signals": signals,
        }
    changed = [
        (side, label)
        for side, label in (("buy", "买入"), ("sell", "卖出"))
        if directions[side]["signals"]
    ]
    if changed:
        pieces = []
        for side, label in (("buy", "买入"), ("sell", "卖出")):
            signals = directions[side]["signals"]
            if not signals:
                pieces.append(f"{label}侧暂无近期事件")
                continue
            states = []
            for state, text in (("new", "已触发"), ("active", "仍在观察"), ("waiting", "等待条件")):
                count = sum(signal["status"] == state for signal in signals)
                if count:
                    if technical["meta"].get("bar_status") == "intraday" and state != "waiting":
                        text = "盘中观察"
                    states.append(f"{count}项{text}")
            missing = _missing_conditions(signals)
            pieces.append(
                f"{label}侧：{'、'.join(states)}" + (f"（还差：{missing}）" if missing else "")
            )
        summary_text = (
            f"截至{technical['as_of']}，"
            + "；".join(pieces)
            + ("；盘中待收盘核对。" if technical["meta"].get("bar_status") == "intraday" else "。")
        )
    elif valid:
        summary_text = f"截至{technical['as_of']}，买卖两侧均无新的近期技术事件。"
        if technical["meta"].get("bar_status") == "intraday":
            summary_text += "盘中观察，待收盘核对。"
    else:
        nav = (market or {}).get("nav") or {}
        latest = nav.get("latest") if market and market.get("subject_key") == subject_key else None
        nav_date = _day(latest.get("date")) if isinstance(latest, dict) else None
        summary_text = (
            f"已取得截至{nav_date}的净值走势；本基金买卖时点仍缺同产品技术判断。"
            if subject.get("kind") == "holding" and nav_date
            else "同产品技术资料未取得或日期不一致，买卖时点无法确认。"
        )
    review_dates = [
        item.get("audit", {}).get("generated_at")
        for item in items
        if item.get("audit", {}).get("generated_at")
    ]
    limitations = list(board.get("limitations") or [])
    for item in items:
        limitations.extend(item.get("card", {}).get("limitations") or [])
    if technical:
        limitations.extend(technical.get("limitations") or [])
    return {
        "schema_version": "opportunity-brief/1",
        "run_id": board.get("run_id"),
        "subject": subject,
        "summary": {"kind": "facts", "text": summary_text},
        "directions": directions,
        "background": _background(items),
        "opposition": {side: _opposition(by_side.get(side)) for side in ("buy", "sell")},
        "dates": {
            "technical": technical.get("as_of") if technical else None,
            "nav": (market.get("nav") or {}).get("latest", {}).get("date")
            if isinstance((market or {}).get("nav", {}).get("latest"), dict)
            else None,
            "disclosure": (market.get("disclosure") or {}).get("report_date") if market else None,
            "review_generated": max(review_dates) if review_dates else None,
            "checked_at": board.get("checked_at"),
        },
        "review_status": board.get("status"),
        "key_gaps": _key_gaps(board, items, technical_valid=valid, errors=errors),
        "technical": technical,
        "market": market,
        "limitations": limitations,
        "errors": dict(errors or {}),
    }
