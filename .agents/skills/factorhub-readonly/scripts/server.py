"""Project MCP/CLI adapter for the published FactorHub client; GET queries only."""

import argparse
import asyncio
import json
import os

import httpx
from factorhub_mcp.client import FactorHubClient
from factorhub_mcp.server import _dispatch, handle_list_tools
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

ALLOWED_TOOLS = frozenset({
    "list_factors", "get_factor_scores", "get_factor_nav",
    "get_index_daily", "get_trade_dates",
})
BASE_URL = "https://factorhub.cn/api/v1"
server = Server(
    "factorhub_readonly",
    instructions=(
        "FactorHub 外部资料查询，只开放五个 GET 查询。供应商绩效摘要不是股票评分明细，"
        "指数不是 ETF；空表如实报告。429 后停止。数据查询不授权策略采用或交易。"
    ),
)


@server.list_tools()
async def list_tools():
    tools = [t for t in await handle_list_tools() if t.name in ALLOWED_TOOLS]
    for tool in tools:
        tool.annotations = types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        )
    return tools


def result(text, *, error=False):
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)], isError=error,
    )


@server.call_tool()
async def query(name: str, arguments: dict):
    # This restriction applies to direct calls as well as the advertised catalog.
    if name not in ALLOWED_TOOLS:
        return result("此接入只提供指定查询，未开放该工具。", error=True)
    key = os.environ.get("FACTORHUB_API_KEY", "")
    if not key:
        return result(
            "尚未配置 FACTORHUB_API_KEY，无法查询供应商数据。请通过授权的环境变量配置密钥。",
            error=True,
        )
    # Ignore upstream base URL overrides; credentials always go to this origin.
    client = FactorHubClient(api_key=key, base_url=BASE_URL)
    try:
        data = await _dispatch(client, name, arguments)
        return result(json.dumps(data, ensure_ascii=False, indent=2))
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        messages = {
            401: "供应商认证失败，请检查授权的密钥配置。",
            403: "当前账户未获该查询权限。",
            404: "供应商未找到请求资源，请核对参数。",
            429: "供应商限制请求次数，本次停止，不自动重试。",
        }
        return result(messages.get(status, f"供应商查询失败（HTTP {status}）。"), error=True)
    except httpx.HTTPError:
        return result("供应商连接或返回异常，本次未取得数据。", error=True)
    except (KeyError, TypeError, ValueError):
        return result("参数或供应商返回格式异常，请核对工具定义。", error=True)


async def run():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--query", choices=sorted(ALLOWED_TOOLS))
    parser.add_argument("--arguments", default="{}")
    args = parser.parse_args()
    if args.list_tools:
        tools = asyncio.run(list_tools())
        print(json.dumps([t.model_dump(mode="json") for t in tools], ensure_ascii=False, indent=2))
    elif args.query:
        arguments = json.loads(args.arguments)
        if not isinstance(arguments, dict):
            parser.error("arguments must be a JSON object")
        response = asyncio.run(query(args.query, arguments))
        print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2))
        raise SystemExit(1 if response.isError else 0)
    else:
        asyncio.run(run())


if __name__ == "__main__":
    main()
