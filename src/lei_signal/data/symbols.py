"""输入代码清洗与市场识别。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Market(StrEnum):
    US = "us"
    HK = "hk"
    CN_SH = "cn_sh"
    CN_SZ = "cn_sz"
    SECTOR = "sector"
    OTHER = "other"


MARKET_CN: dict[str, str] = {
    "us": "美股",
    "hk": "港股",
    "cn_sh": "沪市",
    "cn_sz": "深市",
    "sector": "板块",
    "other": "其他",
}


@dataclass(frozen=True, slots=True)
class SymbolInfo:
    """标准化后的标的标识。"""

    symbol: str          # Yahoo 口径，例如 159915.SZ
    market: Market
    bare_code: str       # 去掉后缀的原始代码，例如 159915
    timezone: str        # 交易所本地时区

    @property
    def market_cn(self) -> str:
        return MARKET_CN[self.market.value]


#: 沪市代码前缀。6xxxxx 为主板股票，5xxxxx 为沪市 ETF/基金，9xxxxx 为 B 股。
_SH_PREFIXES = ("5", "6", "9")


def normalize_symbol(raw: str) -> str:
    """把用户输入统一为 Yahoo 口径代码。"""
    return resolve_symbol(raw).symbol


def resolve_symbol(raw: str) -> SymbolInfo:
    """识别市场并补全后缀。

    六位纯数字按前缀补 .SS/.SZ；港股要求显式 .HK，避免与 A 股六位码混淆。
    """
    symbol = raw.strip().upper()
    if not symbol:
        raise ValueError("请输入股票或ETF代码")

    if re.fullmatch(r"\d{6}", symbol):
        if symbol.startswith(_SH_PREFIXES):
            return SymbolInfo(f"{symbol}.SS", Market.CN_SH, symbol, "Asia/Shanghai")
        return SymbolInfo(f"{symbol}.SZ", Market.CN_SZ, symbol, "Asia/Shanghai")

    # 东财板块代码：BK + 4 位数字（如 BK0457 电网设备）。
    # .SECTOR 后缀避免与 A 股六位码 / ETF 混淆。
    if re.fullmatch(r"BK\d{4}", symbol):
        return SymbolInfo(f"{symbol}.SECTOR", Market.SECTOR, symbol, "Asia/Shanghai")

    if not re.fullmatch(r"[A-Z0-9.^=\-]+", symbol):
        raise ValueError("代码格式无法识别；港股请使用 0700.HK 形式")

    if symbol.endswith(".SS"):
        return SymbolInfo(symbol, Market.CN_SH, symbol[:-3], "Asia/Shanghai")
    if symbol.endswith(".SZ"):
        return SymbolInfo(symbol, Market.CN_SZ, symbol[:-3], "Asia/Shanghai")
    if symbol.endswith(".HK"):
        return SymbolInfo(symbol, Market.HK, symbol[:-3], "Asia/Hong_Kong")
    if "." not in symbol:
        return SymbolInfo(symbol, Market.US, symbol, "America/New_York")
    return SymbolInfo(symbol, Market.OTHER, symbol.split(".")[0], "UTC")


def is_a_share(info: SymbolInfo) -> bool:
    """是否 A 股标的（可使用东方财富增强源）。"""
    return info.market in (Market.CN_SH, Market.CN_SZ)


def eastmoney_secid(info: SymbolInfo) -> str:
    """A 股代码到东方财富 secid 的映射。

    移植说明：secid 的 `market.code` 形式来自
    licai-wt-pg-integration@2ee7fdc src/plan_guardian/adapters/market/eastmoney_source.py
    （ProviderSecid）。旧实现要求外部映射目录显式提供 secid；此处改为按交易所
    后缀直接推导，因为新项目只处理公开的沪深代码，不涉及 FundId 映射目录。
    market 1 = 沪市，0 = 深市。
    """
    if not is_a_share(info):
        raise ValueError(f"{info.symbol} 不是 A 股标的，无法映射 secid")
    prefix = "1" if info.market is Market.CN_SH else "0"
    return f"{prefix}.{info.bare_code}"


__all__ = [
    "MARKET_CN",
    "Market",
    "SymbolInfo",
    "eastmoney_secid",
    "is_a_share",
    "normalize_symbol",
    "resolve_symbol",
]
