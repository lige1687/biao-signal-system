"""B0主控反例的pytest固化（R1–R4）：修前应失败，修后应全绿。

全部使用合成夹具，不依赖个人真实缓存；不用mock放行资格检查。
期望依据：docs/experiments/factor-unit-b0-controller-review-2026-09-15.md §2。
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_unit.state_description import describe_states
from lei_signal.research.factor_unit.study_contract import validate_study_contract

REPO = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
CACHE = Path.home() / '.lei_signal_lab/cache/timing'
CARD = ('docs/experiments/raw/factor-research-workbench-v1-2026-09-14/'
        'candidate-card-dual-ma-bull-state-draft-1.md')
CN_CAL = ('docs/experiments/raw/research-calendar-completion-2026-09-10/'
          'calendar-merged/calendar.json')
SD = 'docs/experiments/raw/factor-unit-close-adapter-2026-09-15/source-decision.csv'
REQUIRED_CODE = [
    'src/lei_signal/research/factor_unit/__init__.py',
    'src/lei_signal/research/factor_unit/close_state.py',
    'src/lei_signal/research/factor_unit/study_contract.py',
    'src/lei_signal/research/factor_unit/state_description.py',
    'scripts/check_factor_unit_readiness.py',
    'src/lei_signal/features/indicators.py',
    'src/lei_signal/rules/lei_color.py',
    'src/lei_signal/rules/dual_ma.py',
    'src/lei_signal/domain/rules_config.py',
    'configs/rules.v2.yaml',
    'src/lei_signal/research/trading_calendar.py',
]
REQUIRED_STANDARDS = [
    'docs/research/experiment-backtest-principles.md@1.1',
    'docs/research/definition-standard.md@1.1.0',
    'docs/research/ai-execution-contract.md@1.0.1',
    'docs/research/experiment-report-template.md@1.1.0',
]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def fx(tmp_path_factory):
    """合成夹具：合成价格、合成逐日日历、合成证据文件。"""
    tmp = tmp_path_factory.mktemp('b0fx')
    prices = {}
    for i, sym in enumerate(('510300', '159915', 'SPY', 'QQQ')):
        p = tmp / f'{sym}.parquet'
        pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=60).strftime('%Y-%m-%d'),
            'open': 1.0, 'high': 1.0, 'low': 1.0,
            'close': 100.0 + i,  # 每只不同，保证哈希唯一
        }).to_parquet(p)
        prices[sym] = p
    # 合成逐日日历（schedule：session/close_at 逐日，覆盖2020全年+尾部缓冲）
    days = pd.date_range('2019-11-01', '2020-12-31', freq='D')
    cal = tmp / 'us_calendar_synthetic.parquet'
    pd.DataFrame({
        'session': days.strftime('%Y-%m-%d'),
        'close_at': days.tz_localize('America/New_York').strftime('%Y-%m-%dT16:00:00%z'),
        'is_half_day': False,
    }).to_parquet(cal)
    # 合成证据文件（结构化记录，synthetic身份）
    ev = tmp / 'evidence_synthetic.json'
    records = []
    for sym, p in prices.items():
        records.append({
            'symbol': sym, 'input_sha256': _sha(p),
            'price_basis_status': 'price_basis_verified',
            'data_mode': 'synthetic',
            'verification_method': 'synthetic_fixture',
            'sources': ['synthetic-fixture'],
        })
    ev.write_text(json.dumps({'schema': 'factor-unit-price-evidence/1', 'records': records}))
    # 合成SD CSV：完整sha256与夹具哈希精确一致（sha256_16前缀不再接受），
    # 档位=producer_candidate_only（真实模式单测用）
    sd = tmp / 'source-decision-fixture.csv'
    lines = ['symbol,sha256,provenance_tier']
    for sym, p in prices.items():
        lines.append(f'{sym},{_sha(p)},producer_candidate_only')
    sd.write_text('\n'.join(lines) + '\n')
    return {'tmp': tmp, 'prices': prices, 'us_cal': cal, 'evidence': ev, 'sd': sd}


def syn_contract(fx, **over):
    c = {
        'data_mode': 'synthetic',
        'object_ref': 'candidate:lei.dual_ma.bull_state@draft-1',
        'candidate_card': {'path': CARD, 'sha256': _sha(REPO / CARD)},
        'theme': 'trend', 'type': 'state_signal', 'use': 'historical_description',
        'lookback': 20, 'e_offset': 1, 'x_offset': 22, 'regime': 'none',
        'evaluation_window': {'start': '2020-02-01', 'end': '2020-02-20'},
        'universe': {'universe_id': 'synthetic', 'members': ['510300', '159915', 'SPY', 'QQQ'],
                     'attribute_labels': {}},
        'target_basis': 'total_return_wealth',
        'data_identity': {
            sym: {'path': str(p), 'sha256': _sha(p), 'fetched_at': None,
                  'available_at': None, 'available_at_source': None,
                  'point_in_time_verified': False,
                  'date_range': ['2020-01-01', '2020-03-01'],
                  'price_basis_status': 'price_basis_verified',
                  'price_basis_evidence': {'path': str(fx['evidence']),
                                           'sha256': _sha(fx['evidence'])}}
            for sym, p in fx['prices'].items()
        },
        'calendar_identity': {
            'CN': {'source': None,
                   'synthetic_schedule': {'path': str(fx['us_cal']), 'sha256': _sha(fx['us_cal'])},
                   'exchange': 'SYNTHETIC', 'timezone': 'Asia/Shanghai',
                   'session_close': '15:00', 'half_day_close': None},
            'US': {'source': None,
                   'synthetic_schedule': {'path': str(fx['us_cal']), 'sha256': _sha(fx['us_cal'])},
                   'exchange': 'SYNTHETIC', 'timezone': 'America/New_York',
                   'session_close': '16:00',
                   'half_day_close': {'time': '13:00', 'timezone': 'America/New_York'}},
        },
        'source_decision': {'path': SD, 'sha256': _sha(REPO / SD)},
        'code_identity': {k: _sha(REPO / k) for k in REQUIRED_CODE},
        'standards': [{'path': s.split('@')[0], 'version': s.split('@')[1],
                       'sha256': _sha(REPO / s.split('@')[0])} for s in REQUIRED_STANDARDS],
        'research_cutoff': '2026-09-15T23:59:00+08:00',
    }
    c.update(over)
    return c


# ── R1 反例 ──────────────────────────────────────────────────────────

def test_r1_nonexistent_price_evidence_rejected(fx):
    c = syn_contract(fx)
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': '/definitely/not/real.json',
                                     'sha256': '0' * 64}
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_evidence_hash_mismatch_rejected(fx):
    c = syn_contract(fx)
    c['data_identity']['510300']['price_basis_evidence']['sha256'] = 'f' * 64
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_evidence_symbol_hash_contradiction_rejected(fx):
    c = syn_contract(fx)
    # 证据里510300的input_sha256被换成SPY的——矛盾必须拒绝
    d = json.loads(fx['evidence'].read_text())
    for rec in d['records']:
        if rec['symbol'] == '510300':
            rec['input_sha256'] = _sha(fx['prices']['SPY'])
    bad = fx['tmp'] / 'evidence_bad.json'
    bad.write_text(json.dumps(d))
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': str(bad), 'sha256': _sha(bad)}
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_synthetic_evidence_for_real_identity_rejected(fx):
    c = syn_contract(fx, data_mode='real')
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_real_mode_without_vendor_trace_stays_restricted(fx):
    # 真实身份+verified声明但无供应商可回查材料 → 降级restricted，不编造正例
    c = syn_contract(fx, data_mode='real',
                     source_decision={'path': str(fx['sd']), 'sha256': _sha(fx['sd'])})
    ev = fx['tmp'] / 'evidence_real.json'
    records = [{'symbol': sym, 'input_sha256': _sha(fx['prices'][sym]),
                'price_basis_status': 'price_basis_verified', 'data_mode': 'real',
                'sources': ['self-declared'], 'vendor_traceable': False}
               for sym in fx['prices']]
    ev.write_text(json.dumps({'schema': 'factor-unit-price-evidence/1', 'records': records}))
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': str(ev), 'sha256': _sha(ev)}
    got = validate_study_contract(c)
    assert got['status'] == 'restricted'
    assert any(v['target'] != 'pending_controller_freeze' for v in got['markets'].values())


def test_r1_source_decision_contradiction_rejected(fx):
    # 真实身份声称verified且供应商原件合法，来源裁定CSV仍记录
    # producer_candidate_only → 有效档位与CSV档位矛盾拒绝
    vendor = fx['tmp'] / 'vendor-resp.json'
    vendor.write_text(json.dumps({'records': [
        {'symbol': sym, 'input_sha256': _sha(p),
         'request_params': {'adjust': 'qfq', 'symbol': sym},
         'price_semantics': 'vendor_adjusted_close'}
        for sym, p in fx['prices'].items()]}))
    c = syn_contract(fx, data_mode='real',
                     source_decision={'path': str(fx['sd']), 'sha256': _sha(fx['sd'])})
    ev = fx['tmp'] / 'evidence_real_ok.json'
    records = [{'symbol': sym, 'input_sha256': _sha(fx['prices'][sym]),
                'price_basis_status': 'price_basis_verified', 'data_mode': 'real',
                'sources': ['sd'], 'vendor_traceable': True,
                'vendor_response_ref': {'path': str(vendor), 'sha256': _sha(vendor)}}
               for sym in fx['prices']]
    ev.write_text(json.dumps({'schema': 'factor-unit-price-evidence/1', 'records': records}))
    for e in c['data_identity'].values():
        e['price_basis_evidence'] = {'path': str(ev), 'sha256': _sha(ev)}
    with pytest.raises(ValueError, match='档位'):
        validate_study_contract(c)


def test_r1_missing_card_rejected(fx):
    c = syn_contract(fx)
    c['candidate_card'] = {'path': CARD, 'sha256': _sha(REPO / CARD)}
    c['candidate_card']['path'] = 'docs/experiments/raw/nowhere/candidate-card.md'
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_bad_card_hash_rejected(fx):
    c = syn_contract(fx)
    c['candidate_card']['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_standards_cut_to_one_rejected(fx):
    c = syn_contract(fx)
    c['standards'] = [c['standards'][0]]
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_standards_wrong_version_rejected(fx):
    c = syn_contract(fx)
    c['standards'][0]['version'] = '9.9'
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_standards_fingerprint_rejected(fx):
    c = syn_contract(fx)
    c['standards'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_available_at_garbage_rejected(fx):
    c = syn_contract(fx)
    e = c['data_identity']['SPY']
    e.update(available_at='garbageT', available_at_source='dummy',
             point_in_time_verified=True)
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_real_point_in_time_claim_rejected(fx):
    # 本B0不实现逐行真实历史资格：真实身份的point_in_time_verified=true一律拒绝
    c = syn_contract(fx, data_mode='real')
    e = c['data_identity']['SPY']
    e.update(available_at='2020-03-01T16:00:00-05:00',
             available_at_source='synthetic-fixture', point_in_time_verified=True)
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_calendar_missing_hash_rejected(fx):
    c = syn_contract(fx)
    for mkt in c['calendar_identity'].values():
        mkt['synthetic_schedule'].pop('sha256')
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_cn_calendar_content_checked(fx):
    # 真实CN日历逐日核验：评价窗落在1995（实际days从2019-09起）→ 逐日缺定义，给出缺失日期
    c = syn_contract(fx, evaluation_window={'start': '1995-01-01', 'end': '1995-03-31'})
    c['calendar_identity']['CN'] = {
        'source': {'path': CN_CAL, 'sha256': _sha(REPO / CN_CAL)},
        'synthetic_schedule': None, 'exchange': 'SZSE',
        'timezone': 'Asia/Shanghai', 'session_close': '15:00', 'half_day_close': None,
    }
    got = validate_study_contract(c)
    assert got['status'] == 'restricted'
    assert any('缺定义' in r and '1994-12-07' in r for r in got['reasons'])
    assert got['markets']['510300']['target'] == 'blocked'


def test_r1_cn_calendar_covering_window_qualifies(fx):
    # 合法对照：评价窗在CN日历实际覆盖内（2020-02）→ CN逐日核验通过
    c = syn_contract(fx)
    c['calendar_identity']['CN'] = {
        'source': {'path': CN_CAL, 'sha256': _sha(REPO / CN_CAL)},
        'synthetic_schedule': None, 'exchange': 'SZSE',
        'timezone': 'Asia/Shanghai', 'session_close': '15:00', 'half_day_close': None,
    }
    got = validate_study_contract(c)
    assert got['markets']['510300']['calendar'] == 'qualified'
    assert got['markets']['510300']['target'] == 'pending_controller_freeze' 


def test_r1_cn_calendar_wrong_market_rejected(fx):
    c = syn_contract(fx)
    c['calendar_identity']['US'] = {
        'source': {'path': CN_CAL, 'sha256': _sha(REPO / CN_CAL)},
        'synthetic_schedule': None, 'exchange': 'NYSE',
        'timezone': 'America/New_York', 'session_close': '16:00', 'half_day_close': None,
    }
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_calendar_missing_single_day_located(fx):
    # 合成日历删掉评价窗内一天 → 逐日检查给出确切缺失日期
    days = pd.date_range('2019-11-01', '2020-12-31', freq='D')
    df = pd.DataFrame({
        'session': days.strftime('%Y-%m-%d'),
        'close_at': days.tz_localize('America/New_York').strftime('%Y-%m-%dT16:00:00%z'),
    })
    df = df[df['session'] != '2020-02-10']
    cal2 = fx['tmp'] / 'us_calendar_gap.parquet'
    df.to_parquet(cal2)
    c = syn_contract(fx)
    for mkt in c['calendar_identity'].values():
        mkt['synthetic_schedule'] = {'path': str(cal2), 'sha256': _sha(cal2)}
    got = validate_study_contract(c)
    assert got['status'] == 'restricted'
    assert any('2020-02-10' in r for r in got['reasons'])


def test_r1_data_tamper_is_identity_error(fx):
    # 数据被篡改属身份错误（ValueError→CLI退出3），不得改称资料不足
    c = syn_contract(fx)
    c['data_identity']['510300']['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r1_legal_synthetic_positive_pending(fx):
    # 合法对照：合成身份全部合格 → 至少 pending（非一律拒绝）
    got = validate_study_contract(syn_contract(fx))
    assert got['status'] == 'ok'
    assert all(v['target'] == 'pending_controller_freeze'
               for v in got['markets'].values())


# ── R2 反例（主控30日例） ────────────────────────────────────────────

@pytest.fixture()
def valid_fixture():
    dates = pd.date_range('2020-01-01', periods=30, freq='D')
    schedule = pd.DataFrame({
        'session': dates,
        'close_at': dates.tz_localize('Asia/Shanghai') + pd.Timedelta(hours=15),
    })
    values = pd.DataFrame({'symbol': 'SYNTHETIC', 'session': dates,
                           'state': [None] * 5 + [True] * 25, 'I': [100.0] * 30})
    contract = {
        'data_mode': 'synthetic',
        'object_ref': 'candidate:lei.dual_ma.bull_state@draft-1',
        'lookback': 20, 'e_offset': 1, 'x_offset': 22,
        'evaluation_window': {'start': '2020-01-01', 'end': '2020-01-30'},
        'research_cutoff': '2030-01-01T15:00:00+08:00',
        'sparse_anchor_session': {'SYNTHETIC': '2020-01-06'},
        'sparse_step': 23,
    }
    return values, schedule, contract


def test_r2_cutoff_2019_gives_zero_mature(valid_fixture):
    values, schedule, contract = valid_fixture
    contract['research_cutoff'] = '2019-01-01T15:00:00+08:00'
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    assert out['comparison']['n'] == 0
    assert out['true_group']['n'] == 0 and out['false_group']['n'] == 0


def test_r2_cutoff_same_day_before_close_immature(valid_fixture):
    values, schedule, contract = valid_fixture
    # 首个已知观察t=5的标签结束=2020-01-28 15:00；截止提前到当日14:00 → 该行未成熟，
    # 且此前观察全部未知 → 成熟主比较为0
    contract['research_cutoff'] = '2020-01-28T14:00:00+08:00'
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    assert out['comparison']['n'] == 0


def test_r2_cutoff_exactly_at_close_mature(valid_fixture):
    values, schedule, contract = valid_fixture
    # 截止=2020-01-28 15:00 → 恰好只有t=5成熟（正好收盘=成熟）
    contract['research_cutoff'] = '2020-01-28T15:00:00+08:00'
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    assert out['comparison']['n'] == 1
    # 截止=2020-01-30 15:00 → t=5,6,7全部成熟
    contract['research_cutoff'] = '2020-01-30T15:00:00+08:00'
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    assert out['comparison']['n'] == 3


def test_r2_comparison_set_reconciles(valid_fixture):
    values, schedule, contract = valid_fixture
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    comp = out['comparison']
    assert comp['n'] == 3
    assert out['true_group']['n'] + out['false_group']['n'] == comp['n']
    # 背景样本（含未知状态）单列，不与比较集混称
    assert out['background']['n'] == 8
    assert out['background']['n_unknown_state'] == 5


def test_r2_string_false_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    values['state'] = 'false'
    with pytest.raises(ValueError):
        describe_states(values, schedule, contract)


def test_r2_int_state_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    values['state'] = 2
    with pytest.raises(ValueError):
        describe_states(values, schedule, contract)


def test_r2_all_dates_outside_schedule_structured_zero(valid_fixture):
    values, schedule, contract = valid_fixture
    values['session'] = values['session'] + pd.DateOffset(years=5)
    out = describe_states(values, schedule, contract)
    sym = out['symbols']['SYNTHETIC']
    assert sym['comparison']['n'] == 0
    assert sym['observations_outside_window'] == 30


def test_r2_empty_values_structured(valid_fixture):
    _, schedule, contract = valid_fixture
    empty = pd.DataFrame({'symbol': [], 'session': [], 'state': [], 'I': []})
    out = describe_states(empty, schedule, contract)
    assert out['symbols'] == {}


def test_r2_bad_i_values_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    for bad in (0.0, -1.0, np.inf):
        v = values.copy()
        v.loc[0, 'I'] = bad
        with pytest.raises(ValueError):
            describe_states(v, schedule, contract)


def test_r2_duplicate_key_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    values = pd.concat([values, values.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        describe_states(values, schedule, contract)


def test_r2_close_at_naive_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    schedule = schedule.copy()
    schedule['close_at'] = schedule['close_at'].dt.tz_localize(None)
    with pytest.raises(ValueError):
        describe_states(values, schedule, contract)


def test_r2_close_at_date_mismatch_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    schedule = schedule.copy()
    schedule.loc[0, 'close_at'] = schedule.loc[0, 'close_at'] + pd.Timedelta(days=1)
    with pytest.raises(ValueError):
        describe_states(values, schedule, contract)


def test_r2_sparse_step_invalid_rejected(valid_fixture):
    values, schedule, contract = valid_fixture
    for step in (0, -1, 1):
        contract['sparse_step'] = step
        with pytest.raises(ValueError):
            describe_states(values, schedule, contract)


def test_r2_sparse_anchor_from_contract(valid_fixture):
    values, schedule, contract = valid_fixture
    # 锚点=合同声明（2020-01-06=index5，首个已知状态），不按第一个已知状态动态改选
    contract['sparse_anchor_session'] = {'SYNTHETIC': '2020-01-03'}  # 已知状态前的锚
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    slots = out['sparse_view']['slots']
    assert slots[0]['session'] == '2020-01-03'
    assert slots[0]['state'] is None  # 该格未知→跳过不补选；下一格=01-26
    assert slots[1]['session'] == '2020-01-26'


def test_r2_missing_whole_day_breaks_segment(valid_fixture):
    values, schedule, contract = valid_fixture
    # 删掉2020-01-10整行（价格缺失）：状态段必须在缺日处断开
    v2 = values[values['session'] != pd.Timestamp('2020-01-10')]
    out = describe_states(v2, schedule, contract)['symbols']['SYNTHETIC']
    # true@5..9 与 true@11..17 是两段（缺日断开）
    assert out['state_segments']['true_segments'] >= 2


def test_r2_required_fields_no_silent_defaults(valid_fixture):
    values, schedule, contract = valid_fixture
    for key in ('research_cutoff', 'evaluation_window', 'sparse_anchor_session'):
        c2 = copy.deepcopy(contract)
        c2.pop(key)
        with pytest.raises(ValueError):
            describe_states(values, schedule, c2)


def test_r2_dst_and_half_day_close_at_used(valid_fixture):
    values, schedule, contract = valid_fixture
    # 半日市：某日close_at=13:00；截止定在当日14:00 → 该日为终点的标签未成熟
    contract['research_cutoff'] = '2020-01-28T14:00:00+08:00'
    schedule = schedule.copy()
    schedule.loc[27, 'close_at'] = schedule.loc[27, 'session'].tz_localize(
        'Asia/Shanghai') + pd.Timedelta(hours=13)
    out = describe_states(values, schedule, contract)['symbols']['SYNTHETIC']
    # t=5 终点=01-28 当日13:00收盘 ≤ 14:00截止 → 成熟；t=6 终点=01-29 15:00 → 未成熟
    assert out['comparison']['n'] == 1


# ── R3 反例 ──────────────────────────────────────────────────────────

def test_r3_required_code_keys_cannot_shrink(fx):
    c = syn_contract(fx)
    c['code_identity'] = {REQUIRED_CODE[0]: _sha(REPO / REQUIRED_CODE[0])}
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r3_missing_production_function_key_rejected(fx):
    c = syn_contract(fx)
    del c['code_identity']['src/lei_signal/rules/dual_ma.py']
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r3_missing_rules_ledger_key_rejected(fx):
    c = syn_contract(fx)
    del c['code_identity']['configs/rules.v2.yaml']
    with pytest.raises(ValueError):
        validate_study_contract(c)


def test_r3_required_keys_include_production_files():
    # 哈希核验在CLI层（集成测试覆盖退出3）；此处锁定必需集合内容不可裁剪
    from lei_signal.research.factor_unit.study_contract import REQUIRED_CODE_KEYS
    for must in ('src/lei_signal/rules/dual_ma.py', 'src/lei_signal/rules/lei_color.py',
                 'src/lei_signal/features/indicators.py',
                 'src/lei_signal/domain/rules_config.py', 'configs/rules.v2.yaml',
                 'scripts/check_factor_unit_readiness.py',
                 'src/lei_signal/research/trading_calendar.py'):
        assert must in REQUIRED_CODE_KEYS
