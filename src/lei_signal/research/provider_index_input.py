"""Bind retained Tencent index day prices to source bytes, never to market claims.

No market features/targets are calculated. A successful match establishes only
provider-price reconstruction, not official methodology or actionable trading.
"""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

IDENTITIES = {'sh000300': ('沪深300', '000300'), 'sz399006': ('创业板指', '399006')}
FIELDS = ('open', 'close', 'high', 'low')


def _fail(message):
    raise ValueError('provider index input: ' + message)


def _path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        _fail('source paths must be nonempty and relative to root')
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        _fail('source path escapes root')
    return path


def _json(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        _fail(f'cannot read JSON source {path.name}: {exc}')
    if not isinstance(value, dict):
        _fail('JSON source must be an object')
    return value


def _hash(path, expected):
    if not isinstance(expected, str) or len(expected) != 64:
        _fail('source SHA-256 must be explicit')
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _fail(f'cannot read source {path.name}: {exc}')
    if actual != expected:
        _fail(f'source SHA-256 mismatch: {path.name}')
    return actual


def _date(value):
    try:
        if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
            _fail('date must be YYYY-MM-DD')
    except ValueError:
        _fail('date must be YYYY-MM-DD')
    return value


def _price(value):
    if value is None or isinstance(value, bool):
        _fail('OHLC must contain positive finite numbers')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        _fail('OHLC must contain positive finite numbers')
    if not number.is_finite() or number <= 0:
        _fail('OHLC must contain positive finite numbers')
    return number


def _row(raw):
    if not isinstance(raw, dict) or not {'date', *FIELDS} <= raw.keys():
        _fail('missing date/OHLC fields')
    values = tuple(_price(raw[f]) for f in FIELDS)
    o, c, h, l = values
    if not l <= min(o, c) <= max(o, c) <= h:
        _fail('illegal OHLC order')
    return _date(raw['date']), values


def _canonical(rows):
    output = [_row(r) for r in rows]
    dates = [d for d, _ in output]
    if not dates or dates != sorted(set(dates)):
        _fail('source dates must be nonempty, ascending and unique')
    return output


def qualify_provider_index_panel(payload, contract, root):
    """Validate actual CSV -> raw day response -> panel and declared calendar.

    Returns quality/semantics/warnings for the root preflight. All failures are
    ValueError. The root still owns contract freezing and scientific judgment.
    """
    try:
        return _qualify(payload, contract, Path(root).resolve())
    except (KeyError, TypeError, IndexError, AttributeError, OSError) as exc:
        _fail(f'invalid schema/source: {exc}')


def _qualify(payload, contract, root):
    q = contract['data']['qualification']
    if q['adapter'] != 'tencent_index_price/1.0':
        _fail('unsupported adapter')
    if contract['target']['entry_field'] != 'close':
        _fail('actionable opening prices are unsupported')
    if contract['target'].get('price_measure') != 'provider_index_price':
        _fail('target must measure provider index price, not account or total return')
    if contract['target'].get('kind') not in {'forward_return', 'mae', 'max_drawdown', 'up', 'downside_event'}:
        _fail('account/unsupported target')
    if contract['question']['layer'] != 'factor_information' or contract['question']['validation']['stage'] != 'exploration':
        _fail('only historical exploratory factor information is supported')
    basis = contract['question'].get('target', {}).get('price_basis', '')
    if any(word in str(basis).lower() for word in ('total_return', 'totalreturn', 'account')):
        _fail('account/total-return price basis is unsupported')
    if contract['publication']['conclusion'] not in {'insufficient', 'not_supported'}:
        _fail('supported/general market claim is prohibited for provider reconstruction')
    manifest_file = _path(root, q['manifest_path'])
    manifest = _json(manifest_file)
    if manifest['schema_version'] != 'provider-index-input/1.0':
        _fail('unsupported manifest schema')
    if [manifest['start'], manifest['end']] != ['2020-12-18', '2026-06-30']:
        _fail('manifest period differs from retained source scope')
    sources = manifest['sources']
    assets = contract['universe']['assets']
    if not isinstance(sources, list) or not isinstance(assets, list) or not assets:
        _fail('sources and asset pool must be nonempty lists')
    source_assets = [s['asset'] for s in sources]
    if len(set(source_assets)) != len(source_assets) or len(set(assets)) != len(assets) or set(source_assets) != set(assets):
        _fail('manifest and planned asset pool differ; partial substitution is prohibited')
    calendar_path = _path(root, manifest['calendar_path'])
    if calendar_path != _path(root, q['calendar_path']):
        _fail('qualification and manifest calendar paths differ')
    hashes = {manifest['calendar_path']: _hash(calendar_path, manifest['calendar_sha256'])}
    hashes[q['manifest_path']] = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    calendar = _json(calendar_path)
    if calendar.get('authority') != 'exchange_official' or 'SZSE' not in calendar.get('publisher', ''):
        _fail('retained SZSE calendar source is required')
    expected_dates = []
    for d, record in sorted(calendar['days'].items()):
        _date(d)
        if type(record.get('is_trading_day')) is not bool:
            _fail('calendar trading-day states must be explicit booleans')
        if manifest['start'] <= d <= manifest['end'] and record['is_trading_day']:
            expected_dates.append(d)
    if not expected_dates or expected_dates[0] != manifest['start'] or expected_dates[-1] != manifest['end']:
        _fail('calendar does not cover source endpoints')
    if payload['calendar'] != expected_dates:
        _fail('actual panel calendar differs from full retained trading-day axis')
    expected_panel = {}
    for source in sources:
        asset = source['asset']
        if asset not in IDENTITIES or (source['name'], source['code']) != IDENTITIES[asset]:
            _fail('manifest index identity is unsupported or incorrect')
        paths = {}
        for role in ('bars', 'response', 'request'):
            paths[role] = _path(root, source[role + '_path'])
            hashes[source[role + '_path']] = _hash(paths[role], source[role + '_sha256'])
        response = _json(paths['response'])
        if type(response.get('code')) is not int or response['code'] != 0:
            _fail('provider response was not successful')
        data = response['data'][asset]
        quote = data['qt'][asset]
        if quote[1:3] != [source['name'], source['code']]:
            _fail('response identity differs from manifest')
        if not isinstance(data.get('day'), list):
            _fail('raw day branch required; adjusted branches cannot substitute')
        response_rows = []
        for row in data['day']:
            if not isinstance(row, list) or len(row) < 5:
                _fail('invalid raw day record')
            response_rows.append(dict(zip(('date', *FIELDS), row[:5])))
        raw = _canonical(response_rows)
        request = _json(paths['request'])
        if request.get('symbol', asset) != asset or request.get('returned_branch', 'day') != 'day':
            _fail('request identity/actual branch differs')
        if request.get('response_sha256', source['response_sha256']) != source['response_sha256']:
            _fail('request and response fingerprints differ')
        with paths['bars'].open(newline='', encoding='utf-8') as stream:
            csv_rows = _canonical(list(csv.DictReader(stream)))
        if csv_rows != raw:
            _fail('CSV dates/OHLC differ from raw provider response')
        if [d for d, _ in raw] != expected_dates:
            _fail('each index must cover the complete calendar without gaps')
        expected_panel.update({(asset, d): values for d, values in raw})
    actual_panel = {}
    for bar in payload['bars']:
        if bar['status'] != 'quoted' or bar.get('provider_price_known') is not True or bar.get('price_series') != 'provider_index_price':
            _fail('panel must preserve quoted provider-price status')
        if bar.get('action_known') is not False or bar.get('open_actionable') is not False:
            _fail('action history and actionable opens cannot be self-certified')
        d, values = _row(bar)
        key = bar['asset'], d
        if key in actual_panel:
            _fail('duplicate panel asset/date')
        actual_panel[key] = values
    if actual_panel != expected_panel:
        _fail('panel hides, fabricates or changes source dates/assets/OHLC')
    return {'quality': {'request_satisfied': True, 'rows': len(actual_panel),
                       'assets': list(assets), 'source_hashes': hashes,
                       'calculation_run': False, 'production_authorized': False},
            'semantics': {'price_series_bound': True, 'calendar_bound': True,
                'action_history_completeness': 'not_applicable_to_provider_index_price',
                'opening_actionability': 'unsupported', 'historical_arrival': 'not_certified',
                'official_index_methodology': 'not_certified',
                'sse_independent_calendar': 'not_certified'},
            'warnings': [{'code': 'provider_index_scope', 'message': '仅限腾讯历史指数价格代理；不是官方全收益、可成交资产或账户收益。'},
                         {'code': 'provider_index_calendar', 'message': '日期绑定现存深交所日历；未独立认证沪市日历与历史到达时点。'}]}
