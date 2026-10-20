"""主控限定复核四项反例的pytest固化（2026-09-15）：修前应失败，修后应全绿。

反例来源：docs/experiments/factor-unit-b0-fix-controller-review-2026-09-15.md §4
（P1自填证据升级 / P1稀疏截止泄漏 / P2可空布尔断点 / P2证据漏归档）。
T4的CLI归档断言在 tests/integration/test_factor_unit_readiness_cli.py。

全部为合成夹具；真实资格本轮0次运行，不为造正例伪造市场核验。
独立期望：无供应商原件的真实正向资格数=0；合法合成正例数>0；
含分红财富目标不能仅凭供应商调整价声明通过。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research.factor_unit.close_state import compute_close_state
from lei_signal.research.factor_unit.state_description import describe_states
from lei_signal.research.factor_unit.study_contract import validate_study_contract
from tests.unit.test_factor_unit_b0_controller_cases import fx as fx  # noqa: F401
from tests.unit.test_factor_unit_b0_controller_cases import syn_contract

REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ── Task 1：自填证据不得升级真实含分红资格 ───────────────────────────

def _real_single_symbol(fx, tier, vendor_ref, sd_tier=None, sd_dup=False,
                        ev_dup=False):
    """真实510300身份（文件/哈希/日历）不变，只同步改合同/证据/CSV声明层。

    与主控 reproduce.py 的伪造方式一致：所有外部文件哈希真实一致，
    但声明内容是自写的——不得因此得到真实目标资格。
    """
    c = syn_contract(fx, data_mode='real')
    c['universe']['members'] = ['510300']
    c['data_identity'] = {'510300': c['data_identity']['510300']}
    c['calendar_identity'] = {'CN': c['calendar_identity']['CN']}
    entry = c['data_identity']['510300']
    entry['price_basis_status'] = tier
    rec = {'symbol': '510300', 'input_sha256': _sha(fx['prices']['510300']),
           'price_basis_status': tier, 'data_mode': 'real',
           'vendor_traceable': vendor_ref is not None,
           'vendor_response_ref': vendor_ref}
    records = [rec, dict(rec)] if ev_dup else [rec]
    ev = fx['tmp'] / ('ev-four-' + hashlib.sha256(
        json.dumps(records, sort_keys=True, default=str).encode()).hexdigest()[:12] + '.json')
    ev.write_text(json.dumps({'schema': 'factor-unit-price-evidence/1',
                              'records': records}))
    entry['price_basis_evidence'] = {'path': str(ev), 'sha256': _sha(ev)}
    lines = ['symbol,sha256,provenance_tier',
             f"510300,{_sha(fx['prices']['510300'])},{sd_tier or tier}"]
    if sd_dup:
        lines.append(lines[1])
    sd = fx['tmp'] / ('sd-four-' + hashlib.sha256(
        '\n'.join(lines).encode()).hexdigest()[:12] + '.csv')
    sd.write_text('\n'.join(lines) + '\n')
    c['source_decision'] = {'path': str(sd), 'sha256': _sha(sd)}
    return c


def _vendor_file(fx, symbol='510300', input_sha=None, request_params=None,
                 price_semantics='vendor_adjusted_close'):
    if request_params is None:
        request_params = {'adjust': 'qfq', 'symbol': symbol}
    payload = {'records': [{'symbol': symbol,
                            'input_sha256': input_sha or _sha(fx['prices']['510300']),
                            'request_params': request_params,
                            'price_semantics': price_semantics}]}
    p = fx['tmp'] / ('vendor-' + hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12] + '.json')
    p.write_text(json.dumps(payload))
    return p


def test_forged_snapshot_provenance_bound_not_qualified(fx):
    # 主控反例1：合同/证据/CSV一致自填snapshot_provenance_bound，无供应商原件
    c = _real_single_symbol(fx, 'snapshot_provenance_bound',
                            '/definitely/nonexistent/provider.json')
    got = validate_study_contract(c)
    assert got['status'] == 'restricted'
    assert got['markets']['510300']['target'] == 'blocked'
    assert any('manual_target_review_required' in r for r in got['reasons'])


def test_forged_price_basis_verified_fake_vendor_rejected(fx):
    # 主控反例2：verified+指向不存在文件的字符串vendor_response_ref → 拒绝
    c = _real_single_symbol(fx, 'price_basis_verified',
                            '/definitely/nonexistent/provider.json')
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_structured_vendor_ref_nonexistent_file_rejected(fx):
    c = _real_single_symbol(fx, 'price_basis_verified',
                            {'path': '/definitely/nonexistent/provider.json',
                             'sha256': '0' * 64})
    with pytest.raises(ValueError, match='不存在'):
        validate_study_contract(c)


def test_vendor_record_wrong_input_binding_rejected(fx):
    # 供应商原件身份真实但绑定的是另一只产品的输入哈希 → 错产品/错输入拒绝
    vf = _vendor_file(fx, input_sha=_sha(fx['prices']['SPY']))
    c = _real_single_symbol(fx, 'price_basis_verified',
                            {'path': str(vf), 'sha256': _sha(vf)})
    with pytest.raises(ValueError, match='输入'):
        validate_study_contract(c)


def test_vendor_record_missing_params_or_semantics_rejected(fx):
    vf = _vendor_file(fx, request_params={})
    c = _real_single_symbol(fx, 'price_basis_verified',
                            {'path': str(vf), 'sha256': _sha(vf)})
    with pytest.raises(ValueError, match='请求参数'):
        validate_study_contract(c)


def test_valid_vendor_material_still_not_total_return_qualified(fx):
    # 来源检查可完成，但含分红财富构造未核 → 目标仍不批准，不得称资格齐备
    vf = _vendor_file(fx)
    c = _real_single_symbol(fx, 'price_basis_verified',
                            {'path': str(vf), 'sha256': _sha(vf)})
    got = validate_study_contract(c)
    assert got['status'] == 'restricted'
    assert got['markets']['510300']['target'] == 'blocked'
    assert any('来源检查完成' in n for n in got['notes'])
    assert any('manual_target_review_required' in r for r in got['reasons'])


def test_conflicting_duplicate_evidence_records_rejected(fx):
    c = _real_single_symbol(fx, 'snapshot_provenance_bound', None, ev_dup=True)
    with pytest.raises(ValueError, match='重复'):
        validate_study_contract(c)


def test_duplicate_source_decision_rows_rejected(fx):
    c = _real_single_symbol(fx, 'snapshot_provenance_bound', None, sd_dup=True)
    with pytest.raises(ValueError, match='唯一'):
        validate_study_contract(c)


def test_sha256_16_prefix_no_longer_accepted(fx):
    c = _real_single_symbol(fx, 'snapshot_provenance_bound', None)
    short = _sha(fx['prices']['510300'])[:16]
    sd = fx['tmp'] / 'sd-prefix16.csv'
    sd.write_text('symbol,sha256_16,provenance_tier\n'
                  f'510300,{short},snapshot_provenance_bound\n')
    c['source_decision'] = {'path': str(sd), 'sha256': _sha(sd)}
    with pytest.raises(ValueError, match='完整sha256'):
        validate_study_contract(c)


def test_legal_synthetic_positive_still_passes(fx):
    # 合法合成目标仍可通过以验证代码，不是把所有用途一律拒绝
    got = validate_study_contract(syn_contract(fx))
    assert got['status'] == 'ok'
    assert all(v['target'] == 'pending_controller_freeze'
               for v in got['markets'].values())


# ── Task 2：稀疏结果与主比较共用同一合法集合 ─────────────────────────

@pytest.fixture()
def synthetic_50_day_fixture():
    """固定夹具：2020-01-01起50个合成日、15:00+08收盘、state全true、
    I=100..149，评价期全50日，锚点第一日。不是实际交易所日历。"""
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    schedule = pd.DataFrame({
        'session': dates,
        'close_at': dates.tz_localize('Asia/Shanghai') + pd.Timedelta(hours=15),
    })
    values = pd.DataFrame({'symbol': 'SYN', 'session': dates,
                           'state': [True] * 50,
                           'I': [float(100 + i) for i in range(50)]})
    contract = {
        'data_mode': 'synthetic',
        'object_ref': 'candidate:lei.dual_ma.bull_state@draft-1',
        'lookback': 20, 'e_offset': 1, 'x_offset': 22,
        'evaluation_window': {'start': '2020-01-01', 'end': '2020-02-19'},
        'research_cutoff': '2030-01-01T15:00:00+08:00',
        'sparse_anchor_session': {'SYN': '2020-01-01'},
        'sparse_step': 23,
    }
    return values, schedule, contract


def test_sparse_cannot_see_future(synthetic_50_day_fixture):
    values, schedule, contract = synthetic_50_day_fixture
    contract['research_cutoff'] = '2019-01-01T15:00:00+08:00'
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    assert row['comparison']['n'] == 0
    assert row['sparse_view']['true_slots_up'] == 0
    assert all(s['skipped'] and s['main'] is None and s['aux'] is None
               for s in row['sparse_view']['slots'])


def test_sparse_positive_control_cutoff_2030(synthetic_50_day_fixture):
    # 正向对照：截止2030 → 有效稀疏格为第0/23日，两个上涨计数保留；
    # 第46日目标不足跳过。不能靠取消稀疏输出蒙混通过。
    values, schedule, contract = synthetic_50_day_fixture
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    sv = row['sparse_view']
    assert [s['session'] for s in sv['slots']] == ['2020-01-01', '2020-01-24',
                                                   '2020-02-16']
    assert sv['slots'][0]['skipped'] is False
    assert abs(sv['slots'][0]['main'] - (122.0 / 101.0 - 1.0)) < 1e-12
    assert sv['slots'][1]['skipped'] is False
    assert abs(sv['slots'][1]['main'] - (145.0 / 124.0 - 1.0)) < 1e-12
    assert sv['slots'][2]['skipped'] is True
    assert sv['slots'][2]['skipped_reason'] == 'tail_immature'
    assert sv['slots'][2]['main'] is None and sv['slots'][2]['aux'] is None
    assert sv['true_slots_up'] == 2
    assert sv['false_slots_down'] == 0


def test_sparse_unknown_state_slot_not_counted(synthetic_50_day_fixture):
    # 未知状态格不展示成已可观察结果，不计true/false计数
    values, schedule, contract = synthetic_50_day_fixture
    values['state'] = values['state'].astype(object)
    values.loc[0, 'state'] = None
    values.loc[23, 'state'] = None
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    sv = row['sparse_view']
    assert all(s['skipped'] for s in sv['slots'])
    assert sv['slots'][0]['skipped_reason'] == 'state_unknown'
    assert sv['slots'][0]['main'] is None and sv['slots'][0]['aux'] is None
    assert sv['true_slots_up'] == 0


def test_sparse_not_mature_reason_before_close(synthetic_50_day_fixture):
    values, schedule, contract = synthetic_50_day_fixture
    # 截止=第0格标签终点(2020-01-23)收盘前 → 三格全部未成熟
    contract['research_cutoff'] = '2020-01-23T14:00:00+08:00'
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    sv = row['sparse_view']
    assert all(s['skipped'] and s['skipped_reason'] in ('not_mature', 'tail_immature')
               for s in sv['slots'])
    assert sv['true_slots_up'] == 0


# ── Task 3：上游可空布尔（pd.NA）原样接入 ────────────────────────────

@pytest.fixture()
def nullable_state_fixture():
    """50行真实接口格式：close=[100]*20+range(101,131)，state来自
    compute_close_state 原样可空布尔列；I独立取正的合成尺度；截止2030。"""
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    schedule = pd.DataFrame({
        'session': dates,
        'close_at': dates.tz_localize('Asia/Shanghai') + pd.Timedelta(hours=15),
    })
    calc = compute_close_state(pd.Series([100.0] * 20 + list(range(101, 131)),
                                         index=dates))
    values = pd.DataFrame({'symbol': 'SYN', 'session': dates,
                           'state': calc['state'].array,
                           'I': [100.0] * 50})
    contract = {
        'data_mode': 'synthetic',
        'object_ref': 'candidate:lei.dual_ma.bull_state@draft-1',
        'lookback': 20, 'e_offset': 1, 'x_offset': 22,
        'evaluation_window': {'start': '2020-01-01', 'end': '2020-02-19'},
        'research_cutoff': '2030-01-01T15:00:00+08:00',
        'sparse_anchor_session': {'SYN': '2020-01-01'},
        'sparse_step': 23,
    }
    return values, schedule, contract


def test_nullable_boolean_pipeline_hand_computed(nullable_state_fixture):
    # 手算期望：第0—19行未知；第20—27行状态true且21间隔标签完整 →
    # comparison.n=8；余行标签不足。不import被测函数生成期望。
    values, schedule, contract = nullable_state_fixture
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    assert row['state_unknown'] == 20
    assert row['comparison']['n'] == 8
    assert row['true_group']['n'] == 8
    assert row['false_group']['n'] == 0
    assert row['true_group']['n'] + row['false_group']['n'] == row['comparison']['n']


def test_all_pd_na_states_accepted_as_unknown(nullable_state_fixture):
    import pandas as _pd
    values, schedule, contract = nullable_state_fixture
    values['state'] = _pd.array([_pd.NA] * 50, dtype='boolean')
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    assert row['state_unknown'] == 50
    assert row['comparison']['n'] == 0


def test_mixed_bool_na_none_nan_accepted(nullable_state_fixture):
    values, schedule, contract = nullable_state_fixture
    mixed = [True, False, None, float('nan'), pd.NA] * 10
    values['state'] = mixed
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    assert row['state_unknown'] == 30
    assert row['state_true'] == 10 and row['state_false'] == 10


def test_string_and_numeric_states_still_rejected(nullable_state_fixture):
    values, schedule, contract = nullable_state_fixture
    for bad in ('false', '', 0, 1, 2):
        v = values.copy()
        v['state'] = [bad] * 50
        with pytest.raises(ValueError):
            describe_states(v, schedule, contract)


def test_task4_placeholder():
    # T4（价格证据归档）的CLI断言在集成测试；此处仅占位提醒四任务边界。
    assert True
