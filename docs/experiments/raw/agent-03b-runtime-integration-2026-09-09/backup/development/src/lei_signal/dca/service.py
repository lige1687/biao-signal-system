"""定投服务编排：每周应投清单、标的状态看板、埋伏触发板、证据账本读取。

规则全部来自归档（见 configs/dca_evidence.json）；本层只做计算与拼装，
不发明规则。供 routes/dca.py 调用；加载器/证据路径可注入供单测。

数据状态（总控 R02 / 契约 v1.2 §2）：每个状态按**真实依赖**分别返回
active(true/false/null)、current、health/reason、data_refs：
- deep20 只依赖该标的价格；bottom_zone 还依赖市场宽度；
- 缺数据=null（无法判定），条件不满足=false（未触发）——两者分开；
- current=true 仅在该状态全部必要依赖确认及时且有效时成立；发布策略
  未核实/日历不可知 → 依赖 health=unknown → current=None（未知不默认当前）；
- 旧字段（deep20/bottom_zone 布尔、data_freshness 等）保留为兼容别名。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd

from lei_signal.data_provenance import (
    COMPAT_UNKNOWN,
    MarketDataRef,
    SourcePolicy,
    assess_freshness,
    breadth_market,
    evidence_ref,
    file_generated_at,
    reference_calendar,
    rule_ref,
)
from lei_signal.dca.presets import PRESETS, TRACKED, Leg
from lei_signal.dca.state import TargetState, compute_state

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE = _REPO_ROOT / "configs" / "dca_evidence.json"

# 降级信封错误码（展示层据此给明确提示，不当正常空账本渲染）
EVIDENCE_MISSING = "EVIDENCE_FILE_MISSING"
EVIDENCE_CORRUPT = "EVIDENCE_JSON_CORRUPT"


def load_evidence(path: Path | None = None) -> dict:
    """读证据账本；缺失/损坏时返回可识别降级信封（200 可用，但 available=False）。"""
    p = path or DEFAULT_EVIDENCE
    if not p.is_file():
        return {
            "version": "",
            "available": False,
            "error_code": EVIDENCE_MISSING,
            "error_detail": f"证据账本文件不存在: {p}",
            "note": "证据账本缺失——所有历史期望/战绩引用不可用，"
                    "这不是「无结论」，是「读不到依据」",
            "state_expectations": {},
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {
            "version": "",
            "available": False,
            "error_code": EVIDENCE_CORRUPT,
            "error_detail": f"证据账本 JSON 解析失败: {e}",
            "note": "证据账本格式损坏——引用不可用，请检查 configs/dca_evidence.json",
            "state_expectations": {},
        }
    if not isinstance(data, dict):
        return {
            "version": "",
            "available": False,
            "error_code": EVIDENCE_CORRUPT,
            "error_detail": "证据账本顶层必须是 JSON 对象",
            "note": "证据账本结构异常——引用不可用",
            "state_expectations": {},
        }
    data.setdefault("available", True)
    return data


def evidence_meta(path: Path) -> dict:
    """账本级元信息：可用性 + 每条数字的 EvidenceRef（v1.2 含哈希）+ 规则引用。"""
    ev = load_evidence(path)
    ledger_version = str(ev.get("version") or "")
    refs = []
    if ev.get("available"):
        for key, entry in (ev.get("state_expectations") or {}).items():
            refs.append(evidence_ref(key, entry,
                                     ledger_version=ledger_version).to_dict())
        for key, entry in (ev.get("combos") or {}).items():
            refs.append(evidence_ref(f"combos.{key}", entry,
                                     ledger_version=ledger_version).to_dict())
        for key in ("ambush_template", "rebalance_policy"):
            if ev.get(key):
                refs.append(evidence_ref(key, ev[key],
                                         ledger_version=ledger_version).to_dict())
    rules = [
        rule_ref("dca_state_thresholds",
                 fallback_note="账本缺段时采用实验原值 deep20_gap=-0.20 / "
                               "bottom_zone_dd2y=-0.15（第十一轮口径）").to_dict(),
        rule_ref("breadth_position").to_dict(),
    ]
    return {
        "available": bool(ev.get("available")),
        "error_code": ev.get("error_code"),
        "error_detail": ev.get("error_detail"),
        "version": ledger_version,
        "path": str(path),
        "generated_at": file_generated_at(path),
        "rules": rules,
        "refs": refs,
        "note": "实验数字引用卡（v1.2）：每条带来源路径/内容哈希/状态/窗口/"
                "口径/适用策略/兼容性；status=unverified 或 compatibility="
                "unknown 的条目只显示限制说明，不得当依据引用",
    }


def _expectation(evidence: dict, key: str) -> dict | None:
    return (evidence.get("state_expectations") or {}).get(key)


def weekly_buy_list(
    legs: list[dict],
    base_amount: float,
    frequency: str = "weekly",
    rebalance: str = "quarterly",
    today: date | None = None,
) -> dict:
    """当期应投清单：等权拆分到各腿 + 再平衡提示。

    不含择时：金额与频率固定（一~十二轮：任何择时旋钮无益或有害）。
    base_amount 属用户输入（origin=user_input），不来自实验账本。
    """
    today = today or date.today()
    n = len(legs)
    per = round(base_amount / n, 2) if n else 0.0
    items = []
    for leg in legs:
        items.append({
            "code": leg["code"], "name": leg["name"], "role": leg.get("role", ""),
            "amount": per,
            "take_profit_basket_external": leg.get("take_profit"),
        })
    rebalance_due = False
    if rebalance == "quarterly":
        # 季度内第一周提示做再平衡（执行期口径与回测一致：季末后首个执行日）
        rebalance_due = _is_first_period_of_quarter(today, frequency)
    elif rebalance == "monthly":
        rebalance_due = today.day <= 7
    return {
        "as_of": today.isoformat(),
        "frequency": frequency,
        "base_amount": base_amount,
        "base_amount_origin": "user_input",
        "per_leg_amount": per,
        "items": items,
        "rebalance_hint": {
            "due": rebalance_due,
            "policy": rebalance,
            "note": "把各腿市值拉回等权（卖涨多补跌多）；组合内不做止盈"
                    "（dca-joint-policy：组合内止盈 0/12 判负）",
        },
    }


def _is_first_period_of_quarter(today: date, frequency: str) -> bool:
    if frequency == "weekly":
        return today.month in (1, 4, 7, 10) and today.day <= 7
    return today.month in (1, 4, 7, 10)


def _price_ref(symbol: str, market: str, as_of: str | None,
               assessment) -> MarketDataRef:
    health = assessment.health if assessment is not None else (
        "missing" if not as_of else "unknown")
    return MarketDataRef(
        source_id=f"timing_cache:{symbol}",
        instrument_id=symbol,
        market=market,
        observed_at=as_of,
        available_at=None,           # 来源发布可用时间未核实（01D 审计后登记）
        generated_at=None,
        last_valid_at=as_of,
        health=health,
        reason=assessment.reason if assessment is not None else "无行情数据",
        calendar_ref=(assessment.calendar.to_dict()
                      if assessment is not None and assessment.calendar else None),
        as_of_cutoff=assessment.as_of_cutoff if assessment is not None else None,
    )


def _current(active: bool | None, dep_healths: list[str]) -> bool | None:
    """current：active 且全部依赖确认及时（fresh）才 True；确认滞后为 False；
    有任一依赖 unknown（无法判定）→ None（未知不默认当前）。"""
    if active is not True:
        return None
    if any(h == "unknown" for h in dep_healths):
        return None
    return all(h == "fresh" for h in dep_healths)


def targets_state(
    loader: Callable[[str], pd.DataFrame | None],
    evidence: dict,
    symbols: list[tuple[str, str]] | None = None,
    b200_cn: float | None = None,
    b200_us: float | None = None,
    breadth_meta: dict[str, MarketDataRef] | None = None,
    *,
    now=None,
    policies: dict[str, SourcePolicy] | None = None,
    calendars: dict | None = None,
) -> list[dict]:
    """跟踪池状态看板：每标的状态 + 期望引用 + 按依赖的结构化信号状态。"""
    policies = policies or {}
    calendars = calendars or {}
    ledger_version = str(evidence.get("version") or "")
    out = []
    for sym, name in (symbols or list(TRACKED)):
        market = breadth_market(sym)
        b200 = b200_us if sym.startswith("^") else b200_cn
        st: TargetState = compute_state(sym, name, loader(sym), b200)
        d = st.to_dict()
        # 价格依赖评价（行情缺/未来/日历不可知均显式降级，不默认当前）
        assessment = None
        if st.as_of:
            cal = calendars.get(market)
            if cal is None:
                cal = reference_calendar(market)
            assessment = assess_freshness(
                st.as_of, market, now=now,
                policy=policies.get(market), calendar=cal)
        price = _price_ref(sym, market, st.as_of, assessment)
        bref = (breadth_meta or {}).get("us" if sym.startswith("^") else "cn")
        bref_d = bref.to_dict() if bref else None
        # 宽度依赖健康：有引用卡用它的 health；值存在但无引用卡=unknown
        if bref is not None:
            breadth_health = str(bref.health)
        else:
            breadth_health = "missing" if b200 is None else "unknown"
        price_health = price.health
        d["signals"] = {
            "deep20": {
                "active": st.deep20,
                "current": _current(st.deep20, [price_health]),
                "health": price_health,
                "reason": price.reason,
                "data_refs": [price.to_dict()],
                "note": "深超跌只依赖该标的价格；缺数据=null（无法判定）",
            },
            "bottom_zone": {
                "active": st.bottom_zone,
                "current": _current(st.bottom_zone, [price_health,
                                                     breadth_health]),
                "health": (breadth_health if breadth_health != "fresh"
                           else price_health),
                "reason": ("宽度缺失或不可判" if breadth_health == "missing"
                           else (bref.reason if bref else
                                 "宽度元信息未提供，发布节奏未核实")),
                "data_refs": [price.to_dict()] + ([bref_d] if bref_d else []),
                "note": "底部区域依赖价格+市场宽度；宽度缺失时 active=null",
            },
        }
        # ---- 兼容别名（round-01 字段，旧消费者仍在读）----
        d["data_freshness"] = {
            "as_of": st.as_of,
            "freshness": {"fresh": "ok", "incomplete": "partial"}.get(
                price_health, price_health),
            "lag_trading_days": (assessment.reference_lag_trading_days
                                 if assessment else None),
            "health": price_health,
            "reason": price.reason,
        }
        d["breadth_freshness"] = bref_d
        d["expectation"] = None
        d["expectation_ref"] = None
        if st.state_status in ("ok", "degraded"):
            entry_key = None
            if st.deep20 is True:
                entry_key = "deep20"
            elif st.bottom_zone is True:
                entry_key = "bottom_zone"
            elif st.tier == "low":
                entry_key = "tier_low"
            if entry_key:
                entry = _expectation(evidence, entry_key)
                d["expectation"] = entry
                d["expectation_ref"] = evidence_ref(
                    entry_key, entry, ledger_version=ledger_version,
                    compatibility=COMPAT_UNKNOWN).to_dict()
        out.append(d)
    return out


def triggers_board(
    loader: Callable[[str], pd.DataFrame | None],
    evidence: dict,
    symbols: list[tuple[str, str]] | None = None,
    b200_cn: float | None = None,
    b200_us: float | None = None,
    breadth_meta: dict[str, MarketDataRef] | None = None,
    *,
    now=None,
    policies: dict[str, SourcePolicy] | None = None,
    calendars: dict | None = None,
) -> dict:
    """埋伏触发板：按状态依赖列触发/不可判/缺数据，current 只认确认及时。"""
    states = targets_state(loader, evidence, symbols, b200_cn, b200_us,
                           breadth_meta, now=now, policies=policies,
                           calendars=calendars)

    def _rows(signal: str, want: bool) -> list[dict]:
        out = []
        for s in states:
            sig = (s.get("signals") or {}).get(signal) or {}
            if sig.get("active") is want and s["state_status"] != "insufficient_data":
                r = dict(s)
                r["current"] = sig.get("current")
                out.append(r)
        return out

    deep = _rows("deep20", True)
    bottom = _rows("bottom_zone", True)
    unjudgeable_deep = [s["symbol"] for s in states
                        if ((s.get("signals") or {}).get("deep20") or {})
                        .get("active") is None]
    unjudgeable_bottom = [s["symbol"] for s in states
                          if ((s.get("signals") or {}).get("bottom_zone") or {})
                          .get("active") is None]
    unavailable = [s["symbol"] for s in states
                   if s["state_status"] == "insufficient_data"]
    stale_triggers = [s["symbol"] for s in deep + bottom
                      if s["current"] is not True]
    tmpl = (evidence.get("ambush_template") or {})
    ledger_version = str(evidence.get("version") or "")
    note = ("路牌统计（只提示不判定）；触发状态用于预期管理与篮子外独立"
            "埋伏，不改变基础定投节奏（dca-trigger-gating：门控判负）")
    if stale_triggers:
        note += ("；⚠ 以下触发未确认及时（current 非 true：数据过期或发布"
                 f"节奏未核实，属历史状态，不称当前机会）：{','.join(stale_triggers)}")
    return {
        "as_of": states[0]["as_of"] if states else "",
        "deep20_triggered": [s["symbol"] for s in deep],
        "bottom_zone_triggered": [s["symbol"] for s in bottom],
        "deep20_triggered_as_of": {s["symbol"]: s["as_of"] for s in deep},
        "bottom_zone_triggered_as_of": {s["symbol"]: s["as_of"] for s in bottom},
        "stale_data_triggers": stale_triggers,
        "unjudgeable": {"deep20": unjudgeable_deep,
                        "bottom_zone": unjudgeable_bottom},
        "data_unavailable": unavailable,
        "detail": {"deep20": deep, "bottom_zone": bottom},
        "template": tmpl,
        "template_ref": evidence_ref("ambush_template", tmpl,
                                     ledger_version=ledger_version).to_dict()
        if isinstance(tmpl, dict) and tmpl else None,
        "note": note,
    }


def legs_from_preset(preset_id: str) -> list[dict]:
    return list(PRESETS[preset_id]["legs"])


def leg_dicts(legs: tuple[Leg, ...]) -> list[dict]:
    return [leg.__dict__ for leg in legs]
