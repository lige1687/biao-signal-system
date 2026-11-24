"""Confirmed local records, using the original LEI plan/holding tables.

Receipt rows add provenance and actual broker/opening-basis evidence. They are
not a second plan or trade ledger. No function places broker orders.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lei_signal.integrations.chat_transactions import WorkflowError, _date, _request_id, fingerprint

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _past_date(value: str) -> str:
    value = _date(value)
    if value > datetime.now(SHANGHAI).date().isoformat():
        raise WorkflowError("未来日期不能作为实际持仓或平台确认")
    return value


KINDS = {
    "holding_watch",
    "activate_plan",
    "holding_basis",
    "broker_fill",
    "reconcile",
    "new_holding",
}


def prepare_card(
    kind: str, fields: dict, request_id: str, *, original_message: str, conversation_ref: str
) -> dict:
    """Pure proposal. Confirmation is a separate human action."""
    if kind not in KINDS or not isinstance(fields, dict):
        raise WorkflowError("不支持的记录类型")
    _request_id(request_id)
    if not original_message.strip() or not conversation_ref.strip():
        raise WorkflowError("需要原话和对话出处")
    card = {
        "kind": kind,
        "fields": fields,
        "request_id": request_id,
        "original_message": original_message,
        "conversation_ref": conversation_ref,
        "source_kind": "user_declared_in_codex",
        "is_broker_order": False,
    }
    card["fingerprint"] = fingerprint(card)
    return card


def _number(value, *, zero=False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkflowError("数值必须为有限非负数字")
    if not math.isfinite(value) or value < 0 or (not zero and value == 0):
        raise WorkflowError("数值缺失或不合理")
    return float(value)


def _read(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _receipts(conn, kind: str | None = None) -> list[dict]:
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name='codex_workflow_receipts'"
    ).fetchone():
        return []
    rows = conn.execute("SELECT * FROM codex_workflow_receipts ORDER BY created_at, request_id")
    return [
        {
            **dict(row),
            "card": json.loads(row["card_json"]),
            "result": json.loads(row["result_json"]),
        }
        for row in rows
        if kind is None or row["kind"] == kind
    ]


class ConfirmedWorkflow:
    """DB path is server configuration, never a tool/client input."""

    def __init__(
        self,
        db_path: str | None = None,
        *,
        context_loader: Callable | None = None,
        nav_loader: Callable | None = None,
    ):
        from lei_signal.api.config import sqlite_path

        self.db_path = str(db_path or sqlite_path())
        self.context_loader = context_loader or self._live_context
        if nav_loader is None:
            from lei_signal.portfolio.funddata import fetch_nav_history

            nav_loader = fetch_nav_history
        self.nav_loader = nav_loader

    @staticmethod
    def _live_context(symbol: str):
        from lei_signal.api.schemas import SymbolDetailDTO
        from lei_signal.integrations.gpt_context import SystemContext
        from lei_signal.plans.context import from_symbol_detail

        result = SystemContext().analysis(symbol)
        if not result["available"]:
            raise WorkflowError(f"同产品分析不可用：{result['errors']}")
        data = result["data"]
        meta = data.get("meta") or {}
        if (
            meta.get("is_intraday_forming")
            or meta.get("cache_fallback_used")
            or meta.get("stale")
            or meta.get("error")
            or not meta.get("last_bar_date")
        ):
            raise WorkflowError("行情时点或完成状态尚未核实")
        if str(meta["last_bar_date"])[:10] > datetime.now(SHANGHAI).date().isoformat():
            raise WorkflowError("不能使用未来行情")
        if data.get("symbol") != symbol:
            raise WorkflowError("分析对象与计划产品不一致")
        from lei_signal.api.portfolio_workspace import _expected_bar_date

        expected = _expected_bar_date(symbol, datetime.now(SHANGHAI))
        if expected is None or str(meta["last_bar_date"])[:10] < expected:
            raise WorkflowError("行情早于系统可核实的最近收盘日；节假日缺口需另核")
        return from_symbol_detail(SymbolDetailDTO.model_validate(data))

    def read_plan(self, plan_id: str) -> dict:
        from lei_signal.plans.store import get_plan

        with closing(_read(self.db_path)) as conn:
            plan = get_plan(conn, plan_id)
        if plan is None:
            raise WorkflowError("计划不存在")
        result = asdict(plan)
        return {"plan": result, "fingerprint": fingerprint(result)}

    def confirm(self, card: dict, confirmation: dict) -> dict:
        from lei_signal.storage.sqlite_store import connect

        body = {k: v for k, v in card.items() if k != "fingerprint"}
        if (
            card.get("kind") not in KINDS
            or fingerprint(body) != card.get("fingerprint")
            or confirmation.get("confirmed") is not True
            or confirmation.get("fingerprint") != card.get("fingerprint")
            or confirmation.get("request_id") != card.get("request_id")
        ):
            raise WorkflowError("需要用户确认展示的完整记录；内容变化须重新确认")
        _request_id(card["request_id"])
        with closing(connect(self.db_path)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS codex_workflow_receipts(
                request_id TEXT PRIMARY KEY, kind TEXT NOT NULL, fingerprint TEXT NOT NULL,
                card_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            try:
                prior = conn.execute(
                    "SELECT * FROM codex_workflow_receipts WHERE request_id=?",
                    (card["request_id"],),
                ).fetchone()
                if prior:
                    if prior["fingerprint"] != card["fingerprint"]:
                        raise WorkflowError("请求编号已用于不同内容，拒绝重复或改写")
                    conn.rollback()
                    return json.loads(prior["result_json"])
                result = json.loads(
                    json.dumps(self._apply(conn, card), ensure_ascii=False, allow_nan=False)
                )
                conn.execute(
                    "INSERT INTO codex_workflow_receipts VALUES(?,?,?,?,?,?)",
                    (
                        card["request_id"],
                        card["kind"],
                        card["fingerprint"],
                        json.dumps(card, ensure_ascii=False),
                        json.dumps(result, ensure_ascii=False),
                        datetime.now(SHANGHAI).isoformat(),
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        with closing(_read(self.db_path)) as conn:
            row = conn.execute(
                "SELECT result_json FROM codex_workflow_receipts WHERE request_id=?",
                (card["request_id"],),
            ).fetchone()
            if row is None or json.loads(row[0]) != result:
                raise WorkflowError("记录写入后读回不一致")
        return result

    def _apply(self, conn, card: dict) -> dict:
        from lei_signal.plans import evidence, store

        kind, fields = card["kind"], card["fields"]
        if kind == "new_holding":
            import re

            from lei_signal.portfolio.models import PortfolioHolding
            from lei_signal.portfolio.store import holding_id_for, upsert_holding

            if (
                not re.fullmatch(r"\d{6}", fields.get("code", ""))
                or not fields.get("name")
                or fields["name"] == fields["code"]
            ):
                raise WorkflowError("需要明确的基金名称和代码")
            if conn.execute(
                "SELECT 1 FROM portfolio_holdings WHERE code=?", (fields["code"],)
            ).fetchone():
                raise WorkflowError("产品已在持仓中，请用原持仓对账")
            if not conn.execute(
                "SELECT 1 FROM portfolio_groups WHERE group_key=?", (fields.get("group_key"),)
            ).fetchone():
                raise WorkflowError("请选择已有持仓分组")
            _number(fields.get("shares"), zero=True)
            _number(fields.get("cost"), zero=True)
            _number(fields.get("nav"))
            _past_date(fields.get("basis_date"))
            if not fields.get("evidence_ref") or not isinstance(
                fields.get("included_trade_ids"), list
            ):
                raise WorkflowError("需要实际份额来源和已包含的成交清单")
            for tid in fields["included_trade_ids"]:
                t = conn.execute(
                    "SELECT fund_code FROM fund_trades WHERE trade_id=?", (tid,)
                ).fetchone()
                if t is None or t["fund_code"] != fields["code"]:
                    raise WorkflowError("包含的成交与产品不一致")
            navs = self.nav_loader(fields["code"])
            point = next((n for n in navs if n.date == fields["basis_date"]), None)
            if point is None or point.unit_nav != fields["nav"]:
                raise WorkflowError("新持仓需要同产品且对应日期的系统净值")
            pid = holding_id_for(fields["name"])
            if conn.execute(
                "SELECT 1 FROM portfolio_holdings WHERE holding_id=?", (pid,)
            ).fetchone():
                raise WorkflowError("名称与现有持仓冲突，请核对代码和份额")
            holding = PortfolioHolding(
                pid,
                fields["group_key"],
                fields["name"],
                fields["code"],
                fields["shares"] * fields["nav"],
                (fields["shares"] * fields["nav"] / fields["cost"] - 1) * 100
                if fields["cost"]
                else None,
                as_of=fields["basis_date"],
            )
            upsert_holding(conn, holding)
            conn.execute(
                "INSERT INTO portfolio_holdings_nav VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    pid,
                    fields["code"],
                    point.unit_nav,
                    point.date,
                    fields["shares"],
                    fields["cost"],
                    point.unit_nav,
                    point.date,
                    datetime.now(SHANGHAI).isoformat(),
                ),
            )
            return {
                "status": "holding_created",
                "holding": asdict(holding),
                "note": "新持仓采用确认份额；技术条件仍需另关联计划。",
            }
        if kind == "holding_watch":
            from lei_signal.api.schemas import CreateHoldingWatchRequest

            if set(fields) - set(CreateHoldingWatchRequest.model_fields):
                raise WorkflowError("持仓观察字段超出已有系统定义")
            validated = CreateHoldingWatchRequest.model_validate(fields).model_dump()
            validated.pop("entered_on", None)
            pid = "codex_watch_" + fingerprint({"request_id": card["request_id"]})[:20]
            plan = store.create_plan(
                conn,
                **validated,
                plan_kind="holding_watch",
                plan_id=pid,
                source="user",
                commit=False,
            )
            store.add_annotation(
                conn,
                pid,
                ref_kind="codex_conversation",
                ref_id=card["conversation_ref"],
                kind="user_rationale",
                reason_cn=card["original_message"],
                author="user",
                commit=False,
            )
            return {
                "plan": asdict(plan),
                "status": "draft",
                "note": "观察草稿已保存，尚未启用条件判断，不替代原始入场计划。",
            }
        if kind == "activate_plan":
            from lei_signal.domain.rules_config import ruleset_version
            from lei_signal.plans.conformance import evaluate_draft_conformance

            plan = store.get_plan(conn, fields.get("plan_id"))
            if plan is None or fingerprint(asdict(plan)) != fields.get("plan_fingerprint"):
                raise WorkflowError("计划已变化或不存在，请重新展示后确认")
            today = datetime.now(SHANGHAI).date().isoformat()
            if plan.state != "draft" or not plan.valid_until or plan.valid_until < today:
                raise WorkflowError("计划不是有效期内的草稿")
            if plan.ruleset_version != ruleset_version():
                raise WorkflowError("计划规则版本已变化")
            ctx = self.context_loader(plan.symbol)
            if not ctx.last_bar_date or ctx.last_bar_date > today or ctx.cache_fallback_used:
                raise WorkflowError("分析日期或缓存资格不满足确认要求")
            report = evaluate_draft_conformance(plan, ctx)
            if not report.can_confirm:
                raise WorkflowError(
                    "系统计划检查未通过：" + ",".join(x.code for x in report.hard_issues)
                )
            kwargs = {"expected_fingerprint": evidence.plan_fingerprint(plan), "commit": False}
            if plan.plan_kind == "holding_watch":
                confirmed = store.confirm_holding_watch(
                    conn, plan.plan_id, entered_on=today, **kwargs
                )
            else:
                confirmed = store.confirm_plan(conn, plan.plan_id, **kwargs)
            return {"plan": asdict(confirmed), "status": confirmed.state}
        if kind == "holding_basis":
            h = conn.execute(
                "SELECT * FROM portfolio_holdings WHERE holding_id=?", (fields.get("holding_id"),)
            ).fetchone()
            if h is None or not h["code"] or h["code"] != fields.get("code"):
                raise WorkflowError("起始持仓与实际产品不一致")
            _number(fields.get("shares"), zero=True)
            _number(fields.get("cost"), zero=True)
            _past_date(fields.get("basis_date"))
            if not fields.get("evidence_ref") or not isinstance(
                fields.get("included_trade_ids"), list
            ):
                raise WorkflowError("需要确认来源及已包含的成交编号清单")
            for tid in fields["included_trade_ids"]:
                t = conn.execute(
                    "SELECT fund_code FROM fund_trades WHERE trade_id=?", (tid,)
                ).fetchone()
                if t is None or t["fund_code"] != h["code"]:
                    raise WorkflowError("包含的成交与产品不一致")
            if any(
                x["card"]["fields"]["holding_id"] == h["holding_id"] for x in _receipts(conn, kind)
            ):
                raise WorkflowError("已有起始依据，不能重复添加；修正须另行核对")
            return {
                "status": "basis_confirmed",
                "holding_id": h["holding_id"],
                "product_name": h["name"],
                "fields": fields,
                "note": "尚未改动持仓市值。",
            }
        if kind == "broker_fill":
            trade = conn.execute(
                "SELECT * FROM fund_trades WHERE trade_id=?", (fields.get("trade_id"),)
            ).fetchone()
            if trade is None or trade["fund_code"] != fields.get("code"):
                raise WorkflowError("平台确认必须绑定同产品的已有成交记录")
            _number(fields.get("shares"))
            _number(fields.get("fee"), zero=True)
            if fields.get("cash_amount") is not None:
                _number(fields["cash_amount"])
            _past_date(fields.get("fill_date"))
            if not fields.get("evidence_ref") or fields["fill_date"] < trade["trade_date"]:
                raise WorkflowError("需要平台确认出处和合理的确认日期")
            if any(
                x["card"]["fields"]["trade_id"] == trade["trade_id"] for x in _receipts(conn, kind)
            ):
                raise WorkflowError("该成交已有平台确认，不能重复增加份额")
            return {
                "status": "broker_fill_confirmed",
                "trade_id": trade["trade_id"],
                "fields": fields,
                "side": trade["side"],
            }
        if kind == "reconcile":
            proposal = self._reconciliation(
                conn, fields["holding_id"], fields["nav"], fields["nav_date"]
            )
            if proposal["status"] != "ready" or proposal["fingerprint"] != fields.get(
                "proposal_fingerprint"
            ):
                raise WorkflowError("对账资料不齐或展示后的资料已变化")
            from lei_signal.portfolio.store import list_holdings, upsert_holding

            holding = next(x for x in list_holdings(conn) if x.holding_id == fields["holding_id"])
            updated = replace(
                holding,
                market_value=proposal["market_value"],
                return_pct=proposal["return_pct"],
                as_of=fields["nav_date"],
            )
            upsert_holding(conn, updated)
            # Future NAV refreshes must use the confirmed shares/cost, rather than
            # reverting this row to shares inferred from the old screenshot.
            conn.execute(
                "UPDATE portfolio_holdings_nav SET implied_shares=?,cost_value=? "
                "WHERE holding_id=?",
                (proposal["shares"], proposal["cost"], holding.holding_id),
            )
            return {
                "status": "reconciled",
                "holding": asdict(updated),
                "shares": proposal["shares"],
                "cost": proposal["cost"],
                "included_trade_ids": proposal["included_trade_ids"],
            }
        raise WorkflowError("不支持的操作")

    def reconciliation(self, holding_id: str, nav: float, nav_date: str) -> dict:
        with closing(_read(self.db_path)) as conn:
            return self._reconciliation(conn, holding_id, nav, nav_date)

    @staticmethod
    def _reconciliation(conn, holding_id: str, nav: float, nav_date: str) -> dict:
        _number(nav)
        _date(nav_date)
        h = conn.execute(
            "SELECT * FROM portfolio_holdings WHERE holding_id=?", (holding_id,)
        ).fetchone()
        if h is None:
            raise WorkflowError("持仓不存在")
        nav_row = conn.execute(
            "SELECT * FROM portfolio_holdings_nav WHERE holding_id=?", (holding_id,)
        ).fetchone()
        if (
            nav_row is None
            or nav_row["code"] != h["code"]
            or nav_row["latest_nav_date"] != nav_date
            or nav_row["latest_nav"] != nav
        ):
            raise WorkflowError("必须采用系统保存的同产品净值及其真实日期")
        if nav_date > datetime.now(SHANGHAI).date().isoformat():
            raise WorkflowError("不能使用未来净值")
        basis = next(
            (
                r["card"]["fields"]
                for r in _receipts(conn, "holding_basis")
                if r["card"]["fields"]["holding_id"] == holding_id
            ),
            None,
        )
        if basis is None:
            basis = next(
                (
                    r["card"]["fields"]
                    for r in _receipts(conn, "new_holding")
                    if r["result"]["holding"]["holding_id"] == holding_id
                ),
                None,
            )
        if basis is None:
            return {
                "status": "pending",
                "product_name": h["name"],
                "missing": ["起始实际份额、成本、日期和已包含的成交"],
            }
        if nav_date < basis["basis_date"]:
            raise WorkflowError("净值日期早于起始持仓日期")
        fills = {
            r["card"]["fields"]["trade_id"]: r["card"]["fields"]
            for r in _receipts(conn, "broker_fill")
        }
        trades = conn.execute(
            "SELECT * FROM fund_trades WHERE fund_code=? ORDER BY trade_date,created_at,trade_id",
            (h["code"],),
        ).fetchall()
        shares, cost = basis["shares"], basis["cost"]
        included, missing = list(basis["included_trade_ids"]), []
        for trade in trades:
            if trade["trade_id"] in included:
                continue
            if trade["trade_date"] < basis["basis_date"]:
                missing.append(f"确认早期成交是否已包含：{trade['trade_id']}")
                continue
            fill = fills.get(trade["trade_id"])
            if fill is None:
                missing.append(f"平台确认份额/费用：{trade['trade_id']}")
                continue
            if fill["fill_date"] > nav_date:
                missing.append(f"净值日期早于成交确认：{trade['trade_id']}")
                continue
            units = fill["shares"]
            if trade["side"] == "buy":
                if fill["fee"] and not fill.get("cash_amount"):
                    missing.append(f"确认实际支付总金额（含费用）：{trade['trade_id']}")
                    continue
                shares += units
                cost += fill.get("cash_amount") or trade["amount"]
            else:
                if units > shares:
                    raise WorkflowError("赎回份额超过已核实持仓，不能更新")
                cost *= (shares - units) / shares if shares else 0
                shares -= units
            included.append(trade["trade_id"])
        market_value = round(shares * nav, 4)
        result = {
            "status": "pending" if missing else "ready",
            "holding_id": holding_id,
            "product_name": h["name"],
            "code": h["code"],
            "shares": shares,
            "cost": round(cost, 4),
            "market_value": market_value,
            "return_pct": round((market_value / cost - 1) * 100, 6) if cost else None,
            "nav": nav,
            "nav_date": nav_date,
            "missing": missing,
            "included_trade_ids": included,
            "snapshot_before": dict(h),
            "nav_source_before": dict(nav_row),
            "note": "只采用确认的起始份额与平台份额；系统估算份额不参与。",
        }
        result["fingerprint"] = fingerprint(result)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Confirmed local records, never broker orders")
    parser.add_argument(
        "action",
        choices=(
            "preview",
            "confirm",
            "read-plan",
            "reconcile",
            "trade-preview",
            "trade-confirm",
            "plan-discuss",
            "plan-draft",
            "holding-link",
        ),
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--plan-id")
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text()) if args.input else {}
    service = ConfirmedWorkflow()
    if args.action == "preview":
        result = prepare_card(**payload)
    elif args.action == "confirm":
        result = service.confirm(payload["card"], payload["confirmation"])
    elif args.action == "read-plan":
        result = service.read_plan(args.plan_id)
    elif args.action == "reconcile":
        result = service.reconciliation(**payload)
    else:
        from lei_signal.integrations.chat_transactions import ChatTransactions, LocalAPIClient

        bridge = ChatTransactions(LocalAPIClient())
        if args.action == "trade-preview":
            result = bridge.preview_trade(**payload)
        elif args.action == "trade-confirm":
            result = bridge.record_trade(**payload)
        elif args.action == "plan-discuss":
            result = bridge.discuss_plan(**payload)
        elif args.action == "plan-draft":
            result = bridge.save_plan_draft(**payload)
        else:
            result = bridge.link_holding(**payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
