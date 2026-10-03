"""Reproduce protocol and query boundary checks without calling provider APIs."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tomllib
from unittest.mock import patch

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
SCRIPT = ROOT / '.agents/skills/factorhub-readonly/scripts/server.py'
spec = importlib.util.spec_from_file_location('factorhub_adapter', SCRIPT)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
config = tomllib.loads((ROOT / '.codex/config.toml').read_text())['mcp_servers']['factorhub_readonly']
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


async def verify():
    selected = {t.name for t in await adapter.list_tools()}
    check('five advertised tools', len(selected) == 5)
    check('Codex config matches adapter tools', selected == set(config['enabled_tools']))
    check('no POST tool advertised', 'run_backtest' not in selected)
    with patch.dict(os.environ, {}, clear=True):
        denied = await adapter.query('run_backtest', {})
        missing = await adapter.query('get_trade_dates', {})
    check('direct POST tool rejected before credential access', denied.isError and '未开放' in denied.content[0].text)
    check('missing credential produces explicit error', missing.isError and 'FACTORHUB_API_KEY' in missing.content[0].text)

    cases = [
        ('list_factors', {'page': 1, 'page_size': 2}, '/api/v1/factors'),
        ('get_factor_scores', {'code': 'MOM001'}, '/api/v1/factors/MOM001/scores'),
        ('get_factor_nav', {'code': 'MOM001'}, '/api/v1/factors/MOM001/nav'),
        ('get_index_daily', {'ts_code': '000300.SH', 'start_date': '20260921', 'end_date': '20260925'}, '/api/v1/market/index'),
        ('get_trade_dates', {'start_date': '20260921', 'end_date': '20260925'}, '/api/v1/calendar/trade-dates'),
    ]
    observed = []
    def respond(request):
        observed.append({'method': request.method, 'host': request.url.host, 'path': request.url.path, 'params': dict(request.url.params)})
        return httpx.Response(200, json={'data': [{'date': '20260921'}]})
    original = httpx.AsyncClient
    def mock_client(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(respond)
        return original(*args, **kwargs)
    with patch.dict(os.environ, {'FACTORHUB_API_KEY': 'offline-test-only', 'FACTORHUB_BASE_URL': 'https://invalid.example'}), patch('httpx.AsyncClient', mock_client):
        for name, args, path in cases:
            reply = await adapter.query(name, args)
            check(f'{name} dispatch success', not reply.isError)
            check(f'{name} fixed HTTPS GET route', observed[-1]['method'] == 'GET' and observed[-1]['host'] == 'factorhub.cn' and observed[-1]['path'] == path)
            check(f'{name} preserves query parameters', all(observed[-1]['params'].get(k) == str(v) for k, v in args.items() if k != 'code'))
    def limited(request):
        return httpx.Response(429)
    def limited_client(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(limited)
        return original(*args, **kwargs)
    with patch.dict(os.environ, {'FACTORHUB_API_KEY': 'offline-test-only'}), patch('httpx.AsyncClient', limited_client):
        reply = await adapter.query('get_trade_dates', {})
        check('429 classified without vendor exception-handler bug', reply.isError and '不自动重试' in reply.content[0].text)

    env = {k: v for k, v in os.environ.items() if k != 'FACTORHUB_API_KEY'}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    params = StdioServerParameters(command=sys.executable, args=[str(SCRIPT)], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            check('real stdio initialize', init.serverInfo.name == 'factorhub_readonly')
            tools = await session.list_tools()
            check('real stdio list_tools contains only five queries', {t.name for t in tools.tools} == selected)
            denied = await session.call_tool('run_backtest', {})
            check('real stdio rejects unadvertised backtest', denied.isError)
            reply = await session.call_tool('get_trade_dates', {})
            check('real stdio missing credential marked isError', reply.isError and 'FACTORHUB_API_KEY' in reply.content[0].text)
    return observed


if __name__ == '__main__':
    observed = asyncio.run(verify())
    (RAW / 'adapter-checks.json').write_text(json.dumps({'passed': len(checks), 'checks': checks, 'mock_requests': observed, 'live_provider_queries': 0}, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(checks)} checks passed; live FactorHub queries: 0')
