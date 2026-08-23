"""基本面参考层：service 降级与缓存行为的单元测试（不打真实网络）。"""
from __future__ import annotations

import math

import pytest

from lei_signal.fundamentals import sources
from lei_signal.fundamentals.service import FundamentalsService


def _board(code: str = "BK0475") -> dict:
    return {
        "code": code,
        "name": "银行Ⅱ",
        "latest": 100.0,
        "pct_change": 1.5,
        "turnover_rate": 0.8,
        "total_mv_yi": 1000.0,
        "main_net_inflow_yi": 2.5,
        "main_net_inflow_pct": 3.0,
        "up_count": 30,
        "down_count": 5,
    }


def _macro(key: str) -> dict:
    return {"key": key, "name_cn": key.upper(), "period": "2026年07月份", "value": 50.0, "yoy": None, "note_cn": ""}


def _stub_valuation(monkeypatch: pytest.MonkeyPatch) -> None:
    """给估值分位的两个全史源打桩。

    rates() / rates_history() 都会**无条件**取 CAPE 与沪深300 PE 全史（它们不依赖
    国债，是为了在 ERP 全挂时仍能显示），所以任何调这两个方法的测试都必须打桩，
    否则会真连 multpl.com / akshare。
    """
    monkeypatch.setattr(sources, "fetch_us_cape_history", lambda: {"2026-08-01": 42.35})
    monkeypatch.setattr(sources, "fetch_hs300_pe_history", lambda: {"2026-08-18": 13.77})


def test_overview_assembles_macro_and_boards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_industry_boards", lambda: [_board()])
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", lambda: _macro("cpi"))
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))

    result = FundamentalsService().overview()

    assert result["board_count"] == 1
    assert [m["key"] for m in result["macro"]] == ["pmi", "cpi", "ppi"]
    assert result["errors"] == []
    assert "参考层" in result["disclaimer_cn"]


def test_overview_degrades_when_one_source_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> list[dict]:
        raise sources.FundamentalsSourceError("timeout")

    monkeypatch.setattr(sources, "fetch_industry_boards", boom)
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", boom)
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))

    result = FundamentalsService().overview()

    # 板块挂了 → 空列表但页面其余部分照常；CPI 挂了 → 其余两个宏观指标保留。
    assert result["boards"] == []
    assert [m["key"] for m in result["macro"]] == ["pmi", "ppi"]
    assert len(result["errors"]) == 2


def test_overview_uses_cache_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fetch() -> list[dict]:
        calls["n"] += 1
        return [_board()]

    monkeypatch.setattr(sources, "fetch_industry_boards", fetch)
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", lambda: _macro("cpi"))
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))

    svc = FundamentalsService()
    svc.overview()
    svc.overview()
    assert calls["n"] == 1  # 第二次命中缓存

    svc.overview(refresh=True)
    assert calls["n"] == 2  # refresh 强制重拉


def test_industry_flow_clamps_days(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, int] = {}

    def fetch(code: str, *, days: int) -> list[dict]:
        seen["days"] = days
        return [{"date": "2026-08-07", "main_yi": -1.0}]

    monkeypatch.setattr(sources, "fetch_industry_flow", fetch)

    result = FundamentalsService().industry_flow("BK0475", days=500)
    assert seen["days"] == 60  # 上限钳制
    assert result["points"][0]["date"] == "2026-08-07"


def test_rates_includes_margin_and_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_treasury", lambda: {"cn": {}, "us": {}, "cn_us_spread_10y": None})
    monkeypatch.setattr(sources, "fetch_vix", lambda: None)
    monkeypatch.setattr(sources, "fetch_margin", lambda: {"date": "2026-08-12", "rzye_yi": 1.0})
    _stub_valuation(monkeypatch)

    r = FundamentalsService().rates()
    assert r["margin"]["rzye_yi"] == 1.0
    assert r["vix"] is None
    assert r["errors"] == []


def test_margin_failure_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom():
        raise sources.FundamentalsSourceError("net")

    monkeypatch.setattr(sources, "fetch_treasury", lambda: {"cn": {}, "us": {}, "cn_us_spread_10y": None})
    monkeypatch.setattr(sources, "fetch_vix", lambda: None)
    monkeypatch.setattr(sources, "fetch_margin", boom)
    _stub_valuation(monkeypatch)

    r = FundamentalsService().rates()
    assert r["margin"] is None
    assert any("两融" in e for e in r["errors"])


def test_commodities_and_etf_none_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_commodity_ratios", lambda: None)
    monkeypatch.setattr(sources, "fetch_etf_strength", lambda: None)
    svc = FundamentalsService()
    assert svc.commodities()["commodities"] is None
    assert svc.etf_strength()["etf"] is None


def test_industry_boards_include_pe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sources,
        "fetch_industry_boards",
        lambda: [{"code": "BK1", "name": "t", "pe_ttm": -71.5, "pct_change": 1.0}],
    )
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", lambda: _macro("cpi"))
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))
    ov = FundamentalsService().overview()
    assert ov["boards"][0]["pe_ttm"] == -71.5


def _hist(value: float = 50.0) -> list[dict]:
    return [
        {"date": "2026-06-01", "value": value - 0.5},
        {"date": "2026-07-01", "value": value},
    ]


def test_macro_history_returns_series(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_pmi_history", lambda **kw: _hist(49.2))
    monkeypatch.setattr(sources, "fetch_cpi_history", lambda **kw: _hist(0.5))
    monkeypatch.setattr(sources, "fetch_ppi_history", lambda **kw: _hist(3.5))

    r = FundamentalsService().macro_history(page_size=12)

    assert r["errors"] == []
    assert set(r["series"]) == {"pmi", "cpi", "ppi"}
    pmi = r["series"]["pmi"]
    assert pmi["label"] == "制造业 PMI"
    assert pmi["unit"] == ""
    assert pmi["dates"] == ["2026-06-01", "2026-07-01"]  # 升序
    assert pmi["values"] == [48.7, 49.2]
    assert r["as_of"] == "2026-07-01"


def test_macro_history_degrades_per_item(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**kw):
        raise sources.FundamentalsSourceError("net")

    monkeypatch.setattr(sources, "fetch_pmi_history", lambda **kw: _hist(49.2))
    monkeypatch.setattr(sources, "fetch_cpi_history", boom)
    monkeypatch.setattr(sources, "fetch_ppi_history", lambda **kw: _hist(3.5))

    r = FundamentalsService().macro_history(page_size=12)

    assert "cpi" not in r["series"]
    assert set(r["series"]) == {"pmi", "ppi"}
    assert any("宏观历史 cpi" in e for e in r["errors"])
    assert r["as_of"] == "2026-07-01"  # 其余两项仍有数据


def test_fetch_margin_parses_eastmoney_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """两融改用东财 RPTA_RZRQ_LSHJ（沪深合计）后，解析应带出占流通市值比。"""
    row = {
        "DIM_DATE": "2026-08-13 00:00:00",
        "RZYE": 2649740550850.0,
        "RQYE": 25977668669.0,
        "RZRQYE": 2675718219519.0,
        "RZMRE": 242100000000.0,
        "RZYEZB": 2.63679,
    }
    monkeypatch.setattr(sources, "_fetch_margin_rows", lambda page_size=1: [row])

    m = sources.fetch_margin()
    assert m["date"] == "2026-08-13"
    assert m["rzrqye_yi"] == pytest.approx(26757.18, abs=0.01)
    assert m["rzyezb_pct"] == pytest.approx(2.637, abs=0.001)


def test_rates_history_includes_margin_ratio_series(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_treasury_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_vix_history", lambda lookback_days=730: {})
    monkeypatch.setattr(
        sources, "fetch_cn_erp_history",
        lambda lookback_days=730, treasury_hist=None: {},
    )
    monkeypatch.setattr(
        sources, "fetch_us_erp_history",
        lambda lookback_days=730, treasury_hist=None: {},
    )
    monkeypatch.setattr(
        sources, "fetch_margin_history",
        lambda lookback_days=730: {
            "2026-08-12": {"rzrqye_yi": 26500.0, "rzyezb_pct": 2.61},
            "2026-08-13": {"rzrqye_yi": 26757.18, "rzyezb_pct": 2.64},
        },
    )
    _stub_valuation(monkeypatch)

    r = FundamentalsService().rates_history()
    assert r["series"]["margin_rzyezb"]["values"] == [2.61, 2.64]
    assert r["series"]["margin_rzrqye"]["values"] == [26500.0, 26757.18]
    assert r["errors"] == []


def test_overlay_history_merges_sources_with_degradation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """长周期叠加：各序列独立取数独立降级，A 股指数缺一个不影响其余。"""
    monkeypatch.setattr(
        sources, "fetch_treasury_history",
        lambda lookback_days=730: {"2026-08-13": {"cn_10y": 1.7, "us_10y": 4.63}},
    )
    monkeypatch.setattr(
        sources, "fetch_margin_history",
        lambda lookback_days=730: {"2026-08-13": {"rzyezb_pct": 2.64, "rzrqye_yi": 26757.18}},
    )
    monkeypatch.setattr(
        sources, "fetch_cn_index_history",
        lambda code, lookback_days=5200: {"2026-08-13": 3700.0 if code == "sh000001" else 4600.0},
    )
    monkeypatch.setattr(
        sources, "fetch_fred_index_history",
        lambda sid: {"2026-08-13": 7800.0},
    )

    r = FundamentalsService().overlay_history(years=20)
    assert r["series"]["cn_10y"]["values"] == [1.7]
    assert r["series"]["margin_rzyezb"]["values"] == [2.64]
    assert r["series"]["sse"]["values"] == [3700.0]
    assert r["series"]["nasdaq"]["values"] == [7800.0]
    assert r["errors"] == []

    # 单项失败 -> 降级进 errors，其余照常
    def boom(sid):
        raise sources.FundamentalsSourceError("fred down")

    monkeypatch.setattr(sources, "fetch_fred_index_history", boom)
    r2 = FundamentalsService().overlay_history(years=20)
    assert "sp500" not in r2["series"] and "nasdaq" not in r2["series"]
    assert r2["series"]["cn_10y"]["values"] == [1.7]
    assert any("标普500" in e for e in r2["errors"])


# ── VIX 数据源：Yahoo v8 图表 API（不走 yfinance）──────────────────────────


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _chart(stamps: list[int | None], closes: list[float | None]) -> dict:
    quote = {"quote": [{"close": closes}]}
    return {"chart": {"result": [{"timestamp": stamps, "indicators": quote}]}}


def test_fetch_yahoo_closes_skips_null_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """停牌/未成交 bar（close=None）应被剔除，而非变成 0 或报错。"""
    # 2026-08-13 / 2026-08-14 两个交易日，中间夹一个 null bar。
    payload = _chart([1755086400, 1755172800, 1755259200], [14.63, None, 14.25])
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResp(payload))

    out = sources._fetch_yahoo_closes("^VIX", {})
    assert list(out.values()) == [14.63, 14.25]
    assert all(v is not None for v in out.values())


def test_fetch_vix_raises_instead_of_silent_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """限流必须抛错让 errors[] 可见——旧实现吞成 None，前端只显示"暂不可用"。"""
    payload = {"chart": {"error": {"description": "Too Many Requests. Rate limited."}}}
    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResp(payload))

    with pytest.raises(sources.FundamentalsSourceError, match="Too Many Requests"):
        sources.fetch_vix()


def test_vix_failure_surfaces_in_rates_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """service 层：VIX 失败降级为 None，但原因要出现在 errors[] 里。"""
    def boom():
        raise sources.FundamentalsSourceError("Yahoo v8 错误：Too Many Requests")

    treasury = {"cn": {}, "us": {}, "cn_us_spread_10y": None}
    monkeypatch.setattr(sources, "fetch_treasury", lambda: treasury)
    monkeypatch.setattr(sources, "fetch_vix", boom)
    monkeypatch.setattr(sources, "fetch_margin", lambda: {"date": "2026-08-14", "rzye_yi": 1.0})
    _stub_valuation(monkeypatch)

    r = FundamentalsService().rates()
    assert r["vix"] is None
    assert any("VIX" in e for e in r["errors"])


def test_fetch_vix_history_uses_calendar_day_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    """必须走 period1/period2 自然日，不能用 range=Nd（Yahoo 按 K 线根数解释）。"""
    seen: dict = {}

    def fake_get(url, params=None, **kwargs):
        seen.update(params or {})
        return _FakeResp(_chart([1755172800], [14.25]))

    monkeypatch.setattr(sources.requests, "get", fake_get)

    sources.fetch_vix_history(730)
    assert "range" not in seen, "range=Nd 会被解释为交易日根数，语义错误"
    assert seen["interval"] == "1d"
    # period1/period2 跨度应为 730 个自然日（容忍 1 天取整误差）。
    span_days = (seen["period2"] - seen["period1"]) / 86400
    assert abs(span_days - 730) <= 1


# ── ERP 历史（股债性价比走势）────────────────────────────────────────────


def test_fetch_cn_erp_history_joins_pe_and_treasury(monkeypatch: pytest.MonkeyPatch) -> None:
    """ERP = 1/PE×100 − 中债10Y，按交集日期逐日计算，并按 lookback 截尾。"""
    monkeypatch.setattr(
        sources, "fetch_hs300_pe_history",
        lambda: {"2025-01-02": 10.0, "2025-01-03": 12.5, "2026-08-18": 13.77},
    )
    treasury = {
        "2025-01-02": {"cn_10y": 2.0},
        "2025-01-03": {"cn_10y": None},  # 国债缺数日应被剔除
        "2026-08-18": {"cn_10y": 1.69},
    }

    out = sources.fetch_cn_erp_history(730, treasury)
    # 10 倍 PE -> 盈利收益率 10% - 2% = 8%；13.77 -> 7.26 - 1.69 = 5.57
    assert out == {"2025-01-02": 8.0, "2026-08-18": 5.57}

    # lookback 截尾：只保留尾部 730 天 -> 2025-01 两个点被截掉。
    out_short = sources.fetch_cn_erp_history(30, treasury)
    assert "2025-01-02" not in out_short
    assert "2026-08-18" in out_short


def test_fetch_cn_erp_history_errors_without_treasury(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_hs300_pe_history", lambda: {"2025-01-02": 10.0})
    with pytest.raises(sources.FundamentalsSourceError, match="中债10Y历史缺失"):
        sources.fetch_cn_erp_history(730, {})


def test_fetch_us_erp_history_asof_joins_monthly_ey(monkeypatch: pytest.MonkeyPatch) -> None:
    """月频 EY 按 as-of 前向填充到国债日频：EY 变、利率不变时 ERP 随利率日动。"""
    monkeypatch.setattr(
        sources, "fetch_us_ey_history",
        lambda: {"2026-03-01": 3.93, "2026-04-01": 3.5},
    )
    treasury = {
        "2026-02-27": {"us_10y": 4.5},  # 早于首个 EY 点 -> 无值，剔除
        "2026-03-02": {"us_10y": 4.5},  # 用 3 月 EY
        "2026-03-03": {"us_10y": 4.4},  # 用 3 月 EY，利率日动
        "2026-04-02": {"us_10y": 4.4},  # 用 4 月 EY（月度跳变）
    }

    out = sources.fetch_us_erp_history(730, treasury)
    assert out == {
        "2026-03-02": -0.57,  # 3.93 - 4.5
        "2026-03-03": -0.47,  # 3.93 - 4.4
        "2026-04-02": -0.9,  # 3.5 - 4.4
    }


def test_fetch_us_ey_history_parses_monthly_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """multpl 月度表解析：'Mar 1, 2026 | 3.93%' -> {'2026-03-01': 3.93}。"""

    class _FakeResp:
        text = (
            "<table><tr><td>Mar 1, 2026</td><td>&#x2002;\n3.93%\n</td></tr>"
            "<tr><td>Feb 1, 2026</td><td> 3.69% </td></tr>"
            "<tr><td>garbage</td><td>xx</td></tr></table>"
        )

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResp())
    out = sources.fetch_us_ey_history()
    assert out == {"2026-02-01": 3.69, "2026-03-01": 3.93}


def test_rates_history_includes_erp_series(monkeypatch: pytest.MonkeyPatch) -> None:
    """rates_history 输出中美 ERP 序列；ERP 失败时降级并写入 errors，不影响其余。"""
    monkeypatch.setattr(sources, "fetch_treasury_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_vix_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_margin_history", lambda lookback_days=730: {})
    monkeypatch.setattr(
        sources, "fetch_cn_erp_history",
        lambda lookback_days=730, treasury_hist=None: {"2026-08-18": 5.58},
    )

    def boom_us(lookback_days=730, treasury_hist=None):
        raise sources.FundamentalsSourceError("multpl 限流")

    monkeypatch.setattr(sources, "fetch_us_erp_history", boom_us)
    _stub_valuation(monkeypatch)

    r = FundamentalsService().rates_history()
    assert r["series"]["erp_cn"]["values"] == [5.58]
    assert "erp_us" not in r["series"] or r["series"]["erp_us"]["values"] == []
    assert any("美股ERP历史" in e for e in r["errors"])
    assert not any("A股ERP" in e for e in r["errors"])


# ── 估值分位对照（CAPE / 沪深300 PE_TTM）──────────────────────────────────────


def test_fetch_us_cape_history_strips_html_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    """裸数值序列必须先剥 HTML 实体：``&#x2002;``（em space）本身含数字 2002。

    这是实测踩过的坑——不剥实体的话裸数值正则会把 2002 当读数抓走，整表变成
    同一个值 2002.0。带 ``%`` 的盈利收益率序列因正则要求百分号而躲过，CAPE 必踩。
    """

    class _FakeResp:
        text = (
            "<table><tr><td>Aug 1, 2026</td><td>&#x2002;\n42.35\n</td></tr>"
            "<tr><td>Jul 1, 2026</td><td>&nbsp;41.06</td></tr>"
            "<tr><td>Mar 1, 2009</td><td>&#x2002;13.32</td></tr>"
            "<tr><td>garbage</td><td>xx</td></tr></table>"
        )

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(sources.requests, "get", lambda *a, **k: _FakeResp())
    out = sources.fetch_us_cape_history()
    assert out == {"2009-03-01": 13.32, "2026-07-01": 41.06, "2026-08-01": 42.35}
    assert 2002.0 not in out.values(), "实体 &#x2002; 未剥离，2002 被当成读数"


def test_percentile_rank_and_dual_window_snapshot() -> None:
    """分位快照必须同时给标定窗口与全史两个分位——分位是取样窗口的函数。

    这里构造一个「全史含极端旧值、标定窗口不含」的序列：同一个现值在两个窗口下
    分位不同，只报一个数就等于把窗口依赖藏起来。
    """
    assert sources.percentile_rank([1.0, 2.0, 3.0, 4.0], 3.0) == 75.0
    assert math.isnan(sources.percentile_rank([], 1.0))

    hist = {
        "1900-01-01": 5.0,
        "1910-01-01": 6.0,
        "1950-01-01": 10.0,
        "1960-01-01": 20.0,
        "1970-01-01": 30.0,
        "2026-08-01": 25.0,
    }
    snap = sources._valuation_snapshot(hist, "1950-01-01")
    assert snap["value"] == 25.0
    assert snap["as_of"] == "2026-08-01"
    assert snap["calib_from"] == "1950" and snap["calib_n"] == 4
    assert snap["full_from"] == "1900" and snap["full_n"] == 6
    assert snap["percentile"] == 75.0  # 标定窗口 [10,20,30,25] 中 ≤25 的占 3/4
    assert snap["percentile_full"] == pytest.approx(83.3)  # 全史 6 个里 ≤25 的占 5/6


def test_valuation_snapshot_rejects_empty_history() -> None:
    with pytest.raises(sources.FundamentalsSourceError):
        sources._valuation_snapshot({}, "1950-01-01")


def test_rates_includes_valuation_and_degrades_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """估值分位与 ERP 相互独立降级：CAPE 挂了不能拖累 A 股 PE 分位。

    这两项存在的意义就是校正股债收益差的利率污染，所以 ERP 全挂时它们必须照常显示。
    """

    def boom_cape() -> dict[str, float]:
        raise sources.FundamentalsSourceError("multpl 限流")

    monkeypatch.setattr(
        sources, "fetch_treasury", lambda: {"cn": {}, "us": {}, "cn_us_spread_10y": None}
    )
    monkeypatch.setattr(sources, "fetch_vix", lambda: None)
    monkeypatch.setattr(sources, "fetch_margin", lambda: None)
    monkeypatch.setattr(sources, "fetch_us_cape_history", boom_cape)
    monkeypatch.setattr(
        sources, "fetch_hs300_pe_history",
        lambda: {"2018-12-28": 10.6, "2026-08-18": 13.77},
    )

    r = FundamentalsService().rates()
    assert r["valuation"]["us_cape"] is None
    assert any("美股CAPE" in e for e in r["errors"])
    # A 股 PE 分位不受影响，且两个窗口分位都在。
    cn = r["valuation"]["cn_pe"]
    assert cn["value"] == 13.77
    assert cn["percentile"] == 100.0 and cn["percentile_full"] == 100.0
    assert cn["calib_from"] == "2010" and cn["full_from"] == "2018"


def test_rates_history_includes_valuation_series(monkeypatch: pytest.MonkeyPatch) -> None:
    """rates_history 输出 CAPE（月频）与沪深300 PE（日频）序列，并按自然日截尾。"""
    monkeypatch.setattr(sources, "fetch_treasury_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_vix_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_margin_history", lambda lookback_days=730: {})
    monkeypatch.setattr(
        sources, "fetch_cn_erp_history",
        lambda lookback_days=730, treasury_hist=None: {},
    )
    monkeypatch.setattr(
        sources, "fetch_us_erp_history",
        lambda lookback_days=730, treasury_hist=None: {},
    )
    # 1900 那条远在 lookback 之外，必须被截掉——证明截尾生效而不是原样透传。
    monkeypatch.setattr(
        sources, "fetch_us_cape_history",
        lambda: {"1900-01-01": 20.0, "2026-08-01": 42.35},
    )
    monkeypatch.setattr(
        sources, "fetch_hs300_pe_history",
        lambda: {"1900-01-01": 15.0, "2026-08-18": 13.77},
    )

    r = FundamentalsService().rates_history(lookback_days=365)
    assert r["series"]["cape_us"]["values"] == [42.35]
    assert r["series"]["cape_us"]["unit"] == "倍"
    assert r["series"]["pe_cn"]["values"] == [13.77]
    assert r["errors"] == []


def test_valuation_history_failure_surfaces_in_rates_history_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """估值分位序列取数失败时降级为空序列并写入 errors，不影响其余序列。"""

    def boom_pe() -> dict[str, float]:
        raise sources.FundamentalsSourceError("akshare 超时")

    monkeypatch.setattr(sources, "fetch_treasury_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_vix_history", lambda lookback_days=730: {})
    monkeypatch.setattr(sources, "fetch_margin_history", lambda lookback_days=730: {})
    monkeypatch.setattr(
        sources, "fetch_cn_erp_history",
        lambda lookback_days=730, treasury_hist=None: {},
    )
    monkeypatch.setattr(
        sources, "fetch_us_erp_history",
        lambda lookback_days=730, treasury_hist=None: {},
    )
    monkeypatch.setattr(sources, "fetch_us_cape_history", lambda: {"2026-08-01": 42.35})
    monkeypatch.setattr(sources, "fetch_hs300_pe_history", boom_pe)

    r = FundamentalsService().rates_history(lookback_days=365)
    assert r["series"]["cape_us"]["values"] == [42.35]
    assert r["series"]["pe_cn"]["values"] == []
    assert any("A股PE历史" in e for e in r["errors"])
    assert not any("CAPE" in e for e in r["errors"])
