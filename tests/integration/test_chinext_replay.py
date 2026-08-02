"""修复 9：创业板 ETF 漏买案例的真实逐日黄金回放。

真实数据获取失败时（外部数据源限流）：
  - 不得把合成数据冒充真实数据。
  - 明确记录外部数据源失败。
  - 可以增加 CSV/Parquet 上传入口作为可复现实盘数据导入方式（已在 UI）。
  - 提交真实案例测试所需的合法行情快照或说明仍未完成，不能宣称真实验收通过。

此测试在两种模式下执行：
  1. 真实数据：若 tests/fixtures/159915_real.parquet 存在，则使用真实数据。
  2. 否则：使用 golden_bullish_engulfing 样的「反向底部 + 长周期空头」环境
     作为有据可查的离线回放。

两种模式都不假装是「真实回测验收」，仅作为可复现的离线回归。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.types import Stage
from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from tests.golden.fixtures import golden_bullish_engulfing

_FIXTURE_PATH = Path(__file__).parents[2] / "tests" / "fixtures" / "159915_real.parquet"


def _real_or_synthetic_data() -> pd.DataFrame:
    """如果存在真实数据快照则使用；否则明确标记为合成。"""
    if _FIXTURE_PATH.exists():
        df = pd.read_parquet(_FIXTURE_PATH)
        # 在 evidence 报告中：使用真实数据
        return df, "real_snapshot"
    # 没有真实数据快照：使用黄金样例，但标记为合成
    return golden_bullish_engulfing(), "synthetic_golden_fixture"


def test_chinext_etf_replay_engulfing_survives_long_bearish_trend() -> None:
    """核心回放：反包事件不被长周期 Block；候选期能继续推进。"""
    bars, source = _real_or_synthetic_data()
    frame = compute_long_trend(classify_colors(compute_features(bars)))
    # 验证：长周期空头（如果 source 是 real，data 可能不同）
    last = frame.iloc[-1]
    long_is_bearish = last["ema60"] < last["ema120"]

    result = analyze_bars("159915.SZ" if source == "real_snapshot" else "TEST", bars, \
    build_history=True)

    # 关键不变量
    bottoms = [s for s in result.bottoms if s.structure_type == "bullish_reversal_bottom"]
    assert bottoms, "必须有反包底部结构"
    if long_is_bearish:
        # 门禁 6：长周期空头环境下反包底部必须被记录
        assert all(b.status.value == "confirmed" for b in bottoms), "长周期空头下反包也必须确认"

    # 状态机：最终阶段应至少进入底部观察
    final = result.assessment
    assert final.stage in (Stage.BOTTOM_WATCH, Stage.STRUCTURE_CONFIRMED,
                            Stage.EARLY_STRENGTH, Stage.JOINT_CONFIRMED,
                            Stage.TREND_REINFORCED, Stage.RISK_WATCH,
                            Stage.KEY_RISK), (
        f"实际 {source} 模式下必须进入机会阶段，实际 stage={final.stage.value}"
    )

    # 数据来源标识
    assert source in ("real_snapshot", "synthetic_golden_fixture")
    if source == "synthetic_golden_fixture":
        # 必须明确标记是合成数据，不得冒充真实回测
        pytest.skip(
            "未找到真实 159915 数据快照：tests/fixtures/159915_real.parquet。\n"
            "本测试不假装是真实验收通过。\n"
            "请使用 CSV/Parquet 上传入口（修复 9）保存真实快照后再启用。"
        )


def test_chinext_etf_short_term_strength_kept_for_long_trend_lift() -> None:
    """短周期转强必须保留到长周期改善后升级（架构第 15 节漏信号案例）。"""
    from tests.golden.fixtures import golden_delayed_upgrade
    result = analyze_bars("159915.SZ", golden_delayed_upgrade(), build_history=True)
    # 找：状态从 早期转强/共同确认 升级到 趋势增强
    transitions = [
        (h.day, h.opportunity_stage) for h in result.history
        if h.opportunity_stage in (Stage.TREND_REINFORCED,)
    ]
    assert transitions, "长周期改善后必须升级到趋势增强"
    # 升级到 trend_reinforced 的日子之后仍然没有新 EMA20 交叉
    # 这部分断言在 test_delayed_upgrade.py 中完整覆盖
