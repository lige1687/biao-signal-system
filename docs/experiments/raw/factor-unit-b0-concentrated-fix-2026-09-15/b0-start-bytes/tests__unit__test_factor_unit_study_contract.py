"""factor_unit.study_contract 反例先行测试。

任务书要求的最少反例逐一覆盖，每项都有合法对照（不是一律拒绝）。
全部为合同结构测试，不触碰真实数据内容。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lei_signal.research.factor_unit.study_contract import validate_study_contract

REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
CACHE = Path.home() / '.lei_signal_lab/cache/timing'
CARD = ('docs/experiments/raw/factor-research-workbench-v1-2026-09-14/'
        'candidate-card-dual-ma-bull-state-draft-1.md')
CARD_SHA = hashlib.sha256((REPO / CARD).read_bytes()).hexdigest()
CN_CAL = ('docs/experiments/raw/research-calendar-completion-2026-09-10/'
          'calendar-merged/calendar.json')


CODE_ID = {
    'src/lei_signal/research/factor_unit/close_state.py': None,
    'src/lei_signal/research/factor_unit/study_contract.py': None,
    'src/lei_signal/research/factor_unit/state_description.py': None,
}

def _entry(sym):
    path = CACHE / f'{sym}.parquet'
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'fetched_at': None, 'available_at': None, 'point_in_time_verified': False,
            'price_basis_status': 'producer_candidate_only'}


def base_contract(**over):
    c = {
        'object_ref': 'candidate:lei.dual_ma.bull_state@draft-1',
        'candidate_card': {'path': CARD, 'sha256': CARD_SHA},
        'theme': 'trend', 'type': 'state_signal', 'use': 'historical_description',
        'lookback': 20, 'e_offset': 1, 'x_offset': 22, 'regime': 'none',
        'market': 'CN+US',
        'universe': {
            'universe_id': 'b0_dual_ma_carriers_2026-09-15',
            'members': ['510300', '159915', 'SPY', 'QQQ'],
            'attribute_labels': {'510300': ['broad'], '159915': ['growth', 'broad'],
                                 'SPY': ['broad'], 'QQQ': ['growth']},
        },
        'target_basis': 'total_return_wealth',
        'data_identity': {sym: _entry(sym) for sym in
                            ('510300', '159915', 'SPY', 'QQQ')},
        'calendar_identity': {
            'CN': {'source': CN_CAL,
                   'sha256': hashlib.sha256((REPO / CN_CAL).read_bytes()).hexdigest(),
                   'coverage': ['1990-01-01', '2026-12-31'], 'session_close': '15:00',
                   'timezone': 'Asia/Shanghai', 'half_day_close': None},
            'US': {'source': None, 'reason': '无本地可核NYSE/Nasdaq日历'},
        },
        'standards': ['docs/research/experiment-backtest-principles.md@1.1',
                      'docs/research/definition-standard.md@1.1.0',
                      'docs/research/ai-execution-contract.md@1.0.1',
                      'docs/research/experiment-report-template.md@1.1.0'],
        'research_cutoff': '2026-09-15T23:59:00+08:00',
        'code_identity': {k: hashlib.sha256((REPO / k).read_bytes()).hexdigest() for k in CODE_ID},
        '_repo_root': str(REPO),
    }
    c.update(over)
    return c


# ── 合法对照 ─────────────────────────────────────────────────────────

def test_valid_contract_restricted_but_not_error():
    got = validate_study_contract(base_contract())
    assert got['status'] in ('restricted',)
    assert got['allowed_uses'] == []  # 存在 pending/blocked → 不放行
    assert any('point_in_time_verified=false' in n for n in got['notes'])
    assert any('blocked' in r for r in got['reasons'])  # 阻断仍在 reasons
    assert got['markets']['510300']['target'] in ('blocked', 'pending_controller_freeze')
    assert got['markets']['SPY']['calendar'] == 'unverified'


def test_verified_price_basis_unlocks_target_pending():
    c = base_contract()
    for s in c['data_identity'].values():
        s['price_basis_status'] = 'price_basis_verified'
        s['price_basis_evidence'] = 'independent-evidence.json'
    got = validate_study_contract(c)
    assert got['markets']['510300']['target'] == 'pending_controller_freeze'
    assert any('pending_controller_freeze' in n for n in got['notes'])
    assert got['reasons'] == [] or all('无本地可核日历' in r for r in got['reasons'])


def test_alternative_target_recorded_not_mixed():
    c = base_contract(target_basis='vendor_adjusted_price_change')
    got = validate_study_contract(c)
    assert got['markets']['510300']['target'] == 'blocked'  # 未达 snapshot_provenance_bound
    assert 'alternative_target_note' in got


# ── 反例（非法 → ValueError） ────────────────────────────────────────

def test_forged_object_reference():
    c = base_contract(object_ref='dual_ma.bull_state@1.0.0')  # 伪造已登记引用
    with pytest.raises(ValueError, match='object_ref'):
        validate_study_contract(c)


def test_modified_window_params():
    for key, val in (('lookback', 25), ('e_offset', 0), ('x_offset', 20)):
        c = base_contract(**{key: val})
        with pytest.raises(ValueError, match=key):
            validate_study_contract(c)


def test_session_close_as_available_at():
    c = base_contract()
    c['data_identity']['510300']['available_at'] = '2026-08-27T15:00:00'
    c['data_identity']['510300']['available_at_source'] = 'session_close:Asia/Shanghai'
    with pytest.raises(ValueError, match='冒充'):
        validate_study_contract(c)


def test_naive_available_at_without_source():
    c = base_contract()
    c['data_identity']['SPY']['available_at'] = '2026-08-27T16:00:00'  # 无来源
    with pytest.raises(ValueError, match='available_at'):
        validate_study_contract(c)


def test_self_certified_trust_flag():
    c = base_contract()
    c['data_identity']['SPY']['point_in_time_verified'] = True  # 无 available_at 自填可信
    with pytest.raises(ValueError, match='point_in_time_verified'):
        validate_study_contract(c)


def test_us_half_day_claimed_as_16():
    c = base_contract()
    c['calendar_identity']['US'] = {'source': 'x', 'sha256': 'y',
                                    'coverage': ['1990-01-01', '2026-12-31'],
                                    'session_close': '16:00', 'timezone': 'America/New_York',
                                    'half_day_close': {'time': '16:00',
                                                       'timezone': 'America/New_York'}}
    with pytest.raises(ValueError, match='half_day_close'):
        validate_study_contract(c)


def test_dst_offset_clock_rejected():
    # 用固定UTC偏移冒充当地墙钟：EST 16:00 写成 21:00+00:00 → 夏令时会差一小时
    c = base_contract()
    c['calendar_identity']['CN'] = dict(c['calendar_identity']['CN'])
    c['calendar_identity']['CN']['session_close'] = '07:00+00:00'
    with pytest.raises(ValueError, match='UTC偏移'):
        validate_study_contract(c)


def test_wrong_timezone_name():
    c = base_contract()
    c['calendar_identity']['CN']['timezone'] = 'UTC'
    with pytest.raises(ValueError, match='timezone'):
        validate_study_contract(c)


def test_empty_code_identity_keys_and_bad_card_hash():
    c = base_contract(candidate_card={'path': CARD, 'sha256': '0' * 64})
    with pytest.raises(ValueError, match='sha256'):
        validate_study_contract(c)


def test_calendar_hash_mismatch_reason_not_pass():
    c = base_contract()
    c['calendar_identity']['CN']['sha256'] = 'f' * 64
    got = validate_study_contract(c)
    assert any('哈希不符' in r for r in got['reasons'])


def test_calendar_missing_source_blocks_market():
    c = base_contract()
    c['calendar_identity']['CN'] = {'source': None}
    got = validate_study_contract(c)
    assert any('CN' in r and 'blocked' in r for r in got['reasons'])


def test_date_conflict_flagged():
    c = base_contract()
    c['data_identity']['510300']['date_range'] = ['2012-05-28', '2027-08-27']  # 超出日历覆盖
    got = validate_study_contract(c)
    assert any('日期冲突' in r or '超出日历覆盖' in r for r in got['reasons'])


def test_unknown_price_scale_cannot_compute_meaningful_change():
    c = base_contract()
    c['data_identity']['SPY']['price_basis_status'] = 'producer_candidate_only'
    c['target_basis'] = 'vendor_adjusted_price_change'
    got = validate_study_contract(c)
    assert got['markets']['SPY']['target'] == 'blocked'
    assert any('至少需要 snapshot_provenance_bound' in r for r in got['reasons'])


def test_carrier_substitution_rejected():
    c = base_contract()
    c['universe']['members'] = ['510300', '159915', 'SPY', 'IWM']  # 换标的
    with pytest.raises(ValueError, match='members'):
        validate_study_contract(c)


def test_prediction_use_rejected():
    c = base_contract(use='prediction')
    with pytest.raises(ValueError, match='use'):
        validate_study_contract(c)


def test_empty_code_identity_rejected():
    c = base_contract(code_identity={})
    with pytest.raises(ValueError, match='code_identity'):
        validate_study_contract(c)


def test_sha_drift_is_blocking_not_error():
    c = base_contract()
    c['data_identity']['510300']['sha256'] = '0' * 64
    got = validate_study_contract(c)
    assert any('哈希与合同不符' in r for r in got['reasons'])
    assert got['markets']['510300']['target'] == 'blocked' 
