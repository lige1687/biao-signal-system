"""Independent read-only source and exact-arithmetic check; writes only its receipt."""

import csv
import hashlib
import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
OLD = Path('/Volumes/win+mac通用/LeiSignal-新实验结果/contrarian-market-data-research-20261020/contrarian-market-data-research-20261020-20261020T201641-8db4c9e11062/result/china')
NEW_J = HERE.parent / 'institutional-flow-return-study-2026-10-23/cn-source-qualification'
H = json.loads((HERE / 'huaxia/fields.json').read_text())
J = json.loads((NEW_J / '070002-2024FY-fields.json').read_text())
OLD_FIELDS = next(x for x in json.loads((OLD / '070002-report-fields.json').read_text()) if x['period_end'] == '2024-06-30')
ROOT = json.loads((HERE / 'comparison-summary.json').read_text())


def f(value):
    return Fraction(str(value).replace(',', ''))


def ratio_record(value):
    return {'numerator': value.numerator, 'denominator': value.denominator,
            'decimal_12': format(Decimal(value.numerator) / Decimal(value.denominator), '.12f')}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_holdings(path, period=None):
    with path.open(newline='') as source:
        rows = list(csv.DictReader(source))
    if period:
        rows = [row for row in rows if row['period_end'] == period]
    assert len(rows) == len({row['stock_code'] for row in rows})
    assert len(rows) == len({int(row.get('rank', row.get('index'))) for row in rows})
    assert sorted(int(row.get('rank', row.get('index'))) for row in rows) == list(range(1, len(rows) + 1))
    return {row['stock_code']: row for row in rows}


paths = {
    '070002_H1': OLD / '070002-holdings.csv',
    '070002_FY': NEW_J / '070002-2024FY-holdings.csv',
    '000001_H1': Path(H['2024H1']['holdings_csv']),
    '000001_FY': Path(H['2024FY']['holdings_csv']),
}
source_hashes = {key: sha(path) for key, path in paths.items()}
assert {str(paths[key]): digest for key, digest in source_hashes.items()} == ROOT['sources']
rows = {
    '070002': (load_holdings(paths['070002_H1'], '2024-06-30'), load_holdings(paths['070002_FY'])),
    '000001': (load_holdings(paths['000001_H1']), load_holdings(paths['000001_FY'])),
}
expected_rows = {'070002': (69, 39), '000001': (174, 175)}
assert {key: tuple(map(len, pair)) for key, pair in rows.items()} == expected_rows

pdfs = {
    '070002_H1': (OLD / '070002-2024H1-jsfund.pdf', OLD_FIELDS['sha256']),
    '070002_FY': (Path('/Volumes/win+mac通用/LeiSignal-新实验结果/institutional-flow-return-study-20261023/institutional-flow-return-study-20261023-20261023T172814-06ef305d60d5/result/china/070002-2024FY-jsfund.pdf'), J['pdf_sha256']),
    '000001_H1': (Path(H['2024H1']['official_pdf_path']), H['2024H1']['official_pdf_sha256']),
    '000001_FY': (Path(H['2024FY']['official_pdf_path']), H['2024FY']['official_pdf_sha256']),
}
pdf_hashes = {}
for key, (path, expected) in pdfs.items():
    actual = sha(path)
    assert actual == expected, (key, actual, expected)
    pdf_hashes[key] = actual

funds = {}
for fund, (start, end) in rows.items():
    counts = {'start': len(start), 'end': len(end), 'union': len(start.keys() | end.keys()),
              'both': len(start.keys() & end.keys()), 'entered': len(end.keys() - start.keys()),
              'absent_at_end': len(start.keys() - end.keys())}
    values = (sum((f(row['fair_value_cny']) for row in start.values()), Fraction()),
              sum((f(row['fair_value_cny']) for row in end.values()), Fraction()))
    if fund == '070002':
        h1 = {key: f(OLD_FIELDS[key + '_units']) for key in ('opening', 'subscriptions', 'redemptions', 'closing')}
        fy = {key: f(J['annual_flow'][key + '_units']) for key in ('opening', 'subscriptions', 'redemptions', 'closing')}
        reported = (f(OLD_FIELDS['stock_assets_cny']), f(J['stock_assets_cny']))
        h2_saved = {key: f(J['derived_2024H2_flow'][key + '_units']) for key in h1}
    else:
        h1 = {key: f(H['2024H1']['flow'][key]) for key in ('opening', 'subscriptions', 'redemptions', 'closing')}
        fy = {key: f(H['2024FY']['flow'][key]) for key in h1}
        reported = (f(H['2024H1']['stock_assets_cny']), f(H['2024FY']['stock_assets_cny']))
        h2_saved = {key: f(H['2024H2_derived_flow'][key]) for key in h1}
    assert values == reported, (fund, values, reported)
    for period in (h1, fy):
        assert period['opening'] + period['subscriptions'] - period['redemptions'] == period['closing']
    assert h1['opening'] == fy['opening']
    h2 = {'opening': h1['closing'], 'subscriptions': fy['subscriptions'] - h1['subscriptions'],
          'redemptions': fy['redemptions'] - h1['redemptions'], 'closing': fy['closing']}
    assert h2 == h2_saved
    assert h2['opening'] + h2['subscriptions'] - h2['redemptions'] == h2['closing']
    net = h2['redemptions'] - h2['subscriptions']
    p = max(net / h2['opening'], Fraction())
    root = ROOT['funds'][fund]
    assert (counts['start'], counts['end'], counts['union'], counts['both']) == (root['start_holdings'], root['end_holdings'], root['union'], root['both'])
    assert p == f(str(root['net_redemption_unit_fraction'])) or abs(float(p) - root['net_redemption_unit_fraction']) < 1e-15
    funds[fund] = {'counts': counts, 'value_cny': [str(Decimal(v.numerator) / Decimal(v.denominator)) for v in values],
                   'h2_units': {key: str(Decimal(v.numerator) / Decimal(v.denominator)) for key, v in h2.items()},
                   'net_redeemed_units': str(Decimal(net.numerator) / Decimal(net.denominator)),
                   'net_redemption_fraction': ratio_record(p)}

start_j, end_j = rows['070002']
start_h, end_h = rows['000001']
initial = start_j.keys() | start_h.keys()
joint = start_j.keys() & start_h.keys()
final = end_j.keys() | end_h.keys()
final_joint = end_j.keys() & end_h.keys()
four = joint & final_joint
assert (len(initial), len(joint), len(final), len(final_joint), len(four)) == (234, 9, 198, 16, 5)
assert (len(initial), len(joint), len(final), len(final_joint), len(four)) == tuple(ROOT[key] for key in ('initial_union', 'initial_common', 'final_union', 'final_common', 'four_observation_common'))

five = {}
for code in sorted(four):
    candidates = [start_j[code], end_j[code], start_h[code], end_h[code]]
    names = [row['stock_name'].replace(' ', '') for row in candidates]
    assert len(set(names)) == 1, (code, names)
    qj0, qj1, qh0, qh1 = (f(row['shares']) for row in candidates)
    assert min(qj0, qj1, qh0, qh1) > 0
    relative = (qj1 * qh0) / (qj0 * qh1)
    root = next(item for item in ROOT['relative_share_ratios'] if item['code'] == code)
    assert abs(float(relative) - root['relative_share_ratio']) < 1e-12
    five[code] = {'name': names[0], 'shares': [str(int(q)) for q in (qj0, qj1, qh0, qh1)],
                  'relative_share_ratio': ratio_record(relative)}

# Read the saved official PDFs, not just the extracted CSVs. A code and its
# Chinese name must occur together in each report's holdings text.
pdf_text = {key: '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
            for key, (path, _) in pdfs.items()}
for code, item in five.items():
    pattern = re.compile(re.escape(code) + r'\s+' + re.escape(item['name']))
    for key, text in pdf_text.items():
        assert pattern.search(text), (code, item['name'], key)

p_j = f(funds['070002']['net_redemption_fraction']['numerator']) / f(funds['070002']['net_redemption_fraction']['denominator'])
p_h = f(funds['000001']['net_redemption_fraction']['numerator']) / f(funds['000001']['net_redemption_fraction']['denominator'])
pressure_by_code = {}
weights = set()
for code in initial:
    a = f(start_j[code]['fair_value_cny']) if code in start_j else Fraction()
    b = f(start_h[code]['fair_value_cny']) if code in start_h else Fraction()
    assert a + b > 0
    weight = a / (a + b)
    direct = (a * p_j + b * p_h) / (a + b)
    affine = p_h + (p_j - p_h) * weight
    assert direct == affine, (code, direct, affine)
    weights.add(weight)
    pressure_by_code[code] = direct
unique_exact = len(set(pressure_by_code.values()))
assert unique_exact == len(weights) == 11

# Reproduce the original bounded-precision path separately. Decimal's
# division rounds p before each stock's weighted arithmetic; algebraically
# identical single-fund cases can then differ in the last decimal place.
p_j_decimal = Decimal(funds['070002']['net_redeemed_units']) / Decimal(funds['070002']['h2_units']['opening'])
p_h_decimal = Decimal(funds['000001']['net_redeemed_units']) / Decimal(funds['000001']['h2_units']['opening'])
decimal_values = set()
for code in initial:
    a = Decimal(start_j[code]['fair_value_cny']) if code in start_j else Decimal()
    b = Decimal(start_h[code]['fair_value_cny']) if code in start_h else Decimal()
    decimal_values.add((a * p_j_decimal + b * p_h_decimal) / (a + b))
assert len(decimal_values) == ROOT['pressure_values_unique'] == 14

receipt = {
    'scope': 'Independent read-only four-report arithmetic and source-text verification; no prices or future returns read',
    'source_csv_sha256': source_hashes,
    'official_pdf_sha256': pdf_hashes,
    'funds': funds,
    'cross_fund': {'initial_union': len(initial), 'initial_common': len(joint),
                   'final_union': len(final), 'final_common': len(final_joint),
                   'four_observation_common': len(four), 'five_common': five,
                   'five_name_and_code_present_in_all_four_original_pdfs': True},
    'pressure': {'definition': 'beginning holding value weighted positive net unit redemption fraction',
                 'unique_exact_fraction_values': unique_exact,
                 'unique_exact_ownership_weights': len(weights),
                 'max_affine_residual_exact': '0',
                 'single_fund_values': 2, 'both_fund_codes': len(joint),
                 'root_decimal_string_unique_count': ROOT['pressure_values_unique'],
                 'independently_reproduced_decimal_28_unique_count': len(decimal_values),
                 'decimal_precision': 28,
                 'root_decimal_string_count_is_precision_artifact': ROOT['pressure_values_unique'] != unique_exact,
                 'corrected_unique_count_for_report': unique_exact,
                 'interpretation': 'One interval with two funds: pressure contains no cross-sectional ranking information beyond beginning ownership fraction.'},
    'returns_read': False, 'effects_calculated': False,
}
target = HERE / 'independent-check.json'
if target.exists():
    assert json.loads(target.read_text())['pressure']['corrected_unique_count_for_report'] == unique_exact
target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'passed_with_corrected_unique_count', 'unique_exact': unique_exact,
                  'root_decimal_count': ROOT['pressure_values_unique'], 'five_codes': sorted(four)}, ensure_ascii=False))
