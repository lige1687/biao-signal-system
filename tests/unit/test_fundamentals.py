"""基本面参考层：service 降级与缓存行为的单元测试（不打真实网络）。"""
from __future__ import annotations

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
        sources, "fetch_margin_history",
        lambda lookback_days=730: {
            "2026-08-12": {"rzrqye_yi": 26500.0, "rzyezb_pct": 2.61},
            "2026-08-13": {"rzrqye_yi": 26757.18, "rzyezb_pct": 2.64},
        },
    )

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


# ── 美国宏观（FRED）：派生计算 / 逐序列降级 / 缓存 ────────────────────────


def _weekly_dates(n: int = 30) -> list[str]:
    from datetime import date, timedelta

    d0 = date(2026, 1, 3)
    return [(d0 + timedelta(days=7 * i)).isoformat() for i in range(n)]


def _monthly_dates(n: int = 26) -> list[str]:
    # 从 2024-01 起的 n 个月（字符串序 = 时间序）
    ys, ms = 2024, 1
    out = []
    for i in range(n):
        y, m = ys + (ms - 1 + i) // 12, (ms - 1 + i) % 12 + 1
        out.append(f"{y:04d}-{m:02d}-01")
    return out


def _fake_fred(series_id: str, *, cosd: str | None = None) -> dict[str, float]:
    weekly = {d: 200000.0 + i * 1000 for i, d in enumerate(_weekly_dates())}
    monthly = {d: 150000.0 + i * 100 for i, d in enumerate(_monthly_dates())}
    if series_id == "ICSA":
        return weekly
    if series_id == "CCSA":
        return {d: 1700000.0 + i * 5000 for i, d in enumerate(_weekly_dates())}
    if series_id == "WEI":
        return {d: 2.0 + i * 0.01 for i, d in enumerate(_weekly_dates())}
    if series_id == "BAMLH0A0HYM2":
        return {"2026-08-24": 2.7, "2026-08-25": 2.69}
    return monthly  # PAYEMS/HSN1F/CSUSHPINSA/TOTALSA/PPIFIS/CPIAUCSL/DGORDER


def test_fetch_us_macro_derives_ma4_and_yoy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "_FRED_PAUSE", 0)
    monkeypatch.setattr(sources, "_fetch_fred_series", _fake_fred)

    r = sources.fetch_us_macro()

    assert r["errors"] == []
    assert [it["key"] for it in r["items"]] == [s["key"] for s in sources._US_MACRO_SPEC]
    # 初请：value = 最后 4 周均值，且 note 带本周值
    icwa = next(it for it in r["items"] if it["key"] == "icwa")
    last4 = sum(200000.0 + i * 1000 for i in range(26, 30)) / 4
    assert icwa["value"] == pytest.approx(last4, abs=0.1)
    assert "本周 22.9 万" in icwa["note_cn"]
    # 非农同比：最后一点 vs 12 个月前
    payems = next(it for it in r["items"] if it["key"] == "payems_yoy")
    assert payems["value"] == pytest.approx((152500.0 / 151300.0 - 1) * 100, abs=0.01)
    assert "月净增" in payems["note_cn"]
    # 派生序列：yoy 首点为第 13 个月、ma4 首点为第 4 周
    assert len(r["series"]["payems_yoy"]["values"]) == 26 - 12
    assert len(r["series"]["icwa"]["values"]) == 30 - 3
    assert r["as_of"] == max(it["date"] for it in r["items"])


def test_fetch_us_macro_degrades_per_series(monkeypatch: pytest.MonkeyPatch) -> None:
    def flaky(series_id: str, *, cosd: str | None = None) -> dict[str, float]:
        if series_id == "WEI":
            raise sources.FundamentalsSourceError("限流")
        return _fake_fred(series_id)

    monkeypatch.setattr(sources, "_FRED_PAUSE", 0)
    monkeypatch.setattr(sources, "_fetch_fred_series", flaky)

    r = sources.fetch_us_macro()

    assert "wei" not in r["series"]
    assert len(r["items"]) == len(sources._US_MACRO_SPEC) - 1
    assert any("周经济指数" in e for e in r["errors"])


def test_service_us_macro_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fetch() -> dict:
        calls["n"] += 1
        return {"as_of": None, "items": [], "series": {}, "errors": []}

    monkeypatch.setattr(sources, "fetch_us_macro", fetch)
    svc = FundamentalsService()
    svc.us_macro()
    svc.us_macro()
    assert calls["n"] == 1
    svc.us_macro(refresh=True)
    assert calls["n"] == 2


def test_etf_strength_includes_rel_lines_and_xly_xlp(monkeypatch: pytest.MonkeyPatch) -> None:
    """ETF 相对强度应带出相对净值线（起点=100）与可选/必选消费比价 XLY/XLP。"""
    from datetime import date, timedelta

    tickers = [t for t, _, _ in sources._ETF_SECTORS] + ["SPY"]
    days = [(date(2026, 1, 5) + timedelta(days=i)).isoformat() for i in range(80)]
    # 每个 ticker 恒定价格（100 + 序号）-> 相对比价恒定，便于断言
    closes = {t: [(d, 100.0 + i) for d in days] for i, t in enumerate(tickers)}
    monkeypatch.setattr(sources, "_yf_closes", lambda ts, period="6mo": closes)

    r = sources.fetch_etf_strength()

    assert r is not None
    assert len(r["dates"]) == 80
    assert len(r["items"]) == 11
    xly = next(it for it in r["items"] if it["code"] == "XLY")
    assert xly["rel_line"][0] == 100  # 窗口起点归一为 100
    assert xly["rel_line"][-1] == 100  # 恒定价格 -> 恒定比价（跑平 SPY）
    assert r["xly_xlp"] is not None
    assert r["xly_xlp"]["ratio"] == pytest.approx(100.0 / 101.0, abs=1e-3)
    assert r["xly_xlp"]["chg_1m"] == 0.0
    assert r["xly_xlp"]["chg_3m"] == 0.0
