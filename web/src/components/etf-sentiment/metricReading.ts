export type MetricGuide = {
  question: string;
  measure: string;
  scale: string;
  highLow: string;
  priceReading: string;
};

const historicalScale = "0—100为自身历史位置：分别与此前252、504个交易日比较，再取平均。90分位可粗读为比约90%的历史观测高；50附近居中。";
const priceGuide: MetricGuide = {
  question: "价格相对近期趋势，偏上还是偏下？",
  measure: "收盘价相对20日指数均线（EMA20）的有正负偏离，按近20日波动缩放，再比较自身历史。",
  scale: historicalScale,
  highLow: "高值表示偏离比自身过去更靠上；低值更靠下。分位保留相对位置，单凭它不能确认价格实际在均线上还是下。",
  priceReading: "看上图上涨时偏离是否也升高、回落时是否收敛，用来观察价格拉伸与修复。这项来自价格本身。",
};

export const metricGuides: Record<string, MetricGuide> = {
  activity_pct: {
    question: "这个行业的交易现在有多热？",
    measure: "行业指数看近5日平均成交量；一级行业样本看近5日成交额占比。都与自身过去比较。",
    scale: historicalScale,
    highLow: "越高越活跃，可作为交易拥挤的观察线索；越低越冷清。上涨或下跌放量都能升高，需结合上图判断方向。",
    priceReading: "价格涨、活跃升：上涨同时得到更多交易参与；活跃很高、价格推不动或转跌：重点观察量价是否转弱。",
  },
  price_pct: priceGuide,
  stall_score: {
    question: "成交很热，价格却推不动了吗？",
    measure: "（成交活跃分位＋100−近5日涨幅分位）÷2，比较交易热度与短期价格推进。",
    scale: "0—100是组合分，不是历史分位。80分不表示超过历史80%，也没有已验证的统一高危分界。",
    highLow: "活跃越高、5日涨幅在历史中越弱，组合分越高；低分表示这种不协调较弱。高分时价格仍可能上涨。",
    priceReading: "高分时对照上图，看价格是否横住、冲高回落或仍在上涨；可观察量价不协调，尚未证明能识别派发者。",
  },
  heat_pct: {
    question: "小单相对大单的流量，在行业中排多靠前？",
    measure: "小单与大单净流量差额的20日平均，在当天有资料的行业中排序。",
    scale: "0—100是当日行业位次：90约为当天排名前10%，比较对象是其他行业，不是自己的历史。",
    highLow: "越高，说明小单相对大单的流量指标排名越靠前；越低越靠后。订单大小无法直接认定散户或机构身份。",
    priceReading: "对照价格看订单结构与行情是否同向、是否持续或背离；旧资料只支持有限风险线索。",
  },
  legacy_z: {
    question: "小单流量相对自己过去异常了多少？",
    measure: "20日平均小单流量经估算市值缩放，再与此前120个完整观测的均值和波动比较。",
    scale: "单位是历史标准差：0接近自身均值，正值偏强，负值偏弱；1.5表示高出约1.5个历史标准差。",
    highLow: "越高表示向上的流量异常越强；低于0表示低于历史均值。1.5是旧强热条件之一，需结合行业普涨程度。",
    priceReading: "观察小单流量异常是否伴随价格加速或滞涨，再看“旧强热提示”是否同时满足普涨条件。",
  },
  legacy_alarm: {
    question: "旧强热的三项条件同时出现了吗？",
    measure: "小单流量异常≥1.5，且行业中站上50日、200日均线的股票比例都>70%，同时成立时亮起。",
    scale: "1＝三项同时满足；0＝资料齐全但未同时满足；空白＝缺资料。这里没有分位或情绪好坏分数。",
    highLow: "亮起表示流量异常与行业普涨叠加。历史风险线索较强，但触发稀少，也有亮起后继续上涨的情况。",
    priceReading: "在上图看亮起后继续冲高、震荡还是回落，并留意持续时间；0只表示条件未齐，不表示安全。",
  },
  rawcorr_pct: {
    question: "行业里的股票是否越来越一起涨跌？",
    measure: "行业成员近20日收益两两相关性的平均值，再比较自身历史；包含整个市场共同波动。",
    scale: historicalScale,
    highLow: "越高表示相对自身历史越同步，越低表示更分化。同步可能来自共同消息或市场走势。",
    priceReading: "结合上图区分同步上涨与同步下跌；用于观察齐涨齐跌程度，风险预警增量尚不稳定。",
  },
  residcorr_pct: {
    question: "扣掉大盘影响后，行业内还同步吗？",
    measure: "先用历史关系扣除共同市场涨跌，再计算成员剩余收益的20日相关性和历史位置。",
    scale: historicalScale,
    highLow: "越高表示大盘之外的行业共振越强；越低表示个股差异较多。它不能直接识别共同持有人。",
    priceReading: "与“行业内部同步”一起看：两者都高，行业自身共振更明显；原始同步高而这项低，更多可能随市场。",
  },
  etf_activity_pct: {
    question: "这只ETF本身的交易有多热？",
    measure: "这只ETF近5日平均成交量，相对它自己过去的交易量。行业热度与ETF交易热度可以不同。",
    scale: historicalScale,
    highLow: "越高表示这只ETF交易越活跃，越低越冷清；ETF份额规模也会影响成交量。",
    priceReading: "对照ETF价格看放量上涨、放量不涨或缩量；当前用于状态观察，尚未单独检验这只ETF的预警效果。",
  },
  etf_price_pct: { ...priceGuide, measure: "只用这只ETF收盘价相对EMA20的有正负偏离，按近期波动缩放，再比较它自身历史。" },
};

export function referenceLabel(id: string, value: number, original: string): string {
  if (id === "activity_pct" || id === "etf_activity_pct") return `交易偏热参考 · ${value}`;
  if (id === "price_pct" || id === "etf_price_pct") return `偏离偏高参考 · ${value}`;
  if (id === "heat_pct") return `当日行业前${100 - value}% · ${value}`;
  if (id === "rawcorr_pct" || id === "residcorr_pct") return `高同步参考 · ${value}`;
  if (id === "legacy_z") return `旧强热条件之一 · ${value}`;
  return original;
}

export function referenceReading(id: string, threshold: number | undefined): string {
  if (threshold == null) return id === "legacy_alarm" ? "看0/1状态：1为条件齐备，0为未齐备；缺资料留白。" : "组合分暂不设统一危险线，先看分数变化与价格表现。";
  if (id === "legacy_z") return `≥${threshold}满足旧强热的流量条件；低于它表示该条件未满足。`;
  if (id === "heat_pct") return `≥${threshold}进入当天行业排名前约${100 - threshold}%；低于它表示未进入这组前排。`;
  const meaning = id.includes("activity") ? "高活跃" : id.includes("price") ? "偏离偏高" : "高同步";
  return `≥${threshold}进入${meaning}参考区，可粗看作自身历史较高的前约${100 - threshold}%；<${threshold}表示尚未达到这条线。P${threshold}取近1年、2年分位的平均，是观察参考，非顶底分界。`;
}

export function currentReading(id: string, value: number | null | undefined, threshold: number | undefined): string {
  if (value == null || !Number.isFinite(value)) return "这一天没有可用指标，先查看有资料的日期。";
  if (id === "legacy_alarm") return value === 1 ? "旧强热亮起：流量异常与行业普涨同时出现。" : "旧强热未亮起：三项条件未同时满足。";
  if (id === "stall_score") return "读作量价不协调的组合分，越高越值得对照价格是否推得动。";
  if (id === "legacy_z") return value >= (threshold ?? Infinity) ? "流量异常达到旧强热的单项条件，继续查看行业普涨条件。" : value < 0 ? "小单流量低于自身历史均值。" : "小单流量高于或接近自身均值，尚未达到旧强热的单项参考。";
  if (id === "heat_pct") return value >= (threshold ?? Infinity) ? "小单相对大单的流量指标排在当日行业前列。" : "按当天行业之间的相对排名阅读，尚未进入虚线以上的前排。";
  const high = threshold != null && value >= threshold;
  if (id.includes("activity")) return high ? "交易处于自身历史高活跃区，可留意价格能否继续推进。" : value >= 50 ? "交易活跃度处于历史中位以上，尚未进入高活跃参考区。" : "交易活跃度处于历史中位以下，参与相对偏冷。";
  if (id.includes("price")) return high ? "有正负的价格偏离处于历史偏高区，留意价格拉伸和回落。" : value >= 50 ? "价格偏离在自身历史中偏上，尚未进入偏高参考区。" : "价格偏离在自身历史中偏下，结合价格看弱势或修复。";
  return high ? "行业内同步程度处于历史高位，观察是一起涨还是一起跌。" : value >= 50 ? "同步程度处于历史中位以上，尚未达到高同步参考。" : "同步程度处于历史中位以下，个股走势相对分化。";
}
