#!/usr/bin/env python3
"""Annotate narrowly verified issuer-CIK windows without changing source candidates."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def month_ord(value):
    year, month = map(int, value.split('-'))
    return year * 12 + month


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', required=True)
    ap.add_argument('--candidates', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    rules_path, candidates_path, out = Path(args.rules), Path(args.candidates), Path(args.out)
    rules_doc = json.loads(rules_path.read_text(encoding='utf-8'))
    expected_candidates_sha = rules_doc['source_candidate_sha256']
    actual_candidates_sha = sha256(candidates_path)
    if actual_candidates_sha != expected_candidates_sha:
        raise SystemExit(f'candidate SHA mismatch: {actual_candidates_sha}')
    if out.exists():
        raise SystemExit(f'output exists; refusing overwrite: {out}')
    out.mkdir(parents=True, exist_ok=False)
    with candidates_path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        source_rows = list(reader)
    required = {'month', 'ticker', 'candidate_ciks'}
    if not required.issubset(fields):
        raise SystemExit(f'unexpected source schema; missing {sorted(required - set(fields))}')

    selected = []
    by_rule = {}
    for rule in rules_doc['rules']:
        tickers = set(rule.get('tickers', [rule.get('ticker')]))
        low, high = month_ord(rule['start_month']), month_ord(rule['end_month'])
        matched = [r for r in source_rows if r['ticker'] in tickers and low <= month_ord(r['month']) <= high]
        by_rule[rule.get('ticker', '+'.join(rule.get('tickers', [])))] = len(matched)
        for row in matched:
            corrected = str(rule['cik']).zfill(10)
            selected.append({
                **row,
                'source_candidate_ciks': row.get('candidate_ciks', ''),
                'corrected_issuer_cik_annotation': corrected,
                'verified_issuer_annotation': rule['issuer'],
                'rule_window_start_month': rule['start_month'],
                'rule_window_end_month_inclusive': rule['end_month'],
                'retain_distinct_label_note': rule['retain_distinct_label'],
                'evidence_json': json.dumps(rule['evidence'], ensure_ascii=False),
                'annotation_only_not_financial_inheritance': 'true'
            })
    keys = [(r['month'], r['ticker']) for r in selected]
    if len(keys) != len(set(keys)):
        raise SystemExit('duplicate (month,ticker) selected; refusing output')
    out_fields = fields + [
        'source_candidate_ciks', 'corrected_issuer_cik_annotation', 'verified_issuer_annotation',
        'rule_window_start_month', 'rule_window_end_month_inclusive', 'retain_distinct_label_note',
        'evidence_json', 'annotation_only_not_financial_inheritance'
    ]
    data_path = out / 'changed-candidates.csv'
    with data_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(selected)
    counts = dict(by_rule)
    summary = {
        'selected_row_count': len(selected),
        'unique_month_ticker_keys': len(set(keys)),
        'expected_count_for_review_only': 52,
        'counts_by_rule': counts,
        'no_forcing_to_expected_count': True,
        'source_candidates_sha256': actual_candidates_sha,
        'rules_sha256': sha256(rules_path),
        'preserves_original_candidate_values': True,
        'does_not_authorize_predecessor_financial_inheritance_or_terminal_value': True
    }
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    outputs = []
    for name in ['changed-candidates.csv', 'summary.json']:
        p = out / name
        outputs.append({'path': name, 'sha256': sha256(p), 'bytes': p.stat().st_size})
    manifest = {
        'rules_path': str(rules_path.resolve()), 'rules_sha256': sha256(rules_path),
        'candidate_path': str(candidates_path.resolve()), 'candidate_sha256': actual_candidates_sha,
        'outputs': outputs, 'selected_rows': len(selected), 'source_only': True
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Re-read UTF-8 CSV and verify keys/counts and file hashes.
    with data_path.open(encoding='utf-8', newline='') as f:
        reread = list(csv.DictReader(f))
    if len(reread) != len(selected) or len({(r['month'], r['ticker']) for r in reread}) != len(selected):
        raise SystemExit('readback row/key verification failed')
    for item in outputs:
        if sha256(out / item['path']) != item['sha256']:
            raise SystemExit(f'readback hash mismatch: {item["path"]}')
    print(json.dumps({'status': 'success', 'output': str(out), 'summary': summary,
                      'manifest_sha256': sha256(out / 'manifest.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
