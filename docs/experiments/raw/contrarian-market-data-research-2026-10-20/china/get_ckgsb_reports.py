"""Acquire only reports explicitly linked by CKGSB's public survey index."""

import hashlib
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


BASE = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china')
INDEX = 'https://english.ckgsb.edu.cn/knowledge/the-ckgsb-investor-sentiment-survey/'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
with urllib.request.urlopen(urllib.request.Request(INDEX, headers=HEADERS), timeout=30) as response:
    html = response.read()
soup = BeautifulSoup(html, 'html.parser')
items = []
for div in soup.select('div.reports-item'):
    title = div.select_one('h4.reports-title')
    if not title:
        continue
    label = title.get_text(' ', strip=True)
    match = re.search(r'Q([1-4])\s+(20\d{2})', label)
    if not match:
        continue
    period = f'{match.group(2)}Q{match.group(1)}'
    links = [{'label': a.get_text(' ', strip=True), 'url': a.get('href')}
             for a in div.select('a[href]') if '.pdf' in a.get('href', '').lower()]
    chosen = next((x for x in links if x['label'].startswith('[CH]')), None)
    if chosen is None:
        chosen = next((x for x in links if x['label'] == 'Report'), None)
    if chosen is None:
        chosen = next((x for x in links if 'Key Findings' in x['label']), None)
    entry = {'period': period, 'index_title': label, 'index_url': INDEX,
             'available_pdf_links': links, 'chosen': chosen,
             'retrieved_utc': datetime.now(timezone.utc).isoformat()}
    if chosen:
        filename = f'ckgsb-iss-{period}.pdf'
        try:
            quoted_url = urllib.parse.quote(chosen['url'], safe=':/?=&%')
            entry['requested_url'] = quoted_url
            if (BASE / filename).is_file():
                data = (BASE / filename).read_bytes()
                entry['already_downloaded'] = True
            else:
                with urllib.request.urlopen(urllib.request.Request(quoted_url, headers=HEADERS), timeout=60) as response:
                    data = response.read()
                    entry['http_status'] = response.status
                    entry['content_type'] = response.headers.get('Content-Type')
            if not data.startswith(b'%PDF'):
                raise ValueError(f'not a PDF: {data[:30]!r}')
            (BASE / filename).write_bytes(data)
            entry.update({'file': filename, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        except Exception as exc:
            entry['error'] = str(exc)
    items.append(entry)
with (BASE / 'ckgsb-source-index.json').open('w', encoding='utf-8') as out:
    json.dump({'index_url': INDEX, 'index_sha256': hashlib.sha256(html).hexdigest(),
               'fetched_utc': datetime.now(timezone.utc).isoformat(), 'reports': items}, out,
              ensure_ascii=False, indent=2)
print(json.dumps({'index_reports': len(items), 'downloaded': sum('file' in x for x in items),
                  'failed': [(x['period'], x.get('error')) for x in items if 'error' in x]}, ensure_ascii=False))
