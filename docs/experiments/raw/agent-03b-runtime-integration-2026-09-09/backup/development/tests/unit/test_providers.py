"""Provider 测试：不依赖网络，使用假客户端。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from lei_signal.data.cache import ParquetCache
from lei_signal.data.providers import (
    ChainedPriceProvider,
    EastmoneyPriceProvider,
    TencentPriceProvider,
    YahooPriceProvider,
)
from lei_signal.data.validation import DataUnavailableError


def _yahoo_frame(rows: int = 30) -> pd.DataFrame:
    close = np.linspace(10.0, 20.0, rows)
    return pd.DataFrame(
        {
            "Open": close - 0.1,
            "High": close + 0.2,
            "Low": close - 0.2,
            "Close": close,
            "Volume": [1_000_000] * rows,
        },
        index=pd.to_datetime(pd.bdate_range("2024-01-02", periods=rows), utc=True),
    )


class FakeTicker:
    info = {"shortName": "Invesco QQQ Trust"}

    def __init__(self, rows: int = 30) -> None:
        self._rows = rows
        self.last_kwargs: dict[str, object] = {}

    def history(self, **kwargs: object) -> pd.DataFrame:
        self.last_kwargs = kwargs
        return _yahoo_frame(self._rows)


def test_yahoo_provider_normalizes_columns_and_requests_adjusted_data() -> None:
    ticker = FakeTicker()
    provider = YahooPriceProvider(ticker_factory=lambda _: ticker, sleep=lambda _: None)
    data = provider.fetch("qqq")

    assert data.symbol == "QQQ"
    assert data.display_name == "Invesco QQQ Trust"
    assert data.bars.columns.tolist() == ["open", "high", "low", "close", "volume"]
    assert data.bars.index.tz is None
    # 必须请求复权数据
    assert ticker.last_kwargs["auto_adjust"] is True
    assert ticker.last_kwargs["interval"] == "1d"
    assert data.report.adjusted is True
    assert data.report.provider == "yahoo"


def test_yahoo_provider_reports_data_unavailable_on_empty_result() -> None:
    class EmptyTicker:
        info: dict[str, str] = {}

        def history(self, **_: object) -> pd.DataFrame:
            return pd.DataFrame()

    provider = YahooPriceProvider(
        ticker_factory=lambda _: EmptyTicker(), sleep=lambda _: None
    )
    with pytest.raises(DataUnavailableError, match="没有找到"):
        provider.fetch("NOPE")


def test_yahoo_provider_wraps_network_errors_in_chinese() -> None:
    def boom(_: str) -> object:
        raise RuntimeError("connection reset")

    with pytest.raises(DataUnavailableError, match="无法获取"):
        YahooPriceProvider(ticker_factory=boom, sleep=lambda _: None).fetch("QQQ")


def _eastmoney_payload(rows: int = 30) -> str:
    klines = []
    for i in range(rows):
        day = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        klines.append(
            f"{day.date()},{close - 0.05},{close},{close + 0.08},{close - 0.09},"
            f"{1_000_000 + i},{12345678},1.2"
        )
    return json.dumps({"data": {"code": "159915", "market": 0, "name": "创业板ETF",
                                "klines": klines}})


def test_eastmoney_provider_parses_klines_and_requests_adjusted() -> None:
    captured: dict[str, str] = {}

    def opener(url: str) -> str:
        captured["url"] = url
        return _eastmoney_payload()

    provider = EastmoneyPriceProvider(opener=opener, sleep=lambda _: None)
    data = provider.fetch("159915")

    assert data.symbol == "159915.SZ"
    assert data.display_name == "创业板ETF"
    assert len(data.bars) == 30
    assert data.bars.columns.tolist() == ["open", "high", "low", "close", "volume"]
    # 改造点：必须使用前复权 fqt=1，而不是旧实现的 fqt=0
    assert "fqt=1" in captured["url"]
    assert "secid=0.159915" in captured["url"]
    assert data.report.adjusted is True


def test_eastmoney_provider_rejects_non_a_share() -> None:
    provider = EastmoneyPriceProvider(opener=lambda _: "{}", sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="不是 A 股"):
        provider.fetch("QQQ")


def test_eastmoney_provider_surfaces_malformed_payloads() -> None:
    with pytest.raises(DataUnavailableError, match="非 JSON"):
        EastmoneyPriceProvider(
            opener=lambda _: "<html>error</html>", sleep=lambda _: None
        ).fetch("159915")
    with pytest.raises(DataUnavailableError, match="缺少 data"):
        EastmoneyPriceProvider(opener=lambda _: '{"rc":1}', sleep=lambda _: None).fetch("159915")
    with pytest.raises(DataUnavailableError, match="没有返回日线"):
        EastmoneyPriceProvider(
            opener=lambda _: '{"data":{"code":"159915","market":0,"klines":[]}}',
            sleep=lambda _: None,
        ).fetch("159915")


def test_chained_provider_prefers_eastmoney_for_a_shares() -> None:
    order: list[str] = []

    class Recorder:
        def __init__(self, name: str, succeed: bool) -> None:
            self.name = name
            self._succeed = succeed

        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN202
            order.append(self.name)
            if not self._succeed:
                raise DataUnavailableError(f"{self.name} 不可用")
            return EastmoneyPriceProvider(
                opener=lambda _: _eastmoney_payload(), sleep=lambda _: None
            ).fetch(symbol)

    chained = ChainedPriceProvider([Recorder("yahoo", False), Recorder("eastmoney", True)])
    chained.fetch("159915")
    assert order[0] == "eastmoney"


def test_chained_provider_reports_all_failures() -> None:
    class Failing:
        def __init__(self, name: str) -> None:
            self.name = name

        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN202
            raise DataUnavailableError(f"{self.name} 挂了")

    chained = ChainedPriceProvider([Failing("yahoo"), Failing("eastmoney")])
    with pytest.raises(DataUnavailableError, match="所有行情源均不可用") as exc:
        chained.fetch("QQQ")
    assert "yahoo" in str(exc.value)
    assert "eastmoney" in str(exc.value)


def test_parquet_cache_roundtrip_and_corruption_is_a_miss(tmp_path) -> None:  # noqa: ANN001
    cache = ParquetCache(tmp_path)
    frame = _yahoo_frame(25).rename(columns=str.lower)
    frame.index = frame.index.tz_localize(None)
    # provider 必须显式声明为可信来源，否则命中会被来源校验拦掉，
    # 下面的「损坏文件视为未命中」就会因为错误的原因通过。
    entry = cache.write("QQQ", frame, provider="yahoo")
    assert entry.rows == 25

    loaded = cache.read("QQQ", required_columns=("open", "close"))
    assert loaded is not None and len(loaded) == 25

    # 缺列视为未命中
    assert cache.read("QQQ", required_columns=("nonexistent",)) is None
    # 损坏文件视为未命中，不得抛出
    entry.path.write_bytes(b"not parquet")
    assert cache.read("QQQ") is None
    assert cache.read("NEVER_FETCHED") is None


def test_eastmoney_retries_transient_failures_before_giving_up() -> None:
    """瞬时中断应重试；成功后不得报告不可用。"""
    calls: list[int] = []

    def flaky(_: str) -> str:
        calls.append(1)
        if len(calls) < 3:
            raise DataUnavailableError("东方财富连接中断：RemoteDisconnected")
        return _eastmoney_payload()

    provider = EastmoneyPriceProvider(opener=flaky, attempts=3, sleep=lambda _: None)
    data = provider.fetch("159915")
    assert len(calls) == 3
    assert len(data.bars) == 30


def test_eastmoney_reports_last_error_after_exhausting_retries() -> None:
    attempts: list[int] = []

    def always_fail(_: str) -> str:
        attempts.append(1)
        raise DataUnavailableError("东方财富连接中断：RemoteDisconnected")

    provider = EastmoneyPriceProvider(opener=always_fail, attempts=3, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="连接中断"):
        provider.fetch("159915")
    assert len(attempts) == 3


def test_eastmoney_rotates_hosts_across_retry_budget() -> None:
    """重试预算摊到不同号段主机：单主机被掐时下一次尝试换主机，总次数仍为 attempts。"""
    urls: list[str] = []

    def always_fail(url: str) -> str:
        urls.append(url)
        raise DataUnavailableError("东方财富连接中断：RemoteDisconnected")

    provider = EastmoneyPriceProvider(opener=always_fail, attempts=3, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError):
        provider.fetch("159915")
    hosts = {url.split("?")[0] for url in urls}
    assert len(urls) == 3
    assert len(hosts) == 3


def test_yahoo_retries_rate_limit_then_succeeds() -> None:
    state: list[int] = []

    class Flaky:
        info = {"shortName": "Invesco QQQ Trust"}

        def history(self, **_: object) -> pd.DataFrame:
            state.append(1)
            if len(state) < 2:
                raise RuntimeError("Too Many Requests. Rate limited.")
            return _yahoo_frame(30)

    provider = YahooPriceProvider(
        ticker_factory=lambda _: Flaky(), attempts=3, sleep=lambda _: None
    )
    data = provider.fetch("QQQ")
    assert len(state) == 2
    assert len(data.bars) == 30


def test_network_errors_are_always_data_unavailable_not_raw_exceptions() -> None:
    """OSError 子类(RemoteDisconnected 等)不得穿透到界面。"""
    from http.client import RemoteDisconnected

    def disconnect(_: str) -> str:
        raise RemoteDisconnected("Remote end closed connection without response")

    provider = EastmoneyPriceProvider(opener=disconnect, attempts=1, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError):
        provider.fetch("159915")


# ---------- 腾讯 provider ----------

def _tencent_payload(rows: int = 30, market_key: str = "sz159915") -> str:
    qfqday = []
    for i in range(rows):
        day = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        qfqday.append([
            day.strftime("%Y-%m-%d"),
            f"{close - 0.05:.4f}",   # open
            f"{close:.4f}",          # close
            f"{close + 0.08:.4f}",   # high
            f"{close - 0.09:.4f}",   # low
            f"{1_000_000 + i}",      # volume
        ])
    return json.dumps({
        "code": 0,
        "msg": "",
        "data": {market_key: {"qfqday": qfqday, "qfqfactor": 1.0}},
    })


def test_tencent_provider_parses_qfqday_and_is_marked_adjusted() -> None:
    captured: dict[str, str] = {}

    def opener(url: str) -> str:
        captured["url"] = url
        return _tencent_payload()

    provider = TencentPriceProvider(opener=opener, sleep=lambda _: None)
    data = provider.fetch("159915")

    assert data.symbol == "159915.SZ"
    assert len(data.bars) == 30
    assert data.bars.columns.tolist() == ["open", "high", "low", "close", "volume"]
    # 必须显式请求 qfq 前复权
    assert "qfq" in captured["url"]
    assert "param=sz159915" in captured["url"]
    assert data.report.adjusted is True
    assert data.report.provider == "tencent"


def test_tencent_provider_uses_sh_prefix_for_shanghai() -> None:
    captured: dict[str, str] = {}

    def opener(url: str) -> str:
        captured["url"] = url
        return _tencent_payload(market_key="sh600000")

    provider = TencentPriceProvider(opener=opener, sleep=lambda _: None)
    provider.fetch("600000")
    assert "param=sh600000" in captured["url"]


def test_tencent_provider_rejects_non_a_share() -> None:
    provider = TencentPriceProvider(opener=lambda _: "{}", sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="不是 A 股"):
        provider.fetch("QQQ")


def test_tencent_provider_surfaces_qfqday_missing() -> None:
    """qfqday 和 day 都缺失时必须显式报错。"""
    payload = json.dumps({"code": 0, "data": {"sz159915": {}}})
    provider = TencentPriceProvider(opener=lambda _: payload, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="未返回 qfqday/day"):
        provider.fetch("159915")


def test_tencent_provider_etf_falls_back_to_unadjusted_day() -> None:
    """ETF 场景：qfqday 缺失但 day 有数据时，回退到不复权并如实标记。"""
    day_rows = []
    for i in range(30):
        day = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        close = 10.0 + i * 0.1
        day_rows.append([
            day.strftime("%Y-%m-%d"),
            f"{close - 0.05:.4f}",
            f"{close:.4f}",
            f"{close + 0.08:.4f}",
            f"{close - 0.09:.4f}",
            f"{1_000_000 + i}",
        ])
    # 只有 day，没有 qfqday —— ETF 常见情况
    payload = json.dumps({"code": 0, "data": {"sh515130": {"day": day_rows}}})
    provider = TencentPriceProvider(opener=lambda _: payload, sleep=lambda _: None)
    data = provider.fetch("515130")

    assert data.symbol == "515130.SS"
    assert len(data.bars) == 30
    # 必须如实标记不复权
    assert data.report.adjusted is False
    # 必须有警告说明回退原因
    assert any("未返回前复权" in str(w) for w in data.report.warnings)


def test_tencent_provider_surfaces_error_code() -> None:
    payload = json.dumps({"code": 1, "msg": "param invalid"})
    provider = TencentPriceProvider(opener=lambda _: payload, sleep=lambda _: None)
    with pytest.raises(DataUnavailableError, match="腾讯返回错误"):
        provider.fetch("159915")


def test_tencent_provider_surfaces_malformed_payloads() -> None:
    with pytest.raises(DataUnavailableError, match="非 JSON"):
        TencentPriceProvider(
            opener=lambda _: "<html>error</html>", sleep=lambda _: None
        ).fetch("159915")
    with pytest.raises(DataUnavailableError, match="缺少 data"):
        TencentPriceProvider(
            opener=lambda _: '{"code":0,"rc":1}', sleep=lambda _: None
        ).fetch("159915")
    with pytest.raises(DataUnavailableError, match="qfqday 元素字段不足"):
        TencentPriceProvider(
            opener=lambda _: json.dumps({"code": 0, "data": {"sz159915": {"qfqday": [[]]}}}),
            sleep=lambda _: None,
        ).fetch("159915")


def test_tencent_provider_retries_transient_failures_then_succeeds() -> None:
    calls: list[int] = []

    def flaky(_: str) -> str:
        calls.append(1)
        if len(calls) < 3:
            raise DataUnavailableError("腾讯连接中断：RemoteDisconnected")
        return _tencent_payload()

    provider = TencentPriceProvider(opener=flaky, attempts=3, sleep=lambda _: None)
    data = provider.fetch("159915")
    assert len(calls) == 3
    assert len(data.bars) == 30


def test_chained_provider_prefers_tencent_for_a_shares() -> None:
    """腾讯是 A 股新主源，必须排在东方财富之前。"""
    order: list[str] = []

    class Recorder:
        def __init__(self, name: str, succeed: bool) -> None:
            self.name = name
            self._succeed = succeed

        def fetch(self, symbol: str, *, min_rows: int = 21):  # noqa: ANN202
            order.append(self.name)
            if not self._succeed:
                raise DataUnavailableError(f"{self.name} 不可用")
            return TencentPriceProvider(
                opener=lambda _: _tencent_payload(), sleep=lambda _: None
            ).fetch(symbol)

    chained = ChainedPriceProvider(
        [Recorder("yahoo", False), Recorder("eastmoney", False), Recorder("tencent", True)]
    )
    chained.fetch("159915")
    assert order[0] == "tencent"


def test_chained_provider_skips_sina_when_tencent_present() -> None:
    """Sina 已退出默认链路——默认 Provider 链中不应出现它。"""
    from lei_signal.data.providers import default_provider

    chain = default_provider()._providers  # noqa: SLF001 - 测试可见私有
    names = [provider.name for provider in chain]
    assert "sina" not in names
    assert names[0] == "tencent"


def test_yahoo_v8_parses_payload_and_supports_overseas_index() -> None:
    """Yahoo v8 公开图表 API：解析字段正确 + 海外指数（如 ^KS11）走通。

    之前 yfinance 走 query2 端点会触发 IP 限流（429），新 provider 改走
    query1/v8，实测稳定。fail_open 行为：异常 / 字段缺失 → DataUnavailableError。
    """
    import json

    from lei_signal.data.providers import DataUnavailableError, YahooV8PriceProvider

    # 真实 v8 响应形状（截取 1 根 bar 的关键字段）
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "KRW",
                        "symbol": "^KS11",
                        "longName": "KOSPI Composite Index",
                    },
                    "timestamp": [1754000000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [6200.5],
                                "high": [6260.0],
                                "low": [6198.0],
                                "close": [6257.45],
                                "volume": [272959],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }

    p = YahooV8PriceProvider(opener=lambda _u: json.dumps(payload))
    result = p.fetch("^KS11", min_rows=1)
    assert result.symbol == "^KS11"
    assert result.display_name == "KOSPI Composite Index"
    assert result.bars["close"].iloc[-1] == 6257.45
    assert result.bars["volume"].iloc[-1] == 272959

    # 错误响应：必须 raise 而非返回空
    p_err = YahooV8PriceProvider(
        opener=lambda _u: json.dumps({"chart": {"result": [], "error": None}})
    )
    try:
        p_err.fetch("^KS11")
    except DataUnavailableError as exc:
        assert "无数据" in str(exc)
    else:
        raise AssertionError("expected DataUnavailableError on empty result")

    # 网络异常：原样向上抛 DataUnavailableError，不抛 OSError
    def boom(_u: str) -> str:
        raise OSError("connection reset")

    try:
        YahooV8PriceProvider(opener=boom).fetch("^KS11")
    except DataUnavailableError as exc:
        assert "请求失败" in str(exc)
    else:
        raise AssertionError("expected DataUnavailableError on network failure")


def test_ths_board_provider_parses_line_payload() -> None:
    """同花顺行业板块：解析 line js 的 字段顺序 日期,开,高,低,收,量,额。

    实测 d.10jqka.com.cn/v4/line/bk_881278/01/2026.js 返回该顺序，
    高在收前（与 OHLC 惯例相反），解析时必须对调，否则 OHLC 校验失败。
    """
    from lei_signal.data.providers import THSBoardProvider

    # 模拟两年份的 JSONP 响应：quotebridge_v4_line_bk_{code}_01_{year}({"data":"..."})
    def fake_opener(url: str, headers: dict) -> str:  # noqa: ARG001
        if "2025" in url:
            data = "20250102,100.0,105.0,99.0,104.0,1000,100000,,,,0"
            return f'quotebridge_v4_line_bk_881278_01_2025({{"data":"{data}"}})'
        data = "20260105,104.0,106.0,103.0,105.5,1200,120000,,,,0"
        return f'quotebridge_v4_line_bk_881278_01_2026({{"data":"{data}"}})'  # noqa: E501

    p = THSBoardProvider(opener=fake_opener, start_year=2025)  # type: ignore[arg-type]
    # 跳过 cookie 计算（opener 已注入，不会调 _compute_cookie）
    p._cookie = "fake"  # type: ignore[assignment]
    result = p.fetch("TH881278", min_rows=1)
    b = result.bars
    assert len(b) == 2
    # 2026 行：开104 高106 低103 收105.5
    last = b.iloc[-1]
    assert last["open"] == 104.0
    assert last["high"] == 106.0
    assert last["low"] == 103.0
    assert last["close"] == 105.5
    assert last["volume"] == 1200.0


def test_ths_board_provider_rejects_non_sector_symbol() -> None:
    from lei_signal.data.providers import THSBoardProvider

    p = THSBoardProvider()
    assert p.supports("TH881278") is True
    assert p.supports("000001.SS") is False
    assert p.supports("BK0457") is False


def test_ths_board_provider_appends_intraday_today_bar() -> None:
    """盘中增强：today.js 日期比年文件新且 OHLC 自洽时，追加当日形成中 bar。

    实测 today.js 字段（2026-08-19 盘中验证）：1=日期 7=开 8=高 9=低
    11=现价 13=量。通信设备/半导体/银行/电力同日互证，与年文件口径一致。
    """
    from lei_signal.data.providers import THSBoardProvider

    def fake_opener(url: str, headers: dict) -> str:  # noqa: ARG001
        if "today" in url:
            quote = (
                '{"bk_881278":{"1":"20260106","7":"106.0","8":"107.5",'
                '"9":"105.0","11":"107.0","13":1500,"19":"160000","dt":"1030"}}'
            )
            return f"quotebridge_v4_line_bk_881278_01_today({quote})"
        if "2025" in url:
            data = "20250102,100.0,105.0,99.0,104.0,1000,100000,,,,0"
            return f'quotebridge_v4_line_bk_881278_01_2025({{"data":"{data}"}})'
        data = "20260105,104.0,106.0,103.0,105.5,1200,120000,,,,0"
        return f'quotebridge_v4_line_bk_881278_01_2026({{"data":"{data}"}})'

    p = THSBoardProvider(opener=fake_opener, start_year=2025)  # type: ignore[arg-type]
    p._cookie = "fake"  # type: ignore[assignment]
    b = p.fetch("TH881278", min_rows=1).bars
    assert len(b) == 3
    last = b.iloc[-1]
    assert b.index[-1] == pd.Timestamp("2026-01-06")
    assert (last["open"], last["high"], last["low"], last["close"]) == (106.0, 107.5, 105.0, 107.0)
    assert last["volume"] == 1500.0


def test_ths_board_provider_skips_stale_or_bad_today_quote() -> None:
    """today.js 追加的守门：日期不比历史新、或 OHLC 不自洽时不得追加。"""
    from lei_signal.data.providers import THSBoardProvider

    year_payload = (
        '{"data":"20260105,104.0,106.0,103.0,105.5,1200,120000,,,,0"}'
    )

    def make_opener(today_body: str):
        def fake_opener(url: str, headers: dict) -> str:  # noqa: ARG001
            if "today" in url:
                return f"quotebridge_v4_line_bk_881278_01_today({today_body})"
            return f'quotebridge_v4_line_bk_881278_01_2026({year_payload})'

        return fake_opener

    # 日期与历史最后一根相同（盘前/收盘后已并入年文件）：不追加
    same_day = json.dumps({"bk_881278": {"1": "20260105", "7": "106.0", "8": "107.0", "9": "105.0",
                                          "11": "106.5", "13": 100}})
    p = THSBoardProvider(opener=make_opener(same_day), start_year=2026)  # type: ignore[arg-type]
    p._cookie = "fake"  # type: ignore[assignment]
    assert len(p.fetch("TH881278", min_rows=1).bars) == 1

    # OHLC 不自洽（high < open）：不追加
    bad_ohlc = json.dumps({"bk_881278": {"1": "20260106", "7": "106.0", "8": "105.0", "9": "104.0",
                                          "11": "105.5", "13": 100}})
    p2 = THSBoardProvider(opener=make_opener(bad_ohlc), start_year=2026)  # type: ignore[arg-type]
    p2._cookie = "fake"  # type: ignore[assignment]
    assert len(p2.fetch("TH881278", min_rows=1).bars) == 1
