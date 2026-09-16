"""``research/data_quality.py`` 的单元测试。

期望值全部手算：小样本的行数、条数、裁决结果直接写死在断言里，
不调用被测函数生成期望。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.data_quality import (
    BLOCK,
    CONDITIONAL,
    UNUSABLE,
    USABLE,
    WARN,
    UseNotPermitted,
    check_actions,
    check_prices,
    check_snapshot,
    merge_reports,
    require_use,
)

GOOD = "510300.SS"
OTHER = "512890.SS"


def _frame(dates, closes, *, volume=1000.0):
    """构造合法 OHLC：high=close+0.1，low=close-0.1，open=close。"""
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.1 for c in closes],
            "low": [c - 0.1 for c in closes],
            "close": closes,
            "volume": [volume] * len(closes),
        },
        index=pd.to_datetime(dates),
    )


def _clean(symbol=GOOD):
    return {symbol: _frame(["2026-09-01", "2026-09-02", "2026-09-03"], [4.0, 4.1, 4.2])}


def _codes(report):
    return {f.code for f in report.findings}


_ALL_2026_MONTHS = tuple(f"2026-{m:02d}" for m in range(1, 13))


def _test_calendar(months=_ALL_2026_MONTHS, trading_weekdays=True):
    """构造一份**真实存在**的小日历供测试声明日历权威。

    第六轮自查发现：早期只要传 ``calendar=_test_calendar()``
    这句字符串、根本不给日历对象，就能让「无合格日历」告警消失、裁决变绿。
    修复后声明权威必须同时提供日历对象，因此测试也必须给一份真日历——
    与生产调用方走同一条路，不再有捷径。
    """
    import calendar as _cal
    from datetime import date

    from lei_signal.research.trading_calendar import TradingCalendar

    days = {}
    for ym in months:
        y, m = (int(x) for x in ym.split("-"))
        for d in range(1, _cal.monthrange(y, m)[1] + 1):
            day = date(y, m, d)
            trading = trading_weekdays and day.weekday() < 5
            days[day.isoformat()] = {
                "is_trading_day": trading,
                "source_flag": "1" if trading else "0",
                "source_month": ym,
            }
    return TradingCalendar({
        "authority": "exchange_official",
        "publisher": "测试用合成日历",
        "months_requested": list(months),
        "months_failed": [],
        "days": days,
    })



# --------------------------------------------------------------------------
# 干净数据：所有用途可用
# --------------------------------------------------------------------------


def test_clean_data_is_usable_for_every_use():
    report = check_prices(_clean(), calendar=_test_calendar())
    assert report.counts["instruments"] == 1
    assert report.counts["rows_total"] == 3
    assert report.blocked_instruments == ()
    for verdict in report.verdicts:
        assert verdict.verdict == USABLE, verdict


def test_missing_calendar_downgrades_but_does_not_block():
    """无合格日历：相关用途降级为有条件，但不是不可用。"""
    report = check_prices(_clean(), calendar_authority="none")
    assert "no_qualified_calendar" in _codes(report)
    assert report.verdict_for("ranking") == CONDITIONAL
    assert report.verdict_for("research_signal") == CONDITIONAL
    # 描述与诊断不依赖日历，仍然可用
    assert report.verdict_for("description") == USABLE
    assert report.verdict_for("diagnostic") == USABLE


# --------------------------------------------------------------------------
# 数值异常
# --------------------------------------------------------------------------


def test_non_positive_price_blocks():
    frames = {GOOD: _frame(["2026-09-01", "2026-09-02"], [4.0, 0.0])}
    report = check_prices(frames, calendar=_test_calendar())
    assert "non_positive_price" in _codes(report)
    assert report.blocked_instruments == (GOOD,)
    assert report.verdict_for("attribution") == UNUSABLE


def test_infinite_value_blocks():
    frames = {GOOD: _frame(["2026-09-01", "2026-09-02"], [4.0, np.inf])}
    report = check_prices(frames, calendar=_test_calendar())
    assert "non_finite_value" in _codes(report)


def test_nan_value_blocks():
    frames = {GOOD: _frame(["2026-09-01", "2026-09-02"], [4.0, np.nan])}
    report = check_prices(frames, calendar=_test_calendar())
    assert "non_finite_value" in _codes(report)


def test_ohlc_relation_violation_blocks():
    frame = _frame(["2026-09-01"], [4.0])
    frame.loc[frame.index[0], "high"] = 3.0  # high < low
    report = check_prices({GOOD: frame}, calendar=_test_calendar())
    assert "ohlc_relation" in _codes(report)


def test_negative_volume_blocks_and_zero_volume_only_warns():
    neg = _frame(["2026-09-01"], [4.0], volume=-1.0)
    assert "negative_volume" in _codes(
        check_prices({GOOD: neg}, calendar=_test_calendar())
    )
    zero = _frame(["2026-09-01", "2026-09-02"], [4.0, 4.1], volume=0.0)
    report = check_prices({GOOD: zero}, calendar=_test_calendar())
    assert "zero_volume_days" in _codes(report)
    assert report.blocked_instruments == ()  # 零成交量不阻断
    assert report.verdict_for("research_signal") == CONDITIONAL


def test_empty_frame_blocks_all_uses():
    report = check_prices(
        {GOOD: pd.DataFrame()}, calendar=_test_calendar()
    )
    assert "empty_frame" in _codes(report)
    for verdict in report.verdicts:
        assert verdict.verdict == UNUSABLE


# --------------------------------------------------------------------------
# 顺序、重复与冲突
# --------------------------------------------------------------------------


def test_unsorted_dates_block():
    frame = _frame(["2026-09-03", "2026-09-01"], [4.2, 4.0])
    report = check_prices({GOOD: frame}, calendar=_test_calendar())
    assert "dates_not_sorted" in _codes(report)


def test_duplicate_identical_rows_only_warn():
    frame = _frame(["2026-09-01", "2026-09-01"], [4.0, 4.0])
    report = check_prices({GOOD: frame}, calendar=_test_calendar())
    codes = _codes(report)
    assert "duplicate_rows" in codes
    assert "duplicate_conflict" not in codes
    assert report.blocked_instruments == ()


def test_duplicate_conflicting_rows_block():
    frame = _frame(["2026-09-01", "2026-09-01"], [4.0, 4.5])
    report = check_prices({GOOD: frame}, calendar=_test_calendar())
    assert "duplicate_conflict" in _codes(report)
    assert report.blocked_instruments == (GOOD,)


# --------------------------------------------------------------------------
# 覆盖、预热、评价期
# --------------------------------------------------------------------------


def test_coverage_short_warns():
    report = check_prices(
        _clean(), requested_days={GOOD: 10}, calendar=_test_calendar()
    )
    assert "coverage_short" in _codes(report)
    # 手算：请求 10 行，实际 3 行
    finding = next(f for f in report.findings if f.code == "coverage_short")
    assert finding.evidence == {"requested": 10, "actual": 3}


def test_warmup_insufficient_blocks_ranking_but_not_description():
    report = check_prices(
        _clean(), warmup_rows=273, calendar=_test_calendar()
    )
    assert "warmup_insufficient" in _codes(report)
    assert report.verdict_for("ranking") == UNUSABLE
    assert report.verdict_for("research_signal") == UNUSABLE
    # description 不在该 finding 的影响范围内，必须仍可用
    assert report.verdict_for("description") == USABLE


def test_evaluation_window_empty_blocks():
    report = check_prices(
        _clean(),
        evaluation_start="2027-01-01",
        evaluation_end="2027-12-31",
        calendar=_test_calendar(),
    )
    assert "evaluation_window_empty" in _codes(report)


def test_starts_after_window_warns():
    report = check_prices(
        _clean(),
        evaluation_start="2026-01-01",
        evaluation_end="2026-12-31",
        calendar=_test_calendar(),
    )
    assert "starts_after_window" in _codes(report)


def test_no_calendar_means_no_coverage_denominator():
    report = check_prices(
        _clean(),
        evaluation_start="2026-01-01",
        evaluation_end="2026-12-31",
        calendar_authority="none",
    )
    assert "coverage_denominator_unknown" in _codes(report)


# --------------------------------------------------------------------------
# 代码错配与口径混用
# --------------------------------------------------------------------------


def test_symbol_convention_mismatch_warns():
    """冻结输入用 .SH，仓库 resolve_symbol 判为非 A 股；按代码 join 会空交集。"""
    report = check_prices(
        {"510300.SH": _frame(["2026-09-01"], [4.0])},
        calendar=_test_calendar(),
    )
    assert "symbol_convention_mismatch" in _codes(report)
    assert report.verdict_for("ranking") == CONDITIONAL
    assert report.blocked_instruments == ()


def test_price_basis_mixing_blocks_comparison():
    frames = {GOOD: _frame(["2026-09-01"], [4.0]), OTHER: _frame(["2026-09-01"], [1.0])}
    report = check_prices(
        frames,
        declared_basis={GOOD: "nominal_close", OTHER: "economic_index"},
        calendar=_test_calendar(),
    )
    assert "price_basis_mixed" in _codes(report)
    assert report.verdict_for("comparison") == UNUSABLE
    assert report.verdict_for("ranking") == UNUSABLE
    # 纯描述不受口径混用影响
    assert report.verdict_for("description") == USABLE


def test_declared_but_absent_instrument_blocks():
    report = check_prices(
        _clean(),
        expected_instruments=[GOOD, "999999.SS"],
        calendar=_test_calendar(),
    )
    assert "source_missing" in _codes(report)


# --------------------------------------------------------------------------
# 只阻断受影响部分
# --------------------------------------------------------------------------


def test_bad_instrument_does_not_block_the_good_one():
    frames = {
        GOOD: _frame(["2026-09-01", "2026-09-02"], [4.0, 4.1]),
        OTHER: _frame(["2026-09-01", "2026-09-02"], [1.0, 0.0]),  # 非正价
    }
    report = check_prices(frames, calendar=_test_calendar())
    # 手算：只有 OTHER 被阻断，GOOD 不受牵连
    assert report.blocked_instruments == (OTHER,)
    good_findings = [f for f in report.findings if f.instrument == GOOD]
    assert all(f.level != BLOCK for f in good_findings)


# --------------------------------------------------------------------------
# 公司行动
# --------------------------------------------------------------------------


def _dividend(eid="510300-cash_dividend-2026-01-05", cash=0.03, **kw):
    base = {
        "event_id": eid,
        "symbol": "510300",
        "type": "cash_dividend",
        "effective_date": "2026-01-05",
        "cash_per_unit": cash,
    }
    base.update(kw)
    return base


def test_clean_actions_still_report_unproven_coverage():
    """没有行动记录不等于已证明没有行动——这条永远出现。"""
    report = check_actions([_dividend()], declared_symbols=["510300.SH"])
    assert "coverage_unproven" in _codes(report)
    assert report.counts["total"] == 1
    assert report.counts["unique_ids"] == 1


def test_empty_actions_also_report_unproven_coverage():
    report = check_actions([], declared_symbols=["510300.SH"])
    assert "coverage_unproven" in _codes(report)
    assert report.counts["total"] == 0


def test_duplicate_action_id_blocks():
    report = check_actions([_dividend(), _dividend()])
    assert "action_duplicate_id" in _codes(report)
    assert report.verdict_for("attribution") == UNUSABLE


def test_conflicting_action_id_blocks():
    report = check_actions([_dividend(cash=0.03), _dividend(cash=0.09)])
    assert "action_conflicting_id" in _codes(report)


def test_missing_event_id_blocks():
    bad = _dividend()
    del bad["event_id"]
    assert "action_missing_id" in _codes(check_actions([bad]))


def test_missing_required_date_blocks():
    bad = _dividend()
    del bad["effective_date"]
    assert "action_missing_date" in _codes(check_actions([bad]))


def test_dividend_amount_boundaries():
    # 零金额合法
    assert "action_bad_amount" not in _codes(check_actions([_dividend(cash=0.0)]))
    # 负金额非法
    assert "action_bad_amount" in _codes(check_actions([_dividend(cash=-1.0)]))
    # 非有限非法
    assert "action_bad_amount" in _codes(check_actions([_dividend(cash=float("inf"))]))


def test_dividend_missing_amount_blocks_and_undeclared_field_not_accepted():
    bad = _dividend()
    del bad["cash_per_unit"]
    bad["dividend"] = 0.05  # 未声明字段，不得被当成每份分红
    assert "action_missing_amount" in _codes(check_actions([bad]))


def test_split_ratio_boundaries():
    def split(ratio):
        return {
            "event_id": f"512890-split-{ratio}",
            "symbol": "512890",
            "type": "split",
            "effective_date": "2026-02-01",
            "split_ratio": ratio,
        }

    assert "action_bad_ratio" not in _codes(check_actions([split(2.0)]))
    assert "action_bad_ratio" in _codes(check_actions([split(0)]))
    assert "action_bad_ratio" in _codes(check_actions([split(-2)]))


def test_unknown_action_type_warns_not_blocks():
    weird = _dividend(eid="x-weird-1")
    weird["type"] = "spin_off"
    report = check_actions([weird])
    assert "action_unknown_type" in _codes(report)


def test_symbol_outside_declared_pool_blocks():
    report = check_actions([_dividend()], declared_symbols=["512890.SH"])
    assert "action_symbol_not_declared" in _codes(report)


def test_missing_available_at_warns_by_default_and_can_block():
    warned = check_actions([_dividend()])
    assert "action_available_at_unknown" in _codes(warned)
    assert warned.verdict_for("attribution") == CONDITIONAL
    assert warned.counts["without_available_at"] == 1

    strict = check_actions([_dividend()], require_available_at=True)
    assert strict.verdict_for("attribution") == UNUSABLE


def test_present_available_at_is_not_flagged():
    ok = _dividend(available_at="2026-01-04T15:30:00+08:00")
    report = check_actions([ok])
    assert "action_available_at_unknown" not in _codes(report)
    assert report.counts["without_available_at"] == 0


def test_account_events_passed_as_actions_are_rejected():
    """events（账户权益日志）不得当作 actions（原始公司行动）输入。"""
    account_event = {
        "account_id": "E11-fee0.001",
        "event_id": "510300-cash_dividend-2026-01-05",
        "symbol": "510300",
        "type": "cash_dividend",
        "effective_date": "2026-01-05",
        "event": "cash_paid",
        "amount": 1234.56,
    }
    report = check_actions([account_event])
    assert "events_passed_as_actions" in _codes(report)
    assert report.verdict_for("attribution") == UNUSABLE


# --------------------------------------------------------------------------
# 合并
# --------------------------------------------------------------------------


def test_merge_takes_the_strictest_verdict():
    clean = check_prices(_clean(), calendar=_test_calendar())
    dirty = check_actions([_dividend(), _dividend()])
    merged = merge_reports(clean, dirty)
    assert merged.verdict_for("attribution") == UNUSABLE
    # 价格侧干净的用途不被行动侧问题牵连
    assert merged.verdict_for("comparison") == USABLE


# --------------------------------------------------------------------------
# 第四轮：结构属性 vs 可修缺陷、公告日期下界
# --------------------------------------------------------------------------




def _synthetic_listing_ref(tmp_path, symbol="512890.SS", listing="2026-06-01"):
    """生成结构化合成资格记录（仅算法测试，不是真实市场资格证明）。"""
    import hashlib
    import json

    doc = tmp_path / "listing-qualification.json"
    doc.write_text(json.dumps({
        "symbol": symbol[:6], "listing_date": listing,
        "qualification": "synthetic_algorithm_test",
    }, ensure_ascii=False), encoding="utf-8")
    return {"path": str(doc),
            "sha256": hashlib.sha256(doc.read_bytes()).hexdigest()}

def _nonrectangular_pool():
    """贴近真实混合池：一只覆盖整窗，一只晚上市。

    只用一只晚上市的标的会让「整池零报价」也成立（那是另一个真实缺陷），
    掩盖本测试要验的「非矩形属于固有属性」。
    """
    days = ["2026-06-01", "2026-06-02"]     # 周一、周二
    early = ["2026-05-28", "2026-05-29", *days]   # 周四、周五 + 上面两天
    return {
        GOOD: _frame(early, [4.0, 4.05, 4.1, 4.15]),
        OTHER: _frame(days, [1.0, 1.1]),           # 晚上市
    }


def test_structural_finding_is_labelled_and_separated(tmp_path):
    """固有属性与可修缺陷必须分开归类。

    主控 v1.1.0 后：自述/合成的上市证据不再产生 structural=True——
    `starts_after_window` 一律为未确认的可修缺陷。
    分类机制本身改用手工构造的 structural finding 覆盖。
    """
    report = check_prices(
        _nonrectangular_pool(),
        evaluation_start="2026-05-28",
        evaluation_end="2026-06-02",
        calendar=_test_calendar(),
        listing_evidence={OTHER: {"listing_date": "2026-06-01",
                                  "source": _synthetic_listing_ref(tmp_path)}},
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"
    assert f.evidence["evidence_check"]["dates"]["outcome"] == "coherent"
    assert f.instrument == OTHER
    blockers = report.blockers_for("ranking")
    assert blockers["structural"] == []
    assert blockers["fixable"] == ["starts_after_window"]

    from lei_signal.research.data_quality import Finding, QualityReport, _verdicts_from

    synthetic_report = QualityReport(
        (
            Finding(WARN, "starts_after_window", "手工构造的结构属性",
                    instrument=OTHER, affects_uses=("ranking",), structural=True),
            Finding(WARN, "zero_volume_days", "手工构造的可修缺陷",
                    instrument=GOOD, affects_uses=("ranking",)),
        ),
        (),
        {},
    )
    synthetic_report = QualityReport(
        synthetic_report.findings, _verdicts_from(synthetic_report.findings), {}
    )
    blockers = synthetic_report.blockers_for("ranking")
    assert blockers["structural"] == ["starts_after_window"]
    assert blockers["fixable"] == ["zero_volume_days"]


def test_accept_structural_allows_only_when_nothing_fixable_remains():
    """机制：只剩已声明固有属性时，显式接受才放行；默认仍拒绝。

    改用手工构造的结构 finding——自述/合成上市证据已不产生 structural
    （主控 v1.1.0），机制测试不应依赖那条已关闭的路径。
    """
    from lei_signal.research.data_quality import Finding, QualityReport, _verdicts_from

    findings = (
        Finding(WARN, "starts_after_window", "已声明的固有属性",
                instrument=OTHER, affects_uses=("ranking",), structural=True),
    )
    report = QualityReport(findings, _verdicts_from(findings), {})
    # 默认仍然拒绝——接受动作必须由调用方主动做出
    with pytest.raises(UseNotPermitted):
        require_use(report, "ranking")
    # 明确接受固有属性后放行
    assert require_use(report, "ranking", accept_structural=True) == CONDITIONAL


def test_accept_structural_does_not_excuse_fixable_defects(tmp_path):
    """有可修缺陷时，接受固有属性也不得放行——这不是放宽闸门的后门。"""
    frames = _nonrectangular_pool()
    frames[OTHER] = _frame(["2026-06-01", "2026-06-02"], [1.0, 0.0])  # 非正价
    report = check_prices(
        frames,
        evaluation_start="2026-05-28",
        evaluation_end="2026-06-02",
        calendar=_test_calendar(),
        listing_evidence={OTHER: {"listing_date": "2026-06-01",
                                  "source": _synthetic_listing_ref(tmp_path)}},
    )
    assert report.blockers_for("ranking")["fixable"], "应存在可修缺陷"
    with pytest.raises(UseNotPermitted):
        require_use(report, "ranking", accept_structural=True)


def test_announcement_date_counted_as_lower_bound_not_available_at():
    """公告日期只作下界统计，绝不写入 available_at。"""
    with_ann = _dividend(eid="a-1")
    with_ann["announcement_date"] = "2026-01-02"
    without = _dividend(eid="a-2")
    report = check_actions([with_ann, without])

    assert report.counts["without_available_at"] == 2
    assert report.counts["with_announcement_lower_bound"] == 1
    f = next(x for x in report.findings if x.code == "action_available_at_unknown")
    assert f.evidence["fully_unknown"] == 1
    assert "不写入 available_at" in f.message
    assert "action_announcement_lower_bound_available" in _codes(report)
    # 输入记录本身未被改写
    assert "available_at" not in with_ann


# --------------------------------------------------------------------------
# 第五轮自查：修复后的回归守卫
# --------------------------------------------------------------------------


def test_structural_label_cannot_bypass_a_blocking_verdict():
    """缺陷A回归：把 BLOCK 级 finding 标成 structural 也不得绕过闸门。

    自查发现的真缺陷——原实现只看「有没有可修缺陷」，不看裁决本身，
    因此裁决为 unusable 时仍会返回 conditional 放行。
    """
    from lei_signal.research.data_quality import Finding, QualityReport, _verdicts_from

    findings = (
        Finding(
            BLOCK,
            "blocking_but_labelled_structural",
            "阻断级问题被错标为固有属性",
            affects_uses=("ranking",),
            structural=True,
        ),
    )
    report = QualityReport(findings, _verdicts_from(findings), {})
    assert report.verdict_for("ranking") == UNUSABLE
    assert report.blockers_for("ranking")["fixable"] == []
    # 即使「无可修缺陷」且明确接受固有属性，裁决为不可用时仍必须拒绝
    with pytest.raises(UseNotPermitted):
        require_use(report, "ranking", accept_structural=True)


def test_calendar_check_uses_public_accessor_only():
    """缺陷B回归：不得访问 TradingCalendar 的私有属性。"""
    import inspect

    from lei_signal.research.data_quality import _check_against_calendar

    src = inspect.getsource(_check_against_calendar)
    assert "calendar._days" not in src
    assert "calendar.trading_days(" in src


def test_declared_symbols_no_longer_truncate_blindly():
    """缺陷H回归：前六位相同的不同产品不得被认成同一只。"""
    action = _dividend()  # symbol=510300
    # 声明池给一个前六位相同但根本不是同一产品的代码：必须报错而非默默匹配
    with pytest.raises(ValueError, match="无法解析为产品身份"):
        check_actions([action], declared_symbols=["5103001234.XX"])

    # 合法写法照常工作
    ok = check_actions([action], declared_symbols=["510300.SS"])
    assert "action_symbol_not_declared" not in _codes(ok)
    outside = check_actions([action], declared_symbols=["512890.SS"])
    assert "action_symbol_not_declared" in _codes(outside)


# --------------------------------------------------------------------------
# 第三轮自查：修复后的回归守卫
# --------------------------------------------------------------------------


def test_claiming_calendar_authority_without_a_calendar_is_refused():
    """缺陷K回归：一句自由字符串曾经就能让裁决变绿。

    原实现允许任意 calendar_authority 字符串；传 "exchange_official" 而
    不给日历对象时，「无合格日历」告警消失、ranking 直接变 usable，且无兜底。
    """
    frames = {GOOD: _frame(["2026-06-01"], [4.0])}
    with pytest.raises(ValueError, match="却未提供 calendar 对象"):
        check_prices(frames, calendar_authority="exchange_official")
    with pytest.raises(ValueError, match="未知日历权威"):
        check_prices(frames, calendar_authority="随便编一个", calendar=_test_calendar())
    # 诚实声明 none 仍可用，但会如实降级
    report = check_prices(frames, calendar_authority="none")
    assert "no_qualified_calendar" in _codes(report)
    assert report.verdict_for("ranking") == CONDITIONAL


def test_currency_mixing_is_detected():
    """缺陷L回归：快照记了币种，但校验器原本完全不看。"""
    frames = {GOOD: _frame(["2026-06-01"], [4.0]), OTHER: _frame(["2026-06-01"], [1.0])}
    report = check_prices(
        frames,
        calendar=_test_calendar(),
        declared_currency={GOOD: "CNY", OTHER: "USD"},
    )
    assert "currency_mixed" in _codes(report)
    assert report.verdict_for("comparison") == UNUSABLE
    # 同币种不报
    ok = check_prices(frames, calendar=_test_calendar(), declared_currency="CNY")
    assert "currency_mixed" not in _codes(ok)


def test_declared_uses_cross_check_cannot_be_overridden_by_verdict():
    """缺陷N回归：产物声明不含某用途时，质量裁决再好也不得放行。

    实测曾出现：快照 uses 不含 ranking，质量报告却放行 ranking，两轮无人发现。
    """
    frames = {GOOD: _frame(["2026-06-01", "2026-06-02"], [4.0, 4.1])}
    report = check_prices(frames, calendar=_test_calendar())
    # 裁决本身允许 description
    assert require_use(report, "description") == USABLE
    # 但产物声明里没有 description 时必须拒绝
    with pytest.raises(UseNotPermitted, match="不含"):
        require_use(report, "description", declared_uses=["diagnostic"])


def test_lying_about_price_basis_is_caught_by_cross_check():
    """缺陷S回归：调用方口头声明必须与产物记录核对。"""
    frames = {GOOD: _frame(["2026-06-01"], [4.0])}
    report = check_prices(
        frames,
        declared_basis="后复权连续价",
        snapshot_basis="nominal_close",
        calendar=_test_calendar(),
    )
    assert "price_basis_conflict" in _codes(report)
    assert report.verdict_for("description") == UNUSABLE
    # 一致时不报
    ok = check_prices(
        frames, declared_basis="nominal_close", snapshot_basis="nominal_close",
        calendar=_test_calendar(),
    )
    assert "price_basis_conflict" not in _codes(ok)


def test_empty_string_evaluation_window_is_refused():
    """缺陷R回归：空串会被当成「没有评价期」静默放过，语义与 None 不同。"""
    frames = {GOOD: _frame(["2026-06-01"], [4.0])}
    with pytest.raises(ValueError, match="为空字符串"):
        check_prices(frames, evaluation_start="", calendar_authority="none")
    with pytest.raises(ValueError, match="为空字符串"):
        check_prices(frames, evaluation_end="  ", calendar_authority="none")


def test_warmup_rows_matches_registry_authority():
    """缺陷Q防漂移：预热阈值的权威值在 factor_runtime，调用方各自手传。

    若权威值变更而调用方仍传 273，会静默分叉。用测试把漂移暴露出来。
    """
    from lei_signal.research.factor_runtime import MINIMUM_QUOTES

    assert MINIMUM_QUOTES == 273, (
        f"混合池月选资格阈值已从 273 变为 {MINIMUM_QUOTES}；"
        "所有手传 273 的调用方与文档都需同步更新"
    )


def test_check_snapshot_derives_basis_and_currency_from_the_snapshot():
    """根治方向：不留「调用方自己说」这条路。"""
    from types import SimpleNamespace

    frames = {GOOD: _frame(["2026-06-01", "2026-06-02"], [4.0, 4.1])}
    loaded = SimpleNamespace(
        frames=frames,
        snapshot={"semantics": {"price_basis": "nominal_close", "currency": "CNY",
                                "fields": list(frames[GOOD].columns)}},
    )
    report = check_snapshot(loaded, calendar=_test_calendar())
    # 口径自洽，因此不会有冲突项
    assert "price_basis_conflict" not in _codes(report)
    assert "currency_mixed" not in _codes(report)
    # check_snapshot 不接受口径参数——从结构上无法谎报
    import inspect

    params = inspect.signature(check_snapshot).parameters
    assert "declared_basis" not in params
    assert "declared_currency" not in params


# --------------------------------------------------------------------------
# 第五轮（变异检测）暴露的覆盖假象：以下逻辑此前无任何测试守护
# --------------------------------------------------------------------------


def test_trading_day_with_zero_pool_quotes_is_reported():
    """变异 N2 暴露：日历说是交易日、整池却零报价，此前无测试守护。

    这与「部分产品缺报价」是两件事：整池空缺意味着数据缺口，须单独报出。
    """
    # 2026-06-01(一)、06-02(二) 有报价；06-03(三)、06-04(四)、06-05(五) 整池空缺
    frames = {GOOD: _frame(["2026-06-01", "2026-06-02"], [4.0, 4.1])}
    report = check_prices(
        frames,
        calendar=_test_calendar(),
        evaluation_start="2026-06-01",
        evaluation_end="2026-06-05",
    )
    f = next(
        x for x in report.findings if x.code == "trading_day_without_any_quote"
    )
    # 手算：06-03/04/05 三个工作日都是交易日且整池无报价
    assert f.evidence["count"] == 3
    assert f.evidence["dates"] == ["2026-06-03", "2026-06-04", "2026-06-05"]


def test_late_first_quote_is_not_structural_without_listing_evidence():
    """主控纠正：缺上市资格证据时保留未知，不允许仅靠 accept_structural 放行。"""
    report = check_prices(
        _nonrectangular_pool(),
        evaluation_start="2026-05-28",
        evaluation_end="2026-06-02",
        calendar=_test_calendar(),
    )
    f = next(x for x in report.findings if x.code == "starts_after_window")
    assert f.structural is False
    assert f.evidence["cause"] == "unconfirmed"
    with pytest.raises(UseNotPermitted):
        require_use(report, "ranking", accept_structural=True)
