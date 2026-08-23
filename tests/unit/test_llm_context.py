"""技术摘要全喂：覆盖全部约定维度；数据不足时显式占位不猜测。"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.plans.llm_context import build_discussion_context

FIXTURE = Path(__file__).resolve().parents[1] / "000300.SS.bars.parquet"


@lru_cache(maxsize=1)
def _result():
    # analyze_bars 对 1500 根 bar 耗时明显，整个模块只构造一次并复用。
    bars = pd.read_parquet(FIXTURE)
    return analyze_bars("000300.SS", bars)


def test_context_covers_all_dimensions():
    ctx = build_discussion_context(_result(), None, [], [])
    for key in ("symbol", "display_name", "as_of", "assessment", "dual_ma",
                "structures", "volume", "volume_profile", "macd",
                "recent_events", "buy_point_review", "plans"):
        assert key in ctx, f"缺维度 {key}"


def test_volume_profile_marked_proxy():
    ctx = build_discussion_context(_result(), None, [], [])
    vp = ctx["volume_profile"]
    assert vp is None or vp.get("proxy") is True  # 必须标注代理，不得冒充真实筹码


def test_recent_events_capped_at_20():
    ctx = build_discussion_context(_result(), None, [], [])
    assert len(ctx["recent_events"]) <= 20


def test_real_fields_not_silently_empty():
    """字段接地：结构状态/事件摘要必须来自真实字段，而非 getattr 空串兜底。"""
    ctx = build_discussion_context(_result(), None, [], [])
    assert ctx["structures"], "fixture 应存在结构"
    assert all(s["state_cn"] for s in ctx["structures"])
    assert ctx["recent_events"]
    assert all(e["summary_cn"] for e in ctx["recent_events"])
    # VolumeProfileProxy 有 val 字段（brief 裁定核实后一并输出）
    assert ctx["volume_profile"] is not None
    assert "val" in ctx["volume_profile"]
