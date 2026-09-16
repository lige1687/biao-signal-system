"""主控复核 v1.1.0 §10.3 的 R1 剩余问题修复守卫（research-controller-fixes-2026-09-13-02）。

核心：「日期算法自洽」与「可用于真实研究的证据资格」彻底分开。
哈希一致只证明字节一致，不证明内容为真；自述/合成记录不获得真实资格。
断言必须走到 require_use 这一层，不能只停在函数返回的 synthetic 标签。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from lei_signal.research import data_quality as q
from lei_signal.research.trading_calendar import TradingCalendar

ROOT = Path(__file__).resolve().parents[2]
COUNTEREXAMPLES = (
    ROOT / "docs/experiments/raw/research-data-foundation-controller-review-2026-09-13"
)
FIXED_FILES = (
    "listing-explicit-synthetic.json",
    "listing-qualification-omitted.json",
)


def _calendar() -> TradingCalendar:
    days = {}
    d = date(2026, 5, 1)
    while d <= date(2026, 6, 30):
        tr = d.weekday() < 5
        days[str(d)] = {"is_trading_day": tr, "source_flag": str(int(tr)),
                        "source_month": str(d)[:7]}
        d += timedelta(days=1)
    return TradingCalendar({
        "authority": "exchange_official", "publisher": "SYNTHETIC ONLY",
        "months_requested": ["2026-05", "2026-06"], "days": days,
    })


def _frame(ds):
    return pd.DataFrame({
        "open": [10.0] * len(ds), "high": [11.0] * len(ds),
        "low": [9.0] * len(ds), "close": [10.0] * len(ds),
        "volume": [100.0] * len(ds),
    }, index=pd.to_datetime(ds))


def _frames():
    return {
        "510300.SS": _frame(["2026-05-28", "2026-05-29", "2026-06-01", "2026-06-02"]),
        "512890.SS": _frame(["2026-06-01", "2026-06-02"]),
    }


def _outcomes(report):
    out = {}
    for use in ("ranking", "comparison"):
        try:
            q.require_use(report, use, accept_structural=True)
            out[use] = "ALLOWED"
        except q.UseNotPermitted:
            out[use] = "REJECTED"
    return out


# ---------------------------------------------------------------------------
# 主控 §10.4 固定反例：两份文件 × 两个入口 × 两个用途必须全部拒绝
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", FIXED_FILES)
def test_fixed_counterexamples_rejected_everywhere(filename):
    p = COUNTEREXAMPLES / filename
    assert p.is_file(), "固定反例文件必须存在且未被移动"
    evidence = {"512890.SS": {"listing_date": "2026-06-01", "source": {
        "path": str(p),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}}}
    loaded = SimpleNamespace(
        verified=True, frames=_frames(),
        snapshot={"semantics": {"price_basis": "nominal_close", "currency": "CNY"}},
    )
    cal = _calendar()
    kw = dict(calendar=cal, evaluation_start="2026-05-28",
              evaluation_end="2026-06-02")
    reports = {
        "check_prices": q.check_prices(_frames(), listing_evidence=evidence, **kw),
        "check_snapshot": q.check_snapshot(loaded, listing_evidence=evidence, **kw),
    }
    for entry, report in reports.items():
        f = next(f for f in report.findings if f.code == "starts_after_window")
        assert f.structural is False, f"{filename} 经 {entry} 不得为结构属性"
        assert f.evidence["cause"] == "unconfirmed"
        out = _outcomes(report)
        assert out == {"ranking": "REJECTED", "comparison": "REJECTED"}, (
            f"{filename} 经 {entry} 必须全部拒绝，实际 {out}"
        )


def test_explicit_synthetic_and_omitted_are_distinguished_but_neither_qualifies():
    """显式合成与省略 qualification 被区分标记，但两者都不获得真实资格。"""
    flags = {}
    for filename in FIXED_FILES:
        p = COUNTEREXAMPLES / filename
        evidence = {"512890.SS": {"listing_date": "2026-06-01", "source": {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}}}
        report = q.check_prices(
            _frames(), calendar=_calendar(),
            evaluation_start="2026-05-28", evaluation_end="2026-06-02",
            listing_evidence=evidence,
        )
        f = next(f for f in report.findings if f.code == "starts_after_window")
        flags[filename] = f.evidence["evidence_check"]["source"]["outcome"]
    assert flags["listing-explicit-synthetic.json"] == "synthetic"
    assert flags["listing-qualification-omitted.json"] == "unverified"


# ---------------------------------------------------------------------------
# 日期算法诊断仍然可用（与资格无关）
# ---------------------------------------------------------------------------


def _doc(tmp_path: Path, *, symbol="512890", listing="2026-06-01",
         qualification="synthetic_algorithm_test") -> dict:
    doc = tmp_path / "listing-qualification.json"
    doc.write_text(json.dumps({
        "symbol": symbol, "listing_date": listing,
        "qualification": qualification,
        "note": "合成资格记录，仅用于算法测试，不是真实市场资格证明",
    }, ensure_ascii=False), encoding="utf-8")
    return {"path": str(doc),
            "sha256": hashlib.sha256(doc.read_bytes()).hexdigest()}


def _check_with_listing(listing: str, tmp_path: Path):
    return q.check_prices(
        _frames(), calendar=_calendar(),
        evaluation_start="2026-05-28", evaluation_end="2026-06-02",
        listing_evidence={"512890.SS": {
            "listing_date": listing,
            "source": _doc(tmp_path, listing=listing)}},
    )


def test_date_diagnostics_still_work_for_algorithm_testing(tmp_path):
    """同日上市：dates 诊断 coherent、source 标记 synthetic、资格仍不成立。"""
    report = _check_with_listing("2026-06-01", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    check = f.evidence["evidence_check"]
    assert check["dates"]["outcome"] == "coherent"
    assert check["source"]["outcome"] == "synthetic"
    assert check["synthetic"] is True
    assert f.structural is False
    assert _outcomes(report) == {"ranking": "REJECTED", "comparison": "REJECTED"}


def test_residual_branch_still_reports_residual_days(tmp_path):
    """上市在评价期内、中间有开市缺报价：原因仍点名残余日。"""
    report = _check_with_listing("2026-05-28", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    check = f.evidence["evidence_check"]
    assert check["dates"]["outcome"] == "residual"
    assert "2026-05-29" in check["dates"]["residual_days"]
    assert f.structural is False


def test_early_listing_branch_still_named(tmp_path):
    report = _check_with_listing("2026-05-20", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.evidence["evidence_check"]["dates"]["outcome"] == "earlier_than_window"


def test_friday_listing_still_not_auto_normal(tmp_path):
    report = _check_with_listing("2026-05-29", tmp_path)
    f = next(x for x in report.findings if x.code == "starts_after_window")
    check = f.evidence["evidence_check"]
    assert check["dates"]["outcome"] == "residual"
    assert f.structural is False


def test_self_declared_official_qualification_gains_nothing(tmp_path):
    """自述 official/verified 同样不构成资格（未声明≠已核验）。"""
    report = q.check_prices(
        _frames(), calendar=_calendar(),
        evaluation_start="2026-05-28", evaluation_end="2026-06-02",
        listing_evidence={"512890.SS": {
            "listing_date": "2026-06-01",
            "source": _doc(tmp_path, qualification="official_verified_real")}},
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["evidence_check"]["source"]["outcome"] == "unverified"
    assert _outcomes(report) == {"ranking": "REJECTED", "comparison": "REJECTED"}
