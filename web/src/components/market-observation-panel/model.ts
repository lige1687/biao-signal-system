export type Point = { date: string; value: number | null; ma20?: number | null; mean?: number | null; std?: number | null; band_upper_1_5?: number | null; band_lower_1_5?: number | null; band_upper_2_0?: number | null; band_lower_2_0?: number | null };
export type ObservationCardData = { frequency: "daily" | "weekly" | "monthly"; unit: string; sourceName: string; sourceUrl?: string; note?: string; mainLabel?: string; latestQualifier?: string; points: Point[]; lines?: { id: string; label: string; points: Point[]; dashed?: boolean }[]; auxiliary?: { label: string; value: number | null; unit: string; date: string }[]; window: number; observations: number; current_zscore: number | null; current_zscore_raw?: number | null; current_percentile: number | null };
export type ObservationPanelData = { schemaVersion: 1; generatedAt: string; cards: Record<string, ObservationCardData>; partialUpdate?: { message: string; cardIds: string[]; sourceFetchedAt: string; previousGeneratedAt: string; previousAsOf: string; asOfMeaning: string } };
export type Rail = { value: number; label: string; tone?: "watch" | "high" | "low" | "neutral"; color?: "amber" | "red" | "darkred" | "gray" | "blue" };
export type IndicatorMeta = { id: string; label: string; market: "cn" | "us" | "global"; group: "pressure" | "breadth" | "positioning"; meaning: string; reading: string; human_reminder: string; hard_thresholds: Rail[]; direction: "higher_pressure" | "higher_sentiment" | "context"; precision?: number; ratioAlert?: number };

const pressure = new Set([
  "vix", "vxn", "vix-term-structure", "hv-us", "hv-cn", "hy-oas", "ofr-fsi", "nfci",
  "cn-daily-amount-top5", "downside-price-impact", "cn-current-members-pairwise-correlation",
  "us-current-members-pairwise-correlation", "us-cor3m", "cn-300etf-atm-iv",
]);
const sentiment = new Set(["focus-momentum", "cn-financing", "salience-str", "aaii", "naaim", "finra-margin", "baker-wurgler"]);
const metric = (
  id: string, label: string, market: IndicatorMeta["market"], group: IndicatorMeta["group"],
  reminder: string, reading: string, thresholds: Rail[] = [], precision?: number,
): IndicatorMeta => ({
  id, label, market, group, human_reminder: reminder, meaning: reminder, reading,
  hard_thresholds: thresholds, precision,
  direction: pressure.has(id) ? "higher_pressure" : sentiment.has(id) ? "higher_sentiment" : "context",
  ...(id === "hv-cn" || id === "hv-us" ? { ratioAlert: 1.25 } : {}),
});
const rail = (value: number, label: string, tone: Rail["tone"] = "neutral", color?: Rail["color"]): Rail => ({ value, label, tone, color });

export const INDICATOR_META_CONFIG: Record<string, IndicatorMeta> = Object.fromEntries([
  metric("vix", "VIX · 标普500预期波动", "us", "pressure",
    "看期权市场给美股短期波动定了多高的价。超过20留意升温，超过30留意恐慌。", "看压力是否传到信贷。",
    [rail(20, "高波警戒 20", "watch"), rail(30, "恐慌极值 30", "high")]),
  metric("vxn", "VXN · 纳指100预期波动", "us", "pressure",
    "看科技股的期权保险有多贵。与 VIX 对照，看压力是否集中在纳指。", "对照纳指与标普波动。",
    [rail(25, "警戒 25", "watch"), rail(35, "恐慌 35", "high")]),
  metric("vix-term-structure", "VIX · 期限结构", "us", "pressure",
    "比值超过1，眼前的预期波动高于未来三个月，短期避险需求更强。", "看期限比能否回到1。",
    [rail(1, "倒挂 1.0", "watch", "red"), rail(1.15, "极端倒挂 1.15", "high", "darkred")], 3),
  metric("hv-us", "标普500 · 20/60日波动率", "us", "pressure",
    "看实际震荡有没有加速。20日波动高于60日，说明近期涨跌幅在放大。", "结合期权看波动。"),
  metric("hv-cn", "上证 · 20/60日波动率", "cn", "pressure",
    "看实际震荡有没有加速。20日波动高于60日，说明近期涨跌幅在放大。", "结合宽度看震荡。"),
  metric("hy-oas", "美国高收益债信用利差", "us", "pressure",
    "看风险较高的企业借钱要多付多少利息。利差扩大，信用市场开始要求更多补偿。", "看企业融资压力。",
    [rail(4, "压力 4.0%", "watch"), rail(5, "高压力 5.0%", "high")]),
  metric("ofr-fsi", "OFR金融压力指数", "global", "pressure",
    "看全球金融市场是否比平时紧张。零以上高于长期常态，零以下低于常态。", "对照信用利差。",
    [rail(0, "长期常态 0", "high")], 3),
  metric("nfci", "NFCI · 美国金融条件", "us", "pressure",
    "看美国市场融资环境的松紧。负值偏松，正值偏紧。", "观察融资松紧。",
    [rail(0, "长期平均 0", "high")], 3),
  metric("cn-daily-amount-top5", "沪深A股成交额集中度", "cn", "breadth",
    "看成交额有多少挤在最活跃的5%股票里。越集中，越要看热门股还赚不赚钱。", "看热门股是否转弱。",
    [rail(35, "分散参照 35%", "neutral"), rail(46, "拥挤参照 46%", "high")]),
  metric("focus-momentum", "焦点股动量 · 固定300股历史", "cn", "breadth",
    "看固定300股里成交最活跃的一小批股票，近20日平均是赚钱还是亏钱。", "对照成交集中度。",
    [rail(0, "盈亏分界 0%")]),
  metric("downside-price-impact", "下跌价格冲击 · 20日历史", "cn", "breadth",
    "看下跌时同样一笔成交额对应多大跌幅。明显高于历史时，留意承接转弱。", "留意下跌承接。"),
  metric("cn-current-members-pairwise-correlation", "沪深300当前成员20日两两相关", "cn", "breadth",
    "看当前成分股是一起涨跌，还是各走各的。相关越高，个股分散越难。", "结合指数看涨跌方向。",
    [rail(.15, "分化 0.15", "low"), rail(.4, "同步 0.40", "high")], 3),
  metric("us-current-members-pairwise-correlation", "标普500当前成员20日两两相关", "us", "breadth",
    "看当前成分股是一起涨跌，还是各走各的。相关越高，个股分散越难。", "结合指数看涨跌方向。",
    [rail(.15, "分化 0.15", "low"), rail(.4, "同步 0.40", "high")], 3),
  metric("us-cor3m", "标普500 · COR3M隐含相关", "us", "breadth",
    "看标普500中市值最大的50只成分股与指数期权隐含的三个月相关。越高，预期分散效果越弱。", "对照实际相关，注意股票池与观察期不同。",
    [rail(15, "分化 15%", "low"), rail(40, "同步 40%", "high")]),
  metric("cn-300etf-atm-iv", "沪深300ETF近月平值隐含波动代理", "cn", "breadth",
    "看沪深300ETF期权给近月震荡定了多高的价。读数越高，市场预期波动越大。", "对照实际波动。"),
  metric("cn-financing", "A股两融杠杆与热度", "cn", "positioning",
    "看每天有多少成交靠融资买入。超过10.5%留意杠杆拥挤，低于6.5%说明参与偏冷。", "对照余额占比。",
    [rail(6.5, "杠杆冰点 6.5%", "low"), rail(10.5, "杠杆过热 10.5%", "high")]),
  metric("cn-index-futures-basis", "四大期指连续年化基差", "cn", "positioning",
    "看期货比现货贵还是便宜。深贴水时，同时检查分红、换月和对冲需求。", "看大小盘贴水差。",
    [rail(-10, "深度贴水 −10%", "low"), rail(0, "升贴水分界 0%")]),
  metric("salience-str", "凸显收益偏向 · 20日历史", "cn", "positioning",
    "把涨跌特别显眼的交易日看得更重，观察它们把个股平均收益向上拉还是向下拖。", "看显眼行情偏涨或偏跌。",
    [rail(0, "零轴 0")]),
  metric("cn-300etf-pcr-oi", "沪深300ETF期权持仓量 PCR", "cn", "positioning",
    "看盘后还没平仓的认沽合约有多少，相对认购有多重。", "对照价格和波动。", [], 3),
  metric("cn-300etf-pcr-volume", "沪深300ETF期权成交量 PCR", "cn", "positioning",
    "看当天认沽和认购哪类成交更活跃。", "留意认沽交易热度。", [], 3),
  metric("us-option-pcr-volume", "美股期权成交量 PCR", "us", "positioning",
    "看个股和总体期权里，认沽相对认购成交有多活跃。", "对照个股与总体。", [], 3),
  metric("aaii", "AAII个人投资者调查", "us", "positioning",
    "看美国散户说看涨的人比看跌的人多多少。极端读数可结合价格找分歧。", "对照机构仓位。",
    [rail(-20, "偏看跌 −20%", "low"), rail(0, "看涨看跌均衡"), rail(20, "偏看涨 +20%", "high")]),
  metric("naaim", "NAAIM管理人自报仓位", "us", "positioning",
    "看主动管理人自己报了多少股票敞口。仓位高时更容易集中在同一方向。", "对照散户看法。",
    [rail(40, "轻仓 40%", "low"), rail(85, "高仓位 85%", "high")]),
  metric("finra-margin", "FINRA客户融资", "us", "positioning",
    "看美国融资账户借款的月度水位。长期升高时，留意杠杆对行情的影响。", "结合融资同比。"),
  metric("baker-wurgler", "Baker–Wurgler · 月度情绪背景", "us", "positioning",
    "用较慢的月度数据看美股情绪水位。虚线接续近期融资和调查提供的代理读数。", "作者与代理分开读。",
    [rail(0, "中轴 0")], 3),
].map(item => [item.id, item]));

export const PANEL_QUERY_KEY = ["marketObservationPanel", "panel.v1"] as const;
export const PANEL_URL = "/research/market-observation-panel/panel.v1.json";
export const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
export const latest = (data?: ObservationCardData) => data?.points[data.points.length - 1];
export function formatNumber(value: number | null | undefined, precision = 2): string { return finite(value) ? new Intl.NumberFormat("zh-CN", { maximumFractionDigits: precision }).format(value) : "暂无读数"; }
export function formatValue(value: number | null | undefined, unit: string, precision = 2): string { return finite(value) ? `${formatNumber(value, precision)}${unit === "%" ? "%" : unit ? ` ${unit}` : ""}` : "暂无读数"; }
export function isFresh(date: string | undefined, frequency: ObservationCardData["frequency"], now = new Date()): boolean {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const at = new Date(`${date}T00:00:00Z`).getTime();
  if (!Number.isFinite(at)) return false;
  const days = (now.getTime() - at) / 86_400_000;
  // Exchange holidays and release lags are deliberately given room; this is an availability flag, not a trading calendar.
  return days >= -.5 && days <= (frequency === "daily" ? 7 : frequency === "weekly" ? 16 : 70);
}
export function validPacket(input: unknown): input is ObservationPanelData {
  if (!input || typeof input !== "object") return false;
  const packet = input as ObservationPanelData;
  if (packet.schemaVersion !== 1 || typeof packet.generatedAt !== "string" || !packet.cards || typeof packet.cards !== "object" || Array.isArray(packet.cards)) return false;
  if (packet.partialUpdate !== undefined && (!packet.partialUpdate || typeof packet.partialUpdate.message !== "string"
    || !Array.isArray(packet.partialUpdate.cardIds) || !packet.partialUpdate.cardIds.every(id => typeof id === "string"))) return false;
  return Object.values(packet.cards).every(card => card && ["daily", "weekly", "monthly"].includes(card.frequency)
    && typeof card.unit === "string" && typeof card.sourceName === "string" && Array.isArray(card.points)
    && card.points.every(point => point && typeof point.date === "string" && (point.value === null || finite(point.value)))
    && (card.lines === undefined || Array.isArray(card.lines) && card.lines.every(line => typeof line.id === "string" && typeof line.label === "string" && Array.isArray(line.points)))
    && (card.auxiliary === undefined || Array.isArray(card.auxiliary))
    && finite(card.window) && finite(card.observations)
    && (card.current_zscore === null || finite(card.current_zscore))
    && (card.current_percentile === null || finite(card.current_percentile)));
}
