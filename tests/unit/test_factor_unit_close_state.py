"""factor_unit.close_state 的反例先行测试。

期望全部来自本文件的独立参考实现/手算常数（不拿被测函数当期望）；
与旧调用链的比对只作观察输出。全部输入为合成数据。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_unit.close_state import compute_close_state

# ── 独立参考实现（不 import lei_signal） ─────────────────────────────

def ref_ema20(closes: np.ndarray) -> np.ndarray:
    """旧 seeded_ema 语义的独立实现：跳过前导NaN，首窗SMA作种子，α=2/21。"""
    out = np.full(len(closes), np.nan)
    first = 0
    while first < len(closes) and np.isnan(closes[first]):
        first += 1
    if len(closes) - first < 20:
        return out
    out[first + 19] = np.mean(closes[first : first + 20])
    a = 2.0 / 21.0
    for i in range(first + 20, len(closes)):
        out[i] = a * closes[i] + (1 - a) * out[i - 1]
    return out


def ref_sma20(closes: np.ndarray) -> np.ndarray:
    out = np.full(len(closes), np.nan)
    for i in range(19, len(closes)):
        w = closes[i - 19 : i + 1]
        out[i] = np.nan if np.isnan(w).any() else w.mean()
    return out


def rel_close(a: float, b: float, tol: float = 1e-10) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(a - b) <= tol * max(1.0, abs(b))


# ── 基本行为（任务书示例断言 + true/false 边界） ─────────────────────

def test_close_only_has_nullable_warmup():
    # 合成观察序号，非真实交易日历
    idx = pd.date_range('2020-01-01', periods=21, freq='D')
    got = compute_close_state(pd.Series([100.0] * 20 + [105.0], index=idx))
    assert got['state'].iloc[:20].isna().all()
    assert bool(got['state'].iloc[20]) is True


def test_twenty_rows_not_ready_and_column_set_exact():
    idx = pd.date_range('2020-01-01', periods=20, freq='D')
    got = compute_close_state(pd.Series([100.0] * 20, index=idx))
    assert got['state'].isna().all()
    assert (got['missing_reason'].iloc[:19] == 'warmup_not_ready').all()
    # 第20根：颜色仍未就绪（需21根），同样缺失而非false
    assert got['missing_reason'].iloc[19] == 'warmup_not_ready'
    assert list(got.columns) == [
        'close', 'ema20', 'sma20', 'close_lag20', 'signal_color', 'state',
        'missing_reason',
    ]


def test_false_cases_constant_and_below():
    idx = pd.date_range('2020-01-01', periods=21, freq='D')
    const = compute_close_state(pd.Series([100.0] * 21, index=idx))
    # 恒定：close=SMA20=EMA20（非严格高于），lag相等→非green → 有效false
    assert const['state'].iloc[20] is False or bool(const['state'].iloc[20]) is False
    below = compute_close_state(pd.Series([100.0] * 20 + [99.0], index=idx))
    assert bool(below['state'].iloc[20]) is False


def test_no_volume_or_ohlcv_needed():
    close = pd.Series(
        [100.0] * 20 + [105.0, 106.0], index=pd.date_range('2020-01-01', periods=22)
    )
    got = compute_close_state(close)  # 传入的就是纯 close Series
    assert bool(got['state'].iloc[21]) is True


# ── 独立手算期望（EMA种子/递推、SMA含当日） ─────────────────────────

def test_hand_computed_ema_sma_seed_and_recursion():
    closes = np.array([100.0, 101.0, 99.0, 102.0, 103.0] * 8, dtype=float)  # 40根
    idx = pd.date_range('2021-01-01', periods=len(closes), freq='D')
    got = compute_close_state(pd.Series(closes, index=idx))
    exp_ema = ref_ema20(closes)
    exp_sma = ref_sma20(closes)
    for i in range(len(closes)):
        assert rel_close(got['ema20'].iloc[i], exp_ema[i]), f'ema mismatch at {i}'
        assert rel_close(got['sma20'].iloc[i], exp_sma[i]), f'sma mismatch at {i}'
    # 种子行 = 首窗SMA；SMA含当日
    assert rel_close(got['ema20'].iloc[19], closes[:20].mean())
    assert rel_close(got['sma20'].iloc[19], closes[:20].mean())
    assert rel_close(got['sma20'].iloc[20], closes[1:21].mean())


def test_state_matches_independent_rule():
    closes = np.array([100.0, 101.0, 99.0, 102.0, 103.0, 98.0] * 6, dtype=float)
    idx = pd.date_range('2021-01-01', periods=len(closes), freq='D')
    got = compute_close_state(pd.Series(closes, index=idx))
    ema, sma = ref_ema20(closes), ref_sma20(closes)
    for i in range(len(closes)):
        reason = got['missing_reason'].iloc[i]
        st = got['state'].iloc[i]
        not_ready = (
            i < 20 or np.isnan(ema[i]) or np.isnan(ema[i - 1])
            or np.isnan(sma[i]) or np.isnan(sma[i - 1]) or i - 20 < 0
        )
        if not_ready:
            assert reason == 'warmup_not_ready' and pd.isna(st)
            continue
        lag = closes[i - 20]
        green = closes[i] > ema[i] and closes[i] > lag
        expected = (
            green and closes[i] > sma[i]
            and ema[i] > ema[i - 1] and sma[i] > sma[i - 1]
        )
        assert bool(st) == expected, f'state mismatch at {i}'


# ── 非法输入（任务书：重复/乱序、非正、无穷报错；NaN保留） ──────────

def test_invalid_inputs_raise():
    idx = pd.date_range('2020-01-01', periods=5, freq='D')
    dup = pd.Series([100.0] * 6, index=pd.DatetimeIndex(list(idx) + [idx[0]]))
    with pytest.raises(ValueError):
        compute_close_state(dup)
    unsorted = pd.Series([100.0] * 5, index=pd.DatetimeIndex(sorted(idx, reverse=True)))
    with pytest.raises(ValueError):
        compute_close_state(unsorted)
    with pytest.raises(ValueError):
        compute_close_state(pd.Series([100.0, 0.0, 100.0, 100.0, 100.0], index=idx))
    with pytest.raises(ValueError):
        compute_close_state(pd.Series([100.0, -1.0, 100.0, 100.0, 100.0], index=idx))
    with pytest.raises(ValueError):
        compute_close_state(pd.Series([100.0, np.inf, 100.0, 100.0, 100.0], index=idx))


def test_leading_and_internal_nan_semantics():
    # 前导NaN：按旧 seeded_ema 语义跳过——从首个有效值起算
    vals = [np.nan, np.nan] + [100.0] * 19 + [105.0, 106.0]
    got = compute_close_state(pd.Series(vals, index=pd.date_range('2020-01-01', periods=23)))
    exp_ema = ref_ema20(np.array(vals, dtype=float))
    assert rel_close(got['ema20'].iloc[21], exp_ema[21])  # 种子=首个有效值后第20根
    assert bool(got['state'].iloc[22]) is True
    # 内部NaN：旧EMA递推被污染→后续全部不可用，不跳过不重启
    poisoned = [100.0] * 10 + [np.nan] + [100.0] * 40
    got2 = compute_close_state(
        pd.Series(poisoned, index=pd.date_range('2020-01-01', periods=51))
    )
    assert got2['missing_reason'].iloc[10] == 'price_missing'
    later = got2.iloc[30:]
    assert later['state'].isna().all()
    assert (later['missing_reason'] == 'warmup_not_ready').all()
    # 绝不恢复：最后一行也不可用
    assert got2['missing_reason'].iloc[-1] == 'warmup_not_ready'


def test_price_missing_kept_not_dropped():
    vals = [100.0] * 19 + [np.nan] + [105.0, 106.0, 107.0]
    got = compute_close_state(pd.Series(vals, index=pd.date_range('2020-01-01', periods=23)))
    assert got['missing_reason'].iloc[19] == 'price_missing'
    assert pd.isna(got['state'].iloc[19])
    assert len(got) == 23  # 行保留，不删


# ── 前缀不变与缩放不变 ────────────────────────────────────────────────

def test_prefix_invariance_on_append():
    prefix = [100.0, 101.0, 99.0, 102.0, 103.0] * 6  # 30根
    idx = pd.date_range('2021-01-01', periods=45, freq='D')
    before = compute_close_state(pd.Series(prefix, index=idx[:30]))
    after = compute_close_state(pd.Series(prefix + [104.0] * 15, index=idx))
    for col in ('close', 'ema20', 'sma20', 'close_lag20', 'signal_color',
                'state', 'missing_reason'):
        b, a = before[col], after[col].iloc[:30]
        if b.dtype == object or col in ('signal_color', 'missing_reason'):
            assert (b.astype(str).values == a.astype(str).values).all(), col
        else:
            bb, aa = b.astype(float).values, a.astype(float).values
            same = (np.isnan(bb) & np.isnan(aa)) | (
                ~np.isnan(bb) & ~np.isnan(aa)
                & (np.abs(bb - aa) <= 1e-10 * np.maximum(1.0, np.abs(aa)))
            )
            assert same.all(), col


def test_scale_invariance_noncritical():
    base = [100.0, 101.0, 99.0, 102.0, 103.0] * 6 + [110.0]
    s = pd.Series(base, index=pd.date_range('2021-01-01', periods=31))
    scaled = compute_close_state(s * 100.0)
    normal = compute_close_state(s)
    for i in range(21, 31):
        if pd.isna(normal['state'].iloc[i]):
            continue
        # 非临界（close与均线差远大于容差）时布尔必须精确一致
        c = base[i]
        e, m = normal['ema20'].iloc[i], normal['sma20'].iloc[i]
        critical = (abs(c - e) <= 1e-6 * max(1.0, abs(c))) or (
            abs(c - m) <= 1e-6 * max(1.0, abs(c))
        )
        if not critical:
            assert bool(normal['state'].iloc[i]) == bool(scaled['state'].iloc[i]), i


# ── 与旧调用链（合成完整OHLCV）逐行比对 ─────────────────────────────

def test_line_by_line_match_with_old_chain_synthetic_ohlcv():
    from lei_signal.features.indicators import compute_features
    from lei_signal.rules.dual_ma import dual_ma_bull_state
    from lei_signal.rules.lei_color import classify_colors

    closes = [100.0, 101.0, 99.0, 102.0, 103.0, 98.0, 105.0, 97.0] * 10  # 80根
    idx = pd.date_range('2022-01-01', periods=len(closes), freq='D')
    bars = pd.DataFrame(
        {
            'open': closes,
            'high': [c + 1 for c in closes],
            'low': [c - 1 for c in closes],
            'close': closes,
            'volume': [1000.0] * len(closes),
        },
        index=idx,
    )
    old_feats = compute_features(bars)
    old_colored = classify_colors(old_feats)
    old_state = dual_ma_bull_state(old_colored)

    got = compute_close_state(pd.Series(closes, index=idx))
    diffs = []
    for i in range(len(closes)):
        tol_e = 1e-10 * max(1.0, abs(old_colored['ema20'].iloc[i]))
        if abs(got['ema20'].iloc[i] - old_colored['ema20'].iloc[i]) > tol_e:
            diffs.append((i, 'ema20'))
        tol_s = 1e-10 * max(1.0, abs(old_colored['sma20'].iloc[i]))
        if abs(got['sma20'].iloc[i] - old_colored['sma20'].iloc[i]) > tol_s:
            diffs.append((i, 'sma20'))
        if str(got['signal_color'].iloc[i]) != str(old_colored['signal_color'].iloc[i]):
            diffs.append((i, 'signal_color'))
        old_b = bool(old_state.iloc[i])
        new_b = False if pd.isna(got['state'].iloc[i]) else bool(got['state'].iloc[i])
        if new_b != old_b:
            diffs.append((i, 'state'))
    assert diffs == [], f'line-by-line diffs: {diffs[:10]}'


# ── R3 等价解释（同窗完整+种子后递推+非临界 ⇒ state ⟺ green ∧ C>SMA20） ──

def test_equivalence_green_and_above_sma_noncritical():
    closes = [100.0, 101.0, 99.0, 102.0, 103.0, 98.0, 105.0, 97.0] * 10
    got = compute_close_state(
        pd.Series(closes, index=pd.date_range('2022-01-01', periods=len(closes)))
    )
    for i in range(21, len(closes)):
        st = got['state'].iloc[i]
        if pd.isna(st):
            continue
        c = closes[i]
        e, m = got['ema20'].iloc[i], got['sma20'].iloc[i]
        tol = 1e-10 * max(1.0, abs(c))
        if abs(c - e) <= tol or abs(c - m) <= tol:
            continue  # 浮点临界：不作等价判定
        green = got['signal_color'].iloc[i] == 'green'
        assert bool(st) == (green and c > m), i


# ── 含分红缩放例：本轮未实现 → 显式 not applicable ────────────────────

def test_dividend_scaling_not_implemented():
    # R6：含现金分红的缩放小例本轮未实现（价格与每份分红同步缩放、
    # 拆分比例不随货币缩放）；A阶段仅验证纯价格缩放，不得声称分红缩放已验证。
    pytest.skip('分红消费未实现；实现前此用例不适用，不谎报覆盖')
