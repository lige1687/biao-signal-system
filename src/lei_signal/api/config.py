"""看盘系统后端配置：默认大盘、TTL、存储路径。

默认大盘列表使用**显式全后缀符号**：裸 6 位代码会被 resolve_symbol
按股票规则路由（如 000001 → 000001.SZ 平安银行），指数必须写 .SS。
市场标签覆盖只作用于展示层（如 ^KS11 经 Yahoo 可得但 symbols.py 会
误标为美股），不改 symbols.py 的市场枚举。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from lei_signal.data.cache import DEFAULT_CACHE_DIR


@dataclass(frozen=True, slots=True)
class DashboardIndex:
    """一只默认大盘指数（展示层覆盖名与市场标签）。"""

    symbol: str
    display_name: str
    market_cn: str


DASHBOARD_INDICES: tuple[DashboardIndex, ...] = (
    DashboardIndex("000001.SS", "上证指数", "A股"),
    DashboardIndex("000688.SS", "科创50", "A股"),
    DashboardIndex("000300.SS", "沪深300", "A股"),
    DashboardIndex("^IXIC", "纳斯达克", "美股"),
    DashboardIndex("^GSPC", "标普500", "美股"),
    DashboardIndex("^HSTECH", "恒生科技", "港股"),
    DashboardIndex("^KS11", "韩国KOSPI", "韩国"),
)

#: 符号 → 展示覆盖。自选股若与默认大盘同符号，同样套用覆盖名/市场标签。
INDEX_OVERRIDES: dict[str, DashboardIndex] = {idx.symbol: idx for idx in DASHBOARD_INDICES}

DEFAULT_QUOTE_TTL_SECONDS = 900
ERROR_TTL_SECONDS = 60
SPARKLINE_BARS = 60
KEY_CHANGE_LOOKBACK_DAYS = 120
DETAIL_MAX_BARS = 400
RECENT_EVENTS_LIMIT = 60

DISCLAIMER_CN = (
    "本系统为技术信号研究工具，所有信号仅为客观观察记录，不构成任何买卖建议。"
    "数据延迟约 15 分钟。"
)


def cache_root() -> str:
    """与 Streamlit 端共用 LEI_CACHE_ROOT，避免两个前端维护分裂的缓存。"""
    return os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR))


def sqlite_path() -> str:
    return os.environ.get("LEI_SQLITE_PATH", str(DEFAULT_CACHE_DIR.parent / "lab.db"))


def quote_ttl_seconds() -> int:
    return int(os.environ.get("LEI_QUOTE_TTL_SECONDS", str(DEFAULT_QUOTE_TTL_SECONDS)))
