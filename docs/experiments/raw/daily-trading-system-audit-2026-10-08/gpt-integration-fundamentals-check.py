"""Check added fixed fundamentals sections through the real local MCP service."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    root = Path(__file__).resolve().parents[4]
    folder = root / "data/cache/gpt-system-integration"
    runtime = folder / "runtime"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "lei_signal.integrations.gpt_mcp"],
        env={"PYTHONPATH": os.pathsep.join(map(str, [runtime / "compat", runtime, root / "src"]))},
        cwd=str(root),
    )
    responses: dict[str, dict] = {}
    checks = []
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for section in ("overview", "rates", "us-macro", "rates-history", "macro-history"):
            started = time.monotonic()
            result = await session.call_tool("fundamentals", {"section": section, "market": "us"})
            assert not result.isError, section
            value = result.structuredContent
            assert isinstance(value, dict), section
            assert value["selection"]["section"] == section
            assert not value["selection"]["market_parameter_applied"]
            responses[section] = value
            checks.append(
                {
                    "section": section,
                    "protocol_succeeded": True,
                    "available": value["available"],
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "selection": value["selection"],
                    "sources": value["sources"],
                    "errors": value["errors"],
                    "limitations": value["limitations"],
                }
            )
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    private_path = folder / f"fundamentals-mcp-{now.strftime('%Y%m%dT%H%M%S%f')}.json"
    private_path.write_text(json.dumps(responses, ensure_ascii=False, indent=2) + "\n")
    receipt = {
        "verified_at": now.isoformat(),
        "transport": "local_stdio",
        "checks": checks,
        "all_sections_available": all(item["available"] for item in checks),
        "private_responses": str(private_path.relative_to(root)),
        "forced_refresh_requested": False,
        "production_writes": False,
    }
    Path(__file__).with_name("gpt-integration-fundamentals-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "verified_at": receipt["verified_at"],
                "checks": [
                    {k: v for k, v in item.items() if k not in {"limitations", "sources"}}
                    for item in checks
                ],
                "all_sections_available": receipt["all_sections_available"],
                "private_responses": receipt["private_responses"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
