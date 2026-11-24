import hashlib
import json

import pytest

from lei_signal.research import attempt_review


def build(*args, **kwargs):
    from lei_signal.research.practice_context import build_history_context
    return build_history_context(*args, **kwargs)


def put(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False))
    return target


def study(root, name='old'):
    path = f'docs/experiments/raw/{name}'
    put(root, f'{path}/contract.json', {
        'history': {'family': 'momentum'}, 'scope': {'symbols': ['SPY']},
        'decision_use': 'monthly allocation', 'case_selection': 'already seen',
        'question': {'text': 'increment?', 'validation': {'stage': 'historical'}},
    })
    put(root, f'{path}/checkpoint.json', {
        'status': 'completed', 'results_seen': True,
        'conclusion': {'judgment': 'no_increment_for_use', 'use': 'monthly allocation'},
        'reopen_conditions': ['new independent observations'],
    })
    return path


def test_declared_negative_and_reopen_remain_bound_to_original_fields(tmp_path):
    path = study(tmp_path)
    result = build(tmp_path, studies=[path])
    item = result['matched'][0]
    assert item['declared']['conclusions'][0]['value']['judgment'] == 'no_increment_for_use'
    ref = item['declared']['reopen_conditions'][0]
    assert ref['field'] == '/reopen_conditions'
    assert ref['source']['path'] == f'{path}/checkpoint.json'
    expected_sha = hashlib.sha256((tmp_path / ref['source']['path']).read_bytes()).hexdigest()
    assert ref['source']['sha256'] == expected_sha
    assert item['declared']['seen_history'] != 'unknown'
    assert result['boundaries']['history_reset'] is False


def test_blocked_and_execution_are_not_economic_failure(tmp_path):
    path = study(tmp_path)
    put(tmp_path, f'{path}/checkpoint.json', {
        'status': 'blocked', 'blocked_reason': 'historical membership missing',
        'scientific_effect_status': 'not_evaluated',
    })
    item = build(tmp_path, studies=[path])['matched'][0]
    assert item['declared']['conclusions'][0]['value'] == 'not_evaluated'
    assert item['declared']['blockers'][0]['value'] == 'historical membership missing'
    assert item['declared']['execution_status'][0]['value'] == 'blocked'
    assert item['assessment'] == 'declarations_only_manual_review'


def test_metadata_discovery_follows_only_registered_study_and_keeps_report(tmp_path):
    path = study(tmp_path)
    report = 'docs/experiments/old.md'
    put(tmp_path, 'docs/experiments/registry.json', {'entries': {report: {
        'oneLiner': 'momentum old negative evidence', 'verdict': 'falsified',
        'raw_directory': path,
    }}})
    result = build(tmp_path, terms=['momentum'])
    items = result['matched']
    assert any(x['kind'] == 'study' and x['report_reference'] == report for x in items)
    assert any(x['kind'] == 'report_metadata' for x in items)
    assert result['boundaries']['automatic_rejection'] is False
    assert result['search']['report_body_followed'] is False


def test_no_hit_is_not_no_prior_research(tmp_path):
    result = build(tmp_path, terms=['unknown'])
    assert result['matched'] == []
    assert result['search']['no_match_meaning'] == (
        'no_match_in_bounded_sources_not_no_prior_research'
    )
    assert result['search']['registry_source']['status'] == 'missing'


def test_missing_truncated_and_escaping_studies_visible(tmp_path, monkeypatch):
    path = study(tmp_path)
    monkeypatch.setattr(attempt_review, 'MAX_BYTES', 30)
    result = build(tmp_path, studies=[path, 'absent', '../escape'])
    assert any(
        x['status'] == 'truncated_size_limit'
        for x in result['matched'][0]['review']['files']
    )
    assert result['matched'][1]['declared']['conclusions'] == 'unknown'
    assert any(x['status'] == 'unsafe_path' for x in result['errors'])


def test_source_read_is_bounded_read_only_and_does_not_follow_out(tmp_path):
    path = study(tmp_path)
    put(tmp_path, f'{path}/manifest.json', {'out': '/outside/do-not-read', 'status': 'read_only'})
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = build(tmp_path, studies=[path])
    after = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert before == after
    assert result['read_only'] is True
    assert result['boundaries']['scientific_validation'] == 'not_tested'
    assert any(
        x['value'] == 'read_only'
        for x in result['matched'][0]['declared']['execution_status']
    )


def test_limits_and_symlink_escape(tmp_path):
    for n in range(3):
        study(tmp_path, str(n))
    result = build(tmp_path, studies=[f'docs/experiments/raw/{n}' for n in range(3)], limit=1)
    assert len(result['matched']) == 1
    assert result['search']['matches_truncated'] is True
    with pytest.raises(ValueError):
        build(tmp_path, terms=['x'], limit=100000)
    (tmp_path / 'escape').symlink_to(tmp_path.parent, target_is_directory=True)
    result = build(tmp_path, studies=['escape'])
    assert result['errors'][0]['status'] == 'unsafe_path'


def test_ledger_preserves_seen_history_and_execution(tmp_path):
    ledger = tmp_path / attempt_review._family_path('momentum')
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\n'.join(json.dumps(x) for x in [
        {'event': 'family', 'family': 'momentum', 'budget': {}},
        {'event': 'start', 'run_id': 'r', 'classification': 'historical', 'results_seen': True},
        {'event': 'finish', 'run_id': 'r', 'status': 'failed'},
    ]))
    result = build(tmp_path, family='momentum')
    item = result['matched'][0]
    assert item['review']['seen_history'] == 'yes'
    assert item['declared']['conclusions'] == 'unknown'
    assert item['review']['runs'][0]['status'] == 'failed'


def test_real_research_checkpoint_shape_preserves_nested_delivery_and_report(tmp_path):
    # Matches the existing research-closure resume checkpoint, not an inferred
    # conclusion extracted from a report sentence.
    path = 'docs/experiments/raw/resume'
    put(tmp_path, f'{path}/checkpoint.json', {
        'execution_status': 'paused', 'verdict': 'not_evaluated',
        'stop_reason': 'runtime_interrupted',
        'contract': {'decision_use': 'bounded arithmetic', 'scope': 'synthetic only'},
        'delivery': {'research_decision': 'save partial evidence',
                     'unknown': 'independent future validation'},
        'report_delivery': 'outputs/final_report.md',
        'resume_conditions': ['overall weighting remains unchecked'],
    })
    item = build(tmp_path, studies=[path])['matched'][0]
    declarations = item['declared']
    assert any(x['field'] == '/delivery/research_decision' for x in declarations['conclusions'])
    assert any(x['value'] == 'runtime_interrupted' for x in declarations['execution_status'])
    assert item['report_reference'] == 'outputs/final_report.md'
    assert declarations['report_references'][0]['field'] == '/report_delivery'


def test_registry_outside_study_is_reported_without_reading(tmp_path):
    put(tmp_path, 'docs/experiments/registry.json', {'entries': {
        'docs/experiments/a.md': {'oneLiner': 'momentum', 'raw_directory': '../outside'},
    }})
    result = build(tmp_path, terms=['momentum'])
    assert result['errors'][0]['status'] == 'unsafe_path'
    assert result['matched'][0]['kind'] == 'report_metadata'
    assert result['matched'][0]['declared']['conclusions'] == 'unknown'


def test_large_declaration_is_marked_and_cannot_expand_response_without_bound(tmp_path):
    path = 'docs/experiments/raw/large'
    put(tmp_path, f'{path}/checkpoint.json', {
        'conclusion': 'a' * 13000,
        'nested': [{'decision_use': 'b' * 5000} for _ in range(100)],
    })
    result = build(tmp_path, studies=[path])
    assert result['search']['declarations_truncated'] is True
    declaration = result['matched'][0]['declared']['conclusions'][0]
    assert declaration['value']['status'] == 'truncated_value'
    assert len(json.dumps(result)) < 150000
