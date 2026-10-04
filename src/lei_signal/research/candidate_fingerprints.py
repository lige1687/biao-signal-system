"""Optional, conservative formula identity hints before candidate evaluation.

Uses the pinned FactorMiner parser/compiler. No labels, model calls, formula
execution, candidate deletion, or prior research-result reuse are performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

UPSTREAM_COMMIT = '75e056067a90ed6c4cf2e1737df773eed79abce8'
CONTEXT_FIELDS = frozenset({'data_sha256', 'universe', 'target', 'horizon',
                          'available_at', 'units', 'missing_policy',
                          'evaluation_protocol', 'baseline', 'evaluator'})
REQUIRED_FILES = frozenset({'factorminer/__init__.py', 'factorminer/_lazy_exports.py',
    'factorminer/core/__init__.py', 'factorminer/core/parser.py',
    'factorminer/core/types.py', 'factorminer/core/expression_tree.py',
    'factorminer/core/expression_plan.py'})


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _compiler(upstream, provenance):
    root = Path(upstream).resolve()
    spec = json.loads(Path(provenance).read_text())
    if spec.get('upstream_commit') != UPSTREAM_COMMIT:
        raise ValueError('Unreviewed upstream version')
    entries = spec.get('files', [])
    names = [item['path'] for item in entries]
    if len(names) != len(set(names)) or not REQUIRED_FILES <= set(names):
        raise ValueError('Incomplete or duplicate source bindings')
    for item in entries:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or Path(item['path']).is_absolute():
            raise ValueError('Source path outside pinned directory')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Source fingerprint differs')
    # Do not combine a pinned parser with already imported unpinned children.
    for name, module in tuple(sys.modules.items()):
        if name == 'factorminer' or name.startswith('factorminer.'):
            filename = getattr(module, '__file__', None)
            if filename is None or not Path(filename).resolve().is_relative_to(root):
                raise ValueError('Another FactorMiner implementation is loaded')
    sys.path.insert(0, str(root))
    from factorminer.core.parser import parse
    from factorminer.core.expression_plan import compile_tree
    return parse, compile_tree


def inspect_candidates(payload, *, upstream, provenance):
    """Preserve every proposal; mark exact repeated computation identities only.

    Context values are caller declarations, not independently qualified evidence.
    Equal identity does not authorize skipping a trial or transferring its score.
    """
    if not isinstance(payload, dict) or set(payload) != {'schema', 'candidates'} or payload['schema'] != 'candidate-fingerprints/1':
        raise ValueError('Expected candidate-fingerprints/1')
    rows = payload['candidates']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise ValueError('Expected 1 to 256 candidates per inspection')
    seen_ids = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'candidate_id', 'formula', 'context'}:
            raise ValueError('Exact candidate fields required')
        cid = row['candidate_id']
        if not isinstance(cid, str) or not cid.strip() or cid in seen_ids:
            raise ValueError('Nonempty unique candidate IDs required; preserve revisions')
        seen_ids.add(cid)
        ctx = row['context']
        if not isinstance(ctx, dict) or set(ctx) != CONTEXT_FIELDS or any(not isinstance(v, str) or not v.strip() for v in ctx.values()):
            raise ValueError('All ten context dimensions must be explicit strings')
        if len(ctx['data_sha256']) != 64 or any(c not in '0123456789abcdef' for c in ctx['data_sha256']):
            raise ValueError('Exact input SHA256 required')
        f = row['formula']
        if not isinstance(f, str) or not f.strip() or len(f) > 2048 or f.count('(') > 64:
            raise ValueError('Formula exceeds inspection limits or is empty')
    parse, compile_tree = _compiler(upstream, provenance)
    seen = {}; output = []
    for row in rows:
        item = {'candidate_id': row['candidate_id'], 'formula': row['formula'],
                'context_sha256': _hash(row['context'])}
        try:
            tree = parse(row['formula']); plan = compile_tree(tree)
        except (ValueError, TypeError, SyntaxError, KeyError, RecursionError) as exc:
            item.update(status='invalid_formula', error_type=type(exc).__name__, reason=str(exc))
        else:
            identity = _hash({'source_commit': UPSTREAM_COMMIT, 'source_bindings_sha256':
                             hashlib.sha256(Path(provenance).read_bytes()).hexdigest(),
                             'structure': plan.digest, 'context': row['context']})
            item.update(status='same_structure_and_context' if identity in seen else 'unreviewed_candidate',
                        duplicate_of=seen.get(identity), identity=identity,
                        structure_sha256=plan.digest, normalized_formula=plan.formula,
                        required_features=sorted(plan.required_features),
                        lookback=plan.max_lookback, cross_sectional=plan.cross_sectional)
            seen.setdefault(identity, row['candidate_id'])
        output.append(item)
    return {'schema': 'candidate-fingerprints-result/1', 'upstream_commit': UPSTREAM_COMMIT,
            'candidates': output, 'automatic_deletions': 0, 'financial_validity': 'not_evaluated',
            'limitations': ['Caller context has not been independently qualified',
                'Algebraic, correlated and complementary candidates require separate review',
                'Retain every attempted proposal; matching identity does not authorize score reuse']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True); p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--provenance', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): p.error('Output already exists; preserve evidence')
    result = inspect_candidates(json.loads(a.input.read_text()), upstream=a.upstream, provenance=a.provenance)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create also protects against a concurrent writer.
    with a.output.open('x') as f: f.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'candidates': len(result['candidates']), 'automatic_deletions': 0}))


if __name__ == '__main__': main()
