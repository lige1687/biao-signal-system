"""主控复核四类漏放的修复守卫（research-controller-fixes-2026-09-11）。

每项按「先复现 → 失败测试 → 最小修复 → 通过」执行。
本文件前四个测试即主控反例的固化：修复前全部失败，修复后全部通过。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research import data_quality as q
from lei_signal.research.data_snapshot import load_snapshot
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


@pytest.fixture(scope="module")
def full_calendar():
    return TradingCalendar.from_file(CALENDAR, PUB)


def _tampered_copy(tmp_path: Path) -> Path:
    copy = tmp_path / "snap"
    shutil.copytree(SNAPSHOT_V2, copy)
    target = copy / "normalized" / "510300.SS.csv"
    original = target.read_text(encoding="utf-8")
    tampered = original.replace("3.904", "3.905", 1)
    assert tampered != original, "篡改必须真实发生"
    target.write_text(tampered, encoding="utf-8")
    return copy


# ---------------------------------------------------------------------------
# 必修一：哈希核验失败仍被放行
# ---------------------------------------------------------------------------


def test_tampered_snapshot_cannot_be_relabelled_as_usable(tmp_path, full_calendar):
    """主控反例：verified=False 的快照，ranking 仍被判可用、require_use 放行。"""
    loaded = load_snapshot(_tampered_copy(tmp_path))
    assert loaded.verified is False
    assert loaded.hash_mismatches

    report = q.check_snapshot(
        loaded, calendar=full_calendar,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    assert report.verdict_for("ranking") == q.UNUSABLE, (
        "核验失败不能被重新标为正常可用"
    )
    assert "snapshot_integrity_failed" in {f.code for f in report.findings}
    # 两种绕过方式都必须失效
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking", allow_conditional=True)
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking", accept_structural=True)


def test_untampered_snapshot_still_works(tmp_path, full_calendar):
    """防止「一律拒绝」的假修复：未改动快照必须照常工作。"""
    loaded = load_snapshot(SNAPSHOT_V2)
    assert loaded.verified is True
    report = q.check_snapshot(
        loaded, calendar=full_calendar,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    assert "snapshot_integrity_failed" not in {f.code for f in report.findings}
    assert q.require_use(report, "description") == q.USABLE
    # 查看坏数据用于排查仍保留：load_snapshot 本身不因 verified=False 抛错
    loaded_bad = load_snapshot(_tampered_copy(tmp_path))
    assert loaded_bad.verified is False
    assert "510300.SS" in loaded_bad.frames  # 可查看，但不能正常研究使用


# ---------------------------------------------------------------------------
# 必修二：日历月份覆盖冒充逐日完整
# ---------------------------------------------------------------------------


def _calendar_with_missing_day(tmp_path: Path) -> TradingCalendar:
    """算法测试用合成日历（不是官方资料）：2026-01 已请求，但缺 2026-01-05。"""
    from datetime import date

    days = {}
    for d in range(1, 32):
        if d == 5:
            continue  # 故意漏掉 2026-01-05
        day = date(2026, 1, d)
        trading = day.weekday() < 5
        days[day.isoformat()] = {
            "is_trading_day": trading,
            "source_flag": "1" if trading else "0",
            "source_month": "2026-01",
        }
    p = tmp_path / "gap-cal.json"
    p.write_text(json.dumps({
        "authority": "exchange_official",   # 自报的资格标签
        "publisher": "合成测试日历",
        "months_requested": ["2026-01"],
        "months_failed": [],
        "days": days,
    }), encoding="utf-8")
    return TradingCalendar.from_file(p)


def test_month_requested_but_day_missing_is_not_complete(tmp_path):
    """主控反例：月份已请求但缺一天，coverage.complete 却为 True。"""
    cal = _calendar_with_missing_day(tmp_path)
    # status 对缺失日如实返回未知——这点原本就对
    assert cal.status("2026-01-05").status == "unknown"
    # 但 complete 必须为 False，并指出哪个不完整
    cov = cal.coverage("2026-01-01", "2026-01-31")
    assert cov.complete is False
    d = cov.to_dict()
    assert "2026-01" in d["day_incomplete_months"]


def test_quote_on_calendar_unknown_day_is_reported(tmp_path):
    """主控反例：含 2026-01-05 报价的输入，ranking 仍被判可用。"""
    cal = _calendar_with_missing_day(tmp_path)
    frames = {
        "510300.SS": pd.DataFrame(
            {"open": [4.0, 4.05], "high": [4.1, 4.15], "low": [3.9, 3.95],
             "close": [4.0, 4.05], "volume": [100, 100]},
            index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
        )
    }
    report = q.check_prices(
        frames, calendar=cal,
        evaluation_start="2026-01-01", evaluation_end="2026-01-31",
    )
    assert "quote_on_unknown_calendar_day" in {f.code for f in report.findings}
    assert report.verdict_for("ranking") != q.USABLE
    # 未知不能被当作休市，也不能悄悄消失
    assert cal.status("2026-01-05").status == "unknown"


def test_day_incomplete_month_downgrades_even_with_good_authority_string(tmp_path):
    """不能只凭对象存在或自报 exchange_official 就提升资格。"""
    cal = _calendar_with_missing_day(tmp_path)  # authority 自报 exchange_official
    frames = {
        "510300.SS": pd.DataFrame(
            {"open": [4.0], "high": [4.1], "low": [3.9], "close": [4.0], "volume": [100]},
            index=pd.to_datetime(["2026-01-02"]),
        )
    }
    report = q.check_prices(
        frames, calendar=cal,
        evaluation_start="2026-01-01", evaluation_end="2026-01-31",
    )
    assert "calendar_days_incomplete" in {f.code for f in report.findings}
    assert report.verdict_for("ranking") != q.USABLE


# ---------------------------------------------------------------------------
# 必修三：单产品缺报价被全池日期并集掩盖
# ---------------------------------------------------------------------------


def test_single_product_internal_gap_is_visible(full_calendar):
    """主控反例：删 510300 的 2023-02-02 报价，findings 前后完全相同。"""
    loaded = load_snapshot(SNAPSHOT_V2)
    frames = {s: f.copy() for s, f in loaded.frames.items()}
    before = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=full_calendar,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    assert not [
        f for f in before.findings
        if f.code == "product_internal_gap" and f.instrument == "510300.SS"
    ], "删除前 510300 不应已有内部缺口（复现前置条件）"
    frames["510300.SS"] = frames["510300.SS"].drop(index=pd.Timestamp("2023-02-02"))
    after = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=full_calendar,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    gap = [f for f in after.findings if f.code == "product_internal_gap"]
    assert gap, "单产品内部缺日报价必须可见，不能被全池并集掩盖"
    hit = [f for f in gap if f.instrument == "510300.SS"
           and "2023-02-02" in f.evidence.get("dates", [])]
    assert hit, f"必须定位到具体产品与日期，实际：{[g.evidence for g in gap][:2]}"
    # 缺口不自动等于错误，也不自动等于停牌：原因未确认
    assert hit[0].evidence.get("cause") == "unconfirmed"


class _Ns:
    """最小快照替身：只提供 check_snapshot 所需的属性。"""

    def __init__(self, frames, snapshot):
        self.frames = frames
        self.snapshot = snapshot


def test_late_first_quote_without_listing_evidence_stays_unknown(full_calendar):
    """「首个报价较晚」不能自动判为「晚上市、补不了的固有属性」。"""
    loaded = load_snapshot(SNAPSHOT_V2)
    report = q.check_snapshot(
        loaded, calendar=full_calendar,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False, "缺少上市资格证据时不得标为固有属性"
    # 因而不是固有属性，accept_structural 不得放行
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking", accept_structural=True)


def test_halt_explanation_must_match_product_and_date(full_calendar):
    """停牌解释必须匹配实际缺失的产品与日期，不能用数量够了就解释任意缺失。"""
    loaded = load_snapshot(SNAPSHOT_V2)
    frames = {s: f.copy() for s, f in loaded.frames.items()}
    frames["510300.SS"] = frames["510300.SS"].drop(index=pd.Timestamp("2023-02-02"))
    halts = [
        # 这条停牌是 512890 的 2021-10-22——产品与日期都对不上 510300 的 2023-02-02
        {"event_id": "512890-halt-2021-10-22", "symbol": "512890",
         "type": "trading_halt", "effective_date": "2021-10-22",
         "halt": {"start_date": "2021-10-22", "end_date": "2021-10-22"}},
    ]
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=full_calendar,
        actions=halts,
        evaluation_start="2019-09-02", evaluation_end="2026-06-30",
    )
    gap = next(f for f in report.findings
               if f.code == "product_internal_gap" and f.instrument == "510300.SS")
    assert "2023-02-02" in gap.evidence.get("dates", [])
    assert gap.evidence.get("cause") == "unconfirmed", (
        "错产品的停牌记录不得用来解释 510300 的缺失"
    )


# ---------------------------------------------------------------------------
# 必修四：公司行动身份和时间只做了表面检查
# ---------------------------------------------------------------------------


def _div(eid="510300-cash_dividend-2026-01-05", **kw):
    base = {
        "event_id": eid,
        "symbol": "510300",
        "type": "cash_dividend",
        "effective_date": "2026-01-05",
        "cash_per_unit": 0.03,
    }
    base.update(kw)
    return base


def test_action_symbol_with_wrong_exchange_suffix_is_rejected():
    """主控反例：symbol="510300.SZ" 时 attribution 仍 usable。

    510300 登记在上交所；.SZ 是交易所冲突，不得通过。
    """
    report = q.check_actions([_div(symbol="510300.SZ")], declared_symbols=["510300.SS"])
    assert report.verdict_for("attribution") == q.UNUSABLE
    assert "action_identity_conflict" in {f.code for f in report.findings}


def test_action_symbol_none_is_rejected():
    """主控反例：symbol=None 时 attribution 仍 usable。"""
    report = q.check_actions([_div(symbol=None)], declared_symbols=["510300.SS"])
    assert report.verdict_for("attribution") == q.UNUSABLE
    assert "action_missing_identity" in {f.code for f in report.findings}


def test_action_bad_effective_date_is_rejected():
    """主控反例：effective_date="garbage" 时 attribution 仍 usable。"""
    report = q.check_actions([_div(effective_date="garbage")], declared_symbols=["510300.SS"])
    assert report.verdict_for("attribution") == q.UNUSABLE
    assert "action_bad_date" in {f.code for f in report.findings}


def test_action_bad_available_at_is_rejected_even_when_required():
    """主控反例：available_at="garbage" 且 require_available_at=True 也挡不住。"""
    bad = _div(available_at="garbage")
    for strict in (False, True):
        report = q.check_actions([bad], declared_symbols=["510300.SS"],
                                 require_available_at=strict)
        assert report.verdict_for("attribution") == q.UNUSABLE, f"strict={strict}"
        assert "action_available_at_bad_format" in {f.code for f in report.findings}


def test_valid_available_at_must_be_timezone_aware():
    """带时区的合法 available_at 通过；无时区的按非法格式处理。"""
    ok = _div(available_at="2026-01-04T15:30:00+08:00")
    report = q.check_actions([ok], declared_symbols=["510300.SS"])
    assert "action_available_at_bad_format" not in {f.code for f in report.findings}

    naive = _div(available_at="2026-01-04 15:30:00")  # 无时区
    report2 = q.check_actions([naive], declared_symbols=["510300.SS"])
    assert "action_available_at_bad_format" in {f.code for f in report2.findings}


def test_available_at_after_effective_date_is_allowed_as_reconstruction():
    """生效后取得资料合法（历史修订性质），不得强制 available_at 早于生效日。"""
    late = _div(available_at="2026-01-10T09:00:00+08:00")  # 晚于 01-05 生效日
    report = q.check_actions([late], declared_symbols=["510300.SS"])
    assert "action_available_at_bad_format" not in {f.code for f in report.findings}
    # 但须如实标注：这不证明生效日之前已可知
    f = next((x for x in report.findings if x.code == "action_acquired_after_effective"), None)
    assert f is not None and f.level == q.INFO


def test_legal_actions_still_pass():
    """保留正向测试：合法行动在宽松模式下不被误判。"""
    good = [
        _div(available_at="2026-01-04T15:30:00+08:00"),
        {
            "event_id": "512890-split-2021-10-22",
            "symbol": "512890",
            "type": "split",
            "effective_date": "2021-10-22",
            "split_ratio": 2.0,
            "announcement_date": "2021-10-13",
        },
    ]
    report = q.check_actions(good, declared_symbols=["510300.SS", "512890.SS"])
    blocking = [f for f in report.findings if f.level == q.BLOCK]
    assert blocking == [], f"合法行动不应被阻断：{[(f.code, f.message) for f in blocking]}"
