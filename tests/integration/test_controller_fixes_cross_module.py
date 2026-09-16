"""跨模块守卫（research-controller-fixes-2026-09-11 §8）。

四个跨模块命题，各自对应一类「单点检查互相掩盖」的失败模式：
1. 失败加载结果不能正常放行；
2. 不完整日历不能被完整快照掩盖；
3. 错身份行动不能被正确价格身份掩盖；
4. 基础检查通过不能冒充动量定义绑定成功。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research import data_quality as q
from lei_signal.research import definitions as d
from lei_signal.research.data_snapshot import bind_definitions, load_snapshot
from lei_signal.research.trading_calendar import TradingCalendar

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_V2 = (
    ROOT / "docs/experiments/raw/research-identity-wiring-2026-09-10"
    / "canonical-snapshot-v2"
)
CALENDAR = (
    ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10"
    / "calendar-merged/calendar.json"
)
PUB = (
    ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10"
    / "publication-evidence.json"
)
ACTIONS = (
    ROOT
    / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation"
    / "action-sources/normalized-actions.json"
)


@pytest.fixture(scope="module")
def loaded():
    return load_snapshot(SNAPSHOT_V2)


@pytest.fixture(scope="module")
def cal():
    return TradingCalendar.from_file(CALENDAR, PUB)


def test_failed_load_cannot_pass_anywhere(tmp_path, cal):
    """1：verified=False 沿正常链路传到最后一关也必须拒绝。"""
    copy = tmp_path / "snap"
    shutil.copytree(SNAPSHOT_V2, copy)
    target = copy / "normalized" / "510300.SS.csv"
    original = target.read_text(encoding="utf-8")
    tampered = original.replace("3.904", "3.905", 1)
    assert tampered != original
    target.write_text(tampered, encoding="utf-8")

    bad = load_snapshot(copy)
    assert bad.verified is False
    report = q.check_snapshot(
        bad, calendar=cal,
        actions=json.loads(ACTIONS.read_text())["events"],
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    for use in q.USES:
        with pytest.raises(q.UseNotPermitted):
            q.require_use(report, use, allow_conditional=True,
                          accept_structural=True)


def test_incomplete_calendar_not_masked_by_complete_snapshot(loaded, tmp_path):
    """2：快照再完整，日历漏日也不能被掩盖。"""
    days = {
        "2026-01-02": {"is_trading_day": True, "source_flag": "1",
                       "source_month": "2026-01"},
        "2026-01-03": {"is_trading_day": False, "source_flag": "0",
                       "source_month": "2026-01"},
        # 故意漏 2026-01-05
    }
    for dnum in range(6, 32):
        day = f"2026-01-{dnum:02d}"
        wd = pd.Timestamp(day).weekday() < 5
        days[day] = {"is_trading_day": bool(wd), "source_flag": "1" if wd else "0",
                     "source_month": "2026-01"}
    p = tmp_path / "gap.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": ["2026-01"], "months_failed": [], "days": days,
    }), encoding="utf-8")
    gap_cal = TradingCalendar.from_file(p)

    frames = {
        "510300.SS": loaded.frames["510300.SS"].loc[
            (loaded.frames["510300.SS"].index >= "2026-01-02")
            & (loaded.frames["510300.SS"].index <= "2026-01-09")
        ]
    }
    assert pd.Timestamp("2026-01-05") in frames["510300.SS"].index
    report = q.check_prices(frames, calendar=gap_cal,
                            evaluation_start="2026-01-01",
                            evaluation_end="2026-01-31")
    assert report.verdict_for("ranking") != q.USABLE
    assert "quote_on_unknown_calendar_day" in {f.code for f in report.findings}


def test_bad_action_identity_not_masked_by_good_prices(loaded, cal):
    """3：价格身份全对，行动身份错了照样不能放行。"""
    actions = json.loads(ACTIONS.read_text())["events"]
    polluted = [*actions, {
        "event_id": "x-bad-identity", "symbol": "510300.SZ",   # 交易所冲突
        "type": "cash_dividend", "effective_date": "2026-01-05",
        "cash_per_unit": 0.03,
    }]
    report = q.check_snapshot(
        loaded, calendar=cal, actions=polluted,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    assert "action_identity_conflict" in {f.code for f in report.findings}
    assert report.verdict_for("attribution") == q.UNUSABLE
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "attribution", allow_conditional=True,
                      accept_structural=True)


def test_passing_basic_checks_does_not_satisfy_momentum_definition(loaded, cal):
    """4：基础格式检查全部通过，不等于满足 mixed.momentum.raw@1.0.0。

    该定义要的是 economic_index；名义价快照缺它，绑定必须继续拒绝。
    不改卡片要求来获得通过。
    """
    report = q.check_snapshot(
        loaded, calendar=cal,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    # 基础检查可以过（description/diagnostic）
    assert q.require_use(report, "description") == q.USABLE

    binding = bind_definitions(
        registry=d.load_registry(),
        refs=["mixed.momentum.raw@1.0.0"],
        purpose="description",
        snapshot=loaded.snapshot,
    )
    info = binding["bindings"]["mixed.momentum.raw@1.0.0"]
    assert info["resolved"] is True
    assert info["directly_satisfiable"] is False
    assert info["missing_fields"] == ["economic_index"], (
        "基础检查通过不能冒充定义绑定成功——economic_index 必须仍然缺"
    )
