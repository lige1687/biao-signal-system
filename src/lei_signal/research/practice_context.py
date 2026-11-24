"""Bounded, read-only historical declarations for research preparation.

Matches invite source review; they never reject a proposal or authorize a rerun.
The existing attempt review remains the journal/source identity implementation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import attempt_review

REGISTRY = 'docs/experiments/registry.json'
MAX_LIMIT = 20
MAX_QUERIES = 20
MAX_REGISTRY_ENTRIES = 2000
MAX_VALUE_CHARS = 12000
MAX_DECLARATIONS = 80
MAX_DECLARATION_CHARS = 64000
# Exact field names only: no interpretation of words in conclusions or statuses.
FIELDS = {
    'conclusions': {'conclusion', 'conclusions', 'judgment', 'verdict', 'decision',
                    'scientific_effect_status', 'evidence_status', 'effect_status',
                    'final_conclusion', 'research_decision', 'finding', 'findings'},
    'decision_use': {'decision_use', 'use', 'uses', 'intended_use', 'applicable_use',
                     'applicable_uses', 'not_applicable_uses'},
    'objects': {'scope', 'objects', 'object_refs', 'definition_refs', 'definition_ref',
                'definition', 'symbols', 'universe', 'market', 'period'},
    'blockers': {'blockers', 'blocker', 'blocked_reason', 'blocking_conditions',
                 'missing_inputs', 'missing_definition', 'blocked', 'blocking_reason'},
    'reopen_conditions': {'reopen', 'reopen_conditions', 'reopening_conditions',
                         'reopen_condition', 'resume_conditions', 'resume_condition',
                         'recovery_conditions', 'restart_conditions', 'reopen_when',
                         'what_would_change_decision', 'reopening_criteria'},
    'execution_status': {'status', 'execution_status', 'run_status', 'mode', 'stop_reason'},
    'report_references': {'report', 'report_reference', 'report_delivery', 'registered_report'},
    'seen_history': {'results_seen', 'case_selection', 'all_history_previously_seen',
                     'seen_history', 'seen_history_declaration', 'validation_stage'},
}


def _bounded(value):
    encoded = json.dumps(value, ensure_ascii=False)
    if len(encoded) > MAX_VALUE_CHARS:
        return {'status': 'truncated_value', 'preview': encoded[:MAX_VALUE_CHARS],
                'original_characters': len(encoded)}
    return value


def _pointer(parts):
    return '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def _declarations(root, reviewed):
    found = {name: [] for name in FIELDS}
    truncated = False
    declaration_chars = 0
    declaration_count = 0
    for binding in reviewed['files']:
        if binding['status'] != 'read':
            continue
        expected = list if Path(binding['path']).name == 'attempts.json' else dict
        source, obj = attempt_review._json(root, binding['path'], expected)
        if obj is None:
            continue
        # Fields extracted after a concurrent edit must not inherit the old SHA.
        if source['sha256'] != binding['sha256']:
            truncated = True
            continue
        stack = [((), obj)]
        visited = 0
        while stack:
            parts, node = stack.pop()
            visited += 1
            if visited > 5000:
                truncated = True
                break
            if isinstance(node, dict):
                for key, value in node.items():
                    for group, names in FIELDS.items():
                        if key in names:
                            if declaration_count >= MAX_DECLARATIONS:
                                truncated = True
                                continue
                            bounded = _bounded(value)
                            truncated |= bounded != value
                            declaration = {'value': bounded, 'source': source,
                                           'field': _pointer((*parts, key))}
                            size = len(json.dumps(declaration, ensure_ascii=False))
                            if declaration_chars + size > MAX_DECLARATION_CHARS:
                                truncated = True
                                continue
                            declaration_chars += size
                            declaration_count += 1
                            found[group].append(declaration)
                    # Containers representing a declaration are kept whole. Descend
                    # only for other fields, avoiding duplicate nested judgments.
                    if not any(key in names for names in FIELDS.values()):
                        stack.append(((*parts, key), value))
            elif isinstance(node, list):
                stack.extend(((*parts, i), value) for i, value in enumerate(node[:500]))
                truncated |= len(node) > 500
    return {key: values or 'unknown' for key, values in found.items()}, truncated


def build_history_context(root, *, terms=(), family=None, studies=(), limit=6) -> dict:
    """Return source-bound declarations, never an economic verdict or permission.

    Search covers existing family ledgers and report registry metadata only.
    Only explicit study paths and registry raw_directory links expose named JSONs.
    Report bodies, output directories and external paths are never followed.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('root must be a directory')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f'limit must be between 1 and {MAX_LIMIT}')
    if isinstance(terms, str) or isinstance(studies, str):
        raise ValueError('terms and studies must be sequences, not strings')
    terms, studies = tuple(terms), tuple(studies)
    if len(terms) > MAX_QUERIES or len(studies) > MAX_QUERIES:
        raise ValueError(f'at most {MAX_QUERIES} terms or studies')
    if any(not isinstance(t, str) or not t.strip() or len(t) > 200 for t in terms):
        raise ValueError('terms must be nonblank strings of at most 200 characters')
    if not terms and not family and not studies:
        raise ValueError('provide terms, family or studies')
    matched, errors, ledger_paths = [], [], set()
    search = {'scope': ['family_journals', REGISTRY, 'explicit_or_registered_study_named_json'],
              'report_body_followed': False, 'output_followed': False,
              'registry_source': {'path': REGISTRY, 'status': 'not_requested'},
              'matches_truncated': False, 'registry_candidates_truncated': False,
              'declarations_truncated': False,
              'no_match_meaning': 'no_match_in_bounded_sources_not_no_prior_research'}

    def add(item):
        if len(matched) < limit:
            matched.append(item)
        else:
            search['matches_truncated'] = True

    seen_studies = set()

    def add_study(path, report='unknown'):
        if path in seen_studies:
            return
        seen_studies.add(path)
        # Once display is full, do not read more study files.
        if len(matched) >= limit:
            search['matches_truncated'] = True
            return
        try:
            reviewed = attempt_review.review(root, studies=[path])['studies'][0]
            declared, truncated = _declarations(root, reviewed)
            if report == 'unknown' and reviewed['report_reference'] == 'unknown':
                refs = declared['report_references']
                if isinstance(refs, list):
                    report = refs[0]['value']
            search['declarations_truncated'] |= truncated
            add({'kind': 'study', 'path': path, 'declared': declared,
                 'report_reference': (report if report != 'unknown'
                                      else reviewed['report_reference']),
                 'assessment': 'declarations_only_manual_review',
                 'review': _bounded(reviewed)})
        except (ValueError, OSError) as exc:
            errors.append({'path': str(path), 'status': 'unsafe_path' if isinstance(exc, ValueError)
                           else 'read_error', 'error': str(exc)})

    for path in studies:
        add_study(path)
    queries = [{'family': family}] if family else []
    queries += [{'term': term} for term in dict.fromkeys(terms)]
    for query in queries:
        try:
            review = attempt_review.review(root, **query)
            errors.extend(review['errors'])
            for ledger in review['ledgers']:
                path = ledger['source']['path']
                if path in ledger_paths:
                    continue
                ledger_paths.add(path)
                declared = {name: 'unknown' for name in FIELDS}
                declared['seen_history'] = [{'value': ledger['seen_history'],
                                             'source': ledger['source'],
                                             'field': 'results_seen in indexed journal events'}]
                add({'kind': 'ledger', 'path': path, 'declared': declared,
                     'report_reference': 'unknown', 'review': _bounded(ledger),
                     'assessment': 'declarations_only_manual_review'})
        except (ValueError, OSError) as exc:
            errors.append({'status': 'journal_read_error', 'error': str(exc)})
    if terms or family:
        try:
            source, registry = attempt_review._json(root, REGISTRY)
            search['registry_source'] = source
            entries = registry.get('entries', {}) if registry else {}
            if not isinstance(entries, dict):
                errors.append({'path': REGISTRY, 'status': 'invalid_registry_entries'})
                entries = {}
            search['registry_entries'] = len(entries)
            search['registry_candidates_truncated'] = len(entries) > MAX_REGISTRY_ENTRIES
            needles = [t.casefold() for t in terms] + ([family.casefold()] if family else [])
            for i, (report, metadata) in enumerate(entries.items()):
                if i >= MAX_REGISTRY_ENTRIES:
                    break
                if not isinstance(metadata, dict):
                    continue
                text = json.dumps([report, metadata], ensure_ascii=False).casefold()
                if not any(term in text for term in needles):
                    continue
                path = metadata.get('raw_directory')
                if isinstance(path, str):
                    add_study(path, report)
                add({'kind': 'report_metadata', 'path': report, 'report_reference': report,
                     'metadata': _bounded(metadata), 'source': source,
                     'field': _pointer(('entries', report)),
                     'declared': {name: 'unknown' for name in FIELDS},
                     'assessment': 'metadata_match_manual_review_required'})
        except (ValueError, OSError) as exc:
            errors.append({'path': REGISTRY, 'status': 'registry_read_error', 'error': str(exc)})
    return {'schema': 'research-practice-history/1', 'read_only': True,
            'query': {'terms': list(terms), 'family': family,
                      'studies': list(studies), 'limit': limit},
            'matched': matched, 'search': search, 'errors': errors,
            'boundaries': {'scientific_validation': 'not_tested', 'automatic_rejection': False,
                           'automatic_execution': False, 'unfreeze_authorized': False,
                           'history_reset': False,
                           'declarations_may_be_corrected': True,
                           'unknown_is_not_ineffective': True}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(attempt_review.ROOT))
    parser.add_argument('--term', action='append', default=[])
    parser.add_argument('--family')
    parser.add_argument('--study', action='append', default=[])
    parser.add_argument('--limit', type=int, default=6)
    args = parser.parse_args(argv)
    print(json.dumps(build_history_context(args.root, terms=args.term, family=args.family,
                                          studies=args.study, limit=args.limit),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
