"""MCP transport for LEI evidence and optional explicitly confirmed local records.

The default stdio transport has no listening socket. The optional HTTP
transport binds only to loopback; neither transport exposes file, URL, or
HTTP-method inputs to MCP clients.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

_FUND_CODE = re.compile(r"[0-9]{6}\Z")
_LOOPBACK = "127.0.0.1"


def _fund_code(value: str | None) -> str | None:
    if value is not None and not _FUND_CODE.fullmatch(value):
        raise ValueError("fund_code must be a fund identifier, not a path or URL")
    return value


def _bounded(value: int, *, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def create_server(
    context: Any = None,
    *,
    port: int = 8765,
    allow_confirmed_records: bool = False,
    workflow: Any = None,
    transactions: Any = None,
) -> Any:
    """Create a fresh SDK server; context injection keeps protocol tests offline."""
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.types import ToolAnnotations
    except ImportError as exc:
        raise RuntimeError(
            "MCP SDK is missing; install the pinned MCP requirements in the "
            "isolated runtime before starting this server"
        ) from exc

    if context is None:
        from lei_signal.integrations.gpt_context import SystemContext

        context = SystemContext()

    _bounded(port, name="port", minimum=1, maximum=65535)
    server = FastMCP(
        "lei-system" if allow_confirmed_records else "lei-system-readonly",
        instructions=(
            "Read LEI evidence. Always show product names and source dates. "
            "Records require an exact separate human confirmation. Never broker orders."
        ),
        host=_LOOPBACK,
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
    read_only_local = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=False,
    )
    read_only_public = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
    )

    @server.tool(annotations=read_only_public, structured_output=True)
    def overview(query: str = "", limit: int = 10) -> dict[str, Any]:
        """Read the LEI overview; query filters only system-upgrade goals.

        Other overview sections are unchanged. The default returns ten short
        goal evidence previews; use a specific query to find more relevant goals.
        """
        if not isinstance(query, str) or len(query) > 160 or "\x00" in query:
            raise ValueError("query must be text of at most 160 characters")
        return context.overview(
            query=query,
            limit=_bounded(limit, name="limit", minimum=1, maximum=20),
        )

    @server.tool(annotations=read_only_local, structured_output=True)
    def storage() -> dict[str, Any]:
        """Read fixed local volume identity and free space; never clean up or call the API."""
        return context.storage()

    @server.tool(annotations=read_only_local, structured_output=True)
    def portfolio(fund_code: str | None = None) -> dict[str, Any]:
        """Read the portfolio context, optionally for one fund identifier."""
        return context.portfolio(fund_code=_fund_code(fund_code))

    @server.tool(annotations=read_only_public, structured_output=True)
    def fundamentals(market: str = "cn", section: str = "observations") -> dict[str, Any]:
        """Read a fixed fundamentals section.

        Only observations use market selection. Other sections can make slow
        GET requests that refresh public data under the system's existing TTL.
        """
        if market not in {"cn", "us"}:
            raise ValueError("market must be cn or us")
        if section not in {
            "observations",
            "overview",
            "rates",
            "us-macro",
            "rates-history",
            "macro-history",
        }:
            raise ValueError("unsupported fundamentals section")
        return context.fundamentals(market=market, section=section)

    @server.tool(annotations=read_only_local, structured_output=True)
    def news(fund_code: str | None = None, limit: int = 20) -> dict[str, Any]:
        """Read existing news context; news does not create trading signals."""
        return context.news(
            fund_code=_fund_code(fund_code),
            limit=_bounded(limit, name="limit", minimum=1, maximum=20),
        )

    @server.tool(annotations=read_only_local, structured_output=True)
    def plans(fund_code: str | None = None) -> dict[str, Any]:
        """Read confirmed and pending plan context without changing it."""
        return context.plans(fund_code=_fund_code(fund_code))

    @server.tool(annotations=read_only_local, structured_output=True)
    def trades() -> dict[str, Any]:
        """Read existing trade records without placing or editing orders."""
        return context.trades()

    @server.tool(annotations=read_only_local, structured_output=True)
    def factors() -> dict[str, Any]:
        """Read registered factor status without running experiments."""
        return context.factors()

    @server.tool(annotations=read_only_local, structured_output=True)
    def research_search(query: str = "", limit: int = 10) -> dict[str, Any]:
        """Search the bounded LEI research catalog by text."""
        if not isinstance(query, str) or len(query) > 160 or "\x00" in query:
            raise ValueError("query must be text of at most 160 characters")
        return context.research_search(
            query=query,
            limit=_bounded(limit, name="limit", minimum=1, maximum=20),
        )

    @server.tool(annotations=read_only_local, structured_output=True)
    def research_report(name: str, max_chars: int = 12000) -> dict[str, Any]:
        """Read a named report from the existing research catalog."""
        if (
            not isinstance(name, str)
            or len(name) > 240
            or not name.startswith("docs/experiments/")
            or not name.endswith(".md")
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or any(char in name for char in ("\\", ":", "\x00", "\n", "\r"))
        ):
            raise ValueError("name must be an indexed docs/experiments report name")
        return context.research_report(
            name=name,
            max_chars=_bounded(max_chars, name="max_chars", minimum=1, maximum=12000),
        )

    @server.tool(annotations=read_only_local, structured_output=True)
    def latest_brief(slot: str | None = None) -> dict[str, Any]:
        """Read a saved 1135 information or 1440 confirmed-plan-review brief."""
        if slot not in {None, "1135", "1440"}:
            raise ValueError("slot must be 1135 or 1440")
        return context.latest_brief(slot=slot)

    @server.tool(annotations=read_only_local, structured_output=True)
    def opportunities() -> dict[str, Any]:
        """Read saved candidates by product name; no new scan or buy instruction."""
        return context.opportunities()

    @server.tool(annotations=read_only_public, structured_output=True)
    def analysis(symbol: str) -> dict[str, Any]:
        """Read one system product analysis; never borrow index prices for a fund."""
        if not re.fullmatch(r"[A-Za-z0-9.^]{1,24}", symbol):
            raise ValueError("invalid symbol")
        return context.analysis(symbol=symbol)

    @server.tool(annotations=read_only_local, structured_output=True)
    def daily_review(slot: str = "1440") -> dict[str, Any]:
        """Name-first holdings, confirmed conditions, candidate and source gaps."""
        if slot not in {"1135", "1440"}:
            raise ValueError("unsupported slot")
        return context.daily_review(slot=slot)

    @server.tool(annotations=read_only_local, structured_output=True)
    def plan_scenario(plan_id: str) -> dict[str, Any]:
        """Read conditional price picture and arithmetic from one saved plan."""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", plan_id):
            raise ValueError("invalid plan identity")
        return context.plan_scenario(plan_id=plan_id)

    if allow_confirmed_records:
        from lei_signal.integrations.chat_transactions import ChatTransactions, LocalAPIClient
        from lei_signal.integrations.chat_workflow import ConfirmedWorkflow, prepare_card

        workflow = workflow or ConfirmedWorkflow()
        transactions = transactions or ChatTransactions(LocalAPIClient())
        record_write = ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, openWorldHint=False
        )

        @server.tool(annotations=read_only_local, structured_output=True)
        def record_preview(
            kind: str, fields: dict, request_id: str, original_message: str, conversation_ref: str
        ) -> dict[str, Any]:
            """Pure proposal for watch/basis/fill/reconciliation. It is not confirmation."""
            return prepare_card(
                kind,
                fields,
                request_id,
                original_message=original_message,
                conversation_ref=conversation_ref,
            )

        @server.tool(annotations=record_write, structured_output=True)
        def record_confirm(card: dict, confirmation: dict) -> dict[str, Any]:
            """Only after the human confirms this exact card; never buy/sell orders."""
            return workflow.confirm(card, confirmation)

        @server.tool(annotations=read_only_local, structured_output=True)
        def plan_record(plan_id: str) -> dict[str, Any]:
            """Read a saved plan and content fingerprint before explicit activation."""
            return workflow.read_plan(plan_id)

        @server.tool(annotations=read_only_local, structured_output=True)
        def reconciliation(holding_id: str, nav: float, nav_date: str) -> dict[str, Any]:
            """Preview actual-share accounting using the system's same-product NAV."""
            return workflow.reconciliation(holding_id, nav, nav_date)

        @server.tool(annotations=read_only_local, structured_output=True)
        def trade_preview(message: str, request_id: str) -> dict[str, Any]:
            """Parse asserted past trade into a named confirmation card; no writes."""
            return transactions.preview_trade(message, request_id=request_id)

        @server.tool(annotations=record_write, structured_output=True)
        def trade_record(card: dict, confirmation: dict) -> dict[str, Any]:
            """Record a human-confirmed past transaction and read back; never orders."""
            return transactions.record_trade(card, confirmation)

        @server.tool(annotations=record_write, structured_output=True)
        def plan_discussion(message: str, symbol: str, request_id: str) -> dict[str, Any]:
            """Save a real user question in system discussion, without activating a plan."""
            return transactions.discuss_plan(message, symbol, request_id)

        @server.tool(annotations=record_write, structured_output=True)
        def plan_draft(fields: dict, source: dict, request_id: str) -> dict[str, Any]:
            """Save a source-bound draft; server checks provenance, no automatic activation."""
            return transactions.save_plan_draft(fields, source, request_id)

        @server.tool(annotations=record_write, structured_output=True)
        def holding_plan_link(holding_id: str, plan_id: str, confirmation: dict) -> dict[str, Any]:
            """Explicitly confirmed same-product holding/plan association and read-back."""
            return transactions.link_holding(holding_id, plan_id, confirmation)

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEI read-only MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default=_LOOPBACK)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-confirmed-records", action="store_true")
    args = parser.parse_args(argv)
    if args.host != _LOOPBACK:
        parser.error("only 127.0.0.1 is allowed; remote binding is disabled")
    if not 1 <= args.port <= 65535:
        parser.error("port must be from 1 to 65535")
    try:
        server = create_server(port=args.port, allow_confirmed_records=args.allow_confirmed_records)
    except (ImportError, RuntimeError) as exc:
        print(f"Cannot start LEI MCP: {exc}", file=sys.stderr)
        return 2
    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
