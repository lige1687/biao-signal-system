"""Locate the same A-share bullish-response question in acquired CKISS originals.

Values below were transcribed from the cited page, with separate retail and
financial-industry respondents. This is source qualification, not a factor test.
"""

import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader


BASE = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china')
SOURCE_INDEX = json.loads((BASE / 'ckgsb-source-index.json').read_text(encoding='utf-8'))
INDEX = {x['period']: x for x in SOURCE_INDEX['reports']}
# period, source page (PDF one-based), retail %, financial-industry %, publication date
ROWS = [
    ('2018Q3', 2, '62', '38', ''),
    ('2018Q4', 5, '64', '44', ''),
    ('2019Q1', 4, '67.2', '60.7', ''),
    ('2019Q3', 4, '64', '51.6', ''),
    ('2019Q4', 4, '64', '53', ''),
    ('2020Q1', 5, '53.7', '43', ''),
    ('2020Q3', 2, '60.2', '52.9', ''),
    ('2021Q1', 4, '61.3', '79.9', ''),
    ('2021Q3', 6, '54.5', '81.4', ''),
    ('2021Q4', 2, '52.8', '83.5', ''),
    ('2022Q1', 6, '54.9', '79.7', ''),
    ('2023Q1', 8, '68.3', '87.8', ''),
    ('2023Q3', 7, '63.2', '85.3', ''),
    ('2025Q1', 5, '62.6', '59.9', '2025-05-21'),
    ('2025Q3', 5, '61.7', '65.9', '2025-09-23'),
    ('2025Q4', 5, '64.2', '59.8', '2026-01-28'),
    ('2026Q1', 4, '61.6', '67', '2026-05-21'),
    ('2026Q3', 6, '59.6', '57.6', '2026-09-17'),
]
PUBLICATION = {
    '2025Q1': 'https://english.ckgsb.edu.cn/new/2025-chinese-investor-trends-gold-bonds-real-estate-shifts/',
    '2025Q3': 'https://english.ckgsb.edu.cn/new/china-investor-confidence-rebounds/',
    '2025Q4': 'https://english.ckgsb.edu.cn/new/retail-vs-institutional-investors-in-china/',
    '2026Q1': 'https://english.ckgsb.edu.cn/new/china-investor-sentiment-q1-2026/',
    '2026Q3': 'https://english.ckgsb.edu.cn/new/ckgsb-survey-finds-cautious-investor-sentiment-in-chinas-stock-market-in-q3-2026/',
}
out = []
for period, page, retail, finance, published in ROWS:
    entry = INDEX[period]
    source = BASE / entry['file']
    reader = PdfReader(source)
    page_text = re.sub(r'\s+', ' ', reader.pages[page - 1].extract_text() or '')
    if not re.search(r'A\s*股', page_text) or not re.search(r'散\s*户', page_text):
        raise ValueError(f'question context absent: {period} p{page}')
    if not re.search(rf'(?<!\d){re.escape(retail)}\s*%', page_text):
        raise ValueError(f'retail value absent: {period} p{page}')
    if not re.search(rf'(?<!\d){re.escape(finance)}\s*%', page_text):
        raise ValueError(f'finance value absent: {period} p{page}')
    # These are intentionally text locators, not a reconstructed exact quote.
    anchor = re.search(r'(?:认为\s*A\s*股|A\s*股.*?上涨|散\s*户.*?上涨)', page_text)
    locator = page_text[anchor.start():anchor.start() + 380] if anchor else page_text[:380]
    out.append({'directory_period': period, 'pdf_file': entry['file'],
                'pdf_sha256': entry['sha256'], 'source_pdf_url': entry['chosen']['url'],
                'pdf_page_one_based': page, 'question': 'A股未来约12个月会上涨的受访者比例',
                'retail_bullish_pct': retail, 'financial_industry_bullish_pct': finance,
                'first_public_date_verified': published, 'publication_url': PUBLICATION.get(period, ''),
                'source_text_locator': locator})
with (BASE / 'ckgsb-retail-bullish-a-share.csv').open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print(json.dumps({'original_pdf_directory_entries': len(INDEX), 'usable_same_question_rows': len(out),
                  'verified_publication_dates': sum(bool(x['first_public_date_verified']) for x in out)}, ensure_ascii=False))
