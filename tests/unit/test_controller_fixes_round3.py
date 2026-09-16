"""主控返修单 R1/R2/R3 的修复守卫（research-controller-fixes-2026-09-13）。

反例来自主控书面复核报告 §3/§4/§5 与 §7 复跑入口。
每项：先复现 → 失败测试 → 最小修复 → 通过。
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research import data_quality as q
from lei_signal.research.trading_calendar import TradingCalendar


def _synthetic_calendar() -> TradingCalendar:
    days = {}
    d = date(2026, 5, 1)
    while d <= date(2026, 6, 30):
        tr = d.weekday() < 5
        days[d.isoformat()] = {
            "is_trading_day": tr, "source_flag": "1" if tr else "0",
            "source_month": d.isoformat()[:7],
        }
        d += timedelta(days=1)
    return TradingCalendar({
        "authority": "exchange_official",
        "publisher": "SYNTHETIC ALGORITHM TEST ONLY",
        "months_requested": ["2026-05", "2026-06"], "days": days,
    })


def _frame(ds):
    return pd.DataFrame({
        "open": [10.0] * len(ds), "high": [11.0] * len(ds),
        "low": [9.0] * len(ds), "close": [10.0] * len(ds),
        "volume": [100.0] * len(ds),
    }, index=pd.to_datetime(ds))


def _gate(report):
    try:
        q.require_use(report, "ranking", accept_structural=True)
        return "ALLOWED"
    except q.UseNotPermitted:
        return "REJECTED"


# ===========================================================================
# R1：上市日期自洽不能代替来源核验
# ===========================================================================


def _r1_frames():
    return {
        "510300.SS": _frame(["2026-05-28", "2026-05-29", "2026-06-01", "2026-06-02"]),
        "512890.SS": _frame(["2026-06-01", "2026-06-02"]),
    }


def _r1_check(evidence):
    return q.check_prices(
        _r1_frames(), calendar=_synthetic_calendar(),
        evaluation_start="2026-05-28", evaluation_end="2026-06-02",
        listing_evidence={"512890.SS": evidence} if evidence else None,
    )


def test_r1_dummy_source_with_coherent_date_must_not_pass():
    """主控反例：{"listing_date": "2026-06-01", "source": "dummy"}。"""
    report = _r1_check({"listing_date": "2026-06-01", "source": "dummy"})
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"
    assert _gate(report) == "REJECTED"
    # 诊断必须同时让人看见「日期算法自洽」与「来源未核验」两层
    reason = f.evidence["evidence_check"]["reason"]
    assert "日期算法自洽" in reason
    assert "来源未核验" in reason


def test_r1_unverifiable_reference_rejected():
    """不存在的路径、错误的哈希、非 JSON、缺字段，全部拒绝。"""
    for bad in (
        {"path": "no/such/file.json", "sha256": "0" * 64},
        {"path": "docs/experiments/registry.json", "sha256": "0" * 64},
        {"path": "docs/experiments/registry.json", "sha256": "not-a-hash"},
    ):
        report = _r1_check({
            "listing_date": "2026-06-01",
            "source": bad,
        })
        f = next(x for x in report.findings if x.code == "starts_after_window")
        assert f.structural is False, f"引用 {bad} 不得通过"
        assert _gate(report) == "REJECTED"


def _write_qualification_doc(tmp_path: Path, *, symbol="512890",
                            listing="2026-06-01",
                            qualification="synthetic_algorithm_test") -> dict:
    doc = tmp_path / "listing-qualification.json"
    payload = {
        "symbol": symbol,
        "listing_date": listing,
        "qualification": qualification,
        "note": "合成资格记录，仅用于算法测试，不是真实市场资格证明",
    }
    doc.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    import hashlib
    return {
        "path": str(doc),
        "sha256": hashlib.sha256(doc.read_bytes()).hexdigest(),
    }


def test_r1_coherent_verified_synthetic_doc_passes_algorithm_path(tmp_path):
    """正向：可回查、哈希一致、产品与日期匹配的（合成）资格记录可通过算法路径——

    但输出必须明确标注它是合成证据，不是真实市场资格。
    """
    report = _r1_check({
        "listing_date": "2026-06-01",
        "source": _write_qualification_doc(tmp_path),
    })
    f = next(x for x in report.findings if x.code == "starts_after_window")
    # 主控 v1.1.0：自述/合成记录不获得真实研究资格——
    # 算法诊断成立，但 structural 必须为 False，且 require_use 层必须拒绝
    assert f.structural is False
    check = f.evidence["evidence_check"]
    assert check["dates"]["outcome"] == "coherent"
    assert check.get("synthetic") is True, (
        "合成证据必须被显式标注，不得冒充真实市场资格"
    )
    for use in ("ranking", "comparison"):
        with pytest.raises(q.UseNotPermitted):
            q.require_use(report, use, accept_structural=True)


def test_r1_doc_for_wrong_product_or_date_rejected(tmp_path):
    """来源对应另一产品或另一上市日期时拒绝。"""
    ref = _write_qualification_doc(tmp_path, symbol="512890", listing="2026-06-01")
    for wrong in (
        {"listing_date": "2026-06-02", "source": ref},   # 日期对不上
    ):
        report = _r1_check(wrong)
        f = next(x for x in report.findings if x.code == "starts_after_window")
        assert f.structural is False

    # 产品对不上：把证据挂到 510300 名下
    report = q.check_prices(
        _r1_frames(), calendar=_synthetic_calendar(),
        evaluation_start="2026-05-28", evaluation_end="2026-06-02",
        listing_evidence={"510300.SS": {
            "listing_date": "2026-06-01", "source": ref}},
    )
    # 510300 本身不触发 starts_after_window（首报价在窗口内），
    # 但挂在晚出现产品名下时引用错产品的文档必须拒绝
    report2 = _r1_check({"listing_date": "2026-06-01",
                         "source": _write_qualification_doc(
                             tmp_path, symbol="600000")})
    f = next(x for x in report2.findings if x.code == "starts_after_window")
    assert f.structural is False


def test_r1_stale_reference_rejected_after_content_change(tmp_path):
    """引用内容变化后不得继续沿用旧核验结论（哈希不匹配即拒绝）。"""
    ref = _write_qualification_doc(tmp_path)
    doc = Path(ref["path"])
    payload = json.loads(doc.read_text(encoding="utf-8"))
    payload["listing_date"] = "2026-06-02"   # 内容变了，哈希没更新
    doc.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    report = _r1_check({"listing_date": "2026-06-02", "source": ref})
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert "哈希" in f.evidence["evidence_check"]["reason"] or "sha256" in \
        f.evidence["evidence_check"]["reason"]


# ===========================================================================
# R2：直接价格入口不能消费未核验停牌记录
# ===========================================================================


def _r2_frames():
    return {
        "510300.SS": _frame(["2026-06-01", "2026-06-02", "2026-06-03"]),
        "512890.SS": _frame(["2026-06-01", "2026-06-03"]),   # 缺 06-02
    }


def _account_event_halt():
    return {
        "event_id": "synthetic-halt", "symbol": "512890.SS",
        "type": "trading_halt", "effective_date": "2026-06-02",
        "halt": {"start_date": "2026-06-02", "end_date": "2026-06-02"},
        "account_id": "test-account", "amount": 0,
    }


def test_r2_direct_entry_rejects_account_event_halt():
    """主控反例：直接 check_prices 传混入账户字段的停牌记录。"""
    kw = dict(calendar=_synthetic_calendar(),
              evaluation_start="2026-06-01", evaluation_end="2026-06-03")

    clean = q.check_prices(_r2_frames(), **kw)
    assert clean.verdict_for("ranking") == q.CONDITIONAL
    assert _gate(clean) == "REJECTED"

    bad = q.check_prices(_r2_frames(), halts=[_account_event_halt()], **kw)
    # 非法记录不得解释缺口、不得升级排序
    gap = next(f for f in bad.findings if f.code == "product_internal_gap")
    assert "2026-06-02" in gap.evidence.get("dates", [])
    assert gap.evidence.get("cause") == "unconfirmed"
    assert bad.verdict_for("ranking") != q.USABLE
    assert _gate(bad) == "REJECTED"
    # 且混入情况必须可见，不能静默丢弃
    assert "events_passed_as_actions" in {f.code for f in bad.findings}


def test_r2_direct_entry_rejects_wrong_identity_and_conflicts():
    """错身份、缺 ID、冲突 ID、非法区间，直接入口同样不得消费。"""
    kw = dict(calendar=_synthetic_calendar(),
              evaluation_start="2026-06-01", evaluation_end="2026-06-03")
    base = {
        "event_id": "h1", "symbol": "512890.SS", "type": "trading_halt",
        "effective_date": "2026-06-02",
        "halt": {"start_date": "2026-06-02", "end_date": "2026-06-02"},
    }
    variants = [
        {**base, "symbol": "512890.SZ"},                          # 交易所冲突
        {**base, "event_id": None},                               # 缺 ID
        {**base, "halt": {"start_date": "2026-06-03",
                          "end_date": "2026-06-02"}},             # 倒置区间
    ]
    for bad in variants:
        report = q.check_prices(_r2_frames(), halts=[bad], **kw)
        gap = next(f for f in report.findings if f.code == "product_internal_gap")
        assert gap.evidence.get("cause") == "unconfirmed", bad
        assert report.verdict_for("ranking") != q.USABLE

    # 冲突 ID：同 ID 不同内容，两条都不可信
    a = dict(base)
    b = dict(base)
    b["halt"] = {"start_date": "2026-06-02", "end_date": "2026-06-03"}
    report = q.check_prices(_r2_frames(), halts=[a, b], **kw)
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert gap.evidence.get("cause") == "unconfirmed"


def test_r2_legal_halt_still_explains_with_event_id():
    """合法停牌仍能解释具体产品具体日期，引用保留 event_id。"""
    good = {
        "event_id": "512890-halt-2026-06-02", "symbol": "512890.SS",
        "type": "trading_halt", "effective_date": "2026-06-02",
        "halt": {"start_date": "2026-06-02", "end_date": "2026-06-02"},
    }
    report = q.check_prices(
        _r2_frames(), halts=[good],
        calendar=_synthetic_calendar(),
        evaluation_start="2026-06-01", evaluation_end="2026-06-03",
    )
    gap = next(f for f in report.findings if f.code == "product_internal_gap")
    assert "2026-06-02" in gap.evidence.get("explained_by_halt", [])
    assert any(r.get("event_id") == "512890-halt-2026-06-02"
               for r in gap.evidence.get("explained_by", []))


# ===========================================================================
# R3：资格起点语义与残余缺口测试
# ===========================================================================


def _r3_check(listing: str, tmp_path: Path):
    """用结构化合成资格记录构造 R3 场景（明确标记：仅算法测试）。"""
    frames = {
        "510300.SS": _frame(["2026-05-28", "2026-05-29", "2026-06-01", "2026-06-02"]),
        "512890.SS": _frame(["2026-06-01", "2026-06-02"]),
    }
    return q.check_prices(
        frames, calendar=_synthetic_calendar(),
        evaluation_start="2026-05-28", evaluation_end="2026-06-02",
        listing_evidence={"512890.SS": {
            "listing_date": listing,
            "source": _write_qualification_doc(tmp_path, listing=listing)}},
    )


def test_r3_residual_reason_must_be_residual_not_early_listing(tmp_path):
    """主控 R3.1：上市日期放进评价期、中间确有开市缺报价日时，
    拒绝原因必须是「残余缺口」，不能只断言 structural=False。
    """
    report = _r3_check("2026-05-28", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    reason = f.evidence["evidence_check"]["reason"]
    assert "残余" in reason, f"应命中残余缺口分支，实际：{reason}"
    assert "2026-05-29" in reason, f"应指出残余日，实际：{reason}"


def test_r3_early_listing_branch_also_named(tmp_path):
    """对照：上市早于评价期时，原因须为「早于评价期」而非残余。"""
    report = _r3_check("2026-05-20", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert "早于评价期" in f.evidence["evidence_check"]["reason"]


def test_r3_friday_listing_monday_first_quote_is_not_auto_normal(tmp_path):
    """主控 R3.2：周五上市、周一首报价不能无条件当作正常。

    合成日历明确 2026-05-29（周五）开市。上市当天是否具备报价资格未知——
    资格起点未知则保留未知，不得仅因隔了周末就忽略上市日当天。
    """
    report = _r3_check("2026-05-29", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False, (
        "上市当天（周五，开市）到首报价（周一）之间的报价资格起点未知，"
        "不得整体免除"
    )
    assert "残余" in f.evidence["evidence_check"]["reason"]


def test_r3_same_day_listing_and_first_quote_stays_coherent(tmp_path):
    """正向：上市日与首报价同一天，无残余，保持自洽。"""
    report = _r3_check("2026-06-01", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    # 日期算法自洽仍可诊断；但自述/合成记录不获得真实资格
    assert f.structural is False
    assert f.evidence["evidence_check"]["dates"]["outcome"] == "coherent"
    assert f.evidence["evidence_check"].get("synthetic") is True
