"""Qualify the saved 070002 2024 reports; no return or factor calculation."""

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


BASE = Path(__file__).resolve().parent
NEW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/china')
OLD = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china')
PDF = NEW / '070002-2024FY-jsfund.pdf'
EXPECTED = '37bf4ac34c71eb5bd1cc7d2e3f145d9ec7ee81fd65795e00092f515a9425128f'
OLD_EXPECTED = '5dca7d4bc812dee742cc5f2b646b2d2059305380dabef64737b0f71c0f350277'
NUM = r'([\d,]+(?:\.\d+)?)'
HOLDING = re.compile(r'^\s*(\d{1,3})\s+([036]\d{5})\s+(.+?)\s+([\d,]+)\s+([\d,]+\.\d{2})\s+(\d+\.\d{2})\s*$', re.M)


def amt(s, pattern):
    m = re.search(pattern, s)
    if not m:
        raise ValueError('Missing field: ' + pattern)
    return Decimal(m.group(1).replace(',', ''))


assert hashlib.sha256(PDF.read_bytes()).hexdigest() == EXPECTED
assert hashlib.sha256((OLD / '070002-2024H1-jsfund.pdf').read_bytes()).hexdigest() == OLD_EXPECTED
pages = [p.extract_text() or '' for p in PdfReader(PDF).pages]
assert len(pages) == 65 and '2025' in pages[0] and '28' in pages[0]
full = '\n'.join(pages)
start = full.rfind('8.3 期末按公允价值占基金资产净值比例大小排序的所有股票投资明细')
end = full.find('8.4 报告期内股票投资组合的重大变动', start)
assert start > 0 and end > start
raw = HOLDING.findall(full[start:end])
assert len(raw) == 39 and [int(x[0]) for x in raw] == list(range(1, 40))
holdings = [dict(rank=int(rank), stock_code=code, stock_name=name.strip(), shares=shares.replace(',', ''),
                 fair_value_cny=value.replace(',', ''), pct_fund_nav=pct)
            for rank, code, name, shares, value, pct in raw]
fair_total = sum(Decimal(r['fair_value_cny']) for r in holdings)
assert fair_total == Decimal('1584508621.98')
flow = full[full.rfind('§10 开放式基金份额变动'):]
annual = dict(opening_units=amt(flow, r'本报告期期初基金份额总额\s+' + NUM),
              subscriptions_units=amt(flow, r'本报告期基金总申购份额\s+' + NUM),
              redemptions_units=amt(flow, r'本报告期基金总赎回份额\s+' + NUM),
              closing_units=amt(flow, r'本报告期期末基金份额总额\s+' + NUM))
assert annual['opening_units'] + annual['subscriptions_units'] - annual['redemptions_units'] == annual['closing_units']
prior = next(x for x in json.loads((OLD / '070002-report-fields.json').read_text()) if x['period_end'] == '2024-06-30')
assert annual['opening_units'] == Decimal(prior['opening_units'])
h2 = dict(opening_units=Decimal(prior['closing_units']),
          subscriptions_units=annual['subscriptions_units'] - Decimal(prior['subscriptions_units']),
          redemptions_units=annual['redemptions_units'] - Decimal(prior['redemptions_units']),
          closing_units=annual['closing_units'])
assert h2['opening_units'] + h2['subscriptions_units'] - h2['redemptions_units'] == h2['closing_units']
with (OLD / '070002-holdings.csv').open(newline='') as f:
    old = [x for x in csv.DictReader(f) if x['period_end'] == '2024-06-30']
assert len(old) == 69
old_codes = {x['stock_code'] for x in old}
new_codes = {x['stock_code'] for x in holdings}
manifest = json.loads(Path('/Volumes/win+mac通用/LeiSignal-新实验结果/high52-execution-revalidation-20261020/high52-execution-revalidation-20261020-20261020T103838-98db6d9bfda6/result/acquisition-v1/new_source_manifest.json').read_text())
price_codes = {x.split('.')[-1] for x in manifest['asset_sources']}
out = {
    'fund_code': '070002', 'period_end': '2024-12-31', 'report_type': 'annual',
    'report_sent_date': '2025-03-28', 'official_announcement_page_date': '2025-03-28',
    'official_announcement_time': None, 'amendment_history_checked': False,
    'pdf_sha256': EXPECTED, 'pdf_bytes': PDF.stat().st_size, 'pdf_pages': len(pages),
    'holdings_scope': 'all', 'holdings_rows': len(holdings), 'holdings_pages': [48, 49],
    'holdings_total_fair_value_cny': str(fair_total), 'stock_assets_cny': '1584508621.98',
    'stock_pct_total_assets': '69.51', 'annual_flow': {k: str(v) for k, v in annual.items()},
    'derived_2024H2_flow': {k: str(v) for k, v in h2.items()},
    'flow_pages': [53], 'flow_note': '2024 annual gross units minus H1 gross units; includes conversion and dividend reinvestment, not cash',
    'saved_H1_holdings_rows': len(old), 'H1_to_FY_shared_stock_codes': len(old_codes & new_codes),
    'saved_300_stock_price_codes': len(price_codes),
    'H1_price_code_overlap': len(old_codes & price_codes),
    'FY_price_code_overlap': len(new_codes & price_codes),
    'pair_union_price_code_overlap': len((old_codes | new_codes) & price_codes),
    'pair_union_stock_codes': len(old_codes | new_codes),
    'effects_calculated': 0,
}
(BASE / '070002-2024FY-fields.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
with (BASE / '070002-2024FY-holdings.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(holdings[0]))
    writer.writeheader()
    writer.writerows(holdings)
print(json.dumps(out, ensure_ascii=False))
