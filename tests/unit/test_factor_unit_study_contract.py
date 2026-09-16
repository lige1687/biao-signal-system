"""factor_unit.study_contract 测试（B0集中修复版：证据结构化/日历内容级/身份闭合）。

保留原合同反例并适配新结构；主控反例主文件在
tests/unit/test_factor_unit_b0_controller_cases.py。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.research.factor_unit.study_contract import validate_study_contract
from tests.unit.test_factor_unit_b0_controller_cases import fx as fx
from tests.unit.test_factor_unit_b0_controller_cases import syn_contract

REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _real_mode_low_tier(fx):
    """真实模式+producer_candidate_only证据与匹配的夹具SD。"""
    c = syn_contract(fx, data_mode='real')
    ev = fx['tmp'] / 'evidence_real_pco.json'
    records = [{'symbol': sym, 'input_sha256': _sha(fx['prices'][sym]),
                'price_basis_status': 'producer_candidate_only', 'data_mode': 'real',
                'sources': ['sd']}
               for sym in fx['prices']]
    ev.write_text(json.dumps({'schema': 'factor-unit-price-evidence/1',
                              'records': records}))
    sd = fx['tmp'] / 'source-decision-fixture.csv'
    lines = ['symbol,sha256,provenance_tier']
    for sym, p in fx['prices'].items():
        lines.append(f'{sym},{_sha(p)},producer_candidate_only')
    sd.write_text('\n'.join(lines) + '\n')
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': str(ev), 'sha256': _sha(ev)}
        e['price_basis_status'] = 'producer_candidate_only'
    c['source_decision'] = {'path': str(sd), 'sha256': _sha(sd)}
    return c


# ── 合法对照 ─────────────────────────────────────────────────────────

def test_valid_synthetic_contract_ok(fx):
    got = validate_study_contract(syn_contract(fx))
    assert got['status'] == 'ok'
    assert all(v['target'] == 'pending_controller_freeze'
               for v in got['markets'].values())
    assert any('point_in_time_verified=false' in n for n in got['notes'])


def test_alternative_target_recorded_not_mixed(fx):
    c = syn_contract(fx, target_basis='vendor_adjusted_price_change')
    got = validate_study_contract(c)
    assert got['markets']['510300']['target'] == 'pending_controller_freeze'
    assert 'alternative_target_note' in got


# ── 身份与结构反例 ───────────────────────────────────────────────────

def test_forged_object_reference(fx):
    c = syn_contract(fx, object_ref='dual_ma.bull_state@1.0.0')
    with pytest.raises(ValueError, match='object_ref'):
        validate_study_contract(c)


def test_modified_window_params(fx):
    for key, val in (('lookback', 25), ('e_offset', 0), ('x_offset', 20)):
        c = syn_contract(fx, **{key: val})
        with pytest.raises(ValueError, match=key):
            validate_study_contract(c)


def test_session_close_as_available_at(fx):
    c = syn_contract(fx)
    e = c['data_identity']['510300']
    e['available_at'] = '2020-03-01T15:00:00+08:00'
    e['available_at_source'] = 'session_close:Asia/Shanghai'
    with pytest.raises(ValueError, match='冒充'):
        validate_study_contract(c)


def test_naive_available_at_rejected(fx):
    c = syn_contract(fx)
    e = c['data_identity']['SPY']
    e['available_at'] = '2020-03-01T16:00:00'  # 无时区
    e['available_at_source'] = 'fixture'
    with pytest.raises(ValueError, match='时区'):
        validate_study_contract(c)


def test_real_point_in_time_rejected(fx):
    c = _real_mode_low_tier(fx)
    e = c['data_identity']['SPY']
    e.update(available_at='2020-03-01T16:00:00-05:00',
             available_at_source='fixture', point_in_time_verified=True)
    with pytest.raises(ValueError, match='真实身份'):
        validate_study_contract(c)


def test_us_half_day_claimed_as_16(fx):
    c = syn_contract(fx)
    c['calendar_identity']['US']['half_day_close'] = {
        'time': '16:00', 'timezone': 'America/New_York'}
    with pytest.raises(ValueError, match='half_day_close'):
        validate_study_contract(c)


def test_dst_offset_clock_rejected(fx):
    c = syn_contract(fx)
    c['calendar_identity']['CN']['session_close'] = '07:00+00:00'
    with pytest.raises(ValueError, match='UTC偏移'):
        validate_study_contract(c)


def test_calendar_missing_source_blocks_market(fx):
    c = syn_contract(fx)
    c['calendar_identity']['US'] = {'source': None, 'synthetic_schedule': None}
    got = validate_study_contract(c)
    assert got['markets']['SPY']['target'] == 'blocked'
    assert any('无日历材料' in r for r in got['reasons'])


def test_evaluation_window_outside_calendar_located(fx):
    c = syn_contract(fx, evaluation_window={'start': '2021-06-01', 'end': '2021-06-30'})
    got = validate_study_contract(c)
    assert got['status'] == 'restricted'
    assert any('缺定义' in r for r in got['reasons'])


def test_carrier_substitution_rejected(fx):
    c = syn_contract(fx)
    c['universe']['members'] = ['510300', '159915', 'SPY', 'IWM']
    with pytest.raises(ValueError, match='members'):
        validate_study_contract(c)


def test_prediction_use_rejected(fx):
    c = syn_contract(fx, use='prediction')
    with pytest.raises(ValueError, match='use'):
        validate_study_contract(c)


def test_evidence_missing_schema_rejected(fx):
    c = syn_contract(fx)
    bad = fx['tmp'] / 'evidence_noschema.json'
    bad.write_text('{"records": []}')
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': str(bad), 'sha256': _sha(bad)}
    with pytest.raises(ValueError, match='schema'):
        validate_study_contract(c)


def test_unknown_price_scale_blocked_in_real_mode(fx):
    c = _real_mode_low_tier(fx)
    got = validate_study_contract(c)
    assert got['markets']['SPY']['target'] == 'blocked'
    assert any('更高价格档位' in r for r in got['reasons'])
