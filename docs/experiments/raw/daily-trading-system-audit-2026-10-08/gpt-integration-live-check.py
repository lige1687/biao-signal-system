"""Verify the real local MCP adapter; private responses stay in ignored cache."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    root = Path(__file__).resolve().parents[4]
    folder = root / "data/cache/gpt-system-integration"
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    tag = now.strftime("%Y%m%dT%H%M%S%f")
    paths = [
        root / "data/cache/gpt-system-integration/runtime/compat",
        root / "data/cache/gpt-system-integration/runtime",
        root / "src",
    ]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "lei_signal.integrations.gpt_mcp", "--transport", "stdio"],
        env={"PYTHONPATH": os.pathsep.join(map(str, paths))},
        cwd=str(root),
    )
    responses = {}
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        names = (await session.list_tools()).tools
        assert initialized.serverInfo.name == "lei-system-readonly"
        assert len(names) == 10
        assert all(
            t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in names
        )
        calls = [
            ("overview", {}),
            ("portfolio", {"fund_code": "013403"}),
            ("fundamentals", {"market": "cn"}),
            ("news", {"limit": 3}),
            ("plans", {"fund_code": "013403"}),
            ("trades", {}),
            ("factors", {}),
            ("research_search", {"query": "research-evidence-catalog", "limit": 3}),
            (
                "research_report",
                {
                    "name": "docs/experiments/research-evidence-catalog-2026-10-07.md",
                    "max_chars": 3000,
                },
            ),
            ("latest_brief", {"slot": "1135"}),
        ]
        for name, arguments in calls:
            result = await session.call_tool(name, arguments)
            assert not result.isError, (name, result)
            value = result.structuredContent
            assert isinstance(value, dict), name
            assert value["available"], (name, value.get("errors"))
            stamp = datetime.fromisoformat(value["generated_at"])
            assert stamp.tzinfo and stamp >= now
            responses[name] = value
        assert responses["portfolio"]["data"]["user_stated_context"]
        assert not any(
            x.get("is_confirmed_monitoring_plan")
            for x in responses["portfolio"]["data"]["user_stated_context"]
        )
        assert responses["news"]["data"]["blogger_yesterday"]
        assert responses["news"]["errors"].get("news_receipt"), "known source failures hidden"
        report = responses["research_report"]["data"]
        assert report["registry_sha256_verified"]
        assert (await session.call_tool("execute_trade", {})).isError
        assert (
            await session.call_tool("portfolio", {"fund_code": "http://external.invalid"})
        ).isError
    private_path = folder / f"live-mcp-{tag}.json"
    private_path.write_text(json.dumps(responses, ensure_ascii=False, indent=2) + "\n")
    summary = {
        "verified_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "server": initialized.serverInfo.model_dump(),
        "transport": "local_stdio",
        "tools_called": [t.name for t in names],
        "all_real_tools_available": True,
        "coverage": responses["overview"]["data"]["workspace"]["coverage"],
        "preserved_news_failure_count": len(responses["news"]["errors"]["news_receipt"]),
        "preserved_unconfirmed_user_context": True,
        "report_sha256_verified": report["sha256"],
        "known_source_errors": {k: list(v["errors"]) for k, v in responses.items() if v["errors"]},
        "write_tool_rejected": True,
        "external_input_rejected": True,
        "private_responses": str(private_path.relative_to(root)),
        "chatgpt_actual_call_verified": False,
        "production_writes": False,
    }
    receipt = Path(__file__).with_name("gpt-integration-live-receipt.json")
    receipt.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
