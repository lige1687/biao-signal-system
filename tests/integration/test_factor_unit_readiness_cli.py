"""check_factor_unit_readiness CLI 集成测试（B0集中修复版）。

覆盖：合成正/负、真实资格1批、被改输入(退出3)、删必需键(退出3)、
错哈希(退出3)、参数擅改(退出3)、目录已存在(退出3)、restricted不打印资料齐备。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.unit.test_factor_unit_b0_controller_cases import fx as fx
from tests.unit.test_factor_unit_b0_controller_cases import syn_contract

REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
CLI = REPO / 'scripts/check_factor_unit_readiness.py'
TMP = Path('/tmp/factor_unit_cli_fix_test')
CARD = ('docs/experiments/raw/factor-research-workbench-v1-2026-09-14/'
        'candidate-card-dual-ma-bull-state-draft-1.md')
SD = 'docs/experiments/raw/factor-unit-close-adapter-2026-09-15/source-decision.csv'


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def env(fx):
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    return syn_contract(fx)


def run_cli(contract: dict, name: str, fresh: bool = True):
    cp = TMP / f'{name}-contract.json'
    cp.write_text(json.dumps(contract))
    out = TMP / f'{name}-out'
    if fresh:
        shutil.rmtree(out, ignore_errors=True)
    proc = subprocess.run(['python3', str(CLI), '--contract', str(cp), '--out', str(out)],
                          capture_output=True, text=True)
    return proc, out


def test_synthetic_positive_exit0_package_complete(env):
    proc, out = run_cli(env, 'syn-pos')
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['package_completed'] is True
    assert manifest['qualification_status'] == 'ok'
    assert manifest['exit_code'] == 0
    # 运行合同原字节随包保存，且 contract_sha256 反查一致
    src = (out / 'contract.source.json').read_bytes()
    assert hashlib.sha256(src).hexdigest() == manifest['contract_sha256']
    # file_hashes 用包内相对路径并与实际集合双向核对
    rels = set(manifest['file_hashes'])
    on_disk = {str(f.relative_to(out)).replace('\\', '/')
               for f in out.rglob('*') if f.is_file() and f.name != 'manifest.json'}
    assert rels == on_disk
    assert all(h for h in manifest['file_hashes'].values())
    # 完整必需代码键入包（生产函数/规则/CLI，非只新模块）
    for rel in ('src__lei_signal__rules__dual_ma.py', 'src__lei_signal__rules__lei_color.py',
                'configs__rules.v2.yaml', 'scripts__check_factor_unit_readiness.py',
                'src__lei_signal__research__trading_calendar.py'):
        assert (out / 'code-freeze' / rel).is_file(), rel


def test_synthetic_positive_archives_price_evidence(env, fx):
    """四项修复T4：合同直接引用的price_basis_evidence原字节必须入包，
    依赖闭包双向核对为空（不默默漏包）。"""
    proc, out = run_cli(env, 'syn-ev')
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ev_dir = out / 'evidence'
    archived = [p for p in ev_dir.iterdir() if p.is_file()]
    assert archived, '合同引用的 price_basis_evidence 必须随包保存'
    assert any(p.read_bytes() == fx['evidence'].read_bytes() for p in archived)
    manifest = json.loads((out / 'manifest.json').read_text())
    closure = manifest['dependency_closure']
    assert str(fx['evidence']) in closure['expected']
    assert closure['missing_from_archive'] == []
    assert closure['archived_not_expected'] == []


def test_missing_price_evidence_file_exit3(env):
    c = json.loads(json.dumps(env))
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': '/definitely/absent-evidence.json',
                                     'sha256': '0' * 64}
    proc, _ = run_cli(c, 'syn-noev')
    assert proc.returncode == 3


def test_synthetic_negative_missing_source_decision_exit3(env):
    c = dict(env)
    c.pop('source_decision')
    proc, _ = run_cli(c, 'syn-neg')
    assert proc.returncode == 3


def test_required_code_keys_shrunk_exit3(env):
    c = dict(env)
    keep = 'src/lei_signal/research/factor_unit/__init__.py'
    c['code_identity'] = {keep: _sha(REPO / keep)}
    proc, _ = run_cli(c, 'syn-keys')
    assert proc.returncode == 3
    assert '必需代码键' in proc.stderr


def test_wrong_required_key_hash_exit3(env):
    c = dict(env)
    c['code_identity']['src/lei_signal/rules/dual_ma.py'] = '0' * 64
    proc, _ = run_cli(c, 'syn-badhash')
    assert proc.returncode == 3
    assert '哈希不符' in proc.stderr


def test_param_tamper_exit3(env):
    proc, _ = run_cli(dict(env, x_offset=20), 'syn-param')
    assert proc.returncode == 3


def test_output_dir_exists_exit3(env):
    proc, out = run_cli(env, 'syn-pos', fresh=False)
    assert proc.returncode == 3


def test_bad_card_hash_exit3(env):
    c = dict(env)
    c['candidate_card'] = dict(c['candidate_card'], sha256='f' * 64)
    proc, _ = run_cli(c, 'syn-card')
    assert proc.returncode == 3


def test_real_qualification_exit2_restricted_not_claimed_complete(fx):
    cache = Path.home() / '.lei_signal_lab/cache/timing'
    c = syn_contract(fx, data_mode='real')
    c['data_identity'] = {
        sym: {'path': str(cache / f'{sym}.parquet'),
              'sha256': _sha(cache / f'{sym}.parquet'),
              'fetched_at': None, 'available_at': None,
              'available_at_source': None, 'point_in_time_verified': False,
              'date_range': ['2012-05-28', '2026-08-27'],
              'price_basis_status': 'producer_candidate_only',
              'price_basis_evidence': {'path': str(fx['evidence']),
                                       'sha256': _sha(fx['evidence'])}}
        for sym in ('510300', '159915', 'SPY', 'QQQ')}
    # 真实模式需要 evidence 记录 data_mode=real + 与真实载体哈希前缀匹配的
    # 规整SD CSV（v1 source-decision.csv 有未引号逗号，机器解析列错位——Task4 出 v2）
    ev = TMP / 'evidence_real.json'
    records = [{'symbol': sym, 'input_sha256': _sha(cache / f'{sym}.parquet'),
                'price_basis_status': 'producer_candidate_only', 'data_mode': 'real',
                'sources': ['source-decision-v2.csv']}
               for sym in c['data_identity']]
    ev.write_text(json.dumps({'schema': 'factor-unit-price-evidence/1',
                              'records': records}))
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': str(ev), 'sha256': _sha(ev)}
    sd = TMP / 'source-decision-fixture.csv'
    lines = ['symbol,sha256,provenance_tier']
    for sym in c['data_identity']:
        lines.append(f"{sym},{_sha(cache / (sym + '.parquet'))},"
                     "producer_candidate_only")
    sd.write_text('\n'.join(lines) + '\n')
    c['source_decision'] = {'path': str(sd), 'sha256': _sha(sd)}
    proc, out = run_cli(c, 'real-check')
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert '资料齐备' not in proc.stdout
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['package_completed'] is True  # restricted也可打包完成
    assert manifest['qualification_status'] == 'restricted'
    assert manifest['exit_code'] == 2
    assert manifest['structure']['510300']['rows'] == 3465
    verdict = json.loads((out / 'verdict.json').read_text())
    assert verdict['markets']['SPY']['target'] == 'blocked'
