#!/usr/bin/env python3
"""Prepare already acquired financial PDFs for controlled, evidence-preserving parsing.

This tool performs no network access and computes no market or portfolio effects.
The caller must supply a separately approved parser SHA before annual parsing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPECTED_DEVICE = 16777238
EXPECTED_UUID = 'DEBA1C85-6059-3865-B50A-A8EE1F80E4D9'
MIN_FREE_BYTES = 10 * 1024**3
PARSER_MODULE = ROOT / 'src/lei_signal/research/profitability_discovery.py'
ANNUAL_TITLE_RE = re.compile(r'(?<!\d)(20\d{2})\s*年?\s*(?:年度报告|年报)')
NOTICE_CONTEXT_RE = re.compile(r'公告|通知|说明')
NOTICE_ACTION_RE = re.compile(r'更正|补充')
REVISION_RE = re.compile(r'更新后|修订版|修订稿|更正后|补充后|已取消|取消|撤销')
CODE_RE = re.compile(r'(?<!\d)(\d{6})(?!\d)')
YEAR_RE = re.compile(r'(?<!\d)(20\d{2})\s*年')
ISSUER_CODE_FIELD_RE = re.compile(r'证券代码|股票代码|公司代码')


def cohort_to_publisher_code(cohort_code: str) -> str:
    match = re.fullmatch(r'(?:sh|sz)\.(\d{6})', str(cohort_code))
    if not match:
        raise ValueError(f'invalid frozen cohort code: {cohort_code}')
    return match.group(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_create_only(path: Path, payload: object) -> str:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _resolve_plan_path(plan_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else plan_path.parent / path


def _verify_external(plan_path: Path, plan: dict, out: Path) -> dict:
    storage_path = _resolve_plan_path(plan_path, plan['storage_plan'])
    storage = _read_json(storage_path)
    mount = Path(storage['external_mount'])
    expected_parent = Path(plan['output']).resolve()
    out = out.resolve()
    info = plistlib.loads(subprocess.run(
        ['/usr/sbin/diskutil', 'info', '-plist', str(mount)],
        capture_output=True, check=True, timeout=10).stdout)
    checks = {
        'mounted': os.path.ismount(mount),
        'uuid_matches': info.get('VolumeUUID') == EXPECTED_UUID == storage.get('external_uuid'),
        'device_matches': mount.stat().st_dev == EXPECTED_DEVICE == storage.get('external_device'),
        'external_result_exists': expected_parent.is_dir(),
        'result_on_expected_device': expected_parent.stat().st_dev == EXPECTED_DEVICE,
        'output_is_new_child': out.parent == expected_parent,
        'output_absent': not out.exists(),
        'free_reserve_ok': shutil.disk_usage(mount).free >= MIN_FREE_BYTES,
        'storage_plan_not_execution_authority': storage.get('execution_authorized') is False,
    }
    if not all(checks.values()):
        raise ValueError(f'external output guard failed: {checks}')
    return {'checks': checks, 'storage_plan_path': str(storage_path),
            'storage_plan_sha256': sha256_file(storage_path), 'external_mount': str(mount),
            'external_device': EXPECTED_DEVICE, 'external_uuid': EXPECTED_UUID,
            'reserve_bytes': MIN_FREE_BYTES}


def _announcement_date(milliseconds):
    if milliseconds is None or str(milliseconds).strip() == '':
        return None, None
    moment = datetime.fromtimestamp(int(milliseconds) / 1000, tz=timezone.utc).astimezone(
        ZoneInfo('Asia/Shanghai'))
    return moment.date().isoformat(), moment.isoformat()


def _validate_source_pdf(item: dict, publisher_code: str) -> tuple[Path, dict]:
    path_text = item.get('source_path')
    expected_hash = item.get('sha256')
    expected_bytes = item.get('bytes')
    if item.get('status') not in {'obtained', 'reused'}:
        raise ValueError('source_status_not_complete_obtained_or_reused')
    if not isinstance(path_text, str) or not path_text:
        raise ValueError('source_path_missing')
    if str(item.get('code', '')) != publisher_code:
        raise ValueError('publisher_code_differs_from_cohort_mapping')
    if not re.fullmatch(r'[0-9a-f]{64}', str(expected_hash or '')):
        raise ValueError('source_sha256_missing_or_invalid')
    if not isinstance(expected_bytes, int) or expected_bytes <= 5:
        raise ValueError('source_bytes_missing_or_invalid')
    path = Path(path_text)
    if not path.is_file():
        raise ValueError('source_file_missing')
    actual_bytes = path.stat().st_size
    actual_hash = sha256_file(path)
    with path.open('rb') as handle:
        prefix = handle.read(5)
    checks = {'status_qualified': True, 'publisher_code_matches': True,
              'bytes_match': actual_bytes == expected_bytes,
              'sha256_matches': actual_hash == expected_hash, 'pdf_header': prefix == b'%PDF-'}
    if not all(checks.values()):
        raise ValueError(f'source_identity_check_failed:{checks}')
    return path, {'path': str(path), 'bytes': actual_bytes, 'sha256': actual_hash,
                  'checks': checks}


def classify_pdf_header(pages: list[str], publisher_code: str, report_year: int | None,
                        announcement_title: str | None = None) -> dict:
    """Keep document form and issuer identity as independent evidence fields."""
    text = '\n'.join(pages[:8])
    code_matches = set(CODE_RE.findall(text))
    field_lines = [line.strip() for line in text.splitlines()
                   if ISSUER_CODE_FIELD_RE.search(line)]
    field_codes = set()
    for line in field_lines:
        field_codes.update(CODE_RE.findall(line))
    title_years = {int(value) for value in YEAR_RE.findall(text)}
    has_annual_title = bool(re.search(r'年度报告|年报', text))
    title_text = announcement_title or ''
    title_has_annual = bool(ANNUAL_TITLE_RE.search(title_text))
    title_notice = title_has_annual and bool(NOTICE_CONTEXT_RE.search(title_text))
    first_two_pages = '\n'.join(pages[:2])
    top_lines = [line.strip() for line in first_two_pages.splitlines() if line.strip()][:8]
    body_title_notice = any(
        ANNUAL_TITLE_RE.search(line)
        and NOTICE_CONTEXT_RE.search(line)
        and NOTICE_ACTION_RE.search(line)
        for line in top_lines)
    notices = title_notice or body_title_notice
    revision_text = '\n'.join([title_text, text])
    revision_markers = sorted(set(REVISION_RE.findall(revision_text)))
    if field_codes == {publisher_code}:
        identity = 'match'
    elif len(field_codes) > 1:
        identity = 'identity_unknown'
    elif field_codes and publisher_code not in field_codes:
        identity = 'conflict'
    elif publisher_code in code_matches and not field_codes:
        identity = 'weak_match'
    else:
        identity = 'identity_unknown'

    if not text.strip():
        form = 'unknown'
    elif notices:
        form = 'notice'
    elif report_year is not None and report_year in title_years and has_annual_title:
        form = 'suspected_full_text'
    elif has_annual_title:
        form = 'other_or_year_mismatch'
    else:
        form = 'unknown'
    return {'document_form': form, 'identity_status': identity,
            'identity_field_lines': field_lines, 'identity_field_codes': sorted(field_codes),
            'all_header_codes': sorted(code_matches), 'header_years': sorted(title_years),
            'annual_title_present': has_annual_title, 'notice_terms_present': notices,
            'title_notice_context': title_notice, 'body_title_notice_context': body_title_notice,
            'revision_markers': revision_markers,
            'cancellation_date': 'unknown' if re.search(r'已取消|取消|撤销', revision_text) else None,
            'header_text_pages': len(pages[:8])}


def _extract_all_pages(pdf_path: Path) -> list[str]:
    import pypdfium2

    pdf = pypdfium2.PdfDocument(str(pdf_path))
    pages = []
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            text_page = None
            try:
                text_page = page.get_textpage()
                pages.append(text_page.get_text_range())
            finally:
                if text_page is not None:
                    text_page.close()
                page.close()
    finally:
        pdf.close()
    return pages


def _source_rows(progress: dict, cohort: dict, limit_codes: int | None):
    codes = cohort['fixed_codes']
    if len(codes) != 600 or len(set(codes)) != 600:
        raise ValueError('frozen cohort must contain 600 unique ordered codes')
    mapping = {code: cohort_to_publisher_code(code) for code in codes}
    if len(set(mapping.values())) != len(codes):
        raise ValueError('cohort to publisher code mapping is not one-to-one')
    publisher_to_cohort = {publisher: full for full, publisher in mapping.items()}
    source_codes = progress.get('codes')
    if not isinstance(source_codes, dict):
        raise ValueError('progress codes must be an object keyed by exact cohort code')
    unknown = sorted(set(source_codes) - set(publisher_to_cohort))
    if unknown:
        raise ValueError(f'progress contains codes outside frozen cohort: {unknown[:5]}')
    chosen = codes if limit_codes is None else codes[:limit_codes]
    for cohort_code in chosen:
        publisher_code = mapping[cohort_code]
        state = source_codes.get(publisher_code)
        if not isinstance(state, dict) or state.get('status') not in {'complete', 'incomplete'}:
            yield cohort_code, publisher_code, None, 'code_state_not_final_complete_or_incomplete'
            continue
        for item in state.get('pdfs', []):
            if not isinstance(item, dict) or item.get('status') not in {'obtained', 'reused'}:
                continue
            yield cohort_code, publisher_code, item, None


def _load_parser(expected_sha256: str):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('--parser-sha256 must be a lowercase SHA-256 digest')
    actual = sha256_file(PARSER_MODULE)
    if actual != expected_sha256:
        raise ValueError(f'parser SHA mismatch: expected {expected_sha256}, actual {actual}')
    sys.path.insert(0, str(ROOT / 'src'))
    module = importlib.import_module('lei_signal.research.profitability_discovery')
    return module, actual


def prepare(progress_path: Path, plan_path: Path, parser_sha256: str,
            out: Path, limit_codes: int | None = None) -> dict:
    progress_path, plan_path, out = progress_path.resolve(), plan_path.resolve(), out.resolve()
    if limit_codes is not None and limit_codes < 1:
        raise ValueError('--limit-codes must be positive')
    plan = _read_json(plan_path)
    if plan.get('schema') != 'financial-filings-acquisition/1':
        raise ValueError('unexpected bulk acquisition plan schema')
    storage_receipt = _verify_external(plan_path, plan, out)
    cohort_path = Path(plan['cohort_path'])
    if sha256_file(cohort_path) != plan['cohort_sha256']:
        raise ValueError('bound financial cohort SHA mismatch')
    cohort = _read_json(cohort_path)
    if progress_path.is_file() is False:
        raise ValueError('progress file does not exist')
    progress = _read_json(progress_path)
    if progress.get('schema') != 'financial-filings-progress/1':
        raise ValueError('unexpected acquisition progress schema')
    if not PARSER_MODULE.is_file():
        raise ValueError(f'parser module is missing in owned worktree: {PARSER_MODULE}')
    parser, parser_sha = _load_parser(parser_sha256)

    out.mkdir(exist_ok=False)
    if out.stat().st_dev != EXPECTED_DEVICE:
        raise ValueError('created output directory is not on the authorized external device')
    docs_dir = out / 'documents'
    notices_dir = out / 'notice-text'
    docs_dir.mkdir()
    notices_dir.mkdir()
    summary = {'schema': 'financial-document-preparation/1',
               'created_at': datetime.now(timezone.utc).isoformat(),
               'progress_path': str(progress_path), 'progress_sha256': sha256_file(progress_path),
               'plan_path': str(plan_path), 'plan_sha256': sha256_file(plan_path),
               'cohort_path': str(cohort_path), 'cohort_sha256': sha256_file(cohort_path),
               'parser_module_path': str(PARSER_MODULE), 'parser_module_sha256': parser_sha,
               'storage': storage_receipt,
               'limit_codes': limit_codes,
               'limit_codes_meaning': 'source-qualification diagnostic count only; not a financial-effect sample',
               'source_code_counts': {'complete': 0, 'incomplete': 0, 'not_final_or_missing': 0},
               'documents': [], 'errors': [],
               'market_effects_run': False, 'version_chain_completeness_inferred': False}
    selected_codes = cohort['fixed_codes'] if limit_codes is None else cohort['fixed_codes'][:limit_codes]
    for code in selected_codes:
        state = progress.get('codes', {}).get(cohort_to_publisher_code(code))
        if isinstance(state, dict) and state.get('status') in {'complete', 'incomplete'}:
            summary['source_code_counts'][state['status']] += 1
        else:
            summary['source_code_counts']['not_final_or_missing'] += 1
    seen = set()
    for cohort_code, publisher_code, item, skip_reason in _source_rows(progress, cohort, limit_codes):
        if item is None:
            summary['errors'].append({'cohort_code': cohort_code,
                                      'publisher_code': publisher_code, 'reason': skip_reason})
            continue
        key = (cohort_code, str(item.get('announcement_id', '')))
        if key in seen:
            summary['errors'].append({'cohort_code': cohort_code, 'publisher_code': publisher_code,
                                      'announcement_id': key[1],
                                      'reason': 'duplicate_document_identity'})
            continue
        seen.add(key)
        try:
            pdf_path, source_identity = _validate_source_pdf(item, publisher_code)
            title = item.get('announcement_title')
            year = item.get('report_year_from_title')
            year = int(year) if year is not None else None
            announcement_day, announcement_time = _announcement_date(item.get('announcement_time_ms'))
            pages = _extract_all_pages(pdf_path)
            header = classify_pdf_header(pages, publisher_code, year, title)
            categories = list(item.get('categories') or [])
            is_annual_candidate = 'annual' in categories and year is not None
            parsed = None
            if is_annual_candidate:
                parsed = parser.parse_annual_pdf(pdf_path, year, publisher_code,
                                                 item.get('announcement_id'), announcement_day)
            entry = {'source': {'cohort_code': cohort_code,
                                'publisher_code': publisher_code,
                                'announcement_id': str(item.get('announcement_id', '')),
                                'title': title, 'categories': categories,
                                'report_year_from_title': year,
                                'announcement_time_ms': item.get('announcement_time_ms'),
                                'announcement_date_asia_shanghai': announcement_day,
                                'announcement_time_asia_shanghai': announcement_time,
                                'publisher_metadata': {k: item.get(k) for k in (
                                    'org_id_from_response', 'adjunct_url_as_returned',
                                    'pdf_url', 'status', 'reason')},
                                'source_identity': source_identity},
                     'header_evidence': header,
                     'financial_parser_result': parsed,
                     'version_chain_completeness': 'unknown'}
            stem = f'{publisher_code}-{item.get("announcement_id", "unknown")}'
            entry_path = docs_dir / f'{stem}.json'
            entry_sha = write_json_create_only(entry_path, entry)
            notice_output = None
            if 'correction' in categories or header['document_form'] == 'notice':
                notice_payload = [{'page': i + 1, 'text': text} for i, text in enumerate(pages)]
                notice_path = notices_dir / f'{stem}.json'
                notice_sha = write_json_create_only(notice_path, notice_payload)
                notice_output = {'path': str(notice_path), 'sha256': notice_sha,
                                 'pages': len(notice_payload)}
            summary['documents'].append({'cohort_code': cohort_code,
                                         'publisher_code': publisher_code,
                                         'announcement_id': str(item.get('announcement_id', '')),
                                         'path': str(entry_path), 'sha256': entry_sha,
                                         'notice_text': notice_output,
                                         'document_form': header['document_form'],
                                         'identity_status': header['identity_status']})
        except Exception as exc:
            summary['errors'].append({'cohort_code': cohort_code,
                                      'publisher_code': publisher_code,
                                      'announcement_id': str(item.get('announcement_id', '')),
                                      'reason': f'{type(exc).__name__}:{exc}'})
    summary['counts'] = {'documents_written': len(summary['documents']),
                         'documents_failed': len(summary['errors']),
                         'source_complete_codes': summary['source_code_counts']['complete'],
                         'source_incomplete_codes': summary['source_code_counts']['incomplete']}
    summary_path = out / 'manifest.json'
    summary['manifest_path'] = str(summary_path)
    summary['manifest_sha256'] = write_json_create_only(summary_path, summary)
    return summary


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--progress', required=True, type=Path,
                     help='read-only acquisition progress.json')
    cli.add_argument('--plan', required=True, type=Path,
                     help='frozen bulk-acquisition plan JSON')
    cli.add_argument('--parser-sha256', required=True,
                     help='approved SHA-256 of profitability_discovery.py')
    cli.add_argument('--out', required=True, type=Path,
                     help='new directory directly under the approved external result path')
    cli.add_argument('--limit-codes', type=int,
                     help='diagnostic source-qualification prefix length; not an effects sample')
    args = cli.parse_args(argv)
    result = prepare(args.progress, args.plan, args.parser_sha256, args.out, args.limit_codes)
    print(json.dumps({'manifest_path': result['manifest_path'],
                      'manifest_sha256': result['manifest_sha256'],
                      'counts': result['counts']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
