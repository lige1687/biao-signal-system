"""Recalculate official-source ratios with an independent XLSX reader and math."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import re
import warnings
import openpyxl

ROOT = Path(__file__).resolve().parents[3]
RAW = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/funding')
HERE = Path(__file__).parent
warnings.filterwarnings('ignore', message='Workbook contains no default style')

def workbook(path):
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = book.active
    sheet.reset_dimensions()
    rows = list(sheet.iter_rows(values_only=True))
    book.close()
    return rows

def number(value):
    return Decimal(str(value).replace(',', ''))

def source_json(path):
    value = path.read_text().strip()
    return json.loads(value[len('callback('):-1] if value.startswith('callback(') else value)

packet = json.loads((ROOT / 'web/public/research/microstructure-observations-20261108/funding.json').read_text())
cards = {c['id']: c for c in packet['cards']}
ratio_card = cards['cn-margin-buy-share-a-stocks']
calculated = []
raw_files = set()
for point in ratio_card['points']:
    day = point['date']; compact = day.replace('-', '')
    sh_paths = sorted(RAW.glob(f'sse-margin-{compact}-page*.json'))
    sh_rows = [r for path in sh_paths for r in source_json(path)['result']]
    sh_buy = sum((number(r['rzmre']) for r in sh_rows if re.fullmatch(r'6\d{5}', str(r['stockCode']))), Decimal(0))
    sz_path = RAW / f'szse-margin-{compact}.xlsx'
    sz = workbook(sz_path)
    assert sz[0][2] == '融资买入额(元)'
    sz_buy = sum((number(row[2]) for row in sz[1:] if re.fullmatch(r'[03]\d{5}', str(row[0]).zfill(6))), Decimal(0))
    sh_market = RAW / f'sse-stock-market-{compact}.json'
    sh_turn = source_json(sh_market)['result']
    assert {row['PRODUCT_CODE'] for row in sh_turn} == {'01', '03'}
    assert all(row['TRADE_DATE'] == compact for row in sh_turn)
    sh_amount = sum(number(row['TRADE_AMT']) for row in sh_turn) * 100_000_000
    sz_market = RAW / f'szse-turnover-{compact}.xlsx'
    sz_turn = workbook(sz_market)
    assert sz_turn[0][2] == '成交金额(元)'
    selected = [row for row in sz_turn[1:] if str(row[0]).strip() in ('主板A股', '创业板A股')]
    assert len(selected) == 2
    sz_amount = sum(number(row[2]) for row in selected)
    ratio = float((sh_buy + sz_buy) / (sh_amount + sz_amount) * 100)
    assert point['value'] is not None and abs(point['value'] - ratio) < 1e-10, day
    calculated.append(ratio)
    raw_files.update([*sh_paths, sz_path, sh_market, sz_market])
means = [None if i < 19 else sum(calculated[i-19:i+1])/20 for i in range(len(calculated))]
mean_card = cards['cn-margin-buy-share-a-stocks-ma20']
assert len(mean_card['points']) == len(calculated)
for expected, point in zip(means, mean_card['points']):
    assert expected is None and point['value'] is None or expected is not None and abs(expected-point['value']) < 1e-10
for values, card in [(calculated,ratio_card),(means,mean_card)]:
    for i, point in enumerate(card['percentiles']):
        prior = values[max(0,i-250):i]
        if values[i] is None or len(prior)!=250 or None in prior:
            assert point['value'] is None
        else:
            # The financing series uses a midrank for equal observations.
            expected=100*(sum(x < values[i] for x in prior)+.5*sum(x == values[i] for x in prior))/250
            assert abs(expected-point['value'])<.00501
result={'verifiedDates':len(calculated),'first':ratio_card['points'][0]['date'],
    'last':ratio_card['points'][-1]['date'],'latestRatio':calculated[-1],
    'latestMean20':means[-1], 'latestRatioPercentile':ratio_card['percentiles'][-1]['value'],
    'latestMeanPercentile':mean_card['percentiles'][-1]['value'], 'rawObjectsIndependentlyRead':len(raw_files),
    'latestPacketSha256':hashlib.sha256((ROOT/'web/public/research/microstructure-observations-20261108/funding.json').read_bytes()).hexdigest()}
(HERE/'root-funding-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
