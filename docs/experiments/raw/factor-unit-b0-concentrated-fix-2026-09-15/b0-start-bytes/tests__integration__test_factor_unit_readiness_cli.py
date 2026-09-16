"""check_factor_unit_readiness CLI 集成测试（合成正/负各1 + 真实资格1批）。"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
CLI = REPO / 'scripts/check_factor_unit_readiness.py'
TMP = Path('/tmp/factor_unit_cli_test')
CARD = (
    'docs/experiments/raw/factor-research-workbench-v1-2026-09-14/'
    'candidate-card-dual-ma-bull-state-draft-1.md'
)
CN_CAL = ('docs/experiments/raw/research-calendar-completion-2026-09-10/'
          'calendar-merged/calendar.json')
SD = 'docs/experiments/raw/factor-unit-close-adapter-2026-09-15/source-decision.csv'
CODE_ID = [
    'src/lei_signal/research/factor_unit/__init__.py',
    'src/lei_signal/research/factor_unit/close_state.py',
    'src/lei_signal/research/factor_unit/study_contract.py',
    'src/lei_signal/research/factor_unit/state_description.py',
]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_synthetic_fixtures() -> dict:
    """合成正例所需：两市场合成行情、合成美区日历、合成已验证价格证据。"""
    import pandas as pd

    data_dir = TMP / 'fixtures'
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for sym in ('510300', '159915', 'SPY', 'QQQ'):
        p = data_dir / f'{sym}.parquet'
        pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=30).strftime('%Y-%m-%d'),
            'open': 1.0, 'high': 1.0, 'low': 1.0, 'close': 100.0,
        }).to_parquet(p)
        paths[sym] = p
    us_cal = data_dir / 'us_calendar_synthetic.json'
    us_cal.write_text(json.dumps({'note': 'synthetic calendar fixture；非真实NYSE证据'}))
    evidence = data_dir / 'price_basis_evidence_synthetic.json'
    evidence.write_text(json.dumps({'note': 'synthetic evidence fixture'}))
    return {'data_dir': data_dir, 'us_cal': us_cal, 'evidence': evidence, 'prices': paths}


def syn_contract(fx: dict, **over):
    c = {
        'data_mode': 'synthetic',
        'object_ref': 'candidate:lei.dual_ma.bull_state@draft-1',
        'candidate_card': {'path': CARD, 'sha256': _sha(REPO / CARD)},
        'theme': 'trend', 'type': 'state_signal', 'use': 'historical_description',
        'lookback': 20, 'e_offset': 1, 'x_offset': 22, 'regime': 'none',
        'universe': {'universe_id': 'synthetic', 'members': ['510300', '159915', 'SPY', 'QQQ'],
                     'attribute_labels': {}},
        'target_basis': 'total_return_wealth',
        'data_identity': {
            sym: {'path': str(p), 'sha256': _sha(p), 'fetched_at': None,
                  'available_at': None, 'point_in_time_verified': False,
                  'price_basis_status': 'price_basis_verified',
                  'price_basis_evidence': str(fx['evidence'])}
            for sym, p in fx['prices'].items()
        },
        'calendar_identity': {
            'CN': {'source': CN_CAL, 'sha256': _sha(REPO / CN_CAL),
                   'coverage': ['1990-01-01', '2026-12-31'],
                   'session_close': '15:00', 'timezone': 'Asia/Shanghai',
                   'half_day_close': None},
            'US': {'source': str(fx['us_cal']), 'sha256': _sha(fx['us_cal']),
                   'coverage': ['1990-01-01', '2026-12-31'],
                   'session_close': '16:00', 'timezone': 'America/New_York',
                   'half_day_close': {'time': '13:00', 'timezone': 'America/New_York'}},
        },
        'source_decision': {'path': SD, 'sha256': _sha(REPO / SD)},
        'code_identity': {k: _sha(REPO / k) for k in CODE_ID},
        'standards': ['docs/research/experiment-backtest-principles.md@1.1'],
        'research_cutoff': '2026-09-15T23:59:00+08:00',
    }
    c.update(over)
    return c


@pytest.fixture(scope='module')
def fx():
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    return make_synthetic_fixtures()


def run_cli(contract: dict, name: str, fresh: bool = True):
    cp = TMP / f'{name}-contract.json'
    cp.write_text(json.dumps(contract))
    out = TMP / f'{name}-out'
    if fresh:
        shutil.rmtree(out, ignore_errors=True)
    proc = subprocess.run(['python3', str(CLI), '--contract', str(cp), '--out', str(out)],
                          capture_output=True, text=True)
    return proc, out


def test_synthetic_positive_exit0_freeze_complete(fx):
    proc, out = run_cli(syn_contract(fx), 'syn-pos')
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['completed'] is True
    assert all(h for h in manifest['file_hashes'].values())
    verdict = json.loads((out / 'verdict.json').read_text())
    assert verdict['status'] == 'ok'
    code_files = list((out / 'code-freeze').iterdir())
    assert len(code_files) >= 10  # 5代码 + 5规范/卡 + 来源表 + 日历
    # 目录已存在 → 拒绝覆盖
    proc2, _ = run_cli(syn_contract(fx), 'syn-pos', fresh=False)
    assert proc2.returncode == 3


def test_synthetic_negative_no_source_decision(fx):
    c = syn_contract(fx)
    c.pop('source_decision')
    proc, out = run_cli(c, 'syn-neg')
    assert proc.returncode == 2
    verdict = json.loads((out / 'verdict.json').read_text())
    assert any('source_decision' in r for r in verdict['reasons'])


def test_real_contract_exit2_with_structures():
    from tests.unit.test_factor_unit_study_contract import base_contract
    c = base_contract()
    c['data_mode'] = 'real'
    c['source_decision'] = {'path': SD, 'sha256': _sha(REPO / SD)}
    proc, out = run_cli(c, 'real-check')
    assert proc.returncode == 2
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['completed'] is True
    assert manifest['structure']['510300']['rows'] == 3465
    assert manifest['structure']['QQQ']['first_date'] == '1999-03-10'
    verdict = json.loads((out / 'verdict.json').read_text())
    assert verdict['markets']['SPY']['target'] == 'blocked'


def test_real_tampered_input_exit2():
    from tests.unit.test_factor_unit_study_contract import base_contract
    c = base_contract()
    c['data_mode'] = 'real'
    c['source_decision'] = {'path': SD, 'sha256': _sha(REPO / SD)}
    c['data_identity']['510300']['sha256'] = '0' * 64
    proc, _ = run_cli(c, 'real-tamper')
    assert proc.returncode == 2
    assert '510300' in proc.stdout


def test_param_tamper_exit3(fx):
    proc, _ = run_cli(syn_contract(fx, x_offset=20), 'syn-param')
    assert proc.returncode == 3


def test_bad_card_identity_exit3(fx):
    c = syn_contract(fx)
    c['candidate_card']['sha256'] = 'f' * 64
    proc, _ = run_cli(c, 'syn-card')
    assert proc.returncode == 3
