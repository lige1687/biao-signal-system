"""Read-only signal rows tied to one analysis result and its daily bars."""

from __future__ import annotations

from datetime import date
from math import isfinite
from typing import Any

from lei_signal.api.sell_signals import RECENCY_BARS


def _day(value: Any) -> str | None:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return None
    return value.isoformat() if isinstance(value, date) else None


def _age(frame: Any, day: str | None) -> int | None:
    if not day or frame is None or len(frame.index) == 0:
        return None
    days = [ts.date().isoformat() for ts in frame.index]
    if day not in days:
        return None
    return len(days) - 1 - days.index(day)


def _row(
    *,
    result: Any,
    side: str,
    identity: str,
    title: str,
    summary: str,
    state: str,
    event_date: str | None,
    state_changed_date: str | None,
    rule_id: str | None = None,
    lifecycle_id: str | None = None,
    structure_id: str | None = None,
    conditions: list[str] | None = None,
    missing_conditions: list[str] | None = None,
    key_prices: list[dict] | None = None,
    invalidation_cn: str = "",
    next_step_cn: str = "",
    provenance: str = "system",
) -> dict:
    age = _age(result.frame, event_date)
    state_age = _age(result.frame, state_changed_date)
    current = state != "cleared"
    status = (
        "cleared"
        if not current
        else "waiting"
        if state in {"watch", "waiting", "candidate"}
        else "new"
        if age == 0
        else "active"
        if state in {"confirmed", "active"}
        else "unknown"
    )
    return {
        "id": identity,
        "side": side,
        "title": title,
        "summary": summary,
        "status": status,
        "event_date": event_date,
        "state_changed_date": state_changed_date,
        "age_bars": age,
        "state_age_bars": state_age,
        "is_recent": bool(current and age is not None and age < RECENCY_BARS),
        "rule_id": rule_id,
        "lifecycle_id": lifecycle_id,
        "structure_id": structure_id,
        "conditions": conditions or [],
        "missing_conditions": missing_conditions or [],
        "key_prices": key_prices or [],
        "invalidation_cn": invalidation_cn,
        "next_step_cn": next_step_cn,
        "provenance": provenance,
    }


def _price(label: str, value: Any) -> list[dict]:
    if value is None:
        return []
    number = float(value)
    return [{"label": label, "value": number}] if isfinite(number) else []


def build_signal_rows(result: Any, review: Any) -> list[dict]:
    """Expose existing buy review and sell lifecycle facts, without new rules."""
    rows: list[dict] = []
    buys = list(review.candidates)
    for group in review.resonance_groups:
        buys.extend(group.candidates)
    for candidate in buys:
        state_day = _day(candidate.last_state_change_date)
        event_day = state_day or _day(candidate.opened_date)
        candidate_identity = candidate.lifecycle_id or candidate.rule_id or "unknown"
        rows.append(
            _row(
                result=result,
                side="buy",
                identity=(
                    f"buy:{candidate.scenario_id}:{candidate_identity}:"
                    f"{event_day or 'undated'}:{_day(candidate.opened_date) or 'unopened'}"
                ),
                title=candidate.scenario_cn,
                summary=candidate.state_cn or candidate.scenario_cn,
                state=candidate.state,
                event_date=event_day,
                state_changed_date=state_day,
                rule_id=candidate.rule_id,
                lifecycle_id=candidate.lifecycle_id,
                conditions=list(candidate.satisfied_conditions),
                missing_conditions=list(candidate.missing_conditions),
                key_prices=_price("关键价", candidate.key_price)
                + _price("失效价", candidate.invalidation_price),
                invalidation_cn=candidate.invalidation_cn,
                next_step_cn=candidate.next_step_cn,
                provenance="research_proxy" if candidate.research_proxy else "system",
            )
        )
    # Historical buy rows remain visible as background. They never become current alerts.
    for historical in review.historical_structures:
        changed = _day(historical.last_state_change_date)
        opened = _day(historical.opened_date)
        historical_identity = historical.lifecycle_id or historical.rule_id
        rows.append(
            _row(
                result=result,
                side="buy",
                identity=f"buy:{historical_identity}:{changed or opened or 'undated'}",
                title=historical.scenario_cn,
                summary=historical.note,
                state=historical.state,
                event_date=changed or opened,
                state_changed_date=changed,
                rule_id=historical.rule_id,
                lifecycle_id=historical.lifecycle_id,
                key_prices=_price("关键价", historical.key_price),
                provenance="research_proxy",
            )
        )
    # One row per relevant top structure preserves confirmation and clearing dates.
    for structure in getattr(result, "structures", []) or []:
        if getattr(structure, "side", None) != "top" or not getattr(
            structure, "confirmed_date", None
        ):
            continue
        confirmed = _day(structure.confirmed_date)
        cleared = _day(getattr(structure, "invalidated_date", None))
        detected = _day(getattr(structure, "detected_date", None))
        top_event = next(
            (
                event
                for event in getattr(result, "events", []) or []
                if getattr(event, "rule_id", None) == "top_structure"
                and getattr(event, "structure_id", None) == structure.structure_id
                and (getattr(event, "evidence", None) or {}).get("sub_rule")
                == "top_structure_confirmed"
            ),
            None,
        )
        top_conditions = []
        if detected:
            top_conditions.append(f"顶部候选开始观察：{detected}")
        top_conditions.append("第二高点低于前高")
        if structure.neckline is not None:
            top_conditions.append(f"确认日收盘跌破此前回落低点 {structure.neckline:.4f}")
        risk_reason = (
            getattr(top_event, "reason_cn", "")
            or "顶部构造已确认：第二高点低于前高，收盘跌破此前回落低点；仅为风险提示"
        )
        invalidation_cn = (
            f"最高价突破前高 {structure.reference_high:.4f} 时解除预警"
            if structure.reference_high is not None
            else "最高价突破前高时解除预警"
        )
        rows.append(
            _row(
                result=result,
                side="sell",
                identity=f"sell:top:{structure.structure_id}",
                title="顶部构造预警",
                summary=f"顶部警报于{cleared}被新高解除" if cleared else risk_reason,
                state="cleared" if cleared else "confirmed",
                event_date=confirmed,
                state_changed_date=cleared or confirmed,
                rule_id="top_structure",
                structure_id=structure.structure_id,
                conditions=top_conditions,
                key_prices=_price("此前回落低点", structure.neckline)
                + _price("前高（解除预警参考）", structure.reference_high),
                invalidation_cn=invalidation_cn if not cleared else "已被新高解除",
                next_step_cn=(
                    "核对是否对应你的原入场依据；单独顶部预警不构成卖出结论"
                    if not cleared
                    else "留作历史记录"
                ),
                provenance=str(getattr(structure, "provenance", "system")),
            )
        )
    for structure in getattr(result, "structures", []) or []:
        if (
            getattr(structure, "side", None) != "bottom"
            or getattr(structure, "status", None) != "invalidated"
            or not getattr(structure, "invalidated_date", None)
        ):
            continue
        confirmed = getattr(structure, "confirmed_date", None) is not None
        invalidated = _day(structure.invalidated_date)
        rows.append(
            _row(
                result=result,
                side="sell",
                identity=f"sell:bottom:{structure.structure_id}",
                title="底部结构失效" if confirmed else "底部候选结构未成立",
                summary=getattr(structure, "invalidated_reason", "") or "结构已失效",
                state="confirmed" if confirmed else "cleared",
                event_date=invalidated,
                state_changed_date=invalidated,
                rule_id="bottom_structure",
                structure_id=structure.structure_id,
                key_prices=_price("结构 C 点", structure.c_price),
                next_step_cn="结合原入场依据核对持仓" if confirmed else "留作历史记录",
                provenance=str(getattr(structure, "provenance", "system")),
            )
        )
    wave_events = [
        e
        for e in getattr(result, "events", []) or []
        if getattr(e, "rule_id", None) == "key_wave_black"
        and (getattr(e, "evidence", None) or {}).get("sub_rule")
        in {"key_wave_black_started", "key_wave_black_ended"}
    ]
    wave_events.sort(key=lambda e: e.available_date)
    for index, event in enumerate(wave_events):
        sub = (event.evidence or {}).get("sub_rule")
        if sub != "key_wave_black_started":
            continue
        ended = next(
            (
                e
                for e in wave_events[index + 1 :]
                if (e.evidence or {}).get("sub_rule") == "key_wave_black_ended"
            ),
            None,
        )
        started_day = _day(event.available_date)
        ended_day = _day(ended.available_date) if ended else None
        rows.append(
            _row(
                result=result,
                side="sell",
                identity=f"sell:wave:{event.event_id}",
                title="反向关键性波动",
                summary=("关键性波动已结束" if ended else event.reason_cn),
                state="cleared" if ended else "confirmed",
                event_date=started_day,
                state_changed_date=ended_day or started_day,
                rule_id=event.rule_id,
                lifecycle_id=getattr(event, "lifecycle_id", None),
                invalidation_cn="颜色转为灰色或绿色时结束" if not ended else "已结束",
                next_step_cn="观察当前趋势与原计划失效位" if not ended else "留作历史记录",
                provenance=str(getattr(event, "provenance", "system")),
            )
        )
    for event in getattr(result, "events", []) or []:
        if getattr(event, "rule_id", None) != "exit_ema20_costbasis":
            continue
        event_day = _day(event.available_date)
        evidence = getattr(event, "evidence", {}) or {}
        # A historical trigger remains dated history; the current bar must still
        # satisfy the already-computed operands before it can be an active warning.
        frame = result.frame
        latest = frame.iloc[-1] if len(frame.index) else None
        recovered = (
            latest is not None
            and {"close", "ema20", "close_lag20"}.issubset(frame.columns)
            and all(latest[k] == latest[k] for k in ("close", "ema20", "close_lag20"))
            and not (latest["close"] < latest["ema20"] and latest["close"] < latest["close_lag20"])
        )
        rows.append(
            _row(
                result=result,
                side="sell",
                identity=f"sell:exit:{event.event_id}",
                title="抵扣价退出提醒（研究代理）",
                summary=event.reason_cn,
                state="cleared"
                if recovered and event_day != _day(frame.index[-1].date())
                else "confirmed",
                event_date=event_day,
                state_changed_date=event_day,
                rule_id=event.rule_id,
                key_prices=sum(
                    (
                        _price(label, evidence.get(key))
                        for key, label in (
                            ("ema20", "EMA20"),
                            ("close_lag20", "20 日抵扣价"),
                            ("close", "触发日收盘价"),
                        )
                    ),
                    [],
                ),
                next_step_cn="结合原计划退出条件复核",
                provenance="research_proxy",
            )
        )
    # Keep cleared top and wave lifecycles visible; cap only old buy/bottom
    # background so a large set of historical bottoms cannot crowd the page.
    current = [row for row in rows if row["is_recent"]]
    history = [row for row in rows if not row["is_recent"]]
    history.sort(key=lambda row: row["state_changed_date"] or "", reverse=True)
    lifecycle_history = [
        row for row in history if row["id"].startswith(("sell:top:", "sell:wave:"))
    ]
    other_history = [row for row in history if row not in lifecycle_history]
    ordered = current + lifecycle_history + other_history[:12]
    unique: list[dict] = []
    seen: set[str] = set()
    for row in ordered:
        if row["id"] not in seen:
            unique.append(row)
            seen.add(row["id"])
    return unique


__all__ = ["build_signal_rows"]
