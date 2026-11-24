"""Offline, source-qualified equity market structure observations.

The CSI 300 and S&P 500 panels below are explicitly current-member snapshots
looked backwards. They are price-shape observations, not historical index series.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
ROOT = Path('/Volumes/win+mac通用/LeiSignal-新实验结果')
CN_RAW = ROOT / 'public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity'
OLD_UNION = ROOT / 'twenty-year-universe-data-20261025/twenty-year-universe-data-20261025-20261025T154847-f27d39c4e083/result/cn/stock-source-union-v4/actual-date-unions.jsonl'
CN_SNAPSHOT = ROOT / 'stock-universe-cn-20261015/stock-universe-cn-20261015-20261015T194200-354f8f803e8c/result'
US_SNAPSHOT = ROOT / 'stock-universe-us-20261015/stock-universe-us-20261015-20261015T194201-82eb0af53148/result'
INDUSTRY = ROOT / 'microstructure-observations-20261108/equity'
MONTHLY = REPO / 'docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/implementation-v2/concentration/monthly.json'
OUTPUT = REPO / 'web/public/research/microstructure-observations-20261108/equity.json'
EVIDENCE = REPO / 'docs/ops/microstructure-observations-20261108/equity'
AMOUNT_START, AMOUNT_END = '2026-09-01', '2026-10-23'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def concentration(amounts: dict[str, float | None], fraction: float) -> float | None:
    """Largest ceil(fraction*n) amounts / all amounts; missing stays unknown."""
    if not amounts or any(v is None or not math.isfinite(v) or v < 0 for v in amounts.values()):
        return None
    total = sum(amounts.values())
    if total <= 0:
        return None
    ranked = sorted(amounts.items(), key=lambda item: (-item[1], item[0]))
    k = math.ceil(fraction * len(ranked))
    return sum(v for _, v in ranked[:k]) / total


def covered_concentration(amounts: dict[str, float | None], expected: set[str], fraction: float,
                          conflicts: set[str] | None = None) -> float | None:
    if conflicts or not expected.issubset(amounts):
        return None
    return concentration({code: amounts[code] for code in expected}, fraction)


def aggregate_amount_concentration(stocks, calendar: list[str], *, daily_start: str,
                                   monthly_end: str) -> dict:
    """Rank same-day or whole-month stock amounts with an exact lifecycle gate.

    Each stock is (code, IPO date, first delisted date or None, dated amounts).
    A supplied zero is valid; an absent/invalid amount is unknown. Monthly
    amounts are summed per security before ranking, never averaged daily shares.
    Caller must qualify source identities, calendar and lifecycle dates first.
    """
    if calendar != sorted(set(calendar)):
        raise ValueError('calendar must be unique and increasing')
    days_by_month: dict[str, list[str]] = defaultdict(list)
    for day in calendar:
        if day[:7] <= monthly_end:
            days_by_month[day[:7]].append(day)
    daily = {day: {} for day in calendar if day >= daily_start}
    monthly = {month: {} for month in days_by_month}
    month_missing: dict[str, dict[str, int]] = defaultdict(dict)
    seen = set()
    for code, ipo, first_delisted, amounts in stocks:
        if code in seen or not ipo:
            raise ValueError('unique security and a known IPO date required')
        seen.add(code)

        def listed(day):
            return ipo <= day and (not first_delisted or day < first_delisted)

        def valid(value):
            return value is not None and math.isfinite(value) and value >= 0

        for day, bucket in daily.items():
            if listed(day):
                value = amounts.get(day)
                bucket[code] = value if valid(value) else None
        for month, dates in days_by_month.items():
            expected = [day for day in dates if listed(day)]
            if not expected:
                continue
            values = [amounts.get(day) for day in expected]
            missing = sum(not valid(value) for value in values)
            monthly[month][code] = None if missing else math.fsum(values)
            if missing:
                month_missing[month][code] = missing

    def result_row(date, amounts, missing):
        n = len(amounts)
        return {'date': date, 'n': n, 'k5': math.ceil(.05 * n), 'k10': math.ceil(.10 * n),
                'observedStocks': sum(value is not None for value in amounts.values()),
                'missingCodes': sorted(missing), 'missingStockDays': sum(missing.values()),
                'denominator': math.fsum(amounts.values()) if amounts and not missing else None,
                'top5': concentration(amounts, .05), 'top10': concentration(amounts, .10)}

    return {
        'daily': [result_row(day, amounts, {code: 1 for code, value in amounts.items() if value is None})
                  for day, amounts in daily.items()],
        'monthly': [result_row(days_by_month[month][-1], amounts, month_missing[month])
                    for month, amounts in monthly.items()],
        'lifecycleConvention': 'IPO included; delisting effective date excluded',
        'securitiesInspected': len(seen),
    }


def accepted_concentration_cards() -> list[dict] | None:
    """Use only the explicitly accepted, fingerprinted refresh when rebuilding."""
    receipts = ('concentration-daily-history/accepted.json', 'concentration-refresh/accepted.json')
    receipt = next((EVIDENCE.parent / name for name in receipts if (EVIDENCE.parent / name).is_file()), None)
    if receipt is None:
        return None
    record = json.loads(receipt.read_text())
    path = Path(record['cardsPath'])
    if record.get('status') != 'accepted' or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError('concentration refresh has no accepted source binding')
    if sha(path) != record['cardsSha256']:
        raise RuntimeError('accepted concentration cards changed')
    cards = json.loads(path.read_text())
    expected = {'cn-daily-amount-top5', 'cn-daily-amount-top10', 'cn-monthly-amount-top5'}
    if len(cards) != 3 or {c['id'] for c in cards} != expected:
        raise RuntimeError('accepted concentration card identity mismatch')
    return cards


def adjusted_close(raw: float, factor: float) -> float:
    if not math.isfinite(raw) or not math.isfinite(factor) or raw <= 0 or factor <= 0:
        raise ValueError('positive finite price and factor required')
    return raw * factor


def qualified_amount(status: str, amount: str, volume: str) -> float | None:
    if status == '0':
        try:
            if (amount == '' or float(amount) == 0) and (volume == '' or float(volume) == 0):
                return 0.0
        except ValueError:
            return None
        return None
    if status != '1':
        return None
    try:
        a, v = float(amount), float(volume)
    except ValueError:
        return None
    if not math.isfinite(a) or not math.isfinite(v) or a < 0 or v < 0 or ((a == 0) != (v == 0)):
        return None
    return a


def back_factor_events(body: dict) -> dict[str, float]:
    fields = body['fields']
    date_idx = fields.index('dividOperateDate')
    factor_idx = fields.index('backAdjustFactor')
    return {row[date_idx]: float(row[factor_idx]) for row in body.get('data', [])}


def above_prior_quantile(value: float | None, prior: list[float | None], q: float) -> bool | None:
    if value is None or not math.isfinite(value) or not prior or any(x is None or not math.isfinite(x) for x in prior):
        return None
    return value > float(np.percentile(prior, q))


def cross_section(prices: dict[str, list[float | None]], window: int = 20) -> dict[str, float | None]:
    """Daily return dispersion and last-window average pairwise Pearson r."""
    if len(prices) < 2 or any(len(x) != window + 1 for x in prices.values()):
        return {'dispersion': None, 'correlation': None}
    arr = np.asarray(list(prices.values()), dtype=float)
    if not np.isfinite(arr).all() or (arr <= 0).any():
        return {'dispersion': None, 'correlation': None}
    returns = arr[:, 1:] / arr[:, :-1] - 1
    disp = float(np.std(returns[:, -1], ddof=0) * 100)
    if np.any(np.std(returns, axis=1) == 0):
        return {'dispersion': disp, 'correlation': None}
    corr = np.corrcoef(returns)
    upper = corr[np.triu_indices(len(prices), 1)]
    return {'dispersion': disp, 'correlation': float(np.mean(upper)) if np.isfinite(upper).all() else None}


def prior_percentiles(values: list[float | None], window: int) -> list[float | None]:
    out = []
    for i, v in enumerate(values):
        prior = values[max(0, i-window):i]
        out.append(None if v is None or len(prior) != window or any(x is None for x in prior)
                   else 100 * sum(x < v for x in prior) / window)
    return out


def card(id: str, title: str, market: str, unit: str, scope: str, meaning: str,
         source: str, url: str, points: list[dict], limitations: list[str],
         details: list[dict] | None = None) -> dict:
    return {'id': id, 'title': title, 'market': market, 'unit': unit, 'frequency': 'daily',
            'scope': scope, 'meaning': meaning, 'sourceName': source, 'sourceUrl': url,
            'refreshedAt': datetime.now(timezone.utc).isoformat(), 'refreshMode': 'snapshot',
            'points': points, 'percentileWindow': None, 'limitations': limitations,
            'latestDetails': details or []}


def load_amounts(ledger: dict) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Archived BaoStock daily amounts; each date gets its own lifecycle coverage gate."""
    monthly = json.loads(MONTHLY.read_text())
    month = next(p for p in monthly['points'] if p['date'].startswith('2026-09'))
    if month['value'] is None:
        raise RuntimeError('September source-month coverage gate failed')
    meta_path = CN_RAW / 'all-equity-read-index-v8-meta.json'
    meta = json.loads(meta_path.read_text())
    index = Path(meta['index_path'])
    if sha(index) != meta['index_sha256']:
        raise RuntimeError('BaoStock v8 index SHA mismatch')
    ledger['inputs'].extend([{'path': str(MONTHLY), 'sha256': sha(MONTHLY)},
                             {'path': str(meta_path), 'sha256': sha(meta_path)},
                             {'path': str(index), 'sha256': sha(index)}])
    coverage = json.loads((REPO / 'docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json').read_text())
    calendar_ref = coverage['baseline']['calendar']
    calendar_path = Path(calendar_ref['path'])
    if sha(calendar_path) != calendar_ref['sha256']:
        raise RuntimeError('amount calendar SHA mismatch')
    with calendar_path.open() as stream:
        amount_days = [r['trade_date'] for r in csv.DictReader(stream) if AMOUNT_START <= r['trade_date'] <= AMOUNT_END]
    by_date: dict[str, dict[str, float | None]] = {day: {} for day in amount_days}
    ledger['inputs'].append({'path': str(calendar_path), 'sha256': sha(calendar_path)})
    expected_by_date: dict[str, set[str]] = defaultdict(set)
    bad_by_date: dict[str, set[str]] = defaultdict(set)
    current_codes = {p.name.removesuffix('-daily.json') for p in CN_SNAPSHOT.glob('*-daily.json')}
    raw_prices: dict[str, dict[str, float]] = defaultdict(dict)
    factor_events: dict[str, dict[str, float]] = defaultdict(dict)
    read_files = 0
    with index.open() as stream, OLD_UNION.open() as old_stream:
        previous = json.loads(next(old_stream))
        for line in stream:
            item = json.loads(line)
            code = item['code']
            while previous and previous['code'] < code:
                previous = json.loads(next(old_stream, 'null'))
            old = previous if previous and previous['code'] == code else None
            if not code.startswith(('sh.60', 'sh.68', 'sz.00', 'sz.30')):
                continue
            if item.get('supplier_ipo', '') > AMOUNT_END or (item.get('supplier_out') or '9999') < AMOUNT_START:
                continue
            refs = (old['source_refs'] if old else []) + item['new_price_sources'] + item['reused_raw_sources']
            if code in current_codes:
                base_factor_file = CN_SNAPSHOT / f'{code}-adjustments.json'
                if base_factor_file.is_file():
                    factor_events[code].update(back_factor_events(json.loads(base_factor_file.read_text())))
                for factor_ref in item.get('new_factor_sources', []):
                    fp = Path(factor_ref.get('source_path') or factor_ref['path'])
                    payload = fp.read_bytes()
                    if hashlib.sha256(payload).hexdigest() != (factor_ref.get('compressed_sha256') or factor_ref.get('sha256')):
                        raise RuntimeError('factor SHA mismatch: ' + str(fp))
                    factor_body = json.loads(gzip.decompress(payload) if fp.suffix == '.gz' else payload)
                    factor_events[code].update(back_factor_events(factor_body))
            seen_paths = set()
            for ref in refs:
                first = ref.get('valid_slice_start') or ref.get('observed_first_date') or ref.get('first_date') or ref.get('source_request_start') or '9999'
                last = ref.get('valid_slice_end') or ref.get('observed_last_date') or ref.get('last_date') or ref.get('source_request_end') or '0000'
                if first > AMOUNT_END or last < AMOUNT_START:
                    continue
                path = Path(ref.get('source_path') or ref['path'])
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                blob = path.read_bytes()
                if hashlib.sha256(blob).hexdigest() != (ref.get('compressed_sha256') or ref.get('sha256')):
                    raise RuntimeError('raw source SHA mismatch: ' + str(path))
                body = json.loads(gzip.decompress(blob) if path.suffix == '.gz' else blob)
                fields = body['fields']
                for row in body['data']:
                    rec = dict(zip(fields, row))
                    day = rec['date']
                    if day not in by_date:
                        continue
                    status = rec['tradestatus']
                    value = qualified_amount(status, rec['amount'], rec['volume'])
                    prior = by_date[day].get(code)
                    if code in by_date[day] and (prior is None or value is None or not math.isclose(prior, value, abs_tol=0.01)):
                        bad_by_date[day].add(code)
                    if code not in bad_by_date[day]:
                        by_date[day][code] = value
                    if code in current_codes and status == '1':
                        try:
                            close = float(rec['close'])
                            if close > 0 and math.isfinite(close):
                                raw_prices[code][day] = close
                        except ValueError:
                            pass
                read_files += 1
            for day in by_date:
                if item['supplier_ipo'] <= day <= (item.get('supplier_out') or '9999'):
                    expected_by_date[day].add(code)
    ledger['archivedRawObjectsRead'] = read_files
    ledger['inputs'].append({'path': str(OLD_UNION), 'sha256': sha(OLD_UNION)})
    result = []
    for day in amount_days:
        amounts = by_date[day]
        # The existing month gate checks exact source dates against each security's supplier lifecycle.
        # Reuse that stronger gate, while a day with an invalid amount remains null.
        expected = expected_by_date[day]
        result.append({'date': day, 'top5': covered_concentration(amounts, expected, .05, bad_by_date[day]),
                       'top10': covered_concentration(amounts, expected, .10, bad_by_date[day]),
                       'n': len(expected), 'missing': len(expected - amounts.keys()),
                       'conflicts': len(bad_by_date[day])})
    if not result:
        raise RuntimeError('no valid September amount dates')
    adjusted = {}
    for code, series in raw_prices.items():
        events = sorted(factor_events[code].items())
        event_days = [d for d, _ in events]
        factors = [f for _, f in events]
        qualified = {}
        for day, price in series.items():
            pos = bisect.bisect_right(event_days, day)-1
            if pos >= 0 and factors[pos] > 0:
                qualified[day] = adjusted_close(price, factors[pos])
        adjusted[code] = qualified
    ledger['cnRecentPriceMembers'] = len(adjusted)
    return result, adjusted


def cn_prices(recent: dict[str, dict[str, float]] | None = None) -> tuple[dict[str, dict[str, float]], dict]:
    if recent is not None:
        return recent, {'files': len(recent), 'sha256': sha(CN_RAW / 'all-equity-read-index-v8-meta.json')}
    out = {}
    files = sorted(CN_SNAPSHOT.glob('*-daily.json'))
    for path in files:
        try:
            body = json.loads(path.read_text())
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        fields = body['fields']
        factor_file = path.with_name(path.name.replace('-daily.json', '-adjustments.json'))
        factor_rows = json.loads(factor_file.read_text())['data'] if factor_file.exists() else []
        factor_dates = [row[1] for row in factor_rows]
        factors = [float(row[2]) for row in factor_rows]
        series = {}
        for row in body['data']:
            rec = dict(zip(fields, row))
            if '2026-04-01' <= rec['date'] <= '2026-06-30' and rec['tradestatus'] == '1':
                try:
                    price = float(rec['close'])
                    if price > 0:
                        loc = bisect.bisect_right(factor_dates, rec['date']) - 1
                        factor = factors[loc] if loc >= 0 else 1.0
                        if factor > 0:
                            series[rec['date']] = adjusted_close(price, factor)
                except ValueError:
                    pass
        out[path.stem.removesuffix('-daily')] = series
    return out, {'files': len(out), 'sha256': sha(CN_SNAPSHOT / 'summary.json')}


def us_prices() -> tuple[dict[str, dict[str, float]], dict]:
    out = {}
    recent_ledger = REPO / 'docs/ops/microstructure-observations-20261108/constituents/source-ledger.json'
    if recent_ledger.is_file():
        refs = json.loads(recent_ledger.read_text())
        if len(refs) != 502 or any(ref.get('qualification') != 'ok' for ref in refs):
            raise RuntimeError('US recent fixed-pool source ledger incomplete')
        files = []
        for ref in refs:
            path = Path(ref['path'])
            if sha(path) != ref['sha256'] or path.stem != ref['symbol']:
                raise RuntimeError('US recent source SHA/symbol mismatch: ' + str(path))
            files.append(path)
    else:
        files = sorted(p for p in US_SNAPSHOT.glob('*.json') if p.name not in ('summary.json', 'verification.json'))
    from datetime import datetime
    for path in files:
        try:
            body = json.loads(path.read_text())
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        result = (body.get('chart', {}).get('result') or [None])[0]
        if not result:
            continue
        timestamps = result.get('timestamp') or []
        closes = (result.get('indicators', {}).get('adjclose') or [{}])[0].get('adjclose') or []
        series = {}
        for stamp, close in zip(timestamps, closes):
            day = datetime.fromtimestamp(stamp, timezone.utc).strftime('%Y-%m-%d')
            if ('2026-08-25' <= day <= '2026-11-06' if recent_ledger.is_file() else '2026-04-01' <= day <= '2026-06-30') and close is not None and close > 0:
                series[day] = float(close)
        out[path.stem] = series
    return out, {'files': len(out), 'sha256': sha(recent_ledger if recent_ledger.is_file() else US_SNAPSHOT / 'summary.json'),
                 'recentLedger': str(recent_ledger) if recent_ledger.is_file() else None,
                 'recentBytes': sum(x['bytes'] for x in refs) if recent_ledger.is_file() else 0}


def member_cards(market: str, prices: dict[str, dict[str, float]], info: dict) -> list[dict]:
    # Require every member in each dated window. Missing dates create null points.
    dates = sorted(set().union(*(set(s) for s in prices.values())))
    points_d = []
    points_c = []
    covered = []
    paired_covered = []
    for i, day in enumerate(dates):
        day_disp = None
        pair_count = 0
        if i >= 1:
            yesterday = dates[i-1]
            paired = [s[day]/s[yesterday]-1 for s in prices.values() if day in s and yesterday in s]
            pair_count = len(paired)
            if len(paired) >= math.ceil(.95 * len(prices)):
                day_disp = float(np.std(paired, ddof=0)*100)
        if i >= 20:
            window = dates[i-20:i+1]
            complete = {code: [s[d] for d in window] for code, s in prices.items()
                        if all(d in s for d in window)}
            used = len(complete)
            val = cross_section(complete) if used >= math.ceil(.95 * len(prices)) else {'dispersion': None, 'correlation': None}
        else:
            used = 0
            val = {'correlation': None}
        points_d.append({'date': day, 'value': day_disp})
        points_c.append({'date': day, 'value': val['correlation']})
        covered.append(used)
        paired_covered.append(pair_count)
    chinese = '沪深300' if market == 'cn' else '标普500'
    asof = '2026-10-15'
    scope = f'{chinese}于{asof}取得的当前成分代理名单（{len(prices)}只可读报价）；日离散用前后两日有价股，20日相关用全21日有价股；固定名单回看，不是历史逐时成分'
    source = 'BaoStock当前300股名单、归档日线及复权因子' if market == 'cn' else 'Yahoo Finance当前IVV持仓股报价快照'
    url = 'https://github.com/zxygithub/baostock/blob/master/docs/pythonAPI.md' if market == 'cn' else 'https://query1.finance.yahoo.com/v8/finance/chart/AAPL'
    price_end = dates[-1] if dates else '无合格日'
    limits = ['当前成员固定回看，退出股票和历史换股未纳入；不可称为历史指数成分或交易证据。',
              f'报价原件截至{price_end}；中国使用供应商后复权因子（跨批次原始锚定），美国使用Yahoo调整收盘价。供应商复权历史修订和逐时到达未核；缺日、停牌或零方差时保留空值。',
              '每窗完整报价股票数可能变化；低于当前名单95%时留空，不能与正式加权指数离散度或相关性直接对比。',
              '相关系数与Cboe期权隐含相关的对象、期限、权重和时态均不同。']
    details = [{'label': '成员名单日期', 'value': asof}, {'label': '报价截止日期', 'value': price_end}, {'label': '报价股票数', 'value': str(info['files'])},
               {'label': '末日两日有价股数', 'value': str(paired_covered[-1])},
               {'label': '末日21日完整股数', 'value': str(covered[-1])}]
    return [card(f'{market}-current-members-daily-dispersion', f'{chinese}当前成员日收益离散度', market, '百分点', scope,
                 '描述同日逐股涨跌差距；高值不自动意味着选股收益。', source, url, points_d, limits, details),
            card(f'{market}-current-members-pairwise-correlation', f'{chinese}当前成员20日两两相关', market, '相关系数', scope,
                 '描述逐股是否同动；共同上涨与共同下跌都可能抬高相关。', source, url, points_c, limits, details)]


def industry_turnover_card(code: str, name: str, series: dict[str, float], dates: list[str],
                           source: str, url: str, limits: list[str]) -> dict:
    points = [{'date': day, 'value': series.get(day)} for day in dates]
    values = [point['value'] for point in points]
    percentiles = prior_percentiles(values, 756)
    prior = values[-757:-1]
    qualified = len(prior) == 756 and all(value is not None for value in prior)
    p95 = float(np.percentile(prior, 95)) if qualified else None
    p98 = float(np.percentile(prior, 98)) if qualified else None
    latest = values[-1]
    details = [{'label': '观察窗', 'value': '此前756个交易日完整窗（近3年）'},
               {'label': '最近读数', 'value': f'{latest:.2f}%' if latest is not None else '缺失'},
               {'label': '自身P95阈值', 'value': f'{p95:.2f}%' if p95 is not None else '样本不足'},
               {'label': '自身P98阈值', 'value': f'{p98:.2f}%' if p98 is not None else '样本不足'}]
    result = card(f'cn-industry-turnover-{code.lower()}', f'{name}日换手率', 'cn', '%',
                  f'东方财富行业板块{code}（{name}），供应商报告换手率；当前板块定义回看历史',
                  '与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。',
                  source, url, points, limits, details)
    result['percentileWindow'] = 756
    result['percentiles'] = [{'date': day, 'value': value} for day, value in zip(dates, percentiles)]
    return result


def focused_industry_turnover_cards(ledger: dict, dates: list[str]) -> list[dict]:
    path = EVIDENCE.parent / 'industry-turnover-picker/focused-source-ledger.json'
    if not path.is_file():
        return []
    refs = json.loads(path.read_text())
    expected = {'BK1326': '半导体设备', 'BK1325': '半导体材料'}
    if len(refs) != len(expected) or {ref['code']: ref['name'] for ref in refs} != expected:
        raise RuntimeError('focused industry source list changed')
    cards = []
    for ref in refs:
        code, name = ref['code'], ref['name']
        raw = path.parent / 'raw' / f'{code}.json'
        if ref.get('status') != 200 or sha(raw) != ref['sha256']:
            raise RuntimeError(f'focused industry source SHA or status mismatch: {code}')
        body = json.loads(raw.read_text())
        data = body['data']
        if body['rc'] != 0 or (data['code'], data['name']) != (code, name):
            raise RuntimeError(f'focused industry source identity mismatch: {code}')
        rows = [line.split(',') for line in data['klines']]
        if [row[0] for row in rows] != dates or any(len(row) != 11 for row in rows):
            raise RuntimeError(f'focused industry calendar or schema mismatch: {code}')
        series = {row[0]: float(row[10]) for row in rows}
        if any(not math.isfinite(value) or not 0 <= value <= 100 for value in series.values()):
            raise RuntimeError(f'focused industry turnover out of range: {code}')
        cards.append(industry_turnover_card(code, name, series, dates, '东方财富行业板块历史行情',
                     'https://quote.eastmoney.com/center/boardlist.html#industry_board',
                     ['板块成分和换手率分母以东方财富口径为准。',
                      '历史位置使用此前756个交易日比较。']))
    ledger['focusedIndustryTurnover'] = {'path': str(path), 'sha256': sha(path), 'requests': len(refs),
                                       'bytes': sum(ref['bytes'] for ref in refs)}
    return cards


def industry_turnover_cards(ledger: dict) -> list[dict]:
    refs = json.loads((INDUSTRY / 'industry-history-request-ledger.json').read_text())
    if len(refs) != 56:
        raise RuntimeError('selected industry panel incomplete')
    panel = {}
    for ref in refs:
        path = Path(ref['path'])
        if sha(path) != ref['sha256']:
            raise RuntimeError('industry source SHA mismatch: ' + str(path))
        body = json.loads(path.read_text())
        rows = body['data']['klines']
        series = {}
        for raw in rows:
            fields = raw.split(',')
            if len(fields) != 11:
                continue
            try:
                value = float(fields[10])
            except ValueError:
                continue
            if math.isfinite(value) and value >= 0:
                series[fields[0]] = value
        panel[ref['code']] = (ref['name'], series)
    ledger['inputs'].append({'path': str(INDUSTRY / 'industry-history-request-ledger.json'),
                             'sha256': sha(INDUSTRY / 'industry-history-request-ledger.json'),
                             'objects': len(refs), 'totalBytes': sum(x['bytes'] for x in refs)})
    dates = sorted(set().union(*(set(series) for _, series in panel.values())))
    history = {code: [] for code in panel}
    p95_points, p98_points = [], []
    latest_tail = []
    latest_extreme = []
    for day in dates:
        current = {}
        qualifying = []
        extreme = []
        for code, (name, series) in panel.items():
            value = series.get(day)
            prior = history[code][-756:]
            if value is not None:
                current[code] = value
                if len(prior) == 756 and above_prior_quantile(value, prior, 95):
                    qualifying.append((name, value, float(np.percentile(prior, 95))))
                if len(prior) == 756 and above_prior_quantile(value, prior, 98):
                    extreme.append((name, value, float(np.percentile(prior, 98))))
            history[code].append(value)
        all_ready = len(current) == len(panel)
        p95_ready = all_ready and all(len(history[code]) >= 757 and all(x is not None for x in history[code][-757:-1]) for code in panel)
        p95_points.append({'date': day, 'value': 100 * len(qualifying)/len(panel) if p95_ready else None})
        p98_points.append({'date': day, 'value': 100 * len(extreme)/len(panel) if p95_ready else None})
        if all_ready:
            latest_tail = sorted(qualifying, key=lambda x: -x[1])
            latest_extreme = sorted(extreme, key=lambda x: -x[1])
    scope = '东方财富BK04与BK10代码组56个行业板块，供应商报告的日换手率；含细分与交叉类别，不是完整互斥行业体系'
    limits = ['来源只标“换手率”，历史分母、行业成分及修订时点未独立认证；不可宣称自行计算的自由流通换手或逐时成员。',
              '56个代码由BK04和BK10前缀在当次496项供应商名单中固定选取，覆盖半导体；交叉行业不可视为56个独立板块。',
              '自身P95/P98只用此前756个交易日完整窗，缺值则留空；当前日不参与。阈值为线性分位，历史位置为严格小于当前值的经验比例，遇到并列值可能稍有不同；高换手不识别买方或未来涨跌。']
    details = [{'label': '最新高于自身P95板块', 'value': '、'.join(f'{n} {v:.2f}%' for n,v,_ in latest_tail[:6]) or '无'},
               {'label': '最新高于自身P98板块', 'value': '、'.join(f'{n} {v:.2f}%' for n,v,_ in latest_extreme[:6]) or '无'},
               {'label': '板块数', 'value': str(len(panel))}]
    source = '东方财富行业板块历史行情 f61'
    url = 'https://quote.eastmoney.com/center/boardlist.html#industry_board'
    summaries = [card('cn-industry-turnover-above-own-p95', '行业换手高于自身近三年P95占比', 'cn', '%', scope,
                 '观察所选行业中异常活跃的比例；只是交易活跃状态。', source, url, p95_points, limits, details),
            card('cn-industry-turnover-above-own-p98', '行业换手高于自身近三年P98占比', 'cn', '%', scope,
                 '观察所选行业换手相对各自历史的极端活跃比例。', source, url, p98_points,
                 limits, details)]
    individual = []
    for code, (name, series) in sorted(panel.items()):
        url = next(ref['url'] for ref in refs if ref['code'] == code)
        individual.append(industry_turnover_card(code, name, series, dates, source, url, limits))
    return summaries + individual + focused_industry_turnover_cards(ledger, dates)


def build() -> dict:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    list1 = INDUSTRY / 'eastmoney-industry-list.json'
    list_more = json.loads((INDUSTRY / 'industry-list-request-ledger.json').read_text())
    histories = json.loads((INDUSTRY / 'industry-history-request-ledger.json').read_text())
    requests = [{'url': 'https://17.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A90+t%3A2+f%3A%2150&fields=f12%2Cf14%2Cf8',
                 'status': 200, 'bytes': list1.stat().st_size, 'path': str(list1), 'sha256': sha(list1)}]
    requests += list_more
    requests += [{'url': 'https://7.push2his.eastmoney.com/api/qt/stock/kline/get?secid=90.BK0475&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&klt=101&fqt=0&beg=20230101&end=20261108&smplmt=10000&lmt=1000000',
                  'status': 200, 'bytes': 84561, 'probe': True, 'rawSaved': False}]
    requests += [{key: ref[key] for key in ('url', 'status', 'bytes', 'path', 'sha256')} for ref in histories if 'url' in ref]
    ledger = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'newPublicRequests': len(requests),
              'newBytesDownloaded': sum(x['bytes'] for x in requests), 'requestCap': 100,
              'byteCap': 50 * 1024 * 1024, 'requests': requests,
              'failures': [x for x in histories if x.get('error')], 'inputs': []}
    cards = []
    unavailable = []
    amounts, recent_cn = load_amounts(ledger)
    scope = 'BaoStock沪深A股供应商上市期覆盖股，2026年9月1日至10月23日逐日原始成交额；非官方全A主表'
    limits = ['2026年9月整月来源已独立核完整；10月逐交易日按上市期逐股覆盖重新核，缺行日留空；不自动刷新。供应商历史名录和首次可见时点未独立认证。',
              '按当日有效来源股数排序，停牌明确报告为零成交；缺逐股源行不填零。',
              '成交额集中可由买入或卖出驱动，不代表资金净流入或后续收益。']
    for k in ('top5', 'top10'):
        points = [{'date': r['date'], 'value': None if r[k] is None else 100*r[k]} for r in amounts]
        latest_valid = next(r for r in reversed(amounts) if r[k] is not None)
        cards.append(card(f'cn-daily-amount-{k}', f'沪深A股每日成交额前{k[3:]}%占比', 'cn', '%', scope,
                          '观察成交额集中在少数股票的程度；升高并不区分追涨与抛售。', 'BaoStock原始日线',
                          'https://github.com/zxygithub/baostock/blob/master/docs/pythonAPI.md', points, limits,
                          [{'label': '最近合格日', 'value': latest_valid['date']},
                           {'label': '最近合格值', 'value': f'{100*latest_valid[k]:.2f}%'},
                           {'label': '最近合格日期股票数', 'value': str(latest_valid['n'])},
                           {'label': '序列末日缺源股数', 'value': str(amounts[-1]['missing'])}]))
    accepted_amounts = accepted_concentration_cards()
    if accepted_amounts is not None:
        cards = accepted_amounts
    for market, loader in (('cn', lambda: cn_prices(recent_cn)), ('us', us_prices)):
        prices, info = loader()
        ledger['inputs'].append({'path': str(CN_SNAPSHOT if market == 'cn' else US_SNAPSHOT),
                                 'summarySha256': info['sha256'], 'files': info['files']})
        if info.get('recentLedger'):
            ledger['collaboratorUSRecent'] = {'ledger': info['recentLedger'], 'sha256': info['sha256'],
                                              'requests': info['files'], 'bytes': info['recentBytes']}
        cards.extend(member_cards(market, prices, info))
    cards.extend(industry_turnover_cards(ledger))
    unavailable.append({'id': 'cn-all-industry-independent-float-turnover', 'title': '完整行业自行核算自由流通换手', 'market': 'cn',
                        'reason': '供应商目录496项中已取得BK04/BK10两组56个报告换手率板块；其余440项超出当前批次且目录含重叠细分。历史分母与成员版本未独立认证，尚非自行核算的完整互斥行业体系。',
                        'nextRequirement': '当期完整行业归属及逐股自由流通股数、成交股数和时点修订记录。'})
    packet = {'schemaVersion': 1, 'generatedAt': datetime.now(timezone.utc).isoformat(), 'cards': cards,
              'unavailable': unavailable}
    OUTPUT.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
    (EVIDENCE / 'source-ledger.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.parse_args()
    result = build()
    print(json.dumps({'cards': len(result['cards']), 'unavailable': len(result['unavailable']),
                      'latest': [c['points'][-1] for c in result['cards']]}, ensure_ascii=False))
