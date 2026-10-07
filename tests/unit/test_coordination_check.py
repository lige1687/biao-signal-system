"""Check meaningful conflict and stale/offline failure cases without any network writes."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/sync/check_coordination.py'
spec = importlib.util.spec_from_file_location('coordination_check', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def entry(tid='one', owner='thread-one', paths=None, deps=None):
    return {'task_id': tid, 'owner': owner, 'status': 'active',
            'write_paths': paths if paths is not None else ['docs/one/'],
            'depends_on': deps or []}


def docs(entries):
    data = {'schema_version': 1, 'record_id': 'controller',
            'checked_coordination_sha': 'a' * 40, 'assignments': entries}
    return {'controller.md': '```lei-coordination-json\n' + json.dumps(data) + '\n```'}


class CoordinationCheckTests(unittest.TestCase):
    def test_registered_owner_and_child_path(self):
        result = mod.validate(docs([entry()]), 'one', 'thread-one', ['docs/one/result.md'])
        self.assertTrue(result['declared_checks_passed'])

    def test_duplicate_id_even_with_same_owner(self):
        self.assertFalse(mod.validate(docs([entry(), entry()]))['declared_checks_passed'])

    def test_directory_and_child_writers_conflict(self):
        result = mod.validate(docs([entry(paths=['src/']), entry('two', paths=['src/x.py'])]))
        self.assertIn('write overlap', ' '.join(result['errors']))

    def test_completed_and_stale_are_not_automatic_release(self):
        first = entry(); first['status'] = 'completed'
        result = mod.validate(docs([first, entry('two', paths=['docs/one/a.md'])]))
        self.assertFalse(result['declared_checks_passed'])
        first['scope_released'] = True
        self.assertTrue(mod.validate(docs([first, entry('two', paths=['docs/one/a.md'])]))['declared_checks_passed'])

    def test_unknown_or_cyclic_dependency(self):
        self.assertFalse(mod.validate(docs([entry(deps=['missing'])]))['declared_checks_passed'])
        self.assertFalse(mod.validate(docs([entry(deps=['two']), entry('two', paths=['docs/two/'], deps=['one'])]))['declared_checks_passed'])

    def test_wrong_owner_unregistered_and_path_traversal(self):
        for tid, owner, path in [('one', 'other', 'docs/one/a.md'),
                                 ('unknown', 'thread-one', 'docs/one/a.md'),
                                 ('one', 'thread-one', 'docs/one/../../secret')]:
            with self.subTest(tid=tid, owner=owner, path=path):
                self.assertFalse(mod.validate(docs([entry()]), tid, owner, [path])['declared_checks_passed'])

    def test_legacy_report_is_explicitly_unchecked(self):
        result = mod.validate({'legacy.md': '# active, but no structured record'})
        self.assertEqual(result['legacy_records_require_human_review'], ['legacy.md'])
        self.assertFalse(mod.validate({'legacy.md': '# active'}, 'legacy', 'thread')['declared_checks_passed'])

    def test_network_failure_does_not_use_cached_state(self):
        with patch.object(mod, 'load_online', side_effect=RuntimeError('fetch failed')), patch('builtins.print') as out:
            self.assertEqual(mod.main([]), 3)
            result = json.loads(out.call_args.args[0])
            self.assertFalse(result['online_verified'])
            self.assertFalse(result['work_clearance'])


if __name__ == '__main__':
    unittest.main()
