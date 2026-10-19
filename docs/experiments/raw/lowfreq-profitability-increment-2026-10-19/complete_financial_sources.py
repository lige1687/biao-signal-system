#!/usr/bin/env python3
"""Plan bounded, never-started source completion; execution requires frozen contract.

``--plan --snapshot SNAPSHOT.json`` prints a proposal and makes no writes or HTTP.
Snapshot schema ``financial-completion-snapshot/1`` binds plan, cohort, progress,
origin_manifest, acquirer, storage_plan as {path,sha256}, plus ordered ``journals``
bindings (origin journal first, then any prior completion stages). After the
original run ends, save stdout as a frozen plan. ``--execute --contract`` requires
schema ``financial-completion-contract/1`` containing that exact snapshot, a
bound plan {path,sha256}, an approved finite request_budget equal to the plan's
operation count, ``execution_authorized: true``, and a fresh external output
directory. No implied authorization follows from a plan alone.

Catalog waves request only currently determinable unissued pages. If page 1
reveals more pages, freeze a new snapshot and new finite contract. PDF planning
waits until no permitted catalog page remains, then uses only issuers whose
two catalogs are complete. Other issuers remain explicitly unknown. Started-but-unfinished
and failed operations remain blocked forever. The merged progress stays in a
new output directory; no original source/journal is changed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
UUID = 'DEBA1C85-6059-3865-B50A-A8EE1F80E4D9'
DEVICE = 16777238
RESERVE = 10 * 1024**3


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1 << 20), b''):
            digest.update(part)
    return digest.hexdigest()


def bound(binding):
    path = Path(binding['path'])
    if not path.is_absolute() or not path.is_file() or sha(path) != binding['sha256']:
        raise ValueError(f'missing or changed snapshot source: {path}')
    return path


def read(binding):
    return json.loads(bound(binding).read_text(encoding='utf-8'))


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    return sha(path)


def original_acquirer(binding):
    path = bound(binding)
    spec = importlib.util.spec_from_file_location('frozen_financial_acquirer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def journal_starts(bindings):
    starts, finished = {}, set()
    counts = {'catalog': 0, 'pdf': 0, 'total': 0}
    consecutive_failures, terminal_stop = 0, None
    for binding in bindings:
        with bound(binding).open(encoding='utf-8') as stream:
            for line in stream:
                item = json.loads(line)
                op = item['op_id']
                if item['event'] == 'start':
                    if op in starts:
                        raise ValueError(f'operation already started in another stage: {op}')
                    starts[op] = item
                    counts[item['kind']] += 1; counts['total'] += 1
                elif item['event'] == 'finish':
                    if op in finished:
                        raise ValueError(f'duplicate operation finish: {op}')
                    finished.add(op)
                    consecutive_failures = 0 if item.get('successful') else consecutive_failures + 1
                    if item.get('status') == 429:
                        terminal_stop = 'prior_http_429'
                    elif consecutive_failures >= 2:
                        terminal_stop = 'prior_two_consecutive_external_failures'
    if not finished <= set(starts):
        raise ValueError('finish without start')
    return starts, finished, counts, consecutive_failures, terminal_stop


def snapshot_data(snapshot):
    if snapshot.get('schema') != 'financial-completion-snapshot/1':
        raise ValueError('snapshot schema mismatch')
    inputs = snapshot['inputs']
    if set(inputs) != {'plan', 'cohort', 'progress', 'origin_manifest', 'acquirer', 'storage_plan'}:
        raise ValueError('snapshot input bindings incomplete')
    journals = snapshot['journals']
    if not journals:
        raise ValueError('origin journal is required')
    origin, progress = read(inputs['origin_manifest']), read(inputs['progress'])
    plan, cohort, storage = read(inputs['plan']), read(inputs['cohort']), read(inputs['storage_plan'])
    acquirer = original_acquirer(inputs['acquirer'])
    if (plan.get('schema') != 'financial-filings-acquisition/1' or
            progress.get('schema') != 'financial-filings-progress/1' or
            origin.get('schema') != 'financial-filings-bulk-result/1' or
            plan['cohort_sha256'] != inputs['cohort']['sha256'] or
            origin['plan_sha256'] != inputs['plan']['sha256'] or
            origin['cohort_sha256'] != inputs['cohort']['sha256'] or
            origin['storage_plan_sha256'] != inputs['storage_plan']['sha256'] or
            origin['script_sha256'] != inputs['acquirer']['sha256'] or
            origin['journal_sha256_at_manifest'] != journals[0]['sha256'] or
            Path(origin['journal_path']) != Path(journals[0]['path']) or
            plan['max_pages_per_query'] != 30 or plan['page_size'] != 30 or
            plan['http_concurrency'] != 4 or plan['retries'] != 0 or
            plan['global_min_start_interval_seconds'] != .5 or
            plan['per_operation_timeout_seconds'] != 40 or
            plan['max_bytes_pdf_each'] != 30000000):
        raise ValueError('frozen acquisition lineage or limits differ')
    codes = cohort['fixed_codes']
    if len(codes) != 600 or len(set(codes)) != 600:
        raise ValueError('fixed cohort not 600 unique codes')
    publisher_codes = [code.split('.')[1] for code in codes]
    if set(progress['codes']) != set(publisher_codes):
        raise ValueError('progress not exact 600')
    starts, finished, counts, tail_failures, terminal_stop = journal_starts(journals)
    if progress.get('operations') != counts:
        raise ValueError('progress operation counts do not match bound journals')
    if len(journals) == 1:
        if origin['codes'] != progress['codes'] or origin['actual_http_starts'] != counts:
            raise ValueError('original run not frozen at final manifest')
    else:
        lineage = progress.get('completion_lineage', {})
        if lineage.get('origin_manifest_sha256') != inputs['origin_manifest']['sha256'] or \
                lineage.get('journal_sha256s') != [x['sha256'] for x in journals]:
            raise ValueError('merged progress lacks exact stage lineage')
    # Reuse the frozen URL and annual/correction target rules, not a second filter.
    return {'plan': plan, 'cohort': cohort, 'progress': progress, 'storage': storage,
            'acquirer': acquirer, 'starts': starts, 'finished': finished, 'counts': counts,
            'tail_failures': tail_failures, 'terminal_stop': terminal_stop}


def propose(snapshot):
    context = snapshot_data(snapshot)
    plan, progress, starts, acquirer = (context[k] for k in ('plan', 'progress', 'starts', 'acquirer'))
    operations, blocked = [], []
    codes = [code.split('.')[1] for code in context['cohort']['fixed_codes']]
    all_catalogs_complete = all(
        all(str(progress['codes'][code].get('catalogs', {}).get(category, {}).get('status', '')).startswith('complete')
            for category in ('annual', 'correction')) for code in codes)
    stage = 'pdf' if all_catalogs_complete else 'catalog'
    if context.get('terminal_stop'):
        return {'schema': 'financial-completion-plan/1', 'stage': stage,
                'snapshot_sha256': hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                'operations': [], 'operation_count': 0,
                'blocked': [{'reason': context['terminal_stop']}],
                'prior_http_starts': context['counts'], 'max_pages_per_code_category': 30,
                'catalog_page1_reveals_later_pages_only_in_new_snapshot': True,
                'no_http_from_plan': True}
    mapping = acquirer._index_mapping(plan)
    if stage == 'catalog':
        for code in codes:
            for category in ('annual', 'correction'):
                cat = progress['codes'][code].get('catalogs', {}).get(category, {})
                if str(cat.get('status', '')).startswith('complete'):
                    continue
                expected = cat.get('expected_pages')
                pages = range(1, min(int(expected), 30) + 1) if expected is not None else range(1, 2)
                saved_pages = {int(x['page']) for x in cat.get('pages', [])}
                for page in pages:
                    op_id = f'catalog:{code}:{category}:{page}'
                    if op_id in starts:
                        if page not in saved_pages:
                            blocked.append({'op_id': op_id, 'reason': 'already_started_never_retry'})
                        continue
                    if page in saved_pages:
                        raise ValueError(f'saved catalog page has no durable start: {op_id}')
                    payload = acquirer._payload(code, mapping.get(code), plan['categories'][category],
                                                plan['query_date_range'], page)
                    operations.append({'op_id': op_id, 'kind': 'catalog', 'code': code,
                                       'category': category, 'page': page, 'method': 'POST',
                                       'url': plan['endpoint'], 'data': payload})
    if not operations:
        stage = 'pdf'
        for code in codes:
            state = progress['codes'][code]
            if not all(str(state.get('catalogs', {}).get(k, {}).get('status', '')).startswith('complete')
                       for k in ('annual', 'correction')):
                blocked.append({'code': code, 'reason': 'catalog_incomplete_no_permitted_page_remaining'})
                continue
            targets = acquirer._targets(state['catalogs'], set(plan['annual_report_years']))
            saved = {str(x['announcement_id']): x for x in state.get('pdfs', [])}
            for target in targets:
                aid = target['announcement_id']
                op_id = f'pdf:{code}:{aid}'
                if aid in saved and saved[aid].get('status') in ('obtained', 'reused'):
                    continue
                if op_id in starts:
                    blocked.append({'op_id': op_id, 'reason': 'already_started_never_retry'})
                elif not target.get('pdf_url'):
                    blocked.append({'op_id': op_id, 'reason': 'actual_adjunct_url_missing_or_invalid'})
                else:
                    operations.append({'op_id': op_id, 'kind': 'pdf', 'code': code,
                                       'announcement_id': aid, 'method': 'GET',
                                       'url': target['pdf_url'], 'target': target})
    operations.sort(key=lambda x: x['op_id'])
    return {'schema': 'financial-completion-plan/1', 'stage': stage,
            'snapshot_sha256': hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            'operations': operations, 'operation_count': len(operations), 'blocked': blocked,
            'prior_http_starts': context['counts'], 'max_pages_per_code_category': 30,
            'catalog_page1_reveals_later_pages_only_in_new_snapshot': True,
            'no_http_from_plan': True}


def external_guard(out, storage, origin_output):
    mount = Path(storage['external_mount'])
    if (not out.is_absolute() or out.exists() or out.parent != Path(origin_output) or
            not mount.is_mount() or mount.stat().st_dev != DEVICE or
            out.parent.stat().st_dev != DEVICE or
            storage['external_device'] != DEVICE or storage['external_uuid'] != UUID or
            shutil.disk_usage(mount).free < RESERVE):
        raise ValueError('new external output path/device/capacity invalid')
    info = plistlib.loads(subprocess.run(['diskutil', 'info', '-plist', str(mount)],
                                     capture_output=True, check=True, timeout=10).stdout)
    if info.get('VolumeUUID') != UUID:
        raise ValueError('external volume UUID changed')


def rebuild_catalogs(progress, operations, responses, acquirer, plan):
    for task in operations:
        if task['kind'] != 'catalog':
            continue
        code, category = task['code'], task['category']
        state = progress['codes'][code]
        cat = state.setdefault('catalogs', {}).setdefault(category, {})
        record = responses.get(task['op_id'], {})
        if not record.get('successful'):
            cat['status'] = 'incomplete'; cat['reason'] = record.get('error', 'unissued')
            continue
        raw = json.loads(Path(record['body_path']).read_text(encoding='utf-8'))
        count, announcements = raw.get('totalAnnouncement'), raw.get('announcements')
        if str(count).isdigit():
            count = int(count)
        else:
            cat['status'] = 'incomplete'; cat['reason'] = 'catalog_schema_missing_total'; continue
        if count == 0 and announcements is None:
            announcements = []
        if not isinstance(announcements, list) or count == 0 and announcements:
            cat['status'] = 'incomplete'; cat['reason'] = 'catalog_schema_invalid'; continue
        if cat.get('totalAnnouncement') not in (None, count):
            cat['status'] = 'incomplete'; cat['reason'] = 'catalog_total_changed_between_pages'; continue
        cat['totalAnnouncement'] = count
        cat['expected_pages'] = max(1, math.ceil(count / plan['page_size']))
        pages = {int(x['page']): x for x in cat.get('pages', [])}
        pages[task['page']] = {'page': task['page'], 'raw_path': record['body_path'],
                               'sha256': record['sha256'], 'returned': len(announcements),
                               'exact_code': sum(str(x.get('secCode')) == code for x in announcements),
                               'wrong_code': sum(str(x.get('secCode')) != code for x in announcements)}
        cat['pages'] = [pages[n] for n in sorted(pages)]
        all_items = []
        for page in cat['pages']:
            body = Path(page['raw_path'])
            if sha(body) != page['sha256']:
                raise ValueError('saved catalog body changed during merge')
            doc = json.loads(body.read_text(encoding='utf-8'))
            listed = doc.get('announcements')
            if count == 0 and listed is None:
                listed = []
            if (not isinstance(listed, list) or int(doc.get('totalAnnouncement', -1)) != count or
                    page['page'] < cat['expected_pages'] and not listed):
                cat['status'] = 'incomplete'; cat['reason'] = 'saved_catalog_page_schema_or_total_conflict'
                break
            all_items.extend(x for x in listed if str(x.get('secCode')) == code)
        cat['exact_announcements'] = all_items
        cat['pages_read'] = len(cat['pages'])
        if cat.get('reason') != 'saved_catalog_page_schema_or_total_conflict':
            cat['status'] = ('complete_empty' if count == 0 else 'complete') if \
                set(pages) == set(range(1, cat['expected_pages'] + 1)) else 'incomplete'
            cat['reason'] = None if cat['status'].startswith('complete') else 'unread_pages_after_bounded_wave'


def merge_progress(context, plan_result, responses, journal_binding):
    progress = copy.deepcopy(context['progress'])
    operations = plan_result['operations']
    rebuild_catalogs(progress, operations, responses, context['acquirer'], context['plan'])
    for task in operations:
        if task['kind'] != 'pdf':
            continue
        state = progress['codes'][task['code']]
        row = dict(task['target'])
        response = responses.get(task['op_id'], {})
        row.update({'status': 'obtained' if response.get('successful') else 'incomplete',
                    'reason': response.get('error', 'unissued'), 'source_path': response.get('body_path'),
                    'bytes': response.get('bytes'), 'sha256': response.get('sha256')})
        existing = [x for x in state.get('pdfs', [])
                    if str(x.get('announcement_id')) != task['announcement_id']]
        state['pdfs'] = existing + [row]
    for code, state in progress['codes'].items():
        catalogs = state.get('catalogs', {})
        complete = all(str(catalogs.get(k, {}).get('status', '')).startswith('complete')
                       for k in ('annual', 'correction'))
        if complete:
            targets = context['acquirer']._targets(catalogs, set(context['plan']['annual_report_years']))
            finished = {(x['code'], str(x['announcement_id'])) for x in state.get('pdfs', [])
                        if x.get('status') in ('obtained', 'reused')}
            state['pdf_targets_expected'] = len(targets)
            state['pdfs_unissued_count'] = len(targets) - len(finished)
            state['status'] = 'complete' if not state['pdfs_unissued_count'] else 'incomplete'
        else:
            state['status'] = 'incomplete'
    counts = dict(context['counts'])
    _, _, stage_counts, _, _ = journal_starts([journal_binding])
    progress['operations'] = {key: counts[key] + stage_counts[key] for key in counts}
    progress['global_stop'] = any(not x.get('successful') for x in responses.values())
    progress['updated_utc'] = datetime.now(timezone.utc).isoformat()
    return progress


def execute(contract_path):
    contract = json.loads(Path(contract_path).read_text(encoding='utf-8'))
    if contract.get('schema') != 'financial-completion-contract/1' or contract.get('execution_authorized') is not True:
        raise ValueError('explicit execution contract required')
    if contract.get('runner_sha256') != sha(__file__):
        raise ValueError('runner changed after approval')
    snapshot = contract['snapshot']
    plan_binding = contract['plan']
    proposal = read(plan_binding)
    recomputed = propose(snapshot)
    if proposal != recomputed or proposal['stage'] != contract.get('stage'):
        raise ValueError('stage plan differs from frozen snapshot')
    tasks = proposal['operations']
    if not tasks or contract.get('request_budget') != len(tasks) or contract['request_budget'] > 14000:
        raise ValueError('explicit finite stage budget must equal exact unissued tasks')
    context = snapshot_data(snapshot)
    origin_output = context['plan']['output']
    out = Path(contract['output']).resolve()
    external_guard(out, context['storage'], origin_output)
    # Recheck the originating run is not still writing, independent of hashes.
    with bound(snapshot['journals'][0]).open('r') as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('original acquisition still active') from exc
        # Hold the common originating-run lock throughout the whole stage,
        # preventing a second stage or original resume from issuing the same op.
        try:
            return execute_locked(contract_path, contract, snapshot, plan_binding,
                                  proposal, tasks, context, out)
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def execute_locked(contract_path, contract, snapshot, plan_binding, proposal, tasks, context, out):
    out.mkdir(mode=0o700)
    (out / 'raw').mkdir()
    (out / 'journal.jsonl').open('x').close()
    write_new(out / 'run-meta.json', {'contract_path': str(contract_path),
              'contract_sha256': sha(contract_path), 'plan_sha256': plan_binding['sha256'],
              'stage': proposal['stage'], 'prior_http_starts': context['counts'],
              'request_budget': len(tasks), 'market_effects_run': False})
    acquisition_plan = dict(context['plan'])
    acquisition_plan['max_catalog_requests'] = len(tasks) if proposal['stage'] == 'catalog' else 0
    acquisition_plan['max_pdf_requests'] = len(tasks) if proposal['stage'] == 'pdf' else 0
    acquisition_plan['max_total_http_operations'] = len(tasks)
    controller = context['acquirer'].Controller(acquisition_plan, out, [], resume=False)
    controller.consecutive_failures = context['tail_failures']
    responses = {}
    def request(task):
        mount = Path(context['storage']['external_mount'])
        if (not mount.is_mount() or mount.stat().st_dev != DEVICE or
                out.stat().st_dev != DEVICE or shutil.disk_usage(mount).free < RESERVE):
            controller.stop.set()
            raise ValueError('registered external device/capacity changed before request')
        return controller.request(task['op_id'], task['kind'], task['method'], task['url'],
                                  data=task.get('data'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {pool.submit(request, task): task for task in tasks}
        for future in as_completed(future_map):
            task = future_map[future]
            try:
                responses[task['op_id']] = future.result()
            except Exception as exc:
                controller.stop.set()
                responses[task['op_id']] = {'event': 'worker_error', 'error': f'{type(exc).__name__}:{exc}',
                                           'successful': False}
    new_journal = {'path': str(out / 'journal.jsonl'), 'sha256': sha(out / 'journal.jsonl')}
    merged = merge_progress(context, proposal, responses, new_journal)
    merged['completion_lineage'] = {'origin_manifest_sha256': snapshot['inputs']['origin_manifest']['sha256'],
        'journal_sha256s': [x['sha256'] for x in snapshot['journals']] + [new_journal['sha256']],
        'prior_progress_sha256': snapshot['inputs']['progress']['sha256'],
        'stage_plan_sha256': plan_binding['sha256']}
    progress_hash = write_new(out / 'progress.json', merged)
    manifest = {'schema': 'financial-completion-result/1', 'stage': proposal['stage'],
                'contract_path': str(contract_path), 'contract_sha256': sha(contract_path),
                'input_bindings': snapshot, 'plan_binding': plan_binding,
                'prior_http_starts': context['counts'],
                'new_http_starts': journal_starts([new_journal])[2],
                'cumulative_http_starts': merged['operations'],
                'new_journal': new_journal, 'merged_progress': {'path': str(out / 'progress.json'),
                                                               'sha256': progress_hash},
                'unissued_or_blocked': proposal['blocked'] + [task['op_id'] for task in tasks
                                                               if not responses[task['op_id']].get('successful')],
                'all_600_complete': all(x['status'] == 'complete' for x in merged['codes'].values()),
                'market_effects_run': False}
    manifest_hash = write_new(out / 'manifest.json', manifest)
    return {'manifest_path': str(out / 'manifest.json'), 'manifest_sha256': manifest_hash,
            'merged_progress_sha256': progress_hash, 'stage': proposal['stage'],
            'new_http_starts': manifest['new_http_starts'], 'all_600_complete': manifest['all_600_complete']}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    group = cli.add_mutually_exclusive_group()
    group.add_argument('--plan', action='store_true')
    group.add_argument('--execute', action='store_true')
    cli.add_argument('--snapshot', type=Path)
    cli.add_argument('--contract', type=Path)
    args = cli.parse_args()
    if not args.execute:
        if not args.snapshot:
            cli.error('--snapshot is required for --plan')
        print(json.dumps(propose(json.loads(args.snapshot.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))
    else:
        if not args.contract:
            cli.error('--contract is required for --execute')
        print(json.dumps(execute(args.contract), ensure_ascii=False))
