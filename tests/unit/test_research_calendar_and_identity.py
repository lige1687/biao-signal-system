"""第二轮：交易日历与研究身份映射的单元测试。

期望值手算或来自官方来源的独立事实（例如 2024 年春节休市日），
不由被测函数生成。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lei_signal.research.symbol_identity import (
    REGISTERED_PRODUCTS,
    IdentityError,
    audit_mapping,
    build_mapping,
    parse_identity,
)
from lei_signal.research.trading_calendar import (
    CLOSED,
    TRADING,
    UNKNOWN,
    TradingCalendar,
)

ROOT = Path(__file__).resolve().parents[2]
CALENDAR = (
    ROOT
    / "docs/experiments/raw/research-data-provenance-round2-2026-09-10"
    / "calendar-szse/calendar.json"
)


# --------------------------------------------------------------------------
# 交易日历
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cal() -> TradingCalendar:
    if not CALENDAR.exists():
        pytest.skip("本轮日历产物不存在")
    return TradingCalendar.from_file(CALENDAR)


def _synthetic(tmp_path: Path) -> TradingCalendar:
    """不依赖网络产物的小日历，用于确定性断言。"""
    payload = {
        "authority": "exchange_official",
        "publisher": "测试用",
        "months_requested": ["2026-01"],
        "months_failed": [],
        "days": {
            "2026-01-01": {"is_trading_day": False, "source_flag": "0",
                           "source_month": "2026-01"},
            "2026-01-02": {"is_trading_day": True, "source_flag": "1",
                           "source_month": "2026-01"},
            "2026-01-03": {"is_trading_day": False, "source_flag": "0",
                           "source_month": "2026-01"},
        },
    }
    p = tmp_path / "cal.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return TradingCalendar.from_file(p)


def test_spring_festival_2024_weekday_closures(cal):
    """独立事实：2024 年春节 A 股 2/9(除夕)~2/16 休市。

    2/9 为周五、2/12–2/16 为周一至周五，共 6 个工作日休市。
    """
    expected_closed_weekdays = [
        "2024-02-09", "2024-02-12", "2024-02-13",
        "2024-02-14", "2024-02-15", "2024-02-16",
    ]
    for day in expected_closed_weekdays:
        assert cal.status(day).status == CLOSED, day
    # 春节后第一个交易日
    assert cal.status("2024-02-19").status == TRADING


def test_national_day_2025_weekday_closures(cal):
    for day in ("2025-10-01", "2025-10-02", "2025-10-03",
                "2025-10-06", "2025-10-07", "2025-10-08"):
        assert cal.status(day).status == CLOSED, day
    assert cal.status("2025-10-09").status == TRADING


def test_weekend_makeup_workday_is_still_market_closed(cal):
    """周末调休上班 ≠ 股市开市：样本内不存在任何被标为交易日的周末。"""
    from datetime import date

    offenders = [
        d
        for d in cal._days
        if date.fromisoformat(d).weekday() >= 5 and cal.status(d).status == TRADING
    ]
    assert offenders == []


def test_out_of_range_returns_unknown_not_weekday(cal):
    """区间外必须是 unknown，且绝不能因为是周二就当交易日。"""
    st = cal.status("2018-05-15")  # 周二，但不在已取月份
    assert st.status == UNKNOWN
    assert "不回退为工作日" in st.reason
    assert st.is_trading is False


def test_unknown_is_never_treated_as_trading(tmp_path):
    c = _synthetic(tmp_path)
    assert c.is_trading_day("2026-02-02") is False
    assert c.status("2026-02-02").status == UNKNOWN


def test_covered_month_but_missing_day_is_still_unknown(tmp_path):
    c = _synthetic(tmp_path)
    st = c.status("2026-01-15")  # 该月已取，但来源未列出这一天
    assert st.status == UNKNOWN
    assert "来源未列出" in st.reason


def test_schedule_known_at_always_unknown(cal):
    """本来源只给结果，不给公布时刻——不得假装能回答「当时是否已知」。"""
    st = cal.schedule_known_at("2025-10-01", as_of="2025-06-01")
    assert st.status == UNKNOWN
    assert "发布时刻" in st.reason


def test_coverage_reports_missing_months(cal):
    cov = cal.coverage("2019-09-01", "2026-06-30")
    # 冻结区间共 82 个月，本轮只抽样了一部分
    assert not cov.complete
    assert len(cov.missing_months) > 0
    assert "2019-09" in cov.covered_months
    assert "2026-06" in cov.covered_months


def test_classify_absence_distinguishes_closure_from_missing_quotes(cal):
    closed = cal.classify_absence("2025-10-01", symbols_with_quote=0, symbols_expected=14)
    assert closed["verdict"] == "market_closed"

    partial = cal.classify_absence("2019-09-02", symbols_with_quote=3, symbols_expected=14)
    assert partial["verdict"] == "partial_quotes"

    empty = cal.classify_absence("2019-09-02", symbols_with_quote=0, symbols_expected=14)
    assert empty["verdict"] == "trading_day_but_pool_empty"

    unknown = cal.classify_absence("2018-01-02", symbols_with_quote=0, symbols_expected=14)
    assert unknown["verdict"] == "unknown_calendar"


# --------------------------------------------------------------------------
# 身份映射
# --------------------------------------------------------------------------


def test_two_suffixes_map_to_same_product():
    a = parse_identity("510300.SH")
    b = parse_identity("510300.SS")
    assert a.canonical == b.canonical == "510300.SS"
    assert a.source_format == "SH"
    assert b.source_format == "SS"
    # 原始写法逐字保留，不被覆盖
    assert a.raw == "510300.SH"


def test_canonical_form_is_repo_resolvable():
    """映射后的规范写法必须能被生产 resolve_symbol 认成 A 股。"""
    assert parse_identity("510300.SH").repo_resolvable is True
    assert parse_identity("159652.SZ").repo_resolvable is True


def test_different_products_never_merge():
    m = build_mapping(["510300.SH", "512890.SH"])
    assert len({i.canonical for i in m.values()}) == 2


def test_duplicate_identity_is_rejected():
    """两种写法指向同一产品时，同批出现必须报错而不是静默合并。"""
    with pytest.raises(IdentityError, match="重复身份"):
        build_mapping(["510300.SH", "510300.SS"])


def test_repeated_raw_code_is_rejected():
    with pytest.raises(IdentityError, match="重复代码"):
        build_mapping(["510300.SH", "510300.SH"])


def test_unknown_exchange_suffix_is_rejected():
    with pytest.raises(IdentityError, match="后缀"):
        parse_identity("510300.XX")


def test_missing_suffix_is_rejected_not_guessed():
    """六位裸码不猜交易所——猜测会造成跨市场错误合并。"""
    with pytest.raises(IdentityError, match="缺少交易所后缀"):
        parse_identity("510300")


def test_unregistered_product_is_rejected_by_default():
    with pytest.raises(IdentityError, match="不在本轮显式登记"):
        parse_identity("600000.SH")
    # 显式放宽后可解析，但仍标注未登记
    loose = parse_identity("600000.SH", require_registered=False)
    assert loose.registered is False


def test_conflicting_exchange_is_rejected():
    """159652 登记在深交所；写成 .SH 属冲突，必须拒绝。"""
    with pytest.raises(IdentityError, match="冲突"):
        parse_identity("159652.SH")


def test_all_fourteen_registered_products_parse():
    assert len(REGISTERED_PRODUCTS) == 14
    for code, exchange in REGISTERED_PRODUCTS.items():
        suffix = "SH" if exchange == "SSE" else "SZ"
        ident = parse_identity(f"{code}.{suffix}")
        assert ident.registered is True
        assert ident.repo_resolvable is True


def test_audit_balances_products_rows_and_dates():
    import pandas as pd

    frames = {
        "510300.SH": pd.DataFrame(
            {"close": [1.0, 2.0]}, index=pd.to_datetime(["2026-01-02", "2026-01-05"])
        ),
        "512890.SH": pd.DataFrame(
            {"close": [3.0]}, index=pd.to_datetime(["2026-01-02"])
        ),
    }
    mapping = build_mapping(frames)
    mapped = {mapping[k].canonical: v for k, v in frames.items()}

    # 不传映射后数据 → 行数未核对，balanced 必须为假（不许假装核过）
    unverified = audit_mapping(frames, mapping)
    assert unverified.rows_after is None
    assert unverified.rows_verified is False
    assert unverified.balanced is False

    # 传入映射后数据 → 行数真核对
    audit = audit_mapping(frames, mapping, mapped_frames=mapped)
    # 手算：2 个产品、3 行、日期 2026-01-02 ~ 2026-01-05
    assert audit.products_before == audit.products_after == 2
    assert audit.rows_before == audit.rows_after == 3
    assert audit.rows_verified is True
    assert audit.first_date == "2026-01-02"
    assert audit.last_date == "2026-01-05"
    assert audit.balanced is True


def test_audit_detects_row_loss_after_mapping():
    """真核对必须能发现行数变化——否则它抓不到该抓的东西。"""
    import pandas as pd

    frames = {
        "510300.SH": pd.DataFrame(
            {"close": [1.0, 2.0]}, index=pd.to_datetime(["2026-01-02", "2026-01-05"])
        )
    }
    mapping = build_mapping(frames)
    # 故意在映射后少一行
    lossy = {"510300.SS": frames["510300.SH"].iloc[:1]}
    audit = audit_mapping(frames, mapping, mapped_frames=lossy)
    assert audit.rows_before == 2
    assert audit.rows_after == 1
    assert audit.balanced is False


def test_audit_reports_empty_intersection():
    """这正是本轮要防的静默污染：.SH 与 .SS 直接按代码 join 会空交集。"""
    import pandas as pd

    frames = {"510300.SH": pd.DataFrame({"close": [1.0]},
                                        index=pd.to_datetime(["2026-01-02"]))}
    mapping = build_mapping(frames)
    # 对侧是不同产品，规范身份无交集
    audit = audit_mapping(frames, mapping, counterpart_symbols=["512400.SS"])
    assert audit.empty_intersection is True
    assert "空交集" in audit.note
    # 对侧是同一产品的另一种写法 → 映射后应当匹配上
    ok = audit_mapping(frames, mapping, counterpart_symbols=["510300.SS"])
    assert ok.empty_intersection is False
    assert "共有产品 1 个" in ok.note


# --------------------------------------------------------------------------
# 第三轮：补齐后的日历、发布时间证据、停牌解释
# --------------------------------------------------------------------------

MERGED = (
    ROOT
    / "docs/experiments/raw/research-calendar-completion-2026-09-10"
    / "calendar-merged/calendar.json"
)
PUB = (
    ROOT
    / "docs/experiments/raw/research-calendar-completion-2026-09-10"
    / "publication-evidence.json"
)


@pytest.fixture(scope="module")
def full_cal() -> TradingCalendar:
    if not MERGED.exists():
        pytest.skip("第三轮合并日历不存在")
    return TradingCalendar.from_file(MERGED, PUB if PUB.exists() else None)


def test_merged_calendar_covers_full_frozen_range(full_cal):
    cov = full_cal.coverage("2019-09-02", "2026-06-30")
    assert cov.complete is True, f"仍缺月份：{cov.missing_months}"
    # 独立事实：冻结价格文件的日期并集为 1652 个交易日
    assert cov.trading_days_known == 1652


def test_schedule_known_at_answers_for_2026_with_evidence(full_cal):
    """2026 年安排由上证公告〔2025〕45号于 2025-12-22 公布。"""
    assert full_cal.schedule_known_from("2026-02-16") == "2025-12-22"
    after = full_cal.schedule_known_at("2026-02-16", as_of="2026-01-05")
    assert after.status == TRADING          # 已可知
    assert "2025-12-22" in after.reason
    before = full_cal.schedule_known_at("2026-02-16", as_of="2025-12-01")
    assert before.status == CLOSED          # 当时尚不可知
    assert "早于" in before.reason


def test_schedule_known_at_stays_unknown_without_evidence(full_cal):
    """2019—2025 年度通知未取得，必须保持未知，不得假设同样提前公布。"""
    assert full_cal.schedule_known_from("2021-10-22") is None
    st = full_cal.schedule_known_at("2021-10-22", as_of="2021-01-01")
    assert st.status == UNKNOWN
    assert "不得假设该年同样提前公布" in st.reason


def test_registered_halt_explains_the_only_gap(full_cal):
    """512890 在 2021-10-22 停牌一天，是全区间唯一的单产品缺报价。"""
    unexplained = full_cal.classify_absence(
        "2021-10-22", symbols_with_quote=10, symbols_expected=11
    )
    assert unexplained["verdict"] == "partial_quotes"

    explained = full_cal.classify_absence(
        "2021-10-22", symbols_with_quote=10, symbols_expected=11, halted_symbols=1
    )
    assert explained["verdict"] == "partial_quotes_explained_by_halt"
    assert explained["halted_symbols"] == 1


def test_closed_day_still_takes_precedence_over_halt(full_cal):
    """休市日不因为有停牌记录就改判——休市是全市场事实，优先。"""
    out = full_cal.classify_absence(
        "2026-02-16", symbols_with_quote=0, symbols_expected=14, halted_symbols=1
    )
    assert out["verdict"] == "market_closed"


def test_coverage_refuses_reversed_range(full_cal):
    """缺陷J回归：起止倒置原本返回 complete=True 且零覆盖——静默假通过。"""
    with pytest.raises(ValueError, match="起止倒置"):
        full_cal.coverage("2026-06-30", "2019-09-02")


def test_registered_products_match_frozen_pool():
    """防漂移：硬编码的 14 只必须与冻结池 candidate-pool.json 一致。

    REGISTERED_PRODUCTS 是冻结池的手写副本；池子变更不会自动同步，
    因此用测试把漂移暴露出来。
    """
    import json

    pool_path = (
        ROOT
        / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation"
        / "candidate-pool.json"
    )
    if not pool_path.exists():
        pytest.skip("冻结池不存在")
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    frozen = {
        c["symbol"][:6]: ("SSE" if c["symbol"].endswith(".SH") else "SZSE")
        for c in pool["candidates"]
    }
    assert frozen == REGISTERED_PRODUCTS, (
        "硬编码产品表已与冻结池不一致——"
        f"仅在池中={sorted(set(frozen) - set(REGISTERED_PRODUCTS))}，"
        f"仅在表中={sorted(set(REGISTERED_PRODUCTS) - set(frozen))}"
    )


# --------------------------------------------------------------------------
# 第五轮（变异检测）暴露的覆盖假象
# --------------------------------------------------------------------------


def test_schedule_known_on_the_exact_publication_date(full_cal):
    """变异 N7 暴露：边界日此前无测试，`>=` 改成 `>` 不会被发现。

    发布当日即可知——安排在那天已经公布，不能判成「尚不可知」。
    """
    published = full_cal.schedule_known_from("2026-02-16")
    assert published == "2025-12-22"
    on_the_day = full_cal.schedule_known_at("2026-02-16", as_of=published)
    assert on_the_day.status == TRADING, "发布当日必须算已可知"
    day_before = full_cal.schedule_known_at("2026-02-16", as_of="2025-12-21")
    assert day_before.status == CLOSED


def test_bare_code_must_be_exactly_six_digits():
    """变异 N9 暴露：六位长度校验此前无测试。"""
    for bad in ("12345.SS", "1234567.SS", "51030.SZ"):
        with pytest.raises(IdentityError, match="六位数字"):
            parse_identity(bad, require_registered=False)
    # 正常六位可解析
    assert parse_identity("600000.SS", require_registered=False).bare_code == "600000"
