"""证券识别只排除回测编号所在位置，不排除同值的用户选择。"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from lei_signal.api.routes.agent import _symbol_candidates_from_message


@pytest.mark.parametrize('message, expected', [
    ('看518880，run_id=20260909-180000-518880', ['518880.SS']),
    ('run_id=20260909-180000-518880，另外看518880', ['518880.SS']),
    ('看RUN，run_id=20260909-180000-abcdef', ['RUN']),
    ('run_id=20260909-180000-abcdef 和 20260909-190000-600000', []),
    ('看518880与600000，run_id=20260909-180000-600000',
     ['518880.SS', '600000.SS']),
])
def test_run_identifiers_do_not_hide_independent_symbols(message, expected):
    probed = []

    def resolve(token):
        probed.append(token)
        return SimpleNamespace(symbol=token + '.SS' if token.isdigit() else token)

    with patch('lei_signal.data.symbols.resolve_symbol', side_effect=resolve):
        assert _symbol_candidates_from_message(message) == expected
    assert '180000' not in probed
    assert '190000' not in probed
    assert 'ABCDEF' not in probed
