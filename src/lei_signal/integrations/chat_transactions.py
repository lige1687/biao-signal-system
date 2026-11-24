"""Bounded chat bridge to the existing plan and fund trade APIs.

The server owns source binding, plan conformance, trade accounting and storage.
Cards returned here are immutable snapshots for a separate user confirmation.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


class WorkflowError(ValueError):
    pass


def fingerprint(value: dict[str, Any]) -> str:
    data = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(data.encode()).hexdigest()


def _request_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value):
        raise WorkflowError("需要稳定的请求编号（8–128 位字母、数字或 ._:-）")
    return value


def _plan_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise WorkflowError("计划编号格式无效")
    return value


def _date(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise WorkflowError("请先核对实际成交日期，格式 YYYY-MM-DD") from exc
    return value


def _call(transport: Any, method: str, path: str, payload: dict | None = None) -> Any:
    response = transport.request(method, path, json=payload)
    data = response.json()
    if response.status_code >= 400:
        raise WorkflowError(f"系统接口 {method} {path} 返回 {response.status_code}: {data}")
    return data


class LocalAPIClient:
    """HTTP transport restricted to a fixed loopback origin and API paths."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", client: Any = None):
        import httpx

        parts = urlsplit(base_url)
        if (
            parts.scheme != "http"
            or parts.hostname not in {"127.0.0.1", "localhost"}
            or parts.username
            or parts.password
            or parts.path not in {"", "/"}
            or parts.query
            or parts.fragment
        ):
            raise WorkflowError("仅允许固定本机 HTTP API 地址")
        self._client = client or httpx.Client(
            base_url=base_url, timeout=15, trust_env=False, follow_redirects=False
        )

    def request(self, method: str, path: str, json: dict | None = None) -> Any:
        allowed = {
            "GET": {"/api/portfolio", "/api/copilot/trades", "/api/portfolio/workspace"},
            "POST": {
                "/api/agent/chat",
                "/api/plans",
                "/api/copilot/trades/preview",
                "/api/copilot/trades",
            },
        }
        dynamic = (
            bool(re.fullmatch(r"/api/plans/[A-Za-z0-9_-]{1,128}(?:/conformance)?", path))
            and method == "GET"
        )
        dynamic = dynamic or (
            method == "POST"
            and bool(re.fullmatch(r"/api/plans/[A-Za-z0-9_-]{1,128}/confirm", path))
        )
        dynamic = dynamic or (
            method == "PUT"
            and bool(re.fullmatch(r"/api/portfolio/holdings/[A-Za-z0-9_-]{1,128}/plan", path))
        )
        if path not in allowed.get(method, set()) and not dynamic:
            raise WorkflowError("接口路径不在允许范围")
        return self._client.request(method, path, json=json)


class ChatTransactions:
    def __init__(self, transport: Any):
        self.transport = transport

    def discuss_plan(
        self, message: str, symbol: str, request_id: str, session_id: str | None = None
    ) -> dict:
        """Enroll the real user question; the server freezes source identity."""
        _request_id(request_id)
        if not message.strip() or not symbol.strip():
            raise WorkflowError("需要原问题和明确标的")
        body = {
            "message": message,
            "symbol": symbol,
            "context_kind": "symbol",
            "client_request_id": request_id,
        }
        if session_id:
            body["session_id"] = session_id
        answer = _call(self.transport, "POST", "/api/agent/chat", body)
        if not answer.get("question_id") or not answer.get("session_id"):
            raise WorkflowError("系统未返回可追溯的原问题，不能保存对话草稿")
        return answer

    def save_plan_draft(self, fields: dict, source: dict, request_id: str) -> dict:
        """Create a draft with server-verified question provenance."""
        _request_id(request_id)
        allowed = {
            "symbol",
            "module",
            "direction",
            "ruleset_version",
            "reason",
            "valid_until",
            "entry_rule_id",
            "entry_lifecycle_id",
            "entry_trigger_cn",
            "entry_price_ref",
            "invalidation_price",
            "target_b_price",
            "target_b_source",
            "reward_risk_at_plan",
            "thesis_cn",
            "invalidation_criteria_cn",
            "drawdown_playbook_cn",
            "take_profit_plan_cn",
            "stop_plan_cn",
        }
        if set(fields) - allowed:
            raise WorkflowError("计划字段超出既有系统草稿接口")
        qid, sid = source.get("question_id"), source.get("session_id")
        if not isinstance(qid, int) or qid < 1 or not isinstance(sid, str) or not sid:
            raise WorkflowError("需要系统返回的原问题编号与会话编号")
        if source.get("resolved_symbol") and source["resolved_symbol"] != fields.get("symbol"):
            raise WorkflowError("问题标的与草稿标的不一致")
        body = dict(
            fields, client_request_id=request_id, source_question_id=qid, source_session_id=sid
        )
        created = _call(self.transport, "POST", "/api/plans", body)
        plan_id = _plan_id(created["plan_id"])
        current = _call(self.transport, "GET", f"/api/plans/{plan_id}")
        if current["plan_id"] != created["plan_id"] or current["state"] != "draft":
            raise WorkflowError("草稿回读未验证")
        try:
            conformance = _call(self.transport, "GET", f"/api/plans/{plan_id}/conformance")
        except WorkflowError as exc:
            conformance = {"can_confirm": False, "unavailable": str(exc)}
        return {
            "plan": current,
            "fingerprint": fingerprint(current),
            "conformance": conformance,
            "request_id": request_id,
            "source_question_id": qid,
        }

    def confirm_plan(
        self, plan_id: str, confirmation: dict, expected_fingerprint: str, expected_request_id: str
    ) -> dict:
        _plan_id(plan_id)
        _request_id(expected_request_id)
        if confirmation.get("confirmed") is not True or confirmation.get("plan_id") != plan_id:
            raise WorkflowError("需要用户明确确认该计划编号")
        if confirmation.get("request_id") != expected_request_id:
            raise WorkflowError("确认请求编号与草稿请求编号不一致")
        if confirmation.get("fingerprint") != expected_fingerprint:
            raise WorkflowError("确认的计划内容与展示内容不一致")
        current = _call(self.transport, "GET", f"/api/plans/{plan_id}")
        if fingerprint(current) != expected_fingerprint or current["state"] != "draft":
            raise WorkflowError("草稿已变化；请重新核对")
        report = _call(self.transport, "GET", f"/api/plans/{plan_id}/conformance")
        if not report.get("can_confirm"):
            raise WorkflowError("系统符合性检查未通过")
        saved = _call(self.transport, "POST", f"/api/plans/{plan_id}/confirm", {})
        readback = _call(self.transport, "GET", f"/api/plans/{plan_id}")
        if readback["plan_id"] != saved["plan_id"] or readback["state"] != saved["state"]:
            raise WorkflowError("计划确认回读未验证")
        return readback

    def preview_trade(self, message: str, request_id: str | None = None) -> dict:
        """Parse only an asserted past trade. Ambiguous speech remains pending."""
        if not message.strip():
            raise WorkflowError("需要成交原话")
        date_match = re.search(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)", message)
        # Existing best-effort amount parser can read the year as the amount.
        parse_text = message.replace(date_match.group(1), " ") if date_match else message
        from lei_signal.integrations.gpt_context import product_identities

        names = {symbol[:6]: value["name"] for symbol, value in product_identities().items()}
        try:
            portfolio = _call(self.transport, "GET", "/api/portfolio")
            names.update(
                {
                    h.get("code"): h.get("name")
                    for g in portfolio.get("groups", [])
                    for h in g.get("holdings", [])
                    if h.get("name") and h.get("name") != h.get("code")
                }
            )
        except WorkflowError:
            pass
        if not re.search(r"(?<!\d)\d{6}(?!\d)", parse_text):

            def normalized(text):
                return re.sub(r"\([^)]*\)|（[^）]*）|\s+", "", text)

            matches = {
                code
                for code, name in names.items()
                if code
                and len(str(code)) == 6
                and normalized(name)
                and normalized(name) in normalized(message)
            }
            if len(matches) == 1:
                parse_text += " " + next(iter(matches))
        parsed = _call(
            self.transport, "POST", "/api/copilot/trades/preview", {"message": parse_text}
        )
        hypothetical = bool(
            re.search(
                r"如果|假如|假设|打算|计划|准备|想买|想卖|可能|要是|尚未|还没|没有|未成交|未确认|未买|未卖|撤单|取消|撤回|别记|不要记|跌到|涨到|站上|等到|才买",
                message,
            )
        )
        sides = {
            "buy" if re.search(r"买|申购|加仓", message) else "",
            "sell" if re.search(r"卖|赎回|减仓", message) else "",
        } - {""}
        explicit_date = date_match is not None
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        trade_date = date_match.group(1) if date_match else None
        if not date_match:
            for term, days in (("前天", 2), ("昨天", 1), ("今天", 0)):
                if term in message:
                    trade_date = (today - timedelta(days=days)).isoformat()
                    explicit_date = True
                    break
        missing = list(parsed.get("missing") or [])
        if not explicit_date:
            missing.append("明确成交日期")
        if hypothetical:
            missing.append("实际成交声明")
        if not re.search(r"买了|卖了|申购了|赎回了|成交|已买|已卖", message):
            missing.append("实际成交声明")
        if len(sides) != 1:
            missing.append("唯一买卖方向")
        codes = set(re.findall(r"(?<!\d)\d{6}(?!\d)", parse_text))
        if len(codes) != 1:
            missing.append("唯一产品代码")
        if re.search(r"价格|单价|净值|\d+(?:\.\d+)?\s*份", parse_text):
            missing.append("需分别核对成交金额与价格/份额")
        if not parsed.get("fund_code") or not parsed.get("amount"):
            missing.append("产品代码或金额")
        card = {
            "original_message": message,
            "fund_code": parsed.get("fund_code"),
            "fund_name": names.get(parsed.get("fund_code"))
            or parsed.get("fund_name")
            or "名称待核对",
            "side": next(iter(sides)) if len(sides) == 1 else None,
            "amount": parsed.get("amount"),
            "trade_date": trade_date,
            "missing": sorted(set(missing)),
            "status": "pending",
        }
        if card["fund_name"] in {"名称待核对", card["fund_code"]}:
            card["missing"].append("产品名称待核对")
        if card["trade_date"] and _date(card["trade_date"]) > today.isoformat():
            card["missing"].append("未来日期不能作为已成交记录")
        if request_id is not None:
            card["request_id"] = _request_id(request_id)
        if not card["missing"]:
            _date(card["trade_date"])
            card["status"] = "confirmable"
        card["fingerprint"] = fingerprint(card)
        return card

    def record_trade(self, card: dict, confirmation: dict) -> dict:
        snapshot = {k: v for k, v in card.items() if k != "fingerprint"}
        if (
            fingerprint(snapshot) != card.get("fingerprint")
            or confirmation.get("fingerprint") != card.get("fingerprint")
            or confirmation.get("confirmed") is not True
            or card.get("status") != "confirmable"
            or card.get("missing")
        ):
            raise WorkflowError("成交确认卡不完整或已变化")
        request_id = _request_id(confirmation.get("request_id"))
        if card.get("request_id") and request_id != card["request_id"]:
            raise WorkflowError("确认请求编号与展示的成交卡不一致")
        if card.get("side") not in {"buy", "sell"}:
            raise WorkflowError("买卖方向不明确")
        _date(card["trade_date"])
        if card["trade_date"] > datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat():
            raise WorkflowError("未来日期不能记为已成交")
        if not re.fullmatch(r"[0-9]{6}", card.get("fund_code", "")):
            raise WorkflowError("需要准确基金代码")
        amount = card.get("amount")
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
            or amount <= 0
        ):
            raise WorkflowError("金额必须为正数")
        payload = {k: card[k] for k in ("fund_code", "fund_name", "side", "amount", "trade_date")}
        payload["request_id"] = request_id
        if confirmation.get("plan_id"):
            payload["plan_id"] = _plan_id(confirmation["plan_id"])
        saved = _call(self.transport, "POST", "/api/copilot/trades", payload)
        ledger = _call(self.transport, "GET", "/api/copilot/trades")
        matches = [t for t in ledger["trades"] if t["trade_id"] == saved["trade_id"]]
        if len(matches) != 1 or any(
            matches[0].get(k) != payload[k] for k in ("fund_code", "side", "amount", "trade_date")
        ):
            raise WorkflowError("成交台账回读未验证")
        return matches[0]

    def reconcile_holdings(self) -> dict:
        """Read-only discrepancy preview; old holdings are never inserted as trades."""
        portfolio = _call(self.transport, "GET", "/api/portfolio")
        ledger = _call(self.transport, "GET", "/api/copilot/trades")
        positions = {p["fund_code"]: p for p in ledger.get("positions", [])}
        rows = []
        for group in portfolio.get("groups", []):
            for h in group.get("holdings", []):
                p = positions.get(h.get("code"))
                rows.append(
                    {
                        "holding_id": h["holding_id"],
                        "code": h.get("code"),
                        "product_name": h.get("name") or "名称待核对",
                        "snapshot_value": h.get("market_value"),
                        "ledger_position": p,
                        "status": "needs_opening_basis" if not p else "needs_verification",
                        "pending": ["原始份额", "原始成本", "费用", "券商确认记录"],
                    }
                )
        return {
            "portfolio_as_of": portfolio.get("as_of"),
            "rows": rows,
            "ledger_trade_count": len(ledger.get("trades", [])),
            "note": "快照市值不能倒推出份额或成交；本结果未改动任何台账。",
        }

    def link_holding(self, holding_id: str, plan_id: str, confirmation: dict) -> dict:
        _plan_id(holding_id)
        _plan_id(plan_id)
        shown = {"holding_id": holding_id, "plan_id": plan_id}
        if confirmation.get("confirmed") is not True or confirmation.get(
            "fingerprint"
        ) != fingerprint(shown):
            raise WorkflowError("需要确认持仓与该计划的准确关联")
        _call(
            self.transport,
            "PUT",
            f"/api/portfolio/holdings/{holding_id}/plan",
            {"plan_id": plan_id},
        )
        workspace = _call(self.transport, "GET", "/api/portfolio/workspace")
        row = next(
            (x for x in workspace.get("items", []) if x.get("holding_id") == holding_id), None
        )
        if not row or (row.get("plan") or {}).get("plan_id") != plan_id:
            raise WorkflowError("关联后的持仓计划读回未验证")
        return row
