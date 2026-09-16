"""主控复核剩余三处遗漏的修复守卫（research-controller-fixes-2026-09-11-02）。

每项：独立期望值 → 失败测试 → 最小修复 → 通过。
本文件的反例测试修复前应全部失败。
"""
from __future__ import annotations

import json
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
def loaded():
    return load_snapshot(SNAPSHOT_V2)


@pytest.fixture(scope="module")
def cal():
    return TradingCalendar.from_file(CALENDAR, PUB)


class _Ns:
    def __init__(self, frames, snapshot):
        self.frames = frames
        self.snapshot = snapshot
        self.verified = True
        self.hash_mismatches = ()


def _gap_frames(loaded, symbol="510300.SS", day="2024-02-02"):
    frames = {s: f.copy() for s, f in loaded.frames.items()}
    frames[symbol] = frames[symbol].drop(index=pd.Timestamp(day))
    return frames


def _halt(symbol, start, end, **kw):
    rec = {
        "event_id": f"{symbol}-halt-{start}",
        "symbol": symbol,
        "type": "trading_halt",
        "effective_date": start,
        "halt": {"start_date": start, "end_date": end},
    }
    rec.update(kw)
    return rec


# ===========================================================================
# 一、非法停牌记录先被消费，排序仍获放行
# ===========================================================================


def test_unexplained_gap_keeps_ranking_limited(loaded, cal):
    """前置：无停牌记录时缺口未解释，ranking 不得可用。"""
    frames = _gap_frames(loaded)
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal,
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    assert report.verdict_for("ranking") != q.USABLE
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking")
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking", accept_structural=True)


def test_wrong_exchange_halt_cannot_explain_gap(loaded, cal):
    """主控反例 1：symbol="510300.SZ" 的停牌记录不得解释 510300.SS 的缺口。"""
    frames = _gap_frames(loaded)
    halts = [_halt("510300.SZ", "2024-02-02", "2024-02-02")]
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=halts,
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    # 行动校验照常报告身份冲突
    assert "action_identity_conflict" in {f.code for f in report.findings}
    # 但缺口不得因此变成已解释
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert "2024-02-02" in gap.evidence.get("dates", [])
    assert gap.evidence.get("cause") == "unconfirmed"
    # 排序不得升级为可用
    assert report.verdict_for("ranking") != q.USABLE
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking")
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking", accept_structural=True)


def test_account_event_halt_cannot_explain_gap(loaded, cal):
    """主控反例 1b：带 amount 账户字段的停牌记录同样不得被消费。"""
    frames = _gap_frames(loaded)
    halts = [_halt("510300", "2024-02-02", "2024-02-02",
                   account_id="E11", event="trading_halt", amount=0)]
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=halts,
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    assert "events_passed_as_actions" in {f.code for f in report.findings}
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert "2024-02-02" in gap.evidence.get("dates", [])
    assert gap.evidence.get("cause") == "unconfirmed"
    assert report.verdict_for("ranking") != q.USABLE


def test_conflicting_duplicate_halt_cannot_explain_gap(loaded, cal):
    """冲突重复的记录同样不得作为解释证据。"""
    frames = _gap_frames(loaded)
    a = _halt("510300", "2024-02-02", "2024-02-02")
    b = _halt("510300", "2024-02-02", "2024-02-02")
    b["halt"]["end_date"] = "2024-02-03"  # 同 event_id 但内容冲突
    b["event_id"] = a["event_id"]
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=[a, b],
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert gap.evidence.get("cause") == "unconfirmed"
    assert report.verdict_for("ranking") != q.USABLE


def test_inverted_halt_range_cannot_explain_gap(loaded, cal):
    """非法/倒置的停牌日期区间不得作为解释证据。"""
    frames = _gap_frames(loaded)
    halts = [_halt("510300", "2024-02-05", "2024-02-02")]  # start > end
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=halts,
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert gap.evidence.get("cause") == "unconfirmed"
    assert report.verdict_for("ranking") != q.USABLE


def test_garbage_halt_dates_cannot_explain_gap(loaded, cal):
    """halt.start_date/end_date 非法时同样不得消费（不能只验顶层日期）。"""
    frames = _gap_frames(loaded)
    bad = _halt("510300", "garbage", "also-garbage")
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=[bad],
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    assert "action_bad_date" in {f.code for f in report.findings}
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert gap.evidence.get("cause") == "unconfirmed"
    assert report.verdict_for("ranking") != q.USABLE


def test_right_product_wrong_date_cannot_explain_gap(loaded, cal):
    """正确产品、但日期对不上的停牌，不得解释缺口。"""
    frames = _gap_frames(loaded)
    halts = [_halt("510300", "2024-02-03", "2024-02-03")]  # 缺口是 02-02
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=halts,
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert "2024-02-02" in gap.evidence.get("dates", [])
    assert gap.evidence.get("cause") == "unconfirmed"


def test_legal_halt_explains_with_traceable_reference(loaded, cal):
    """正向：合法停牌可解释，且解释引用可追溯（event_id）。

    同时：这不等于证明当时可交易——available_at 缺失须分别说明。
    """
    frames = _gap_frames(loaded)
    halts = [_halt("510300", "2024-02-02", "2024-02-02")]
    report = q.check_snapshot(
        _Ns(frames, loaded.snapshot), calendar=cal, actions=halts,
        evaluation_start="2024-02-01", evaluation_end="2024-02-05",
    )
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert "2024-02-02" in gap.evidence.get("explained_by_halt", [])
    refs = gap.evidence.get("explained_by", [])
    assert refs and all(r.get("event_id") for r in refs), (
        "解释必须保留可追溯引用（event_id）"
    )
    assert "available_at" not in halts[0], "不得为历史日期解释补造 available_at"


# ===========================================================================
# 二、listing_evidence 仍只是非空开关
# ===========================================================================


def _late_pool():
    days = ["2026-06-01", "2026-06-02"]
    early = ["2026-05-28", "2026-05-29", *days]
    good = "510300.SS"
    late = "512890.SS"
    def fr(ds, closes):
        return pd.DataFrame(
            {"open": closes, "high": [c + .1 for c in closes],
             "low": [c - .1 for c in closes], "close": closes,
             "volume": [100.0] * len(ds)},
            index=pd.to_datetime(ds))
    return {good: fr(early, [4.0, 4.05, 4.1, 4.15]), late: fr(days, [1.0, 1.1])}, late


def _check_with_evidence(evidence):
    frames, late = _late_pool()
    return q.check_prices(
        frames,
        evaluation_start="2026-05-28",
        evaluation_end="2026-06-02",
        calendar=_mini_calendar(),
        listing_evidence=evidence,
    )


def _mini_calendar():
    import calendar as _c
    from datetime import date
    days = {}
    for m in (5, 6):
        for d in range(1, _c.monthrange(2026, m)[1] + 1):
            day = date(2026, m, d)
            tr = day.weekday() < 5
            days[day.isoformat()] = {
                "is_trading_day": tr,
                "source_flag": "1" if tr else "0",
                "source_month": f"2026-{m:02d}",
            }
    return TradingCalendar({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": ["2026-05", "2026-06"], "months_failed": [],
        "days": days,
    })


def test_dummy_source_string_is_not_evidence():
    """主控反例 2a：{"source": "dummy"} 不得标为结构属性。"""
    _, late = _late_pool()
    report = _check_with_evidence({late: {"source": "dummy"}})
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"


def test_contradicting_listing_date_is_not_evidence():
    """主控反例 2b：评价期前已上市，不能解释评价期后才有报价。"""
    _, late = _late_pool()
    report = _check_with_evidence(
        {late: {"listing_date": "2000-01-01",
                "source": "contradicts-late-listing"}}
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"


def test_listing_after_first_quote_is_rejected():
    """上市日期晚于首个报价，自相矛盾，不得接受。"""
    _, late = _late_pool()
    report = _check_with_evidence(
        {late: {"listing_date": "2026-07-01", "source": "合成证据"}}
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False


def test_listing_with_residual_gap_stays_unconfirmed():
    """上市日期非法/来源不合格时同样保持未确认（残余分支的专项见
    test_controller_fixes_round3.py::test_r3_residual_reason_must_be_residual_not_early_listing）。"""
    _, late = _late_pool()
    report = _check_with_evidence(
        # 上市 2026-05-20，但首报价 2026-06-01：中间有交易日没报价
        {late: {"listing_date": "2026-05-20", "source": "合成证据"}}
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"


def test_coherent_synthetic_listing_evidence_is_structural(tmp_path):
    """正向：可回查且产品/日期一致的合成资格记录允许标为结构属性——

    只验证算法，合成来源不是真实市场资格证明。
    """
    import hashlib
    import json

    _, late = _late_pool()
    doc = tmp_path / "listing-qualification.json"
    doc.write_text(json.dumps({
        "symbol": "512890", "listing_date": "2026-06-01",
        "qualification": "synthetic_algorithm_test",
        "note": "合成资格记录，仅用于算法测试",
    }, ensure_ascii=False), encoding="utf-8")
    report = _check_with_evidence(
        {late: {
            "listing_date": "2026-06-01",
            "source": {"path": str(doc),
                       "sha256": hashlib.sha256(doc.read_bytes()).hexdigest()},
        }}
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    # 主控 v1.1.0：自述/合成记录不获得真实研究资格——
    # 日期算法诊断仍可用，但不再产生 structural=True
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"
    assert f.evidence["evidence_check"]["dates"]["outcome"] == "coherent"
    assert f.evidence["evidence_check"].get("synthetic") is True


def test_missing_or_bad_listing_date_rejected():
    """缺日期 / 非法日期都不得通过。"""
    _, late = _late_pool()
    for bad in ({}, {"listing_date": "garbage", "source": "合成证据"},
                {"listing_date": "2026-13-01", "source": "合成证据"}):
        report = _check_with_evidence({late: bad})
        f = next(x for x in report.findings if x.code == "starts_after_window")
        assert f.structural is False, f"证据 {bad} 不得通过"


# ===========================================================================
# 三、日历按条数判断完整，非法日期能补足数量
# ===========================================================================


def _calendar_payload_with_replacement(tmp_path: Path) -> Path:
    """主控反例：把 2026-01-05 换成 2026-01-99，条数不变。"""
    import calendar as _c
    from datetime import date
    days = {}
    for d in range(1, _c.monthrange(2026, 1)[1] + 1):
        day = date(2026, 1, d)
        tr = day.weekday() < 5
        days[day.isoformat()] = {
            "is_trading_day": tr, "source_flag": "1" if tr else "0",
            "source_month": "2026-01",
        }
    del days["2026-01-05"]
    days["2026-01-99"] = {"is_trading_day": True, "source_flag": "1",
                          "source_month": "2026-01"}
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": ["2026-01"], "months_failed": [], "days": days,
    }), encoding="utf-8")
    return p


def test_invalid_date_key_cannot_pad_completeness(tmp_path):
    """主控反例 3：等条数替换后 complete 不得为 True。"""
    cal = TradingCalendar.from_file(_calendar_payload_with_replacement(tmp_path))
    assert cal.status("2026-01-05").status == "unknown"
    cov = cal.coverage("2026-01-01", "2026-01-31")
    assert cov.complete is False
    d = cov.to_dict()
    assert "2026-01" in d["day_incomplete_months"]
    # 非法记录必须显式报告，不能悄悄消失
    assert d.get("invalid_records"), "非法日期记录必须被显式列出"


def test_leap_day_is_a_valid_calendar_date(tmp_path):
    """闰日 2024-02-29 是合法日期，不得误判为非法。"""
    days = {}
    for d in range(1, 30):
        day = f"2024-02-{d:02d}"
        tr = pd.Timestamp(day).weekday() < 5
        days[day] = {"is_trading_day": bool(tr),
                     "source_flag": "1" if tr else "0",
                     "source_month": "2024-02"}
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": ["2024-02"], "months_failed": [], "days": days,
    }), encoding="utf-8")
    cal = TradingCalendar.from_file(p)
    cov = cal.coverage("2024-02-01", "2024-02-29")
    assert cov.complete is True
    assert cal.status("2024-02-29").status in ("trading", "closed")


def test_partial_month_query_not_judged_by_out_of_range_gaps(tmp_path):
    """只查一个月的部分区间时，不因区间外缺日误判。"""
    days = {}
    for d in range(10, 21):  # 只录 2026-01-10..20
        day = f"2026-01-{d:02d}"
        tr = pd.Timestamp(day).weekday() < 5
        days[day] = {"is_trading_day": bool(tr),
                     "source_flag": "1" if tr else "0",
                     "source_month": "2026-01"}
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": ["2026-01"], "months_failed": [], "days": days,
    }), encoding="utf-8")
    cal = TradingCalendar.from_file(p)
    cov = cal.coverage("2026-01-10", "2026-01-20")
    assert cov.complete is True, "区间 [01-10,01-20] 内记录齐全，不得误判"
    d = cov.to_dict()
    # 但整月不完整必须单列，不能与区间完整性混为一谈
    assert "2026-01" in d.get("month_incomplete_months", [])


def test_downstream_quality_also_catches_invalid_calendar(tmp_path):
    """不只测 coverage：下游质量判断同样不得被非法日期骗过。"""
    cal = TradingCalendar.from_file(_calendar_payload_with_replacement(tmp_path))
    frames = {
        "510300.SS": pd.DataFrame(
            {"open": [4.0], "high": [4.1], "low": [3.9], "close": [4.0],
             "volume": [100]},
            index=pd.to_datetime(["2026-01-05"]),
        )
    }
    report = q.check_prices(frames, calendar=cal,
                            evaluation_start="2026-01-01",
                            evaluation_end="2026-01-31")
    assert report.verdict_for("ranking") != q.USABLE
