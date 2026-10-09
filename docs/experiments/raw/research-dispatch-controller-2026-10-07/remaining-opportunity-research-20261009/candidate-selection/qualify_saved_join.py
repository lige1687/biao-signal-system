"""Read-only identity/source qualification; never reads Y or computes outcomes."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
PLAN = HERE / 'execution-plan.json'
MANIFEST = HERE / 'source-manifest.json'
OUT = HERE / 'qualification-receipt.json'
FIELDS = ('open', 'high', 'low', 'close')
CSV_FIELDS = ('asset', 'date', 'profile_known', 'profile_unknown_reason',
              'overhead_supply_ratio', 'profile_window_start', 'profile_window_end',
              'volume_break_dates_in_window')


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def finite_positive(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def close(a, b) -> bool:
    return finite_positive(a) and finite_positive(b) and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)


def checked_index(rows, label):
    out = {}
    by_asset = {}
    for row in rows:
        key = (row['asset'], row['date'])
        if key in out:
            raise ValueError(f'duplicate {label} key {key}')
        out[key] = row
        by_asset.setdefault(row['asset'], []).append(row)
    for asset, group in by_asset.items():
        if [r['date'] for r in group] != sorted(r['date'] for r in group):
            raise ValueError(f'unsorted {label} dates {asset}')
    return out, by_asset


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    plan = load_json(PLAN)
    if digest(Path(__file__)) != plan['script_sha256'] or digest(MANIFEST) != plan['manifest_sha256']:
        raise ValueError('execution script or manifest drift')
    m = load_json(MANIFEST)
    paths = {
        'case': (Path(m['native_cases']['path']), m['native_cases']['sha256']),
        'feature_csv': (REPO / m['saved_feature']['path'], m['saved_feature']['sha256']),
        'qualification': (REPO / m['saved_feature']['qualification_path'], m['saved_feature']['qualification_sha256']),
        'profile_panel': (REPO / m['saved_feature']['underlying_panel_path'], m['saved_feature']['underlying_panel_sha256']),
        'native_price': (REPO / m['native_price']['path'], m['native_price']['sha256']),
        'native_calendar': (REPO / m['native_calendar']['path'], m['native_calendar']['sha256']),
        'profile_source_manifest': (REPO / m['saved_feature']['source_manifest_path'], m['saved_feature']['source_manifest_sha256']),
        'definition': (REPO / m['definition']['path'], m['definition']['sha256']),
        'feature_adapter': (REPO / m['frozen_feature_code']['adapter_path'], m['frozen_feature_code']['adapter_sha256']),
        'feature_proxy': (REPO / m['frozen_feature_code']['proxy_path'], m['frozen_feature_code']['proxy_sha256']),
    }
    if sorted(paths) != sorted(plan['inputs']):
        raise ValueError('input inventory drift')
    for name, (path, expected) in paths.items():
        if digest(path) != expected or plan['inputs'][name] != expected:
            raise ValueError(f'{name} SHA mismatch')
    cases = load_json(paths['case'][0])
    panel = load_json(paths['profile_panel'][0])
    native = load_json(paths['native_price'][0])
    qualification = load_json(paths['qualification'][0])
    assert len(cases) == 76 and panel['price_series'] == 'economic_price'
    assert qualification['input_policy']['price_series'].startswith('economic_price')
    profile, profile_by_asset = checked_index(panel['bars'], 'profile panel')
    native_idx, native_by_asset = checked_index(native['bars'], 'native price')
    features = {}
    with paths['feature_csv'][0].open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        if not set(CSV_FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('saved feature fields missing')
        for raw in reader:
            row = {field: raw[field] for field in CSV_FIELDS}
            key = (row['asset'], row['date'])
            if key in features:
                raise ValueError(f'duplicate feature key {key}')
            features[key] = row
    case_keys = [(c['asset'], c['date']) for c in cases]
    if len(set(case_keys)) != 76 or len({c['case_id'] for c in cases}) != 76:
        raise ValueError('case identity duplicate')
    if sum(len(c['member_event_ids']) for c in cases) != 84 or len({c['lifecycle'] for c in cases}) != 33:
        raise ValueError('alias/lifecycle count drift')
    if any(c['price_basis_id'] != 'economic_price' or c['source_sha256'][0] != paths['native_price'][1] for c in cases):
        raise ValueError('case price basis drift')
    native_pos = {a: {r['date']: i for i, r in enumerate(rows)} for a, rows in native_by_asset.items()}
    profile_pos = {a: {r['date']: i for i, r in enumerate(rows)} for a, rows in profile_by_asset.items()}
    results = []
    for case in cases:
        asset, date = case['asset'], case['date']
        reasons = []
        if asset not in profile_by_asset:
            reasons.append('outside_saved_four_etfs')
        else:
            f = features.get((asset, date))
            if f is None:
                reasons.append('saved_feature_key_absent')
            if date not in profile_pos[asset] or date not in native_pos.get(asset, {}):
                reasons.append('case_date_missing_in_price_panel')
            if not reasons:
                pi = profile_pos[asset][date]
                ni = native_pos[asset][date]
                if pi < 251 or ni < 251:
                    reasons.append('less_than_252_history')
                else:
                    pw = profile_by_asset[asset][pi-251:pi+1]
                    nw = native_by_asset[asset][ni-251:ni+1]
                    if [r['date'] for r in pw] != [r['date'] for r in nw]:
                        reasons.append('historical_252_date_sequence_mismatch')
                    if any(r.get('status') != 'quoted' or r.get('action_known') is not True or
                           not all(finite_positive(r.get(field)) for field in FIELDS) for r in pw):
                        reasons.append('profile_252_price_unqualified')
                    if any(not all(close(p.get(field), n.get(field)) for field in FIELDS)
                           for p, n in zip(pw, nw, strict=True)):
                        reasons.append('historical_252_ohlc_mismatch')
                    trailing = pw[-120:]
                    native_trailing = nw[-120:]
                    if f['profile_window_start'] != trailing[0]['date'] or f['profile_window_end'] != date:
                        reasons.append('feature_120_window_dates_mismatch')
                    if any(r.get('volume_source_known') is not True or r.get('volume_break') is not False or
                           not finite_positive(r.get('volume')) for r in trailing):
                        reasons.append('profile_120_volume_unqualified')
                    if f['volume_break_dates_in_window']:
                        reasons.append('saved_feature_break_in_window')
                    if any(not close(p.get('volume'), n.get('volume'))
                           for p, n in zip(trailing, native_trailing, strict=True)):
                        reasons.append('historical_120_volume_unit_or_source_mismatch')
                    if f['profile_known'] != 'True' or f['profile_unknown_reason']:
                        reasons.append('saved_profile_unknown')
                    try:
                        ratio = float(f['overhead_supply_ratio'])
                        if not math.isfinite(ratio) or not 0 <= ratio <= 1:
                            reasons.append('saved_ratio_invalid')
                    except ValueError:
                        reasons.append('saved_ratio_missing')
        results.append({'case_id': case['case_id'], 'asset': asset, 'signal_date': date,
                        'lifecycle': case['lifecycle'], 'qualified': not reasons, 'reasons': reasons})
    counts = Counter(reason for row in results for reason in row['reasons'])
    by_asset = {asset: {'all_cases': sum(r['asset'] == asset for r in results),
                        'qualified': sum(r['asset'] == asset and r['qualified'] for r in results)}
                for asset in sorted({r['asset'] for r in results})}
    receipt = {'schema': 'goal3-saved-join-qualification/1', 'status': 'qualification_only_no_y_read',
               'execution_plan_sha256': digest(PLAN), 'script_sha256': plan['script_sha256'],
               'manifest_sha256': plan['manifest_sha256'], 'source_sha256': plan['inputs'],
               'case_count': len(cases), 'alias_count': 84, 'lifecycle_count': 33,
               'qualified_count': sum(r['qualified'] for r in results),
               'by_asset': by_asset, 'reasons': dict(sorted(counts.items())), 'cases': results,
               'not_checked': ['Y contents', 'effect', 'historic vendor arrival', 'independent incremental value']}
    with OUT.open('x', encoding='utf-8') as fh:
        json.dump(receipt, fh, ensure_ascii=False, indent=2)
        fh.write('\n')


if __name__ == '__main__':
    main()
