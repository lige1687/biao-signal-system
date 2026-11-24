"""Append accepted observation ids to the released homepage registration table."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[3]
public = ROOT / 'web/public/research/microstructure-observations-20261108'
manifest = json.loads((public / 'catalog.json').read_text())
path = ROOT / 'web/src/components/market-observation-alerts/indicatorCatalog.ts'
source = path.read_text()
match = re.search(r'(export const MICRO_INDICATORS: readonly IndicatorEntry\[\] = \[)(.*?)(\n\];)', source, re.S)
if not match:
    raise RuntimeError('microstructure registration table was changed; review before editing')
existing = json.loads('[' + match[2] + ']')
ids = {row['id'] for row in existing}
additions = []
for row in manifest['indicators']:
    branch = row['packet'].removesuffix('.json')
    if row['id'] in ids or branch not in manifest['acceptedPackets']:
        continue
    if row['status'] == 'pending':
        continue
    additions.append({'id': row['id'], 'label': row['title'], 'market': row['market'],
        'category': row['category'], 'meaning': row['purpose'],
        'limitation': ('历史快照，按卡片日期、股票范围与来源口径阅读。' if row['hasData'] else row['purpose']),
        'readable': row['status'] == 'ready'})
if additions:
    body = match[2].rstrip() + (',' if existing else '') + json.dumps(additions, ensure_ascii=False, indent=2)[1:-1]
    result = source[:match.start(2)] + body.rstrip() + source[match.end(2):]
    path.write_text(result)
    assert all(row['id'] in path.read_text() for row in additions)
print(json.dumps({'added': len(additions), 'existingPreserved': len(existing)}, ensure_ascii=False))
