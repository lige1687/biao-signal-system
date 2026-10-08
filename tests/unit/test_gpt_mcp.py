"""Exercise the real MCP SDK over a subprocess stdio transport."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

_SERVER = """
import sys
from lei_signal.integrations.gpt_mcp import create_server

class FakeContext:
    def __getattr__(self, name):
        if name == "factors":
            def fail():
                raise RuntimeError("source unavailable")
            return fail
        def read(**kwargs):
            return {
                "view": name,
                "available": True,
                "generated_at": "2026-10-08T00:00:00+08:00",
                "data": kwargs,
                "sources": ["fixture"],
                "limitations": [],
                "errors": [],
            }
        return read

create_server(FakeContext(), port=int(sys.argv[2]) if len(sys.argv) > 2 else 8765).run(
    transport=sys.argv[1]
)
"""


def _result_data(result) -> dict:
    assert not result.isError, result
    data = result.structuredContent
    assert isinstance(data, dict), result
    return data


def test_real_stdio_roundtrip_and_read_only_boundary() -> None:
    async def exercise() -> None:
        repo = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join((str(repo / "src"), env.get("PYTHONPATH", "")))
        params = StdioServerParameters(
            command=sys.executable,
            args=["-c", _SERVER, "stdio"],
            env=env,
            cwd=str(repo),
        )
        async with stdio_client(params) as (read, write):  # noqa: SIM117
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert initialized.serverInfo.name == "lei-system-readonly"

                tools = (await session.list_tools()).tools
                expected = {
                    "overview",
                    "portfolio",
                    "fundamentals",
                    "news",
                    "plans",
                    "trades",
                    "factors",
                    "research_search",
                    "research_report",
                    "latest_brief",
                    "opportunities",
                    "analysis",
                    "daily_review",
                    "plan_scenario",
                }
                assert {tool.name for tool in tools} == expected
                fundamentals_schema = next(
                    tool.inputSchema for tool in tools if tool.name == "fundamentals"
                )
                assert "refresh" not in fundamentals_schema.get("properties", {})
                assert all(
                    tool.annotations is not None
                    and tool.annotations.readOnlyHint is True
                    and tool.annotations.destructiveHint is False
                    for tool in tools
                )
                assert {tool.name for tool in tools if tool.annotations.openWorldHint is True} == {
                    "overview",
                    "fundamentals",
                    "analysis",
                }
                assert all(
                    tool.annotations.openWorldHint is False
                    for tool in tools
                    if tool.name not in {"overview", "fundamentals", "analysis"}
                )

                overview = _result_data(
                    await session.call_tool("overview", {"query": "持仓", "limit": 3})
                )
                assert overview["data"] == {"query": "持仓", "limit": 3}
                assert (await session.call_tool("overview", {"limit": 21})).isError
                assert (await session.call_tool("overview", {"query": "x" * 161})).isError
                assert (await session.call_tool("overview", {"query": "x\x00y"})).isError

                portfolio = _result_data(
                    await session.call_tool("portfolio", {"fund_code": "510300"})
                )
                assert portfolio["view"] == "portfolio"
                assert portfolio["data"] == {"fund_code": "510300"}
                assert portfolio["sources"] == ["fixture"]
                assert portfolio["generated_at"].startswith("2026-10-08")

                search = _result_data(
                    await session.call_tool("research_search", {"query": "ETF", "limit": 2})
                )
                assert search["data"] == {"query": "ETF", "limit": 2}
                fundamentals = _result_data(
                    await session.call_tool(
                        "fundamentals", {"market": "us", "section": "rates-history"}
                    )
                )
                assert fundamentals["data"] == {"market": "us", "section": "rates-history"}
                report_name = "docs/experiments/example-2026-10-08.md"
                report = _result_data(
                    await session.call_tool("research_report", {"name": report_name})
                )
                assert report["data"] == {"name": report_name, "max_chars": 12000}
                brief = _result_data(await session.call_tool("latest_brief", {"slot": "1135"}))
                assert brief["data"] == {"slot": "1135"}

                assert (await session.call_tool("portfolio", {"fund_code": "../secret"})).isError
                assert (await session.call_tool("research_report", {"name": "/etc/passwd"})).isError
                assert (
                    await session.call_tool(
                        "research_report", {"name": "docs/experiments/../private.md"}
                    )
                ).isError
                assert (await session.call_tool("latest_brief", {"slot": "yesterday"})).isError
                assert (await session.call_tool("news", {"limit": 1000})).isError
                assert (await session.call_tool("fundamentals", {"section": "refresh"})).isError
                assert (await session.call_tool("factors", {})).isError
                assert (await session.call_tool("execute_trade", {})).isError

    asyncio.run(exercise())


def test_loopback_http_roundtrip() -> None:
    repo = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(repo / "src"), env.get("PYTHONPATH", "")))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-c", _SERVER, "streamable-http", str(port)],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError(f"HTTP server exited: {process.stderr.read()}")
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.05)
        else:
            raise AssertionError("HTTP server did not bind to loopback")

        async def exercise() -> None:
            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):  # noqa: SIM117
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = _result_data(await session.call_tool("overview", {}))
                    assert result["view"] == "overview"
                    assert result["available"] is True

        asyncio.run(exercise())

        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "host-origin-probe", "version": "1"},
            },
        }
        headers = {"Accept": "application/json, text/event-stream"}
        with httpx.Client(trust_env=False) as client:
            bad_host = client.post(
                f"http://127.0.0.1:{port}/mcp",
                json=initialize,
                headers={**headers, "Host": "attacker.example"},
            )
            bad_origin = client.post(
                f"http://127.0.0.1:{port}/mcp",
                json=initialize,
                headers={**headers, "Origin": "http://attacker.example"},
            )
        assert bad_host.status_code == 421, (bad_host.status_code, bad_host.text)
        assert bad_origin.status_code == 403, (bad_origin.status_code, bad_origin.text)
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_remote_bind_is_rejected(capsys) -> None:
    from lei_signal.integrations.gpt_mcp import main

    try:
        main(["--transport", "streamable-http", "--host", "0.0.0.0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("remote host was accepted")
    assert "remote binding is disabled" in capsys.readouterr().err


def test_confirmed_record_protocol_uses_original_isolated_store(tmp_path) -> None:
    """Official SDK, real local receipt/holding tables, no production paths."""
    script = """
import sys
from lei_signal.integrations.gpt_mcp import create_server
from lei_signal.integrations.chat_workflow import ConfirmedWorkflow
from lei_signal.storage.sqlite_store import connect
from lei_signal.portfolio.models import PortfolioGroup, PortfolioHolding
from lei_signal.portfolio.store import upsert_group, upsert_holding
with connect(sys.argv[1]) as conn:
    upsert_group(conn, PortfolioGroup("cn", "测试分组", "cn", 1, "测试"))
    upsert_holding(conn, PortfolioHolding("h1", "cn", "测试通信基金", "515880", 1000, 0))
    conn.commit()
class Context:
    pass
create_server(Context(), allow_confirmed_records=True,
              workflow=ConfirmedWorkflow(sys.argv[1]), transactions=object()).run()
"""
    db = tmp_path / "protocol.db"

    async def exercise():
        repo = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        params = StdioServerParameters(
            command=sys.executable, args=["-c", script, str(db)], env=env, cwd=str(repo)
        )
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            init = await session.initialize()
            assert init.serverInfo.name == "lei-system"
            tools = (await session.list_tools()).tools
            assert len(tools) == 23
            writes = {t.name for t in tools if not t.annotations.readOnlyHint}
            assert writes == {
                "record_confirm",
                "trade_record",
                "plan_discussion",
                "plan_draft",
                "holding_plan_link",
            }
            card = _result_data(
                await session.call_tool(
                    "record_preview",
                    {
                        "kind": "holding_basis",
                        "request_id": "protocol-basis-01",
                        "original_message": "隔离测试实际份额",
                        "conversation_ref": "isolated-test",
                        "fields": {
                            "holding_id": "h1",
                            "code": "515880",
                            "shares": 800,
                            "cost": 900,
                            "basis_date": "2026-09-30",
                            "included_trade_ids": [],
                            "evidence_ref": "测试平台记录",
                        },
                    },
                )
            )
            assert (
                await session.call_tool(
                    "record_confirm", {"card": card, "confirmation": {"confirmed": False}}
                )
            ).isError
            arguments = {
                "card": card,
                "confirmation": {
                    "confirmed": True,
                    "request_id": card["request_id"],
                    "fingerprint": card["fingerprint"],
                },
            }
            result = _result_data(await session.call_tool("record_confirm", arguments))
            assert result["status"] == "basis_confirmed"
            assert _result_data(await session.call_tool("record_confirm", arguments)) == result
            assert (await session.call_tool("execute_trade", {})).isError

    asyncio.run(exercise())
    import sqlite3

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM codex_workflow_receipts").fetchone()[0] == 1
        assert conn.execute("SELECT market_value FROM portfolio_holdings").fetchone()[0] == 1000
