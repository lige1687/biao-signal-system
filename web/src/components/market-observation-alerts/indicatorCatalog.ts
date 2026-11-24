import { OBSERVATION_CATALOG, type ObservationGroup, type ObservationMarket } from "../observation-library/catalog";
import { INDICATOR_META_CONFIG } from "../market-observation-panel/model";
import { INDUSTRY_TURNOVER_ID, INDUSTRY_TURNOVER_OPTIONS, isIndustryTurnoverSeries } from "./industryTurnoverOptions";

export const INDICATOR_CATEGORIES = [
  { id: "valuation", label: "估值与股债" },
  { id: "participation", label: "市场参与" },
  { id: "risk", label: "波动与信用" },
  { id: "funding", label: "资金与情绪" },
  { id: "style", label: "风格与行业" },
  { id: "economy", label: "盈利与经济" },
] as const;

export type CategoryId = typeof INDICATOR_CATEGORIES[number]["id"];

export interface IndicatorEntry {
  id: string;
  label: string;
  market: ObservationMarket;
  category: CategoryId;
  meaning: string;
  limitation: string;
  readable: boolean;
  keywords?: string;
}

const CATEGORY_BY_GROUP: Record<ObservationGroup, CategoryId> = {
  valuation: "valuation",
  participation: "participation",
  credit: "risk",
  positioning: "funding",
  earnings: "economy",
  cycle: "economy",
};

const CATEGORY_OVERRIDES = new Map<string, CategoryId>([
  ["equal-weight-spread", "style"],
  ["industry-diffusion", "style"],
]);

const SEARCH_ALIASES: Readonly<Record<string, string>> = {
  "erp-cn": "ERP 风险溢价",
  "erp-us": "ERP 风险溢价",
};

const EXTRA_INDICATORS: readonly IndicatorEntry[] = [
  {
    id: "sector-margin-share", label: "半导体 / 通信 · 已披露融资交易", market: "cn", category: "funding", readable: true,
    meaning: "已披露融资买入额占同池全部股票成交额，分别看日期与覆盖。",
    limitation: "11-15固定名单回看10-26至11-05共9日；融资明细未列示股票资格未核，非完整行业实际融资占比。",
    keywords: "半导体 通信 通信设备 融资买入 融资交易",
  },
  {
    id: "earnings-revision-samples", label: "2027E盈利预测 · 研报样例", market: "cn", category: "economy", readable: true,
    meaning: "同目标年份同团队原研报预测版本的EPS与净利润并看。",
    limitation: "4股9研报事后取得，全指数修正广度与首次可得时间未知；股本变化或矛盾单列。",
    keywords: "盈利预测 修正 研报 EPS 净利润 2027E",
  },
  {
    id: "sector-breadth", label: "半导体 / 通信 · 内部宽度", market: "cn", category: "participation", readable: true,
    meaning: "看当前行业固定池多少股票站上自身20、50、200日均线。",
    limitation: "名单2026-11-15取得的沪深A股固定池回看，观察至2026-11-13；非历史成员。",
    keywords: "半导体 通信 通信设备 行业 内部宽度 均线",
  },
  {
    id: "star-breadth", label: "科创50 / 科创100 · 数量宽度", market: "cn", category: "participation", readable: true,
    meaning: "看固定名单内多少股票站上20、50、200日均线，以及近60个交易日如何变化。",
    limitation: "2026-11-11名单回看，非逐日历史成分；观察截至2026-11-13。",
    keywords: "科创 科创50 科创100 内部宽度 均线",
  },
  {
    id: "star-weighted-breadth", label: "科创50 / 科创100 · 权重宽度", market: "cn", category: "participation", readable: true,
    meaning: "对比同日站上均线的股票数量和有效指数权重占比。",
    limitation: "2026-10-30单日截面，使用2026-11-11固定名单事后回看。",
    keywords: "科创 科创50 科创100 权重 数量 均线",
  },
  {
    id: INDUSTRY_TURNOVER_ID, label: "行业换手率", market: "cn", category: "style", readable: true,
    meaning: "点开选择关注行业，查看日换手率和近三年的历史分位。",
    limitation: "按板块各自的历史比较成交活跃度。",
    keywords: `情绪 活跃度 通讯设备 ${INDUSTRY_TURNOVER_OPTIONS.map(({ label }) => label).join(" ")}`,
  },
  {
    id: "etf-price-heat", label: "ETF · 量价热度与分歧", market: "cn", category: "style", readable: true,
    meaning: "对照半导体、通信、创业板与沪深300ETF的成交活跃、价格走势和热度回落。",
    limitation: "历史快照；价热分歧用于观察，预测效果仍待独立验证。",
    keywords: "行业 情绪 成交量 换手率 背离 半导体 通信 创业板 沪深300 512480 515880 159915 510300",
  },
  {
    id: "breadth-cn", label: "全A · 市场宽度", market: "cn", category: "participation", readable: true,
    meaning: "看全A有多少股票收在各自均线之上。",
    limitation: "历史高低区间用于比较参与程度。",
    keywords: "市场广度 宽度 广度 全A 沪深",
  },
  {
    id: "breadth-us", label: "标普500 · 市场宽度", market: "us", category: "participation", readable: true,
    meaning: "看标普500成分股中有多少收在各自均线之上。",
    limitation: "覆盖范围为标普500成分股。",
    keywords: "市场广度 宽度 广度 SP500 S&P500 SPY",
  },
  {
    id: "hv-cn", label: "上证 · 20/60日波动率", market: "cn", category: "risk", readable: true,
    meaning: "比较上证指数近20日与近60日的实际波动幅度。",
    limitation: "以收盘价计算历史波动，反映幅度。",
    keywords: "HV 上证指数",
  },
  {
    id: "hv-us", label: "标普500 · 20/60日波动率", market: "us", category: "risk", readable: true,
    meaning: "比较标普500近20日与近60日的实际波动幅度。",
    limitation: "以收盘价计算历史波动，反映幅度。",
    keywords: "HV SP500 S&P500 SPY",
  },
  {
    id: "dr007", label: "DR007资金价格", market: "cn", category: "funding", readable: true,
    meaning: "看存款类机构借用7天资金的成本变化。",
    limitation: "反映银行间短期资金价格。",
    keywords: "回购 银行间 流动性",
  },
  {
    id: "cn-session", label: "沪深300 · 隔夜与日内表现", market: "cn", category: "participation", readable: true,
    meaning: "分开看沪深300从前收盘到开盘、从开盘到收盘的表现。",
    limitation: "观察对象为沪深300指数。",
    keywords: "隔夜收益 日内收益",
  },
  {
    id: "cn-institution", label: "龙虎榜 · 已披露机构席位", market: "cn", category: "funding", readable: true,
    meaning: "看龙虎榜上已披露的机构席位买卖活动。",
    limitation: "仅覆盖上榜且披露为机构的席位。",
    keywords: "机构席位 机构净买入",
  },
  {
    id: "cn-style-relative", label: "大小盘 · 中证1000 / 沪深300", market: "cn", category: "style", readable: true,
    meaning: "用两只ETF的价格比观察小盘相对大盘的强弱。",
    limitation: "以对应ETF的价格为比较口径。",
    keywords: "大小盘 小盘 大盘 512100 510300 ETF",
  },
  {
    id: "us-semiconductor-relative", label: "半导体 / 纳指100", market: "us", category: "style", readable: true,
    meaning: "用两只ETF的价格比观察半导体相对纳指100的强弱。",
    limitation: "以对应ETF的价格为比较口径。",
    keywords: "SMH QQQ ETF 纳斯达克100",
  },
  {
    id: "us-equal-weight-relative", label: "标普500 · 等权 / 市值加权", market: "us", category: "style", readable: true,
    meaning: "用两只ETF的价格比比较标普500等权与市值加权的表现。",
    limitation: "以对应ETF的价格为比较口径。",
    keywords: "RSP SPY ETF 等权 市值权",
  },
  {
    id: "vix-term-structure", label: "VIX · 期限结构", market: "us", category: "risk", readable: true,
    meaning: "比较标普500期权市场近期与三个月的预期波动。",
    limitation: "反映不同期限的预期波动幅度。",
    keywords: "VIX VIX3M 期权",
  },
  {
    id: "industry-structure-cn", label: "沪深300十行业 · 同步与分化", market: "cn", category: "style", readable: true,
    meaning: "看沪深300十个行业的涨跌有多同步、表现相差多大。",
    limitation: "行业分类中金融与地产合为一组，按历史快照展示。",
    keywords: "板块 行业结构 相关性 离散",
  },
];

export const MICRO_INDICATORS: readonly IndicatorEntry[] = [
  {
    "id": "cn-300etf-pcr-volume",
    "label": "沪深300ETF 期权成交量 PCR",
    "market": "cn",
    "category": "funding",
    "meaning": "认沽成交张数相对认购成交张数；看当日期权交易构成。",
    "limitation": "历史快照，按卡片日期和口径阅读。",
    "readable": true
  },
  {
    "id": "cn-300etf-pcr-oi",
    "label": "沪深300ETF 期权持仓量 PCR",
    "market": "cn",
    "category": "funding",
    "meaning": "认沽未平仓张数相对认购未平仓张数；看日末存量构成。",
    "limitation": "历史快照，按卡片日期和口径阅读。",
    "readable": true
  },
  {
    "id": "cn-300etf-atm-iv",
    "label": "沪深300ETF 近月平值隐含波动代理",
    "market": "cn",
    "category": "risk",
    "meaning": "近月接近平值的两侧隐含波动均值；看期权对波动幅度的定价。",
    "limitation": "历史快照，按卡片日期和口径阅读。",
    "readable": true
  },
  {
    "id": "us-option-pcr-volume",
    "label": "美国期权成交量 PCR · 股票与总体",
    "market": "us",
    "category": "funding",
    "meaning": "股票期权与总体期权成交量PCR双线对比；看期权交易构成，两线水平不可直接相减。",
    "limitation": "历史快照，按卡片日期和口径阅读。",
    "readable": true
  },
  {
    "id": "us-cor3m",
    "label": "标普500 三个月隐含相关 COR3M",
    "market": "us",
    "category": "risk",
    "meaning": "根据标普500中市值最大的50只成分股与指数期权，观察约三个月的隐含相关。",
    "limitation": "历史快照，按卡片日期和口径阅读。",
    "readable": true
  },
  {
    "id": "cn-index-futures-basis",
    "label": "A股四大股指期货主力连续年化基差",
    "market": "cn",
    "category": "risk",
    "meaning": "IF/IC/IH/IM按当日持仓量最大合约拼接的主力连续，相对各自现货的年化基差同图对比；IH/IF偏大盘、IC/IM偏小盘。",
    "limitation": "历史快照，按卡片日期和口径阅读；主力换月点存在合约跳变，不是单合约持有收益。",
    "readable": true
  },
  {
    "id": "cn-daily-amount-top5",
    "label": "沪深A股每日成交额前5%占比",
    "market": "cn",
    "category": "participation",
    "meaning": "观察成交额集中在少数股票的程度；升高并不区分追涨与抛售。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-daily-amount-top10",
    "label": "沪深A股每日成交额前10%占比",
    "market": "cn",
    "category": "participation",
    "meaning": "观察成交额集中在少数股票的程度；升高并不区分追涨与抛售。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-current-members-daily-dispersion",
    "label": "沪深300当前成员日收益离散度",
    "market": "cn",
    "category": "participation",
    "meaning": "描述同日逐股涨跌差距；高值不自动意味着选股收益。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-current-members-pairwise-correlation",
    "label": "沪深300当前成员20日两两相关",
    "market": "cn",
    "category": "risk",
    "meaning": "描述逐股是否同动；共同上涨与共同下跌都可能抬高相关。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "us-current-members-daily-dispersion",
    "label": "标普500当前成员日收益离散度",
    "market": "us",
    "category": "participation",
    "meaning": "描述同日逐股涨跌差距；高值不自动意味着选股收益。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "us-current-members-pairwise-correlation",
    "label": "标普500当前成员20日两两相关",
    "market": "us",
    "category": "risk",
    "meaning": "描述逐股是否同动；共同上涨与共同下跌都可能抬高相关。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-above-own-p95",
    "label": "行业换手高于自身近三年P95占比",
    "market": "cn",
    "category": "style",
    "meaning": "观察所选行业中异常活跃的比例；只是交易活跃状态。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-above-own-p98",
    "label": "行业换手高于自身近三年P98占比",
    "market": "cn",
    "category": "style",
    "meaning": "观察所选行业换手相对各自历史的极端活跃比例。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0420",
    "label": "航空机场日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0421",
    "label": "铁路公路日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0422",
    "label": "物流日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0424",
    "label": "水泥日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0427",
    "label": "公用事业日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0428",
    "label": "电力日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0433",
    "label": "农林牧渔日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0436",
    "label": "纺织服饰日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0437",
    "label": "煤炭日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0438",
    "label": "食品饮料日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0440",
    "label": "家居用品日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0448",
    "label": "通信设备日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0450",
    "label": "航运港口日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0451",
    "label": "房地产开发日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0454",
    "label": "塑料日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0456",
    "label": "家用电器日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0457",
    "label": "电网设备日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0458",
    "label": "仪器仪表日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0459",
    "label": "元件日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0464",
    "label": "石油石化日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0465",
    "label": "化学制药日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0471",
    "label": "化学纤维日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0473",
    "label": "证券Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0474",
    "label": "保险Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0475",
    "label": "银行Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0476",
    "label": "装修建材日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0478",
    "label": "有色金属日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0479",
    "label": "钢铁日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0481",
    "label": "汽车零部件日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0482",
    "label": "一般零售日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0484",
    "label": "贸易Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk0486",
    "label": "传媒日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1015",
    "label": "能源金属日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1016",
    "label": "汽车服务日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1018",
    "label": "橡胶日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1019",
    "label": "化学原料日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1020",
    "label": "非金属材料Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1027",
    "label": "小金属日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1028",
    "label": "燃气Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1030",
    "label": "电机Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1031",
    "label": "光伏设备日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1032",
    "label": "风电设备日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1033",
    "label": "电池日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1034",
    "label": "其他电源设备Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1035",
    "label": "美容护理日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1036",
    "label": "半导体日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1037",
    "label": "消费电子日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1038",
    "label": "光学光电子日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1039",
    "label": "电子化学品Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1040",
    "label": "中药Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1041",
    "label": "医疗器械日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1042",
    "label": "医药商业日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1043",
    "label": "专业服务日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1044",
    "label": "生物制品日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1045",
    "label": "房地产服务日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-industry-turnover-bk1046",
    "label": "游戏Ⅱ日换手率",
    "market": "cn",
    "category": "style",
    "meaning": "与该板块自身过去756个有效交易日比较活跃程度；超过高分位仍不是卖出信号。",
    "limitation": "历史快照，按卡片日期、股票范围与来源口径阅读。",
    "readable": true
  },
  {
    "id": "cn-all-industry-independent-float-turnover",
    "label": "完整行业自行核算自由流通换手",
    "market": "cn",
    "category": "style",
    "meaning": "供应商目录496项中已取得BK04/BK10两组56个报告换手率板块；其余440项超出当前批次且目录含重叠细分。历史分母与成员版本未独立认证，尚非自行核算的完整互斥行业体系。",
    "limitation": "供应商目录496项中已取得BK04/BK10两组56个报告换手率板块；其余440项超出当前批次且目录含重叠细分。历史分母与成员版本未独立认证，尚非自行核算的完整互斥行业体系。",
    "readable": false
  }
];

export const INDICATOR_CATALOG: readonly IndicatorEntry[] = [
  ...OBSERVATION_CATALOG.map(({ group, id, label, market, meaning, limitation, readable }) => ({
    id, label, market, meaning, limitation, readable,
    ...(id === "cn-financing" ? {
      label: INDICATOR_META_CONFIG[id].label,
      meaning: INDICATOR_META_CONFIG[id].human_reminder,
      limitation: "主图用沪深股票口径融资买入额占成交额，副读数列出供应商融资余额占流通市值及其日期。",
    } : {}),
    ...(id === "turnover-concentration" ? { meaning: "看成交额集中在少数股票的程度：日频前5%、日频前10%、月频前5%。", keywords: "成交额集中度 每日 月度 前5% 前10% top5 top10" } : {}),
    category: CATEGORY_OVERRIDES.get(id) ?? CATEGORY_BY_GROUP[group],
    keywords: id === "turnover-concentration" ? "成交额集中度 每日 月度 前5% 前10% top5 top10"
      : id === "cn-financing" ? "融资买入额占成交额 融资余额 融资买入占比 20日均值 两融三合一" : SEARCH_ALIASES[id],
  })),
  ...EXTRA_INDICATORS,
  ...MICRO_INDICATORS.filter(({ id }) => !isIndustryTurnoverSeries(id)
    && !["cn-daily-amount-top5", "cn-daily-amount-top10", "cn-all-industry-independent-float-turnover"].includes(id)),
];

export const INDICATOR_BY_ID: ReadonlyMap<string, IndicatorEntry> =
  new Map(INDICATOR_CATALOG.map((item) => [item.id, item]));

interface IndicatorFilters {
  category?: CategoryId | "all";
  market?: ObservationMarket | "all";
  query?: string;
  includePending?: boolean;
}

export function filterIndicators(
  { category = "all", market = "all", query = "", includePending = false }: IndicatorFilters = {},
  entries: readonly IndicatorEntry[] = INDICATOR_CATALOG,
) {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return entries.filter((item) => {
    if (!includePending && !item.readable) return false;
    if (category !== "all" && item.category !== category) return false;
    if (market !== "all" && item.market !== market) return false;
    const searchable = [item.label, item.meaning, item.keywords].join(" ").toLowerCase();
    return terms.every((term) => searchable.includes(term));
  });
}
