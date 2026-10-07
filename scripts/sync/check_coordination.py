#!/usr/bin/env python3
"""Read-only LEI coordination preflight. No locks, scheduling, or research execution.

Online mode always fetches the one authorized coordination branch. Local-file mode
is only for document/tests preparation and never proves an online work clearance.
Only explicit `lei-coordination-json` blocks are machine-checked; legacy Markdown
remains human review material. Declarations do not grant authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

BLOCK = re.compile(r'^```lei-coordination-json\s*\n(.*?)\n```\s*$', re.M | re.S)
ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
SHA = re.compile(r'^[0-9a-f]{40}$')
STATES = {'planned', 'active', 'blocked', 'paused', 'completed', 'archived'}
REMOTE = 'refs/remotes/origin/coordination/lei'


def git(repo: Path, *args: str) -> str:
    p = subprocess.run(['git', '-C', str(repo), *args], text=True,
                       capture_output=True, timeout=45)
    if p.returncode:
        # Avoid exposing remote URL credentials or verbose authentication output.
        raise RuntimeError(f'git {args[0]} failed (exit {p.returncode}); no online clearance')
    return p.stdout


def valid_path(path: object) -> bool:
    if not isinstance(path, str) or not path or '\\' in path:
        return False
    p = PurePosixPath(path)
    return (not p.is_absolute() and path not in {'.', './'}
            and all(x not in {'', '.', '..'} for x in path.rstrip('/').split('/'))
            and not any(x in path for x in '*?['))


def covers(scope: str, path: str) -> bool:
    return path == scope or (scope.endswith('/') and path.startswith(scope))


def overlap(a: str, b: str) -> bool:
    return covers(a, b) or covers(b, a)


def validate(documents: dict[str, str], task_id: str | None = None,
             owner: str | None = None, writes: list[str] | None = None) -> dict:
    errors: list[str] = []
    legacy: list[str] = []
    claims: dict[str, dict] = {}
    record_ids: set[str] = set()
    for name, text in sorted(documents.items()):
        blocks = BLOCK.findall(text)
        if not blocks:
            legacy.append(name)
            continue
        if len(blocks) != 1:
            errors.append(f'{name}: expected one machine-readable block')
            continue
        try:
            record = json.loads(blocks[0])
            if not isinstance(record, dict) or record.get('schema_version') != 1:
                raise ValueError('unsupported block schema')
            rid = record.get('record_id')
            if rid != Path(name).stem or not ID.fullmatch(str(rid)):
                raise ValueError('record_id must match filename')
            if rid in record_ids:
                raise ValueError('duplicate record_id')
            record_ids.add(rid)
            if not SHA.fullmatch(str(record.get('checked_coordination_sha'))):
                raise ValueError('missing full checked_coordination_sha')
            if not isinstance(record.get('assignments'), list):
                raise ValueError('assignments must be a list')
            for entry in record['assignments']:
                if not isinstance(entry, dict):
                    raise ValueError('assignment must be an object')
                tid = entry.get('task_id')
                if not ID.fullmatch(str(tid)) or not isinstance(entry.get('owner'), str) or not entry['owner']:
                    raise ValueError('invalid task_id or missing owner')
                if tid in claims:
                    errors.append(f'duplicate task_id: {tid}')
                    continue
                if entry.get('status') not in STATES:
                    raise ValueError(f'{tid}: invalid status')
                for field in ('write_paths', 'depends_on'):
                    values = entry.get(field)
                    if not isinstance(values, list) or not all(isinstance(x, str) for x in values):
                        raise ValueError(f'{tid}: {field} must be a string list')
                if not all(valid_path(p) for p in entry['write_paths']):
                    raise ValueError(f'{tid}: unsafe or ambiguous write path')
                claims[tid] = {**entry, 'record': name}
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f'{name}: {exc}')
    for tid, entry in claims.items():
        for dep in entry['depends_on']:
            if dep not in claims:
                errors.append(f'{tid}: unknown dependency {dep}')
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(tid: str) -> None:
        if tid in visiting:
            errors.append(f'dependency cycle at {tid}')
            return
        if tid in visited:
            return
        visiting.add(tid)
        for dep in claims[tid]['depends_on']:
            if dep in claims:
                visit(dep)
        visiting.remove(tid)
        visited.add(tid)

    for tid in claims:
        visit(tid)
    items = list(claims.items())
    for i, (left_id, left) in enumerate(items):
        # Age, blocked status and completion do not release write scopes. Release
        # must be explicit and reviewed by the responsible coordinator.
        if left.get('scope_released') is True:
            continue
        for right_id, right in items[i + 1:]:
            if right.get('scope_released') is True:
                continue
            for a in left['write_paths']:
                for b in right['write_paths']:
                    if overlap(a, b):
                        errors.append(f'write overlap: {left_id} and {right_id}: {a} / {b}')
    if writes and not task_id:
        errors.append('write query requires a registered task_id and owner')
    if task_id:
        current = claims.get(task_id)
        if not current:
            errors.append(f'unregistered task_id: {task_id}; human review required')
        elif not owner or owner != current['owner']:
            errors.append(f'{task_id}: queried owner differs from registered owner')
        elif current.get('scope_released') is True:
            errors.append(f'{task_id}: scope was released; register new scope first')
        else:
            for path in writes or []:
                if not valid_path(path) or not any(covers(p, path) for p in current['write_paths']):
                    errors.append(f'{task_id}: write not registered: {path}')
    return {'declared_checks_passed': not errors, 'errors': errors,
            'legacy_records_require_human_review': legacy,
            'declared_task_ids': sorted(claims),
            'scope': 'explicit declarations only; no lock, authorization, or legacy clearance'}


def load_online(repo: Path) -> tuple[str, dict[str, str], str]:
    url = git(repo, 'remote', 'get-url', 'origin').strip()
    if url not in {'git@github.com:lige1687/biao-signal-system.git',
                   'https://github.com/lige1687/biao-signal-system.git',
                   'https://github.com/lige1687/biao-signal-system'}:
        raise RuntimeError('origin is not the authorized LEI repository')
    git(repo, 'fetch', 'origin', 'refs/heads/coordination/lei:' + REMOTE)
    sha = git(repo, 'rev-parse', REMOTE).strip()
    rules = git(repo, 'show', f'{sha}:COORDINATION.md')
    paths = git(repo, 'ls-tree', '-r', '--name-only', sha, 'docs/coordination/tasks').splitlines()
    docs = {p: git(repo, 'show', f'{sha}:{p}') for p in paths if p.endswith('.md')}
    return sha, docs, rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--local-tasks-dir', type=Path, help='offline drafting/tests only')
    parser.add_argument('--task-id')
    parser.add_argument('--owner', help='registered visible conversation id')
    parser.add_argument('--write-path', action='append', default=[])
    args = parser.parse_args(argv)
    report = {'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
              'online_verified': False, 'work_clearance': False}
    try:
        if args.local_tasks_dir:
            docs = {p.name: p.read_text() for p in args.local_tasks_dir.glob('*.md')}
            report['mode'] = 'offline_draft_only'
        else:
            sha, docs, rules = load_online(args.repo.resolve())
            report.update(online_verified=True, checked_coordination_sha=sha,
                          rules_present=bool(rules), mode='online_declarations_only')
        report.update(validate(docs, args.task_id, args.owner, args.write_path))
        # No automatic work permission, even on exit 0. Legacy records and
        # scientific duplication must still be read and reviewed by the actor.
        code = 0 if report['declared_checks_passed'] else 2
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        report.update(errors=[str(exc)], declared_checks_passed=False)
        code = 3
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
