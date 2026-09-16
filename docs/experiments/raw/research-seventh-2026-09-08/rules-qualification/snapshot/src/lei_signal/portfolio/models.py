"""持仓台账数据模型（migration 020 对应的领域对象）。

字段口径全部来自 2026-09-04 养基宝截图录入：
- market_value 是快照日市值（元），不是成本，不是份额；
- return_pct 是 App 显示的持有收益率（%），口径为「当前市值相对投入成本」；
- code 截图未显示，留空待补（后续接天天基金净值接口时回填）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: 分组的市场归属（展示用中文映射在 route 层做，这里只存稳定枚举）
MARKET_US = "us"
MARKET_CN = "cn"
MARKET_HK = "hk"
MARKET_OTHER = "other"
MARKETS = (MARKET_US, MARKET_CN, MARKET_HK, MARKET_OTHER)

#: portfolio_meta 的固定键
META_AS_OF = "as_of"
META_DATA_SOURCE = "data_source_cn"
META_OBSERVATIONS = "observations"


@dataclass(frozen=True, slots=True)
class PortfolioGroup:
    """一个赛道分组：持仓集合 + 「系统怎么看」结论。"""

    group_key: str
    name: str
    market: str
    sort_order: int
    verdict_cn: str
    verdict_basis: str = ""


@dataclass(frozen=True, slots=True)
class PortfolioHolding:
    """一只基金/ETF 持仓（快照行）。"""

    holding_id: str
    group_key: str
    name: str
    code: str | None
    market_value: float
    return_pct: float | None
    tags: tuple[str, ...] = field(default=())
    note: str = ""
    as_of: str = ""
