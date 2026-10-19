#!/usr/bin/env python3
"""Offline, create-only as-known financial panel; never reads outcome columns.

Contract JSON schema ``financial-panel-run/1``::
  {"inputs": {name: {"path": absolute_path, "sha256": lowercase_sha256}},
   "output": {"path": new_directory_under_registered_external_result,
              "mount": "/Volumes/win+mac通用", "external_device": 16777238,
              "external_uuid": "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"}}

Required input names: plan, progress, preparation (one or more bound manifests),
design, version_rules, controller_review, industry_receipt, cohort, price_calendar,
parser, runner. Optional ``notice_review`` is an *approved* JSON document with
reviewer, exact code/ID/source_sha256, affected_years/fields, continuing_scope,
and quote/page evidence matching the bound saved notice text. Unapproved proposals
have no effect. All path/hash bindings and output device are checked before writing.
"""
from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
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
UUID = 'DEBA1C85-6059-3865-B50A-A8EE1F80E4D9'
DEVICE = 16777238
RESERVE = 10 * 1024**3
ANNUAL = re.compile(r'(?<!\d)(20\d{2})\s*年?\s*(?:年度报告|年报)')
# Frozen acquisition scope, acquire_financial_filings.py::EXCLUDE_ANNUAL.
EXCLUDE_ANNUAL = ('摘要', '英文', '审计', '意见', '问询')
INDUSTRY = re.compile(r'^([A-Z]\d{2})')
FIELDS = ('assets', 'revenue', 'cost', 'cfo')
DEPENDENCIES = {'gp': ('assets', 'revenue', 'cost'), 'cfo': ('assets', 'cfo')}
PANEL_COLUMNS = ('month', 'decision_date', 'code', 'industry', 'gp_status', 'gpa',
                 'cfo_status', 'cfoa', 'report_year', 'announcement_id',
                 'publication_date', 'reason')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1 << 20), b''):
            h.update(part)
    return h.hexdigest()


def read_bound(binding):
    path = Path(binding['path'])
    if not path.is_absolute() or not path.is_file() or sha(path) != binding['sha256']:
        raise ValueError(f'bound input absent or changed: {path}')
    return path


def json_bound(binding):
    return json.loads(read_bound(binding).read_text(encoding='utf-8'))


def public_day(milliseconds):
    if milliseconds is None:
        return None
    try:
        return datetime.fromtimestamp(int(milliseconds) / 1000, timezone.utc).astimezone(
            ZoneInfo('Asia/Shanghai')).date().isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def annual_year(title):
    title = str(title or '')
    if excluded_doc_kind(title) or re.search(r'半年度|季度|季报|中期', title):
        return None
    match = ANNUAL.search(title)
    return int(match.group(1)) if match else None


def excluded_doc_kind(title):
    title = str(title or '')
    return next((term for term in EXCLUDE_ANNUAL if term in title), None)


def ambiguous_annual_title(title):
    title = str(title or '')
    return (not excluded_doc_kind(title) and bool(re.search(r'年度报告|年报', title)) and
            annual_year(title) is None and
            not re.search(r'摘要|半年度|季度|季报|中期|公告|通知|说明', title))


def is_notice_title(title):
    return bool(re.search(r'公告|通知|说明', str(title or '')) and
                re.search(r'更正|补充', str(title or '')))


def expected_index(progress, codes):
    """Catalog is the authority; PDF and prepared documents only enrich it."""
    records = {}
    for code in codes:
        publisher = code.split('.')[1]
        state = progress.get('codes', {}).get(publisher, {})
        for category in ('annual', 'correction'):
            cat = state.get('catalogs', {}).get(category, {})
            for ann in cat.get('exact_announcements', []):
                aid = str(ann.get('announcementId') or '')
                if not aid or str(ann.get('secCode')) != publisher:
                    continue
                key = (code, aid)
                title = ann.get('announcementTitle') or ''
                row = records.setdefault(key, {'code': code, 'id': aid, 'title': title,
                                               'publication_date': public_day(ann.get('announcementTime')),
                                               'year': annual_year(title), 'categories': set(),
                                               'excluded_doc_kind': excluded_doc_kind(title),
                                               'pdf': None, 'prepared': None})
                if row['title'] != title or row['publication_date'] != public_day(ann.get('announcementTime')):
                    raise ValueError(f'catalog identity collision: {key}')
                row['categories'].add(category)
        for pdf in state.get('pdfs', []):
            key = (code, str(pdf.get('announcement_id') or ''))
            if key in records:
                records[key]['pdf'] = pdf
    return records


def catalog_coverage(progress, codes):
    """Each code needs both finite catalogs, independent of its PDF failures."""
    result = {}
    for code in codes:
        catalogs = progress.get('codes', {}).get(code.split('.')[1], {}).get('catalogs', {})
        result[code] = {category: str(catalogs.get(category, {}).get('status') or '')
                        for category in ('annual', 'correction')}
    return result


def merge_preparation(records, manifests):
    for manifest in manifests:
        if manifest.get('schema') != 'financial-document-preparation/1':
            raise ValueError('preparation schema changed')
        for item in manifest.get('documents', []):
            key = (item['cohort_code'], str(item['announcement_id']))
            if key not in records:
                raise ValueError(f'prepared document outside expected catalog: {key}')
            path = read_bound(item)
            prepared = json.loads(path.read_text(encoding='utf-8'))
            source = prepared['source']
            if (source['cohort_code'], str(source['announcement_id'])) != key:
                raise ValueError(f'prepared identity mismatch: {key}')
            if (source['publisher_code'] != key[0].split('.')[1]
                    or source['announcement_date_asia_shanghai'] != records[key]['publication_date']
                    or (records[key]['year'] is not None and
                        source['report_year_from_title'] != records[key]['year'])):
                raise ValueError(f'prepared publisher/date/year differs from expected catalog: {key}')
            expected_hash = (records[key]['pdf'] or {}).get('sha256')
            if expected_hash != source['source_identity']['sha256']:
                raise ValueError(f'prepared source hash mismatch: {key}')
            previous = records[key]['prepared']
            if previous is not None and previous != prepared:
                raise ValueError(f'conflicting prepared documents: {key}')
            records[key]['prepared'] = prepared
            records[key]['prepared_binding'] = item


def full_candidate(record):
    if record.get('excluded_doc_kind') or excluded_doc_kind(record['title']):
        return False
    prepared = record['prepared']
    if prepared:
        form = prepared.get('header_evidence', {}).get('document_form')
        candidate = prepared.get('annual_candidate_evidence', {})
        if form == 'notice':
            return False
        if form == 'suspected_full_text' or candidate.get('status') == 'suspected':
            return record['year'] is not None
    return record['year'] is not None and not is_notice_title(record['title'])


def source_fields(record):
    prepared = record['prepared'] or {}
    header = prepared.get('header_evidence', {})
    parsed = prepared.get('financial_parser_result') or {}
    if not prepared:
        return {}, 'source_not_prepared'
    if header.get('identity_status') != 'match':
        return {}, 'identity_not_verified'
    if header.get('document_form') != 'suspected_full_text':
        return {}, 'full_annual_not_verified'
    if parsed.get('report_year') != record['year'] or parsed.get('publication_date') != record['publication_date']:
        return {}, 'parser_period_or_publication_mismatch'
    result = {}
    for name in FIELDS:
        field = parsed.get('fields', {}).get(name, {})
        if field.get('status') != 'qualified' or field.get('value_yuan') is None:
            continue
        try:
            value = Decimal(str(field['value_yuan']))
        except InvalidOperation:
            continue
        if not value.is_finite() or name == 'assets' and value <= 0:
            continue
        result[name] = value
    return result, None


def _reviewed_notice(review, record):
    if not review or review.get('schema') != 'financial-notice-review/1' or not review.get('reviewer'):
        return None
    matches = [x for x in review.get('decisions', []) if
               x.get('cohort_code') == record['code'] and str(x.get('announcement_id')) == record['id']]
    if len(matches) > 1:
        raise ValueError('duplicate reviewed notice')
    if not matches:
        return None
    decision = matches[0]
    if decision.get('controller_accepted') is not True:
        return None
    if decision.get('publication_date') != record['publication_date']:
        raise ValueError('review publication date mismatch')
    source_hash = (record['pdf'] or {}).get('sha256')
    if decision.get('source_sha256') != source_hash:
        raise ValueError('review source hash mismatch')
    notice = (record.get('prepared_binding') or {}).get('notice_text')
    if (not notice or decision.get('notice_text_sha256') != notice['sha256'] or
            decision.get('notice_text_path') != notice['path']):
        raise ValueError('review text hash mismatch')
    if decision.get('disposition') not in {'cleared', 'unrelated_business',
                                           'financial_correction', 'unresolved'}:
        raise ValueError('review disposition invalid')
    if decision.get('continuing_scope') not in {'cleared', 'extends', 'unknown'}:
        raise ValueError('review continuing scope invalid')
    years, fields = decision.get('affected_years'), decision.get('affected_fields')
    if years is not None and (not isinstance(years, list) or not years or
                              any(not isinstance(y, int) for y in years)):
        raise ValueError('review affected years invalid')
    if fields is not None and (not isinstance(fields, list) or not fields or
                               any(f not in FIELDS for f in fields)):
        raise ValueError('review affected fields invalid')
    pages = json.loads(read_bound(notice).read_text(encoding='utf-8'))
    evidence = decision.get('evidence') or []
    if not evidence:
        raise ValueError('review without page quote')
    for item in evidence:
        page = item.get('page')
        quote = item.get('exact_quote')
        if not isinstance(page, int) or page < 1 or page > len(pages) or not quote or quote not in pages[page-1]['text']:
            raise ValueError('review quote/page mismatch')
    return decision


def events_for(records, controller, review):
    business = {(x['cohort_code'], str(x['announcement_id'])) for x in controller.get('decisions', [])
                if x.get('controller_decision') == 'accept_explicit_business_scope_for_this_document_only'}
    events = defaultdict(list)
    for key, record in records.items():
        form = (record['prepared'] or {}).get('header_evidence', {}).get('document_form')
        ambiguous = 'annual' in record['categories'] and ambiguous_annual_title(record['title'])
        annual_notice = 'annual' in record['categories'] and form == 'notice'
        if (key in business or full_candidate(record) or
                not ('correction' in record['categories'] or ambiguous or annual_notice)):
            continue
        approved = _reviewed_notice(review, record)
        events[record['code']].append({'record': record, 'review': approved,
                                       'ambiguous_annual': ambiguous})
    return events


def event_applies(event, report_year, feature, source, allow_measurement_recovery=False):
    if event.get('ambiguous_annual'):
        return True, 'ambiguous_new_annual_year_or_identity'
    review = event['review']
    if not review:
        event_day = event['record'].get('publication_date')
        if (allow_measurement_recovery and event_day and source and
                f'{report_year}-12-31' > event_day and source['publication_date'] > event_day):
            return False, 'measurement_recovered_with_unreviewed_prior_notice'
        return True, 'unreviewed_notice'
    if review.get('disposition') == 'unrelated_business' or (review.get('disposition') == 'cleared' and
                                                              review.get('whole_notice_cleared') is True):
        return False, 'whole_notice_cleared'
    years = review.get('affected_years')
    fields = review.get('affected_fields')
    if fields is not None and not set(fields) & set(DEPENDENCIES[feature]):
        return False, 'known_scope_irrelevant'
    if source and set(source.get('announcement_ids', [])) & set(map(str, review.get('resolved_by_announcement_ids', []))):
        return False, 'explicit_full_version_resolution'
    if years is not None and report_year in years:
        return True, 'affected_year_field_unresolved'
    if years is not None and report_year < min(years):
        return False, 'known_scope_irrelevant'
    if years is not None and review.get('continuing_scope') == 'cleared':
        return False, 'known_scope_irrelevant'
    if years is None and review.get('continuing_scope') == 'cleared' and source:
        fiscal_end = date(report_year, 12, 31)
        event_day = date.fromisoformat(event['record']['publication_date'])
        full_day = date.fromisoformat(source['publication_date'])
        if fiscal_end > event_day and full_day > event_day:
            return False, 'new_period_current_statement_supersedes_unscoped_prior_uncertainty'
    return True, 'continuing_scope_unknown_or_extends'


def select_feature(records, events, code, decision, feature, coverage=None,
                   allow_measurement_recovery=False):
    if coverage is not None and not all(str(coverage.get(code, {}).get(category, '')).startswith('complete')
                                    for category in ('annual', 'correction')):
        return {'status': 'unknown', 'reason': 'source_catalog_incomplete',
                'catalog_status': coverage.get(code, {})}
    if (any(c == code and full_candidate(r) and not r['publication_date']
            for (c, _), r in records.items()) or
            any(not e['record']['publication_date'] for e in events.get(code, []))):
        return {'status': 'unknown', 'reason': 'source_publication_date_unknown'}
    candidates = [r for (c, _), r in records.items() if c == code and full_candidate(r)
                  and r['publication_date'] and r['publication_date'] < decision]
    if not candidates:
        return {'status': 'unknown', 'reason': 'no_public_full_annual'}
    year = max(r['year'] for r in candidates)
    latest = max(r['publication_date'] for r in candidates if r['year'] == year)
    current = [r for r in candidates if r['year'] == year and r['publication_date'] == latest]
    selected_ids = sorted(r['id'] for r in current)
    source = {'report_year': year, 'publication_date': latest,
              'announcement_ids': selected_ids}
    decision_day = date.fromisoformat(decision)
    expiry_month = 12 + 16
    expiry_year = year + (expiry_month - 1) // 12
    expiry_month = (expiry_month - 1) % 12 + 1
    expiry = date(expiry_year, expiry_month, calendar.monthrange(expiry_year, expiry_month)[1])
    if decision_day > expiry:
        return {'status': 'unknown', 'reason': 'annual_older_than_16_months', **source}
    values = [source_fields(r) for r in current]
    needed = DEPENDENCIES[feature]
    if any(reason or not all(field in amounts for field in needed) for amounts, reason in values):
        failures = []
        for record, (amounts, reason) in zip(current, values):
            parser_fields = ((record['prepared'] or {}).get('financial_parser_result') or {}).get('fields', {})
            failures.append({'announcement_id': record['id'], 'source_reason': reason,
                             'missing_fields': [field for field in needed if field not in amounts],
                             'field_reasons': {field: parser_fields.get(field, {}).get('reason')
                                               for field in needed if field not in amounts}})
        return {'status': 'unknown', 'reason': 'latest_full_annual_field_or_identity_unknown',
                'source_failures': failures, **source}
    if any(any(amounts[f] != values[0][0][f] for f in needed) for amounts, _ in values[1:]):
        return {'status': 'unknown', 'reason': 'same_day_dependent_amount_conflict', **source}
    blockers = []
    recovery = []
    for event in events.get(code, []):
        record = event['record']
        if record['publication_date'] and record['publication_date'] < decision:
            applies, reason = event_applies(event, year, feature, source, allow_measurement_recovery)
            detail = {'announcement_id': record['id'], 'publication_date': record['publication_date'],
                      'reason': reason}
            if applies:
                blockers.append(detail)
            elif reason.startswith(('new_period_', 'measurement_recovered_')):
                if reason.startswith('measurement_recovered_'):
                    detail.update(notice_review_status='unreviewed', continuing_scope='unknown',
                                  source_status=(record.get('pdf') or {}).get('status'),
                                  annual_publication_date=source['publication_date'],
                                  annual_fiscal_end=f'{year}-12-31',
                                  annual_announcement_ids=source['announcement_ids'],
                                  financial_authenticity_certified=False)
                recovery.append(detail)
    if blockers:
        return {'status': 'unknown', 'reason': 'applicable_notice_unresolved',
                'blockers': blockers, 'recovery_evidence': recovery, **source}
    amounts = values[0][0]
    ratio = ((amounts['revenue'] - amounts['cost']) / amounts['assets'] if feature == 'gp'
             else amounts['cfo'] / amounts['assets'])
    return {'status': 'qualified', 'value': str(ratio), 'reason': None,
            'amounts_yuan': {k: str(amounts[k]) for k in needed},
            'recovery_evidence': recovery, **source}


def industry_index(receipt):
    if receipt.get('execution', {}).get('successful_requests') != 12 or len(receipt.get('raw_files', [])) != 12:
        raise ValueError('historical industry receipt is not the frozen 12 snapshots')
    snapshots = []
    for bound in receipt.get('raw_files', []):
        raw = json.loads(read_bound(bound).read_text(encoding='utf-8'))
        query = raw['request']['kwargs']['date']
        fields = raw['fields']
        rows = {}
        for values in raw['rows']:
            item = dict(zip(fields, values))
            code = item['code']
            if code in rows:
                raise ValueError(f'duplicate industry source code: {query} {code}')
            rows[code] = item
        snapshots.append((query, rows, bound))
    if len({s[0] for s in snapshots}) != 12:
        raise ValueError('duplicate industry query dates')
    return sorted(snapshots)


def select_industry(snapshots, code, decision):
    available = [s for s in snapshots if s[0] <= decision]
    if not available:
        return 'unknown', 'no_snapshot_at_decision', None
    query, rows, bound = available[-1]
    row = rows.get(code)
    if row is None:
        return 'unknown', 'missing_in_snapshot', {'query': query, 'sha256': bound['sha256']}
    meta = {'query': query, 'sha256': bound['sha256'], 'update_date': row.get('updateDate')}
    if not row.get('updateDate') or row['updateDate'] >= decision:
        return 'unknown', 'industry_update_not_prior', meta
    match = INDUSTRY.match(row.get('industry') or '')
    if row.get('industryClassification') != '证监会行业分类' or not match:
        return 'unknown', 'industry_classification_unknown', meta
    label = match.group(1)
    return label, 'financial_industry_excluded' if label.startswith('J') else None, meta


def calendar_rows(path, codes):
    # Read only the three positionally selected fields. No future outcome value
    # enters a dict, diagnostic, or output, even when present in the source CSV.
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        if len(header) != len(set(header)) or not {'month', 'decision_date', 'code'} <= set(header):
            raise ValueError('saved price calendar lacks key columns')
        indices = {key: header.index(key) for key in ('month', 'decision_date', 'code')}
        seen, dates = set(), {}
        for raw in reader:
            if len(raw) != len(header):
                raise ValueError('price calendar row width changed')
            row = {k: raw[i] for k, i in indices.items()}
            key = (row['month'], row['code'])
            if key in seen or row['code'] not in codes:
                raise ValueError(f'duplicate or out-of-cohort price calendar key: {key}')
            seen.add(key)
            date.fromisoformat(row['decision_date'])
            if row['month'] in dates and dates[row['month']] != row['decision_date']:
                raise ValueError('mixed decision dates within month')
            dates[row['month']] = row['decision_date']
            yield row


def build_rows(calendar, codes, records, events, snapshots, coverage=None,
               allow_measurement_recovery=False):
    rows, audit, queue = [], [], Counter()
    by_code = defaultdict(dict)
    for key, record in records.items():
        by_code[key[0]][key] = record
    for key in calendar:
        month, decision, code = key['month'], key['decision_date'], key['code']
        industry, industry_reason, industry_source = select_industry(snapshots, code, decision)
        gp = select_feature(by_code[code], events, code, decision, 'gp', coverage, allow_measurement_recovery)
        cfo = select_feature(by_code[code], events, code, decision, 'cfo', coverage, allow_measurement_recovery)
        ids = sorted(set(gp.get('announcement_ids', []) + cfo.get('announcement_ids', [])))
        years = {x.get('report_year') for x in (gp, cfo) if x.get('report_year')}
        pubs = {x.get('publication_date') for x in (gp, cfo) if x.get('publication_date')}
        reasons = [x for x in (industry_reason, gp.get('reason'), cfo.get('reason')) if x]
        rows.append({'month': month, 'decision_date': decision, 'code': code,
                     'industry': industry, 'gp_status': gp['status'], 'gpa': gp.get('value', ''),
                     'cfo_status': cfo['status'], 'cfoa': cfo.get('value', ''),
                     'report_year': str(max(years)) if years else '',
                     'announcement_id': '|'.join(ids), 'publication_date': max(pubs) if pubs else '',
                     'reason': '|'.join(dict.fromkeys(reasons))})
        audit.append({'month': month, 'decision_date': decision, 'code': code,
                      'industry_source': industry_source, 'industry_reason': industry_reason,
                      'gp': gp, 'cfo': cfo})
        for feature, result in (('gp', gp), ('cfo', cfo)):
            for blocker in result.get('blockers', []):
                queue[(code, blocker['announcement_id'], feature)] += 1
    if len(rows) != 600 * 132 or len({(r['month'], r['code']) for r in rows}) != len(rows):
        raise ValueError('price calendar is not exact 600 x 132')
    months = []
    for month in sorted({r['month'] for r in rows}):
        subset = [r for r in rows if r['month'] == month]
        months.append({'month': month, 'all_600': len(subset),
                       'annual_source_seen': sum(bool(r['report_year']) for r in subset),
                       'industry_known': sum(r['industry'] != 'unknown' for r in subset),
                       'industry_nonfinancial': sum(r['industry'] != 'unknown' and not r['industry'].startswith('J') for r in subset),
                       'gp_qualified': sum(r['gp_status'] == 'qualified' for r in subset),
                       'cfo_qualified': sum(r['cfo_status'] == 'qualified' for r in subset),
                       'common_pool': sum(r['industry'] != 'unknown' and not r['industry'].startswith('J') and
                                          r['gp_status'] == r['cfo_status'] == 'qualified' for r in subset),
                       'unknown_reasons': dict(Counter(reason for r in subset for reason in r['reason'].split('|') if reason))})
    review_queue = []
    for (c, aid, f), n in queue.items():
        record = records[(c, aid)]
        review_queue.append({'code': c, 'announcement_id': aid, 'feature': f,
                             'blocked_stock_months': n, 'publication_date': record['publication_date'],
                             'title': record['title'], 'source_sha256': (record['pdf'] or {}).get('sha256'),
                             'source_status': (record['pdf'] or {}).get('status', 'unissued')})
    review_queue.sort(key=lambda x: (-x['blocked_stock_months'], x['code'], x['announcement_id'], x['feature']))
    return rows, audit, months, review_queue


def output_guard(spec, plan):
    output = spec['output']
    path, mount = Path(output['path']), Path(output['mount'])
    if (not path.is_absolute() or path.exists() or path.parent != Path(plan['output']) or
            not mount.is_mount() or output['external_device'] != DEVICE or
            output['external_uuid'] != UUID or mount.stat().st_dev != DEVICE or
            path.parent.stat().st_dev != DEVICE or shutil.disk_usage(mount).free < RESERVE):
        raise ValueError('create-only external device/capacity guard failed')
    info = plistlib.loads(subprocess.run(['/usr/sbin/diskutil', 'info', '-plist', str(mount)],
                                   capture_output=True, check=True, timeout=10).stdout)
    if info.get('VolumeUUID') != UUID:
        raise ValueError('external UUID mismatch')
    return path


def run(contract):
    spec = json.loads(contract.read_text(encoding='utf-8'))
    if spec.get('schema') != 'financial-panel-run/1':
        raise ValueError('contract schema mismatch')
    bound = spec['inputs']
    required = {'plan', 'progress', 'preparation', 'design', 'version_rules',
                'controller_review', 'industry_receipt', 'cohort', 'price_calendar',
                'parser', 'runner'}
    if not required <= set(bound):
        raise ValueError(f'input bindings missing: {sorted(required - set(bound))}')
    if Path(bound['runner']['path']).resolve() != Path(__file__).resolve():
        raise ValueError('runner path does not bind this code')
    for name in required - {'preparation'}:
        read_bound(bound[name])
    plan, progress = json_bound(bound['plan']), json_bound(bound['progress'])
    design, rules = json_bound(bound['design']), json_bound(bound['version_rules'])
    measurement_recovery = rules.get('unreviewed_prior_notice_measurement_recovery', False)
    if measurement_recovery:
        if 'qualification_amendment' not in bound:
            raise ValueError('measurement recovery requires explicitly bound amendment')
        amendment = json_bound(bound['qualification_amendment'])
        if (amendment.get('root_accepted') is not True or amendment.get('effect_runs_before') != 0 or
                amendment.get('new_rules_sha256') != bound['version_rules']['sha256'] or
                amendment.get('design_sha256') != bound['design']['sha256']):
            raise ValueError('measurement recovery amendment binding invalid')
    cohort, industry = json_bound(bound['cohort']), json_bound(bound['industry_receipt'])
    controller = json_bound(bound['controller_review'])
    review = json_bound(bound['notice_review']) if 'notice_review' in bound else None
    manifests = [json_bound(x) for x in (bound['preparation'] if isinstance(bound['preparation'], list) else [bound['preparation']])]
    for manifest in manifests:
        for metadata, name in (('parser_module_sha256', 'parser'),
                               ('cohort_sha256', 'cohort'), ('plan_sha256', 'plan')):
            if manifest.get(metadata) != bound[name]['sha256']:
                raise ValueError(f'preparation {metadata} differs from current bound input')
    if rules['design_sha256'] != bound['design']['sha256'] or plan['cohort_sha256'] != bound['cohort']['sha256']:
        raise ValueError('design/cohort chain changed')
    codes = cohort['fixed_codes']
    if len(codes) != 600 or len(set(codes)) != 600 or design['reuse']['monthly_decisions'] != 132:
        raise ValueError('frozen cohort/design count changed')
    expected_price = Path(cohort['price_quality_path']).parent / 'per_stock_month.csv'
    if Path(bound['price_calendar']['path']).resolve() != expected_price.resolve():
        raise ValueError('price calendar is not saved core-v1')
    records = expected_index(progress, codes)
    merge_preparation(records, manifests)
    events = events_for(records, controller, review)
    coverage = catalog_coverage(progress, codes)
    snapshots = industry_index(industry)
    rows, audit, monthly, queue = build_rows(calendar_rows(read_bound(bound['price_calendar']), set(codes)),
                                             codes, records, events, snapshots, coverage, measurement_recovery)
    out = output_guard(spec, plan)
    out.mkdir(mode=0o700)
    if out.stat().st_dev != DEVICE:
        raise ValueError('new directory device changed')
    with (out / 'panel.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, PANEL_COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    for name, payload in [('audit.json', audit), ('monthly-coverage.json', monthly),
                          ('notice-review-queue.json', queue),
                          ('expected-source-index.json', [{**{k: v for k, v in r.items() if k not in ('prepared', 'pdf', 'prepared_binding', 'categories')},
                                                           'categories': sorted(r['categories']), 'pdf': r['pdf'],
                                                           'prepared_binding': r.get('prepared_binding')} for r in records.values()])]:
        with (out / name).open('x', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, default=str)
            stream.write('\n')
    manifest = {'schema': 'financial-panel-result/1', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'contract_path': str(contract), 'contract_sha256': sha(contract),
                'inputs': bound, 'rows': len(rows), 'months': len(monthly),
                'expected_documents': len(records), 'unresolved_notice_queue': len(queue),
                'qualification_policy': rules['schema'],
                'unreviewed_prior_notice_measurement_recovery': measurement_recovery,
                'market_effects_run': False,
                'outputs': {name: sha(out / name) for name in ('panel.csv', 'audit.json',
                     'monthly-coverage.json', 'notice-review-queue.json', 'expected-source-index.json')}}
    with (out / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2); stream.write('\n')
    return manifest


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--contract', type=Path)
    cli.add_argument('--self-test', action='store_true')
    args = cli.parse_args()
    if args.self_test:
        import unittest
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.discover(str(HERE), pattern='test_financial_panel.py'))
        sys.exit(0 if result.wasSuccessful() else 1)
    if not args.contract:
        cli.error('--contract required unless --self-test')
    print(json.dumps(run(args.contract), ensure_ascii=False))
