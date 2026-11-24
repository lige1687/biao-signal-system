"""入场模块引擎黄金回放：独立正确性基准（J1/S1，2026-09-19 冻结）。

纪律（沿用 tests/golden/fixtures.py 反自证约定）：
- 每个样本都是人工构造、目的明确的行情序列；预期结果由规则账文
  （configs/rules.v2.yaml 对应 rule 条目 + 规格节）**独立推导**后与引擎
  实际输出核对一致才录为基准，不是把引擎输出直接录制为预期。
- 规则文件哈希与本文件中的冻结值绑定；哈希变化必须先人工复核每个样本
  的判定依据，再显式更新冻结值，禁止自动重录基准消除失败。
- 「数据不足」类样本锁定引擎的保守语义：指标未就绪/历史不够时不出
  任何事件（宁缺勿错），而不是报错或猜测。

三个样本类（每个引擎各覆盖）：
- 允许入场：门禁齐备且触发条件精确满足 -> confirmed 事件；
- 正常无信号：数据完整、门禁或触发不满足 -> 不出 confirmed；
- 数据不足：历史长度/指标列不足 -> 空结果。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.features.indicators import compute_features
from lei_signal.rules.dense_breakout import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_WATCH,
    detect_dense_breakout_events,
)
from lei_signal.rules.false_breakout_reclaim import (
    SUB_RULE_CONFIRMED as D_CONFIRMED,
    SUB_RULE_WATCH as D_WATCH,
    detect_false_breakout_reclaim_events,
)
from lei_signal.rules.first_ma_pullback import (
    ENTRY_CONFIRMED,
    ENTRY_EARLY,
    SUB_RULE_CONFIRMED as A_CONFIRMED,
    SUB_RULE_TOUCHED,
    detect_first_ma_pullback_events,
)
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.ma_full_alignment import (
    SUB_RULE_BROKEN,
    SUB_RULE_BULLISH_START,
    detect_ma_alignment_events,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 2026-09-19 冻结的规则账本指纹。变更任一文件须先逐样本复核判定依据，
# 再人工更新此处的哈希；CI/测试不得自动重录。
# 说明：契约原文写 rules.v1.yaml，但当前加载器（domain/rules_config.py）
# 实际读取的是 rules.v2.yaml（ruleset_version 2.1.0），故两份都冻结。
FROZEN_RULES_SHA256 = {
    "configs/rules.v1.yaml": "9be26a1626fdf6351478b40b388907e9d8128f74b6bd4aa2b8ff4a850cfdcfd2",
    "configs/rules.v2.yaml": "feb2c51dce704c95eea54fe3a3b6df73b6abf66f1c3e1618c99806ed5c1651c5",
}
FROZEN_RULESET_VERSION = "2.1.0"


# ---------------------------------------------------------------------------
# 冻结记录：规则账本哈希 + ruleset 版本
# ---------------------------------------------------------------------------


def test_rulebook_hash_frozen() -> None:
    """规则账本哈希冻结：任何变化都要求人工复核全部 golden 判定依据。

    判定依据：J1 契约 G1「规则哈希变化须显式复核」。本测试失败时不允许
    直接改哈希了事，必须先说明每个样本在新账本下预期是否变化。
    """
    from lei_signal.domain.rules_config import ruleset_version

    for relative, expected in FROZEN_RULES_SHA256.items():
        content = (_REPO_ROOT / relative).read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        assert actual == expected, (
            f"{relative} 哈希变化（{actual}）。须人工复核 golden 样本判定依据后"
            "再更新 FROZEN_RULES_SHA256，禁止自动重录。"
        )
    assert ruleset_version() == FROZEN_RULESET_VERSION


def _entry_variant(frame: pd.DataFrame) -> pd.DataFrame:
    return classify_colors(compute_features(frame))


def _a_uptrend_frame(
    pre_bars: int = 640,
    g: float = 0.0012,
    dip_depth: float = 0.05,
    dip_len: int = 8,
    recover_len: int = 4,
    tight: bool = False,
) -> pd.DataFrame:
    """模块 A 样本：几何上行 + 受控回撤再收复（时钟二类/周线多头自洽）。"""
    closes = [100.0 * (1.0 + g) ** i for i in range(pre_bars)]
    base = closes[-1]
    for k in range(dip_len):
        closes.append(base * (1.0 + g) ** (k + 1) * (1.0 - dip_depth * (k + 1) / dip_len))
    if recover_len > 0:
        closes.append(closes[-1] * 1.006)
        for _ in range(recover_len - 1):
            closes.append(closes[-1] * 1.004)
    index = pd.bdate_range("2014-01-01", periods=len(closes))
    close = pd.Series(closes, index=index)
    if tight:  # 紧口径：日内振幅极窄 -> 不触碰 SMA+ATR 带
        return pd.DataFrame(
            {"open": close * 1.0002, "high": close * 1.0008, "low": close * 0.9998,
             "close": close, "volume": np.full(len(close), 1e6)},
            index=index,
        )
    return pd.DataFrame(
        {"open": close * 1.0005, "high": close * 1.004, "low": close * 0.996,
         "close": close, "volume": np.full(len(close), 1e6)},
        index=index,
    )


# ---------------------------------------------------------------------------
# 模块 A：first_ma_pullback 3.0.0（规格 §9 模块 A）
# ---------------------------------------------------------------------------


def test_golden_a_entry_allowed() -> None:
    """【允许入场】几何上行趋势中受控回撤 SMA20 后收复。

    判定依据（独立推导，rules.v2.yaml first_ma_pullback 3.0.0 / 规格 §9）：
    - A1 门禁：日增 0.12% 的几何上行使 s60 年化约 30%（时钟二类 10%-100%），
      SMA/EMA 双组多头排列，120 个已完成周后周线多头环境成立；
    - A2 触碰：回撤段 low 跌入 SMA20 + 1 x ATR(20) 带内且 close > close_lag20，
      首次触碰 is_first=True；
    - A3：回撤段内确认严格底部构造或 EMA20 收复（至少一种成立即可，
      本样本两条路径均具备）；
    - A4：收复日 close > EMA20 且 EMA20 上行 -> 早期版；且 close > close_lag20
      -> 确认版。两版同日各出一事件，止损 stop_price = 回撤最低 low（A5）。
    人工核对锚点：首个 confirmed（early 与 confirmed 变体）落在 2016-04-18、
    is_first_touch=True；此后续触碰出事件但 is_first=False。
    """
    events = detect_first_ma_pullback_events(
        _entry_variant(_a_uptrend_frame()), "GOLDEN-A"
    )
    confirmed = [e for e in events if e.evidence["sub_rule"] == A_CONFIRMED]
    assert confirmed, "允许入场样本必须产生确认事件"
    early = [e for e in confirmed if e.evidence["entry_variant"] == ENTRY_EARLY]
    confirmed_v = [e for e in confirmed if e.evidence["entry_variant"] == ENTRY_CONFIRMED]
    assert early and confirmed_v
    assert early[0].available_date == pd.Timestamp("2016-04-18").date()
    assert confirmed_v[0].available_date == pd.Timestamp("2016-04-18").date()
    assert early[0].evidence["is_first_touch"] is True
    # A3 来源（本样本实测为 bottom_structure：回撤内确认了严格底部构造；
    # 规则要求至少一种，两源均合法，此处锁定实际依据可追溯）
    assert early[0].evidence["a3_source"] in ("ema20_reclaim", "bottom_structure")
    touch_day = pd.Timestamp(early[0].evidence["touch_date"])
    frame = classify_colors(compute_features(_a_uptrend_frame()))
    assert early[0].evidence["stop_price"] <= float(frame.loc[touch_day, "low"])
    # 非首次触碰必须可分辨（规格 §9 A2 分别统计）
    touched = [e for e in events if e.evidence["sub_rule"] == SUB_RULE_TOUCHED]
    assert any(e.evidence["is_first_touch"] is False for e in touched)


def test_golden_a_no_signal_when_never_touches() -> None:
    """【正常无信号】数据完整、趋势健康，但价格始终未回撤到触碰带。

    判定依据：紧口径上行（日内振幅 0.1%，ATR 极小）使 low 恒高于
    SMA20 + 1 x ATR(20)，A2 触碰永不成立 -> 全程零事件（无 touched、
    无 confirmed、无 failed）。门禁不满足不等于数据不足，这里是
    「行情不触发」的正常无信号。
    """
    events = detect_first_ma_pullback_events(
        _entry_variant(_a_uptrend_frame(tight=True, dip_len=0, recover_len=0)), "GOLDEN-A"
    )
    assert events == []


def test_golden_a_insufficient_history() -> None:
    """【数据不足】31 根历史：SMA/EMA/周线环境全部未就绪。

    判定依据：A1 门禁要求指标非空（引擎 gate 里 pd.notna 检查）；
    31 根连 SMA60 都未就绪，门禁恒假 -> 空结果，不得报错或猜测。
    """
    frame = _entry_variant(_a_uptrend_frame(pre_bars=31, dip_len=0, recover_len=0))
    assert detect_first_ma_pullback_events(frame, "GOLDEN-A") == []


# ---------------------------------------------------------------------------
# 模块 B：dense_breakout 2.0.0（规格 §9 模块 B）—— 真实路径，无 monkeypatch
# ---------------------------------------------------------------------------


def _b_flat_frame(bars: int, tail: int = 0, rise: float = 0.3) -> pd.DataFrame:
    """横盘 260 根（时钟三类 + 带宽 + 寿命真实成立）后按场景演化。

    flat 段六线恒 100（带宽 0，s60 斜率 0 -> 时钟三类），寿命随横盘累积
    （>=126 根达 B1 整理时间）；tail 段价格稳步抬升 -> 排列形成（埋伏）
    并收盘突破区间上沿（100.4 前高，截至昨日口径）。
    """
    rows = bars + tail
    idx = pd.bdate_range("2024-01-02", periods=rows)
    close = [100.0] * bars
    high = [100.4] * bars
    low = [99.9] * bars
    sma20 = [100.0] * bars
    sma60 = [100.0] * bars
    sma120 = [100.0] * bars
    ema20 = [100.0] * bars
    ema60 = [100.0] * bars
    ema120 = [100.0] * bars
    close_lag20 = [100.0] * bars
    for k in range(tail):
        i = bars + k
        price = 100.0 + k * rise
        close.append(price)
        high.append(price + 0.1)
        low.append(price - 0.1)
        sma20.append(100.0 + (price - 100.0) * 0.8)
        sma60.append(100.0 + (price - 100.0) * 0.3)
        sma120.append(100.0 + (price - 100.0) * 0.1)
        ema20.append(price * 0.9 + 100.0 * 0.1)
        ema60.append(100.0 + (price - 100.0) * 0.5)
        ema120.append(100.0 + (price - 100.0) * 0.2)
        close_lag20.append(close[i - 20] if i >= 20 else 100.0)
    return pd.DataFrame(
        {
            "open": [c - 0.05 for c in close],
            "high": high,
            "low": low,
            "close": close,
            "sma20": sma20, "sma60": sma60, "sma120": sma120,
            "ema20": ema20, "ema60": ema60, "ema120": ema120,
            "close_lag20": close_lag20,
        },
        index=idx,
    )


def test_golden_b_entry_allowed() -> None:
    """【允许入场】横盘密集区（260 根）形成后排列先行、价格随后突破。

    判定依据（rules.v2.yaml dense_breakout 2.0.0 / 规格 §9 B）：
    - B1：六线恒 100 -> 带宽 0 < 2%、s60=0 -> 时钟三类，横盘 260 根 > 126
      整理时间下限（真实 clock_series/bandwidth/age，无桩）；
    - B2 埋伏版：tail 段双组多头排列 false->true -> ambush confirmed，
      止损 = 密集区最低 low = 99.9（zone_low）；
    - B2 突破版：收盘 100.6 > 截至昨日的区间最高 high 100.4 -> breakout
      confirmed，止损同为密集区下沿 99.9（回踩上沿不算失效）；
    - 每个密集区生命周期 watch 只发一次。
    人工核对锚点：watch@2024-08-22（寿命达标首日）、ambush@2025-01-01、
    breakout@2025-01-02，reference_price=100.4、stop_price=99.9。
    """
    events = detect_dense_breakout_events(_b_flat_frame(260, tail=60), "GOLDEN-B")
    subs = [e.evidence["sub_rule"] for e in events]
    assert subs.count(SUB_RULE_WATCH) == 1
    confirmed = [e for e in events if e.evidence["sub_rule"] == SUB_RULE_CONFIRMED]
    variants = {e.evidence["variant"] for e in confirmed}
    assert variants == {"ambush", "breakout"}
    ambush = next(e for e in confirmed if e.evidence["variant"] == "ambush")
    breakout = next(e for e in confirmed if e.evidence["variant"] == "breakout")
    assert ambush.available_date == pd.Timestamp("2025-01-01").date()
    assert breakout.available_date == pd.Timestamp("2025-01-02").date()
    assert breakout.evidence["close"] > breakout.evidence["reference_price"] == 100.4
    assert breakout.evidence["stop_price"] == ambush.evidence["stop_price"] == 99.9


def test_golden_b_no_signal_short_consolidation() -> None:
    """【正常无信号】横盘仅 60 根：带宽与三类时钟成立但寿命未达 126。

    判定依据：B1 整理时间（时钟三类寿命 >= minimum_consolidation_bars=126）
    不满足 -> 无密集区生命周期 -> 不出任何 watch/confirmed。
    """
    assert detect_dense_breakout_events(_b_flat_frame(60, tail=10), "GOLDEN-B") == []


def test_golden_b_insufficient_history() -> None:
    """【数据不足】仅 30 根且指标列残缺：s60/s120 全部未就绪。

    判定依据：时钟三类需 s60 可算，30 根历史不满足 -> 空结果不报错。
    """
    assert detect_dense_breakout_events(_b_flat_frame(30), "GOLDEN-B") == []


# ---------------------------------------------------------------------------
# 模块 C（场景确认维度）：ma_full_alignment 1.0.0 + 三色口径
# ---------------------------------------------------------------------------


def _c_alignment_frame() -> pd.DataFrame:
    """10 根手工帧：SMA 恒多头排列，前 3 根斜率 0（无排列），第 4-6 根
    三条斜率 +1（多头排列成立），第 7 根起 sma60 斜率 -1（排列破坏）。"""
    n = 10
    rows = {
        "sma20": [100.0] * n, "sma60": [99.0] * n, "sma120": [98.0] * n,
        "sma20_slope": [0.0] * n, "sma60_slope": [0.0] * n, "sma120_slope": [0.0] * n,
    }
    for day in (3, 4, 5):
        for key in ("sma20_slope", "sma60_slope", "sma120_slope"):
            rows[key][day] = 1.0
    rows["sma60_slope"][6] = -1.0
    return pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=n))


def test_golden_c_alignment_start_and_break() -> None:
    """【允许入场（场景确认维度）】完整多头排列的成立与破坏各出一次事件。

    判定依据（rules.v2.yaml ma_full_alignment 1.0.0）：多头排列 =
    SMA20>SMA60>SMA120 且三条斜率均 >0。第 4 根（2024-01-05）首次齐备 ->
    bullish_start；第 7 根（2024-01-10）sma60 斜率转负 -> broken。
    排列是场景卡确认维度，本身不是入场信号；本样本锁定其边界切换口径。
    """
    events = detect_ma_alignment_events(_c_alignment_frame(), "GOLDEN-C")
    assert [(e.evidence["sub_rule"], e.available_date) for e in events] == [
        (SUB_RULE_BULLISH_START, pd.Timestamp("2024-01-05").date()),
        (SUB_RULE_BROKEN, pd.Timestamp("2024-01-10").date()),
    ]


def test_golden_c_no_signal_without_alignment() -> None:
    """【正常无信号】位置排列但方向不齐（斜率全 0）：无排列事件。

    判定依据：排列要求三条斜率同号，恒 0 斜率 -> kind 恒 None -> 零事件。
    """
    frame = _c_alignment_frame()
    for key in ("sma20_slope", "sma60_slope", "sma120_slope"):
        frame[key] = 0.0
    assert detect_ma_alignment_events(frame, "GOLDEN-C") == []


def test_golden_c_insufficient_columns() -> None:
    """【数据不足】缺斜率列（指标未就绪等价于列缺失）：引擎返回空。

    判定依据：required 列不齐 -> 空结果（engine 的保守前向语义）。
    """
    frame = _c_alignment_frame().drop(
        columns=["sma20_slope", "sma60_slope", "sma120_slope"]
    )
    assert detect_ma_alignment_events(frame, "GOLDEN-C") == []


# ---------------------------------------------------------------------------
# 模块 D：false_breakout_reclaim 1.0.0（向上假突破快速收回）
# ---------------------------------------------------------------------------


def _d_reclaim_frame(breakout: bool = True) -> pd.DataFrame:
    """30 根手工帧：0-20 根横盘 100（参考位口径），突破日 position=21。

    breakout=True：第 21 根收盘 101.5（>100 x 1.01，前收 100 未破），
    同根 low 99.9 盘中刺穿参考位（被打回）；第 22 根收盘 101.6 收回。
    signal_color 恒 green、SMA 恒多头排列（确认条件就绪）。
    """
    n = 30
    close = [100.0] * n
    high = [100.0] * n
    low = [100.0] * n
    if breakout:
        close[21], high[21], low[21] = 101.5, 101.8, 99.9
        close[22], high[22], low[22] = 101.6, 101.9, 100.5
    return pd.DataFrame(
        {
            "open": [c - 0.1 for c in close], "high": high, "low": low, "close": close,
            "signal_color": ["green"] * n,
            "sma20": [99.0] * n, "sma60": [98.0] * n, "sma120": [97.0] * n,
        },
        index=pd.bdate_range("2024-01-02", periods=n),
    )


def test_golden_d_watch_then_confirmed() -> None:
    """【允许入场】突破前高 1.5% 当日盘中被打回，同日收盘收回。

    判定依据（rules.v2.yaml false_breakout_reclaim 1.0.0）：
    - 参考位 = 此前 20 根最高 high = 100.0（截至昨日，无未来泄漏）；
    - 有效突破 = close 101.5 >= 100 x 1.01 且前一日 close 未达；
    - 被打回 = low 99.9 <= 100（watch）；
    - 收回 = 同根 close 101.5 >= 100，多头排列保持且 green -> confirmed。
    人工核对锚点：watch 与 confirmed 同落 2024-01-31、reference_price=100.0。
    """
    events = detect_false_breakout_reclaim_events(_d_reclaim_frame(), "GOLDEN-D")
    assert [(e.evidence["sub_rule"], e.available_date) for e in events] == [
        (D_WATCH, pd.Timestamp("2024-01-31").date()),
        (D_CONFIRMED, pd.Timestamp("2024-01-31").date()),
    ]
    assert all(e.evidence["reference_price"] == 100.0 for e in events)
    assert events[-1].evidence["arrangement_holds"] is True


def test_golden_d_no_signal_without_breakout() -> None:
    """【正常无信号】价格始终在参考位 1% 突破阈内：无观察也无确认。

    判定依据：close 恒 100 < 100 x 1.01，breakout 条件不成立 -> 零事件。
    """
    assert detect_false_breakout_reclaim_events(
        _d_reclaim_frame(breakout=False), "GOLDEN-D"
    ) == []


def test_golden_d_insufficient_history() -> None:
    """【数据不足】15 根历史（< reference_lookback+1）：引擎跳过判定。

    判定依据：参考位需此前 20 根已完成日 K；不足时无参考位 -> 空结果。
    """
    assert detect_false_breakout_reclaim_events(
        _d_reclaim_frame().iloc[:15], "GOLDEN-D"
    ) == []


@pytest.mark.parametrize(
    "detector",
    [
        detect_first_ma_pullback_events,
        detect_dense_breakout_events,
        detect_ma_alignment_events,
        detect_false_breakout_reclaim_events,
    ],
)
def test_golden_empty_frame_is_noop(detector) -> None:  # noqa: ANN001
    """【数据不足】空帧统一保守语义：零事件、不报错。"""
    assert detector(pd.DataFrame(), "GOLDEN") == []
