/** Observation catalogue, including reviewed C25-C27 descriptive candidates.
 * Priority is reading order, not a forecast or trading score.
 */
export type ObservationMarket = "cn" | "us" | "global";
export type ObservationGroup = "participation" | "earnings" | "valuation" | "credit" | "positioning" | "cycle";

export interface ObservationEntry {
  id: string;
  candidate: string;
  label: string;
  market: ObservationMarket;
  group: ObservationGroup;
  priority: number;
  meaning: string;
  limitation: string;
  readable: boolean;
}

export const GROUP_LABELS: Record<ObservationGroup, string> = {
  participation: "参与结构", earnings: "盈利支持", valuation: "估值背景",
  credit: "信用与金融压力", positioning: "融资与情绪", cycle: "经济周期",
};

const entry = (id: string, candidate: string, label: string, market: ObservationMarket,
  group: ObservationGroup, priority: number, meaning: string, limitation: string,
  readable = false): ObservationEntry => ({ id, candidate, label, market, group, priority, meaning, limitation, readable });

export const OBSERVATION_CATALOG: readonly ObservationEntry[] = [
  entry("equal-weight-spread", "C01", "同池等权相对市值权", "global", "participation", 1, "看上涨是否只由大权重公司推动。", "同一指数池的历史成员、分红与再平衡数据尚未接通。"),
  entry("industry-diffusion", "C02", "行业上涨扩散", "global", "participation", 2, "看行业是否一起走强。", "历史行业分类与固定可比行业分母尚未接通。"),
  entry("new-high-low", "C03", "新高与新低家数", "global", "participation", 3, "补看参与股票的极端分化。", "与宽度同源；完整历史名单与停牌处理尚未接通。"),
  entry("focus-momentum", "C04", "焦点股动量 · 固定300股历史", "cn", "participation", 4, "观察成交集中股票的过去20日涨跌和同池背景。", "固定300股样本续接至2026-10-23；最新交易日尚未补齐，0线不是已验证的买卖阈值。", true),
  entry("turnover-concentration", "C04", "沪深A股成交额集中度", "cn", "participation", 4, "看成交额有多少集中在最活跃的5%股票中。", "供应商覆盖范围的月度历史快照；不完整月份留空，不代表官方全A或今日读数。", true),
  entry("downside-price-impact", "C25", "下跌价格冲击 · 20日历史", "cn", "participation", 6, "看下跌幅度相对于成交额是否变大。", "供应商覆盖沪深A股的样本中位数；截至2026-10-23，受市值、成交与波动影响。", true),
  entry("salience-str", "C26", "凸显收益偏向 · 20日历史", "cn", "positioning", 7, "看加重突出交易日后，平均收益比普通均值高还是低。", "文献参数的独立20日观察版，截至2026-10-23；非视频原式，未验证指数顶底预测。", true),
  entry("smallcap-turnover", "C27", "小盘股换手热度 · 同日快照", "cn", "participation", 8, "看小市值股票的换手率相对同池整体有多高。", "2026-10-30收盘后采集，含2条当日早间无成交报价；仅同日快照，没有历史曲线或自动更新。", true),
  entry("return-dispersion", "C05", "涨幅离散与共同下跌", "global", "participation", 5, "看行情是分化还是一起波动。", "同池完整日线和缺值规则尚未接通。"),
  entry("vix", "C06", "VIX · 标普500预期波动", "us", "credit", 40, "看标普500期权市场预期波动是否升温。", "波动幅度没有涨跌方向；以各项资料日期为准。", true),
  entry("vxn", "C06", "VXN · 纳指100预期波动", "us", "credit", 41, "看纳指100期权市场预期波动。", "只对应纳指100，不代表整个美国市场。", true),
  entry("hy-oas", "C07", "美国高收益债信用利差", "us", "credit", 42, "看企业借债需要的风险补偿。", "利差不是违约率；与VIX可能重复反映压力。", true),
  entry("ofr-fsi", "C08", "OFR金融压力指数", "global", "credit", 43, "看压力是否扩散至信用、融资和避险市场。", "官方历史有修订且约滞后两个工作日；现存资料不等于自动更新。", true),
  entry("nfci", "C09", "NFCI · 美国金融条件", "us", "credit", 44, "看美国金融条件相对长期平均的松紧。", "两年周频历史；发布约滞后一周且历史会修订，零线为长期平均。", true),
  entry("anfci", "C09", "ANFCI · 调整后金融条件", "us", "credit", 45, "看剔除经济活动影响后金融条件是否异常。", "尚无已核显示序列；不与NFCI算两份独立证据。"),
  entry("cn-financing", "C10", "A股两融三合一", "cn", "positioning", 50, "同一张图看融资买入额/成交额、其20日均值，以及融资余额/流通市值的存量水位。", "买入额不是净流入；余额占比与买入额来自不同源，按同日对齐，缺失日留空。", true),
  entry("finra-margin", "C11", "FINRA客户融资与闲置资金", "us", "positioning", 51, "看美国相关客户账户的融资和现金背景。", "月度资料通常次月才公布；2010年前后分列口径变。", true),
  entry("cftc-positions", "C12", "CFTC期货分类持仓", "us", "positioning", 52, "看不同参与者的期货风险暴露。", "只有旧原件；连续现时链与套保识别未核。"),
  entry("etf-shares", "C13", "ETF实际份额变化", "global", "positioning", 53, "看基金一级市场份额创造和赎回。", "只有部分定期报告；无合格连续日频份额，成交量不能替代。"),
  entry("csi300-etf-float-ratio", "C13", "沪深300头部ETF规模占比", "cn", "positioning", 54, "看跟踪沪深300的头部ETF规模，相对于沪深300成分股流通市值有多大。", "基金名单、各ETF净资产历史及沪深300流通市值历史尚未核齐；净资产包含现金等资产，不等于ETF实际持股占比。"),
  entry("aaii", "C14", "AAII个人投资者调查", "us", "positioning", 54, "看受访者的看涨、看跌意见。", "不代表全部散户；极端读数不是买卖指令。", true),
  entry("naaim", "C14", "NAAIM管理人自报仓位", "us", "positioning", 55, "看受访主动管理人的风险敞口。", "自报调查不等于实际全市场仓位。官方2026-08起改为订阅制；本序列=官方延迟表+公开镜像，最近三周由公开图表数字化，误差约±0.1。", true),
  entry("baker-wurgler", "C15", "Baker–Wurgler · 月度情绪背景", "us", "positioning", 56, "以多种美国市场活动观察较慢的情绪水平；不作为阶段顶底提示。", "NYU当前表默认宏观调整后的SENT_ORTH，月度无量纲，末行2025-12；2025-10该列缺失。作者提醒不能用相邻月差值衡量情绪变化；历史首次发布时间未知。", true),
  entry("earnings-revisions", "C16", "盈利预期上修广度", "global", "earnings", 20, "看多数公司的未来盈利预期是否同步改善。", "缺同一历史指数池和两期可比预测快照。"),
  entry("earnings-breadth", "C17", "实际盈利改善与加速", "global", "earnings", 21, "看利润改善是否普遍，以及本季增长是否比上季更快。", "盈利加速并入此项；仍缺同池单季度净利润、可比同比与首次公告时间，现存少量EPS不能替代。"),
  entry("profitability-breadth", "C18", "利润率与资本回报改善", "global", "earnings", 22, "看经营质量改善覆盖多少公司。", "季度字段和行业口径尚未统一。"),
  entry("cash-earnings", "C19", "现金与利润匹配", "global", "earnings", 23, "看利润是否有经营现金支持。", "需分行业及成长投资情景，旧公开组合效果不能代替本地同池。"),
  entry("earnings-concentration", "C20", "指数盈利贡献集中度", "global", "earnings", 24, "看利润主要由少数公司或行业贡献吗。", "历史权重和可比盈利缺失，总利润接近零时比例会失真。"),
  entry("hs300-pe", "C21", "沪深300 PE_TTM", "cn", "valuation", 30, "看沪深300估值在自身历史中的位置。", "只对应沪深300；历史分位和亏损公司处理需按来源读。", true),
  entry("erp-cn", "C21", "沪深300股债利差 · 三年上下轨", "cn", "valuation", 30, "比较沪深300盈利收益率与中国10年国债利率。", "三年均值±2σ，上轨相对便宜、下轨相对偏贵；有据参照版，尚非原视频逐点复刻或已验证买卖信号。", true),
  entry("erp-us", "C21", "标普500股债利差 · 上下轨", "us", "valuation", 31, "比较标普500盈利收益率与美国10年国债利率。", "复用基本面股债收益差；盈利端历史为月频；此前三年1.5/2倍标准差为本地观察参考，触轨收益未验证；仅适用于标普500盈利口径。", true),
  entry("sp500-cape", "C21", "标普500 Shiller CAPE", "us", "valuation", 31, "看标普500长期盈利估值在自身历史中的位置。", "用过去十年经通胀调整的盈利均值计算。", true),
  entry("chinext-pe", "C21", "创业板指估值", "cn", "valuation", 32, "看创业板指自身估值和历史位置。", "该指数独立估值原件、分位窗口及亏损处理尚未接通。"),
  entry("star50-pe", "C21", "科创50估值", "cn", "valuation", 33, "看科创50自身估值和历史位置。", "科创50不是科创板全体；独立估值序列尚未接通。"),
  entry("nasdaq100-pe", "C21", "纳斯达克100 PE_TTM", "us", "valuation", 34, "看纳指100自身估值。", "Siblis Research 2026-09 公开快照为35.09倍。公开表缺连续月度历史，暂不显示10年分位。"),
  entry("industry-relative-value", "C21", "同行业估值与盈利", "cn", "valuation", 35, "看同行中价格较低的公司是否也有盈利支持。", "缺同日行业分类、估值和可比利润全样本；视频未明示估值字段，不能把低PE直接当便宜。"),
  entry("equity-funding-cost", "C21", "企业全收益与资金成本", "cn", "valuation", 36, "长期对照含分红的股票总回报与融资成本。", "全收益指数已有；视频资金成本曲线的定义及连续原数据未核，不能用10年国债利率替代。"),
  entry("cn-social-financing", "C22", "中国社融结构与M1", "cn", "cycle", 60, "看实体信用和货币活跃度变化。", "完整发布版本链未建，M1新旧口径不能直接拼接。"),
  entry("pmi-cn", "C23", "中国制造业PMI", "cn", "cycle", 61, "看制造业调查的扩张与收缩。", "总指数不等于新订单、生产或库存完整分项。", true),
  entry("pmi-us", "C23", "美国制造业PMI", "us", "cycle", 62, "看美国制造业采购经理调查方向。", "美国PMI原读数未接入；现有耐用品订单同比是另一指标，不能冒充PMI。"),
  entry("wei", "C23", "WEI · 美国周经济指数", "us", "cycle", 63, "看美国周度经济活动的变化。", "周度合成代理，不是当周已经公布的GDP。", true),
  entry("oecd-cli", "C24", "OECD经济领先指标", "global", "cycle", 64, "看经济活动相对长期趋势是否转向。", "月度历史会修订且尚未接入；经济转折不等于股价顶底。"),
];

export const OBSERVATION_BY_ID = new Map(OBSERVATION_CATALOG.map((item) => [item.id, item]));
export const READABLE_IDS = new Set(OBSERVATION_CATALOG.filter((item) => item.readable).map((item) => item.id));
export const CANDIDATE_IDS = new Set(OBSERVATION_CATALOG.map((item) => item.candidate));

// Reading priority is shared by the library, home and price comparison menu.
// It describes a reading workflow, not predictive strength or live-data availability.
export const OBSERVATION_SECTIONS = [
  { id: "focus", label: "重点对照", note: "先看股债估值背景；A股三年轨道与美股原值的资料边界不同" },
  { id: "daily", label: "常用观察", note: "先看波动、信用和融资热度" },
  { id: "weekly", label: "每周补充", note: "再看投资者意见与管理人仓位" },
  { id: "background", label: "慢周期背景", note: "估值、月度情绪与经济环境" },
  { id: "historical", label: "历史参考", note: "固定样本或快照，当前读数未接通" },
  { id: "pending", label: "待接入", note: "数据补齐后再展示数值" },
] as const;
export type ObservationSection = typeof OBSERVATION_SECTIONS[number]["id"];

export function observationSection(item: ObservationEntry): ObservationSection {
  if (!item.readable) return "pending";
  if (["erp-cn", "erp-us"].includes(item.id)) return "focus";
  if (["downside-price-impact", "salience-str", "smallcap-turnover", "focus-momentum", "nfci"].includes(item.id)) return "historical";
  if (["vix", "hy-oas", "ofr-fsi", "vxn", "cn-financing"].includes(item.id)) return "daily";
  if (["aaii", "naaim"].includes(item.id)) return "weekly";
  return "background";
}

const READING_ORDER = [
  "erp-cn", "erp-us", "vix", "hy-oas", "cn-financing", "ofr-fsi", "vxn", "aaii", "naaim",
  "turnover-concentration", "hs300-pe", "sp500-cape", "baker-wurgler", "finra-margin", "pmi-cn", "wei",
  "downside-price-impact", "salience-str", "smallcap-turnover", "focus-momentum", "nfci", "csi300-etf-float-ratio", "etf-shares",
  "earnings-revisions", "earnings-breadth", "equal-weight-spread", "industry-diffusion",
  "chinext-pe", "star50-pe", "nasdaq100-pe", "profitability-breadth", "earnings-concentration",
  "cash-earnings", "industry-relative-value", "equity-funding-cost", "cn-social-financing", "oecd-cli", "cftc-positions",
  "return-dispersion", "new-high-low", "anfci", "pmi-us",
] as const;
const RANK_BY_ID = new Map<string, number>(READING_ORDER.map((id, index) => [id, index]));
export function observationReadingRank(item: ObservationEntry): number {
  return RANK_BY_ID.get(item.id) ?? 999;
}
