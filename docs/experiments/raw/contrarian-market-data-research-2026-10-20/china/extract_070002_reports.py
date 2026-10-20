"""Extract disclosed fields from the five acquired 070002 original reports only."""

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


SOURCE = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china')
SPECS = [
    ('070002-2016Q4-cninfo.pdf', '2016-12-31', '2017-01-19', 'quarter', 10),
    ('070002-2021FY-jsfund.pdf', '2021-12-31', '2022-03-30', 'annual', 187),
    ('070002-2023Q4-jsfund.pdf', '2023-12-31', '2024-01-19', 'quarter', 10),
    ('070002-2024H1-jsfund.pdf', '2024-06-30', '2024-08-30', 'interim', 69),
    ('070002-2025Q2-cninfo.pdf', '2025-06-30', '2025-07-21', 'quarter', 10),
]
NUM = r'([\d,]+(?:\.\d+)?)'
HOLDING = re.compile(r'^\s*(\d{1,3})\s+([036]\d{5})\s+(.+?)\s+([\d,]+)\s+([\d,]+\.\d{2})\s+(\d+\.\d{2})\s*$', re.M)


def amount(text, pattern):
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f'missing field: {pattern}')
    return str(Decimal(m.group(1).replace(',', '')))


records = []
holdings = []
for filename, period_end, sent_date, kind, expected_holdings in SPECS:
    data = (SOURCE / filename).read_bytes()
    reader = PdfReader(SOURCE / filename)
    pages = [p.extract_text() or '' for p in reader.pages]
    full = '\n'.join(pages)
    assert period_end[:4] in pages[0]
    assert f'{int(sent_date[:4])}' in pages[0] and f'{int(sent_date[5:7])}' in pages[0]
    stock = re.search(r'其中：股票\s+' + NUM + r'\s+' + NUM, full)
    if not stock:
        raise ValueError(f'missing stock assets: {filename}')
    starts = [m.start() for m in re.finditer('股票投资明细', full)
              if '股票代' in full[m.end():m.end() + 350]]
    if not starts:
        raise ValueError(f'missing holdings section: {filename}')
    start = starts[-1]
    end_match = re.search(r'\n(?:5|7|8)\.4\s+', full[start:])
    if not end_match:
        raise ValueError(f'missing holdings section end: {filename}')
    candidates = HOLDING.findall(full[start:start + end_match.start()])
    if len(candidates) != expected_holdings or [int(x[0]) for x in candidates] != list(range(1, expected_holdings + 1)):
        raise ValueError(f'holdings count/sequence mismatch {filename}: {len(candidates)}')
    for rank, code, name, shares, value, nav_pct in candidates:
        holdings.append({'source_file': filename, 'fund_code': '070002', 'period_end': period_end,
                         'report_sent_date': sent_date, 'disclosure_scope': 'all' if kind != 'quarter' else 'top_10',
                         'rank': int(rank), 'stock_code': code, 'stock_name': name.strip(),
                         'shares': shares.replace(',', ''), 'fair_value_cny': value.replace(',', ''),
                         'pct_fund_nav': nav_pct})
    flows = full[full.rfind('开放式基金份额变动'):]
    rec = {'source_file': filename, 'sha256': hashlib.sha256(data).hexdigest(), 'source_bytes': len(data),
           'page_count': len(pages), 'fund_code': '070002', 'fund_name': '嘉实增长混合',
           'period_end': period_end, 'report_sent_date': sent_date,
           'report_kind': kind, 'holdings_scope': 'all' if kind != 'quarter' else 'top_10',
           'holdings_rows': len(candidates), 'stock_assets_cny': stock.group(1).replace(',', ''),
           'stock_pct_total_assets': stock.group(2),
           'opening_units': amount(flows, r'(?:报告期期初基金份额总额|本报告期期初基金份额总额)\s+' + NUM),
           'subscriptions_units': amount(flows, r'(?:报告期期间基金总申购份额|本报告期基金总申购份额)\s+' + NUM),
           'redemptions_units': amount(flows, r'(?:报告期期间基金总赎回份额|本报告期基金总赎回份额)\s+' + NUM),
           'closing_units': amount(flows, r'(?:报告期期末基金份额总额|本报告期期末基金份额总额)\s+' + NUM)}
    difference = Decimal(rec['opening_units']) + Decimal(rec['subscriptions_units']) - Decimal(rec['redemptions_units']) - Decimal(rec['closing_units'])
    if difference != 0:
        raise ValueError(f'unit bridge mismatch {filename}: {difference}')
    records.append(rec)

with (SOURCE / '070002-report-fields.json').open('w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
with (SOURCE / '070002-holdings.csv').open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(holdings[0]))
    writer.writeheader()
    writer.writerows(holdings)
print(json.dumps({'reports': len(records), 'holding_rows': len(holdings),
                  'by_report': {r['period_end']: r['holdings_rows'] for r in records}}, ensure_ascii=False))
