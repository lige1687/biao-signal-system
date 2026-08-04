"""实时报价快照：换手率 / 量比 / 流通市值。

为什么单独一个源
----------------
日线 provider 只返回 OHLCV，算不出换手率（需要流通股本）。腾讯
``qt.gtimg.cn`` 的实时报价接口带换手率、量比、流通市值，正好补齐
「今日信息概述」需要的盘口维度。

覆盖范围（2026-08 实测）
------------------------
- 沪深 A 股与场内 ETF：完整（沪深300 换手 0.69%/量比 0.95；159915 换手 9.39%）。
- 海外指数（^IXIC / ^GSPC / ^HSTECH / ^KS11）：腾讯此接口**不覆盖**，
  返回 None。界面显示「—」，不得用日线数据推算冒充。

与分析解耦
----------
本模块失败绝不影响 K 线与 LEI 信号：调用方拿到 None 即可。
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from lei_signal.data.symbols import Market, SymbolInfo, is_a_share, resolve_symbol

#: 腾讯实时报价字段下标（~ 分隔，实测 88 字段）。
_IDX_NAME = 1
_IDX_PRICE = 3
_IDX_PREV_CLOSE = 4
_IDX_OPEN = 5
_IDX_CHANGE = 31
_IDX_CHANGE_PCT = 32
_IDX_TURNOVER_RATE = 38  # 换手率 %
_IDX_AMOUNT = 37  # 成交额（万元）
_IDX_FLOAT_CAP = 44  # 流通市值（亿元）
_IDX_TOTAL_CAP = 45  # 总市值（亿元）
_IDX_VOLUME_RATIO = 49  # 量比
_MIN_FIELDS = 50


@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    """盘口快照。任一字段都可能为 None（源未提供时不编数据）。"""

    symbol: str
    display_name: str | None = None
    price: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    turnover_rate: float | None = None  # 换手率 %
    volume_ratio: float | None = None  # 量比
    float_cap_yi: float | None = None  # 流通市值（亿元）
    total_cap_yi: float | None = None  # 总市值（亿元）
    amount_wan: float | None = None  # 成交额（万元）
    provider: str = "tencent_quote"


def _to_float(raw: str) -> float | None:
    """腾讯用 '-1' / '' / '0.00' 表示缺失或不适用；只把可解析的正常值放出去。"""
    text = raw.strip()
    if not text or text in ("-", "-1"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


class TencentQuoteProvider:
    """腾讯实时报价（仅 A 股与场内基金）。"""

    name = "tencent_quote"
    _HOST = "https://qt.gtimg.cn/q="

    def __init__(
        self,
        opener: Callable[[str], str] | None = None,
        *,
        timeout: float = 8.0,
    ) -> None:
        self._opener = opener or self._default_opener
        self._timeout = timeout

    def _default_opener(self, url: str) -> str:
        request = urllib.request.Request(  # noqa: S310 - 固定 https 主机
            url,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"},
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            # 腾讯该接口返回 GBK；errors="replace" 保证不因个别字符炸掉整条。
            return response.read().decode("gbk", errors="replace")

    @staticmethod
    def _tencent_code(info: SymbolInfo) -> str:
        prefix = "sh" if info.market is Market.CN_SH else "sz"
        return f"{prefix}{info.bare_code}"

    def supports(self, symbol: str) -> bool:
        try:
            return is_a_share(resolve_symbol(symbol))
        except ValueError:
            return False

    def fetch(self, symbol: str) -> QuoteSnapshot | None:
        """取盘口快照。不支持的市场或任何失败都返回 None，不抛异常。

        调用方（今日概述面板）把 None 显示为「—」；这里不做重试：
        盘口是锦上添花的维度，不值得为它拖慢整页。
        """
        try:
            info = resolve_symbol(symbol)
        except ValueError:
            return None
        if not is_a_share(info):
            return None

        try:
            text = self._opener(f"{self._HOST}{self._tencent_code(info)}")
        except (urllib.error.URLError, OSError, UnicodeError):
            return None

        parts = text.split("~")
        if len(parts) < _MIN_FIELDS:
            return None

        return QuoteSnapshot(
            symbol=info.symbol,
            display_name=parts[_IDX_NAME].strip() or None,
            price=_to_float(parts[_IDX_PRICE]),
            prev_close=_to_float(parts[_IDX_PREV_CLOSE]),
            change_pct=_to_float(parts[_IDX_CHANGE_PCT]),
            turnover_rate=_to_float(parts[_IDX_TURNOVER_RATE]),
            volume_ratio=_to_float(parts[_IDX_VOLUME_RATIO]),
            float_cap_yi=_to_float(parts[_IDX_FLOAT_CAP]),
            total_cap_yi=_to_float(parts[_IDX_TOTAL_CAP]),
            amount_wan=_to_float(parts[_IDX_AMOUNT]),
        )


__all__ = ["QuoteSnapshot", "TencentQuoteProvider"]
