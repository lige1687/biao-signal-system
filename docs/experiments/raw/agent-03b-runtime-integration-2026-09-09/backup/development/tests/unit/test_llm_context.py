"""技术摘要全喂：覆盖全部约定维度；数据不足时显式占位不猜测。"""
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from lei_signal.api.labels import STRUCTURE_STATUS_CN
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.types import StructureStatus
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


def test_structures_live_only_and_capped():
    """Critical-1：只喂活跃结构；live 超 40 条时按可用日期取最新 40。"""
    ctx = build_discussion_context(_result(), None, [], [])
    live = [s for s in _result().structures if s.is_live]
    assert live, "fixture 应存在 live 结构"
    assert len(ctx["structures"]) == min(40, len(live))
    live_state_cns = {
        STRUCTURE_STATUS_CN[s.value]
        for s in (
            StructureStatus.CANDIDATE,
            StructureStatus.CONFIRMED,
            StructureStatus.ACTIVE,
        )
    }
    assert {s["state_cn"] for s in ctx["structures"]} <= live_state_cns
    # Minor-3：key_prices 剔除值为 None 的键
    assert all(
        v is not None for s in ctx["structures"] for v in s["key_prices"].values()
    )


def test_payload_budget_guard():
    """Important-1：序列化总量 < 30_000 字符（fixture 实测约 12KB，防未来膨胀）。"""
    ctx = build_discussion_context(_result(), None, [], [])
    assert len(json.dumps(ctx, ensure_ascii=False, default=str)) < 30_000


def test_volume_from_all_events():
    """Minor-1：量能维度从全部事件按 rule_id 过滤后截 10，不受 recent_events 截断影响。"""
    ctx = build_discussion_context(_result(), None, [], [])
    all_volume = [e for e in _result().events if "volume" in e.rule_id]
    n_in_recent = sum(1 for e in ctx["recent_events"] if "volume" in e["rule_id"])
    assert len(ctx["volume"]["events"]) >= n_in_recent  # 不得比 recent 里的量能条数还少
    assert len(ctx["volume"]["events"]) == min(10, len(all_volume))  # 全量过滤后截 10
