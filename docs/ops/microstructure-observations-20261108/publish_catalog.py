"""Publish only explicitly reviewed packets into the homepage discovery manifest."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'web/public/research/microstructure-observations-20261108'

def category(id):
    if 'turnover' in id or 'sector' in id:
        return 'style'
    if 'pcr' in id or 'financing' in id or 'margin' in id:
        return 'funding'
    if 'dispersion' in id or 'amount-top' in id:
        return 'participation'
    return 'risk'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--accepted', nargs='+', choices=['funding', 'equity', 'derivatives'], required=True)
    args = parser.parse_args()
    indicators = []
    for branch in ['funding', 'equity', 'derivatives']:
        path = PUBLIC / f'{branch}.json'
        if not path.exists():
            continue
        packet = json.loads(path.read_text())
        for card in packet['cards']:
            has_data = any(p['value'] is not None for p in card['points'])
            indicators.append({'id': card['id'], 'title': card['title'], 'market': card['market'],
                'category': category(card['id']), 'purpose': card['meaning'],
                'status': 'ready' if branch in args.accepted and has_data else 'pending',
                'hasData': has_data, 'asOf': card['points'][-1]['date'],
                'packet': f'{branch}.json'})
        for item in packet['unavailable']:
            indicators.append({'id': item['id'], 'title': item['title'], 'market': item['market'],
                'category': category(item['id']), 'purpose': item['reason'],
                'status': 'unavailable', 'hasData': False, 'asOf': None, 'packet': f'{branch}.json'})
    result = {'schemaVersion': 1, 'generatedAt': datetime.now(timezone.utc).isoformat(),
              'acceptedPackets': args.accepted, 'indicators': indicators}
    (PUBLIC / 'catalog.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (Path(__file__).parent / 'handoff.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'accepted': args.accepted, 'ready': sum(i['status'] == 'ready' for i in indicators)}, ensure_ascii=False))
