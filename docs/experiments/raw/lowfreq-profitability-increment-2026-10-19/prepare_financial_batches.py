#!/usr/bin/env python3
"""Incremental original-document preparation; no network or market effects.

Contract financial-document-batch/1 binds inputs progress/plan/cohort/parser/
preparer as {path,sha256}, reuse_manifests likewise, workers=1..4, output path.
The approved preparer's evidence rules and financial parser remain unchanged.
PDFium runs in separate processes; a PDF is extracted once per new document.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COHORT_SHA = '6f073e37809613469efe6cd2adb6b7ef1b4e77515e99e7149e1636d9e390cc16'
PARSER_SHA = 'dc009a8e95ae1e61dabed0ee861f0109b686f0bebeacb7b1985a91dd5e1f42ae'
PREPARER_SHA = '3bdabe21d029f648435812ab3c517d1d66b46afb8343ca62adb4815d90a9f012'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def bind(record):
    p = Path(record['path']).resolve()
    if sha(p) != record['sha256']:
        raise ValueError(f'input fingerprint mismatch: {p}')
    return p


def write(path, payload):
    b = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    with Path(path).open('xb') as f:
        f.write(b)
        f.flush()
        os.fsync(f.fileno())
    return hashlib.sha256(b).hexdigest()


def load_preparer(path):
    p = Path(path)
    if sha(p) != PREPARER_SHA:
        raise ValueError('approved preparer changed')
    spec = importlib.util.spec_from_file_location('approved_financial_preparer', p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_one(job):
    """Return evidence to the sole parent writer; no worker writes files."""
    full_code, code, item, preparer_path = job
    helper = load_preparer(preparer_path)
    try:
        pdf_path, source_identity = helper._validate_source_pdf(item, code)
        parser, _ = helper._load_parser(PARSER_SHA)
        title = item.get('announcement_title')
        year = item.get('report_year_from_title')
        title_match = helper.ANNUAL_TITLE_RE.search(title or '')
        title_year = int(title_match.group(1)) if title_match and not helper.re.search(
            r'半年度|季度|季报|中期', title or '') else None
        year = int(year) if year is not None else title_year
        if year is not None and title_year is not None and year != title_year:
            raise ValueError('title_year_conflicts_with_acquisition_record')
        day, moment = helper._announcement_date(item.get('announcement_time_ms'))
        pages = helper._extract_all_pages(pdf_path)
        header = helper.classify_pdf_header(pages, code, year, title)
        categories = list(item.get('categories') or [])
        candidate = helper.annual_candidate_evidence(
            categories, year, title, header, pages, parser.HEAD)
        parsed = None
        if candidate['status'] == 'suspected':
            parsed = {'code': str(code), 'report_year': int(year),
                      'announcement_id': str(item.get('announcement_id')),
                      'publication_date': str(day), 'source_path': str(pdf_path),
                      'source_sha256': source_identity['sha256'], 'page_count': len(pages),
                      'text_extractable_pages': sum(bool(p.strip()) for p in pages)}
            try:
                parsed.update(parser._parse_text_pages(pages, int(year)))
            except Exception as exc:
                # Match the approved parser's exception evidence semantics.
                parsed.update({'status': 'unknown', 'reason': 'pdf_extraction_error',
                               'error': f'{type(exc).__name__}: {exc}'})
        entry = {
            'source': {'cohort_code': full_code, 'publisher_code': code,
                       'announcement_id': str(item.get('announcement_id', '')),
                       'title': title, 'categories': categories,
                       'report_year_from_title': year,
                       'announcement_time_ms': item.get('announcement_time_ms'),
                       'announcement_date_asia_shanghai': day,
                       'announcement_time_asia_shanghai': moment,
                       'publisher_metadata': {k: item.get(k) for k in (
                           'org_id_from_response', 'adjunct_url_as_returned', 'pdf_url',
                           'status', 'reason')}, 'source_identity': source_identity},
            'header_evidence': header, 'annual_candidate_evidence': candidate,
            'financial_parser_result': parsed, 'version_chain_completeness': 'unknown'}
        notice = ([{'page': i + 1, 'text': text} for i, text in enumerate(pages)]
                  if 'correction' in categories or header['document_form'] == 'notice' else None)
        return {'entry': entry, 'notice': notice}
    except Exception as exc:
        return {'error': {'cohort_code': full_code, 'publisher_code': code,
                         'announcement_id': str(item.get('announcement_id', '')),
                         'source_sha256': item.get('sha256'),
                         'reason': f'{type(exc).__name__}:{exc}'}}


def reusable_documents(manifest_bindings):
    documents, errors = {}, {}
    for binding in manifest_bindings:
        path = bind(binding)
        m = read(path)
        if m.get('parser_module_sha256') != PARSER_SHA:
            raise ValueError('reuse parser differs')
        if 'preparer_sha256' not in m:
            prior_contract = read(bind(binding['execution_contract']))
            command = prior_contract['command']
            options = {key: command[command.index(key) + 1] for key in
                       ('--out', '--progress', '--plan', '--parser-sha256')}
            receipt = read(bind(binding['execution_receipt']))
            if (prior_contract['runner_sha256'] != PREPARER_SHA
                    or prior_contract['parser_sha256'] != PARSER_SHA
                    or prior_contract['progress_sha256'] != m['progress_sha256']
                    or command[:3] != ['python3', '-B', str(HERE / 'prepare_financial_documents.py')]
                    or Path(options['--out']) != path.parent
                    or options['--progress'] != m['progress_path']
                    or options['--plan'] != m['plan_path']
                    or options['--parser-sha256'] != PARSER_SHA
                    or receipt['execution']['command'] != command
                    or receipt['execution']['manifest_sha256'] != binding['sha256']
                    or receipt['contract_sha256'] != binding['execution_contract']['sha256']):
                raise ValueError('legacy preparation execution contract does not bind manifest')
        elif m['preparer_sha256'] != PREPARER_SHA:
            raise ValueError('reuse preparer differs')
        for record in m['documents']:
            bind(record)
            if record.get('notice_text'):
                bind(record['notice_text'])
            key = (record['cohort_code'], record['announcement_id'])
            if key in documents and documents[key]['sha256'] != record['sha256']:
                raise ValueError(f'conflicting prior prepared evidence: {key}')
            documents[key] = record
        for record in m.get('errors', []):
            if record.get('announcement_id') and record.get('source_sha256'):
                errors[(record['cohort_code'], record['announcement_id'])] = record
    return documents, errors


def run(contract_path):
    started = time.monotonic()
    contract_path = Path(contract_path).resolve()
    c = read(contract_path)
    if c.get('schema') != 'financial-document-batch/1' or c.get('workers') not in (1, 2, 3, 4):
        raise ValueError('invalid preparation contract')
    if c.get('runner_sha256') != sha(Path(__file__)):
        raise ValueError('batch runner fingerprint changed')
    required = {'progress', 'plan', 'cohort', 'parser', 'preparer'}
    if set(c['inputs']) != required:
        raise ValueError('contract input keys differ')
    paths = {key: bind(value) for key, value in c['inputs'].items()}
    if (sha(paths['cohort']) != COHORT_SHA or sha(paths['parser']) != PARSER_SHA
            or sha(paths['preparer']) != PREPARER_SHA
            or paths['parser'] != ROOT / 'src/lei_signal/research/profitability_discovery.py'):
        raise ValueError('frozen cohort or parser implementation changed')
    helper = load_preparer(paths['preparer'])
    cohort, plan, progress = read(paths['cohort']), read(paths['plan']), read(paths['progress'])
    if plan['cohort_sha256'] != COHORT_SHA or progress['schema'] != 'financial-filings-progress/1':
        raise ValueError('unexpected source identity')
    out = Path(c['output']).resolve()
    storage = helper._verify_external(paths['plan'], plan, out)
    old, old_errors = reusable_documents(c.get('reuse_manifests', []))
    out.mkdir(exist_ok=False)
    (out / 'documents').mkdir()
    (out / 'notice-text').mkdir()
    summary = {'schema': 'financial-document-preparation/1',
               'created_at': datetime.now(timezone.utc).isoformat(),
               'contract_path': str(contract_path), 'contract_sha256': sha(contract_path),
               'progress_path': str(paths['progress']), 'progress_sha256': sha(paths['progress']),
               'plan_path': str(paths['plan']), 'plan_sha256': sha(paths['plan']),
               'cohort_path': str(paths['cohort']), 'cohort_sha256': COHORT_SHA,
               'parser_module_path': str(paths['parser']), 'parser_module_sha256': PARSER_SHA,
               'preparer_path': str(paths['preparer']), 'preparer_sha256': PREPARER_SHA,
               'runner_sha256': sha(Path(__file__)), 'storage': storage,
               'reuse_manifests': c.get('reuse_manifests', []),
               'documents': [], 'errors': [], 'new_documents': 0, 'reused_documents': 0,
               'market_effects_run': False, 'version_chain_completeness_inferred': False}
    summary['unprepared_document_states'] = [
        {'publisher_code': code, **item}
        for code, state in progress['codes'].items() for item in state.get('pdfs', [])
        if item.get('status') not in ('obtained', 'reused')]
    summary['code_source_coverage'] = {
        code: {'status': state['status'], 'pdf_targets_expected': state.get('pdf_targets_expected'),
               'pdfs_unissued_count': state.get('pdfs_unissued_count'),
               'pdfs_not_started_reason': state.get('pdfs_not_started_reason'),
               'catalog_status': {k: v['status'] for k, v in state.get('catalogs', {}).items()}}
        for code, state in progress['codes'].items()}
    write(out / 'run-meta.json', summary)
    journal_path = out / 'prepared-journal.jsonl'
    journal_path.open('x').close()

    def checkpoint(kind, record):
        with journal_path.open('a') as stream:
            stream.write(json.dumps({'kind': kind, 'record': record}, ensure_ascii=False,
                                    allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    jobs, seen = [], set()
    for full_code, code, item, reason in helper._source_rows(progress, cohort, None):
        if item is None:
            error = {'cohort_code': full_code, 'publisher_code': code, 'reason': reason}
            summary['errors'].append(error)
            checkpoint('error', error)
            continue
        key = (full_code, str(item.get('announcement_id', '')))
        if key in seen:
            raise ValueError(f'duplicate expected document: {key}')
        seen.add(key)
        if key in old:
            record = old[key]
            entry = read(record['path'])
            source = entry['source']
            _, identity = helper._validate_source_pdf(item, code)
            if (source['source_identity'] != identity or source['title'] != item.get('announcement_title')
                    or source['announcement_time_ms'] != item.get('announcement_time_ms')
                    or set(source['categories']) != set(item.get('categories') or [])):
                raise ValueError(f'prior prepared evidence no longer matches expected source: {key}')
            summary['documents'].append(record)
            summary['reused_documents'] += 1
            checkpoint('reused_document', record)
        elif key in old_errors and old_errors[key]['source_sha256'] == item.get('sha256'):
            summary['errors'].append(old_errors[key])
            checkpoint('reused_error', old_errors[key])
        else:
            jobs.append((full_code, code, item, str(paths['preparer'])))
    with ProcessPoolExecutor(max_workers=c['workers'],
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        iterator = iter(jobs)
        pending = set()
        for _ in range(c['workers'] * 2):
            job = next(iterator, None)
            if job is not None:
                pending.add(pool.submit(prepare_one, job))

        def results():
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    pending.remove(future)
                    result = future.result()
                    # At most 2*workers submissions remain in flight/buffered.
                    job = next(iterator, None)
                    if job is not None:
                        pending.add(pool.submit(prepare_one, job))
                    yield result

        for result in results():
            if 'error' in result:
                summary['errors'].append(result['error'])
                checkpoint('error', result['error'])
                continue
            entry = result['entry']
            source, header = entry['source'], entry['header_evidence']
            stem = f"{source['publisher_code']}-{source['announcement_id']}"
            dest = out / 'documents' / f'{stem}.json'
            digest = write(dest, entry)
            notice_output = None
            if result['notice'] is not None:
                notice_path = out / 'notice-text' / f'{stem}.json'
                notice_digest = write(notice_path, result['notice'])
                notice_output = {'path': str(notice_path), 'sha256': notice_digest,
                                 'pages': len(result['notice'])}
            summary['documents'].append({
                'cohort_code': source['cohort_code'], 'publisher_code': source['publisher_code'],
                'announcement_id': source['announcement_id'], 'path': str(dest), 'sha256': digest,
                'notice_text': notice_output, 'document_form': header['document_form'],
                'identity_status': header['identity_status']})
            summary['new_documents'] += 1
            checkpoint('new_document', summary['documents'][-1])
    # Preserve all code and source failures; success count never means all 600 qualify.
    summary['source_code_counts'] = {status: sum(v['status'] == status for v in progress['codes'].values())
                                     for status in ('complete', 'incomplete', 'pending', 'running')}
    summary['elapsed_seconds'] = time.monotonic() - started
    summary['counts'] = {'documents_written_or_reused': len(summary['documents']),
                         'documents_or_codes_failed': len(summary['errors'])}
    manifest = out / 'manifest.json'
    digest = write(manifest, summary)
    print(json.dumps({'manifest_path': str(manifest), 'manifest_sha256': digest,
                      'new_documents': summary['new_documents'],
                      'reused_documents': summary['reused_documents'],
                      'errors': len(summary['errors']), 'elapsed_seconds': summary['elapsed_seconds']}))


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--contract', required=True, type=Path)
    run(cli.parse_args().contract)
