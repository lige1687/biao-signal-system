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
    DashboardIndex("000698.SS", "科创100", "A股"),
    DashboardIndex("000300.SS", "沪深300", "A股"),
    DashboardIndex("^IXIC", "纳斯达克", "美股"),
    DashboardIndex("^GSPC", "标普500", "美股"),
    DashboardIndex("^HSTECH", "恒生科技", "港股"),
    DashboardIndex("^HSI", "恒生指数", "港股"),
    DashboardIndex("^KS11", "韩国KOSPI", "韩国"),
)

#: 可添加的策略/规模/主题指数清单（供前端「策略指数」选择器使用）。
#: 全部实测数据可达（2026-08）。红利低波指数本身（930904）各源不覆盖，
#: 用 ETF 512890 代替；中证红利/上证红利可作为红利策略的指数口径。
STRATEGY_INDICES: tuple[DashboardIndex, ...] = (
    # 规模
    DashboardIndex("000016.SS", "上证50", "A股"),
    DashboardIndex("000905.SS", "中证500", "A股"),
    DashboardIndex("000852.SS", "中证1000", "A股"),
    DashboardIndex("399311.SZ", "国证2000", "A股"),
    DashboardIndex("399303.SZ", "国证300", "A股"),
    DashboardIndex("000985.SS", "中证全指", "A股"),
    # 红利 / 价值
    DashboardIndex("000922.SS", "中证红利", "A股"),
    DashboardIndex("000015.SS", "上证红利", "A股"),
    DashboardIndex("000925.SS", "基本面50", "A股"),
    # 主题
    DashboardIndex("000977.SS", "人工智能", "A股"),
    DashboardIndex("399967.SZ", "中证军工", "A股"),
    DashboardIndex("399006.SZ", "创业板指", "A股"),
    DashboardIndex("000688.SS", "科创50", "A股"),
    DashboardIndex("399005.SZ", "创业板50", "A股"),
    # 中证行业指数（93xxxx 系列挂东财 market=2 行情位，secid 特判见 symbols.py；
    # 其余 93 系可代码直输添加，按需在此登记进选择器）
    DashboardIndex("931160.SS", "通信设备（中证）", "A股"),
    # 海外
    DashboardIndex("^NDX", "纳斯达克100", "美股"),
    DashboardIndex("^DJI", "道琼斯", "美股"),
    DashboardIndex("^RUT", "罗素2000", "美股"),
    DashboardIndex("^VIX", "恐慌指数VIX", "美股"),
    DashboardIndex("^HSI", "恒生指数", "港股"),
)

#: 符号 → 展示覆盖。自选股若与默认大盘/策略指数同符号，同样套用覆盖名/市场标签。
#: 策略指数一并纳入：加自选后列表/解析卡片直接显示中文名与「A股」标签，
#: 而不是等首次分析回填或误标「沪市」。
INDEX_OVERRIDES: dict[str, DashboardIndex] = {
    idx.symbol: idx for idx in (*DASHBOARD_INDICES, *STRATEGY_INDICES)
}

#: 可添加的美股 ETF 清单（供前端「美股ETF」选择器使用）。
#: 全部实测数据可达（2026-08，49/49 成功，501 根日线）。
#: 命名规范：中文名 + 代码缩写，如「纳指100 QQQ」——中文表意，缩写保留可查性。
US_ETFS: tuple[DashboardIndex, ...] = (
    # 宽基
    DashboardIndex("SPY", "标普500 SPY", "美股"),
    DashboardIndex("IVV", "标普500 IVV", "美股"),
    DashboardIndex("VOO", "标普500 VOO", "美股"),
    DashboardIndex("QQQ", "纳指100 QQQ", "美股"),
    DashboardIndex("TQQQ", "纳指3倍多 TQQQ", "美股"),
    DashboardIndex("SQQQ", "纳指3倍空 SQQQ", "美股"),
    DashboardIndex("DIA", "道琼斯 DIA", "美股"),
    DashboardIndex("IWM", "罗素2000 IWM", "美股"),
    DashboardIndex("VTI", "全美市场 VTI", "美股"),
    # 行业 / 主题
    DashboardIndex("XLK", "科技 XLK", "美股"),
    DashboardIndex("VGT", "信息科技 VGT", "美股"),
    DashboardIndex("SMH", "半导体 SMH", "美股"),
    DashboardIndex("SOXX", "半导体 SOXX", "美股"),
    DashboardIndex("XLF", "金融 XLF", "美股"),
    DashboardIndex("XLE", "能源 XLE", "美股"),
    DashboardIndex("XLV", "医疗 XLV", "美股"),
    DashboardIndex("XBI", "生物科技 XBI", "美股"),
    DashboardIndex("XLI", "工业 XLI", "美股"),
    DashboardIndex("XLY", "可选消费 XLY", "美股"),
    DashboardIndex("XLP", "日常消费 XLP", "美股"),
    DashboardIndex("XLU", "公用事业 XLU", "美股"),
    DashboardIndex("XLB", "原材料 XLB", "美股"),
    DashboardIndex("XLC", "通信服务 XLC", "美股"),
    DashboardIndex("XLRE", "房地产 XLRE", "美股"),
    DashboardIndex("ARKK", "方舟创新 ARKK", "美股"),
    # 风格
    DashboardIndex("VUG", "成长 VUG", "美股"),
    DashboardIndex("VTV", "价值 VTV", "美股"),
    DashboardIndex("SCHD", "红利 SCHD", "美股"),
    DashboardIndex("JEPI", "备兑收益 JEPI", "美股"),
    # 海外市场
    DashboardIndex("EEM", "新兴市场 EEM", "美股"),
    DashboardIndex("IEMG", "新兴市场 IEMG", "美股"),
    DashboardIndex("EFA", "发达市场 EFA", "美股"),
    DashboardIndex("FXI", "中国大盘 FXI", "美股"),
    DashboardIndex("KWEB", "中概互联 KWEB", "美股"),
    DashboardIndex("INDA", "印度 INDA", "美股"),
    DashboardIndex("EWJ", "日本 EWJ", "美股"),
    # 债券 / 商品 / 地产
    DashboardIndex("TLT", "20年国债 TLT", "美股"),
    DashboardIndex("IEF", "7-10年国债 IEF", "美股"),
    DashboardIndex("AGG", "综合债券 AGG", "美股"),
    DashboardIndex("LQD", "投资级债 LQD", "美股"),
    DashboardIndex("HYG", "高收益债 HYG", "美股"),
    DashboardIndex("GLD", "黄金 GLD", "美股"),
    DashboardIndex("SLV", "白银 SLV", "美股"),
    DashboardIndex("IBIT", "比特币 IBIT", "美股"),
    DashboardIndex("USO", "原油 USO", "美股"),
    DashboardIndex("UNG", "天然气 UNG", "美股"),
    DashboardIndex("DBC", "综合商品 DBC", "美股"),
    DashboardIndex("VNQ", "房地产 VNQ", "美股"),
    DashboardIndex("IYR", "房地产 IYR", "美股"),
)

#: 海外指数/ETF 中文名覆盖：Yahoo 返回英文 longName，这里统一成
#: 「中文名 + 缩写」。合并进 INDEX_OVERRIDES 之外单独一张表，因为它
#: 覆盖的是自选股展示名而非大盘卡片。
OVERSEAS_NAME_CN: dict[str, str] = {
    # 美股指数
    "^IXIC": "纳斯达克",
    "^GSPC": "标普500",
    "^NDX": "纳指100 NDX",
    "^DJI": "道琼斯 DJI",
    "^RUT": "罗素2000 RUT",
    "^VIX": "恐慌指数 VIX",
    "^SOX": "费城半导体 SOX",
    # 港股 / 亚太
    "^HSI": "恒生指数",
    "^HSTECH": "恒生科技",
    "^KS11": "韩国KOSPI",
    "^N225": "日经225",
    "^TWII": "台湾加权",
    "^AXJO": "澳洲200",
    # 欧洲
    "^FTSE": "英国富时100",
    "^GDAXI": "德国DAX",
    "^FCHI": "法国CAC40",
    "^STOXX50E": "欧洲斯托克50",
    # 美股 ETF（与 US_ETFS 同名，供自选展示）
    **{etf.symbol: etf.display_name for etf in US_ETFS},
}

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
