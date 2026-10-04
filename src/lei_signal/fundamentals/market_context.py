"""Market-background series and explicit source qualifications; no trading rules."""
from __future__ import annotations

import math
from datetime import date
from typing import Any

_SOURCES = {
    'eastmoney-margin': {
        'provider': '东方财富转引沪深融资资料',
        'source_url': 'https://data.eastmoney.com/rzrq/',
        'series_identity': 'RPTA_RZRQ_LSHJ',
        'frequency': '日',
        'unit_definition': '余额或当日融资买入额，人民币亿元；买入额不是净流入',
        'limitations': '融资余额占比的分母可变化；没有融资偿还字段，不推算真实净流量。',
    },
    'eastmoney-treasury': {
        'provider': '东方财富中美国债资料',
        'source_url': 'https://data.eastmoney.com/cjsj/zmgzsyl.html',
        'series_identity': 'RPTA_WEB_TREASURYYIELD',
        'frequency': '日',
        'unit_definition': '收益率为百分比；10年减2年为百分点',
        'limitations': '国债期限差不是企业信用利差，也不是央行政策利率。',
    },
    'legulegu-hs300': {
        'provider': '乐咕乐股，经AkShare',
        'source_url': 'https://akshare.akfamily.xyz/data/stock/stock.html',
        'series_identity': '沪深300 / 滚动市盈率',
        'frequency': '实际观测',
        'unit_definition': 'PE为倍，历史盈利收益率=100/滚动PE（%）',
        'limitations': '同日期读数与中证官方不一致，具体原因未确认；盈利收益率不是盈利增长或盈利预期。',
    },
    'multpl-ey': {
        'provider': 'Multpl 标普500盈利收益率历史',
        'source_url': 'https://www.multpl.com/s-p-500-earnings-yield/table/by-month',
        'series_identity': 'S&P 500 earnings yield',
        'frequency': '月',
        'unit_definition': '过去盈利相对价格的收益率（%）',
        'limitations': '历史盈利收益率不是EPS、盈利增速或分析师预测；发布修订未核。',
    },
}


def metadata_for(source_id: str, retrieved_at: str | None) -> dict[str, Any]:
    return {
        **_SOURCES[source_id],
        'retrieved_at': retrieved_at,
        'published_at': None,
        'vintage': None,
        'value_status': 'provider_observed',
        'historical_prediction_use': 'unqualified',
        'redistribution_permission': 'unverified',
    }


def make_series(label: str, unit: str, rows: dict[str, Any], *, today: str,
                metadata: dict[str, Any], cutoff: str = '') -> dict[str, Any]:
    items = []
    for period, value in sorted(rows.items()):
        if not isinstance(period, str) or date.fromisoformat(period).isoformat() != period:
            raise ValueError('invalid observation date')
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError('invalid observation value')
        if cutoff <= period <= today:
            items.append((period, None if value is None else round(float(value), 3)))
    return {'label': label, 'unit': unit, 'dates': [d for d, _ in items],
            'values': [v for _, v in items], 'source': metadata}


def financing_series(rows: dict[str, dict[str, Any]], today: str, metadata: dict[str, Any],
                     cutoff: str = '') -> dict[str, Any]:
    fields = [('margin_rzye', '融资余额', 'rzye_yi'),
              ('margin_rqye', '融券余额', 'rqye_yi'),
              ('margin_buy', '当日融资买入额', 'buy_yi')]
    return {key: make_series(label, '亿', {d: r.get(field) for d, r in rows.items()},
                             today=today, cutoff=cutoff, metadata=metadata)
            for key, label, field in fields}


SOURCE_GAPS = {
    'finra_margin': {'status': 'permission_unconfirmed', 'title': '美国FINRA月度融资',
                     'source_url': 'https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics',
                     'reason': '官方资料和月度口径已核；应用展示/自动提取使用范围尚未明确，先核官方页面。'},
    'earnings_forward': {'status': 'missing_input', 'title': '指数盈利预期与修订',
                         'reason': '没有合格共识资料；1/PE不是盈利预期。'},
    'etf_flow': {'status': 'missing_input', 'title': 'ETF净申赎与资金流',
                 'reason': '现有成交额/相对强弱不等于净申赎。'},
    'cn_credit': {'status': 'missing_input', 'title': '中国企业信用利差',
                  'reason': '国债利率或期限差不替代信用利差。'},
    'cn_volatility': {'status': 'missing_input', 'title': '中国波动预期',
                      'reason': '美国VIX不替代中国市场波动预期。'},
}
